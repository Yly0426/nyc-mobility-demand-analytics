# Data Source Notes

The project uses official NYC Taxi & Limousine Commission trip records.

- Official page: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- Raw files are monthly Parquet files.
- Local raw data path: `data/raw/nyc_tlc/`

Downloaded local scope:

| Service | Months | Files | Compressed size |
| --- | --- | ---: | ---: |
| Yellow Taxi | 2024-01 to 2025-10 | 22 | ~1.28 GB |
| High Volume FHV | 2024-01 to 2025-12 | 24 | ~10.93 GB |

The raw data is intentionally not committed to GitHub. Re-run `scripts/download_nyc_tlc.py` or use the official monthly URLs to rebuild the local dataset.
