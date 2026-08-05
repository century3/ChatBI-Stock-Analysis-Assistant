# ChatBI Stock Analysis Assistant

基于 Qwen-Agent 的 ChatBI 股票查询与分析助手：自然语言问数、SQL 可视化、ARIMA 预测、MACD / 布林带 / Prophet 技术分析。支持 A 股与美股。

## 功能

- 股票历史行情查询（SQLite + ExcSql 自动出图）
- ARIMA 未来 N 日收盘价预测
- MACD / 布林带 / Prophet 周期性分析
- 行情自动增量更新（akshare / tushare）
- A 股：贵州茅台、五粮液、国泰君安、中芯国际
- 美股：COHR、IPSC、GOOG、NVDA（裸代码或 `*.US`）

## 快速开始

```bash
pip install -r requirements.txt
# 可选：更新行情到今天
python get_stock_data.py --source akshare
# 启动助手 Web UI
python stock_analysis_assistant-6.py
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | 通义千问 / DashScope API Key（必填） |
| `TAVILY_API_KEY` | Tavily 联网搜索（可选） |
| `TUSHARE_TOKEN` | 使用 tushare 数据源时需要（可选，默认 akshare） |

## 主要文件

- `stock_analysis_assistant-6.py`：助手入口（最新版）
- `get_stock_data.py`：行情拉取与 `stock_data.db` 更新
- `boll_detection.py` / `prophet_analysis.py`：技术分析工具
- `requirements.txt`：依赖
- `faq.txt`：助手 FAQ 上下文

## 示例问法

- 查询贵州茅台最近一个月的股价走势
- 预测美股 COHR / NVDA 未来 5 天的收盘价
- 对比 NVDA 和 GOOG 最近一年的涨跌幅
- 使用 MACD 分析贵州茅台过去一年的买卖点

## License

MIT
