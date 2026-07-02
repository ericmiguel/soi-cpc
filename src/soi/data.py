"""Acquisition, parsing, persistence and domain model for SOI data."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING
from typing import Final

import httpx

from soi.config import CSV_PATH
from soi.config import MISSING_VALUE
from soi.config import SOURCE_URL
from soi.config import TIMEOUT_S

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SOIRecord:
    """A single monthly observation of the standardized SOI.

    Attributes
    ----------
    date : datetime.date
        First day of the observation month, used as the temporal anchor
        for the index value.
    value : float
        Standardized SOI value (dimensionless), computed as the
        normalized sea-level pressure difference (Tahiti - Darwin).
        Positive values indicate La Niña conditions; negative values
        indicate El Niño conditions.
    """

    date: date
    value: float


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


def fetch_raw_soi() -> str:
    """Download the raw SOI text file from CPC.

    Returns
    -------
    str
        Full plain-text content of the SOI data file served by CPC,
        containing both the anomaly and the standardized table.

    Raises
    ------
    httpx.HTTPStatusError
        If the server returns a non-2xx status code.
    httpx.ConnectError
        If the server is unreachable or the connection times out.
    """
    response = httpx.get(SOURCE_URL, follow_redirects=True, timeout=TIMEOUT_S)
    response.raise_for_status()
    return response.text


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def parse_soi(raw: str) -> list[SOIRecord]:
    """Parse the standardized section of the CPC SOI file.

    Parameters
    ----------
    raw : str
        Full plain-text content as returned by :func:`fetch_raw_soi`.
        Must contain two ``YEAR``-header blocks (anomaly then standardized).

    Returns
    -------
    list[SOIRecord]
        One record per valid observation month. Rows where the original
        value equals ``MISSING_VALUE`` (``-999.9``) are silently dropped.
        The list is sorted chronologically by date.
    """
    header_index: Final = 1  # second block = standardized
    blocks = _split_blocks(raw)
    return _parse_block(blocks[header_index])


def _split_blocks(raw: str) -> list[str]:
    """Split the raw file into the two variant blocks by ``YEAR`` header.

    Parameters
    ----------
    raw : str
        Full plain-text content of the CPC SOI file.

    Returns
    -------
    list[str]
        Two strings — anomaly block at index 0, standardized block at index 1.

    Raises
    ------
    ValueError
        If the file does not contain exactly two ``YEAR`` header lines.
    """
    expected_blocks: Final = 2
    lines = raw.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if line.strip().startswith("YEAR")]
    if len(indices) != expected_blocks:
        msg = f"Expected 2 YEAR header lines, found {len(indices)}"
        raise ValueError(msg)
    return [
        "".join(lines[start:end])
        for start, end in zip(indices, [*indices[1:], len(lines)], strict=True)
    ]


def _parse_block(block: str) -> list[SOIRecord]:
    """Convert one fixed-width text block into a sorted list of records.

    Parameters
    ----------
    block : str
        Text block starting with a ``YEAR   JAN   FEB ...`` header,
        followed by one space-separated data line per year.

    Returns
    -------
    list[SOIRecord]
        Chronologically sorted records. Observations whose raw value equals
        ``MISSING_VALUE`` (``-999.9``) are excluded.
    """
    float_re: Final = re.compile(r"-?\d+\.\d+")
    months_per_year: Final = 12
    rows: list[SOIRecord] = []
    for line in block.splitlines():
        year_match = re.match(r"^\s*(\d{4})", line)
        if not year_match:
            continue
        year = int(year_match.group(1))
        values = [float(v) for v in float_re.findall(line)]
        if len(values) != months_per_year:
            continue
        for month_idx, value in enumerate(values):
            if value != MISSING_VALUE:
                rows.append(SOIRecord(date(year, month_idx + 1, 1), value))
    rows.sort(key=lambda r: r.date)
    return rows


# ---------------------------------------------------------------------------
# Persistence — CSV
# ---------------------------------------------------------------------------


def load(path: Path | None = None) -> list[SOIRecord] | None:
    """Load the previously persisted SOI records from the local CSV file.

    Returns
    -------
    list[SOIRecord] or None
        The full record list decoded from ``CSV_PATH``, or ``None``
        if no CSV file exists yet (first run / no data stored).
    """
    csv_path = path or CSV_PATH
    if not csv_path.exists():
        return None
    with csv_path.open(newline="") as f:
        return [
            SOIRecord(date.fromisoformat(row["date"]), float(row["value"]))
            for row in csv.DictReader(f)
        ]


def save(
    records: Sequence[SOIRecord],
    path: Path | None = None,
) -> None:
    """Persist a sequence of SOI records to the local CSV file.

    Overwrites the file at ``CSV_PATH`` with the full content of
    *records*, creating the data directory if necessary.

    Parameters
    ----------
    records : Sequence[SOIRecord]
        Records to write. Each record produces one CSV row with
        columns ``date`` (ISO-8601) and ``value``.
    """
    csv_path = path or CSV_PATH
    csv_header: Final = ["date", "value"]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_header)
        writer.writeheader()
        for r in records:
            writer.writerow({"date": r.date.isoformat(), "value": r.value})


def merge(
    stored: list[SOIRecord] | None,
    fresh: list[SOIRecord],
) -> tuple[list[SOIRecord], int]:
    """Merge freshly parsed records into the stored dataset.

    Deduplication is performed on ``date`` — if the same month appears
    in both *stored* and *fresh*, the fresh value wins (useful for
    corrections published by CPC).  The merge is idempotent: running
    it twice with the same inputs produces the same result.

    Parameters
    ----------
    stored : list[SOIRecord] or None
        Previously persisted records, or ``None`` if no local data
        exists yet.
    fresh : list[SOIRecord]
        Records just parsed from the CPC source, superseding any
        conflicting dates in *stored*.

    Returns
    -------
    merged : list[SOIRecord]
        Sorted, deduplicated union of *stored* and *fresh*.
    new_count : int
        Number of records in *fresh* whose ``date`` was **not**
        present in *stored* (i.e. genuinely new observations).
    """
    if stored is None:
        return fresh, len(fresh)

    stored_by_date = {r.date: r.value for r in stored}
    genuinely_new = [r for r in fresh if r.date not in stored_by_date]
    new_count = len(genuinely_new)

    stored_by_date.update({r.date: r.value for r in fresh})
    merged = sorted(
        (SOIRecord(d, v) for d, v in stored_by_date.items()),
        key=lambda r: r.date,
    )
    return merged, new_count
