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

