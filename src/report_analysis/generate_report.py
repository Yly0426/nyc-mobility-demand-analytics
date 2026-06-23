"""Generate a concise evidence-based Markdown business analysis report."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.utils.project import REPORTS_DIR, TABLES_DIR


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(TABLES_DIR / name)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--sample", action="store_true"); parser.parse_args()
    quality, time, zones, od, price, response, models, did, event, recs = [_read(x) for x in ["data_quality_summary.csv", "time_demand_metrics.csv", "top_pickup_zones.csv", "top_od_routes.csv", "price_driver_metrics.csv", "response_metrics.csv", "model_metrics.csv", "did_results.csv", "event_study_results.csv", "business_recommendations.csv"]]
    top_zone = zones.iloc[0]; top_od = od.iloc[0]; slow = response.loc[response["p90_response_time_min"].idxmax()]; best = models.sort_values("rmse").iloc[0]
    did_demand = did.loc[did["metric_name"] == "log_order_count"].iloc[0]
    report = f'''# 基于 PySpark、Hive 与机器学习的 NYC 网约车运营数据分析报告

## 1. 项目描述
本报告以 NYC TLC High Volume FHV 公开行程数据为基础，分析 2025 年拥堵收费政策窗口中的订单需求、区域分布、OD 路线、乘客价格、司机收益和接驾响应代理，并将预测与准实验结果转化为可审阅的运营建议。

## 2. 数据来源与字段解释
主数据为 HVFHV 月度 Parquet；区域维表为 Taxi Zone Lookup。样本清洗输入名额为 {int(quality.iloc[0]['raw_count']):,}，有效行程 {int(quality.iloc[0]['valid_count']):,}，剔除率 {quality.iloc[0]['drop_rate']:.2%}。核心字段包括上下车时间、上下车 LocationID、里程、基础票价、通行费、拥堵收费、司机收入和 request→on-scene 响应代理。

## 3. 技术栈与分析流程
PySpark/Hive SQL 提供全量数仓接口与指标口径；本地 sample 通过 Pandas 执行同口径汇总；Scikit-learn 与可选 XGBoost 训练区域小时预测；statsmodels 完成 DiD；Matplotlib 输出 PNG；全部结果沉淀为 CSV 与 Markdown。

## 4. Hive 数仓分层设计
ODS 保存原始 HVFHV 与 Taxi Zone；DWD 保存清洗且补充价格、司机收益、响应和政策特征的行程；DWS 输出时间需求、区域需求、OD、价格司机和响应五类指标。对应 Hive SQL 位于 `sql/hive/`。

## 5. 数据清洗与质量检查
过滤无效地点、非正里程、异常行程时长与无效基础票价；`response_time_min` 仅在合理范围内保留。该指标是公开数据代理，并非用户端真实等待时长。

## 6. 时间需求规律分析
详见 `daily_order_trend.png`、`hourly_order_pattern.png`、`weekday_order_pattern.png`。时间需求表按 date-hour-weekday 汇总，为高峰前供给预部署提供基础输入。

## 7. 区域需求分析
最高上车区域为 **{top_zone['pickup_zone']}**，样本订单 {int(top_zone['pickup_order_count']):,}。区域需求表将订单量、单位里程票价、司机每分钟收益与响应代理并列，避免仅以订单量决定调度。

## 8. OD 路线分析
高频 OD 示例为 **{top_od['pickup_zone']} → {top_od['dropoff_zone']}**，订单 {int(top_od['order_count']):,}。高频路线可用于重点保障；若同时出现司机单位时间收益偏低，则进入激励候选而非直接扩大供给。

## 9. 乘客价格与司机收益分析
`price_driver_metrics.csv` 按距离段、时段与政策期统一口径汇总票价、通行费、CBD 收费及司机收益。其用途是识别价格和司机收益是否同步变化，不能以单一基础票价推断司机侧收益。

## 10. 接驾响应分析
样本中最高 P90 响应代理出现在 **{slow['pickup_zone']}** 的 {int(slow['hour'])} 时，P90 为 {slow['p90_response_time_min']:.2f} 分钟。该结果用于筛选可能需要预部署司机的区域，但不等同于真实 SLA。

## 11. 区域小时级订单需求预测模型
当前最优验证模型为 **{best['model_name']}**，RMSE={best['rmse']:.3f}、MAE={best['mae']:.3f}、R²={best['r2_score']:.3f}。预测结果用于辅助高峰前判断区域供给压力，不直接作为自动调度指令。

## 12. 拥堵收费政策影响验证
### 12.1 Difference-in-Differences
订单对数的 treated×post 系数为 {did_demand['coef_treated_post']:.4f}，P={did_demand['p_value']:.4f}。该模型只提供相对变化的补充验证，未完全控制天气、节假日、地铁扰动与司机在线量。

### 12.2 Event Study
`event_study_results.csv` 输出订单、每英里票价与司机每分钟收益的周度相对变化，配合三张事件研究图检查政策前后路径。

### 12.3 因果分析限制说明
处理区是配置化区域名称代理，非官方收费区多边形；sample 窗口与外部控制有限，因此不将结果写成严格因果结论。

## 13. 业务建议
共输出 {len(recs)} 条候选建议，限定为司机供给重分配、重点路线保障、司机激励和乘客优惠四类。建议表包含目标区域或路线、证据指标、行动、业务价值和置信等级；它是运营试点候选，不是自动策略引擎。

## 14. 数据限制
当前报告使用真实公开数据的有界样本；未接入 Yellow Taxi 对照、实时在线司机、取消率、补贴成本或线上实验数据。完整研究应使用对称窗口全量 Spark 路径，并补充外部控制变量。

## 15. 总结
本项目把 Parquet 数据处理、Hive 指标体系、运营分析、区域小时需求预测和政策影响补充验证串成同一条可复现报告链路。最终价值不在于堆叠模型，而在于把分析发现转成边界清楚、可验证的运营建议。
'''
    output = REPORTS_DIR / "nyc_hive_ml_ride_hailing_analysis_report.md"; output.write_text(report, encoding="utf-8")
    summary = "# NYC 网约车运营数据分析摘要\n\n" + "本项目以真实 HVFHV 有界样本生成 Hive-compatible 指标、区域小时预测、政策验证与四类运营建议。详见 `nyc_hive_ml_ride_hailing_analysis_report.md`。\n"
    (REPORTS_DIR / "nyc_hive_ml_ride_hailing_analysis_summary.md").write_text(summary, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
