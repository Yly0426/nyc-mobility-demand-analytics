# NYC Mobility Demand Analytics - Project Summary

## Scope

This report summarizes the `fhvhv_sample_2` run of the NYC TLC mobility analytics pipeline. The validated sample uses the first two months of 2024 High Volume FHV data, covering tens of millions of ride-hailing records.

## Data Quality Findings

The raw data contains realistic operational issues that require cleaning before analysis:

- distance_over_200: 150 records
- duration_over_8h: 39 records
- negative_fare: 8,700 records
- non_positive_distance: 8,216 records
- non_positive_duration: 5 records
- total_amount_over_1000: 8 records

These checks include non-positive duration, non-positive distance, very long trips, missing pickup/dropoff zones, negative fare values, and extreme total amounts.

## Business Metrics

- Valid trips analyzed: 39,005,960
- Average fare: $24.12
- Average distance: 4.88 miles
- Average duration: 18.9 minutes
- Peak pickup hour: 18
- Peak pickup weekday index: 5 where Monday=0
- Highest-demand pickup borough: Manhattan

## Top Pickup Zones

| pickup_borough | pickup_zone | trip_count |
| --- | --- | --- |
| Queens | JFK Airport | 687938 |
| Queens | LaGuardia Airport | 681456 |
| Manhattan | East Village | 545381 |
| Brooklyn | Crown Heights North | 517327 |
| Manhattan | Times Sq/Theatre District | 479305 |
| Manhattan | Midtown Center | 475476 |
| Manhattan | TriBeCa/Civic Center | 463464 |
| Manhattan | East Chelsea | 434848 |
| Manhattan | Union Sq | 434122 |
| Manhattan | West Chelsea/Hudson Yards | 429077 |

## Top OD Flows

| service_type | pickup_location_id | dropoff_location_id | trip_count | distance_sum | duration_sum | fare_sum | avg_distance | avg_duration_min | avg_fare | fare_per_mile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high_volume_fhv | 132 | 265 | 129080 | 3,853,068.96 | 6,672,674.57 | 13,926,735.28 | 29.85 | 51.69 | 107.89 | 3.61 |
| high_volume_fhv | 76 | 76 | 127649 | 183,849.85 | 1,055,066.92 | 1,340,521.34 | 1.44 | 8.27 | 10.50 | 7.29 |
| high_volume_fhv | 26 | 26 | 95132 | 106,893.21 | 908,473.42 | 1,031,997.29 | 1.12 | 9.55 | 10.85 | 9.65 |
| high_volume_fhv | 138 | 265 | 85188 | 2,251,988.29 | 3,896,294.40 | 8,663,632.93 | 26.44 | 45.74 | 101.70 | 3.85 |
| high_volume_fhv | 39 | 39 | 78505 | 99,834.95 | 561,508.85 | 783,967.72 | 1.27 | 7.15 | 9.99 | 7.85 |
| high_volume_fhv | 61 | 61 | 64049 | 81,123.14 | 562,785.00 | 688,012.14 | 1.27 | 8.79 | 10.74 | 8.48 |
| high_volume_fhv | 14 | 14 | 55948 | 64,839.13 | 373,687.32 | 548,760.09 | 1.16 | 6.68 | 9.81 | 8.46 |
| high_volume_fhv | 7 | 7 | 55630 | 55,723.21 | 376,939.02 | 532,866.81 | 1.00 | 6.78 | 9.58 | 9.56 |
| high_volume_fhv | 129 | 129 | 53324 | 60,771.40 | 446,312.98 | 544,092.12 | 1.14 | 8.37 | 10.20 | 8.95 |
| high_volume_fhv | 95 | 95 | 49842 | 58,500.01 | 388,763.18 | 509,243.75 | 1.17 | 7.80 | 10.22 | 8.71 |

## Demand Forecast Baseline

The baseline model predicts zone-hour trip volume using time and pickup-zone features.

- Rows used: 361,043
- MAE: 20.79
- RMSE: 36.40
- R2: 0.907

## Interpretation

The project shows how a mobility platform can transform raw trip logs into reusable operational indicators. The main value is not only forecasting demand, but also building a data pipeline that exposes dirty records, standardizes multi-service schemas, and creates warehouse-ready metrics for business analysis.
