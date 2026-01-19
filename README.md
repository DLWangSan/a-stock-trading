# AStockTrading - A股交易分析系统

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Non--Commercial-red.svg)](LICENSE)

一个专为A股市场设计的股票交易分析系统，基于**TradingAgents多Agent协同架构**，通过多个专业Agent的独立分析和集体辩论，提供全面的交易决策支持。



## 🎯 关于 TradingAgents

本项目采用**TradingAgents多Agent协同分析架构**，这是一种创新的股票分析方法论。系统通过多个专业领域的AI Agent独立分析同一只股票，然后让这些Agent进行"辩论"和协同，最终得出综合判断。

### TradingAgents 核心理念

传统的单一AI模型分析往往存在以下问题：
- 单一视角的局限性
- 模型偏见难以避免
- 分析维度不够全面

TradingAgents通过以下机制解决这些问题：

1. **专业化分工** - 每个Agent专注于特定分析领域（技术分析、资金流、基本面等）
2. **独立判断** - 多个Agent并行独立分析，避免相互影响
3. **集体辩论** - Agent之间进行观点对比和辩论，发现分歧和共识
4. **综合决策** - 基于多Agent的集体智慧生成最终建议

### 系统架构

```
股票数据输入
    ↓
┌─────────────────────────────────┐
│  多个Agent并行独立分析          │
│  • 技术分析Agent                │
│  • 资金流Agent                  │
│  • 基本面Agent                  │
│  • 行业对比Agent                │
│  • 舆情Agent                    │
│  • 日内做T Agent                │
│  • 复盘Agent                    │
└─────────────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Agent辩论与协同                │
│  - 观点对比与分歧识别           │
│  - 共识达成与综合判断           │
└─────────────────────────────────┘
    ↓
综合交易建议输出
```

### Agent 配置

系统默认包含以下Agent（基于TradingAgents论文设计）：

- **技术分析Agent** - 分析K线形态、技术指标、趋势判断
- **资金流Agent** - 分析主力资金动向、资金流向趋势
- **基本面Agent** - 评估估值合理性、财务健康度
- **行业对比Agent** - 分析行业地位、相对表现
- **舆情Agent** - 监控市场情绪、热点事件
- **日内做T Agent** - 提供日内交易建议和价格区间
- **复盘Agent** - 总结当日和近期表现，提炼经验

所有Agent使用相同的Prompt模板（基于TradingAgents论文），并在结尾添加"请用中文输出"的要求。

## ✨ 功能特性

### ✅ 已完成功能

#### 📊 数据获取模块
- [x] 实时行情数据获取（新浪API）
- [x] 多周期K线数据（5分钟、15分钟、30分钟、日线）
- [x] 分时数据（每分钟）
- [x] 资金流向数据（今日、历史、实时分钟线）
- [x] 基本面数据（PE/PB/PS/ROE/EPS等）
- [x] 行业对比数据（排名、平均涨跌幅、头部股票）
- [x] 舆情数据（新闻、股吧热门帖子）

#### 📈 技术指标计算
- [x] 移动平均线（MA5/MA10/MA20/MA30/MA60）
- [x] 指数移动平均线（EMA12/EMA26/EMA50）
- [x] MACD指标
- [x] RSI相对强弱指标
- [x] KDJ随机指标
- [x] 布林带（BOLL）
- [x] OBV能量潮指标

#### 🔧 API接口
- [x] RESTful API设计
- [x] 综合数据接口（含技术指标）
- [x] 格式化数据接口（用于AI分析）
- [x] 舆情数据接口
- [x] CORS跨域支持

### 🚧 计划开发功能

#### 🖥️ 前端界面
- [ ] 现代化Web界面（React + TypeScript）
- [ ] 首页大盘行情展示
- [ ] 自选股管理页面
- [ ] 股票详情页（交互式K线图）
- [ ] 配置页面（AI Key、Agent配置）

#### 🤖 Agent系统
- [ ] Agent配置管理（数据库存储）
- [ ] 多Agent并行分析
- [ ] Agent辩论机制实现
- [ ] 日内做T Agent（价格区间推荐）
- [ ] 复盘Agent（每日复盘总结）

#### 💾 数据管理
- [ ] SQLite数据库集成
- [ ] 自选股管理
- [ ] 分析结果缓存
- [ ] 配置持久化存储

#### 🎨 可视化
- [ ] TradingView风格K线图
- [ ] 技术指标叠加显示
- [ ] 买入卖出价格区间线
- [ ] 资金流向可视化
- [ ] 舆情热力图

#### 🔌 AI集成
- [ ] 多AI服务商支持（OpenAI/DeepSeek/Qwen/Gemini）
- [ ] Agent Prompt管理
- [ ] 分析结果格式化
- [ ] 错误处理和重试机制

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
python api_server.py
```

服务将在 `http://localhost:5000` 启动，访问该地址查看API文档。

## 📖 API文档

### 数据获取API

```bash
# 获取综合数据（含技术指标）
GET /api/sina/comprehensive_with_indicators/<code>

# 获取实时行情
GET /api/sina/realtime/<code>

# 获取资金流向
GET /api/sina/money_flow/<code>

# 获取基本面数据
GET /api/sina/fundamental/<code>

# 获取行业对比
GET /api/sina/industry_comparison/<code>

# 获取舆情数据
GET /api/sentiment/all/<code>?days=7&latest=10&hot=10
```

### 格式化数据API（用于AI分析）

```bash
# 获取格式化的股票数据
GET /api/sina/for_ai_with_indicators/<code>
```

返回包含 `formatted_text`（格式化文本）和 `raw_data`（原始数据）的JSON。

## 🏗️ 项目结构

```
a-stock-trading/
├── api_server.py          # Flask应用入口
├── api_routes.py          # API路由定义
├── data_fetchers.py       # 数据获取模块（新浪+东方财富）
├── technical_indicators.py # 技术指标计算
├── data_formatters.py     # 数据格式化
├── utils.py               # 工具函数
├── test/                  # 测试脚本
└── README.md              # 项目说明
```

## 🔬 技术实现

### 数据源

- **新浪财经API** - 实时行情、K线数据
- **东方财富API** - 资金流向、基本面、舆情数据

### 技术栈

- **Backend**: Flask + SQLAlchemy
- **Database**: SQLite（计划中）
- **AI Integration**: OpenAI/DeepSeek/Qwen/Gemini API（计划中）
- **Data Processing**: Pandas + NumPy

## 📚 相关研究

本项目基于TradingAgents多Agent系统理论，参考了以下研究方向：

- Multi-Agent Systems in Financial Trading
- Ensemble Methods for Stock Prediction
- Debate-based AI Decision Making

## 💬 交流群

欢迎加入我们的交流群，一起讨论A股交易和AI分析技术！

![交流群二维码](image/group_qrcode.png)

## ⚠️ 免责声明

本项目仅供学习和研究使用，不构成任何投资建议。股票交易存在风险，投资需谨慎。

## 📝 License

本项目采用 [Non-Commercial License](LICENSE)，**仅允许用于学习和交流目的，禁止用于任何商业用途**。

## 🙏 致谢

- 数据来源：新浪财经、东方财富
- AI服务：OpenAI、DeepSeek、通义千问、Google Gemini

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=DLWangSan/a-stock-trading&type=Date)](https://star-history.com/#DLWangSan/a-stock-trading&Date)

## 📊 项目统计

![GitHub stars](https://img.shields.io/github/stars/YOUR_USERNAME/a-stock-trading?style=social)
![GitHub forks](https://img.shields.io/github/forks/YOUR_USERNAME/a-stock-trading?style=social)
![GitHub issues](https://img.shields.io/github/issues/YOUR_USERNAME/a-stock-trading)
![GitHub license](https://img.shields.io/github/license/YOUR_USERNAME/a-stock-trading)

