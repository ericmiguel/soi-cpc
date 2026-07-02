# CPC SOI — Southern Oscillation Index

Fetches the standardized SOI from CPC, stores locally as CSV, and
generates a time-series chart and a monthly heatmap.

![Time series](output/soi_timeseries.png)

## Usage

```bash
# first use
uv sync 

# fetch, parse and plot
uv run soi
```

Run again to pick up new monthly data. Only new rows are appended.

## Outputs

| Path | Description |
|---|---|
| `data/soi.csv` | Local cache |
| `output/soi_timeseries.png` | Line chart with area fill |
| `output/soi_heatmap.png` | Year × month heatmap |

## Development

```bash
uv run ruff check
uv run pyrefly
uv run pytest
```
