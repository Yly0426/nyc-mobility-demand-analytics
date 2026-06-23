-- Hive-compatible ODS/DWD/DWS contract. Local sample execution uses Pandas-equivalent exports.
CREATE DATABASE IF NOT EXISTS mobility_analytics;
USE mobility_analytics;

CREATE EXTERNAL TABLE IF NOT EXISTS ods_hvfhv_trip_raw (
  request_datetime TIMESTAMP, on_scene_datetime TIMESTAMP, pickup_datetime TIMESTAMP, dropoff_datetime TIMESTAMP,
  PULocationID INT, DOLocationID INT, trip_miles DOUBLE, base_passenger_fare DOUBLE, tolls DOUBLE,
  congestion_surcharge DOUBLE, cbd_congestion_fee DOUBLE, airport_fee DOUBLE, driver_pay DOUBLE
) STORED AS PARQUET LOCATION '/warehouse/nyc_tlc/ods/hvfhv';

CREATE EXTERNAL TABLE IF NOT EXISTS ods_taxi_zone_lookup (
  location_id INT, borough STRING, zone STRING, service_zone STRING
) ROW FORMAT DELIMITED FIELDS TERMINATED BY ',' STORED AS TEXTFILE
LOCATION '/warehouse/nyc_tlc/ods/taxi_zone_lookup' TBLPROPERTIES ('skip.header.line.count'='1');

CREATE EXTERNAL TABLE IF NOT EXISTS dwd_hvfhv_trip_clean (
  trip_id BIGINT, request_datetime TIMESTAMP, on_scene_datetime TIMESTAMP, pickup_datetime TIMESTAMP, dropoff_datetime TIMESTAMP,
  trip_date DATE, trip_hour INT, weekday INT, is_weekend BOOLEAN, pickup_location_id INT, dropoff_location_id INT,
  pickup_zone STRING, dropoff_zone STRING, pickup_borough STRING, dropoff_borough STRING, trip_miles DOUBLE,
  trip_time_min DOUBLE, base_passenger_fare DOUBLE, tolls DOUBLE, congestion_surcharge DOUBLE, cbd_congestion_fee DOUBLE,
  airport_fee DOUBLE, driver_pay DOUBLE, fare_per_mile DOUBLE, fare_per_minute DOUBLE, driver_pay_per_mile DOUBLE,
  driver_pay_per_minute DOUBLE, response_time_min DOUBLE, is_airport_trip BOOLEAN, is_core_zone_trip BOOLEAN,
  is_boundary_zone_trip BOOLEAN, policy_period STRING
) STORED AS PARQUET LOCATION '/warehouse/nyc_tlc/dwd/hvfhv_trip_clean';
