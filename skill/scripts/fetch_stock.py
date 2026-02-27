#!/usr/bin/env python3
"""
东方财富股票数据抓取工具 v3.1
支持两种模式：
1. API模式（默认）：快速获取实时行情数据
2. 浏览器模式：使用 Playwright 获取完整页面数据（资金流向、新闻、F10等）

支持市场：
- A股：sh600519, sz300750, bj830799
- 港股：hk/00700
- 美股：us/MU, us/AAPL

用法：
    # API模式（快速）
    python fetch_stock.py 600519 --market sh
    
    # 浏览器模式（完整数据）
    python fetch_stock.py 600519 --market sh --browser
    
    # 获取资金流向
    python fetch_stock.py 600519 --market sh --fund-flow
    
    # 获取完整页面内容（转为Markdown）
    python fetch_stock.py 600519 --market sh --full-page
"""

import argparse
import json
import sys
import time
import re
from typing import Optional, Dict, Any

try:
    import requests
    USE_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.parse
    USE_REQUESTS = False

# Playwright 支持
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# 东方财富 API 基础 URL
BASE_API = "https://push2.eastmoney.com/api/qt/stock/get"


def get_secid(code: str, market: str) -> str:
    """
    根据市场类型生成 secid
    A股沪市: 1.代码  A股深市: 0.代码  港股: 116.代码  美股: 105.代码
    """
    market = market.lower()
    code = code.upper()
    
    if market == 'hk':
        return f"116.{code}"
    elif market == 'us':
        return f"105.{code}"
    elif market == 'sh':
        return f"1.{code}"
    elif market == 'sz':
        return f"0.{code}"
    elif market == 'bj':
        return f"0.{code}"
    elif market == 'auto':
        if code.isdigit():
            if code.startswith('6'):
                return f"1.{code}"
            elif code.startswith(('0', '3')):
                return f"0.{code}"
            elif code.startswith(('8', '4')):
                return f"0.{code}"
            elif len(code) == 5:
                return f"116.{code}"
        else:
            return f"105.{code}"
    
    raise ValueError(f"无法识别的市场类型: {market}")


def get_stock_url(code: str, market: str) -> Dict[str, str]:
    """获取股票相关页面URL"""
    market = market.lower()
    code_lower = code.lower() if not code.isdigit() else code
    
    urls = {}
    
    if market in ['sh', 'sz', 'bj']:
        prefix = market
        urls['quote'] = f"https://quote.eastmoney.com/{prefix}{code}.html"
        urls['fund_flow'] = f"https://data.eastmoney.com/zjlx/{code}.html"
        urls['f10'] = f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={prefix.upper()}{code}"
        urls['news'] = f"https://so.eastmoney.com/news/s?keyword={code}"
        urls['report'] = f"https://data.eastmoney.com/report/stock/{code}.html"
    elif market == 'hk':
        urls['quote'] = f"https://quote.eastmoney.com/hk/{code}.html"
        urls['fund_flow'] = f"https://data.eastmoney.com/zjlx/hk{code}.html"
    elif market == 'us':
        urls['quote'] = f"https://quote.eastmoney.com/us/{code.upper()}.html"
    
    return urls


def search_stock_code(name: str) -> Optional[Dict[str, str]]:
    """通过股票名称搜索股票代码"""
    try:
        search_url = "https://searchadapter.eastmoney.com/api/suggest/get"
        params = {
            "input": name,
            "type": "14",
            "token": "D43BF722C8E33BDC906FB84D85E326E8",
            "count": "5"
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        
        if USE_REQUESTS:
            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            data = response.json()
        else:
            import gzip
            url = f"{search_url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url)
            for k, v in headers.items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.info().get('Content-Encoding') == 'gzip':
                    raw = gzip.decompress(resp.read())
                else:
                    raw = resp.read()
                data = json.loads(raw.decode('utf-8'))
        
        if data.get('QuotationCodeTable', {}).get('Data'):
            first = data['QuotationCodeTable']['Data'][0]
            code = first.get('Code', '')
            name = first.get('Name', '')
            market_id = first.get('MktNum', '')
            
            if market_id == '1':
                market = 'sh'
            elif market_id == '0':
                market = 'sz'
            elif market_id == '116':
                market = 'hk'
            elif market_id == '105':
                market = 'us'
            else:
                market = 'auto'
            
            return {
                'code': code,
                'name': name,
                'market': market,
                'secid': f"{market_id}.{code}"
            }
    except Exception as e:
        print(f"搜索股票代码失败: {e}", file=sys.stderr)
    
    return None


def fetch_stock_api(code: str, market: str, retry: int = 3) -> Dict[str, Any]:
    """通过东方财富 API 获取股票实时数据"""
    result = {
        "success": False,
        "code": code,
        "market": market.upper(),
        "data": {},
        "error": None,
        "source": "东方财富API",
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # 如果输入的是中文名称，先搜索代码
        if not code.isalnum() or (not code.isdigit() and not code.isupper()):
            print(f"正在搜索股票: {code}...", file=sys.stderr)
            search_result = search_stock_code(code)
            if search_result:
                code = search_result['code']
                market = search_result['market']
                secid = search_result['secid']
                result['code'] = code
                result['market'] = market.upper()
                result['search_name'] = search_result['name']
                print(f"找到股票: {search_result['name']} ({code})", file=sys.stderr)
            else:
                result["error"] = f"未找到股票: {code}"
                return result
        else:
            secid = get_secid(code, market)
        
        fields = "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f163,f167,f168,f169,f170"
        params = {
            "secid": secid,
            "fields": fields,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b"
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://quote.eastmoney.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        
        print(f"正在获取数据: {secid}...", file=sys.stderr)
        
        api_data = None
        last_error = None
        
        for attempt in range(retry):
            try:
                if USE_REQUESTS:
                    session = requests.Session()
                    response = session.get(BASE_API, params=params, headers=headers, timeout=15)
                    api_data = response.json()
                else:
                    import gzip
                    url = f"{BASE_API}?{urllib.parse.urlencode(params)}"
                    req = urllib.request.Request(url)
                    for k, v in headers.items():
                        req.add_header(k, v)
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        if resp.info().get('Content-Encoding') == 'gzip':
                            data = gzip.decompress(resp.read())
                        else:
                            data = resp.read()
                        api_data = json.loads(data.decode('utf-8'))
                break
            except Exception as e:
                last_error = e
                if attempt < retry - 1:
                    print(f"重试 {attempt + 2}/{retry}...", file=sys.stderr)
                    time.sleep(1)
        
        if api_data is None:
            result["error"] = f"网络请求失败: {last_error}"
            return result
        
        if api_data.get('rc') != 0 or not api_data.get('data'):
            result["error"] = "API返回数据为空"
            return result
        
        raw = api_data['data']
        
        def safe_price(val, divisor=100):
            if val is None or val == '-':
                return '-'
            try:
                return f"{float(val) / divisor:.2f}"
            except:
                return '-'
        
        def safe_percent(val):
            if val is None or val == '-':
                return '-'
            try:
                return f"{float(val) / 100:.2f}%"
            except:
                return '-'
        
        def safe_amount(val):
            if val is None or val == '-':
                return '-'
            try:
                v = float(val)
                if v >= 1e12:
                    return f"{v/1e12:.2f}万亿"
                elif v >= 1e8:
                    return f"{v/1e8:.2f}亿"
                elif v >= 1e4:
                    return f"{v/1e4:.2f}万"
                else:
                    return f"{v:.2f}"
            except:
                return '-'
        
        data = {
            'code': raw.get('f57', code),
            'name': raw.get('f58', ''),
            'price': safe_price(raw.get('f43')),
            'change': safe_price(raw.get('f169')),
            'change_percent': safe_percent(raw.get('f170')),
            'open': safe_price(raw.get('f46')),
            'prev_close': safe_price(raw.get('f60')),
            'high': safe_price(raw.get('f44')),
            'low': safe_price(raw.get('f45')),
            'volume': raw.get('f47', '-'),
            'amount': safe_amount(raw.get('f48')),
            'market_cap': safe_amount(raw.get('f116')),
            'float_cap': safe_amount(raw.get('f117')),
            'pe': safe_price(raw.get('f162'), 100) if raw.get('f162') else safe_price(raw.get('f163'), 100),
            'pb': safe_price(raw.get('f167'), 100),
            'turnover': safe_percent(raw.get('f168')),
            'volume_ratio': safe_price(raw.get('f50'), 100),
            'limit_up': safe_price(raw.get('f51')),
            'limit_down': safe_price(raw.get('f52')),
        }
        
        result['data'] = data
        urls = get_stock_url(code, market)
        result['urls'] = urls
        result['url'] = urls.get('quote', '')
        
        if data.get('price') and data['price'] != '-':
            result['success'] = True
            print(f"✅ 成功获取数据: {data.get('name', code)} 价格: {data['price']}", file=sys.stderr)
        else:
            result['error'] = "无法获取有效价格数据"
            
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ 错误: {result['error']}", file=sys.stderr)
    
    return result


def fetch_page_with_playwright(url: str, wait_time: int = 3) -> Dict[str, Any]:
    """使用 Playwright 获取页面完整内容"""
    if not HAS_PLAYWRIGHT:
        return {
            "success": False,
            "error": "Playwright 未安装，请运行: pip install playwright && python -m playwright install chromium"
        }
    
    result = {
        "success": False,
        "url": url,
        "content": "",
        "text": "",
        "error": None
    }
    
    try:
        print(f"正在使用浏览器访问: {url}...", file=sys.stderr)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            
            # 访问页面，使用 domcontentloaded 而不是 networkidle
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # 等待动态内容加载
            time.sleep(wait_time)
            
            # 尝试等待特定元素
            try:
                page.wait_for_selector('body', timeout=5000)
            except:
                pass
            
            # 获取页面内容
            result['content'] = page.content()
            result['text'] = page.inner_text('body')
            result['title'] = page.title()
            result['success'] = True
            
            print(f"✅ 页面加载成功: {result['title']}", file=sys.stderr)
            
            browser.close()
            
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ 浏览器访问失败: {e}", file=sys.stderr)
    
    return result


def fetch_fund_flow_browser(code: str, market: str) -> Dict[str, Any]:
    """使用 Playwright 获取资金流向数据"""
    urls = get_stock_url(code, market)
    fund_flow_url = urls.get('fund_flow')
    
    if not fund_flow_url:
        return {"success": False, "error": "该市场不支持资金流向查询"}
    
    result = {
        "success": False,
        "code": code,
        "market": market.upper(),
        "data": {},
        "error": None,
        "source": "东方财富(Playwright)",
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    page_result = fetch_page_with_playwright(fund_flow_url, wait_time=4)
    
    if not page_result['success']:
        result['error'] = page_result['error']
        return result
    
    text = page_result['text']
    
    # 解析资金流向数据
    data = {}
    
    # 主力净流入
    main_flow_match = re.search(r'今日主力净流入[：:]\s*([-\d.]+[亿万]?)', text)
    if main_flow_match:
        data['main_flow'] = main_flow_match.group(1)
    
    # 主力净比
    main_ratio_match = re.search(r'主力净比[：:]\s*([-\d.]+%)', text)
    if main_ratio_match:
        data['main_ratio'] = main_ratio_match.group(1)
    
    # 超大单
    super_large_match = re.search(r'超大单净流入[：:]\s*([-\d.]+[亿万]?)', text)
    if super_large_match:
        data['super_large_flow'] = super_large_match.group(1)
    
    # 大单
    large_match = re.search(r'大单净流入[：:]\s*([-\d.]+[亿万]?)', text)
    if large_match:
        data['large_flow'] = large_match.group(1)
    
    # 中单
    medium_match = re.search(r'中单净流入[：:]\s*([-\d.]+[亿万]?)', text)
    if medium_match:
        data['medium_flow'] = medium_match.group(1)
    
    # 小单
    small_match = re.search(r'小单净流入[：:]\s*([-\d.]+[亿万]?)', text)
    if small_match:
        data['small_flow'] = small_match.group(1)
    
    # 尝试从表格中提取更多数据
    # 5日主力净流入
    five_day_match = re.search(r'5日主力净流入[：:]\s*([-\d.]+[亿万]?)', text)
    if five_day_match:
        data['main_flow_5d'] = five_day_match.group(1)
    
    # 10日主力净流入
    ten_day_match = re.search(r'10日主力净流入[：:]\s*([-\d.]+[亿万]?)', text)
    if ten_day_match:
        data['main_flow_10d'] = ten_day_match.group(1)
    
    result['data'] = data
    result['raw_text'] = text[:5000]  # 保留部分原始文本用于调试
    
    if data:
        result['success'] = True
        print(f"✅ 成功获取资金流向数据", file=sys.stderr)
    else:
        result['error'] = "无法解析资金流向数据"
    
    return result


def fetch_full_page(url: str) -> Dict[str, Any]:
    """获取完整页面并转换为Markdown格式"""
    page_result = fetch_page_with_playwright(url, wait_time=4)
    
    if not page_result['success']:
        return page_result
    
    # 简单的HTML到文本转换
    text = page_result['text']
    
    # 清理文本
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line and len(line) > 1:
            cleaned_lines.append(line)
    
    page_result['markdown'] = '\n'.join(cleaned_lines)
    
    return page_result


def format_output(result: Dict[str, Any], output_format: str = "json") -> str:
    """格式化输出"""
    if output_format == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    else:
        lines = []
        lines.append(f"═══════════════════════════════════════════════════")
        lines.append(f"  股票代码: {result['code']} ({result['market']})")
        lines.append(f"  数据来源: {result['source']}")
        lines.append(f"  获取时间: {result['fetch_time']}")
        lines.append(f"═══════════════════════════════════════════════════")
        
        if result["success"]:
            data = result["data"]
            name = data.get('name', '未知')
            
            change = data.get('change', '-')
            if change != '-' and float(change) > 0:
                trend = "📈"
            elif change != '-' and float(change) < 0:
                trend = "📉"
            else:
                trend = "➡️"
            
            lines.append(f"")
            lines.append(f"  📊 {name} ({data.get('code', result['code'])})")
            lines.append(f"")
            lines.append(f"  💰 当前价格: {data.get('price', '-')}")
            lines.append(f"  {trend} 涨跌额:   {change}")
            lines.append(f"  {trend} 涨跌幅:   {data.get('change_percent', '-')}")
            lines.append(f"")
            lines.append(f"  ┌─────────────────────────────────────────────┐")
            lines.append(f"  │ 今开: {data.get('open', '-'):>10}  │  昨收: {data.get('prev_close', '-'):>10} │")
            lines.append(f"  │ 最高: {data.get('high', '-'):>10}  │  最低: {data.get('low', '-'):>10} │")
            lines.append(f"  │ 涨停: {data.get('limit_up', '-'):>10}  │  跌停: {data.get('limit_down', '-'):>10} │")
            lines.append(f"  └─────────────────────────────────────────────┘")
            lines.append(f"")
            lines.append(f"  成交额:   {data.get('amount', '-')}")
            lines.append(f"  总市值:   {data.get('market_cap', '-')}")
            lines.append(f"  流通市值: {data.get('float_cap', '-')}")
            lines.append(f"  换手率:   {data.get('turnover', '-')}")
            lines.append(f"  量比:     {data.get('volume_ratio', '-')}")
            lines.append(f"")
            lines.append(f"  市盈率(PE): {data.get('pe', '-')}")
            lines.append(f"  市净率(PB): {data.get('pb', '-')}")
            
            # 资金流向数据
            if 'main_flow' in data or 'main_ratio' in data:
                lines.append(f"")
                lines.append(f"  ═══ 资金流向 ═══")
                if 'main_flow' in data:
                    lines.append(f"  主力净流入: {data.get('main_flow', '-')}")
                if 'main_ratio' in data:
                    lines.append(f"  主力净比:   {data.get('main_ratio', '-')}")
                if 'super_large_flow' in data:
                    lines.append(f"  超大单:     {data.get('super_large_flow', '-')}")
                if 'large_flow' in data:
                    lines.append(f"  大单:       {data.get('large_flow', '-')}")
        else:
            lines.append(f"")
            lines.append(f"  ❌ 获取失败: {result.get('error', '未知错误')}")
        
        lines.append(f"")
        lines.append(f"═══════════════════════════════════════════════════")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="东方财富股票数据抓取工具 v3.1 (API + Playwright)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s 00700 --market hk              # API模式获取港股
  %(prog)s 600519 --market sh --browser   # 浏览器模式获取A股
  %(prog)s 华丰科技 --fund-flow           # 获取资金流向
  %(prog)s 600519 --full-page             # 获取完整页面内容
"""
    )
    parser.add_argument("code", nargs='?', default=None, help="股票代码或名称")
    parser.add_argument("--market", "-m", default="auto",
                        choices=["hk", "us", "sh", "sz", "bj", "auto"],
                        help="市场类型 (默认: auto)")
    parser.add_argument("--output", "-o", default="json",
                        choices=["json", "text"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--browser", "-b", action="store_true",
                        help="使用浏览器模式获取完整数据")
    parser.add_argument("--fund-flow", "-f", action="store_true",
                        help="获取资金流向数据")
    parser.add_argument("--full-page", action="store_true",
                        help="获取完整页面内容（Markdown格式）")
    parser.add_argument("--url", "-u", type=str,
                        help="直接访问指定URL获取内容")
    
    # 兼容旧参数
    parser.add_argument("--timeout", "-t", type=int, default=15, help="(保留兼容)")
    parser.add_argument("--show-browser", action="store_true", help="(保留兼容)")
    parser.add_argument("--with-flow", action="store_true", help="(保留兼容，等同于--fund-flow)")
    
    args = parser.parse_args()
    
    # 处理直接URL访问
    if args.url:
        result = fetch_full_page(args.url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result.get('success') else 1)
    
    # 处理资金流向
    if args.fund_flow or args.with_flow:
        # 先通过API获取基本信息
        api_result = fetch_stock_api(args.code, args.market)
        if api_result['success']:
            code = api_result['code']
            market = api_result['market'].lower()
        else:
            # 尝试搜索
            search_result = search_stock_code(args.code)
            if search_result:
                code = search_result['code']
                market = search_result['market']
            else:
                print(json.dumps(api_result, ensure_ascii=False, indent=2))
                sys.exit(1)
        
        # 获取资金流向
        flow_result = fetch_fund_flow_browser(code, market)
        
        # 合并结果
        if api_result['success']:
            flow_result['data'].update({
                'name': api_result['data'].get('name'),
                'price': api_result['data'].get('price'),
                'change_percent': api_result['data'].get('change_percent'),
            })
        
        print(format_output(flow_result, args.output) if args.output == 'text' else json.dumps(flow_result, ensure_ascii=False, indent=2))
        sys.exit(0 if flow_result['success'] else 1)
    
    # 处理完整页面获取
    if args.full_page:
        api_result = fetch_stock_api(args.code, args.market)
        if api_result['success'] and api_result.get('url'):
            result = fetch_full_page(api_result['url'])
            result['stock_data'] = api_result['data']
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0 if result.get('success') else 1)
        else:
            print(json.dumps(api_result, ensure_ascii=False, indent=2))
            sys.exit(1)
    
    # 默认API模式
    result = fetch_stock_api(args.code, args.market)
    print(format_output(result, args.output))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
