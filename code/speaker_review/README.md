# WTO CTD Speaker Attribution Review App

A Streamlit app for manually reviewing and correcting flagged speaker attributions in `data/wtoCTDSpeakerParagraphMto117_flagged.csv`.

## Quick start

```bash
# From the repo root:
streamlit run code/speaker_review/speaker_review.py
```

Opens in your browser at `http://localhost:8501`.

## What it does

The flagging script identified ~3,800 paragraphs where the extracted speaker is likely wrong. Most fall into two groups:

- **Judgment calls (~1,300 rows, default view):** `flag_possible_missed_speaker`, `flag_nonspeaker_entity`, `flag_individual_name`, `flag_ambiguous_title_only`, `flag_null_extracted` — these need a human to read the text and decide.
- **Systematic errors (~2,700 `flag_carryforward` rows):** carry-forward paragraphs. Usually correct; include them via the sidebar if you want to audit them.

## How to use it

1. The sidebar lets you filter by flag type. The default view shows the ~1,300 judgment-call rows.
2. Each screen shows:
   - **Flag badges** — what triggered the flag and the script's note (e.g. `"text suggests Argentina (rep_of)"`)
   - **Previous paragraph** (expandable) — for carry-forward context
   - **Full paragraph text** — untruncated
   - **Speaker attribution fields** — `firstent`, `pres.speaker`, `proposed_speaker`
3. The correction field is pre-filled with `proposed_speaker`. Edit it if the proposed value is wrong, or leave it as-is.
4. Click **Save & next** to record your correction and move on. **Skip** marks the row without a correction. **Back** steps backward.

Progress is saved to the CSV on every action — you can stop and resume at any time.

## Output columns added to the CSV

| Column | Values |
|--------|--------|
| `manual_speaker` | Your corrected speaker string (empty = accept proposed) |
| `review_status` | `reviewed` \| `skipped` \| `` (empty = not yet seen) |

The original columns are never modified. After review, use `manual_speaker` (where non-empty) in preference to `proposed_speaker` for downstream analysis.

## Flag priority guide

| Icon | Flags | Action |
|------|-------|--------|
| 🔴 | `flag_null_extracted`, `flag_possible_missed_speaker` | Read carefully — speaker is likely wrong |
| 🟠 | `flag_nonspeaker_entity`, `flag_topic_not_speaker` | Check `flag_notes` for the suggested correction |
| 🟡 | `flag_individual_name`, `flag_ambiguous_title_only` | Determine which delegation the individual represents |
| ⚪ | `flag_carryforward` | Usually correct; skip unless something looks off |
