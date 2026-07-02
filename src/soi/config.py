"""Centralized configuration for the SOI pipeline."""

from pathlib import Path

# --- Data source ---------------------------------------------------------------

SOURCE_URL: str = "https://www.cpc.ncep.noaa.gov/data/indices/soi"

# HTTP request timeout in seconds.
TIMEOUT_S: float = 30.0

# Sentinel value used in the raw file to indicate missing / future data.
MISSING_VALUE: float = -999.9

# --- Project paths -------------------------------------------------------------

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
DATA_DIR: Path = _PROJECT_ROOT / "output" / "data"
OUTPUT_DIR: Path = _PROJECT_ROOT / "output" / "charts"
CSV_PATH: Path = DATA_DIR / "soi.csv"

# --- Chart styling -------------------------------------------------------------

CHART_WIDTH = 14
CHART_HEIGHT = 5
CHART_DPI = 150
POSITIVE_FILL = "#1976D2"
NEGATIVE_FILL = "#D32F2F"
DASHED_GRAY = "#808080"

TITLE = "CPC SOI"
SUB = (
    "standardized SOI index  |  positive = La Niña (cooler east Pacific),"
    " negative = El Niño (warmer east Pacific)"
)
TITLE_SIZE = 12
SUB_SIZE = 8
