# 数据源审计报告

## 一、系统配置中的数据源（.env + 页面）

`.env` 中：
```
PRIMARY_DATA_SOURCE=eastmoney
FALLBACK_DATA_SOURCE=sina
```

数据源管理页面显示：
- 注册源：tdx_local, eastmoney, sina, baostock, web_scrape
- 可通过 `POST /config/datasource/switch` 切换 `_active_name`

## 二、DataSourceManager 注册（fallback.py）

```python
self._primary_name = "eastmoney"   # 硬编码，未读 .env
self._fallback_name = "sina"       # 硬编码，未读 .env
self._active_name = "eastmoney"    # 硬编码，未读 .env
```

`.env` 中的 `PRIMARY_DATA_SOURCE` / `FALLBACK_DATA_SOURCE` **仅用于 API 返回显示**，未真正影响数据源注册。

## 三、各模块数据源实际使用

| 模块 | 通过 DataSourceManager | 直接绕过 |
|------|----------------------|---------|
| Market(行情) | 批量/单只行情 `dsm.get_quotes()`, K线 `dsm.get_kline()` | AkShare 全市场快照/板块涨跌/北向/涨跌停数/year futures; httpx 新浪/东方财富新闻/外围市场 |
| Selection(选股) | 仅 `fill_names()` 查股票名用 `dsm.get_quotes()` | TDX day 文件；akshare 财报/ST/停牌；httpx 东方财富股票列表 |
| Warning(预警) | 监控池行情 `dsm.get_quotes()` | — |
| Dashboard(仪表盘) | — | 直接调 market/warning API，间接依赖 |
| Analysis(分析) | — | 不直接调数据源，从 market/warning API 取已聚合数据 |

## 四、问题总结

1. **`.env` 设置无效**：PRIMARY_DATA_SOURCE/FALLBACK_DATA_SOURCE 仅在 API 返回字段中显示，从未注入 `DataSourceManager`
2. **硬编码**：`register_default_sources()` 行 194-196 硬编码 primary=eastmoney, fallback=sina
3. **多处直调**：market.py 用 akshare/httpx 直取数据约 8 处，selection.py 约 5 处，不经过 DataSourceManager
4. **切换只管一半**：`switch` 切换后仅影响通过 dsm.get_quotes/get_kline 获取的数据，akshare/httpx 直调用不受影响
