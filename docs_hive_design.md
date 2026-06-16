# Hive Warehouse Design

Hive is added as the offline warehouse metadata layer. It manages SQL access over raw Parquet files, cleaned partitioned Parquet tables, and reusable aggregate marts.

## Layers

| Layer | Purpose | Example Tables |
| --- | --- | --- |
| ODS | External tables over official TLC raw files | `ods_fhvhv_trips`, `ods_yellow_trips` |
| DWD | Cleaned and conformed trip fact table | `dwd_clean_trips` |
| DWS | Reusable analytical marts | `dws_hourly_demand`, `dws_zone_hourly_demand` |
| ADS | Dashboard/model-facing outputs | PostgreSQL tables, Streamlit CSV extracts |

## Architecture

```text
NYC TLC Parquet
    -> Hive ODS external tables
    -> PySpark cleaning and feature engineering
    -> Hive DWD partitioned Parquet table
    -> Hive DWS aggregate tables
    -> PostgreSQL / Streamlit / model training
```

## Why Hive Fits

- The source data is already Parquet and monthly, so it maps naturally to external tables.
- Clean trip facts can be partitioned by `pickup_month`.
- Analysts can query offline metrics through SQL.
- PostgreSQL can remain the lighter serving layer for dashboard-ready aggregates.

## Usage

The DDL lives in `src/warehouse/hive_schema.sql`.

```bash
hive -f src/warehouse/hive_schema.sql
```

For a local Windows portfolio project, installing full Hive is optional. The repository demonstrates Hive warehouse design through DDL, layer naming, partition strategy, and Spark-compatible Parquet outputs.

