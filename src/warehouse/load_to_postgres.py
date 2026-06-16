from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from src.utils.paths import PROJECT_ROOT, WAREHOUSE_DIR


TABLE_MAP = {
    "hourly_demand": "hourly_demand",
    "zone_hourly_demand": "zone_hourly_demand",
    "top_od_flows": "top_od_flows",
    "invalid_trip_summary": "invalid_trip_summary",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="fhvhv")
    parser.add_argument("--suffix", default="sample_2")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    args = parser.parse_args()

    if not args.database_url:
        raise ValueError("Provide --database-url or set DATABASE_URL.")

    engine = create_engine(args.database_url)
    schema_sql = (PROJECT_ROOT / "src" / "warehouse" / "schema.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        for stmt in schema_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))

    for prefix, table_name in TABLE_MAP.items():
        path = WAREHOUSE_DIR / f"{prefix}_{args.service}_{args.suffix}.csv"
        if not path.exists():
            print(f"Skip missing {path}")
            continue
        df = pd.read_csv(path)
        df.to_sql(table_name, engine, schema="mobility", if_exists="replace", index=False, chunksize=10_000)
        print(f"Loaded {len(df):,} rows into mobility.{table_name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

