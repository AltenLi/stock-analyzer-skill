# 东方财富数据获取参考

## 登录与限流说明

### 为什么需要登录？

东方财富网对未登录用户实施访问限流策略：
- 搜索请求频率限制
- 部分数据页面需要登录才能完整显示
- API接口调用次数限制

### 登录方式

**登录入口**：https://www.eastmoney.com/default.html （右上角登录按钮）

**支持的登录方式**：
1. 手机号 + 验证码（推荐）
2. 账号密码登录
3. 微信扫码登录
4. QQ扫码登录

**登录后的优势**：
- 数据获取更稳定
- 访问频率限制放宽
- 可查看更多详细数据

### 限流应对策略

如果遇到限流，可采取以下备选方案：
1. 使用 `web_search` 工具搜索股票信息作为补充
2. 降低访问频率，增加请求间隔
3. 优先获取核心数据（行情页面），其他数据用搜索补充

---

## ⏱️ 请求延迟规则（必须遵守）

### 延迟要求

> ⚠️ **每次请求东方财富网页面，必须延迟1秒后再发起下一次请求！**

### 执行模式

```
请求1 (web_fetch) 
    ↓
等待 1 秒
    ↓
请求2 (web_fetch)
    ↓
等待 1 秒
    ↓
请求3 (web_fetch)
    ↓
...
```

### 注意事项

| 场景 | 是否需要延迟 |
|------|-------------|
| `web_fetch` 访问东方财富页面 | ✅ 需要延迟1秒 |
| `web_search` 搜索引擎查询 | ❌ 不需要延迟 |
| 同一批次多个东方财富请求 | ✅ 必须串行，每次间隔1秒 |

### 失败处理

- 请求失败：等待2秒后重试一次
- 连续失败：改用 `web_search` 作为备选数据源

---

## 核心搜索流程

### 模拟主页搜索框

东方财富主页：https://www.eastmoney.com/default.html

主页上的搜索框输入股票名称后，实际上是调用统一搜索服务。搜索框的工作原理：

1. 用户在搜索框输入关键词（如"赛微电子"）
2. 点击搜索或按回车
3. 页面跳转到搜索结果页，URL格式为：
   ```
   https://so.eastmoney.com/Web/s?keyword={关键词}
   ```

### 搜索URL构建

```
# 基础搜索URL（模拟主页搜索框）
https://so.eastmoney.com/Web/s?keyword={股票名称}

# URL编码示例
赛微电子 → https://so.eastmoney.com/Web/s?keyword=赛微电子
比亚迪 → https://so.eastmoney.com/Web/s?keyword=比亚迪
```

### 从搜索结果获取股票信息

搜索结果页会显示匹配的股票，包含：
- 股票代码（如：300456）
- 股票简称（如：赛微电子）
- 市场标识（深圳/上海/北京）
- 股票详情页链接

## URL模板大全

### 1. 股票搜索（主页搜索框）
```
https://so.eastmoney.com/Web/s?keyword={股票名称或代码}
```

### 2. 股票详情页
```
# 深圳股票（0、3开头）
https://quote.eastmoney.com/sz{股票代码}.html

# 上海股票（6开头）
https://quote.eastmoney.com/sh{股票代码}.html

# 北京股票（8、4开头）
https://quote.eastmoney.com/bj{股票代码}.html
```

### 3. 个股资料（F10）
```
https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={市场代码}{股票代码}

# 子页面
# 公司概况
https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={市场代码}{股票代码}#/gsgk
# 财务分析
https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={市场代码}{股票代码}#/cwfx
# 股东研究
https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={市场代码}{股票代码}#/gdyj
# 股本结构
https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code={市场代码}{股票代码}#/gbjg
```

### 4. 资金流向
```
# 个股资金流向
https://data.eastmoney.com/zjlx/{股票代码}.html

# 主力追踪
https://data.eastmoney.com/zlsj/{股票代码}.html
```

### 5. 公告新闻
```
# 公司公告
https://data.eastmoney.com/notices/stock/{股票代码}.html

# 个股新闻
https://so.eastmoney.com/news/s?keyword={股票名称}

# 研究报告
https://data.eastmoney.com/report/stock/{股票代码}.html
```

### 6. 融资融券
```
https://data.eastmoney.com/rzrq/detail/{股票代码}.html
```

### 7. 北向资金持股
```
https://data.eastmoney.com/hsgtcg/stock.html?scode={股票代码}
```

### 8. 龙虎榜
```
https://data.eastmoney.com/stock/lhb/{股票代码}.html
```

### 9. 行业板块
```
https://quote.eastmoney.com/center/boardlist.html#industry_board
```

## 市场代码对照表

| 股票代码开头 | 市场代码 | 交易所 |
|-------------|---------|--------|
| 000xxx | sz | 深圳主板 |
| 001xxx | sz | 深圳主板 |
| 002xxx | sz | 深圳中小板 |
| 003xxx | sz | 深圳主板 |
| 300xxx | sz | 深圳创业板 |
| 301xxx | sz | 深圳创业板 |
| 600xxx | sh | 上海主板 |
| 601xxx | sh | 上海主板 |
| 603xxx | sh | 上海主板 |
| 605xxx | sh | 上海主板 |
| 688xxx | sh | 上海科创板 |
| 689xxx | sh | 上海科创板 |
| 430xxx | bj | 北交所 |
| 830xxx | bj | 北交所 |
| 831xxx | bj | 北交所 |

## 常用财务指标说明

### 估值指标
- **市盈率(PE)**: 股价/每股收益，反映估值水平
  - PE-TTM: 滚动市盈率，最近12个月
  - PE(动): 动态市盈率，预测值
  - PE(静): 静态市盈率，上年年报
- **市净率(PB)**: 股价/每股净资产
- **市销率(PS)**: 总市值/营业收入

### 盈利指标
- **ROE**: 净资产收益率 = 净利润/净资产
- **毛利率**: (营收-成本)/营收
- **净利率**: 净利润/营收
- **EPS**: 每股收益 = 净利润/总股本

### 成长指标
- **营收增长率**: (本期营收-上期营收)/上期营收
- **净利润增长率**: (本期净利-上期净利)/上期净利
- **扣非净利润增长率**: 扣除非经常性损益后的增长

### 风险指标
- **资产负债率**: 总负债/总资产
- **流动比率**: 流动资产/流动负债
- **速动比率**: (流动资产-存货)/流动负债

## 投资评级标准

### 估值评级
| PE水平 | 评级 |
|--------|------|
| PE < 15 且低于行业均值30%以上 | 显著低估 |
| PE < 20 且低于行业均值 | 低估 |
| PE 在行业均值±20%内 | 合理 |
| PE > 行业均值20%以上 | 偏高 |
| PE > 行业均值50%以上 | 高估 |

### ROE评级
| ROE水平 | 评级 |
|---------|------|
| ROE > 20% | 优秀 |
| 15% < ROE ≤ 20% | 良好 |
| 10% < ROE ≤ 15% | 一般 |
| ROE ≤ 10% | 较差 |

### 成长性评级
| 净利润增长率 | 评级 |
|-------------|------|
| > 50% | 高成长 |
| 20% - 50% | 较快成长 |
| 0% - 20% | 稳定成长 |
| < 0% | 负增长 |

### 资金面评级

#### ⭐ 主力净比（核心指标）

**数据来源**：东方财富资金流向页面直接读取
```
页面URL：https://data.eastmoney.com/zjlx/{股票代码}.html
位置：实时资金流向区域 → "今日主力净流入"数值右侧
字段：主力净比
格式示例：17.23%、-5.67%
```

> ✅ **无需计算**：直接从页面读取"主力净比"字段值即可！

| 主力净比 | 评级 | 说明 |
|---------|------|------|
| > 10% | 🔴 强势介入 | 主力大举买入，短期强烈看多信号 |
| 5% - 10% | 🟠 明显流入 | 主力积极布局，值得重点关注 |
| 0% - 5% | 🟡 小幅流入 | 主力温和买入，可适当关注 |
| -5% - 0% | 🟢 小幅流出 | 主力小规模减仓，需保持警惕 |
| < -5% | ⚫ 明显流出 | 主力撤离信号，建议回避 |

> ⚠️ **重要提示**：主力净比是判断短期资金动向的核心指标，权重最高！

#### 5日主力净流入（中期指标）

| 主力净流入(5日) | 评级 |
|----------------|------|
| > 5亿 | 强势流入 |
| 1-5亿 | 明显流入 |
| -1亿 - 1亿 | 资金平衡 |
| -5亿 - -1亿 | 明显流出 |
| < -5亿 | 强势流出 |

## 买卖点位计算参考

### 支撑位计算
1. 近期低点
2. 均线支撑（20日/60日/120日）
3. 成交密集区下沿
4. 黄金分割位（0.618回撤）

### 压力位计算
1. 近期高点
2. 均线压力
3. 成交密集区上沿
4. 前期套牢盘位置

### 目标价计算方法
1. **PE估值法**: 目标PE × 预测EPS
2. **PB估值法**: 目标PB × 每股净资产
3. **PEG估值法**: 合理PE = 净利润增长率 × 100
4. **相对估值法**: 参考同行业公司估值水平

---

## 并购重组估值计算方法

### 何时触发并购分析

当分析过程中发现公司存在以下情况时，需要执行并购估值分析：
- 公告拟收购/已收购某公司股权
- 重大资产重组方案
- 借壳上市/反向收购
- 战略性股权投资（较大比例）

### 并购标的数据获取

**搜索策略**（使用 `web_search`）：

```
# 第一轮：获取并购方案概要
"{收购方} 收购 {标的} 方案 公告"
"{收购方} 并购 重组 对价 股权比例"

# 第二轮：获取标的公司财务数据
"{标的公司} 营业收入 净利润 毛利率 年报"
"{标的公司} 财务数据 估值 行业"

# 第三轮：获取行业PE参考
"{标的所属行业} 行业平均PE A股 估值"
"{标的所属行业} 上市公司 PE中位数"

# 第四轮：获取并购进展
"{收购方} {标的} 并购 审批 进展 最新"
```

### 核心估值计算公式

#### 1. 并表后财务数据测算

```python
# 并表后营收
post_merge_revenue = acquirer_revenue + target_revenue * acquisition_ratio

# 并表后净利润
post_merge_net_profit = acquirer_net_profit + target_net_profit * acquisition_ratio

# 并表后毛利
post_merge_gross_profit = acquirer_gross_profit + target_gross_profit * acquisition_ratio

# 并表后毛利率
post_merge_gross_margin = post_merge_gross_profit / post_merge_revenue

# 并购后总股本（取决于支付方式）
if payment_method == "现金":
    post_merge_shares = acquirer_total_shares  # 现金收购不增发
elif payment_method == "股份":
    post_merge_shares = acquirer_total_shares + new_issued_shares
elif payment_method == "混合":
    post_merge_shares = acquirer_total_shares + new_issued_shares  # 仅股份部分增发

# 并表后EPS
post_merge_eps = post_merge_net_profit / post_merge_shares
```

#### 2. 三种场景估值

```python
# 获取标的行业PE分位数
industry_pe_25 = ...   # 25分位（保守）
industry_pe_50 = ...   # 50分位（中性）
industry_pe_75 = ...   # 75分位（乐观）

# 场景一：乐观
optimistic_market_cap = post_merge_net_profit * industry_pe_75
optimistic_price = optimistic_market_cap / post_merge_shares

# 场景二：中性
neutral_market_cap = post_merge_net_profit * industry_pe_50
neutral_price = neutral_market_cap / post_merge_shares

# 场景三：保守
conservative_market_cap = post_merge_net_profit * industry_pe_25
conservative_price = conservative_market_cap / post_merge_shares

# 涨幅空间
for scenario_price in [optimistic_price, neutral_price, conservative_price]:
    upside = (scenario_price - current_price) / current_price * 100
```

#### 3. 业绩承诺估值法（如有）

```python
# 若标的公司有业绩承诺（通常为3年）
promised_profits = [year1_profit, year2_profit, year3_profit]

# 基于承诺利润的估值
for year, profit in enumerate(promised_profits, 1):
    yearly_post_merge_profit = acquirer_net_profit + profit * acquisition_ratio
    yearly_market_cap = yearly_post_merge_profit * reasonable_pe
    yearly_price = yearly_market_cap / post_merge_shares
    yearly_upside = (yearly_price - current_price) / current_price * 100
```

#### 4. 商誉风险计算

```python
# 商誉 = 收购对价 - 标的可辨认净资产公允价值 × 收购比例
goodwill = acquisition_price - target_net_assets * acquisition_ratio

# 商誉/净资产 比率（风险指标）
goodwill_ratio = goodwill / acquirer_net_assets * 100

# 风险等级
if goodwill_ratio > 80:
    risk = "极高风险 - 商誉减值可能严重侵蚀利润"
elif goodwill_ratio > 50:
    risk = "高风险 - 需警惕商誉减值"
elif goodwill_ratio > 30:
    risk = "中等风险 - 商誉比例偏高"
else:
    risk = "可控风险 - 商誉比例合理"
```

### 并购分析核心指标速查

| 指标 | 公式 | 正面信号 | 负面信号 |
|------|------|---------|---------|
| 营收增厚率 | (标的营收×比例)/收购方营收 | >20% 显著增厚 | <5% 影响有限 |
| 利润增厚率 | (标的净利×比例)/收购方净利 | >30% 利润大幅提升 | <0 标的亏损 |
| 毛利率变化 | 并表后毛利率 - 原毛利率 | 上升 → 业务质量改善 | 下降 → 低毛利业务拖累 |
| EPS增厚/摊薄 | 并表后EPS vs 原EPS | EPS增厚 → 增值收购 | EPS摊薄 → 需更长回收期 |
| PE合理性 | 收购PE vs 行业PE | 收购PE < 行业PE → 低价收购 | 收购PE > 行业PE×2 → 溢价过高 |
| 商誉/净资产 | 商誉/收购方净资产 | <30% 可控 | >50% 高风险 |
| 对价/市值 | 收购对价/收购方市值 | <20% 影响可控 | >50% 蛇吞象风险 |
| 公告至今涨幅 | (当前价-公告日收盘价)/公告日收盘价 | <30% 市场反应温和 | >100% 严重过热，追高风险极大 |

### 公告日股价获取方法

获取并购公告首次发布日期对应的收盘价，用于计算"公告至今涨幅"：

**方法一：东方财富K线历史数据**
```
# 个股日K数据页面
https://quote.eastmoney.com/sz{股票代码}.html → 日K线图查找对应日期
```

**方法二：web_search 搜索**
```
"{股票名称} {公告日期} 收盘价"
"{股票代码} {公告日期} 股价 历史行情"
```

**涨幅预警等级**：
| 公告至今涨幅 | 预警等级 | 说明 |
|-------------|---------|------|
| <30% | 🟢 正常 | 市场温和反应 |
| 30%-50% | 🟡 偏高 | 已有较大涨幅，注意风险 |
| 50%-100% | 🟠 过热 | 可能过度炒作，追高风险大 |
| >100% | 🔴 严重过热 | 极可能透支预期，追高极危险 |
