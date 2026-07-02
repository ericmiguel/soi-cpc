"""Pipeline orchestration: fetch -> parse -> store -> chart."""

from __future__ import annotations

import logging

from soi.charts import monthly_heatmap
from soi.charts import time_series
from soi.config import CSV_PATH
from soi.data import fetch_raw_soi
from soi.data import load
from soi.data import merge
from soi.data import parse_soi
from soi.data import save

log = logging.getLogger(__name__)


def run() -> None:
    """Execute the full SOI pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    log.info("Fetching SOI data from CPC...")
    raw = fetch_raw_soi()

    log.info("Parsing raw data...")
    fresh = parse_soi(raw)
    log.info("Parsed %d rows", len(fresh))

    stored = load()
    merged, new_count = merge(stored, fresh)
    log.info("Merge result: %d new rows -> %d total", new_count, len(merged))

    if new_count > 0:
        save(merged)
        log.info("Saved to %s", CSV_PATH)
    else:
        log.info("No new data - CSV unchanged.")

    log.info("Generating charts...")
    out_ts = time_series(merged)
    log.info("  -> %s", out_ts)
    out_hm = monthly_heatmap(merged)
    log.info("  -> %s", out_hm)

    log.info("Done")


if __name__ == "__main__":
    run()
