# 数据来源说明

本项目使用纽约市出租车和豪华轿车委员会发布的官方出行记录。

- 官方页面：[NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- 原始格式：按月发布的 Parquet 文件
- 本地原始数据目录：`data/raw/nyc_tlc/`

## 已下载的本地数据范围

| 服务类型 | 月份范围 | 文件数 | 体量 |
| --- | --- | ---: | ---: |
| Yellow Taxi | 2024-01 至 2025-10 | 22 | 约 1.28 GB |
| High Volume FHV | 2024-01 至 2025-12 | 24 | 约 10.93 GB |

主分析以 High Volume FHV 为主，因为它同时保留乘客基础票价、过路费、小费和司机收入字段，可支持“价格压力是否传导给司机”的路线级分析。Yellow Taxi 用于补充城市出行观察。

原始数据不会提交到 GitHub。可使用 `scripts/download_nyc_tlc.py` 重新下载，或按官方月度链接重建本地数据集。
