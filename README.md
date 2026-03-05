# Stock Analyzer Skill

📊 股票综合分析工具 - AI编程助手 Skill

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## 功能介绍

根据用户输入的股票名称，从东方财富网获取股票信息，进行**基本面、新闻面、资金面**三维分析，给出投资建议、买入价位和卖出价位。

## 兼容性

本Skill兼容所有支持 `.codebuddy/skills/` 目录结构的AI编程助手工具。

## 安装

### 方式一：从GitHub安装（推荐）

在你的项目目录下运行：

```bash
npx github:AltenLi/stock-analyzer-skill
```

或者使用完整URL：

```bash
npx https://github.com/AltenLi/stock-analyzer-skill.git
```

### 方式二：全局安装

```bash
npm install -g github:AltenLi/stock-analyzer-skill
stock-analyzer-skill
```

### 方式三：手动安装

1. 克隆仓库：
```bash
git clone https://github.com/AltenLi/stock-analyzer-skill.git
```

2. 将 `skill/` 目录复制到你的项目：
```bash
cp -r stock-analyzer-skill/skill/ your-project/.codebuddy/skills/stock-analyzer/
```

## 特性

- 🔍 **智能搜索**：模拟东方财富主页搜索框，根据股票名称自动获取股票代码
- 📈 **多维分析**：
  - 基本面（35%）：PE/PB估值、ROE、成长性、财务健康
  - 新闻面（20%）：公告、研报、舆情分析
  - 资金面（35%）：**主力净比（核心指标）**、北向资金、融资融券
  - 技术面（10%）：均线、支撑压力位
- 💰 **投资建议**：综合评分 + 买入/卖出价位建议
- 📄 **双重输出**：Markdown报告 + 可视化HTML网页
- ⏱️ **防限流**：每次请求延迟1秒，避免被东方财富限流

## 触发关键词

- 分析股票、股票推荐、股票买卖点
- 股票研究、A股分析
- 东方财富 + 股票查询

## 使用示例

```
用户：帮我分析一下赛微电子这只股票
```

Skill会自动：
1. 引导登录东方财富（避免限流）
2. 搜索获取股票代码
3. 下钻获取基本面、新闻面、资金面数据
4. 生成综合分析报告

### 示例输出

> 📄 [301362 民爆光电 分析报告（含并购分析）](301362_民爆光电_分析报告_20260305.html) — 包含基本面、新闻面、资金面、技术面四维分析及并购重组专项分析的完整HTML报告示例。

## 核心指标

### 主力净比（资金面核心）

直接从东方财富资金流向页面读取：
- 页面：`https://data.eastmoney.com/zjlx/{股票代码}.html`
- 位置：实时资金流向区域

| 主力净比 | 评级 |
|---------|------|
| > 10% | 🔴 强势介入 |
| 5%-10% | 🟠 明显流入 |
| 0%-5% | 🟡 小幅流入 |
| -5%-0% | 🟢 小幅流出 |
| < -5% | ⚫ 明显流出 |

## 目录结构

```
stock-analyzer-skill/
├── package.json              # npm包配置
├── bin/
│   └── install.js            # 安装脚本
├── skill/                    # Skill源文件（标准结构）
│   ├── SKILL.md              # 主skill定义（必需）
│   ├── scripts/              # 可执行脚本
│   │   ├── fetch_stock.py    # Selenium股票数据抓取工具
│   │   └── requirements.txt  # Python依赖
│   ├── references/           # 参考文档
│   │   └── eastmoney_guide.md
│   └── assets/               # 输出资源（模板等）
│       ├── report_template.md
│       └── report_template.html
├── README.md
└── LICENSE
```

### Skill 标准目录说明

| 目录 | 用途 | 说明 |
|------|------|------|
| `scripts/` | 可执行脚本 | 需要确定性执行的代码，如数据抓取 |
| `references/` | 参考文档 | Claude 按需加载的详细文档 |
| `assets/` | 输出资源 | 模板、图片等用于生成输出的文件 |

## 注意事项

- ⏱️ 每次请求东方财富延迟1秒，避免限流
- 🔐 建议先登录东方财富获取完整数据
- ⚠️ 本工具仅供参考，不构成投资建议

## License

GNU General Public License v3.0

## 免责声明

本工具仅供学习和参考，不构成任何投资建议。股市有风险，投资需谨慎。使用者应自行承担投资风险。
