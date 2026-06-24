# NYC Ride-hailing Operation Analysis with PySpark, Hive and Machine Learning

中文名：**基于 PySpark、Hive 与机器学习的 NYC 网约车运营数据分析报告**。

这是一个围绕 NYC TLC High Volume FHV 公开行程数据构建的报告型项目。它将 2025 年拥堵收费作为业务背景，依次完成 Parquet 清洗、Hive-compatible 数仓建模、统一指标导出、运营分析、区域小时需求预测、DiD/Event Study 补充验证和运营建议输出。

```text
原始 Parquet → DWD 清洗明细 → DWS 指标表 → 运营分析 / 预测 / 政策验证 → Markdown 报告
```

## Project Overview

项目关注网约车平台在政策变化后需要回答的实际问题：核心区和边界区的需求如何变化？哪些 OD 路线是核心场景？乘客单位里程价格与司机单位时间收益是否同步？哪些区域在高需求时可能出现接驾响应压力？区域小时预测能否辅助高峰前的供给判断？

当前主链路只使用 **High Volume FHV**，因为它同时包含乘客基础票价与 `driver_pay`。Yellow Taxi 数据不作为当前主分析或对照结论的一部分。

## Business Problem

- 时间需求：识别日、小时、工作日/周末的需求规律。
- 区域与 OD：定位热门上车区、高频路线和可能需要重点保障的场景。
- 价格与司机收益：按距离段、时段和政策期比较票价、通行费与司机单位收益。
- 响应代理：基于 `on_scene_datetime - request_datetime` 识别可能的供给滞后；该指标不是用户端真实等待时长。
- 预测与政策验证：用区域小时需求预测辅助调度，用 DiD/Event Study 作为政策变化方向的补充判断。

## Data Sources

| 数据 | 核心字段 | 用途 |
| --- | --- | --- |
| NYC TLC High Volume FHV | 时间、PULocationID/DOLocationID、里程、基础票价、通行费、拥堵收费、司机收入 | 需求、OD、价格、司机收益、响应代理和预测 |
| Taxi Zone Lookup | LocationID、Borough、Zone、service_zone | 区域映射、行政区和机场识别 |

本地样本模式读取政策窗口内的真实 Parquet 有界样本，不生成伪造订单数据。它用于验证工程和展示方法，不应表述为全市全量生产结论。

## Technology Stack

- Python、Pandas、NumPy、PyArrow
- PySpark：完整 Parquet 清洗与数仓路径依赖
- Hive、Hive SQL：ODS/DWD/DWS 分层与统一指标口径
- Matplotlib：PNG 分析图表
- Scikit-learn：随机森林区域小时需求预测 baseline
- XGBoost：区域小时需求预测优化模型
- statsmodels：DiD
- Event Study：周度动态相对变化
- YAML、Git/GitHub：配置与版本管理

## Warehouse Design

```text
ODS: ods_hvfhv_trip_raw, ods_taxi_zone_lookup
  ↓
DWD: dwd_hvfhv_trip_clean
  ↓
DWS: time_demand / zone_demand / od_route / price_driver / response
```

Hive-compatible DDL 与 SQL 位于 [sql/hive](sql/hive)。本地没有 Hive 集群时，`run_hive_sql_exports.py` 用 Pandas 生成与 SQL 对齐的指标 CSV；这不是对真实 Hive 服务连接的宣称。

## Analysis Modules

| 模块 | 主要输出 |
| --- | --- |
| 时间需求 | `time_demand_metrics.csv`、每日/小时/星期订单图 |
| 区域需求 | `zone_demand_metrics.csv`、热门上车/下车区 |
| OD 路线 | `od_route_metrics.csv`、高频 OD 路线 |
| 价格与司机收益 | `price_driver_metrics.csv`、距离段与时段比较 |
| 响应代理 | `response_metrics.csv`、小时响应图 |

## Machine Learning Module

模型以 `zone_id + date + hour` 为粒度预测 `order_count`。特征包括时间、区域、价格/司机收益/响应代理和 1 小时、24 小时、7 天滞后特征。

- 已完成随机森林 baseline 与 XGBoost 两类区域小时需求预测模型训练，并统一输出模型指标、特征重要性和逐区域逐小时预测结果。
- 随机森林用于建立可解释的基线，XGBoost 用于捕捉表格业务数据中的非线性关系和特征交互。
- 预测输出仅为高峰前调度与异常观察提供参考，不是自动调度指令。

## Causal Analysis Module

DiD 比较配置化核心区与对照区在政策前后的相对变化，因变量包括订单对数、每英里票价、司机每分钟收益和响应代理。Event Study 输出订单、票价与司机收益的周度动态路径。

这些结果没有完整控制天气、节假日、地铁扰动、平台补贴和司机在线量，且处理区目前为配置化区域名称代理。因此它们是政策影响方向的补充证据，不等同于严格因果结论。

## Business Recommendations

最终表 `reports/tables/business_recommendations.csv` 只保留四类可审阅的建议：

1. `driver_supply_reallocation`
2. `route_priority`
3. `driver_incentive`
4. `passenger_discount`

每条建议包含目标区域或路线、证据指标、建议动作、业务价值与置信等级。它们是运营试点候选，不是自动投放系统。

## Project Structure

```text
config/                         # 样本与政策区域配置
data/raw/                       # 本地 TLC 原始数据，不提交 GitHub
data/processed/                 # 清洗明细与区域小时面板
sql/hive/                       # Hive-compatible DDL 与 DWS SQL
src/etl/                        # 原始 Parquet 清洗与政策特征
src/report_analysis/            # 主报告流水线、指标导出、图表与报告
src/models/zone_hour_demand_forecast.py
src/causal/                     # DiD / Event Study 入口
reports/tables/                 # CSV 结果
reports/figures/                # PNG 图表
reports/nyc_hive_ml_ride_hailing_analysis_report.md
```

## How to Run

```bash
# 轻量本地分析
pip install -r requirements.txt

# 完整 PySpark / Hive 工作流依赖
pip install -r requirements-full.txt

# 从真实 HVFHV 有界样本生成全部报告成果
python src/report_analysis/run_report_pipeline.py --sample
```

该命令会依次完成：ETL、DWD 准备、Hive-compatible DWS 指标导出、核心图表、区域小时预测、DiD、Event Study 和 Markdown 报告。

## Generated Outputs

- `reports/tables/time_demand_metrics.csv`
- `reports/tables/zone_demand_metrics.csv`
- `reports/tables/top_pickup_zones.csv`
- `reports/tables/top_dropoff_zones.csv`
- `reports/tables/od_route_metrics.csv`
- `reports/tables/top_od_routes.csv`
- `reports/tables/price_driver_metrics.csv`
- `reports/tables/response_metrics.csv`
- `reports/tables/model_metrics.csv`
- `reports/tables/feature_importance.csv`
- `reports/tables/did_results.csv`
- `reports/tables/event_study_results.csv`
- `reports/tables/business_recommendations.csv`
- `data/outputs/zone_hour_demand_predictions.csv`
- `reports/nyc_hive_ml_ride_hailing_analysis_report.md`

## Limitations

- 当前结果来自真实公开数据的有界样本，非全量生产结论。
- 当前样本窗口并不等同于完整、对称的政策评估窗口。
- 处理区是 YAML 名称配置代理，尚非官方收费区多边形。
- 响应时长是 request→on-scene 代理，不是乘客真实等待或平台 SLA。
- 建议规则不含预算、补贴成本、司机在线供给、取消率和履约数据。

## Future Improvements

- 用 Spark 跑完整且对称的政策窗口，并加入天气、节假日和交通扰动。
- 以真实收费区多边形重建处理组，并采用区域聚类标准误与敏感性检验。
- 将 Hive DDL 接入本地或集群环境，统一 DWS 的增量加载。
- 结合在线司机、取消率、补贴成本和实验数据评估运营建议的 ROI。
