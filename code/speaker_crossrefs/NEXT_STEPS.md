# Next Steps

## 1. Set the Anthropic API key

The pipeline requires an `ANTHROPIC_API_KEY` environment variable. The key was not found in the environment or any config file during initial setup.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

To persist across sessions, add the line to `~/.zshrc` and reload:

```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

Get a key at [console.anthropic.com](https://console.anthropic.com) if you don't have one.

---

## 2. Run the test pass before the full batch

Once the key is set, run 10 rows synchronously to verify the prompt produces sensible output:

```bash
cd /Users/foster_nsdpi/Dropbox/WTO-Github/WTO-DataRelease
python3 code/speaker_crossrefs/wtoCTDRefMap.py --test
```

Check the printed results for:
- False positives (geographic or document references incorrectly extracted)
- False negatives (obvious delegation references missed)
- Sentiment mislabels (e.g. a clear endorsement classified as `neutral`)

If the output looks off, adjust the system prompt in `wtoCTDRefMap.py` (`SYSTEM` constant, lines 36–60) before committing to the full batch.

---

## 3. Submit the full batch (~$4)

```bash
python3 code/speaker_crossrefs/wtoCTDRefMap.py
```

The batch ID is saved to `data/wtoCTDRefMap_batch_state.json` immediately after submission, so the run can be resumed if interrupted. Typical turnaround is 1–2 hours. Output goes to `data/wtoCTDSpeakerRefMap.csv`.

---

## 4. Validate the output

After the batch completes, spot-check the output CSV:

- Confirm `ref_entity` values are clean country/organization names (no underscores, no OCR artefacts like `"C hina"`)
- Check sentiment distribution — `neutral` should dominate; a large `oppose` share would be surprising given CTD norms
- Cross-reference a few rows back to the source `paratext` to verify `ref_snippet` is genuinely verbatim

---

## 5. Entity normalization (post-processing, optional)

The model returns entity names as written in the text, which can vary across documents:
- `"European Communities"` vs. `"European Union"` vs. `"EU"`
- `"United States"` vs. `"USA"` vs. `"US"`
- Country names with minor OCR differences

A normalization pass mapping these to canonical names before analysis would improve aggregation. A lookup table or fuzzy-match against a standard country list (e.g. the `country` field already in the source data) would work.

---

## 6. Upstream speaker corrections (optional)

The `speaker` field in the output is inferred from `proposed_speaker` / `pres.speaker` with fill-forward. Rows flagged in `wtoCTDSpeakerParagraphMto117_flagged.csv` as `flag_possible_missed_speaker` (199 rows) or `flag_nonspeaker_entity` may carry incorrect speaker attribution into the cross-reference table. Manual review of those flagged rows first would improve the quality of the `speaker` column in the output.
