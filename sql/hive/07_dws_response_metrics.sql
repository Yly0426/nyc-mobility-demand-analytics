CREATE TABLE IF NOT EXISTS dws_response_metrics STORED AS PARQUET AS
SELECT pickup_zone, trip_hour AS hour, COUNT(*) AS order_count, AVG(response_time_min) AS avg_response_time_min,
       percentile_approx(response_time_min, 0.5) AS p50_response_time_min,
       percentile_approx(response_time_min, 0.9) AS p90_response_time_min,
       AVG(CASE WHEN response_time_min > 10 THEN 1.0 ELSE 0.0 END) AS slow_response_rate
FROM dwd_hvfhv_trip_clean WHERE response_time_min IS NOT NULL GROUP BY pickup_zone, trip_hour;
