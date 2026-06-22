"""Create a Chinese Markdown business report from generated analysis tables."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.utils.project import REPORTS_DIR, TABLES_DIR, ensure_output_dirs


def table(name: str) -> pd.DataFrame:
    """Read a result table or return an empty frame for an unavailable module."""
    path = TABLES_DIR / name
    if not path.exists():
        logging.warning("Report table is missing: %s", path)
        return pd.DataFrame()
    return pd.read_csv(path)


def number(value: object, digits: int = 2) -> str:
    """Format nullable report values without inventing a result."""
    if value is None or pd.isna(value):
        return "暂无可用结果"
    return f"{float(value):.{digits}f}"


def rate(value: object) -> str:
    """Format a nullable proportion."""
    return "暂无可用结果" if value is None or pd.isna(value) else f"{float(value):.1%}"


def first_value(frame: pd.DataFrame, column: str, default: object = None) -> object:
    """Fetch the first value when a table/column exists."""
    return frame.iloc[0][column] if not frame.empty and column in frame else default


def main() -> int:
    """Write the report with calculations pulled from the current result tables."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/business_analysis_report.md")
    parser.add_argument("--sample", action="store_true", help="Label the report as bounded real-data sample mode.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_output_dirs()
    demand, temporal, od = table("demand_shift_summary.csv"), table("time_window_summary.csv"), table("od_flow_change.csv")
    pricing, driver, airport = table("pricing_pressure_summary.csv"), table("driver_pressure_summary.csv"), table("airport_route_analysis.csv")
    response, did, event = table("response_time_analysis.csv"), table("did_results.csv"), table("event_study_results.csv")
    metrics, strategies = table("model_metrics.csv"), table("operation_strategy_cards.csv")
    treated = demand.loc[demand.get("zone_group", pd.Series(dtype=str)).eq("treated_zones")]
    spill = demand.loc[demand.get("zone_group", pd.Series(dtype=str)).eq("spillover_zones")]
    did_demand = did.loc[did.get("metric_name", pd.Series(dtype=str)).eq("log_order_count")]
    top_od = od.iloc[0] if not od.empty else pd.Series(dtype=object)
    top_driver = driver.iloc[0] if not driver.empty else pd.Series(dtype=object)
    top_airport = airport.iloc[0] if not airport.empty else pd.Series(dtype=object)
    response_signal = response.loc[response.get("supply_reallocation_signal", pd.Series(dtype=bool)).astype(bool)] if not response.empty else pd.DataFrame()
    report = f"""# NYC 拥堵收费政策下网约车平台运营策略分析报告

> 报告模式：{'真实 NYC TLC 有界样本演示，不代表全市生产结论。' if args.sample else '本地分析结果。'}

## 1. 项目描述

本项目将 2025-01-05 纽约拥堵收费视为一次外部政策冲击，使用 High Volume FHV 为主分析数据、Yellow Taxi 为补充参照、Taxi Zone Lookup 为区域维表，分析需求、OD 流向、乘客价格、司机收益和接驾响应效率，并输出可进入小流量试点的运营策略。

## 2. 数据来源与字段理解

### 2.1 High Volume FHV 行程表

主表包含请求、到达、上车、下车时间；上下车区域；距离、时长；基础票价、通行费、拥堵收费、小费和 `driver_pay`。它支持从需求到路线、价格、司机收益和服务响应的连续分析。

### 2.2 Yellow Taxi 行程表

Yellow Taxi 作为传统出租车市场的补充参照，包含时间、区域、里程和乘客侧价格，但没有 `driver_pay`，不能用于司机收益结论。

### 2.3 Taxi Zone Lookup 区域维表

该表将 LocationID 映射为行政区和区域名，用于配置收费核心区、外溢区、对照区、机场和 OD 路线。

## 3. 分析目的

核心问题不是“哪里订单多”，而是政策改变成本后，平台应如何调整司机供给、路线激励、乘客优惠和低价值供给控制。

## 4. 数据清洗与质量检查

清洗规则包括无效区域、非正距离、异常时长、异常票价和不合理时间顺序。数据质量汇总见 `reports/tables/data_quality_summary.csv`。响应时长仅在请求和到达现场时间同时存在且时长合理时计算。

## 5. 指标体系设计

需求侧使用订单量、短中长途、机场订单和区域/OD 面板；价格侧使用 `fare_per_mile`、通行费与政策费负担；司机侧使用 `driver_pay_per_minute` 与收入/票价比；服务效率使用响应时长 P50、P90 与慢响应占比。

## 6. 整体需求变化分析

收费核心区订单变化率为 **{rate(first_value(treated, 'change_rate'))}**，外溢区订单变化率为 **{rate(first_value(spill, 'change_rate'))}**。该结果用于判断需求是否可能从核心区向边界区域转移，而不是将全市总量变化直接归因于政策。

![每日订单趋势](figures/daily_order_trend.png)
![区域组订单变化](figures/zone_group_demand_change.png)

## 7. 时间规律分析

时段结果保存在 `hourly_demand_pattern.csv` 与 `time_window_summary.csv`。高峰时段的订单结构决定司机预部署窗口；但 sample 模式下应关注相对结构，不应将抽样绝对订单量解释为城市总量。

![小时需求规律](figures/hourly_demand_pattern.png)

## 8. OD 流向变化分析

当前政策后订单量最高的 OD 路线为 **{top_od.get('pickup_zone_name', '暂无')} → {top_od.get('dropoff_zone_name', '暂无')}**。OD 表同时保留票价和司机单位时间收入变化，可区分需求下降与司机收益压力。

![OD 流向变化](figures/top_od_flow_change.png)

## 9. 乘客价格压力分析

价格压力表按短、中、长途汇总每英里票价和政策费用负担。只有当价格上升、需求相对承压且司机收益未明显恶化时，才将乘客优惠作为候选策略。

![每英里票价变化](figures/fare_per_mile_change.png)
![政策费用负担变化](figures/policy_fee_burden_change.png)

## 10. 司机收益压力分析

当前司机压力评分最高的路线为 **{top_driver.get('pickup_zone_name', '暂无')} → {top_driver.get('dropoff_zone_name', '暂无')}**，评分为 **{number(top_driver.get('driver_pressure_score'))}**。该评分结合通行费变化和司机每分钟收入变化，用于筛选司机激励候选，而不是直接决定补贴金额。

![司机每分钟收入变化](figures/driver_pay_per_minute_change.png)
![司机压力最高路线](figures/driver_pressure_score_top_routes.png)

## 11. 机场路线策略分析

机场路线首条结果为 **{top_airport.get('airport_name', '暂无')} / {top_airport.get('target_area', '暂无')}**。机场路线客单价和服务体验重要，因此同时查看订单、司机收益和响应时长；满足条件时建议优先派单或司机激励试点。

![机场路线变化](figures/airport_route_change.png)

## 12. 接驾响应效率分析

响应效率基于 `request_datetime → on_scene_datetime` 的公开数据代理，不等于乘客端真实等待时长。当前有 **{len(response_signal)}** 个区域组-时段组合触发供给重分配信号，含义是外溢区的 P90 响应时长在政策后变慢，值得先通过预部署司机验证。

![P90 响应时长变化](figures/response_time_p90_change.png)

## 13. Difference-in-Differences 政策影响分析

`log_order_count` 的处理组×政策后系数为 **{number(first_value(did_demand, 'coef_treated_post'), 4)}**，P 值为 **{number(first_value(did_demand, 'p_value'), 4)}**。DiD 依赖对照组与政策前趋势的可信度，不能被解释为绝对因果结论。

![DiD 汇总](figures/did_summary.png)

## 14. Event Study 政策影响路径分析

事件研究当前生成 **{len(event)}** 条周度估计，用于观察政策前是否已出现系统性差异，并追踪政策后影响路径。

![订单事件研究](figures/event_study_order_count.png)
![票价事件研究](figures/event_study_fare_per_mile.png)

## 15. 反事实需求预测模型

模型的政策前样本 MAE 为 **{number(first_value(metrics, 'MAE_pre_policy'))}**，RMSE 为 **{number(first_value(metrics, 'RMSE_pre_policy'))}**。反事实预测是运营辅助工具：它计算实际订单与无政策基线的缺口，但严格政策解释仍以 DiD 和事件研究为主。

![实际与反事实需求](figures/counterfactual_vs_actual.png)

## 16. 运营策略推荐

本次运行生成 **{len(strategies)}** 张策略卡，覆盖司机运力调度、路线级司机激励、乘客优惠、机场专项、边界区策略和低价值供给控制。每张卡均记录目标、时段、问题、证据、预期影响、优先级和置信度。

### 16.1 司机运力调度建议
优先依据外溢评分、政策后订单和响应效率代理，将供给从旧热区向需求承接区预部署。

### 16.2 路线级司机补贴建议
当高价值路线通行费压力上升、司机每分钟收益承压且需求仍存在时，优先进行司机侧小流量激励。

### 16.3 乘客优惠建议
当需求低于反事实基线、乘客价格压力上升且司机收益并未同步承压时，才测试有预算上限的乘客优惠。

### 16.4 机场路线专项策略
机场路线结合需求、司机收益和响应效率设置优先派单或激励，避免与普通城市短途共用规则。

### 16.5 边界外溢区策略
收费区边界附近若出现订单承接和响应变慢，应设置高峰调度热区并按小时复核。

### 16.6 低价值区域供给控制
对订单、司机单位时间收益和外溢信号均弱的区域，下调司机推荐权重以减少无效等待。

## 17. 结论与建议

本项目的最终交付不是预测订单量，而是将需求缺口、价格压力、司机收益压力、通行费压力、区域外溢和响应效率代理转化为可验证的运营试点候选。所有策略均应通过接单率、取消率、空驶时间和履约质量的对照实验决定是否扩大。

## 18. 数据限制与可信度说明

公开 TLC 数据没有在线司机数、用户取消、优惠成本、司机留存和乘客端真实等待时长；收费区也使用透明的区域名称代理。样本结果用于验证工程和分析链路，不能被包装为生产经营结论。

## 19. 后续优化方向

下一步应使用完整 Spark 政策窗口，加入天气、节假日、地铁扰动与地理多边形控制，并把策略清单接入线上小流量实验闭环。

"""
    output = Path(args.output)
    if not output.is_absolute():
        output = Path.cwd() / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    logging.info("Wrote business report to %s", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
