# ui/multilingual_tender_bot.py
from __future__ import annotations
import sys, re
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd

from core.config import CFG
from core.qa import retrieve_candidates, answer_query

# ---------- Page ----------
st.set_page_config(page_title="Multilingual Tender Bot", page_icon="🏗️", layout="wide")
st.title("🏗️ Multilingual Tender Bot")
st.caption("AI Assistant for German Construction & Tender Documents (Qdrant + Jina v3 + optional BGE-M3)")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")

    # Language routing
    route = st.radio(
        "Retrieval Strategy",
        ["Dual (Original + German, RRF)", "German-only (translate EN→DE)", "Original only"],
        index=0,
        help="Your data is German-first. Dual retrieval is safest."
    )
    if route == "Dual (Original + German, RRF)":
        CFG.dual_query = True
        CFG.force_german_retrieval = False
    elif route == "German-only (translate EN→DE)":
        CFG.dual_query = False
        CFG.force_german_retrieval = True
    else:
        CFG.dual_query = False
        CFG.force_german_retrieval = False

    top_k = st.slider("Top-K passages", 4, 24, CFG.final_k)
    CFG.final_k = top_k  # keep UI in control

    show_sources = st.checkbox("Show sources", value=True)
    st.caption(f"Qdrant: `{CFG.qdrant_url}`")
    st.caption(f"Collection: `{CFG.qdrant_collection}`")

# ---------- Session ----------
if "chat" not in st.session_state:
    st.session_state.chat = []

# ---------- Chat History ----------
for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if m.get("hits") and show_sources:
            with st.expander("📚 Sources"):
                for i, h in enumerate(m["hits"][:5], 1):
                    src = h.payload.get("source_path", "") or h.payload.get("source", "")
                    page = h.payload.get("page_start") or h.payload.get("page")
                    score = float(h.score)
                    st.markdown(f"{i}. **{Path(src).name}** {f'(p{page})' if page else ''} — *score {score:.3f}*")

# ---------- Input ----------
q = st.chat_input("Ask in English or German…")
if q:
    st.session_state.chat.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.write(q)

    with st.chat_message("assistant"):
        with st.spinner("Searching your tender corpus…"):
            try:
                hits = retrieve_candidates(q, CFG)
                text = answer_query(q, CFG)

                st.write(text)
                st.session_state.chat.append({"role": "assistant", "content": text, "hits": hits})
                if show_sources and hits:
                    with st.expander("📚 Sources"):
                        for i, h in enumerate(hits[:5], 1):
                            src = h.payload.get("source_path", "") or h.payload.get("source", "")
                            page = h.payload.get("page_start") or h.payload.get("page")
                            score = float(h.score)
                            st.markdown(f"{i}. **{Path(src).name}** {f'(p{page})' if page else ''} — *score {score:.3f}*")
            except Exception as e:
                st.error(f"⚠️ Retrieval temporarily unavailable.\n\n`{e}`")
