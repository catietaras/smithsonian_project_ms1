Smithsonian widow-pension awards
Part 1: Project documentation: November 5, 2026
Research objective
Identify unusually high or low annual pension-rate candidates and investigate their relationship to veteran rank, service duration, and historical period. Flagged values are research leads, not findings of error or fraud.
Source and scope
The project uses OCR of NARA Revolutionary War pension and bounty-land application files, accessed through a Hugging Face corpus. Earlier documentation describes a file-level filter using widow of, per annum, rate of, and dollars.

That search favors standardized annual-rate certificates. It does not establish complete coverage of early claims, private acts, orphan claims, or unpaid veteran balances. Broader corpus discovery remains unfinished.
Chronology and analytical periods
The research chronology begins with the August 24, 1780 resolution. The existing analysis uses seven certificate-date periods beginning in 1836. A proposed 21-period chronology distinguishes earlier contexts and later changes through 1880, but has not been implemented.

Certificate issue date, pension commencement date, and governing law remain separate. A later certificate may concern an earlier law. The earliest certificate found is not necessarily an initial award.

Detailed chronology and proposed boundaries are documented in:
- research/widow_pension_legislation_chronology.csv
- research/proposed_period_boundaries_1780_1899.csv
Earlier references include the Journals of the Continental Congress, volume 17, NARA M804 descriptive pamphlet, and Statutes at Large references recorded in the earlier documentation. Their interpretations were not newly verified in this revision.
Methods and earlier outputs
The earlier build, analysis/build_award_events.py, was documented as using search_results/widow_awards_draft_v17.csv to extract dates, amount candidates, ranks, durations, governing-law references, and event cues while retaining source evidence.

It reported 40,083 candidate page records, 25 exact-duplicate exclusions, and 805 exploratory IQR/MAD research leads. These earlier results were not regenerated during the latest cleaning pass. A distinct row or event ID does not establish a distinct historical award.

Earlier outputs are documented under outputs/; superseded intermediates under archive/cleanup_2026-11-05/. The earlier build was not rerun in this pass.
Limitations
Extracted fields remain provisional. Missingness may be systematic; comparisons are descriptive, not causal. Original values and anomalies are preserved.
Part 2: Progress update: November 10, 2026
What the counts mean
The earlier extraction reported 21,717 candidate files and 40,083 candidate page records. A file can contain several certificates or related pages.

The current analysis contains 40,058 page records across 20,191 files. The 25-row difference matches the previously reported duplicate exclusions, but the code connecting these stages has not been checked. The change in represented file counts also remains unreconciled.

Page records are not distinct widows or awards.
Name cleanup
Copied the analysis table into name_review and retained the original name fields. Added separate candidate-name, review-flag, and verification-note columns.
1. Screened for missing names, location text, and repetition.
2. Added 16 candidates for repeated-name extractions.
3. Removed observed location prefixes to add 6,589 candidates.
4. Refined 42 existing candidates by removing leading N.Y..
5. Added 3,819 candidates using additional observed state/city prefixes.
6. Inspected displayed samples; preserved uncertain spelling and remaining text.
   - 27,620 records contain a widow-name candidate; 12,438 do not.
   - Added 10,424 provisional cleaned-name candidates.
   - Retained all 40,058 working records. No people were merged.
Two user inspections clarified location headings for the Elizabeth Jesse and Belinda Stoughton records. These did not verify every spelling or relationship. Further manual verification was paused.
Date endpoint and charts
March 27, 1899 appears in the OCR for NARA file 196142829, page 64. In the uploaded award-history CSV, its parsed date is blank. The scan was not checked, so the date remains unresolved rather than established as an OCR error.

The latest populated parsed date found in that CSV was June 12, 1898, also unverified. No latest source-confirmed date has been established.

The PDF charts were relabeled “Feb 1853–Mar 1899,” with an unverified-endpoint note. Values were not recalculated, and the unresolved 1899 record does not contribute to the period bars. The notebook retains the open-ended bin “1853-02-03 onward.”
Part 3: Cleaning, summaries, and anomaly analysis: November 15, 2026
Consistency checks completed
All 40,058 records were preserved. Checks found:
- No missing or repeated event IDs; no missing file IDs.
- No provisional widow IDs spanning multiple files.
- No present-but-nonnumeric amounts or negative amounts; all 42 zeros retained.
- No negative numeric durations, duration-group mismatches, or certificate-date/period mismatches.
Checks were run on cleaning_work, a separate working copy. Numeric amounts were converted with pd.to_numeric. Expected duration groups were calculated from numeric months and compared with existing groups. Parsed certificate dates were compared with period boundaries. No mismatches were corrected because none were found.
Data available for analysis
Field	Available	Missing or unresolved
Numeric annual-rate candidate	15,991	24,067
Parsed certificate date	27,718	12,340
Provisional widow ID	27,620	12,438
Service-duration group	14,947	25,111


There are 11,104 records with both a numeric amount and a parsed date. The 4,887 numeric amounts without parsed dates remain in an unresolved-period group.
Analysis rules
An annual-rate candidate is an amount extracted as a possible annual pension rate. It is not a source-confirmed rate or payment received. This applies equally to ordinary and extreme amounts.

Page-level calculations use all retained numeric candidates. Missing amounts are excluded from numeric statistics, not treated as zero. Zeros, extremes, and unresolved groups remain visible.

Summaries retain all event statuses: 36,775 initial-award-not-established records, 2,235 change cues, 1,001 reissue cues, and 47 cancelled or superseded records. These describe extracted candidates rather than confirmed payments.

Period, rank, duration, and combined summaries were calculated. Groups with fewer than 10 numeric amounts are flagged, not removed. Governing law remains separate from certificate period; ambiguous ranks remain ambiguous.
Page-level and provisional widow-level results
Comparison	Count	Mean	Median
All numeric page records	15,991	$75.22	$50.00
Numeric pages with provisional widow IDs	10,777	$70.68	$47.76
One mean candidate per provisional widow group	7,703	$70.31	$50.00


The first comparison changes coverage; the second changes weighting. The complete candidate range is $0–$2,100. $525 is the 99th percentile, not the maximum. Values are interpreted as annual historical-dollar amounts and are not inflation-adjusted.

Of 15,518 provisional widow groups, 7,703 have numeric amounts, 7,815 have none, and 858 have multiple distinct amounts. These are not verified identities or confirmed pension histories.
Measure within each group with amounts	Mean across groups	Median across groups
Lowest extracted annual-rate candidate	$67.98	$46.66
Highest extracted annual-rate candidate	$72.89	$50.75
Mean extracted annual-rate candidate	$70.31	$50.00
Median extracted annual-rate candidate	$70.12	$50.00


$72.89 is the average of group maxima, not the dataset maximum. Group summaries do not establish initial or final entitlements, lifetime payments, or time-weighted averages. Repeated paperwork may affect within-group means.

Older columns named lowest_observed_rate, highest_observed_rate, mean_observed_rate, and median_observed_rate mean these extracted-candidate measures. A rename/export cell was provided, but its execution has not been confirmed.
Anomaly-candidate analysis: next step
An updated anomaly-candidate table has not yet been generated from the cleaned checkpoint. The summaries provide comparison baselines; the earlier 805-lead output is not a current result.

The next analysis will:
1. Flag unusually high or low candidates across all numeric records.
2. Compare candidates within certificate periods, then period/rank/duration groups where sample size and spread support assessment.
3. Keep overall and within-group flags separate. Mark comparisons that cannot be assessed as unassessed, not normal.
4. Track multiple distinct amounts within a provisional widow group separately. Variation can reflect legitimate changes or reissues; it is not automatically a conflict or error.
5. Retain the amount, comparison group, sample size, flag reason, event status, identifiers, source passage, and page link for each lead.
Document thresholds, minimum sample sizes, and zero-spread handling when implementing the method. Flags will not correct or delete values.
AI assistance and researcher review
AI generated Python code for name-cleaning suggestions, consistency checks, summaries, and CSV exports. I ran it in my notebook and reviewed record counts, sample transformations, summary labels, and preservation of original values. My feedback guided revisions. I also inspected selected source pages for location headings.

This was output review, not a line-by-line code audit or verification of every extracted value. Automated checks establish internal consistency, not historical accuracy. Results remain exploratory.
Saved outputs
Saved under search_results/:
File	Contents
widow_pension_cleaning_checkpoint_20261115_100002.csv	40,058 records, 70 columns
provisional_widow_summary_20261115_100534.csv	Provisional widow-group summaries; older labels
page_vs_widow_comparison_20261115_100534.csv	Coverage and weighting comparison
certificate_period_summary_20261115_100534.csv	Period summary
period_rank_summary_20261115_100534.csv	Period and rank summary
period_duration_summary_20261115_100534.csv	Period and duration summary
period_rank_duration_summary_20261115_100534.csv	Combined summary


Summary files retain grouping indexes. Some use earlier labels. Results reflect notebook outputs; exports were not independently recomputed for this documentation.
Remaining work
Reconcile record/file counts, align summary labels, and generate anomaly candidates. Expanded periods, broader corpus discovery, transaction classification, and validated identity linkage remain future research tasks.
