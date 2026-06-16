from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://d37ci6vzurychx.cloudfront.net"
DATASET_PREFIX = {
    "yellow": "yellow_tripdata",
    "green": "green_tripdata",
    "fhv": "fhv_tripdata",
    "fhvhv": "fhvhv_tripdata",
}


def remote_size(url: str) -> int | None:
    headers = {
        "User-Agent": "Mozilla/5.0 nyc-tlc-project-downloader",
        "Accept": "*/*",
    }
    request = Request(url, method="HEAD", headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            length = response.headers.get("Content-Length")
            return int(length) if length else None
    except HTTPError as exc:
        if exc.code == 404:
            return None
        if exc.code != 403:
            raise

    request = Request(url, headers={**headers, "Range": "bytes=0-0"})
    try:
        with urlopen(request, timeout=30) as response:
            content_range = response.headers.get("Content-Range")
            if content_range and "/" in content_range:
                return int(content_range.rsplit("/", 1)[1])
            length = response.headers.get("Content-Length")
            return int(length) if length else None
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def download_file(url: str, destination: Path, expected_size: int | None) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and expected_size and destination.stat().st_size == expected_size:
        return {
            "file": str(destination),
            "url": url,
            "status": "skipped",
            "bytes": expected_size,
        }

    temp_path = destination.with_suffix(destination.suffix + ".part")
    bytes_done = temp_path.stat().st_size if temp_path.exists() else 0
    headers = {
        "User-Agent": "Mozilla/5.0 nyc-tlc-project-downloader",
        "Accept": "*/*",
    }
    if bytes_done:
        headers["Range"] = f"bytes={bytes_done}-"

    request = Request(url, headers=headers)
    started = time.time()
    with urlopen(request, timeout=120) as response, temp_path.open("ab" if bytes_done else "wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            bytes_done += len(chunk)
            if expected_size:
                pct = bytes_done / expected_size * 100
                elapsed = max(time.time() - started, 0.001)
                mbps = (bytes_done / 1024 / 1024) / elapsed
                print(f"\r{destination.name}: {pct:6.2f}% ({mbps:5.1f} MB/s)", end="")
                sys.stdout.flush()
    print()

    if expected_size and temp_path.stat().st_size != expected_size:
        raise RuntimeError(
            f"Size mismatch for {destination.name}: expected {expected_size}, got {temp_path.stat().st_size}"
        )
    temp_path.replace(destination)
    return {
        "file": str(destination),
        "url": url,
        "status": "downloaded",
        "bytes": destination.stat().st_size,
    }


def month_range(years: list[int], through: str | None) -> list[str]:
    months = []
    cutoff = through if through else "9999-12"
    for year in years:
        for month in range(1, 13):
            value = f"{year}-{month:02d}"
            if value <= cutoff:
                months.append(value)
    return months


def main() -> int:
    parser = argparse.ArgumentParser(description="Download NYC TLC monthly parquet files.")
    parser.add_argument("--dataset", choices=sorted(DATASET_PREFIX), default="yellow")
    parser.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    parser.add_argument("--through", help="Optional YYYY-MM cutoff, for example 2025-05.")
    parser.add_argument("--out-dir", default="data/raw/nyc_tlc")
    args = parser.parse_args()

    output_dir = Path(args.out_dir)
    prefix = DATASET_PREFIX[args.dataset]
    results = []

    zone_url = f"{BASE_URL}/misc/taxi_zone_lookup.csv"
    zone_path = output_dir / "taxi_zone_lookup.csv"
    size = remote_size(zone_url)
    print(f"Checking {zone_url}")
    results.append(download_file(zone_url, zone_path, size))

    for ym in month_range(args.years, args.through):
        url = f"{BASE_URL}/trip-data/{prefix}_{ym}.parquet"
        file_path = output_dir / args.dataset / f"{prefix}_{ym}.parquet"
        print(f"Checking {url}")
        try:
            size = remote_size(url)
        except (HTTPError, URLError) as exc:
            print(f"  unavailable: {exc}")
            results.append({"file": str(file_path), "url": url, "status": "unavailable", "bytes": 0})
            continue
        if size is None:
            print("  unavailable: 404")
            results.append({"file": str(file_path), "url": url, "status": "unavailable", "bytes": 0})
            continue
        results.append(download_file(url, file_path, size))

    manifest_json = output_dir / f"{args.dataset}_download_manifest.json"
    manifest_csv = output_dir / f"{args.dataset}_download_manifest.csv"
    manifest_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    with manifest_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file", "url", "status", "bytes"])
        writer.writeheader()
        writer.writerows(results)

    downloaded = [row for row in results if row["status"] in {"downloaded", "skipped"}]
    total_bytes = sum(int(row["bytes"]) for row in downloaded)
    print(f"Ready files: {len(downloaded)}")
    print(f"Total size: {total_bytes / 1024 / 1024 / 1024:.2f} GB")
    print(f"Manifest: {manifest_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
