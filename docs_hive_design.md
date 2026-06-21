# Hive 数仓分层设计

Hive 在本项目中承担离线数仓元数据层：管理原始 Parquet、清洗后的分区明细，以及可复用的区域小时和 OD 小时分析宽表。

## 分层说明

| 分层 | 作用 | 示例表 |
| --- | --- | --- |
| ODS | 映射 NYC TLC 官方原始文件 | `ods_fhvhv_trips`、`ods_yellow_trips` |
| DWD | 清洗、统一字段后的出行事实表 | `dwd_clean_trips` |
| DWS | 可复用的区域小时、OD 小时和政策效果宽表 | `dws_zone_hourly_demand`、`dws_od_policy_panel` |
| ADS | 面向看板、模型和策略推荐的轻量结果层 | PostgreSQL 结果表、Streamlit CSV/JSON |

## 链路

```text
NYC TLC 月度 Parquet
    → Hive ODS 外部表
    → PySpark 清洗与政策特征工程
    → Hive DWD 分区明细表
    → Hive DWS 区域小时 / OD 小时聚合表
    → PostgreSQL / 模型训练 / Streamlit 决策看板
```

## 为什么这样划分

- 原始数据本身按月提供 Parquet，适合以 Hive 外部表管理，避免复制大文件。
- DWD 以 `pickup_month` 等字段分区，便于政策窗口和月份级任务重跑。
- DWS 提供区域需求、OD 流向、价格与司机收益等复用指标，避免每个分析脚本重新扫描明细。
- PostgreSQL 不承载全量订单，只保存结果和策略清单，服务看板与小流量试点分析。

这个边界让大规模离线计算与轻量业务展示各自做擅长的事情。
