CREATE TABLE IF NOT EXISTS dws_zone_demand_metrics STORED AS PARQUET AS
SELECT pickup_zone, pickup_borough, COUNT(*) AS pickup_order_count, AVG(fare_per_mile) AS avg_fare_per_mile,
       AVG(driver_pay_per_minute) AS avg_driver_pay_per_minute, AVG(response_time_min) AS avg_response_time_min
FROM dwd_hvfhv_trip_clean GROUP BY pickup_zone, pickup_borough;
