CREATE TABLE IF NOT EXISTS dws_price_driver_metrics STORED AS PARQUET AS
SELECT CASE WHEN trip_miles <= 2 THEN '短途(0-2英里)' WHEN trip_miles <= 8 THEN '中途(2-8英里)' ELSE '长途(8+英里)' END AS trip_distance_group,
       policy_period, COUNT(*) AS order_count, AVG(fare_per_mile) AS avg_fare_per_mile,
       AVG(fare_per_minute) AS avg_fare_per_minute, AVG(tolls) AS avg_tolls,
       AVG(cbd_congestion_fee) AS avg_cbd_congestion_fee, AVG(driver_pay_per_mile) AS avg_driver_pay_per_mile,
       AVG(driver_pay_per_minute) AS avg_driver_pay_per_minute, AVG(driver_pay / NULLIF(base_passenger_fare, 0)) AS driver_pay_to_fare_ratio
FROM dwd_hvfhv_trip_clean GROUP BY CASE WHEN trip_miles <= 2 THEN '短途(0-2英里)' WHEN trip_miles <= 8 THEN '中途(2-8英里)' ELSE '长途(8+英里)' END, policy_period;
