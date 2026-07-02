from __future__ import annotations

from datetime import date

import pytest

from soi.data import SOIRecord
from soi.data import _parse_block
from soi.data import _split_blocks
from soi.data import load
from soi.data import merge
from soi.data import parse_soi
from soi.data import save

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

SAMPLE_BLOCK_A = """\
 YEAR   JAN   FEB   MAR   APR   MAY   JUN   JUL   AUG   SEP   OCT   NOV   DEC
 1951   0.4   0.4   0.6   0.7   0.7   0.9   0.6   0.8   0.9   1.0   1.2   0.9
 1952   0.5  -0.1  -0.4  -0.5  -0.7  -0.7  -0.6  -0.4  -0.4  -0.7  -0.8  -0.9
"""

SAMPLE_BLOCK_B = """\
 YEAR   JAN   FEB   MAR   APR   MAY   JUN   JUL   AUG   SEP   OCT   NOV   DEC
 1951   0.6   0.6   0.8   0.9   0.9   1.1   0.8   1.0   1.1   1.2   1.4   1.1
 1952   0.7   0.1  -0.2  -0.3  -0.5  -0.5  -0.4  -0.2  -0.2  -0.5  -0.6  -0.7
"""

RAW_TWO_BLOCKS = f"{SAMPLE_BLOCK_A}\n{SAMPLE_BLOCK_B}"


def _records_eq(actual: list[SOIRecord], expected: list[SOIRecord]) -> None:
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected, strict=True):
        assert a.date == e.date
        assert a.value == pytest.approx(e.value)


# ---------------------------------------------------------------------------
# _split_blocks
# ---------------------------------------------------------------------------


def test_split_blocks_returns_two_blocks() -> None:
    blocks = _split_blocks(RAW_TWO_BLOCKS)
    assert len(blocks) == 2


def test_split_blocks_first_is_anomaly() -> None:
    blocks = _split_blocks(RAW_TWO_BLOCKS)
    assert " 1951   0.4" in blocks[0]
    assert " 1951   0.6" not in blocks[0]


def test_split_blocks_second_is_standardized() -> None:
    blocks = _split_blocks(RAW_TWO_BLOCKS)
    assert " 1951   0.6" in blocks[1]
    assert " 1951   0.4" not in blocks[1]


def test_split_blocks_wrong_number_of_headers() -> None:
    raw = "YEAR   JAN\n 2000   1.0\n"
    with pytest.raises(ValueError, match="Expected 2 YEAR header lines, found 1"):
        _split_blocks(raw)


# ---------------------------------------------------------------------------
# _parse_block
# ---------------------------------------------------------------------------


def test_parse_block_returns_correct_records() -> None:
    records = _parse_block(SAMPLE_BLOCK_B)
    expected = [
        SOIRecord(date(1951, 1, 1), 0.6),
        SOIRecord(date(1951, 2, 1), 0.6),
        SOIRecord(date(1951, 3, 1), 0.8),
        SOIRecord(date(1951, 4, 1), 0.9),
        SOIRecord(date(1951, 5, 1), 0.9),
        SOIRecord(date(1951, 6, 1), 1.1),
        SOIRecord(date(1951, 7, 1), 0.8),
        SOIRecord(date(1951, 8, 1), 1.0),
        SOIRecord(date(1951, 9, 1), 1.1),
        SOIRecord(date(1951, 10, 1), 1.2),
        SOIRecord(date(1951, 11, 1), 1.4),
        SOIRecord(date(1951, 12, 1), 1.1),
        SOIRecord(date(1952, 1, 1), 0.7),
        SOIRecord(date(1952, 2, 1), 0.1),
        SOIRecord(date(1952, 3, 1), -0.2),
        SOIRecord(date(1952, 4, 1), -0.3),
        SOIRecord(date(1952, 5, 1), -0.5),
        SOIRecord(date(1952, 6, 1), -0.5),
        SOIRecord(date(1952, 7, 1), -0.4),
        SOIRecord(date(1952, 8, 1), -0.2),
        SOIRecord(date(1952, 9, 1), -0.2),
        SOIRecord(date(1952, 10, 1), -0.5),
        SOIRecord(date(1952, 11, 1), -0.6),
        SOIRecord(date(1952, 12, 1), -0.7),
    ]
    _records_eq(records, expected)


def test_parse_block_skips_missing_values() -> None:
    block = (
        " YEAR   JAN   FEB   MAR   APR   MAY   JUN   JUL"
        "   AUG   SEP   OCT   NOV   DEC\n"
        " 2024   1.0  -999.9   2.0  -999.9   3.0  -999.9   4.0"
        "  -999.9   5.0  -999.9   6.0  -999.9\n"
    )
    records = _parse_block(block)
    expected = [
        SOIRecord(date(2024, 1, 1), 1.0),
        SOIRecord(date(2024, 3, 1), 2.0),
        SOIRecord(date(2024, 5, 1), 3.0),
        SOIRecord(date(2024, 7, 1), 4.0),
        SOIRecord(date(2024, 9, 1), 5.0),
        SOIRecord(date(2024, 11, 1), 6.0),
    ]
    _records_eq(records, expected)


def test_parse_block_skips_malformed_lines() -> None:
    block = """\
 YEAR   JAN   FEB   MAR   APR   MAY   JUN   JUL   AUG   SEP   OCT   NOV   DEC
 garbage line
 2024   1.0   2.0   3.0   4.0   5.0   6.0   7.0   8.0   9.0  10.0  11.0  12.0
"""
    records = _parse_block(block)
    assert len(records) == 12
    assert records[0] == SOIRecord(date(2024, 1, 1), 1.0)


def test_parse_block_returns_sorted() -> None:
    block = """\
 YEAR   JAN   FEB   MAR   APR   MAY   JUN   JUL   AUG   SEP   OCT   NOV   DEC
 2000  12.0  11.0  10.0   9.0   8.0   7.0   6.0   5.0   4.0   3.0   2.0   1.0
 1999   1.0   2.0   3.0   4.0   5.0   6.0   7.0   8.0   9.0  10.0  11.0  12.0
"""
    records = _parse_block(block)
    assert records[0].date == date(1999, 1, 1)
    assert records[-1].date == date(2000, 12, 1)


# ---------------------------------------------------------------------------
# parse_soi  (integration)
# ---------------------------------------------------------------------------


def test_parse_soi_returns_standardized_block() -> None:
    records = parse_soi(RAW_TWO_BLOCKS)
    assert records[0].value == pytest.approx(0.6)
    assert records[12].value == pytest.approx(0.7)


def test_parse_soi_sorted() -> None:
    records = parse_soi(RAW_TWO_BLOCKS)
    dates = [r.date for r in records]
    assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# SOIRecord
# ---------------------------------------------------------------------------


def test_soi_record_creation() -> None:
    r = SOIRecord(date(2024, 6, 1), -1.5)
    assert r.date == date(2024, 6, 1)
    assert r.value == -1.5


def test_soi_record_is_frozen() -> None:
    r = SOIRecord(date(2024, 6, 1), -1.5)
    with pytest.raises(AttributeError):
        r.value = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


def test_merge_without_stored() -> None:
    fresh = [SOIRecord(date(2024, 1, 1), 1.0)]
    merged, new_count = merge(None, fresh)
    assert merged == fresh
    assert new_count == 1


def test_merge_with_stored() -> None:
    stored = [SOIRecord(date(2024, 1, 1), 1.0)]
    fresh = [SOIRecord(date(2024, 2, 1), 2.0)]
    merged, new_count = merge(stored, fresh)
    assert len(merged) == 2
    assert new_count == 1


def test_merge_deduplicates_by_date() -> None:
    stored = [SOIRecord(date(2024, 1, 1), 1.0)]
    fresh = [SOIRecord(date(2024, 1, 1), 99.0)]
    merged, new_count = merge(stored, fresh)
    assert len(merged) == 1
    assert merged[0].value == 99.0
    assert new_count == 0


def test_merge_new_count() -> None:
    stored = [SOIRecord(date(2024, 1, 1), 1.0)]
    fresh = [
        SOIRecord(date(2024, 1, 1), 1.0),
        SOIRecord(date(2024, 2, 1), 2.0),
        SOIRecord(date(2024, 3, 1), 3.0),
    ]
    _, new_count = merge(stored, fresh)
    assert new_count == 2


def test_merge_idempotent() -> None:
    stored = [SOIRecord(date(2024, 1, 1), 1.0)]
    fresh = [SOIRecord(date(2024, 2, 1), 2.0)]
    merged1, _ = merge(stored, fresh)
    merged2, _ = merge(stored, fresh)
    assert merged1 == merged2


def test_merge_sorted_output() -> None:
    stored = [SOIRecord(date(2024, 12, 1), 12.0)]
    fresh = [SOIRecord(date(2024, 1, 1), 1.0)]
    merged, _ = merge(stored, fresh)
    dates = [r.date for r in merged]
    assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# save / load  (round-trip)
# ---------------------------------------------------------------------------


def test_save_and_load_roundtrip(tmp_path) -> None:
    records = [
        SOIRecord(date(2024, 1, 1), 1.5),
        SOIRecord(date(2024, 2, 1), -2.5),
    ]
    csv_path = tmp_path / "soi.csv"
    save(records, path=csv_path)

    loaded = load(path=csv_path)
    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0].date == date(2024, 1, 1)
    assert loaded[0].value == 1.5
    assert loaded[1].date == date(2024, 2, 1)
    assert loaded[1].value == -2.5


def test_load_nonexistent_file(tmp_path) -> None:
    csv_path = tmp_path / "nonexistent.csv"
    assert load(path=csv_path) is None


def test_save_is_idempotent(tmp_path) -> None:
    records = [SOIRecord(date(2024, 1, 1), 1.0)]
    csv_path = tmp_path / "soi.csv"
    save(records, path=csv_path)
    save(records, path=csv_path)
    content = csv_path.read_text()
    assert content.count("2024-01-01") == 1


def test_save_creates_directory(tmp_path) -> None:
    records = [SOIRecord(date(2024, 1, 1), 1.0)]
    nested = tmp_path / "sub" / "dir" / "soi.csv"
    save(records, path=nested)
    assert nested.exists()
    loaded = load(path=nested)
    assert loaded is not None
    assert len(loaded) == 1
