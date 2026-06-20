CREATE DATABASE IF NOT EXISTS mobility_analytics;
USE mobility_analytics;

CREATE EXTERNAL TABLE IF NOT EXISTS ods_fhvhv_trips (
    hvfhs_license_num STRING,
    dispatching_base_num STRING,
    originating_base_num STRING,
    request_datetime TIMESTAMP,
    on_scene_datetime TIMESTAMP,
    pickup_datetime TIMESTAMP,
    dropoff_datetime TIMESTAMP,
    PULocationID INT,
    DOLocationID INT,
    trip_miles DOUBLE,
    trip_time BIGINT,
    base_passenger_fare DOUBLE,
    tolls DOUBLE,
    bcf DOUBLE,
    sales_tax DOUBLE,
    congestion_surcharge DOUBLE,
    airport_fee DOUBLE,
    tips DOUBLE,
    driver_pay DOUBLE,
    shared_request_flag STRING,
    shared_match_flag STRING,
    access_a_ride_flag STRING,
    wav_request_flag STRING,
    wav_match_flag STRING
)
STORED AS PARQUET
LOCATION '/warehouse/nyc_tlc/raw/fhvhv';

CREATE EXTERNAL TABLE IF NOT EXISTS ods_yellow_trips (
    VendorID INT,
    tpep_pickup_datetime TIMESTAMP,
    tpep_dropoff_datetime TIMESTAMP,
    passenger_count DOUBLE,
    trip_distance DOUBLE,
    RatecodeID DOUBLE,
    store_and_fwd_flag STRING,
    PULocationID INT,
    DOLocationID INT,
    payment_type BIGINT,
    fare_amount DOUBLE,
    extra DOUBLE,
    mta_tax DOUBLE,
    tip_amount DOUBLE,
    tolls_amount DOUBLE,
    improvement_surcharge DOUBLE,
    total_amount DOUBLE,
    congestion_surcharge DOUBLE,
    airport_fee DOUBLE
)
STORED AS PARQUET
LOCATION '/warehouse/nyc_tlc/raw/yellow';

CREATE EXTERNAL TABLE IF NOT EXISTS dim_taxi_zone (
    location_id INT,
    borough STRING,
    zone STRING,
    service_zone STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/warehouse/nyc_tlc/raw/zones'
TBLPROPERTIES ('skip.header.line.count'='1');

CREATE EXTERNAL TABLE IF NOT EXISTS dwd_clean_trips (
    service_type STRING,
    pickup_datetime TIMESTAMP,
    dropoff_datetime TIMESTAMP,
    pickup_date DATE,
    pickup_hour INT,
    pickup_weekday INT,
    pickup_location_id INT,
    dropoff_location_id INT,
    trip_distance DOUBLE,
    trip_duration_min DOUBLE,
    fare_amount DOUBLE,
    total_amount DOUBLE,
    driver_pay DOUBLE,
    tips DOUBLE,
    payment_type INT,
    shared_match_flag STRING,
    wav_request_flag STRING,
    is_valid_trip BOOLEAN,
    invalid_reason STRING
)
PARTITIONED BY (pickup_month STRING)
STORED AS PARQUET
LOCATION '/warehouse/nyc_tlc/dwd/clean_trips';

CREATE EXTERNAL TABLE IF NOT EXISTS dws_hourly_demand (
    service_type STRING,
    pickup_date DATE,
    pickup_hour INT,
    pickup_weekday INT,
    pickup_month STRING,
    trip_count BIGINT,
    distance_sum DOUBLE,
    duration_sum DOUBLE,
    fare_sum DOUBLE,
    tips_sum DOUBLE,
    driver_pay_sum DOUBLE,
    avg_distance DOUBLE,
    avg_duration_min DOUBLE,
    avg_fare DOUBLE,
    fare_per_mile DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/warehouse/nyc_tlc/dws/hourly_demand'
TBLPROPERTIES ('skip.header.line.count'='1');

CREATE EXTERNAL TABLE IF NOT EXISTS dws_zone_hourly_demand (
    service_type STRING,
    pickup_date DATE,
    pickup_hour INT,
    pickup_location_id INT,
    trip_count BIGINT,
    distance_sum DOUBLE,
    duration_sum DOUBLE,
    fare_sum DOUBLE,
    avg_distance DOUBLE,
    avg_duration_min DOUBLE,
    avg_fare DOUBLE,
    fare_per_mile DOUBLE,
    pickup_borough STRING,
    pickup_zone STRING,
    pickup_service_zone STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/warehouse/nyc_tlc/dws/zone_hourly_demand'
TBLPROPERTIES ('skip.header.line.count'='1');

MSCK REPAIR TABLE dwd_clean_trips;

-- DWD: one cleaned trip enriched with configurable policy-zone attributes.
-- Grain: trip; logical key is source trip timestamp plus pickup/dropoff zone.
CREATE EXTERNAL TABLE IF NOT EXISTS dwd_trip_policy_feature (
    service_type STRING, pickup_datetime TIMESTAMP, dropoff_datetime TIMESTAMP,
    pickup_location_id INT, dropoff_location_id INT, trip_miles DOUBLE, trip_time DOUBLE,
    base_passenger_fare DOUBLE, total_amount DOUBLE, driver_pay DOUBLE, tips DOUBLE, tolls DOUBLE,
    pickup_zone_name STRING, dropoff_zone_name STRING, pickup_borough STRING, dropoff_borough STRING,
    pickup_zone_group STRING, dropoff_zone_group STRING, is_pickup_treated BOOLEAN,
    is_pickup_spillover BOOLEAN, is_pickup_control BOOLEAN, is_cross_treated_trip BOOLEAN,
    is_airport_trip BOOLEAN, policy_date DATE, post_policy BOOLEAN, trip_date DATE,
    trip_hour INT, weekday INT, is_weekend BOOLEAN, fare_per_mile DOUBLE,
    driver_pay_per_minute DOUBLE
)
PARTITIONED BY (trip_month STRING)
STORED AS PARQUET
LOCATION '/warehouse/nyc_tlc/dwd/trip_policy_feature';

-- DWS: zone-date-hour policy panel, unique on zone_id + dt + hour.
CREATE EXTERNAL TABLE IF NOT EXISTS dws_zone_hour_policy_panel (
    zone_id INT, zone_name STRING, pickup_borough STRING, zone_group STRING, hour INT,
    weekday INT, is_weekend BOOLEAN, post_policy BOOLEAN, order_count BIGINT,
    avg_trip_miles DOUBLE, avg_trip_time DOUBLE, avg_base_fare DOUBLE, avg_total_amount DOUBLE,
    avg_driver_pay DOUBLE, avg_fare_per_mile DOUBLE, avg_driver_pay_per_minute DOUBLE,
    avg_tolls DOUBLE, airport_trip_count BIGINT, short_trip_count BIGINT, long_trip_count BIGINT,
    treated_pickup_count BIGINT, treated_dropoff_count BIGINT, spillover_pickup_count BIGINT,
    control_pickup_count BIGINT, treated_zone BOOLEAN, log_order_count DOUBLE
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '/warehouse/nyc_tlc/dws/zone_hour_policy_panel';

-- DWS: OD-date-hour panel, unique on pickup_zone_id + dropoff_zone_id + dt + hour.
CREATE EXTERNAL TABLE IF NOT EXISTS dws_od_policy_panel (
    pickup_location_id INT, pickup_zone_name STRING, dropoff_location_id INT,
    dropoff_zone_name STRING, hour INT, post_policy BOOLEAN, od_order_count BIGINT,
    avg_trip_miles DOUBLE, avg_trip_time DOUBLE, avg_base_fare DOUBLE, avg_driver_pay DOUBLE,
    avg_tolls DOUBLE, avg_fare_per_mile DOUBLE, avg_driver_pay_per_minute DOUBLE,
    is_cross_treated_od BOOLEAN, is_airport_od BOOLEAN
)
PARTITIONED BY (dt STRING)
STORED AS PARQUET
LOCATION '/warehouse/nyc_tlc/dws/od_policy_panel';

-- Dashboard-facing policy effects and operation recommendations are stored as light DWS marts.
CREATE EXTERNAL TABLE IF NOT EXISTS dws_policy_effect_result (
    metric_name STRING, coef_treated_post DOUBLE, std_error DOUBLE, p_value DOUBLE,
    confidence_interval_low DOUBLE, confidence_interval_high DOUBLE, business_interpretation STRING
) STORED AS PARQUET LOCATION '/warehouse/nyc_tlc/dws/policy_effect_result';

CREATE EXTERNAL TABLE IF NOT EXISTS dws_operation_strategy_recommendation (
    strategy_id STRING, strategy_type STRING, target_zone STRING, target_od_pair STRING,
    target_time_window STRING, problem_detected STRING, evidence_metric STRING,
    recommended_action STRING, expected_business_impact STRING, priority STRING
) STORED AS PARQUET LOCATION '/warehouse/nyc_tlc/dws/operation_strategy_recommendation';
