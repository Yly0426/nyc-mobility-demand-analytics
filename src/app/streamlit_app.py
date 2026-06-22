"""Portfolio-ready Chinese decision product for NYC congestion-pricing analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.project import OUTPUTS_DIR, PROCESSED_DIR, TABLES_DIR


DEMO_DIR = PROJECT_ROOT / "demo_data"
ZONE_GROUPS = {"treated_zones": "收费核心区", "spillover_zones": "需求外溢区", "control_zones": "对照区", "other": "其他区域"}
METRICS = {"log_order_count": "订单量对数", "avg_fare_per_mile": "每英里平均票价", "avg_driver_pay_per_minute": "每分钟司机收入", "airport_trip_count": "机场订单量", "short_trip_count": "短途订单量"}
STRATEGIES = {
    "driver_supply_reallocation": "司机运力重分配",
    "route_level_driver_incentive": "路线级司机激励",
    "passenger_discount": "乘客侧优惠试点",
    "airport_route_strategy": "机场路线专项运营",
    "boundary_zone_strategy": "曼哈顿边界区策略",
    "reduce_low_value_supply": "低价值区域供给控制",
}
PRIORITIES = {"High": "高优先级", "Medium": "中优先级", "Low": "低优先级", "high": "高优先级", "medium": "中优先级", "low": "低优先级"}
WEEKDAYS = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
EVIDENCE_LABELS = {
    "spillover_score": "外溢评分",
    "demand_gap_rate": "需求缺口率",
    "post_policy_average_orders": "政策后平均订单",
    "post_policy_order_count": "政策后订单量",
    "tolls_change_rate": "通行费变化率",
    "driver_pay_per_minute_change_rate": "每分钟司机收入变化率",
    "fare_per_mile_change_rate": "每英里票价变化率",
    "response_time_p90_change_min": "P90 响应时长变化（分钟）",
    "slow_response_rate_change": "慢响应占比变化",
}


def first_existing(*paths: Path) -> Path | None:
    """Return the first local or demo path that is available."""
    return next((path for path in paths if path.exists()), None)


def load_csv(name: str, *, output: bool = False) -> pd.DataFrame:
    """Load a generated CSV first, then the cloud-safe demo equivalent."""
    primary = (OUTPUTS_DIR if output else TABLES_DIR) / name
    path = first_existing(primary, DEMO_DIR / name)
    return pd.read_csv(path) if path else pd.DataFrame()


def load_json(name: str) -> list[dict]:
    """Load structured strategy cards with a demo fallback."""
    path = first_existing(OUTPUTS_DIR / name, DEMO_DIR / name)
    if not path:
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_zone_panel() -> pd.DataFrame:
    """Read the reusable zone-hour panel from full or bundled demo data."""
    path = first_existing(PROCESSED_DIR / "zone_hour_policy_panel.parquet", DEMO_DIR / "zone_hour_policy_panel.parquet")
    data = pd.read_parquet(path) if path else pd.DataFrame()
    if not data.empty:
        data["trip_date"] = pd.to_datetime(data["trip_date"])
    return data


def localized_groups(data: pd.DataFrame, column: str = "zone_group") -> pd.DataFrame:
    """Translate internal policy-group codes for the business interface."""
    result = data.copy()
    if column in result:
        result[column] = result[column].map(ZONE_GROUPS).fillna(result[column])
    return result


def page_header(title: str, subtitle: str) -> None:
    """Use a consistent title and purpose statement on every page."""
    st.subheader(title)
    st.caption(subtitle)


def interpretation(phenomenon: str, meaning: str, action: str) -> None:
    """Put a business reading directly below every chart."""
    st.markdown(
        f"**业务解读**  \\\n+        **现象：** {phenomenon}  \\\n+        **运营含义：** {meaning}  \\\n+        **策略影响：** {action}"
    )


def as_percent(value: float | int | None) -> str:
    """Safely render a rate for narrative text."""
    return "暂无" if value is None or pd.isna(value) else f"{value:.1%}"


def evidence_text(evidence: object) -> str:
    """Render structured evidence as readable Chinese phrases."""
    if isinstance(evidence, str):
        try:
            evidence = json.loads(evidence.replace("'", '"'))
        except json.JSONDecodeError:
            return evidence
    if not isinstance(evidence, dict):
        return "暂无可用证据指标"
    parts = []
    for key, value in evidence.items():
        label = EVIDENCE_LABELS.get(key, key)
        if isinstance(value, float):
            rendered = f"{value:.1%}" if "rate" in key else f"{value:.3f}"
        else:
            rendered = str(value)
        parts.append(f"{label}：{rendered}")
    return "；".join(parts)


st.set_page_config(page_title="纽约拥堵收费下的网约车运营决策", layout="wide")
st.title("纽约拥堵收费下的网约车运营决策")
st.caption("作品集演示：基于 NYC TLC 有界真实订单样本构建。策略结果用于展示分析与试点设计，不等同于生产投放结论。")

zone_panel = load_zone_panel()
did = load_csv("did_results.csv")
events = load_csv("event_study_results.csv")
spillover = load_csv("spillover_zone_ranking.csv")
pricing = load_csv("pricing_driver_impact.csv")
heterogeneity = load_csv("heterogeneity_summary.csv")
predictions = load_csv("counterfactual_predictions.csv", output=True)
cards = pd.DataFrame(load_json("operation_strategy_cards.json"))
supply_actions = load_csv("driver_supply_reallocation.csv", output=True)
route_actions = load_csv("route_incentive_recommendation.csv", output=True)
discount_actions = load_csv("passenger_discount_recommendation.csv", output=True)

if zone_panel.empty:
    st.error("未找到可展示的样本结果。请先运行 sample mode ETL，或确认 demo_data 已随仓库部署。")
    st.stop()

home, pipeline, demand, causal, counterfactual, price, flow, strategy, outputs = st.tabs([
    "首页 / 项目总览", "数据链路", "需求迁移", "因果影响", "反事实预测", "票价与司机影响", "外溢与 OD 流向", "运营策略", "最终成果"
])

date_min, date_max = zone_panel["trip_date"].min(), zone_panel["trip_date"].max()
total_orders = int(zone_panel["order_count"].sum())
zone_count = int(zone_panel["zone_id"].nunique())
top_spillover = spillover.iloc[0] if not spillover.empty else None
did_demand = did.loc[did["metric_name"].eq("log_order_count")].iloc[0] if "metric_name" in did and did["metric_name"].eq("log_order_count").any() else None

with home:
    page_header("把一次政策变化，变成平台可以执行的运营试点", "纽约在 2025-01-05 启动拥堵收费后，本项目从需求、价格、司机收益和 OD 流向中识别应调整的运力与激励策略。")
    st.markdown("### 一句话说明")
    st.write("基于 NYC TLC 2024-2025 出行订单，构建区域小时与 OD 小时面板，用因果分析和反事实预测识别政策冲击，再输出司机调度、路线激励、乘客优惠和低价值供给控制建议。")
    left, right = st.columns(2)
    with left:
        st.markdown("### 业务问题")
        st.write("拥堵收费后，核心区需求、边界区承接、乘客价格和司机收益可能同时变化。平台要决定：司机该去哪里、哪些路线该激励、哪些场景不该继续投入供给。")
    with right:
        st.markdown("### 为什么重要")
        st.write("只看订单总量会错过真正的经营风险：核心区空驶、边界区供给不足、司机拒单和高价值机场路线服务波动。项目把这些风险拆成可检查、可试点的动作。")

    st.markdown("### 数据规模")
    a, b, c, d = st.columns(4)
    a.metric("样本订单量", f"{total_orders:,}")
    b.metric("区域小时观测", f"{len(zone_panel):,}")
    c.metric("覆盖区域", f"{zone_count}")
    d.metric("观察窗口", f"{date_min:%Y-%m-%d} 至 {date_max:%Y-%m-%d}")

    st.markdown("### 分析方法")
    method_columns = st.columns(4)
    method_columns[0].markdown("**区域与 OD 面板**  \\\n+    把订单转成可比较的区域小时和路线小时运营视图。")
    method_columns[1].markdown("**双重差分**  \\\n+    对比收费核心区与对照区的相对变化。")
    method_columns[2].markdown("**事件研究**  \\\n+    检查政策前趋势与政策后影响路径。")
    method_columns[3].markdown("**反事实预测**  \\\n+    估计无政策时的需求基线与需求缺口。")

    st.markdown("### 最终业务产出")
    output_columns = st.columns(4)
    output_columns[0].metric("策略卡", f"{len(cards)} 条")
    output_columns[1].metric("运力重分配建议", f"{len(supply_actions)} 条")
    output_columns[2].metric("路线激励候选", f"{len(route_actions)} 条")
    output_columns[3].metric("乘客优惠候选", f"{len(discount_actions)} 条")

    st.markdown("### 三条关键发现")
    findings = [
        f"收费核心区相对对照区的订单对数估计变化为 {did_demand.coef_treated_post:.3f}，需结合置信区间与前趋势谨慎解读。" if did_demand is not None else "核心区需求变化通过双重差分与事件研究交叉验证，而非简单前后对比。",
        f"{top_spillover.zone_name} 的外溢评分为 {top_spillover.spillover_score:.2f}，是优先监控的需求承接区域。" if top_spillover is not None else "外溢评分用于锁定可能承接核心区转移需求的边界区域。",
        "票价与司机收入按 OD 路线拆分，避免把乘客涨价误判为司机收益同步改善。",
    ]
    for item in findings:
        st.markdown(f"- {item}")
    st.markdown("### 三条业务建议")
    for item in ["对高外溢评分边界区做高峰预部署，避免继续按旧热区配置司机。", "对通行成本上升而司机每分钟收入承压的高价值 OD 路线，优先试点司机侧激励。", "对需求低于反事实基线且乘客价格压力高的场景，采用有预算上限的乘客优惠对照试验。"]:
        st.markdown(f"- {item}")

with pipeline:
    page_header("从原始订单到运营建议的数据链路", "把大规模出行明细加工为可复用的政策分析面板，并将结果沉淀为可浏览、可下载的策略输出。")
    st.markdown("""```text
NYC TLC 原始 Parquet
        ↓
PySpark / Pandas 清洗与字段统一
        ↓
政策区域特征 + 区域小时 / OD 小时面板
        ↓
Hive 分层数仓（ODS / DWD / DWS）→ PostgreSQL 轻量结果层
        ↓
DiD / 事件研究 / 反事实预测 / 规则推荐
        ↓
中文决策看板 + 可下载运营策略清单
```""")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("原始来源", "TLC Yellow + HVFHV")
    p2.metric("处理粒度", "区域-日期-小时 / OD-日期-小时")
    p3.metric("数仓边界", "Hive 放明细，PostgreSQL 放结果")
    p4.metric("面向决策", "六类运营策略")
    st.markdown("### 数据可信度与使用边界")
    st.write("线上版本使用有界真实订单样本，能够完整展示工程和分析链路。TLC 没有平台在线司机数、等待时长、优惠成本与留存数据，因此供给压力和策略效果均需通过后续实验验证。")

with demand:
    page_header("需求迁移：订单结构是否向其他区域移动？", "先观察区域组的订单构成和运营时段，再定位需要进一步检查的高频区域。")
    monthly = localized_groups(zone_panel).copy()
    monthly["月份"] = monthly["trip_date"].dt.strftime("%Y-%m")
    monthly = monthly.groupby(["月份", "zone_group"], as_index=False)["order_count"].sum().rename(columns={"zone_group": "区域分组", "order_count": "订单量"})
    monthly["月度订单占比"] = monthly["订单量"] / monthly.groupby("月份")["订单量"].transform("sum") * 100
    st.plotly_chart(px.bar(monthly, x="月份", y="月度订单占比", color="区域分组", barmode="stack", title="各区域组的月度订单构成（样本占比）", labels={"月度订单占比": "订单占比 (%)"}), use_container_width=True)
    interpretation("图中展示不同区域组在每月样本订单中的结构占比。", "样本绝对量不等于城市总需求，结构变化更适合用于识别迁移方向。", "将结构上升的外溢区纳入司机预部署池，并与实际接驾时长交叉验证。")

    heat = localized_groups(zone_panel).copy()
    heat["运营时段"] = pd.cut(heat["hour"], bins=[-1, 5, 9, 13, 16, 20, 23], labels=["凌晨 0-5", "早高峰 6-9", "上午 10-13", "下午 14-16", "晚高峰 17-20", "夜间 21-23"])
    heat = heat.groupby(["weekday", "运营时段"], observed=False, as_index=False)["order_count"].sum()
    heat["星期"] = heat["weekday"].map(WEEKDAYS)
    matrix = heat.pivot(index="星期", columns="运营时段", values="order_count").reindex(list(WEEKDAYS.values())).fillna(0)
    share = matrix.div(matrix.sum(axis=1), axis=0).fillna(0) * 100
    figure = go.Figure(go.Heatmap(z=share.to_numpy(), x=share.columns, y=share.index, text=share.round(0).to_numpy(), texttemplate="%{text:.0f}%", colorscale=[[0, "#edf5f2"], [0.5, "#58a4b0"], [1, "#114f78"]], xgap=3, ygap=3, colorbar={"title": "占比 (%)"}))
    figure.update_layout(title="星期与运营时段的订单结构", xaxis_title="运营时段", yaxis_title="星期", yaxis={"autorange": "reversed"}, height=430, margin={"l": 55, "r": 35, "t": 55, "b": 70})
    st.plotly_chart(figure, use_container_width=True)
    interpretation("热力图显示一周内各运营时段的订单构成。", "高占比时段是供给紧张和调度优先级更高的候选窗口。", "针对晚高峰或机场到达高峰设置单独的司机预部署与派单规则。")

with causal:
    page_header("因果影响：哪些变化更可能来自拥堵收费？", "用准实验设计区分政策影响与普通季节性、星期效应和区域差异。")
    if not did.empty:
        view = did.copy()
        view["指标"] = view["metric_name"].map(METRICS).fillna(view["metric_name"])
        figure = go.Figure(go.Scatter(x=view["coef_treated_post"], y=view["指标"], mode="markers", marker={"size": 11, "color": "#b34c3e"}, error_x={"type": "data", "array": view["confidence_interval_high"] - view["coef_treated_post"], "arrayminus": view["coef_treated_post"] - view["confidence_interval_low"]}))
        figure.add_vline(x=0, line_color="#6b7280")
        figure.update_layout(title="双重差分估计：收费核心区相对对照区的变化", xaxis_title="政策相对影响", yaxis_title="")
        st.plotly_chart(figure, use_container_width=True)
        interpretation("点为处理组相对对照组的政策后估计，横线为置信区间。", "若置信区间跨过零，不能将该指标的变化当成明确政策效果。", "只把证据较一致的指标用于策略排序，并保留小流量试验作为最终验证。")
        st.dataframe(view[["指标", "coef_treated_post", "p_value", "confidence_interval_low", "confidence_interval_high", "n_observations"]].rename(columns={"coef_treated_post": "政策相对影响", "p_value": "P 值", "confidence_interval_low": "置信区间下限", "confidence_interval_high": "置信区间上限", "n_observations": "观测数"}), hide_index=True, use_container_width=True)
    if not events.empty:
        choices = {METRICS.get(metric, metric): metric for metric in events["metric_name"].unique()}
        label = st.selectbox("选择事件研究指标", list(choices), key="事件研究指标")
        event = events.loc[events["metric_name"].eq(choices[label])].sort_values("event_week")
        figure = px.line(event, x="event_week", y="estimated_effect", markers=True, title=f"{label}的政策前后变化路径", labels={"event_week": "相对政策周", "estimated_effect": "相对影响"})
        figure.add_vline(x=0, line_dash="dash", line_color="#b34c3e")
        figure.add_hline(y=0, line_color="#6b7280")
        st.plotly_chart(figure, use_container_width=True)
        interpretation("政策日前的曲线帮助检查处理组与对照组是否已出现不同趋势。", "政策前趋势越稳定，政策后变化越能作为运营判断的可信输入。", "若前趋势异常，应降低策略置信度，优先收集更多控制变量。")

with counterfactual:
    page_header("反事实预测：如果没有拥堵收费，需求可能在哪里？", "反事实模型是运营辅助工具，用于衡量实际订单相对无政策基线的偏离，不替代因果分析。")
    if predictions.empty:
        st.info("当前部署缺少反事实预测文件。sample mode 运行后将自动生成并展示需求缺口。")
    else:
        predictions["date"] = pd.to_datetime(predictions["date"])
        daily = predictions.groupby("date", as_index=False)[["actual_order_count", "predicted_counterfactual_order_count"]].sum().melt(id_vars="date", var_name="需求口径", value_name="订单量")
        daily["需求口径"] = daily["需求口径"].map({"actual_order_count": "实际订单", "predicted_counterfactual_order_count": "无政策预测订单"})
        st.plotly_chart(px.line(daily, x="date", y="订单量", color="需求口径", title="实际订单与无政策预测基线", labels={"date": "日期"}), use_container_width=True)
        interpretation("两条线之间的差值代表实际需求偏离无政策预测基线的程度。", "需求缺口说明值得进一步检查的区域，但不能单独证明政策因果。", "将缺口与乘客价格压力、司机收益压力共同用于决定发券还是调度。")
        ranking = predictions.groupby(["zone_id", "zone_name"], as_index=False).agg(平均需求缺口=("demand_gap", "mean"), 平均缺口率=("demand_gap_rate", "mean"), 实际订单=("actual_order_count", "sum")).nlargest(15, "平均需求缺口")
        st.plotly_chart(px.bar(ranking, x="平均需求缺口", y="zone_name", orientation="h", title="需求缺口最高的区域", labels={"zone_name": "区域"}), use_container_width=True)
        interpretation("排序展示实际订单低于无政策预测最多的区域。", "这些区域可能存在价格抑制或供给响应不足，也可能受未观测因素影响。", "优先检查高历史订单区域是否适合做有预算上限的乘客优惠或供给调整。")

with price:
    page_header("票价与司机影响：乘客多付的钱有没有传导给司机？", "在 OD 路线层面同时观察票价、通行费、司机每分钟收入和订单变化。")
    if not pricing.empty:
        chart = pricing.rename(columns={"fare_per_mile_change": "每英里票价变化", "driver_pay_per_minute_change": "每分钟司机收入变化", "trip_count_post": "政策后订单量", "subsidy_signal": "存在激励信号", "pickup_zone_name": "上车区域", "dropoff_zone_name": "下车区域"})
        figure = px.scatter(chart, x="每英里票价变化", y="每分钟司机收入变化", size="政策后订单量", color="存在激励信号", hover_data=["上车区域", "下车区域"], title="路线四象限：乘客价格与司机收入变化")
        figure.add_hline(y=0, line_color="#6b7280")
        figure.add_vline(x=0, line_color="#6b7280")
        st.plotly_chart(figure, use_container_width=True)
        interpretation("右下象限表示乘客单位成本上升而司机每分钟收入未同步改善。", "这类路线可能出现司机接单意愿下降，即便乘客价格已经更高。", "优先对高订单量或机场路线测试司机侧激励，而不是默认给乘客发券。")
        st.dataframe(chart.loc[chart["存在激励信号"], ["上车区域", "下车区域", "每英里票价变化", "每分钟司机收入变化", "政策后订单量"]].head(20), hide_index=True, use_container_width=True)

with flow:
    page_header("外溢与 OD 流向：需求是不是换了地方？", "识别可能承接收费区需求的边界区域，并结合异质性判断机场、高峰和距离场景。")
    if not spillover.empty:
        top = localized_groups(spillover).head(20).rename(columns={"zone_name": "区域", "zone_group": "区域分组", "spillover_score": "外溢评分"})
        st.plotly_chart(px.bar(top, x="外溢评分", y="区域", color="区域分组", orientation="h", title="最可能承接转移需求的区域"), use_container_width=True)
        interpretation("外溢评分同时考虑相对订单增长和政策后订单量。", "高评分区域是需求承接候选，不等于已经证明所有增长来自收费政策。", "将排名靠前的边界区放入高峰监控与司机预部署试点。")
    if not heterogeneity.empty:
        hetero = heterogeneity.copy()
        hetero["显示分组"] = hetero["dimension"].astype(str) + " · " + hetero["segment"].astype(str)
        st.plotly_chart(px.bar(hetero, x="relative_change", y="显示分组", orientation="h", color="relative_change", color_continuous_scale="RdBu", title="不同场景的相对订单变化", labels={"relative_change": "相对变化"}), use_container_width=True)
        interpretation("图表按时段、机场、距离和区域类型拆解订单变化。", "平均结果可能掩盖机场或晚高峰等高价值场景的不同反应。", "为高敏感场景单独设定派单、补贴和供给控制规则。")
    response_fields = {"avg_response_time_min", "response_time_p90", "slow_response_rate", "valid_response_count"}
    if response_fields.issubset(zone_panel.columns):
        response = localized_groups(zone_panel).groupby(["zone_group", "post_policy"], as_index=False).agg(P90响应时长=("response_time_p90", "mean"), 有效响应记录=("valid_response_count", "sum"))
        response = response.loc[response["有效响应记录"] > 0].copy()
        response["政策阶段"] = response["post_policy"].map({False: "政策前", True: "政策后"})
        if not response.empty:
            st.plotly_chart(px.bar(response, x="zone_group", y="P90响应时长", color="政策阶段", barmode="group", title="不同区域组的 P90 接驾响应时长代理", labels={"zone_group": "区域分组", "P90响应时长": "分钟"}), use_container_width=True)
            interpretation("图表比较请求到车辆到达的 P90 时长代理。", "外溢区订单增长且 P90 响应时长上升时，说明司机供给可能没有同步迁移。", "将这类区域优先纳入高峰预部署和派单权重调整，而不是仅用乘客优惠解决。")
            st.caption("说明：该指标基于 request_datetime 到 on_scene_datetime 的公开数据代理，不等同于乘客看到的真实等待时长。")

with strategy:
    page_header("运营策略：从证据到可执行试点", "策略推荐器将需求缺口、价格压力、司机收益压力和外溢评分组合为行动优先级；每项建议都需要实验验证。")
    if cards.empty:
        st.info("尚未生成策略卡。运行 sample mode 推荐器后，此处将展示完整的作品集演示卡片。")
    else:
        a, b, c = st.columns(3)
        a.metric("策略总数", f"{len(cards)} 条")
        b.metric("高优先级", f"{cards['priority'].isin(['High', 'high']).sum()} 条")
        c.metric("策略类型", f"{cards['strategy_type'].nunique()} 类")
        options = ["全部"] + [STRATEGIES.get(kind, kind) for kind in cards["strategy_type"].drop_duplicates()]
        selected = st.selectbox("选择策略类型", options, key="策略类型")
        shown = cards if selected == "全部" else cards.loc[cards["strategy_type"].map(lambda kind: STRATEGIES.get(kind, kind)).eq(selected)]
        rank = {"High": 0, "high": 0, "Medium": 1, "medium": 1, "Low": 2, "low": 2}
        shown = shown.assign(_rank=shown["priority"].map(rank).fillna(3)).sort_values(["_rank", "final_action_score"], ascending=[True, False])
        for _, item in shown.iterrows():
            target = item.get("target_zone") or item.get("target_od_pair") or "待确定"
            with st.container(border=True):
                st.markdown(f"### {STRATEGIES.get(item['strategy_type'], item['strategy_type'])}")
                x, y = st.columns([3, 2])
                with x:
                    st.markdown(f"**推荐动作**：{item['recommended_action']}")
                    st.markdown(f"**目标区域 / 路线**：{target}")
                    st.markdown(f"**目标时段**：{item.get('target_time_window', '按小时监控')}")
                    st.markdown(f"**识别到的问题**：{item['problem_detected']}")
                with y:
                    st.metric("行动优先级", PRIORITIES.get(item["priority"], item["priority"]))
                    st.metric("证据置信度", item.get("confidence_level", "Low"))
                    st.metric("综合行动评分", f"{item.get('final_action_score', 0):.3f}")
                st.markdown(f"**证据指标**：{evidence_text(item.get('evidence_metric', {}))}")
                st.markdown(f"**预期业务影响**：{item.get('expected_business_impact', '通过小流量试点验证。')}")
                st.caption("建议试点：两周、部分司机/区域进入实验组，对照观察接单率、取消率、空驶时间与履约质量。")

with outputs:
    page_header("最终成果：可以交给运营团队的文件", "分析的终点不是图表，而是可审阅、可下载、可进入试点流程的策略结果。")
    output_catalog = [
        ("司机运力重分配清单", "driver_supply_reallocation.csv", supply_actions, "标出应提前预部署司机的区域与时段。"),
        ("路线司机激励清单", "route_incentive_recommendation.csv", route_actions, "筛选通行成本压力与司机收益压力并存的 OD 路线。"),
        ("乘客优惠候选清单", "passenger_discount_recommendation.csv", discount_actions, "筛选需求缺口与乘客价格压力并存的区域。"),
        ("运营策略卡", "operation_strategy_cards.json", cards, "为看板提供结构化的目标、证据、动作、影响、优先级和置信度。"),
        ("反事实预测结果", "counterfactual_predictions.csv", predictions, "记录实际订单、无政策预测订单与需求缺口。"),
        ("双重差分结果", "did_results.csv", did, "记录政策影响估计、置信区间与观测数。"),
    ]
    catalog = pd.DataFrame([{"成果": title, "文件": filename, "业务用途": use, "可用记录": f"{len(data):,}"} for title, filename, data, use in output_catalog])
    st.dataframe(catalog, hide_index=True, use_container_width=True)
    for title, filename, data, _ in output_catalog:
        if data.empty:
            continue
        if filename.endswith(".json"):
            payload = json.dumps(data.to_dict(orient="records"), ensure_ascii=False, indent=2).encode("utf-8")
            mime = "application/json"
        else:
            payload = data.to_csv(index=False).encode("utf-8-sig")
            mime = "text/csv"
        st.download_button(f"下载{title}", payload, file_name=filename, mime=mime, key=f"下载_{filename}")
