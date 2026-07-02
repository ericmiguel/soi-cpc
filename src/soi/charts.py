"""Plotnine visualizations for the standardized SOI."""

from __future__ import annotations

import calendar
from typing import TYPE_CHECKING

import pandas as pd
from plotnine import aes
from plotnine import element_blank
from plotnine import element_text
from plotnine import geom_area
from plotnine import geom_hline
from plotnine import geom_line
from plotnine import geom_tile
from plotnine import ggplot
from plotnine import labs
from plotnine import scale_fill_gradient2
from plotnine import scale_x_date
from plotnine import scale_y_continuous
from plotnine import theme
from plotnine import theme_minimal

from soi.config import CHART_DPI
from soi.config import CHART_HEIGHT
from soi.config import CHART_WIDTH
from soi.config import DASHED_GRAY
from soi.config import NEGATIVE_FILL
from soi.config import OUTPUT_DIR
from soi.config import POSITIVE_FILL
from soi.config import SUB
from soi.config import SUB_SIZE
from soi.config import TITLE
from soi.config import TITLE_SIZE

if TYPE_CHECKING:
    from pathlib import Path

    from soi.data import SOIRecord


def _save(p: ggplot, path: Path, *, dpi: int = CHART_DPI) -> None:
    """Render a plotnine figure to a PNG file.

    Creates all parent directories of *path* if they do not exist.

    Parameters
    ----------
    p : ggplot
        Fully built plotnine figure to render.
    path : Path
        Destination file path (``.png`` extension expected).
    dpi : int, optional
        Output resolution in dots per inch. Defaults to ``CHART_DPI``
        (150 in the current configuration).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    p.save(path, dpi=dpi, verbose=False)


# ---------------------------------------------------------------------------
# Time-series
# ---------------------------------------------------------------------------


def time_series(
    records: list[SOIRecord],
    *,
    output_path: Path | None = None,
) -> Path:
    """Line chart of the standardized SOI with diverging area fill.

    Draws a single time-series line over the full date range of
    *records*.  The area below the line is filled in two colours:
    blue for positive values (La Niña) and red for negative values
    (El Niño), with the zero line shown as a dashed grey reference.

    Parameters
    ----------
    records : list[SOIRecord]
        Chronologically sorted SOI observations to plot.  Each record
        contributes one point on the time axis.
    output_path : Path, optional
        Where to save the PNG.  Defaults to
        ``<OUTPUT_DIR>/soi_timeseries.png``.

    Returns
    -------
    Path
        Absolute path to the saved PNG file.
    """
    out = output_path or (OUTPUT_DIR / "soi_timeseries.png")

    pdf = pd.DataFrame([(r.date, r.value) for r in records], columns=["date", "value"])
    pdf["positive"] = pdf["value"].clip(lower=0)
    pdf["negative"] = pdf["value"].clip(upper=0)

    p = (
        ggplot(pdf, aes("date", group=1))
        + geom_area(aes(y="positive"), fill=POSITIVE_FILL, alpha=0.35)
        + geom_area(aes(y="negative"), fill=NEGATIVE_FILL, alpha=0.35)
        + geom_line(aes(y="value"), color="black", size=0.35)
        + geom_hline(yintercept=0, linetype="dashed", color=DASHED_GRAY)
        + labs(title=TITLE, subtitle=SUB, x=None, y=None)
        + scale_x_date(date_breaks="10 years", date_labels="%b/%Y")
        + theme_minimal()
        + theme(
            figure_size=(CHART_WIDTH, CHART_HEIGHT),
            axis_title_x=element_blank(),
            axis_title_y=element_blank(),
            plot_title=element_text(size=TITLE_SIZE, ha="left", margin={"b": 2}),
            plot_subtitle=element_text(size=SUB_SIZE, ha="left", color=DASHED_GRAY),
        )
    )
    _save(p, out)
    return out


# ---------------------------------------------------------------------------
# Monthly heatmap
# ---------------------------------------------------------------------------


def monthly_heatmap(
    records: list[SOIRecord],
    *,
    output_path: Path | None = None,
) -> Path:
    """Year x month heatmap of the standardized SOI.

    Each cell represents one month, coloured by its SOI value.
    The colour scale diverges at zero: blue for positive (La Niña),
    red for negative (El Niño), white at zero.  Rows are years
    (oldest at the top) and columns are months 1-12.

    Parameters
    ----------
    records : list[SOIRecord]
        SOI observations to plot.  The full date range determines
        the vertical span of the heatmap.
    output_path : Path, optional
        Where to save the PNG.  Defaults to
        ``<OUTPUT_DIR>/soi_heatmap.png``.

    Returns
    -------
    Path
        Absolute path to the saved PNG file.
    """
    out = output_path or (OUTPUT_DIR / "soi_heatmap.png")

    month_abbr = {i: calendar.month_abbr[i] for i in range(1, 13)}

    pdf = pd.DataFrame(
        [(r.date.year, r.date.month, r.value) for r in records],
        columns=["year", "month", "value"],
    )
    pdf["month"] = pd.Categorical(
        pdf["month"].map(month_abbr),
        categories=list(month_abbr.values()),
        ordered=True,
    )

    p = (
        ggplot(pdf, aes("month", "year", fill="value"))
        + geom_tile()
        + scale_fill_gradient2(
            low=NEGATIVE_FILL,
            mid="white",
            high=POSITIVE_FILL,
            midpoint=0,
        )
        + scale_y_continuous(
            breaks=range(
                (records[0].date.year // 10) * 10,
                records[-1].date.year + 10,
                10,
            )
        )
        + labs(title=TITLE, subtitle=SUB, fill="Value")
        + theme_minimal()
        + theme(
            figure_size=(10, 16),
            axis_title_x=element_blank(),
            axis_title_y=element_blank(),
            plot_title=element_text(size=TITLE_SIZE, ha="center"),
            plot_subtitle=element_text(
                size=SUB_SIZE, ha="center", color=DASHED_GRAY
            ),
        )
    )
    _save(p, out)
    return out
