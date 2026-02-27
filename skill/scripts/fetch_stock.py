#!/usr/bin/env python3
"""
东方财富股票数据抓取工具 v3.0
使用东方财富 API 获取实时股票数据（无需 Selenium）

支持市场：
- A股：sh600519, sz300750, bj830799
- 港股：hk/00700
- 美股：us/MU, us/AAPL

用法：
    python fetch_stock.py <股票代码> [--market <市场>] [--output <json|text>]

示例：
    python fetch_stock.py 00700 --market hk
    python fetch_stock.py MU --market us
    python fetch_stock.py 600519 --market sh
    python fetch_stock.py 华丰科技 --market auto
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

# 东方财富 API 基础 URL
BASE_API = "https://push2.eastmoney.com/api/qt/stock/get"

# 字段映射说明
# f43: 最新价(分) f44: 最高(分) f45: 最低(分) f46: 今开(分)
# f47: 成交量(手) f48: 成交额 f49: 外盘 f50: 量比
# f51: 涨停价(分) f52: 跌停价(分) f55: 收益 f57: 股票代码
# f58: 股票名称 f60: 昨收(分) f116: 总市值 f117: 流通市值
# f162: 市盈率(动) f163: 市盈率(TTM) f167: 市净率
# f168: 换手率 f169: 涨跌额(分) f170: 涨跌幅(0.01%)


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
        # 自动识别
        if code.isdigit():
            if code.startswith('6'):
                return f"1.{code}"  # 沪市
            elif code.startswith(('0', '3')):
                return f"0.{code}"  # 深市
            elif code.startswith(('8', '4')):
                return f"0.{code}"  # 北交所
            elif len(code) == 5:
                return f"116.{code}"  # 港股
        else:
            return f"105.{code}"  # 美股
    
    raise ValueError(f"无法识别的市场类型: {market}")


def search_stock_code(name: str) -> Optional[Dict[str, str]]:
    """
    通过股票名称搜索股票代码
    """
    try:
        # 东方财富搜索 API
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
            'Accept': 'application/json'
        }
        
        if USE_REQUESTS:
            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            data = response.json()
        else:
            url = f"{search_url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url)
            for k, v in headers.items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        
        if data.get('QuotationCodeTable', {}).get('Data'):
            first = data['QuotationCodeTable']['Data'][0]
            code = first.get('Code', '')
            name = first.get('Name', '')
            market_id = first.get('MktNum', '')
            
            # 根据市场类型确定市场代码
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


def fetch_stock_data(code: str, market: str, retry: int = 3) -> Dict[str, Any]:
    """
    通过东方财富 API 获取股票实时数据
    """
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
        
        # 构建 API URL
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
                    response = session.get(
                        BASE_API, 
                        params=params, 
                        headers=headers, 
                        timeout=15
                    )
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
        
        # 解析数据
        # 价格类字段需要除以100（API返回的是分）
        # 涨跌幅需要除以100（API返回的是0.01%）
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
            'volume': raw.get('f47', '-'),  # 成交量(手)
            'amount': safe_amount(raw.get('f48')),  # 成交额
            'market_cap': safe_amount(raw.get('f116')),  # 总市值
            'float_cap': safe_amount(raw.get('f117')),  # 流通市值
            'pe': safe_price(raw.get('f162'), 100) if raw.get('f162') else safe_price(raw.get('f163'), 100),  # 市盈率
            'pb': safe_price(raw.get('f167'), 100),  # 市净率
            'turnover': safe_percent(raw.get('f168')),  # 换手率
            'volume_ratio': safe_price(raw.get('f50'), 100),  # 量比
            'limit_up': safe_price(raw.get('f51')),  # 涨停价
            'limit_down': safe_price(raw.get('f52')),  # 跌停价
        }
        
        result['data'] = data
        result['url'] = f"https://quote.eastmoney.com/{market.lower()}{code}.html" if market.lower() in ['sh', 'sz'] else f"https://quote.eastmoney.com/{market.lower()}/{code}.html"
        
        # 检查是否成功获取到价格
        if data.get('price') and data['price'] != '-':
            result['success'] = True
            print(f"✅ 成功获取数据: {data.get('name', code)} 价格: {data['price']}", file=sys.stderr)
        else:
            result['error'] = "无法获取有效价格数据"
            
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ 错误: {result['error']}", file=sys.stderr)
    
    return result


def fetch_fund_flow(code: str, market: str) -> Dict[str, Any]:
    """
    获取股票资金流向数据
    """
    result = {
        "success": False,
        "data": {},
        "error": None
    }
    
    try:
        secid = get_secid(code, market)
        
        # 资金流向 API
        base_url = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "klt": "1",  # 1分钟
            "lmt": "1",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b"
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Referer': 'https://quote.eastmoney.com/'
        }
        
        if USE_REQUESTS:
            response = requests.get(base_url, params=params, headers=headers, timeout=15)
            api_data = response.json()
        else:
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url)
            for k, v in headers.items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=15) as resp:
                api_data = json.loads(resp.read().decode('utf-8'))
        
        if api_data.get('data', {}).get('klines'):
            latest = api_data['data']['klines'][-1].split(',')
            # 格式: 时间,主力净流入,小单净流入,中单净流入,大单净流入,超大单净流入
            def safe_flow(val):
                try:
                    v = float(val)
                    if abs(v) >= 1e8:
                        return f"{v/1e8:.2f}亿"
                    elif abs(v) >= 1e4:
                        return f"{v/1e4:.2f}万"
                    else:
                        return f"{v:.2f}"
                except:
                    return '-'
            
            result['data'] = {
                'time': latest[0] if len(latest) > 0 else '-',
                'main_flow': safe_flow(latest[1]) if len(latest) > 1 else '-',
                'small_flow': safe_flow(latest[2]) if len(latest) > 2 else '-',
                'medium_flow': safe_flow(latest[3]) if len(latest) > 3 else '-',
                'large_flow': safe_flow(latest[4]) if len(latest) > 4 else '-',
                'super_large_flow': safe_flow(latest[5]) if len(latest) > 5 else '-',
            }
            result['success'] = True
            
    except Exception as e:
        result['error'] = str(e)
    
    return result


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
            
            # 判断涨跌颜色标记
            change = data.get('change', '-')
            change_pct = data.get('change_percent', '-')
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
            lines.append(f"  {trend} 涨跌幅:   {change_pct}")
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
        else:
            lines.append(f"")
            lines.append(f"  ❌ 获取失败: {result.get('error', '未知错误')}")
        
        lines.append(f"")
        lines.append(f"═══════════════════════════════════════════════════")
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="东方财富股票数据抓取工具 v3.0 (API版本)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s 00700 --market hk          # 获取腾讯控股(港股)
  %(prog)s MU --market us             # 获取美光科技(美股)
  %(prog)s 600519 --market sh         # 获取贵州茅台(A股沪市)
  %(prog)s 300750 --market sz         # 获取宁德时代(A股深市)
  %(prog)s 华丰科技 --market auto     # 通过名称搜索
  %(prog)s AAPL -m us -o text         # 文本格式输出
"""
    )
    parser.add_argument("code", help="股票代码或名称")
    parser.add_argument("--market", "-m", default="auto",
                        choices=["hk", "us", "sh", "sz", "bj", "auto"],
                        help="市场类型 (默认: auto 自动识别)")
    parser.add_argument("--output", "-o", default="json",
                        choices=["json", "text"],
                        help="输出格式 (默认: json)")
    parser.add_argument("--with-flow", "-f", action="store_true",
                        help="同时获取资金流向数据")
    
    # 保留旧参数兼容性
    parser.add_argument("--show-browser", action="store_true",
                        help="(已废弃，保留兼容)")
    parser.add_argument("--timeout", "-t", type=int, default=15,
                        help="(已废弃，保留兼容)")
    
    args = parser.parse_args()
    
    result = fetch_stock_data(
        code=args.code,
        market=args.market
    )
    
    # 如果需要资金流向
    if args.with_flow and result['success']:
        flow_result = fetch_fund_flow(result['code'], result['market'].lower())
        if flow_result['success']:
            result['data']['fund_flow'] = flow_result['data']
    
    print(format_output(result, args.output))
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
