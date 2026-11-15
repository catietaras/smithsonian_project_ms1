# Changelog

## 2026-11-05

- Recorded the research objective and verified all seven notebook law boundaries against the *United States Statutes at Large*. Effect: the analytical periods now have primary-source citations and explicit verification status.
- Added `analysis/build_award_events.py`. Effect: recurring OCR date, name, service, event-status, and duplicate problems are handled reproducibly over all 40,083 candidate pages rather than through a 100-page manual review requirement.
- Created `outputs/provisional_award_events.csv`. Effect: award occurrence, certificate issue, commencement, governing law, and period assignment are represented separately; unknowns remain unknown; an unmarked certificate is not asserted to be an initial award.
- Replaced earliest-certificate-as-first-award reasoning with event-level certificate-date proxy assignment. Effect: no file's earliest observed certificate is silently treated as its first award, and unresolved dates remain unassigned.
- Added conservative exact within-file duplicate linking. Effect: 25 duplicate certificate rows are excluded from analytical counts, while different amounts and dates—including later increases—remain separate events.
- Added provisional file-case and previous-observed-event links for distinct rows. Effect: increases and reissues can be followed without asserting that the available pages form a complete person-level chronology.
- Added seven-period observed-distribution summaries and SVG histograms with sample and missing counts. Effect: the empirical shapes can be inspected before any normal-distribution assumption.
- Added period-level IQR and MAD research leads with full source evidence and provisional OCR/change/reissue categories. Effect: 805 unusual observations are queued for targeted historical investigation without treating the flags as conclusions.
- Added within-period rank and service-duration summaries for groups with at least 10 parsed amounts. Effect: exploratory comparisons are limited to groups with a minimally useful observed sample.
- Audited notebook and script references and moved 23 confirmed redundant or temporary files (about 881 MiB) to `archive/cleanup_2026-11-05/`; nothing was deleted. Effect: the active tree is smaller while every archived file remains recoverable with its original relative path.
- Updated validation sampling to read v17 and reproduce the checkpoint's normalized-law field in code. Effect: the redundant 58 MiB checkpoint is no longer an active dependency, and the 100-page candidate validation sample remains byte-for-byte unchanged.
- Added `CLEANUP_INVENTORY.md` with per-file sizes, reasons, reproducibility, retained evidence, and unresolved-purpose notes.
- Expanded the historical research scope to the Continental Congress widow-pension resolution of August 24, 1780 and carried the chronology through the latest parsed certificate date represented in the data (March 27, 1899, marked as a probable OCR error).
- Added `research/widow_pension_legislation_chronology.csv` with primary or official sources, authority classes, applicability notes, and verification status for changes before 1836 and after 1853.
- Added `research/proposed_period_boundaries_1780_1899.csv` with 21 proposed chronological periods. Effect: 1780–1836 is no longer treated as one regime, and later rate, eligibility, consolidation, and naval-restoration changes have proposed boundaries without prematurely rebuilding outputs.
- Defined separate authority and transaction categories for the 1780 resolution, private acts, general widow pensions, veteran-pension balances, state/Virginia half-pay, other-war benefits, reissues, and uncertainty.
- Audited the original four-phrase source filter. Effect: README now states that the retained JSONL cannot measure upstream false negatives and likely undercaptures early half-pay, private-act, arrears, balance, heir, and orphan records; the dataset is no longer described as representing the entire history.
- Marked the seven-boundary constant in `analysis/build_award_events.py` as a legacy reproduction frame. Effect: future work is directed to implement authority classification before applying the expanded periods, rather than silently relabeling current outputs.
