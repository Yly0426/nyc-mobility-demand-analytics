-- The PySpark job should apply this same validation contract before writing DWD.
INSERT OVERWRITE TABLE dwd_hvfhv_trip_clean
SELECT *, CASE WHEN pickup_datetime >= DATE '2025-01-05' THEN '政策后' ELSE '政策前' END
FROM ods_hvfhv_trip_raw
WHERE trip_miles > 0 AND base_passenger_fare > 0 AND driver_pay >= 0
  AND dropoff_datetime > pickup_datetime;
