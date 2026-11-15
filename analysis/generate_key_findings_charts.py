"""Generate key-findings charts from the November 15 cleaning checkpoint.

These charts summarize what the cleaning process currently supports for the
project objective: finding unusual extracted annual-rate candidates overall
and within comparable certificate-period, rank, and service-duration groups.
Rows remain candidate pages, not verified awards or payments. Missing values
are never treated as zero, and all event statuses remain in scope.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from textwrap import fill

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "smithsonian_matplotlib")
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = (
    ROOT
    / "search_results"
    / "widow_pension_cleaning_checkpoint_20261115_100002.csv"
)
OUTPUT = ROOT / "outputs" / "key_findings_charts"

PERIOD_ORDER = [
    "Before 1836-07-04",
    "1836-07-04 to 1838-07-06",
    "1838-07-07 to 1843-03-02",
    "1843-03-03 to 1844-06-16",
    "1844-06-17 to 1848-02-01",
    "1848-02-02 to 1848-07-28",
    "1848-07-29 to 1853-02-02",
    "1853-02-03 onward",
    "Certificate date unresolved",
]

PERIOD_LABELS = {
    "Before 1836-07-04": "Before Jul. 4, 1836",
    "1836-07-04 to 1838-07-06": "Jul. 1836 to Jul. 1838",
    "1838-07-07 to 1843-03-02": "Jul. 1838 to Mar. 1843",
    "1843-03-03 to 1844-06-16": "Mar. 1843 to Jun. 1844",
    "1844-06-17 to 1848-02-01": "Jun. 1844 to Feb. 1848",
    "1848-02-02 to 1848-07-28": "Feb. 1848 to Jul. 1848",
    "1848-07-29 to 1853-02-02": "Jul. 1848 to Feb. 1853",
    "1853-02-03 onward": "Feb. 1853 onward",
    "Certificate date unresolved": "Certificate date unresolved",
}

COLORS = {
    "navy": "#17324D",
    "blue": "#3D6F9E",
    "teal": "#1F7A70",
    "gold": "#D8A43B",
    "rust": "#C75B46",
    "ink": "#1D2935",
    "gray": "#667581",
    "light": "#E6EBEC",
    "track": "#E2E7E8",
    "paper": "#F7F5F1",
    "white": "#FFFFFF",
}

DOLLARS = FuncFormatter(lambda value, _pos: f"${value:,.0f}")
SLIDE_SIZE = (12.8, 7.2)
OUTPUT_DPI = 250

# Shared slide grid. Keeping these anchors in one place makes the three
# figures line up when they are viewed sequentially or placed in a deck.
PAGE_LEFT = 0.065
PAGE_RIGHT = 0.935
CHART_TOP = 0.68
CHART_BOTTOM = 0.18
SINGLE_CHART_LEFT = 0.28

plt.rcParams.update(
    {
        "font.family": "Avenir Next",
        "font.size": 10,
        "axes.titleweight": 600,
        "axes.labelcolor": COLORS["ink"],
        "xtick.color": COLORS["gray"],
        "ytick.color": COLORS["ink"],
        "text.color": COLORS["ink"],
        "figure.facecolor": COLORS["paper"],
        "axes.facecolor": COLORS["paper"],
        "savefig.facecolor": COLORS["paper"],
    }
)


def load_checkpoint() -> pd.DataFrame:
    if not INPUT.exists():
        raise FileNotFoundError(f"Required checkpoint not found: {INPUT}")
    data = pd.read_csv(INPUT, low_memory=False)
    if data.shape != (40058, 70):
        raise ValueError(f"Expected checkpoint shape (40058, 70); found {data.shape}")
    data["annual_amount_numeric"] = pd.to_numeric(
        data["annual_amount_numeric"], errors="coerce"
    )
    data["certificate_issue_date_parsed"] = pd.to_datetime(
        data["certificate_issue_date"], errors="coerce"
    )
    return data


def header(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(
        PAGE_LEFT,
        0.955,
        "SMITHSONIAN WIDOW-PENSION PROJECT  /  DATA CLEANING",
        ha="left",
        va="top",
        fontsize=8.3,
        fontweight=600,
        color=COLORS["teal"],
    )
    fig.text(
        PAGE_LEFT,
        0.895,
        title,
        ha="left",
        va="top",
        fontsize=22,
        fontweight=600,
        color=COLORS["navy"],
    )
    fig.text(
        PAGE_LEFT,
        0.812,
        fill(subtitle, 125),
        ha="left",
        va="top",
        fontsize=10.2,
        color=COLORS["gray"],
        linespacing=1.25,
    )
    fig.add_artist(
        plt.Line2D(
            [PAGE_LEFT, PAGE_RIGHT],
            [0.755, 0.755],
            transform=fig.transFigure,
            color=COLORS["light"],
            linewidth=1.0,
        )
    )


def footer(fig: plt.Figure, note: str) -> None:
    fig.add_artist(
        plt.Line2D(
            [PAGE_LEFT, PAGE_RIGHT],
            [0.105, 0.105],
            transform=fig.transFigure,
            color=COLORS["light"],
            linewidth=1.0,
        )
    )
    fig.text(
        PAGE_LEFT,
        0.073,
        fill(note, 150),
        ha="left",
        va="top",
        fontsize=7.9,
        color=COLORS["gray"],
        linespacing=1.2,
    )


def style(ax: plt.Axes, axis: str = "x") -> None:
    ax.set_facecolor(COLORS["paper"])
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.grid(axis=axis, color=COLORS["light"], linewidth=0.75)
    ax.set_axisbelow(True)
    ax.tick_params(colors=COLORS["gray"], labelsize=9, length=0, pad=7)


def build_summaries(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    total = len(data)
    amount = data["annual_amount_numeric"]
    date = data["certificate_issue_date_parsed"]
    duration = data["service_duration_group"].ne("duration_unresolved")
    rank = data["veteran_rank"].notna()

    readiness_rows = [
        ("All candidate pages", total, "baseline"),
        ("Resolved rank", int(rank.sum()), "individual"),
        ("Usable certificate date", int(date.notna().sum()), "individual"),
        ("Provisional widow ID", int(data["widow_id"].notna().sum()), "individual"),
        ("Numeric amount", int(amount.notna().sum()), "individual"),
        ("Resolved service duration", int(duration.sum()), "individual"),
        ("Amount + date", int((amount.notna() & date.notna()).sum()), "intersection"),
        (
            "Amount + date + duration",
            int((amount.notna() & date.notna() & duration).sum()),
            "intersection",
        ),
        (
            "Amount + date + duration + rank",
            int((amount.notna() & date.notna() & duration & rank).sum()),
            "intersection",
        ),
    ]
    readiness = pd.DataFrame(readiness_rows, columns=["measure", "records", "type"])
    readiness["percent_of_all_pages"] = 100 * readiness["records"] / total

    widow_data = data.dropna(subset=["widow_id"])
    widow_unique = widow_data.groupby("widow_id")["annual_amount_numeric"].nunique()
    widow_status = pd.DataFrame(
        {
            "amount_status": [
                "No numeric amount",
                "One distinct numeric amount",
                "Multiple distinct numeric amounts",
            ],
            "provisional_widow_groups": [
                int(widow_unique.eq(0).sum()),
                int(widow_unique.eq(1).sum()),
                int(widow_unique.gt(1).sum()),
            ],
        }
    )
    widow_status["percent_of_groups"] = (
        100 * widow_status["provisional_widow_groups"] / len(widow_unique)
    )

    period_rows = []
    for period in PERIOD_ORDER:
        group = data.loc[data["certificate_period_display"].eq(period)]
        values = group["annual_amount_numeric"].dropna()
        period_rows.append(
            {
                "certificate_period": period,
                "candidate_pages": len(group),
                "numeric_amounts": len(values),
                "missing_amounts": group["annual_amount_numeric"].isna().sum(),
                "numeric_availability_pct": 100 * len(values) / len(group),
                "mean": values.mean(),
                "median": values.median(),
                "minimum": values.min(),
                "maximum": values.max(),
            }
        )
    periods = pd.DataFrame(period_rows)

    numeric = amount.dropna()
    distribution = pd.DataFrame(
        [
            {
                "numeric_candidates": len(numeric),
                "mean": numeric.mean(),
                "median": numeric.median(),
                "minimum": numeric.min(),
                "q1": numeric.quantile(0.25),
                "q3": numeric.quantile(0.75),
                "p90": numeric.quantile(0.90),
                "p95": numeric.quantile(0.95),
                "p99": numeric.quantile(0.99),
                "maximum": numeric.max(),
                "above_p99": numeric.gt(numeric.quantile(0.99)).sum(),
                "zero_amounts": numeric.eq(0).sum(),
                "below_100": numeric.lt(100).sum(),
                "below_100_pct": 100 * numeric.lt(100).mean(),
            }
        ]
    )
    return {
        "readiness": readiness,
        "widow_status": widow_status,
        "periods": periods,
        "distribution": distribution,
    }


def chart_readiness(readiness: pd.DataFrame) -> plt.Figure:
    plot = readiness.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(plot))

    fig, ax = plt.subplots(figsize=SLIDE_SIZE, facecolor=COLORS["paper"])
    fig.subplots_adjust(
        left=SINGLE_CHART_LEFT,
        right=PAGE_RIGHT,
        top=CHART_TOP,
        bottom=CHART_BOTTOM,
    )
    header(
        fig,
        "Only 5.5% of pages can support the most detailed comparison",
        "To compare possible pension amounts among similar cases, a page needs four usable fields: an amount, a certificate date, a service length, and a military rank.",
    )

    plain_labels = {
        "All candidate pages": "All candidate pages",
        "Resolved rank": "Military rank available",
        "Usable certificate date": "Certificate date available",
        "Provisional widow ID": "Widow group assigned",
        "Numeric amount": "Numeric amount available",
        "Resolved service duration": "Service length available",
        "Amount + date": "Amount + date",
        "Amount + date + duration": "Amount + date + service length",
        "Amount + date + duration + rank": "Amount + date + service length + rank",
    }
    bar_colors = {
        "All candidate pages": COLORS["navy"],
        "Resolved rank": COLORS["teal"],
        "Usable certificate date": COLORS["teal"],
        "Provisional widow ID": COLORS["teal"],
        "Numeric amount": COLORS["teal"],
        "Resolved service duration": COLORS["teal"],
        "Amount + date": COLORS["blue"],
        "Amount + date + duration": COLORS["gold"],
        "Amount + date + duration + rank": COLORS["rust"],
    }

    ax.barh(y, 100, color=COLORS["track"], height=0.46, zorder=1)
    ax.barh(
        y,
        plot["percent_of_all_pages"],
        color=[bar_colors[value] for value in plot["measure"]],
        height=0.46,
        zorder=2,
    )
    ax.set_yticks(y, [plain_labels[value] for value in plot["measure"]])
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(PercentFormatter(100))
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Share of all 40,058 candidate pages", fontsize=8.7, labelpad=10)
    ax.axhline(2.5, color=COLORS["light"], linewidth=1.2, zorder=0)
    for index, row in plot.iterrows():
        value = row["percent_of_all_pages"]
        label_inside = value >= 86
        ax.text(
            value - 1.2 if label_inside else value + 1.2,
            index,
            f"{value:.1f}%   {int(row['records']):,}",
            va="center",
            ha="right" if label_inside else "left",
            fontsize=8.5,
            fontweight=600 if value <= 8.5 or label_inside else 400,
            color=COLORS["white"] if label_inside else COLORS["ink"],
        )
    style(ax)

    footer(
        fig,
        "What this means: only 2,192 of 40,058 pages contain all four fields needed to compare amounts within similar period, service-length, and rank groups. The other pages remain in the data; missing information does not mean a record is ordinary or unimportant.",
    )
    return fig


def chart_widow_groups(widow_status: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=SLIDE_SIZE, facecolor=COLORS["paper"])
    fig.subplots_adjust(
        left=SINGLE_CHART_LEFT,
        right=PAGE_RIGHT,
        top=CHART_TOP,
        bottom=CHART_BOTTOM,
    )
    header(
        fig,
        "Half of the provisional widow groups have no usable amount",
        "Pages that appear to concern the same widow within one pension file are placed in a provisional group. This helps organize repeated paperwork, but it does not verify a person or establish an award history.",
    )

    left = widow_status.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(left))
    colors = [COLORS["rust"], COLORS["blue"], COLORS["light"]]
    ax.barh(y, left["provisional_widow_groups"], color=colors, height=0.44)
    ax.set_yticks(
        y,
        [
            "More than one different amount",
            "One amount",
            "No usable amount",
        ],
    )
    ax.set_title(
        "15,518 provisional widow groups",
        fontsize=11.5,
        color=COLORS["navy"],
        loc="left",
        pad=14,
    )
    ax.set_xlabel("Number of provisional widow groups", fontsize=8.7, labelpad=10)
    ax.set_xlim(0, 8000)
    ax.set_xticks([0, 2000, 4000, 6000, 8000])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:,.0f}"))
    for index, row in left.iterrows():
        value = row["provisional_widow_groups"]
        inside = value > 1500
        ax.text(
            value - 120 if inside else value + 120,
            index,
            f"{int(row['provisional_widow_groups']):,}\n({row['percent_of_groups']:.1f}%)",
            va="center",
            ha="right" if inside else "left",
            fontsize=9,
            fontweight=600,
            color="white" if inside and value < 7500 else COLORS["ink"],
        )
    style(ax)

    footer(
        fig,
        "What this means: 7,815 groups have no numeric amount to compare. Another 858 contain more than one different amount. Those differences may reflect legitimate changes, reissued paperwork, repeated evidence, or extraction problems; they are leads for later review, not findings of error.",
    )
    return fig


def chart_periods(periods: pd.DataFrame) -> plt.Figure:
    plot = periods.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(plot))
    fig, ax = plt.subplots(figsize=SLIDE_SIZE, facecolor=COLORS["paper"])
    fig.subplots_adjust(
        left=SINGLE_CHART_LEFT,
        right=PAGE_RIGHT,
        top=CHART_TOP,
        bottom=CHART_BOTTOM,
    )
    header(
        fig,
        "Usable amount evidence varies sharply across certificate periods",
        "Each bar includes every candidate page assigned to that period. Green shows pages with a numeric extracted annual-rate candidate; gray shows pages where no numeric amount was available.",
    )

    numeric_pct = plot["numeric_availability_pct"]
    missing_pct = 100 - numeric_pct
    ax.barh(y, numeric_pct, color=COLORS["teal"], height=0.48, label="Numeric amount available")
    ax.barh(
        y,
        missing_pct,
        left=numeric_pct,
        color=COLORS["light"],
        edgecolor="#CDD5DC",
        linewidth=0.5,
        height=0.48,
        label="No numeric amount",
    )
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(PercentFormatter(100))
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Share of candidate pages in each period", fontsize=8.7, labelpad=10)
    ax.set_yticks(y, [PERIOD_LABELS[value] for value in plot["certificate_period"]])
    for index, row in plot.iterrows():
        ax.text(
            min(row["numeric_availability_pct"] + 1.2, 83),
            index,
            f"{row['numeric_availability_pct']:.1f}%  ({int(row['numeric_amounts']):,} of {int(row['candidate_pages']):,} pages)",
            va="center",
            fontsize=8.5,
            fontweight=600,
        )
    ax.legend(
        frameon=False,
        ncol=2,
        loc="lower right",
        bbox_to_anchor=(1, 1.04),
        fontsize=8.8,
    )
    style(ax)

    footer(
        fig,
        "What this means: the share of pages with a usable amount ranges from 24.5% to 60.0%, so comparisons across periods rest on uneven evidence. The unresolved-date group remains visible. Periods use certificate issue dates; commencement dates and governing law are separate fields.",
    )
    return fig


def chart_distribution(data: pd.DataFrame, distribution: pd.DataFrame) -> plt.Figure:
    values = data["annual_amount_numeric"].dropna().to_numpy(dtype=float)
    row = distribution.iloc[0]
    p99 = float(row["p99"])
    maximum = float(row["maximum"])

    fig, axes = plt.subplots(1, 2, figsize=(11, 8.5), facecolor=COLORS["paper"])
    fig.subplots_adjust(left=0.09, right=0.97, top=0.79, bottom=0.16, wspace=0.17)
    header(
        fig,
        "Most extracted amounts are under $100",
        f"Of 15,991 pages with a numeric amount candidate, {row['below_100_pct']:.1f}% are below \\$100. The midpoint is \\${row['median']:,.0f}; the 99th percentile is \\${p99:,.0f}, while the maximum is \\${maximum:,.0f}.",
    )

    axes[0].hist(values, bins=np.arange(0, maximum + 50, 50), color=COLORS["blue"], alpha=0.88)
    axes[0].set_yscale("log")
    axes[0].set_xlim(0, maximum)
    axes[0].set_title("All values: compressed vertical scale reveals rare highs", fontsize=11, color=COLORS["navy"], pad=12)
    axes[0].set_ylabel("Candidate pages per $50 bin (log scale)", fontsize=8.5)
    axes[0].xaxis.set_major_formatter(DOLLARS)
    axes[0].set_xticks(np.arange(0, maximum + 1, 500))

    detail = values[values <= p99]
    axes[1].hist(detail, bins=np.arange(0, p99 + 10, 10), color=COLORS["teal"], alpha=0.88)
    axes[1].set_xlim(0, p99)
    axes[1].set_title(f"The main cluster: \\$0 to \\${p99:,.0f}", fontsize=11, color=COLORS["navy"], pad=12)
    axes[1].set_ylabel("Candidate pages per $10 bin", fontsize=8.5)
    axes[1].xaxis.set_major_formatter(DOLLARS)
    axes[1].set_xticks(np.arange(0, p99 + 1, 100))

    for axis in axes:
        axis.axvline(row["median"], color=COLORS["gold"], linewidth=2.2, label=f"Median ${row['median']:,.0f}")
        axis.axvline(row["mean"], color=COLORS["rust"], linewidth=2.2, linestyle="--", label=f"Mean ${row['mean']:,.2f}")
        axis.set_xlabel("Extracted annual-rate candidate", fontsize=8.5)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", color=COLORS["light"], linewidth=0.8)
        axis.set_axisbelow(True)
        axis.legend(frameon=False, fontsize=8)

    axes[0].annotate(
        f"Maximum ${maximum:,.0f}",
        xy=(maximum, 1),
        xytext=(maximum - 630, 3.5),
        arrowprops={"arrowstyle": "->", "color": COLORS["rust"]},
        fontsize=8,
        color=COLORS["rust"],
    )
    axes[1].text(
        0.98,
        0.95,
        f"{int(row['above_p99']):,} candidates above ${p99:,.0f}\nremain in the full-range panel",
        transform=axes[1].transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color=COLORS["rust"],
    )
    footer(
        fig,
        "What this means: most extracted candidates cluster at lower values, while a small number extend much higher. The $525 line is a descriptive percentile, not an anomaly rule. The charts retain zeros, high values, and all event statuses; none of these amounts is treated as a verified rate or payment.",
    )
    return fig


def validate(data: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> pd.DataFrame:
    readiness = summaries["readiness"].set_index("measure")["records"]
    widow = summaries["widow_status"]
    periods = summaries["periods"]
    distribution = summaries["distribution"].iloc[0]
    checks = [
        ("checkpoint rows", len(data), 40058),
        ("checkpoint source columns", len(data.columns) - 1, 70),
        ("numeric amounts", readiness["Numeric amount"], 15991),
        ("amount and date", readiness["Amount + date"], 11104),
        ("complete comparison fields", readiness["Amount + date + duration + rank"], 2192),
        ("provisional widow groups", widow["provisional_widow_groups"].sum(), 15518),
        (
            "groups with multiple distinct amounts",
            widow.loc[widow["amount_status"].eq("Multiple distinct numeric amounts"), "provisional_widow_groups"].iloc[0],
            858,
        ),
        ("period rows sum", periods["candidate_pages"].sum(), 40058),
        ("period numeric sum", periods["numeric_amounts"].sum(), 15991),
        ("distribution maximum", distribution["maximum"], 2100.0),
        ("distribution p99", distribution["p99"], 525.0),
        ("amounts below 100", distribution["below_100"], 13976),
    ]
    result = pd.DataFrame(checks, columns=["check", "observed", "expected"])
    result["status"] = np.where(result["observed"].eq(result["expected"]), "PASS", "FAIL")
    if not result["status"].eq("PASS").all():
        raise AssertionError(result.loc[result["status"].eq("FAIL")].to_string(index=False))
    return result


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    data = load_checkpoint()
    summaries = build_summaries(data)
    validation = validate(data, summaries)

    summaries["readiness"].to_csv(OUTPUT / "analysis_readiness_summary.csv", index=False)
    summaries["widow_status"].to_csv(OUTPUT / "widow_group_amount_status.csv", index=False)
    summaries["periods"].to_csv(OUTPUT / "period_key_findings_summary.csv", index=False)
    validation.to_csv(OUTPUT / "key_findings_validation.csv", index=False)

    figures = [
        (chart_readiness(summaries["readiness"]), "01_analysis_readiness.png"),
        (
            chart_widow_groups(summaries["widow_status"]),
            "02_provisional_widow_groups.png",
        ),
        (chart_periods(summaries["periods"]), "03_period_evidence_and_center.png"),
    ]
    for figure, filename in figures:
        figure.savefig(
            OUTPUT / filename,
            dpi=OUTPUT_DPI,
            facecolor=figure.get_facecolor(),
            bbox_inches=None,
        )
        plt.close(figure)

    print(f"Input: {INPUT}")
    print(f"Output: {OUTPUT}")
    print("Key comparison-ready rows: 2,192")
    print(f"Validation checks passed: {len(validation)}")


if __name__ == "__main__":
    main()
