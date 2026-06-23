CREATE TABLE IF NOT EXISTS dws_od_route_metrics STORED AS PARQUET AS
SELECT pickup_zone, dropoff_zone, pickup_borough, dropoff_borough, COUNT(*) AS order_count,
       AVG(trip_miles) AS avg_trip_miles, AVG(trip_time_min) AS avg_trip_time_min,
       AVG(base_passenger_fare) AS avg_base_passenger_fare, AVG(fare_per_mile) AS avg_fare_per_mile,
       AVG(driver_pay) AS avg_driver_pay, AVG(driver_pay_per_minute) AS avg_driver_pay_per_minute,
       AVG(response_time_min) AS avg_response_time_min
FROM dwd_hvfhv_trip_clean GROUP BY pickup_zone, dropoff_zone, pickup_borough, dropoff_borough;
