# 项目交接说明：nyc-mobility-demand-analytics

> 审计日期：2026-06-22。本文基于当前本地仓库、已生成的结果表/图表和代码文件；不将样本结果描述为全市生产结论。

## 1. Project Overview

项目名称为“纽约拥堵收费冲击下的网约车运营策略推荐系统”。业务场景是将 2025-01-05 NYC Congestion Pricing 作为外部政策冲击，基于 NYC TLC 出行数据分析区域需求、OD 流向、乘客价格、司机收益与接驾响应效率的变化。当前目标是从真实公开订单的有界样本中生成可审阅的运营试点候选，而不是做普通出租车 EDA 或单纯订单预测。

## 2. Business Problem

当前项目试图回答：收费核心区需求是否相对变化；需求是否向外溢区转移；单位里程票价和政策费用负担如何变化；司机每分钟收益是否受压；机场路线是否需要专项动作；以及哪些区域/路线应进入运力调度、司机激励、乘客优惠或低价值供给控制的试点池。策略输出不是自动投放指令，必须结合线上实验验证。

## 3. Data Sources and Fields

### High Volume FHV Trip Data

- **实际用于当前报告主链路：是。** 原始文件位于 `data/raw/nyc_tlc/fhvhv/`，存在 2024-01 至 2025-12 的 24 个月 Parquet。
- 当前 sample run 读取 2024-11、2024-12、2025-01、2025-02、2025-03 五个月，每月按多 row-group 抽取上限 60,000 行；最终清洗有效行程为 **299,918**。
- 实际保留并使用：`request_datetime`、`on_scene_datetime`、`pickup_datetime`、`dropoff_datetime`、`PULocationID`、`DOLocationID`、`trip_miles`、`base_passenger_fare`、`tolls`、`tips`、`congestion_surcharge`、`cbd_congestion_fee`、`airport_fee`、`driver_pay`。
- 原始文件虽含 `hvfhs_license_num`、`dispatching_base_num`、`originating_base_num`、`sales_tax`、拼车/无障碍标记，但当前政策报告主链路**没有保留或分析**这些字段。
- `trip_time` 由上下车时间差重算；`response_time_min` 为 request 到 on-scene 的公开数据代理，不能当成真实用户等待时长。

### Yellow Taxi Trip Data

- **原始文件存在：是。** `data/raw/nyc_tlc/yellow/` 有 2024-01 至 2025-10 的 22 个月 Parquet。
- **当前报告主链路实际使用：否。** `clean_yellow_taxi.py` 与 `normalize_yellow()` 存在，但 `src/etl/run_etl_pipeline.py` 只调用 HVFHV 清洗。
- Yellow 的时间、区域、距离、`fare_amount`、`tolls_amount`、`total_amount`、`congestion_surcharge`、`cbd_congestion_fee`、`Airport_fee`可用于后续市场参照；它没有 `driver_pay`，不能用于司机收益结论。

### Taxi Zone Lookup

- **实际使用：是。** 路径为 `data/raw/nyc_tlc/taxi_zone_lookup.csv`。
- 使用字段：`LocationID`、`Borough`、`Zone`、`service_zone`。
- 用途：将上下车 ID 映射为区域/行政区，依据 `config/policy_zones.yaml` 的区域名称列表定义收费核心区、外溢区、对照区和机场路线。

## 4. Current Project File Structure

```text
config/
  analysis_config.yaml            # sample 行数、关键路径和报告说明
  policy_zones.yaml               # 政策日期及 treated/spillover/control/airport 名称配置
  data_paths.yaml / model_config.yaml / quality_rules.yaml / project.yaml
data/raw/nyc_tlc/                 # 本地原始 TLC Parquet 与 Zone Lookup，未提交 GitHub
data/processed/                   # 清洗样本、政策特征、zone-hour 与 OD-hour 面板
data/outputs/                     # 反事实预测与策略推荐结果，默认被 .gitignore 忽略
demo_data/                        # 云端看板用的轻量副本
src/etl/                          # 清洗、特征、面板构建、sample ETL 与 Spark 入口
src/analysis/                     # 需求/时段/OD/价格/司机/机场/响应/因果分析
src/models/                       # 反事实模型、策略推荐与旧版模型脚本
src/reports/                      # 自动 Markdown 报告生成器
src/warehouse/                    # Hive 与 PostgreSQL schema/加载代码
reports/tables/                   # 本次 sample 的 CSV 结果
reports/figures/                  # 本次 sample 的 PNG 图表
notebooks/README.md               # 只有说明文件；无可执行 notebook
```

## 5. Code Written or Modified

| 文件 | Purpose / Inputs / Outputs | 当前状态与备注 |
| --- | --- | --- |
| `src/etl/build_crz_features.py` | 政策区域特征；输入清洗行程和 Zone/config；输出 `trip_policy_features.parquet` | Completed；支持 `--sample`，但一键 ETL 直接调用共享函数。 |
| `src/etl/build_zone_hour_panel.py` | 聚合区域-日期-小时面板 | Completed；默认读取政策特征。 |
| `src/etl/build_od_policy_panel.py` | 聚合 OD-日期-小时面板 | Completed。 |
| `src/etl/policy_data.py` | HVFHV/Yellow 字段标准化、区域映射、价格/司机/响应效率特征与两类面板 | Completed；当前主跑 HVFHV。 |
| `src/etl/run_etl_pipeline.py` | sample HVFHV 原始数据到两类面板与质量表 | Completed；只跑 HVFHV，不合并 Yellow。 |
| `src/analysis/demand_shift_analysis.py` | 区域组需求变化；输出需求表和每日/区域组图 | Completed，已运行。 |
| `src/analysis/temporal_pattern_analysis.py` | 小时、时段和工作日/周末需求模式 | Completed，已运行。 |
| `src/analysis/od_flow_analysis.py` | OD 前后变化与路线类别 | Completed，已运行。 |
| `src/analysis/pricing_pressure_analysis.py` | 距离分段的每英里票价和政策费用负担 | Completed，已运行。 |
| `src/analysis/driver_pressure_analysis.py` | OD 司机每分钟收益、通行费与压力评分 | Completed，已运行。 |
| `src/analysis/airport_route_analysis.py` | 机场到核心区/其他区的需求、收益、响应代理 | Completed，已运行。 |
| `src/analysis/response_time_analysis.py` | 区域组×时段 P50/P90/慢响应代理 | Completed，已运行。 |
| `src/analysis/did_policy_impact.py` | zone/hour/weekday 固定效应 DiD | Completed，已运行；目前 5 个因变量，不含 response P90。 |
| `src/analysis/event_study_congestion.py` | 周度事件研究 | Completed，已运行；当前输出 42 行。 |
| `src/models/counterfactual_demand_baseline.py` | HistGradientBoosting 预政策需求基线 | Completed，已运行；使用日历与滞后特征。 |
| `src/models/operation_strategy_recommender.py` | 基于需求缺口、价格/司机/外溢/响应代理生成策略 | Completed，已运行；规则型而非优化器。 |
| `src/reports/generate_business_report.py` | 读取 CSV 自动生成 `business_analysis_report.md` | Completed，已运行；部分章节仍为通用解释而非逐表逐数值叙述。 |
| `src/run_full_analysis.py` | 通过 subprocess 顺序运行 ETL、分析、模型和报告 | Partially verified：组成模块已逐个跑通；未在本次审计中以该单一命令完整重跑。 |
| `src/models/policy_simulation.py`、`train_demand_baseline.py`、`src/analysis/build_metrics.py`、`write_project_report.py` | 旧版/辅助脚本 | 存在但不在当前 `run_full_analysis.py` 主链路；需后续梳理或标记为 legacy。 |

## 6. Analysis Completed

### 数据质量检查
- **问题：** sample 清洗后是否保留合理行程。
- **输入：** 五个月 HVFHV 有界样本。
- **指标/输出：** `data_quality_summary.csv`；raw_count、valid_count、dropped_count、drop_rate。
- **当前结果：** 300,000 个抽样输入名额中 299,918 有效，82 条被排除，drop_rate=0.0273%。
- **限制：** `raw_count` 是配置的抽样上限，不是所有原始 Parquet 的全量行数；原因未按字段拆分。

### 整体需求、时间规律与 OD 流向
- **问题：** 不同区域/时段/路线是否出现不同的前后变化。
- **输入：** `trip_policy_features.parquet`（真实 HVFHV 有界样本）。
- **输出：** `demand_shift_summary.csv`、`hourly_demand_pattern.csv`、`time_window_summary.csv`、`od_flow_change.csv`、`top_od_pairs.csv` 及对应图。
- **限制：** 五个月样本前期两月、后期三月，且是按文件有界抽样；直接 pre/post 计数不应解释为因果或城市总量变化。

### 乘客价格、司机收益与机场路线
- **问题：** 价格、政策费用、司机收益和机场服务是否存在压力。
- **输出：** `pricing_pressure_summary.csv`、`driver_pressure_summary.csv`、`airport_route_analysis.csv` 和对应图。
- **限制：** 司机压力评分是当前样本内标准化规则；不是补贴金额或 ROI 模型。较早月份缺少 CBD 收费字段时按 0 处理，反映字段上线前无该字段，但应做全量时间/政策口径复核。

### 接驾响应效率
- **问题：** 外溢需求出现时供给是否可能未同步迁移。
- **指标：** request→on-scene 的 P50、P90、慢响应占比。
- **输出：** `response_time_analysis.csv`、`response_time_p90_change.png`。
- **限制：** 不是用户端真实等待时间；没有司机在线量、接单时间或取消订单。

### DiD、Event Study、反事实预测与策略推荐
- **DiD：** 输出 5 个指标，使用 treated/control、zone/hour/weekday 固定效应和 HC1 标准误；未使用聚类标准误、天气、节假日或地理多边形处理组。
- **Event Study：** 输出 42 条周度估计和订单/每英里票价图；`event_study_driver_pay.png` **Missing**。
- **反事实：** 预政策训练 HistGradientBoosting；输出 109,506 条 post-policy zone-hour 预测。当前 MAE=0.6862、RMSE=1.2266、平均 post demand gap=-0.0691。
- **策略：** 规则型推荐器生成 12 张卡和 3 类独立 CSV；不是因果优化或线上实验系统。

## 7. Tables Generated

以下均为当前本地真实 HVFHV **有界样本**生成，不是 mock；`data/outputs/` 默认未提交 GitHub，`reports/tables/` 当前关键结果已提交。

| 文件 | 生成脚本 | 行数 / 主要列 | 含义与业务支撑 |
| --- | --- | --- | --- |
| `reports/tables/data_quality_summary.csv` | `run_etl_pipeline.py` | 1；raw/valid/dropped/drop_rate | sample 清洗边界。 |
| `reports/tables/demand_shift_summary.csv` | `demand_shift_analysis.py` | 4；zone_group、pre/post、change_rate | 区域组需求比较。 |
| `reports/tables/hourly_demand_pattern.csv` | `temporal_pattern_analysis.py` | 48；hour、weekend、pre/post | 小时模式。 |
| `reports/tables/time_window_summary.csv` | `temporal_pattern_analysis.py` | 10；time_window、pre/post | 运营时段比较。 |
| `reports/tables/od_flow_change.csv` | `od_flow_analysis.py` | 29,054；OD、orders、价格/收益变化、route_type | 路线经营诊断。 |
| `reports/tables/top_od_pairs.csv` | `od_flow_analysis.py` | 50；OD 前后指标 | 报告的高价值路线摘录。 |
| `reports/tables/pricing_pressure_summary.csv` | `pricing_pressure_analysis.py` | 3；距离段、fare/policy-fee pre/post | 乘客价格压力。 |
| `reports/tables/driver_pressure_summary.csv` | `driver_pressure_analysis.py` | 29,054；司机收益、tolls、pressure score | 司机激励候选。 |
| `reports/tables/airport_route_analysis.csv` | `airport_route_analysis.py` | 6；airport、target_area、订单/收益/响应变化 | 机场专项。 |
| `reports/tables/response_time_analysis.csv` | `response_time_analysis.py` | 20；区域组×时段 P50/P90/慢响应 | 供给响应代理。 |
| `reports/tables/did_results.csv` | `did_policy_impact.py` | 5；coef、SE、P 值、CI | 相对政策影响。 |
| `reports/tables/event_study_results.csv` | `event_study_congestion.py` | 42；week、metric、effect、CI | 动态路径。 |
| `reports/tables/model_metrics.csv` | `counterfactual_demand_baseline.py` | 1；MAE、RMSE、平均 gap | 模型诊断。 |
| `reports/tables/operation_strategy_cards.csv` | `operation_strategy_recommender.py` | 12；类型、目标、证据、动作、优先级 | 试点候选卡。 |
| `data/outputs/counterfactual_predictions.csv` | `counterfactual_demand_baseline.py` | 109,506；zone/date/hour/actual/predicted/gap | 需求缺口。 |
| `data/outputs/driver_supply_reallocation.csv` | recommender | 8；区域、响应/外溢/评分、动作 | 运力重分配候选。 |
| `data/outputs/route_incentive_recommendation.csv` | recommender | 6；OD、收益/通行费/评分、动作 | 司机激励候选。 |
| `data/outputs/passenger_discount_recommendation.csv` | recommender | 8；区域、需求缺口/价格压力/动作 | 乘客优惠候选。 |
| `data/outputs/operation_strategy_cards.json` | recommender | 12；strategy_id/type/target/evidence/action/priority/confidence | 看板与策略交接。 |
| `data/outputs/did_results.json` | DiD | 5；同 DiD CSV | JSON 版本。 |

**Missing：** `data/outputs/airport_route_strategy.csv` 与 `data/outputs/reduce_low_value_supply.csv` 不存在。机场与低价值供给策略仅存在于 `operation_strategy_cards.json/csv` 中，没有独立导出文件。

## 8. Figures Generated

所有 PNG 来自当前 HVFHV 有界样本；字体已配置中文字体。

| 图表 | 生成脚本 | 说明 / 报告章节 |
| --- | --- | --- |
| `daily_order_trend.png` | demand shift | 政策前后样本每日订单；第 6 节。 |
| `zone_group_demand_change.png` | demand shift | 区域组变化率；第 6 节。 |
| `hourly_demand_pattern.png` | temporal | 小时订单模式；第 7 节。 |
| `top_od_flow_change.png` | OD | OD 前后订单差；第 8 节。 |
| `fare_per_mile_change.png` | pricing | 短中长途每英里票价相对变化率；第 9 节。 |
| `policy_fee_burden_change.png` | pricing | 政策费用负担相对变化率；第 9 节。 |
| `driver_pay_per_minute_change.png` | driver | 路线司机每分钟收入变化分布；第 10 节。 |
| `driver_pressure_score_top_routes.png` | driver | 压力评分最高路线；第 10 节。 |
| `airport_route_change.png` | airport | 机场路线订单变化；第 11 节。 |
| `response_time_p90_change.png` | response | 区域组 P90 接驾响应代理前后并排对比；第 12 节。 |
| `did_summary.png` | DiD | 5 个 DiD 系数与区间；第 13 节。 |
| `event_study_order_count.png`、`event_study_fare_per_mile.png` | event study | 周度动态估计；第 14 节。 |
| `counterfactual_vs_actual.png` | counterfactual | 实际与无政策需求基线；第 15 节。 |
| `spillover_heatmap.png`、`fare_driver_pay_comparison.png`、`heterogeneity_by_hour.png`、`heterogeneity_by_zone_group.png` | 旧/补充模块 | 可作为补充诊断，不是新报告主要章节唯一图。 |

**Missing：** `event_study_driver_pay.png` 未生成；规范要求的该图目前未实现。

## 9. Current Business Findings

1. **区域组 pre/post 样本订单均增长。** 证据：treated +40.0%、spillover +37.4%、control +31.5%、other +36.1%。业务含义：不能据此声称“核心区需求下降”或已发生外溢，因为样本前后月份数量不同且抽样绝对量不可直接比较。行动：只将该表作为描述性检查，政策结论以 DiD/事件研究和完整窗口复核。置信度：低。
2. **每英里票价在三个距离段均小幅下降，但政策费用负担上升。** 证据：短途 fare/mile -2.8%、中途 -1.8%、长途 -1.2%；政策费负担分别 +46.2%、+58.8%、+56.1%。业务含义：固定政策费用的相对负担上升不必然转化为更高基础每英里票价。行动：不要仅凭基础票价决定优惠，应结合需求缺口。置信度：低到中，受 sample 设计影响。
3. **DiD 未支持核心区相对订单变化。** 证据：`log_order_count` 系数 0.00885，P=0.3247，95% CI [-0.00876, 0.02646]。业务含义：当前样本与对照配置下，没有显著证据证明核心区相对订单发生变化。行动：不应依据该结果大规模迁移供给。置信度：中等的方法执行、低的外推性。
4. **DiD 显示价格/司机单位时间指标存在负向相对变化。** 证据：`avg_fare_per_mile` -0.5793，P=0.0112；`avg_driver_pay_per_minute` -0.0193，P=0.0164。业务含义：应进一步检查路线层异质性，而不是简单推断所有司机受损。行动：将路线级结果作为小流量激励筛选输入。置信度：中低，未聚类标准误且未加入外部控制。
5. **外溢区早高峰存在一个响应重分配信号。** 证据：外溢区早高峰 P90 从 6.12 分钟到 6.50 分钟，`supply_reallocation_signal=True`。业务含义：可能存在供给未及时随需求迁移。行动：只适合预部署试点与监控，不能视为真实 SLA 恶化。置信度：低到中。
6. **策略结果以低优先级为主。** 证据：12 张策略卡中仅一条乘客优惠为 Medium，其余为 Low，且置信度均为 Low。业务含义：当前样本没有足够强证据支持大规模投放。行动：保留策略输出作为候选池。置信度：低。

## 10. Operation Strategy Outputs

| 类型 | 是否生成 | 输入证据与规则 | 当前实例/价值 | 限制 |
| --- | --- | --- | --- | --- |
| `driver_supply_reallocation` | 是，3 张卡/8 行清单 | spillover、需求缺口、响应 P90/慢响应、综合评分 | Long Island City/Queens Plaza 等候选 | 未使用真实在线司机或等待时间。 |
| `route_level_driver_incentive` | 是，2 张卡/6 行清单 | 高价值/机场 OD、通行费与司机收益压力 | Van Cortlandt Village 等候选 | 不含补贴成本、接单率或 ROI。 |
| `passenger_discount` | 是，2 张卡/8 行清单 | 正需求缺口、价格压力、司机收益 | Green-Wood Cemetery 等候选 | 当前 price 结果未显示 fare/mile 上升，规则/口径需复核。 |
| `airport_route_strategy` | 是，1 张卡；无独立 CSV | 机场 OD、司机压力、订单 | LaGuardia Airport → Ridgewood | 独立 `airport_route_strategy.csv` Missing。 |
| `boundary_zone_strategy` | 是，2 张卡 | 外溢评分、订单、响应代理 | LIC、Astoria | 基于名称代理而非 CRZ 多边形。 |
| `reduce_low_value_supply` | 是，2 张卡；无独立 CSV | other 区、司机收益变差、低综合分 | Governors Island、Maspeth | 独立 `reduce_low_value_supply.csv` Missing。 |

策略卡字段已包含 `strategy_id`、类型、目标区域/OD、时段、问题、结构化证据、动作、预期影响、评分、优先级、置信度与生成时间。规则不是纯硬编码文本，但阈值和归一化是启发式的。

## 11. Report Status

| 文件 | 当前状态 | 内容与数字来源 | 是否需改进 |
| --- | --- | --- | --- |
| `reports/business_analysis_report.md` | 已生成 | 20 节中文报告；读取 demand/DiD/model/策略等 CSV 的部分真实数值 | 是：多数专题仍为通用文字，需增加每张表的精确结果与图表解释。 |
| `reports/business_summary.md` | 已存在 | 中文业务总结，包含数据边界和策略方向 | 是：未随最新报告模块逐项自动更新。 |
| `README.md` | 已存在 | 中文项目说明、运行命令、看板/报告说明 | 是：当前文字仍有“Yellow 补充参照”表述，需明确当前主跑未用 Yellow。 |

## 12. How to Run the Project

```bash
# 轻量展示和报告分析依赖
pip install -r requirements.txt

# 完整本地 ETL/数仓环境再安装
pip install -r requirements-full.txt

# 已验证的分步骤 sample 流程
python src/etl/run_etl_pipeline.py --sample --rows-per-file 60000
python src/analysis/demand_shift_analysis.py --sample
python src/analysis/temporal_pattern_analysis.py --sample
python src/analysis/od_flow_analysis.py --sample
python src/analysis/pricing_pressure_analysis.py --sample
python src/analysis/driver_pressure_analysis.py --sample
python src/analysis/airport_route_analysis.py --sample
python src/analysis/response_time_analysis.py --sample
python src/analysis/did_policy_impact.py --sample
python src/analysis/event_study_congestion.py --sample
python src/analysis/spillover_analysis.py --sample
python src/analysis/pricing_driver_impact.py --sample
python src/analysis/heterogeneity_analysis.py --sample
python src/models/counterfactual_demand_baseline.py --sample
python src/models/operation_strategy_recommender.py --sample
python src/reports/generate_business_report.py --sample

# 封装入口（组件已验证；本次审计未以此单条命令完整复跑）
python src/run_full_analysis.py --config config/analysis_config.yaml --sample
```

`src/reports/generate_business_report.py` 当前只支持 `--output` 和 `--sample`，不支持规范示例中的 `--config`；各专题脚本也主要使用 `--input`/`--sample`，不统一读取 `analysis_config.yaml`。

## 13. Current Limitations

- 结果来自真实公开 HVFHV 有界样本，不是 mock；但不是全量数据，也不是完整生产政策窗口。
- 当前 sample 的 pre/post 覆盖月份不对称（2024-11/12 vs 2025-01/02/03），描述性前后计数存在时间覆盖偏差。
- Yellow Taxi 原始数据和代码存在，但当前报告链路未使用，README 的“补充参照”并未落实为分析结果。
- 原始 HVFHV 中的基地、平台、拼车、无障碍、sales tax 等字段目前未用于报告。
- 区域组是 YAML 名称列表代理，不是官方拥堵收费区地理多边形。
- 数据质量表仅有总量一行，未按异常原因给出真实剔除明细。
- DiD 使用简化固定效应与 HC1 标准误，未做区域聚类、天气/节假日/地铁扰动控制、placebo 或敏感性分析；未覆盖响应 P90 因变量。
- 事件研究缺少 `event_study_driver_pay.png`；策略推荐缺少独立机场和低价值供给 CSV。
- 策略规则有真实计算输入，但评分、阈值、优先级与置信度是启发式；不含成本、预算、司机供给、取消、履约或 ROI。
- 报告只部分自动引用真实数值；多处仍是通用叙述。
- `reports/figures/` 已修正中文字体，但 GitHub/浏览器可能展示旧缓存，最新图表应以最新 commit 的 blob 为准。

## 14. What Needs to Be Improved Next

1. **Priority 1：先修分析可信度。** 用同长度政策前后窗口、完整 HVFHV Spark 路径，加入天气/节假日/地铁扰动，按 zone 聚类标准误，并用 CRZ 多边形替换名称列表。
2. **Priority 2：让 Yellow 真正进入参照分析，或从 README 与报告中移除“已使用 Yellow 参照”的暗示。** 同时补充数据质量原因明细、event-study driver-pay、response P90 DiD。
3. **Priority 3：完善策略输出。** 单独生成机场/低价值供给 CSV；使策略直接读取报告专题表；明确阈值；加入预算、补贴成本、供给、接单/取消率后再谈 ROI。
4. **Priority 4：增强报告自动化。** 为每个章节读取对应表中的最新数值、显著性和样本量，减少通用模板段落。
5. **Priority 5：Streamlit 暂后置。** 在报告、结果表和策略规则口径稳定前，不应继续扩展前端功能。

## 15. Summary for ChatGPT

当前仓库已有真实 TLC 本地原始数据（HVFHV 24 个月、Yellow 22 个月、Zone Lookup），当前主报告实际运行的是 2024-11 至 2025-03 的 299,918 条 HVFHV 有界样本。已构建清洗特征、zone-hour/OD-hour 面板，生成数据质量、需求、时段、OD、价格、司机压力、机场、响应效率、DiD、事件研究、反事实预测和策略推荐结果；报告表约 14 个核心文件、图表至少 14 个核心文件，另有历史补充表/图。核心代码包含 ETL、7 个报告专题模块、DiD/Event Study、HistGradientBoosting 反事实模型、规则型推荐器、自动 Markdown 报告和一键入口。

所有当前结果是**真实公开订单的有界样本结果，不是 mock**；但它们不是全量生产结论。最大缺口是样本前后窗口不对称、Yellow 未接入主分析、因果识别简化、策略缺少成本/供给/线上实验数据、报告自动化不完整。下一轮 prompt 应优先要求：统一全量/对称窗口数据口径、补齐 Yellow 对照或删去其承诺、增强 DiD/Event Study、完善策略独立输出与依据、让报告逐表自动写出真实结论；暂不优先改 Streamlit。
