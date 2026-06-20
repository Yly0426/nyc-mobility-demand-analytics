CREATE SCHEMA IF NOT EXISTS mobility;

CREATE TABLE IF NOT EXISTS mobility.hourly_demand (
    service_type TEXT,
    pickup_date DATE,
    pickup_hour INTEGER,
    pickup_weekday INTEGER,
    pickup_month TEXT,
    trip_count BIGINT,
    distance_sum DOUBLE PRECISION,
    duration_sum DOUBLE PRECISION,
    fare_sum DOUBLE PRECISION,
    tips_sum DOUBLE PRECISION,
    driver_pay_sum DOUBLE PRECISION,
    avg_distance DOUBLE PRECISION,
    avg_duration_min DOUBLE PRECISION,
    avg_fare DOUBLE PRECISION,
    fare_per_mile DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS mobility.zone_hourly_demand (
    service_type TEXT,
    pickup_date DATE,
    pickup_hour INTEGER,
    pickup_location_id INTEGER,
    trip_count BIGINT,
    distance_sum DOUBLE PRECISION,
    duration_sum DOUBLE PRECISION,
    fare_sum DOUBLE PRECISION,
    avg_distance DOUBLE PRECISION,
    avg_duration_min DOUBLE PRECISION,
    avg_fare DOUBLE PRECISION,
    fare_per_mile DOUBLE PRECISION,
    pickup_borough TEXT,
    pickup_zone TEXT,
    pickup_service_zone TEXT
);

CREATE TABLE IF NOT EXISTS mobility.top_od_flows (
    service_type TEXT,
    pickup_location_id INTEGER,
    dropoff_location_id INTEGER,
    trip_count BIGINT,
    distance_sum DOUBLE PRECISION,
    duration_sum DOUBLE PRECISION,
    fare_sum DOUBLE PRECISION,
    avg_distance DOUBLE PRECISION,
    avg_duration_min DOUBLE PRECISION,
    avg_fare DOUBLE PRECISION,
    fare_per_mile DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS mobility.invalid_trip_summary (
    service_type TEXT,
    invalid_reason TEXT,
    record_count BIGINT
);

CREATE TABLE IF NOT EXISTS mobility.zone_hour_policy_metrics (
    zone_id INTEGER NOT NULL, zone_name TEXT, metric_date DATE NOT NULL, hour INTEGER NOT NULL,
    zone_group TEXT, post_policy BOOLEAN, order_count BIGINT, avg_fare_per_mile DOUBLE PRECISION,
    avg_driver_pay_per_minute DOUBLE PRECISION, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (zone_id, metric_date, hour)
);
CREATE INDEX IF NOT EXISTS idx_zone_hour_policy_filter ON mobility.zone_hour_policy_metrics (zone_group, metric_date, hour);

CREATE TABLE IF NOT EXISTS mobility.od_policy_metrics (
    pickup_zone_id INTEGER NOT NULL, dropoff_zone_id INTEGER NOT NULL, metric_date DATE NOT NULL,
    hour INTEGER NOT NULL, od_order_count BIGINT, avg_fare_per_mile DOUBLE PRECISION,
    avg_driver_pay_per_minute DOUBLE PRECISION, is_airport_od BOOLEAN, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pickup_zone_id, dropoff_zone_id, metric_date, hour)
);
CREATE INDEX IF NOT EXISTS idx_od_policy_filter ON mobility.od_policy_metrics (metric_date, hour, is_airport_od);

CREATE TABLE IF NOT EXISTS mobility.causal_effect_results (
    metric_name TEXT PRIMARY KEY, coef_treated_post DOUBLE PRECISION, std_error DOUBLE PRECISION,
    p_value DOUBLE PRECISION, confidence_interval_low DOUBLE PRECISION, confidence_interval_high DOUBLE PRECISION,
    business_interpretation TEXT, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mobility.event_study_results (
    metric_name TEXT NOT NULL, event_week INTEGER NOT NULL, estimated_effect DOUBLE PRECISION,
    std_error DOUBLE PRECISION, ci_low DOUBLE PRECISION, ci_high DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (metric_name, event_week)
);

CREATE TABLE IF NOT EXISTS mobility.pricing_driver_metrics (
    pickup_zone_name TEXT NOT NULL, dropoff_zone_name TEXT NOT NULL, fare_per_mile_change DOUBLE PRECISION,
    driver_pay_per_minute_change DOUBLE PRECISION, demand_change DOUBLE PRECISION, subsidy_signal BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (pickup_zone_name, dropoff_zone_name)
);

CREATE TABLE IF NOT EXISTS mobility.operation_strategy_cards (
    strategy_id TEXT PRIMARY KEY, strategy_type TEXT, target_zone TEXT, target_od_pair TEXT,
    target_time_window TEXT, problem_detected TEXT, evidence_metric TEXT, recommended_action TEXT,
    expected_business_impact TEXT, priority TEXT, created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mobility.model_counterfactual_results (
    zone_id INTEGER NOT NULL, metric_date DATE NOT NULL, hour INTEGER NOT NULL, actual_order_count DOUBLE PRECISION,
    counterfactual_order_count DOUBLE PRECISION, counterfactual_gap DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (zone_id, metric_date, hour)
);
