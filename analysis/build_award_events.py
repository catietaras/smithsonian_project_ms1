"""Build provisional widow-pension award events from the existing page extract.

This workflow is intentionally conservative.  A certificate issue date is used
only as a proxy for the administrative award-event period; a commencement date
is retained separately and is never substituted for it.  Exact within-file
certificate duplicates are linked and excluded from analytical counts.
"""

from __future__ import annotations

import html
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "search_results" / "widow_awards_draft_v17.csv"
OUT = ROOT / "outputs"
FIGURES = OUT / "figures"

# Legacy seven-period frame retained to reproduce the current outputs.  Do not
# extend or relabel it silently: the sourced 1780-1899 proposal lives in
# research/proposed_period_boundaries_1780_1899.csv and requires authority-class
# extraction before categories are rebuilt.
LAW_DATES = [
    ("1836-07-04", "Act of July 4, 1836", "5 Stat. 127–128"),
    ("1838-07-07", "Act of July 7, 1838", "5 Stat. 303"),
    ("1843-03-03", "Act of March 3, 1843", "5 Stat. 647"),
    ("1844-06-17", "Act of June 17, 1844", "5 Stat. 680"),
    ("1848-02-02", "Act of February 2, 1848", "9 Stat. 210–211"),
    ("1848-07-29", "Act of July 29, 1848", "9 Stat. 265–266"),
    ("1853-02-03", "Act of February 3, 1853", "10 Stat. 154"),
]

PERIOD_STARTS = pd.to_datetime([row[0] for row in LAW_DATES])
PERIOD_LABELS = []
for index, (start, title, _citation) in enumerate(LAW_DATES):
    if index + 1 < len(LAW_DATES):
        end = PERIOD_STARTS[index + 1] - pd.Timedelta(days=1)
        PERIOD_LABELS.append(f"{start} to {end:%Y-%m-%d} ({title})")
    else:
        PERIOD_LABELS.append(f"{start} onward ({title})")

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "febr": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4, "may": 5,
    "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8,
    "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
    "eleventh": 11, "twelfth": 12, "thirteenth": 13,
    "fourteenth": 14, "fifteenth": 15, "sixteenth": 16,
    "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
    "twentieth": 20, "twenty first": 21, "twenty second": 22,
    "twenty third": 23, "twenty fourth": 24, "twenty fifth": 25,
    "twenty sixth": 26, "twenty seventh": 27, "twenty eighth": 28,
    "twenty ninth": 29, "thirtieth": 30, "thirty first": 31,
}


def clean_text(value: object) -> str:
    return " ".join(str(value if pd.notna(value) else "").split())


def normalize_date_text(value: object) -> str:
    text = clean_text(value).lower().replace("’", "'")
    text = re.sub(r"(?<=[a-z])[- ]+\s*(?=[a-z])", " ", text)
    text = re.sub(r"\bjan(?:uary|[' ]*y)?\b", "january", text)
    text = re.sub(r"\bfeb(?:ruary|r[' ]*y|[' ]*y)?\b", "february", text)
    text = re.sub(r"\bsept(?:ember|[' ]*r)?\b", "september", text)
    for words, day in sorted(ORDINALS.items(), key=lambda item: -len(item[0])):
        text = re.sub(rf"\b{words}\b", str(day), text)
    text = re.sub(r"\b(\d{1,2})\s*(?:st|nd|rd|th|d)\b", r"\1", text)
    return text


def parse_first_date(value: object) -> pd.Timestamp:
    text = normalize_date_text(value)
    match = re.search(
        r"\b(\d{1,2})\s*(?:day\s+of\s+)?"
        r"(january|february|march|april|may|june|july|august|"
        r"september|october|november|december|jan|febr?|mar|apr|"
        r"jun|jul|aug|sept?|oct|nov|dec)\.?\s*[,.:;—–-]*\s*"
        r"((?:17|18|19)\d{2})\b",
        text,
    )
    if not match:
        return pd.NaT
    day, month, year = match.groups()
    try:
        return pd.Timestamp(year=int(year), month=MONTHS[month], day=int(day))
    except ValueError:
        return pd.NaT


def parse_commencement(value: object) -> pd.Timestamp:
    text = clean_text(value)
    text = re.split(r"\b(?:certificate|recorded|new certificate)\b", text,
                    maxsplit=1, flags=re.I)[0]
    return parse_first_date(text)


def legal_period(value: object) -> str:
    if pd.isna(value):
        return "Unassigned — certificate issue date unresolved"
    date = pd.Timestamp(value)
    if date < PERIOD_STARTS[0]:
        return "Before 1836-07-04 — outside seven-period frame"
    index = int(np.searchsorted(PERIOD_STARTS.values, date.to_datetime64(), side="right") - 1)
    return PERIOD_LABELS[index]


def normalize_laws(reviewed: object, draft: object) -> str | pd._libs.missing.NAType:
    source = reviewed if pd.notna(reviewed) and clean_text(reviewed) else draft
    if pd.isna(source) or not clean_text(source):
        return pd.NA
    found: list[str] = []
    for part in clean_text(source).split("|"):
        parsed = pd.to_datetime(part.strip(), errors="coerce")
        if pd.notna(parsed):
            found.append(parsed.strftime("%Y-%m-%d"))
    return " | ".join(dict.fromkeys(found)) if found else pd.NA


def extract_names(text: object) -> tuple[object, object, str]:
    value = clean_text(text)
    matches = list(re.finditer(r"\bwidow\s+of\b", value, flags=re.I))
    if len(matches) != 1:
        return pd.NA, pd.NA, "unresolved_missing_or_multiple_widow_of"
    marker = matches[0]
    veteran_match = re.match(r"\s*([A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){1,4})\s+who\b",
                             value[marker.end():])
    before = value[max(0, marker.start() - 100):marker.start()]
    widow_match = re.search(r"([A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){1,4})\s*$", before)
    widow = widow_match.group(1) if widow_match else pd.NA
    veteran = veteran_match.group(1) if veteran_match else pd.NA
    status = "provisional_ocr_name_pair" if pd.notna(widow) and pd.notna(veteran) else "partial_name_evidence"
    return widow, veteran, status


def extract_service(text: object) -> tuple[object, object, object, object]:
    value = clean_text(text)
    pre_award = re.split(r"\b(?:inscribed|enrolled)\s+on\s+the\s+roll\b",
                         value, maxsplit=1, flags=re.I)[0]
    duration = re.search(
        r"\bfor\s+((?:\d+|[A-Za-z-]+)(?:\s+(?:years?|yrs?|months?|mos?|"
        r"days?|dys?))(?:\s*(?:,|and)?\s*(?:\d+|[A-Za-z-]+)\s+"
        r"(?:years?|yrs?|months?|mos?|days?|dys?))*)",
        pre_award, flags=re.I,
    )
    company = re.search(r"\b(?:company|comp\.?|co\.?)\s+(?:commanded\s+by\s+)?(.{0,80}?)(?=\b(?:of\s+the\s+reg|regiment|line|for)\b|$)", pre_award, flags=re.I)
    regiment = re.search(r"\b(?:regiment|regt\.?)\s+(?:commanded\s+by\s+)?(.{0,80}?)(?=\b(?:in\s+the|line|for)\b|$)", pre_award, flags=re.I)
    unit_line = re.search(r"\b(?:in\s+the\s+)?([A-Z][A-Za-z. ]{1,35}\s+line)\b", pre_award, flags=re.I)
    return (
        duration.group(1).strip(" ,.;") if duration else pd.NA,
        company.group(1).strip(" ,.;_") if company else pd.NA,
        regiment.group(1).strip(" ,.;_") if regiment else pd.NA,
        unit_line.group(1).strip(" ,.;") if unit_line else pd.NA,
    )


def duration_months(value: object) -> float:
    if pd.isna(value):
        return np.nan
    total = 0.0
    found = False
    for number, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(years?|yrs?|months?|mos?|days?|dys?)", str(value), flags=re.I):
        found = True
        n = float(number)
        if unit.lower().startswith(("year", "yr")):
            total += 12 * n
        elif unit.lower().startswith(("month", "mo")):
            total += n
        else:
            total += n / 30.4375
    return total if found else np.nan


def event_status(text: object) -> str:
    value = clean_text(text)
    if re.search(r"\b(?:cancelled|canceled|superseded)\b", value, re.I):
        return "cancelled_or_superseded_record"
    if re.search(r"\b(?:increas(?:e|ed)|decreas(?:e|ed)|reduc(?:e|ed)|change(?:d)?\s+(?:to|from)|additional pension)\b", value, re.I):
        return "change_event_text_cue"
    if re.search(r"\b(?:new certificate|reissu(?:e|ed)|re-issued|reprinted|duplicate certificate)\b", value, re.I):
        return "reissue_event_text_cue"
    return "initial_award_not_established"


def service_group(months: object) -> str:
    if pd.isna(months):
        return "duration_unresolved"
    value = float(months)
    if value < 6:
        return "under_6_months"
    if value < 12:
        return "6_to_under_12_months"
    if value < 24:
        return "12_to_under_24_months"
    return "24_months_or_more"


def build_events() -> pd.DataFrame:
    data = pd.read_csv(INPUT, low_memory=False)
    events = pd.DataFrame(index=data.index)
    events["event_id"] = [f"event_{index + 1:06d}" for index in range(len(data))]
    events["file_id"] = data["file_id"].astype("string")
    events["file_title"] = data["file_title"]
    events["page_number"] = data["page_number"]
    events["page_url"] = data["page_url"]
    events["source_dataset"] = str(INPUT.relative_to(ROOT))

    names = data["text_original"].apply(extract_names).apply(pd.Series)
    names.columns = ["widow_name", "veteran_name", "identity_status"]
    events = pd.concat([events, names], axis=1)
    events["widow_id"] = events.apply(
        lambda row: f"{row.file_id}_widow_01" if pd.notna(row.widow_name) else pd.NA, axis=1)
    events["veteran_id"] = events.apply(
        lambda row: f"{row.file_id}_veteran_01" if pd.notna(row.veteran_name) else pd.NA, axis=1)

    events["annual_pension_amount"] = pd.to_numeric(data["annual_rate_reviewed"], errors="coerce").combine_first(
        pd.to_numeric(data["annual_rate_draft"], errors="coerce"))
    events["amount_evidence"] = data["rate_passage"]
    events["amount_status"] = np.where(data["annual_rate_reviewed"].notna(), "image_reviewed", np.where(
        events["annual_pension_amount"].notna(), "ocr_parsed_unverified", "unresolved"))
    events["veteran_rank"] = data["rank_reviewed"].combine_first(data["rank_draft"])
    events["rank_status"] = np.where(data["rank_reviewed"].notna(), "image_reviewed", np.where(
        events["veteran_rank"].notna(), "ocr_parsed_unverified", "unresolved"))

    service = data["text_original"].apply(extract_service).apply(pd.Series)
    service.columns = ["service_duration_raw", "service_company_raw", "service_regiment_raw", "service_unit_or_line_raw"]
    events = pd.concat([events, service], axis=1)
    events["service_description"] = data["service_description_reviewed"].combine_first(data["service_role_passage_draft"])
    events["service_duration_months_draft"] = events["service_duration_raw"].apply(duration_months)
    events["service_duration_group"] = events["service_duration_months_draft"].apply(service_group)

    events["governing_law_raw"] = data["award_act_date_reviewed"].combine_first(data["award_act_dates_draft"])
    events["governing_law_dates"] = [normalize_laws(reviewed, draft) for reviewed, draft in zip(
        data["award_act_date_reviewed"], data["award_act_dates_draft"])]
    events["governing_law_status"] = np.where(data["award_act_date_reviewed"].notna(), "image_reviewed", np.where(
        events["governing_law_dates"].notna(), "ocr_parsed_unverified", "unresolved"))
    events["certificate_issue_date"] = data["certificate_date_passage"].apply(parse_first_date)
    events["certificate_issue_date_raw"] = data["certificate_date_passage"]
    events["pension_commencement_date"] = data["start_date_reviewed"].apply(parse_first_date).combine_first(
        data["start_date_passage"].apply(parse_commencement))
    events["pension_commencement_date_raw"] = data["start_date_reviewed"].combine_first(data["start_date_passage"])
    events["assigned_legal_period"] = events["certificate_issue_date"].apply(legal_period)
    events["period_assignment_basis"] = np.where(events["certificate_issue_date"].notna(),
        "certificate_issue_date_proxy_for_administrative_event", "unassigned_date_unresolved")
    events["award_occurrence_date_status"] = "not_directly_established_by_current_extract"
    events["event_status"] = data["text_original"].apply(event_status)
    events["extraction_status"] = data["extraction_status"]
    events["review_status"] = data["review_status"]
    events["review_flags"] = data["review_flags"]
    events["image_review_notes"] = data["image_review_notes"]
    events["source_text"] = data["text_original"]

    # Conservative duplicate rule: exact same file, amount, certificate date,
    # commencement date, and stated law; at least the certificate date and
    # amount must be present.  Distinct dates or amounts remain separate events.
    signature_columns = ["file_id", "annual_pension_amount", "certificate_issue_date",
                         "pension_commencement_date", "governing_law_dates"]
    eligible = events["annual_pension_amount"].notna() & events["certificate_issue_date"].notna()
    duplicate = eligible & events.duplicated(signature_columns, keep="first")
    first_ids = events.loc[eligible].groupby(signature_columns, dropna=False)["event_id"].transform("first")
    events["duplicate_of_event_id"] = pd.NA
    events.loc[eligible, "duplicate_of_event_id"] = first_ids
    events.loc[~duplicate, "duplicate_of_event_id"] = pd.NA
    events["duplicate_status"] = np.where(duplicate, "exact_within_file_certificate_duplicate", "not_identified_as_duplicate")

    # File-scoped linkage preserves distinct changes/reissues while exposing the
    # preceding observed (not necessarily preceding historical) event.  This is
    # deliberately not called a person-level chronology.
    events["provisional_case_id"] = "file_" + events["file_id"].astype(str)
    events["previous_observed_event_id"] = pd.NA
    distinct = events.loc[~duplicate, ["file_id", "event_id", "certificate_issue_date", "page_number"]].copy()
    distinct["page_sort"] = pd.to_numeric(distinct["page_number"], errors="coerce")
    distinct = distinct.sort_values(
        ["file_id", "certificate_issue_date", "page_sort"], na_position="last")
    previous = distinct.groupby("file_id")["event_id"].shift()
    events.loc[distinct.index, "previous_observed_event_id"] = previous
    events["event_link_status"] = np.where(
        events["previous_observed_event_id"].notna(),
        "linked_to_previous_observed_distinct_event_in_file",
        "no_previous_observed_distinct_event_in_file",
    )

    disqualifying = data["review_flags"].fillna("").str.contains(
        "possible_heirs_or_administrator|possible_cancellation_or_replacement", regex=True)
    events["analysis_inclusion"] = (
        ~duplicate & ~disqualifying &
        ~events["event_status"].eq("cancelled_or_superseded_record")
    )
    events["analysis_exclusion_reason"] = ""
    events.loc[duplicate, "analysis_exclusion_reason"] = "exact_duplicate"
    events.loc[disqualifying & ~duplicate, "analysis_exclusion_reason"] = "possible_heirs_administrator_or_replacement"
    events.loc[events["event_status"].eq("cancelled_or_superseded_record") & ~duplicate,
               "analysis_exclusion_reason"] = "cancelled_or_superseded"
    return events


def robust_flags(events: pd.DataFrame) -> pd.DataFrame:
    valid = events.loc[
        events["analysis_inclusion"] & events["annual_pension_amount"].notna() &
        events["certificate_issue_date"].notna()
    ].copy()
    valid["iqr_flag"] = False
    valid["mad_flag"] = False
    valid["period_n"] = 0
    valid["period_median"] = np.nan
    valid["period_iqr"] = np.nan
    valid["period_mad"] = np.nan
    for period, group in valid.groupby("assigned_legal_period", observed=True):
        values = group["annual_pension_amount"].astype(float)
        n = len(values)
        q1, q3 = values.quantile([0.25, 0.75])
        iqr = q3 - q1
        median = values.median()
        mad = (values - median).abs().median()
        index = group.index
        valid.loc[index, ["period_n", "period_median", "period_iqr", "period_mad"]] = [n, median, iqr, mad]
        if n >= 8 and iqr > 0:
            valid.loc[index, "iqr_flag"] = (values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)
        if n >= 8 and mad > 0:
            valid.loc[index, "mad_flag"] = (0.6745 * (values - median).abs() / mad) > 3.5
    flagged = valid.loc[valid["iqr_flag"] | valid["mad_flag"]].copy()
    suspicious = flagged["annual_pension_amount"].ge(500) | flagged["review_flags"].fillna("").str.contains("multiple_rates")
    changed = flagged["event_status"].isin(["change_event_text_cue", "reissue_event_text_cue"])
    flagged["research_lead_type"] = np.select(
        [suspicious, changed],
        ["possible_ocr_or_multi_rate_error", "possible_legitimate_change_or_reissue"],
        default="statistical_research_lead_unresolved",
    )
    flagged["flag_limit"] = "exploratory_period_level_flag; not evidence of error, fraud, or illegitimacy"
    columns = [
        "event_id", "file_id", "page_number", "page_url", "widow_name", "veteran_name",
        "annual_pension_amount", "amount_evidence", "veteran_rank", "service_duration_raw",
        "service_description", "governing_law_dates", "certificate_issue_date",
        "pension_commencement_date", "assigned_legal_period", "event_status", "period_n",
        "period_median", "period_iqr", "period_mad", "iqr_flag", "mad_flag",
        "research_lead_type", "review_flags", "flag_limit", "source_text",
    ]
    return flagged[columns].sort_values(["assigned_legal_period", "annual_pension_amount"])


def distribution_summary(events: pd.DataFrame) -> pd.DataFrame:
    base = events.loc[events["analysis_inclusion"]].copy()
    rows = []
    for period in PERIOD_LABELS:
        group = base.loc[base["assigned_legal_period"].eq(period)]
        amounts = group["annual_pension_amount"].dropna().astype(float)
        rows.append({
            "legal_period": period,
            "candidate_events": len(group),
            "events_with_amount": len(amounts),
            "events_missing_amount": int(group["annual_pension_amount"].isna().sum()),
            "median": amounts.median() if len(amounts) else np.nan,
            "q1": amounts.quantile(.25) if len(amounts) else np.nan,
            "q3": amounts.quantile(.75) if len(amounts) else np.nan,
            "minimum": amounts.min() if len(amounts) else np.nan,
            "maximum": amounts.max() if len(amounts) else np.nan,
        })
    return pd.DataFrame(rows)


def group_summary(events: pd.DataFrame) -> pd.DataFrame:
    data = events.loc[
        events["analysis_inclusion"] & events["annual_pension_amount"].notna() &
        events["certificate_issue_date"].notna()
    ].copy()
    outputs = []
    for grouping, label in [(["assigned_legal_period", "veteran_rank"], "rank"),
                            (["assigned_legal_period", "service_duration_group"], "service_duration")]:
        summary = data.groupby(grouping, dropna=False)["annual_pension_amount"].agg(
            n="size", median="median", minimum="min", maximum="max",
            q1=lambda values: values.quantile(.25), q3=lambda values: values.quantile(.75)).reset_index()
        summary = summary.loc[summary["n"] >= 10].copy()
        summary.insert(0, "comparison_type", label)
        outputs.append(summary.rename(columns={grouping[-1]: "group"}))
    return pd.concat(outputs, ignore_index=True)


def svg_histograms(events: pd.DataFrame, summary: pd.DataFrame, target: Path) -> None:
    width, panel_h, margin = 1100, 180, 55
    height = margin + panel_h * len(PERIOD_LABELS) + 35
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             '<style>text{font-family:Arial,sans-serif;fill:#17202a}.title{font-size:18px;font-weight:bold}.label{font-size:12px}.small{font-size:10px;fill:#566573}.bar{fill:#4472a8}.axis{stroke:#7f8c8d;stroke-width:1}</style>',
             '<text x="55" y="28" class="title">Observed annual widow-pension amounts by certificate-issue legal period</text>',
             '<text x="55" y="46" class="small">Histograms show included, deduplicated candidate events; x-axis is annual dollars and is truncated at each period\'s 99th percentile for legibility.</text>']
    data = events.loc[events["analysis_inclusion"] & events["certificate_issue_date"].notna()].copy()
    for i, period in enumerate(PERIOD_LABELS):
        y0 = margin + i * panel_h
        row = summary.loc[summary["legal_period"].eq(period)].iloc[0]
        amounts = data.loc[data["assigned_legal_period"].eq(period), "annual_pension_amount"].dropna().astype(float)
        label = period.replace(" (Act of ", " — ").replace(")", "")
        parts.append(f'<text x="55" y="{y0 + 16}" class="label">{html.escape(label)} | n={len(amounts):,}; missing={int(row.events_missing_amount):,}</text>')
        left, right, top, bottom = 55, width - 35, y0 + 28, y0 + 145
        parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>')
        if len(amounts):
            cap = float(amounts.quantile(.99))
            cap = max(cap, float(amounts.min()) + 1)
            clipped = amounts.clip(upper=cap)
            counts, edges = np.histogram(clipped, bins=30, range=(0, cap))
            maximum = max(int(counts.max()), 1)
            bar_w = (right - left) / len(counts)
            for j, count in enumerate(counts):
                bar_h = (bottom - top) * count / maximum
                parts.append(f'<rect x="{left + j * bar_w:.1f}" y="{bottom - bar_h:.1f}" width="{max(bar_w - 1, .5):.1f}" height="{bar_h:.1f}" class="bar"/>')
            parts.append(f'<text x="{left}" y="{bottom + 15}" class="small">$0</text>')
            parts.append(f'<text x="{right - 90}" y="{bottom + 15}" class="small">99th pct: ${cap:,.2f}</text>')
            above = int((amounts > cap).sum())
            parts.append(f'<text x="{right - 180}" y="{top + 10}" class="small">above display cap: {above}</text>')
        else:
            parts.append(f'<text x="{left + 10}" y="{top + 35}" class="small">No parsed amounts in this period.</text>')
    parts.append('</svg>')
    target.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    FIGURES.mkdir(exist_ok=True)
    events = build_events()
    summary = distribution_summary(events)
    flags = robust_flags(events)
    groups = group_summary(events)
    events.to_csv(OUT / "provisional_award_events.csv", index=False)
    summary.to_csv(OUT / "period_distribution_summary.csv", index=False)
    flags.to_csv(OUT / "award_research_leads.csv", index=False)
    groups.to_csv(OUT / "rank_service_group_summary.csv", index=False)
    svg_histograms(events, summary, FIGURES / "period_amount_distributions.svg")
    print(f"events: {len(events):,}")
    print(f"analysis included: {events['analysis_inclusion'].sum():,}")
    print(f"exact duplicates linked: {events['duplicate_of_event_id'].notna().sum():,}")
    print(f"certificate dates parsed: {events['certificate_issue_date'].notna().sum():,}")
    print(f"commencement dates parsed: {events['pension_commencement_date'].notna().sum():,}")
    print(f"amounts parsed: {events['annual_pension_amount'].notna().sum():,}")
    print(f"research leads: {len(flags):,}")


if __name__ == "__main__":
    main()
