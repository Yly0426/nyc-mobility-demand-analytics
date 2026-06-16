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

