#!/usr/bin/env python3
"""
speaker_review.py — Streamlit app for reviewing flagged speaker attributions.

Run from the repo root:
    streamlit run code/speaker_review/speaker_review.py

Adds two columns to the flagged CSV as you work:
    manual_speaker   — your corrected speaker (empty = accept proposed)
    review_status    — 'reviewed' | 'skipped' | ''
"""

import hashlib
import streamlit as st
import pandas as pd
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
FLAGGED_CSV = Path('/Users/foster_nsdpi/Dropbox/WTO-Github/WTO-DataRelease/data'
                   '/wtoCTDSpeakerParagraphMto117_flagged.csv')

FLAG_COLS = [
    'flag_possible_missed_speaker',
    'flag_nonspeaker_entity',
    'flag_individual_name',
    'flag_ambiguous_title_only',
    'flag_null_extracted',
    'flag_topic_not_speaker',
    'flag_carryforward',
]

FLAG_LABELS = {
    'flag_possible_missed_speaker': 'Possible missed speaker',
    'flag_nonspeaker_entity':       'Non-speaker entity (committee/body)',
    'flag_individual_name':         'Individual name (not a delegation)',
    'flag_ambiguous_title_only':    'Title only (no delegation name)',
    'flag_null_extracted':          'No speaker extracted',
    'flag_topic_not_speaker':       'Topic/acronym extracted',
    'flag_carryforward':            'Carry-forward (inherited speaker)',
}

FLAG_COLORS = {
    'flag_possible_missed_speaker': '🔴',
    'flag_nonspeaker_entity':       '🟠',
    'flag_individual_name':         '🟡',
    'flag_ambiguous_title_only':    '🟡',
    'flag_null_extracted':          '🔴',
    'flag_topic_not_speaker':       '🟠',
    'flag_carryforward':            '⚪',
}

DEFAULT_FLAGS = [
    'flag_possible_missed_speaker',
    'flag_nonspeaker_entity',
    'flag_individual_name',
    'flag_ambiguous_title_only',
    'flag_null_extracted',
]


# ── Data loading / saving ──────────────────────────────────────────────────────
def load_df() -> pd.DataFrame:
    df = pd.read_csv(FLAGGED_CSV)
    if 'manual_speaker' not in df.columns:
        df['manual_speaker'] = ''
    if 'review_status' not in df.columns:
        df['review_status'] = ''
    # Coerce flag columns to bool
    for c in FLAG_COLS:
        if c in df.columns:
            df[c] = df[c].fillna(False).astype(bool)
    return df


def save_df(df: pd.DataFrame) -> None:
    df.to_csv(FLAGGED_CSV, index=False)


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_flagged(df: pd.DataFrame, selected: list[str], include_reviewed: bool) -> pd.DataFrame:
    valid = [c for c in selected if c in df.columns]
    if not valid:
        return df.iloc[0:0]
    mask = df[valid].any(axis=1)
    if not include_reviewed:
        mask &= df['review_status'].fillna('').eq('')
    return df[mask]


def filter_hash(selected: list[str], include_reviewed: bool) -> str:
    key = str(sorted(selected)) + str(include_reviewed)
    return hashlib.md5(key.encode()).hexdigest()[:8]


def get_prev_paragraph(df: pd.DataFrame, row: pd.Series) -> tuple[str | None, str | None]:
    """Return (speaker, text) for the paragraph immediately before row in same doc."""
    doc = row.get('doc')
    paranum = row.get('paranum')
    if pd.isna(doc) or pd.isna(paranum):
        return None, None
    same_doc = df[df['doc'] == doc].sort_values('paranum')
    earlier = same_doc[same_doc['paranum'] < paranum]
    if earlier.empty:
        return None, None
    prev = earlier.iloc[-1]
    spk = prev.get('proposed_speaker') or prev.get('pres.speaker') or ''
    return str(spk), str(prev['paratext'])


# ── Main app ───────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(page_title='WTO CTD Speaker Review', layout='wide')
    st.title('WTO CTD — Speaker Attribution Review')

    # Load dataframe into session state once
    if 'df' not in st.session_state:
        st.session_state.df = load_df()
    if 'pos' not in st.session_state:
        st.session_state.pos = 0
    if 'filter_hash' not in st.session_state:
        st.session_state.filter_hash = ''

    df = st.session_state.df

    # ── Sidebar ──────────────────────────────────────────────────────────────
    st.sidebar.header('Filter')
    selected_flags = st.sidebar.multiselect(
        'Show flag types',
        options=FLAG_COLS,
        default=DEFAULT_FLAGS,
        format_func=lambda c: f"{FLAG_COLORS[c]} {FLAG_LABELS[c]}",
    )
    include_reviewed = st.sidebar.checkbox('Include already-reviewed rows', value=False)

    # Reset position when filter changes
    fh = filter_hash(selected_flags, include_reviewed)
    if fh != st.session_state.filter_hash:
        st.session_state.pos = 0
        st.session_state.filter_hash = fh

    if not selected_flags:
        st.info('Select at least one flag type in the sidebar to begin.')
        return

    flagged = get_flagged(df, selected_flags, include_reviewed)
    total = len(flagged)

    if total == 0:
        st.success('✅ All rows in the selected categories have been reviewed.')
        return

    # Clamp position
    pos = min(st.session_state.pos, total - 1)
    row_idx = flagged.index[pos]
    row = df.loc[row_idx]

    # ── Sidebar progress ─────────────────────────────────────────────────────
    n_done = df.loc[flagged.index, 'review_status'].ne('').sum()
    st.sidebar.markdown('---')
    st.sidebar.markdown(f'**Progress:** {n_done} / {total} reviewed')
    st.sidebar.progress(int(n_done) / total)
    st.sidebar.markdown(f'Viewing row **{pos + 1}** of {total}')

    jump = st.sidebar.number_input(
        'Jump to row #', min_value=1, max_value=total, value=pos + 1, step=1
    )
    if jump - 1 != pos:
        st.session_state.pos = jump - 1
        st.rerun()

    # ── Flag banner ──────────────────────────────────────────────────────────
    active_flags = [c for c in FLAG_COLS if row.get(c, False)]
    badges = '  '.join(
        f"{FLAG_COLORS[c]} **{FLAG_LABELS[c]}**" for c in active_flags
    )
    st.markdown(badges)

    notes = str(row.get('flag_notes', '') or '')
    if notes.strip():
        st.caption(f'ℹ️ {notes}')

    st.divider()

    # ── Main columns: metadata | text ────────────────────────────────────────
    left, right = st.columns([1, 2])

    with left:
        st.markdown('**Meeting**')
        doc = row.get('doc', '')
        st.markdown(f'`{doc}`')
        st.markdown(
            f"Para **{row.get('paranum', '?')}** &nbsp;·&nbsp; "
            f"pid `{int(row['pid'])}` &nbsp;·&nbsp; "
            f"Year **{row.get('year', '?')}** &nbsp;·&nbsp; "
            f"M**{row.get('meetingno', '?')}**"
        )

        st.markdown('---')
        st.markdown('**Speaker attribution**')
        st.markdown(f"firstent: `{row.get('firstent', '—')}`")
        st.markdown(f"pres.speaker: `{row.get('pres.speaker', '—')}`")

        proposed = str(row.get('proposed_speaker', '') or '')
        st.markdown(f"proposed_speaker: **`{proposed or '—'}`**")

        if str(row.get('review_status', '')):
            st.markdown(
                f"manual_speaker: `{row.get('manual_speaker', '')}` ✓ {row.get('review_status')}"
            )

    with right:
        prev_spk, prev_text = get_prev_paragraph(df, row)
        if prev_text:
            with st.expander('⬆ Previous paragraph (context)', expanded=False):
                if prev_spk:
                    st.caption(f'Speaker: {prev_spk}')
                st.markdown(
                    f'<div style="font-size:0.85em;color:#555;">{prev_text[:600]}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown('**Paragraph text**')
        st.text_area(
            label='paratext',
            value=str(row['paratext']),
            height=220,
            disabled=True,
            label_visibility='collapsed',
        )

    # ── Correction input + actions ───────────────────────────────────────────
    st.divider()

    correction = st.text_input(
        'Corrected speaker — edit if needed, or leave as-is to accept the proposed value:',
        value=proposed,
        key=f'input_{row_idx}',
    )

    col_save, col_skip, col_back, col_spacer = st.columns([1.2, 1, 1, 4])

    with col_save:
        if st.button('✓ Save & next', type='primary', use_container_width=True):
            df.at[row_idx, 'manual_speaker'] = correction.strip()
            df.at[row_idx, 'review_status'] = 'reviewed'
            save_df(df)
            st.session_state.pos = min(pos + 1, total - 1)
            st.rerun()

    with col_skip:
        if st.button('→ Skip', use_container_width=True):
            df.at[row_idx, 'review_status'] = 'skipped'
            save_df(df)
            st.session_state.pos = min(pos + 1, total - 1)
            st.rerun()

    with col_back:
        if st.button('← Back', use_container_width=True):
            st.session_state.pos = max(pos - 1, 0)
            st.rerun()


if __name__ == '__main__':
    main()
