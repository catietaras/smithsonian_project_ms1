#!/usr/bin/env python3
"""Create reproducible validation samples for the widow-pension OCR pipeline.

The candidate sample is built from the retained v17 extract and award-history CSV.
The rejected-file sample requires the full Hugging Face file-level corpus because
rejected records were not saved by the original notebook.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


SEED = 20261105
DATASET_NAME = (
    "RevolutionCrossroads/nara_revolutionary_war_pension_files_PDFs"
)
DATASET_REVISION = "1b44f5dcf2a81b033ad634cd7d5758a3cd8058fc"
INITIAL_TERMS = ("widow of", "per annum", "rate of", "dollars")
STRATUM_QUOTAS = {
    "complete_amount": 20,
    "incomplete_amount": 20,
    "missing_certificate_date": 20,
    "unusually_high_amount": 20,
    "cancellation_or_reissue": 20,
}
HIGH_AMOUNT_THRESHOLD = 500.0

MANUAL_FIELDS = [
    "manual_scan_reviewed",
    "manual_is_widow_award",
    "manual_annual_rate",
    "manual_rank_or_service_role",
    "manual_act_date",
    "manual_certificate_date",
    "manual_commencement_date",
    "manual_cancellation_or_reissue",
    "manual_widow_name",
    "manual_veteran_name",
    "manual_notes",
    "reviewer",
    "review_date",
]


def normalized_file_text(record: dict[str, Any]) -> str:
    pages = record.get("RevX_OCR_text") or []
    text = " ".join(page for page in pages if isinstance(page, str))
    return " ".join(text.lower().split())


def matches_initial_filter(record: dict[str, Any]) -> bool:
    text = normalized_file_text(record)
    return all(term in text for term in INITIAL_TERMS)


def hash_key(*parts: Any) -> str:
    value = "|".join(str(part) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_identifier(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    return text[:-2] if text.endswith(".0") else text


def candidate_flags(row: pd.Series) -> list[str]:
    flags: list[str] = []
    amount = row.get("annual_rate_working")
    if pd.notna(amount):
        flags.append("complete_amount")
        if float(amount) > HIGH_AMOUNT_THRESHOLD:
            flags.append("unusually_high_amount")
    else:
        flags.append("incomplete_amount")
    if pd.isna(row.get("certificate_date_draft")):
        flags.append("missing_certificate_date")
    cancellation_text = " ".join(
        str(row.get(column, "") or "")
        for column in ("review_flags", "text_original")
    )
    if re.search(
        r"cancel|supersed|new\s+certificate|reissu|republish|repeated|duplicate",
        cancellation_text,
        flags=re.I,
    ):
        flags.append("cancellation_or_reissue")
    return flags


def normalize_act_dates(value: Any) -> Any:
    """Reproduce the notebook's award_act_working normalization."""
    if not isinstance(value, str):
        return pd.NA
    dates = []
    for part in value.split("|"):
        parsed = pd.to_datetime(part.strip(), errors="coerce")
        if pd.notna(parsed):
            dates.append(parsed.strftime("%Y-%m-%d"))
    return " | ".join(dict.fromkeys(dates)) if dates else pd.NA


def load_candidates(root: Path) -> pd.DataFrame:
    awards = pd.read_csv(
        root / "search_results/widow_awards_draft_v17.csv",
        low_memory=False,
    )
    reviewed_acts = awards["award_act_date_reviewed"].replace(
        r"^\s*$", pd.NA, regex=True
    )
    draft_acts = awards["award_act_dates_draft"].apply(normalize_act_dates)
    awards["award_act_working"] = reviewed_acts.combine_first(draft_acts)
    history = pd.read_csv(
        root / "search_results/widow_award_history_draft.csv",
        usecols=[
            "file_id",
            "page_number",
            "page_url",
            "certificate_date_draft",
            "veteran_name_candidate",
            "widow_name_context",
        ],
        low_memory=False,
    )
    keys = ["file_id", "page_number", "page_url"]
    candidates = awards.merge(
        history,
        on=keys,
        how="left",
        validate="one_to_one",
    )
    reviewed_amount = pd.to_numeric(
        candidates.get("annual_rate_reviewed"), errors="coerce"
    )
    draft_amount = pd.to_numeric(
        candidates.get("annual_rate_draft"), errors="coerce"
    )
    candidates["annual_rate_working"] = reviewed_amount.combine_first(
        draft_amount
    )
    candidates["selection_flags"] = candidates.apply(
        lambda row: "; ".join(candidate_flags(row)), axis=1
    )
    return candidates


def prior_review_keys(root: Path) -> set[tuple[str, str]]:
    prior_path = root / "search_results/validation_sample_20.csv"
    if not prior_path.exists():
        return set()
    prior = pd.read_csv(prior_path, low_memory=False)
    completed_fields = [
        "amount_matches_scan",
        "rank_matches_scan",
        "act_matches_scan",
        "widow_award_confirmed",
        "validation_notes",
        "image_review_notes",
        "annual_rate_reviewed",
        "rank_reviewed",
        "award_act_date_reviewed",
        "start_date_reviewed",
        "service_description_reviewed",
    ]
    completed_fields = [field for field in completed_fields if field in prior]
    completed = prior[completed_fields].notna().any(axis=1)
    return {
        (clean_identifier(row.file_id), clean_identifier(row.page_number))
        for row in prior.loc[completed, ["file_id", "page_number"]].itertuples()
    }


def select_candidate_sample(candidates: pd.DataFrame, root: Path) -> pd.DataFrame:
    candidates = candidates.copy()
    candidates["_file_key"] = candidates["file_id"].map(clean_identifier)
    candidates["_page_key"] = candidates["page_number"].map(clean_identifier)
    prior_keys = prior_review_keys(root)
    candidates["has_prior_review_work"] = [
        (file_id, page_id) in prior_keys
        for file_id, page_id in zip(
            candidates["_file_key"], candidates["_page_key"]
        )
    ]

    selected_indices: set[int] = set()
    selected_by_stratum: dict[str, list[int]] = {
        stratum: [] for stratum in STRATUM_QUOTAS
    }
    priority = [
        "cancellation_or_reissue",
        "unusually_high_amount",
        "missing_certificate_date",
        "incomplete_amount",
        "complete_amount",
    ]

    # Preserve completed prior work by forcing those rows into an eligible stratum.
    prior_rows = candidates[candidates["has_prior_review_work"]].copy()
    prior_rows["_sort"] = prior_rows.apply(
        lambda row: hash_key(SEED, "prior", row["_file_key"], row["_page_key"]),
        axis=1,
    )
    for index, row in prior_rows.sort_values("_sort").iterrows():
        row_flags = set(row["selection_flags"].split("; "))
        for stratum in priority:
            if (
                stratum in row_flags
                and len(selected_by_stratum[stratum]) < STRATUM_QUOTAS[stratum]
            ):
                selected_by_stratum[stratum].append(index)
                selected_indices.add(index)
                break

    for stratum, quota in STRATUM_QUOTAS.items():
        needed = quota - len(selected_by_stratum[stratum])
        eligible = candidates[
            candidates["selection_flags"].str.split("; ").apply(
                lambda values: stratum in values
            )
            & ~candidates.index.isin(selected_indices)
        ].copy()
        eligible["_sort"] = eligible.apply(
            lambda row: hash_key(
                SEED, "candidate", stratum, row["_file_key"], row["_page_key"]
            ),
            axis=1,
        )
        chosen = eligible.sort_values("_sort").head(needed).index.tolist()
        if len(chosen) != needed:
            raise RuntimeError(
                f"Not enough eligible rows for {stratum}: needed {needed}, "
                f"found {len(chosen)}"
            )
        selected_by_stratum[stratum].extend(chosen)
        selected_indices.update(chosen)

    pieces = []
    for stratum, indices in selected_by_stratum.items():
        piece = candidates.loc[indices].copy()
        piece["sampling_stratum"] = stratum
        pieces.append(piece)
    sample = pd.concat(pieces, ignore_index=True)
    sample["selection_reason"] = sample.apply(
        lambda row: (
            f"Stratified sample: {row['sampling_stratum']}; "
            f"all applicable flags: {row['selection_flags']}"
        ),
        axis=1,
    )
    sample["page_id"] = sample.apply(
        lambda row: f"{row['_file_key']}:{row['_page_key']}", axis=1
    )
    sample["available_scan_url"] = sample["page_url"]
    sample["prior_review_notes"] = sample.get("image_review_notes")
    sample["prior_annual_rate_reviewed"] = sample.get("annual_rate_reviewed")
    sample["prior_rank_reviewed"] = sample.get("rank_reviewed")
    sample["prior_act_date_reviewed"] = sample.get("award_act_date_reviewed")
    sample["prior_start_date_reviewed"] = sample.get("start_date_reviewed")
    sample["prior_service_description_reviewed"] = sample.get(
        "service_description_reviewed"
    )
    for field in MANUAL_FIELDS:
        sample[field] = ""

    columns = [
        "file_id",
        "file_title",
        "page_id",
        "page_number",
        "available_scan_url",
        "text_original",
        "sampling_stratum",
        "selection_flags",
        "selection_reason",
        "annual_rate_draft",
        "annual_rate_reviewed",
        "annual_rate_working",
        "dollars_stated",
        "cents_stated",
        "rate_passage",
        "rank_draft",
        "rank_mentions_check",
        "award_act_dates_draft",
        "award_act_date_reviewed",
        "award_act_working",
        "certificate_date_passage",
        "certificate_date_draft",
        "start_date_passage",
        "review_flags",
        "veteran_name_candidate",
        "widow_name_context",
        "has_prior_review_work",
        "prior_review_notes",
        "prior_annual_rate_reviewed",
        "prior_rank_reviewed",
        "prior_act_date_reviewed",
        "prior_start_date_reviewed",
        "prior_service_description_reviewed",
    ] + MANUAL_FIELDS
    sample = sample[columns].sort_values(
        ["sampling_stratum", "file_id", "page_number"]
    )
    if len(sample) != 100 or sample["page_id"].nunique() != 100:
        raise RuntimeError("Candidate sample must contain 100 unique pages")
    return sample


def relevant_page(record: dict[str, Any]) -> dict[str, Any]:
    pages = record.get("RevX_OCR_text") or []
    page_numbers = record.get("pageNumber") or []
    page_ids = record.get("pageObjectId") or []
    page_urls = record.get("pageLink") or []
    image_urls = record.get("pageImageURL") or []

    def score(text: Any) -> tuple[int, int]:
        normalized = " ".join(str(text or "").lower().split())
        exact = sum(term in normalized for term in INITIAL_TERMS)
        near = sum(
            term in normalized
            for term in ("widow", "wid.", "pension", "annum", "dollar", "rate")
        )
        return (exact * 10 + near, len(normalized))

    best_index = max(range(len(pages)), key=lambda i: score(pages[i]), default=0)
    get = lambda values, default="": (
        values[best_index] if best_index < len(values) else default
    )
    page_number = get(page_numbers, best_index + 1)
    return {
        "page_id": get(page_ids, f"{record.get('NAID', '')}:{page_number}"),
        "page_number": page_number,
        "available_scan_url": get(page_urls) or get(image_urls),
        "page_image_url": get(image_urls),
        "relevant_ocr_text": get(pages),
    }


def load_streaming_dataset(revision: str) -> Iterable[dict[str, Any]]:
    from datasets import load_dataset

    return load_dataset(
        DATASET_NAME,
        revision=revision,
        split="train",
        streaming=True,
    )


def select_rejected_files(
    dataset: Iterable[dict[str, Any]], sample_size: int = 50
) -> tuple[pd.DataFrame, int]:
    # Bottom-k hash sampling is deterministic, order independent, and avoids
    # retaining the full rejected population in memory.
    heap: list[tuple[int, str, dict[str, Any]]] = []
    rejected_count = 0
    for record in dataset:
        if matches_initial_filter(record):
            continue
        rejected_count += 1
        file_id = str(record.get("NAID", ""))
        rank = int(hash_key(SEED, "rejected", file_id), 16)
        item = (-rank, file_id, record)
        if len(heap) < sample_size:
            heapq.heappush(heap, item)
        elif item > heap[0]:
            heapq.heapreplace(heap, item)

    if len(heap) != sample_size:
        raise RuntimeError(
            f"Rejected population contained only {len(heap)} sampleable files"
        )
    selected = [item[2] for item in heap]
    selected.sort(key=lambda record: hash_key(SEED, "rejected", record["NAID"]))
    rows = []
    for record in selected:
        page = relevant_page(record)
        normalized = normalized_file_text(record)
        missing_terms = [term for term in INITIAL_TERMS if term not in normalized]
        row = {
            "file_id": record.get("NAID", ""),
            "file_title": record.get("title", ""),
            "file_url": record.get("naraURL", ""),
            **page,
            "selection_reason": "Random bottom-k hash sample from files rejected by initial exact-phrase filter",
            "initial_filter_result": "rejected",
            "missing_exact_terms": "; ".join(missing_terms),
            "number_of_pages": record.get("numberOfPages", ""),
            "manual_scan_reviewed": "",
            "manual_contains_widow_award": "",
            "manual_missed_widow_award_page_ids": "",
            "manual_filter_miss_reason": "",
            "manual_notes": "",
            "reviewer": "",
            "review_date": "",
        }
        rows.append(row)
    return pd.DataFrame(rows), rejected_count


def write_manifest(
    path: Path,
    root: Path,
    candidate_sample: pd.DataFrame,
    rejected_status: str,
    rejected_population: int | None,
) -> None:
    payload = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": SEED,
        "source_notebook": "smithsonian_pensions_cleaning.ipynb",
        "source_files": [
            "search_results/widow_awards_draft_v17.csv",
            "search_results/widow_award_history_draft.csv",
            "search_results/validation_sample_20.csv",
        ],
        "dataset": DATASET_NAME,
        "dataset_revision": DATASET_REVISION,
        "initial_exact_phrase_filter": list(INITIAL_TERMS),
        "candidate_sample": {
            "rows": len(candidate_sample),
            "method": "Five mutually exclusive assigned strata with 20 pages each. Existing completed scan-review work is forced into an eligible stratum, then remaining places use ascending SHA-256 keys based on seed, stratum, file_id, and page_number.",
            "stratum_quotas": STRATUM_QUOTAS,
            "high_amount_threshold": HIGH_AMOUNT_THRESHOLD,
            "prior_review_rows_reused": int(
                candidate_sample["has_prior_review_work"].sum()
            ),
            "manual_fields_initialized_blank": MANUAL_FIELDS,
        },
        "rejected_file_sample": {
            "requested_rows": 50,
            "status": rejected_status,
            "rejected_population_count": rejected_population,
            "method": "Select the 50 rejected files with the smallest SHA-256 keys based on seed and file_id. This is deterministic, order independent, and requires one pass through the full pinned corpus.",
            "page_choice": "Within each sampled file, retain the OCR page with the highest count of exact-filter and related near-match terms; ties favor longer OCR text.",
        },
        "reproduction_command": (
            ".venv/bin/python validation/create_validation_samples.py "
            "--root . --include-rejected"
        ),
        "notes": [
            "The original notebook did not pin a dataset revision. The revision recorded here is the commit cached when the notebook outputs were inspected.",
            "Manual verification columns are blank. Prior reviewed values and notes are retained in separately labeled prior_* columns.",
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--include-rejected", action="store_true")
    parser.add_argument("--dataset-revision", default=DATASET_REVISION)
    args = parser.parse_args()

    root = args.root.resolve()
    output_dir = root / "validation"
    output_dir.mkdir(exist_ok=True)

    candidates = load_candidates(root)
    candidate_sample = select_candidate_sample(candidates, root)
    candidate_path = output_dir / "candidate_page_validation_sample_100.csv"
    candidate_sample.to_csv(candidate_path, index=False, quoting=csv.QUOTE_MINIMAL)

    rejected_status = "pending_full_corpus_access"
    rejected_population = None
    if args.include_rejected:
        dataset = load_streaming_dataset(args.dataset_revision)
        rejected, rejected_population = select_rejected_files(dataset)
        rejected_path = output_dir / "rejected_file_validation_sample_50.csv"
        rejected.to_csv(rejected_path, index=False, quoting=csv.QUOTE_MINIMAL)
        rejected_status = "complete"

    write_manifest(
        output_dir / "validation_sampling_manifest.json",
        root,
        candidate_sample,
        rejected_status,
        rejected_population,
    )
    print(f"Wrote {len(candidate_sample)} candidate pages to {candidate_path}")
    print(f"Rejected-file sample status: {rejected_status}")


if __name__ == "__main__":
    main()
