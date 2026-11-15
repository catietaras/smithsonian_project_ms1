# Widow-pension validation review guide

## Before reviewing

Open the URL in `available_scan_url` and confirm that it displays the page identified by `file_id`, `page_id`, and `page_number`. If the link opens the wrong page or no image is available, record that in `manual_notes`; do not infer values from OCR alone.

All columns beginning with `manual_` are for the new review. Automated values remain in the draft, working, or extracted columns. The `prior_*` fields preserve earlier scan-review work but do not automatically verify the new row.

## Candidate-page sample

For each scan, check:

1. **Record type:** Is this an actual widow-pension award or award change? Distinguish it from a veteran's award, an application or affidavit, a bureau summary, an heir claim, or a page that merely mentions a widow.
2. **Annual rate:** Transcribe the awarded annual dollars and cents exactly as the scan shows. Note blanks, overwritten figures, crossed-out figures, and multiple rates. Do not convert arrears, lump sums, or semiannual payments into an annual rate.
3. **Status of the award:** Record whether the page represents an initial award, increase, reissue, duplicate, replacement, cancellation, republished certificate, or another transaction. If more than one applies, explain the sequence in `manual_notes`.
4. **Dates:** Keep the governing act date, pension commencement/effective date, and certificate issue date separate. Record only dates that are legible on the scan. Note crossed-out or superseded dates.
5. **Rank or service role:** Transcribe the veteran's rank or roles, including abbreviations and multiple ranks. Do not use the ranks of commanding officers.
6. **Names:** Record the widow's and veteran's names as shown. Preserve uncertain spellings in `manual_notes` rather than silently normalizing them.
7. **OCR and extraction errors:** Compare the scan with `text_original` and the automated fields. Describe consequential differences, especially altered years, amounts, names, or transaction status.

Set `manual_scan_reviewed` only after viewing the scan. Leave a manual field blank when the scan does not establish the answer.

## Rejected-file sample

Review the complete file, not only the page excerpt selected by the script. The excerpt is the page with the strongest near-match to the filter terms, but a widow award may appear elsewhere.

Record whether any page in the file contains an actual widow-pension award. If so, list the relevant page IDs or page numbers and explain which exact phrase was absent or corrupted. Examples include OCR errors, abbreviations such as “wid.”, a dollar sign instead of “dollars,” or award language that does not use “per annum.”

## Interpretation limits

- The 100 candidate pages are deliberately stratified and include prior review work. They can diagnose extraction errors within the chosen strata but are not a simple random sample of all candidate pages. Unweighted percentages from this file should not be reported as overall pipeline accuracy.
- Candidate-page review evaluates precision and field extraction among selected pages. It cannot measure recall because every page already passed the initial filter.
- The 50 rejected files form a deterministic pseudo-random file-level sample only when generated from the complete pinned corpus. Reviewing all pages in those files can estimate the proportion of rejected files containing at least one missed widow award, with substantial sampling uncertainty because the sample is small.
- The rejected-file sample does not directly estimate page-level recall. It also does not, by itself, provide overall record recall without combining its results with a validated estimate of true awards among accepted files and the accepted/rejected population sizes.
- Files vary greatly in length. A random file sample gives each file equal weight, not each page or widow award equal weight.
- OCR coverage and accuracy vary. Files without usable OCR may be underrepresented in any text-filter evaluation even when scans exist.
