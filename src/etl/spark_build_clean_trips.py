from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from src.utils.paths import PROCESSED_DIR, RAW_DIR, ensure_project_dirs


SERVICE_PATTERNS = {
    "yellow": ("yellow", "yellow_tripdata_*.parquet"),
    "fhvhv": ("fhvhv", "fhvhv_tripdata_*.parquet"),
}


def list_files(service: str, sample_files: int | None) -> list[str]:
    folder, pattern = SERVICE_PATTERNS[service]
    files = sorted((RAW_DIR / folder).glob(pattern))
    if sample_files:
        files = files[:sample_files]
    if not files:
        raise FileNotFoundError(f"No raw files found for service={service}")
    return [str(path) for path in files]


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("nyc-mobility-clean-trips")
        .config("spark.sql.shuffle.partitions", "96")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .getOrCreate()
    )


def normalize_yellow(df):
    return df.select(
        F.lit("yellow_taxi").alias("service_type"),
        F.col("tpep_pickup_datetime").cast("timestamp").alias("pickup_datetime"),
        F.col("tpep_dropoff_datetime").cast("timestamp").alias("dropoff_datetime"),
        F.col("PULocationID").cast("int").alias("pickup_location_id"),
        F.col("DOLocationID").cast("int").alias("dropoff_location_id"),
        F.col("trip_distance").cast("double").alias("trip_distance"),
        F.col("fare_amount").cast("double").alias("fare_amount"),
        F.col("total_amount").cast("double").alias("total_amount"),
        F.lit(None).cast("double").alias("driver_pay"),
        F.col("tip_amount").cast("double").alias("tips"),
        F.col("payment_type").cast("int").alias("payment_type"),
        F.lit(None).cast("string").alias("shared_match_flag"),
        F.lit(None).cast("string").alias("wav_request_flag"),
    )


def normalize_fhvhv(df):
    return df.select(
        F.lit("high_volume_fhv").alias("service_type"),
        F.col("pickup_datetime").cast("timestamp").alias("pickup_datetime"),
        F.col("dropoff_datetime").cast("timestamp").alias("dropoff_datetime"),
        F.col("PULocationID").cast("int").alias("pickup_location_id"),
        F.col("DOLocationID").cast("int").alias("dropoff_location_id"),
        F.col("trip_miles").cast("double").alias("trip_distance"),
        F.col("base_passenger_fare").cast("double").alias("fare_amount"),
        F.col("base_passenger_fare").cast("double").alias("total_amount"),
        F.col("driver_pay").cast("double").alias("driver_pay"),
        F.col("tips").cast("double").alias("tips"),
        F.lit(None).cast("int").alias("payment_type"),
        F.col("shared_match_flag").cast("string").alias("shared_match_flag"),
        F.col("wav_request_flag").cast("string").alias("wav_request_flag"),
    )


def add_features_and_rules(df):
    df = (
        df.withColumn(
            "trip_duration_min",
            (F.unix_timestamp("dropoff_datetime") - F.unix_timestamp("pickup_datetime")) / 60.0,
        )
        .withColumn("pickup_date", F.to_date("pickup_datetime"))
        .withColumn("pickup_hour", F.hour("pickup_datetime"))
        .withColumn("pickup_weekday", F.dayofweek("pickup_datetime") - 2)
        .withColumn("pickup_month", F.date_format("pickup_datetime", "yyyy-MM"))
    )
    invalid_reason = (
        F.when(F.col("pickup_datetime").isNull() | F.col("dropoff_datetime").isNull(), "missing_time")
        .when(F.col("trip_duration_min") <= 0, "non_positive_duration")
        .when(F.col("trip_duration_min") > 8 * 60, "duration_over_8h")
        .when(F.col("trip_distance").isNull() | (F.col("trip_distance") <= 0.01), "non_positive_distance")
        .when(F.col("trip_distance") > 200, "distance_over_200")
        .when(F.col("pickup_location_id").isNull() | F.col("dropoff_location_id").isNull(), "missing_zone")
        .when(F.col("fare_amount") < 0, "negative_fare")
        .when(F.col("total_amount") > 1000, "total_amount_over_1000")
    )
    return (
        df.withColumn("invalid_reason", invalid_reason)
        .withColumn("is_valid_trip", F.col("invalid_reason").isNull())
        .select(
            "service_type",
            "pickup_datetime",
            "dropoff_datetime",
            "pickup_date",
            "pickup_hour",
            "pickup_weekday",
            "pickup_month",
            "pickup_location_id",
            "dropoff_location_id",
            "trip_distance",
            "trip_duration_min",
            "fare_amount",
            "total_amount",
            "driver_pay",
            "tips",
            "payment_type",
            "shared_match_flag",
            "wav_request_flag",
            "is_valid_trip",
            "invalid_reason",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", choices=sorted(SERVICE_PATTERNS), default="fhvhv")
    parser.add_argument("--sample-files", type=int, default=None)
    args = parser.parse_args()

    ensure_project_dirs()
    spark = build_spark()
    files = list_files(args.service, args.sample_files)
    raw = spark.read.parquet(*files)
    normalized = normalize_yellow(raw) if args.service == "yellow" else normalize_fhvhv(raw)
    clean = add_features_and_rules(normalized)

    suffix = f"sample_{args.sample_files}" if args.sample_files else "full"
    output_path = PROCESSED_DIR / f"spark_clean_trips_{args.service}_{suffix}"
    clean.write.mode("overwrite").partitionBy("pickup_month").parquet(str(output_path))
    print(f"Wrote {output_path}")
    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

