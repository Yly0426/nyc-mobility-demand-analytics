CREATE TABLE IF NOT EXISTS dws_time_demand_metrics STORED AS PARQUET AS
SELECT trip_date AS date, trip_hour AS hour, weekday, is_weekend, COUNT(*) AS order_count,
       AVG(trip_miles) AS avg_trip_miles, AVG(base_passenger_fare) AS avg_base_passenger_fare, AVG(driver_pay) AS avg_driver_pay
FROM dwd_hvfhv_trip_clean GROUP BY trip_date, trip_hour, weekday, is_weekend;
