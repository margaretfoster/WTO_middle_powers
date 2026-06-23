#!/usr/bin/env python3
"""
wtoCTDRefMap.py — Extract cross-speaker references from WTO CTD minutes.

Produces a one-to-many mapping:
  pid, doc, paranum, year, meetingno, speaker → ref_entity, sentiment, ref_snippet

Usage:
  python3 wtoCTDRefMap.py              # submit batch, poll, collect
  python3 wtoCTDRefMap.py --test       # 10-row synchronous test (no batch)
  python3 wtoCTDRefMap.py --retrieve BATCH_ID   # collect from existing batch

Cost estimate (Haiku batch API): ~$4 for full dataset.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import anthropic
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR    = Path('/Users/foster_nsdpi/Dropbox/WTO-Github/WTO-DataRelease/data')
INPUT_CSV   = DATA_DIR / 'wtoCTDSpeakerParagraphMto117_flagged.csv'
OUTPUT_CSV  = DATA_DIR / 'wtoCTDSpeakerRefMap.csv'
STATE_FILE  = DATA_DIR / 'wtoCTDRefMap_batch_state.json'

MODEL      = 'claude-haiku-4-5'
MAX_TOKENS = 512

# ── Prompts ───────────────────────────────────────────────────────────────────
SYSTEM = """You analyze WTO Committee on Trade and Development meeting minutes.
Your task: identify cross-delegation references — places where the speaker explicitly
references ANOTHER delegation's position, statement, or action.

VALID references (include these):
- Speaker expresses support for / agreement with another delegation → "support"
- Speaker joins or associates with another delegation's position → "support"
- Speaker opposes / disagrees with / criticizes another delegation → "oppose"
- Speaker cites, acknowledges, or responds to another delegation (factual) → "neutral"
- Speaker calls on or directs a request to another delegation → "neutral"
- Speaker thanks or welcomes a specific delegation → "neutral"

NOT valid references (exclude these):
- Geographic references: "the situation in China", "the meeting in Doha"
- Document references: "the paper from the United States" (without attributing a position)
- Self-references: speaker mentions their own country or delegation
- References to WTO bodies, Secretariat, or the Committee itself
- The opening attribution "The representative of X said..." (that is the speaker tag, not a reference)

Return ONLY a JSON array. Each element is one reference:
  {"ref_entity": "clean country/org name", "sentiment": "support|oppose|neutral", "ref_snippet": "≤15 word verbatim quote"}

If no valid cross-delegation references found, return: []

Do not include any explanation outside the JSON array."""


def build_user_msg(speaker: str, text: str) -> str:
    speaker_clean = str(speaker).replace('_', ' ')
    # Cap text at 1 800 chars to stay well within Haiku's context
    return f"Speaker: {speaker_clean}\n\nParagraph:\n{str(text)[:1800]}"


# ── Pre-filter ─────────────────────────────────────────────────────────────────
_REF_RE = re.compile(
    r'\b(?:representative|delegation|delegations|position)\s+of\b|'
    r'\bsupport(?:ed|s|ing)?\s+(?:the|by|that\s+of)?\b|'
    r'\b(?:agreed?|concurr?ed?|associated\s+(?:herself|himself|themselves))\s+with\b|'
    r'\b(?:oppos(?:ed|ing)|object(?:ed|ing))\s+(?:to|by)\b|'
    r'\bshared?\s+the\s+(?:view|concern|position)\b|'
    r'\bjoin(?:ed|ing)\s+(?:the|other)\b|'
    r'\bwelcom(?:ed?|ing)\s+the',
    re.IGNORECASE
)


def n_ents(s) -> int:
    if pd.isna(s):
        return 0
    return len([e.strip() for e in str(s).split(',') if e.strip()])


def load_candidates(verbose: bool = True) -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)

    # Resolve current speaker: prefer proposed_speaker, fallback to pres.speaker, fill forward
    df['current_speaker'] = df['proposed_speaker'].fillna(df['pres.speaker'])
    df['current_speaker'] = df['current_speaker'].ffill()

    df['n_ents'] = df['ents'].apply(n_ents)
    df['has_ref_pattern'] = df['paratext'].apply(
        lambda t: bool(_REF_RE.search(str(t))) if not pd.isna(t) else False
    )

    cands = df[
        df['current_speaker'].notna() &
        (df['n_ents'] >= 2) &
        df['paratext'].notna() &
        ~df['paratext'].str.strip().eq('') &
        df['has_ref_pattern']
    ].copy()

    if verbose:
        print(f"Loaded {len(df)} rows → {len(cands)} candidates after pre-filter")
        total_in  = len(cands) * 600
        total_out = len(cands) * 150
        cost = (total_in / 1e6 * 1.0 + total_out / 1e6 * 5.0) * 0.5
        print(f"Estimated batch cost: ${cost:.2f}")

    return cands


# ── JSON parsing ───────────────────────────────────────────────────────────────
def parse_refs(text: str) -> list[dict]:
    text = text.strip()
    start = text.find('[')
    end   = text.rfind(']')
    if start == -1 or end == -1:
        return []
    try:
        items = json.loads(text[start:end + 1])
        return [i for i in items if isinstance(i, dict) and 'ref_entity' in i]
    except json.JSONDecodeError:
        return []


# ── Row → output record ────────────────────────────────────────────────────────
def make_records(row: pd.Series, refs: list[dict]) -> list[dict]:
    pid = int(row['pid']) if not pd.isna(row['pid']) else row.name
    base = {
        'pid':       pid,
        'doc':       row.get('doc', ''),
        'paranum':   row.get('paranum', None),
        'year':      row.get('year', None),
        'meetingno': row.get('meetingno', None),
        'speaker':   row['current_speaker'],
    }
    return [{**base,
             'ref_entity':  r.get('ref_entity', '').strip(),
             'sentiment':   r.get('sentiment', 'neutral').strip(),
             'ref_snippet': r.get('ref_snippet', '').strip()}
            for r in refs]


# ── Synchronous test mode ──────────────────────────────────────────────────────
def run_test(n: int = 10) -> None:
    client = anthropic.Anthropic()
    cands  = load_candidates()
    sample = cands.sample(min(n, len(cands)), random_state=1)

    print(f"\nRunning synchronous test on {len(sample)} rows...\n")
    records = []
    for _, row in sample.iterrows():
        pid = int(row['pid']) if not pd.isna(row['pid']) else row.name
        msg = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            messages=[{"role": "user", "content": build_user_msg(row['current_speaker'], row['paratext'])}]
        )
        text = next((b.text for b in msg.content if b.type == 'text'), '')
        refs = parse_refs(text)
        print(f"pid={pid}  speaker={row['current_speaker']}")
        print(f"  text: {str(row['paratext'])[:140]}")
        print(f"  refs: {refs}")
        print()
        records.extend(make_records(row, refs))

    if records:
        out = pd.DataFrame(records)
        test_path = DATA_DIR / 'wtoCTDSpeakerRefMap_TEST.csv'
        out.to_csv(test_path, index=False)
        print(f"Wrote {len(out)} reference rows to {test_path}")
    else:
        print("No references found in test sample.")


# ── Batch submission ───────────────────────────────────────────────────────────
def submit_batch(client: anthropic.Anthropic, cands: pd.DataFrame) -> str:
    requests = []
    for _, row in cands.iterrows():
        pid = int(row['pid']) if not pd.isna(row['pid']) else row.name
        requests.append({
            "custom_id": f"pid_{pid}",
            "params": {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "system": SYSTEM,
                "messages": [{"role": "user", "content": build_user_msg(row['current_speaker'], row['paratext'])}]
            }
        })

    print(f"Submitting {len(requests)} requests...")
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch ID: {batch.id}")
    STATE_FILE.write_text(json.dumps({'batch_id': batch.id}))
    print(f"State saved to {STATE_FILE}")
    return batch.id


# ── Batch polling ──────────────────────────────────────────────────────────────
def poll_batch(client: anthropic.Anthropic, batch_id: str) -> None:
    print("Polling for batch completion (checks every 30 s)...")
    while True:
        batch  = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(f"  {batch.processing_status}: processing={counts.processing} "
              f"succeeded={counts.succeeded} errored={counts.errored}")
        if batch.processing_status == 'ended':
            return
        time.sleep(30)


# ── Collect results ────────────────────────────────────────────────────────────
def collect_results(client: anthropic.Anthropic, batch_id: str,
                    cands: pd.DataFrame) -> pd.DataFrame:
    # Index candidates by custom_id for fast lookup
    pid_to_row = {}
    for _, row in cands.iterrows():
        pid = int(row['pid']) if not pd.isna(row['pid']) else row.name
        pid_to_row[f"pid_{pid}"] = row

    records, n_ok, n_empty, n_err = [], 0, 0, 0

    for result in client.messages.batches.results(batch_id):
        row = pid_to_row.get(result.custom_id)
        if row is None:
            continue

        if result.result.type == 'succeeded':
            text = next((b.text for b in result.result.message.content if b.type == 'text'), '')
            refs = parse_refs(text)
            if refs:
                records.extend(make_records(row, refs))
                n_ok += 1
            else:
                n_empty += 1
        else:
            n_err += 1

    print(f"\nResults: {n_ok} paragraphs with references, "
          f"{n_empty} empty, {n_err} errors")
    return pd.DataFrame(records)


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true',
                        help='Run synchronous test on 10 samples')
    parser.add_argument('--retrieve', metavar='BATCH_ID',
                        help='Retrieve results from an already-submitted batch')
    args = parser.parse_args()

    if args.test:
        run_test()
        return

    client = anthropic.Anthropic()
    cands  = load_candidates()

    if args.retrieve:
        batch_id = args.retrieve
        print(f"Retrieving existing batch: {batch_id}")
    elif STATE_FILE.exists():
        state    = json.loads(STATE_FILE.read_text())
        batch_id = state['batch_id']
        print(f"Resuming batch: {batch_id}")
    else:
        batch_id = submit_batch(client, cands)

    poll_batch(client, batch_id)
    out_df = collect_results(client, batch_id, cands)

    if out_df.empty:
        print("No references found.")
        return

    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote {len(out_df)} reference rows to {OUTPUT_CSV}")
    print(f"Unique paragraphs with ≥1 reference: {out_df['pid'].nunique()}")
    print(f"\nSentiment breakdown:\n{out_df['sentiment'].value_counts().to_string()}")
    print(f"\nTop 20 referenced entities:\n{out_df['ref_entity'].value_counts().head(20).to_string()}")

    STATE_FILE.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
