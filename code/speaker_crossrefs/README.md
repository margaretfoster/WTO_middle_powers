# WTO CTD Speaker Cross-Reference Extraction

Extracts and classifies delegation-to-delegation references from WTO Committee on Trade and Development (CTD) meeting minutes. Produces a one-to-many table mapping each paragraph to any other delegations explicitly referenced within it, with a sentiment label (support / oppose / neutral).

---

## Background

The source data (`wtoCTDSpeakerParagraphMto117_flagged.csv`) contains paragraph-level speaker attribution for CTD meetings M1–M117. A speaker's paragraph often mentions other delegations — endorsing their position, disagreeing with them, or simply citing their statement. These cross-references are analytically important but cannot be reliably captured by the same keyword patterns used for primary speaker attribution, because:

- Reference position varies (beginning, middle, or end of paragraph)
- Phrasing is inconsistent ("joined", "associated herself with", "concurred with", "supported the position of", etc.)
- Country names appear for non-delegation reasons (geographic references, past meetings, document titles) and must be excluded
- Sentiment polarity needs to be classified alongside the reference

The pipeline uses a two-stage approach: a fast regex pre-filter to identify candidate paragraphs, followed by Claude (`claude-haiku-4-5`) for structured extraction.

---

## Pipeline

```
wtoCTDSpeakerParagraphMto117_flagged.csv
        │
        ▼
  [1] Pre-filter
      • proposed_speaker / pres.speaker fill-forward → current_speaker
      • ents field must contain ≥ 2 named entities
      • paratext must match reference-pattern regex
        (~6,100 candidates from 11,737 total rows)
        │
        ▼
  [2] Claude Haiku 4.5 extraction (Batches API)
      • System prompt defines valid vs. invalid references
      • Returns JSON: [{ref_entity, sentiment, ref_snippet}]
      • ~1–2 hour turnaround; ~$4 total
        │
        ▼
  [3] Collect & flatten
      • One output row per (paragraph, referenced entity)
        │
        ▼
  data/wtoCTDSpeakerRefMap.csv
```

### Pre-filter regex

Matches common delegation-reference patterns:
- `representative/delegation(s)/position of`
- `supported / agreed / concurred / associated with`
- `opposed / objected to`
- `shared the view/concern/position`
- `joined / joining the / other`
- `welcomed the`

Paragraphs passing the regex AND having ≥ 2 named entities in `ents` are sent to the API. Paragraphs where the model finds no valid reference return `[]` and produce no output rows.

### Sentiment labels

| Label | Meaning |
|-------|---------|
| `support` | Speaker endorses, agrees with, or associates with the referenced delegation |
| `oppose` | Speaker disagrees with, criticizes, or objects to the referenced delegation |
| `neutral` | Speaker cites, acknowledges, calls on, thanks, or responds to the referenced delegation without taking a position |

---

## Output

`data/wtoCTDSpeakerRefMap.csv` — one row per reference found.

| Column | Description |
|--------|-------------|
| `pid` | Paragraph ID (joins to source data) |
| `doc` | Document identifier (e.g. `WT/COMTD/M/45`) |
| `paranum` | Paragraph number within the document |
| `year` | Year of the meeting |
| `meetingno` | Meeting number (1–117) |
| `speaker` | Resolved speaker for this paragraph |
| `ref_entity` | Name of the delegation being referenced |
| `sentiment` | `support` / `oppose` / `neutral` |
| `ref_snippet` | Verbatim ≤15-word excerpt capturing the reference |

---

## Usage

### Prerequisites

```bash
pip install anthropic pandas
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Test on 10 samples (synchronous, cheap)

```bash
python3 wtoCTDRefMap.py --test
```

Calls the API directly on 10 randomly sampled candidates and prints results to the terminal. Writes `data/wtoCTDSpeakerRefMap_TEST.csv` if any references are found. Run this first to verify prompt quality before committing to the full batch.

### Full batch run (~$4, ~1–2 hours)

```bash
python3 wtoCTDRefMap.py
```

Submits all ~6,100 candidates to the Anthropic Batches API (50% discount vs. standard pricing), saves the batch ID to `data/wtoCTDRefMap_batch_state.json`, polls every 30 seconds, and writes the final CSV when the batch ends.

### Resume an interrupted run

If the script is interrupted after submission, restart it and it will pick up the saved batch ID automatically:

```bash
python3 wtoCTDRefMap.py
# or explicitly:
python3 wtoCTDRefMap.py --retrieve msgbatch_XXXX
```

---

## Input data dependency

This script reads from `data/wtoCTDSpeakerParagraphMto117_flagged.csv`, which was produced by the speaker-attribution QA pass (Phase 1). That file adds `proposed_speaker` and several `flag_*` columns to the original `wtoCTDSpeakerParagraphMto117_varyingInc.csv`. The `proposed_speaker` field is preferred over `pres.speaker` as the resolved speaker when present; otherwise `pres.speaker` is used, and the value is filled forward across carry-forward paragraphs (where `speaker.change == 0`).

---

## Known limitations

- **OCR artefacts**: The source data contains occasional OCR errors (e.g. `"C hina"` for `"China"`). These can cause `ref_entity` values to be slightly malformed.
- **Carry-forward rows**: References in carry-forward paragraphs are attributed to the inferred speaker, which may itself be incorrect if the upstream flagging missed a speaker change.
- **Sentiment granularity**: The three-way classification is coarse. Nuanced stances ("took note of", "was not opposed to") are collapsed to `neutral`.
- **Self-reference suppression**: The model is instructed to exclude self-references, but may occasionally include a delegation referencing its own earlier statement.
