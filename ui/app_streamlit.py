from __future__ import annotations

# ---- CRITICAL: Apply packaging workaround BEFORE any other imports ----
import importlib.metadata as _im
_original_version = _im.version
def _patched_version(dist_name: str) -> str:
    if dist_name.lower() == 'packaging':
        return '24.0'
    return _original_version(dist_name)
_im.version = _patched_version

# ---- CRITICAL: Streamlit FIRST ----
import streamlit as st
st.set_page_config(page_title="Tender Bot (Local)", page_icon="🧠", layout="wide")

# app_streamlit.py
"""
RAG Bot (Local): Qdrant + Ollama
- Jina v3 embeddings + DTAD-aware filtering in search
- Metadata-aware routing (DTAD-ID + Region/Year queries)
"""

import os, re, logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import sys
import pandas as pd

# ---- import shim so 'core' is always importable ----
ROOT = Path(__file__).resolve().parent.parent  # project root
for p in (ROOT, ROOT / "core"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from core.config import CFG
from core.qa import retrieve_candidates  # NEW retriever

# --- Logging ---
logger = logging.getLogger("app_streamlit")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# --- Load metadata (normalized) ---
def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().replace(" ", "_").replace("-", "_").lower() for c in df.columns]
    return df

try:
    meta_path = CFG.metadata_path  # e.g., metadata/cleaned_metadata.xlsx
except AttributeError:
    # backward-compat if metadata_path property not present
    meta_path = CFG.metadata_dir / "cleaned_metadata.xlsx"

try:
    if Path(meta_path).exists():
        metadata_df = pd.read_excel(meta_path)
        metadata_df = _normalize_cols(metadata_df)
        logger.info(f"Loaded metadata from {meta_path}, {len(metadata_df)} rows")
    else:
        logger.warning(f"Metadata not found at {meta_path}")
        metadata_df = pd.DataFrame()
except Exception as e:
    logger.error(f"Could not load metadata: {e}")
    metadata_df = pd.DataFrame()

# Dynamic region dictionary (normalized)
region_list = sorted(
    {str(r).strip().lower() for r in (metadata_df.get("region", []) if not metadata_df.empty else []) if pd.notna(r)}
)

# --- Streamlit Page Styling ---
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] { background: #0e0f13; }
.block-container { padding-top: 1.3rem; }
.chat-bubble { border-radius: 14px; padding: 12px 14px; margin: 6px 0 14px 0; }
.user-bubble { background: #111827; border: 1px solid #2f3b52; }
.assistant-bubble { background: #0f172a; border: 1px solid #24334a; }
.citation { background: #101826; border: 1px solid #263255; color: #a1b1d0; font-size: 0.92rem; padding: 10px; margin-top: 8px; }
.score { color: #8ee88a; font-weight: 600; }
.warn { background: #1d1b10; border: 1px solid #544b22; color: #e5d480; padding: 10px 12px; border-radius: 12px; }
hr { border-color: #243043; }
</style>
""",
    unsafe_allow_html=True,
)

# ---- helpers ----
def list_local_models() -> List[str]:
    try:
        import ollama  # lazy import so app still runs without it
        resp = ollama.list()
        models = resp.models if hasattr(resp, "models") else resp.get("models", [])
        names = [m.model for m in models] if models and hasattr(models[0], "model") else [m["name"] for m in models]
        preferred = ["qwen2.5:1.5b", "llama3.2:1b", "phi3:mini"]
        return [m for m in preferred if m in names] + [m for m in names if m not in preferred]
    except Exception:
        return ["qwen2.5:1.5b"]

def abs_source_path(src: str) -> Path:
    """Resolve a payload 'source_path' to a local file under extract/ if needed."""
    p = Path(src) if src else Path("")
    if p.exists():
        return p
    return (CFG.extract_dir / p.name) if p.name else CFG.extract_dir

def llm_chat(model: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    # prefer Ollama python client
    try:
        import ollama
        resp = ollama.chat(model=model, messages=messages, options={"temperature": temperature})
        return resp["message"]["content"]
    except Exception as e_client:
        # HTTP fallback
        try:
            import requests, json
            r = requests.post(
                "http://127.0.0.1:11434/api/chat",
                json={"model": model, "messages": messages, "options": {"temperature": temperature}},
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            if "message" in data and "content" in data["message"]:
                return data["message"]["content"]
            return json.dumps(data)[:2000]
        except Exception as e_http:
            return f"(Ollama unavailable: {e_client} | HTTP: {e_http})"

# --- Sidebar ---
st.sidebar.title("Settings")

MODEL_NAME = st.sidebar.selectbox("Ollama model", list_local_models(), index=0)
top_k = st.sidebar.slider("Top-K passages", 1, 20, int(getattr(CFG, "top_k", 8)))
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
history_k = st.sidebar.slider("Use last K turns as memory", 2, 8, 3)
show_debug = st.sidebar.checkbox("Show retrieved chunks", value=False)

st.sidebar.write("---")
left, mid = st.sidebar.columns(2)
with left:
    if st.button("🧹 Clear history", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_hits = []
        st.toast("History cleared.", icon="🧽")
with mid:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    md = "\n\n".join([f"**{m['role'].title()}**: {m['content']}" for m in st.session_state.messages])
    st.download_button(
        "⬇️ Export chat (.md)",
        data=md,
        file_name="chat.md",
        mime="text/markdown",
        use_container_width=True,
    )

st.sidebar.write("---")
st.sidebar.caption(f"Qdrant: `{CFG.qdrant_url}`  \nCollection: `{CFG.qdrant_collection}`")

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = []
if "last_hits" not in st.session_state:
    st.session_state.last_hits = []

# --- Prompts ---
SYSTEM_PROMPT = (
    "You are a tender assistant. Answer ONLY from the provided context below. "
    "Do not use prior knowledge or external information. "
    "If the answer cannot be found in the context, respond exactly with: 'Not in the tender data.' "
    "Always cite sources with bracket numbers [1], [2] that match the context list. "
    "Never make assumptions or invent facts. "
    "Always answer in the SAME language as the user question. "
    "If multiple IDs or dates appear, only report the ones explicitly matching the user’s query. "
    "If no exact match is found, reply: 'Not in the tender data.' "
    "If multiple dates/values appear for the same ID, cite them exactly as written, without interpretation."
)

FALLBACK_PROMPT = (
    "You are a friendly assistant. The user might be asking something outside of the tender documents. "
    "If the question is NOT related to tender data, you may answer generally. "
    "But if the question IS related to tenders, and no supporting context is available, "
    "always respond with: 'Not in the tender data.' "
    "Never invent tender-specific facts or details."
)

# --- Helpers ---
def build_context(hits) -> Tuple[str, List[Dict[str, Any]]]:
    ctx_lines, items = [], []
    for i, h in enumerate(hits, start=1):
        ctx_lines.append(f"[{i}] {h.text}")
        items.append({"i": i, "source": h.source, "score": round(float(h.score), 3)})
    return "\n\n".join(ctx_lines), items

def augmentation_from_history(history: List[Dict[str, str]], k: int) -> str:
    if not history:
        return ""
    tail = history[-(2 * k) :]
    return "\n".join([f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in tail])

def _dtad_match(df: pd.DataFrame, raw_id: str) -> pd.DataFrame:
    """
    Robust match for DTAD-ID:
      - Treat as string, strip, remove trailing '.0' if any
      - Zero-pad to 8 chars
    """
    if "dtad_id" not in df.columns:
        return df.iloc[0:0]
    want = str(raw_id).strip()
    want = re.sub(r"\.0$", "", want)
    want = want.zfill(8) if want.isdigit() else want

    col = df["dtad_id"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    col = col.str.zfill(8).where(col.str.isnumeric(), col)  # keep non-numeric as-is
    return df[col == want]

def lookup_metadata(query: str) -> str | None:
    """Answer structured queries from metadata (DTAD-ID, year, region)."""
    if metadata_df.empty:
        return None

    q_lower = query.lower()

    # 1) Exact DTAD-ID lookup
    m = re.search(r"\b(\d{7,8})\b", query)
    if m:
        row = _dtad_match(metadata_df, m.group(1))
        if not row.empty:
            r = row.iloc[0]
            logger.info(f"Metadata hit for DTAD-ID {m.group(1)}")
            return (
                f"DTAD-ID {str(r.get('dtad_id','')).zfill(8)} | "
                f"Titel: {r.get('titel','')} | "
                f"Datum: {r.get('datum','')} | "
                f"Region: {r.get('region','')} | "
                f"Vergabestelle: {r.get('name_der_vergabestelle') or r.get('vergabestelle__komplett','')} | "
                f"Quelle: {r.get('source_url','')}"
            )
        else:
            logger.warning(f"DTAD-ID {m.group(1)} not found in metadata")
            return "Not in the tender data."

    # 2) Year + Region filters
    df = metadata_df.copy()
    # Year: prefer derived 'year' if present, else substring on 'datum'
    y_match = re.search(r"(20\d{2})", query)
    if y_match:
        if "year" in df.columns:
            try:
                y = int(y_match.group(1))
                df = df[df["year"] == y]
            except Exception:
                pass
        elif "datum" in df.columns:
            df = df[df["datum"].astype(str).str.contains(y_match.group(1), na=False)]

    # Region by substring match
    for region in region_list:
        if region and region in q_lower and "region" in df.columns:
            df = df[df["region"].astype(str).str.lower().str.contains(region, na=False)]
            break

    if not df.empty and (y_match or any(r in q_lower for r in region_list)):
        logger.info(f"Metadata hit for region/year query: {query}")
        # show top 5
        lines = []
        for _, r in df.head(5).iterrows():
            lines.append(
                f"DTAD-ID {str(r.get('dtad_id','')).zfill(8)} | "
                f"Titel: {r.get('titel','')} | "
                f"Datum: {r.get('datum','')} | "
                f"Region: {r.get('region','')} | "
                f"Quelle: {r.get('source_url','')}"
            )
        return "\n".join(lines)

    return None  # fallback to retrieval

def answer_with_rag(query: str, model: str, top_k: int, temperature: float, history_text: str):
    # Step 1: Metadata route
    meta_answer = lookup_metadata(query)
    if meta_answer:
        return meta_answer, [], True

    # Step 2: Dense retrieval via core.qa
    hits = retrieve_candidates(query, CFG)[:top_k]
    st.session_state.last_hits = hits
    weak = (not hits) or (float(hits[0].score) < 0.58)

    context_str, _ = build_context(hits if hits else [])
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history_text:
        messages.append({"role": "user", "content": f"(Recent conversation)\n{history_text}"})
    messages.append({"role": "user", "content": f"Context:\n{context_str}\n\nQuestion:\n{query}"})

    if not weak:
        logger.info("Qdrant hit")
        return llm_chat(model, messages, temperature), hits, True

    logger.warning("Fallback path used")
    return "Not in the tender data.", hits, False

def render_sources(hits):
    if not hits:
        return
    st.subheader("Sources")
    for i, h in enumerate(hits, start=1):
        with st.container(border=True):
            path = abs_source_path(h.source)
            c1, c2 = st.columns([0.84, 0.16])
            with c1:
                page = f" (page {h.page})" if h.page is not None else ""
                st.markdown(
                    f"<div class='citation'><span class='score'>[{i}] score {float(h.score):.3f}</span> &nbsp;&nbsp;{h.source}{page}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                if path.exists() and path.is_file():
                    data = path.read_bytes()
                    st.download_button(
                        f"Download [{i}]",
                        data=data,
                        file_name=os.path.basename(path),
                        mime="application/pdf",
                        key=f"dl_{i}_{os.path.basename(path)}",
                        use_container_width=True,
                    )
                else:
                    st.button("Missing file", disabled=True, use_container_width=True)

# --- Header + Chat UI ---
st.title("RAG Bot (Local): Qdrant + Ollama")
with st.container(border=True):
    st.caption(
        "Tip: ensure Qdrant is healthy (`curl http://127.0.0.1:6333/readyz`) and your collection is populated. "
        "Use English or German. Commands: `translate ...`, `explain ...`, `summarize ...`, `/clear`."
    )

for m in st.session_state.messages:
    klass = "user-bubble" if m["role"] == "user" else "assistant-bubble"
    st.markdown(f"<div class='chat-bubble {klass}'>{m['content']}</div>", unsafe_allow_html=True)

col_a, col_b, col_c = st.columns([0.32, 0.22, 0.46])
with col_a:
    target_lang = st.radio("Translate last answer to:", ["English", "Deutsch"], horizontal=True)
with col_b:
    disabled = not any(m["role"] == "assistant" for m in st.session_state.messages)
    if st.button("🌐 Translate last answer", disabled=disabled, use_container_width=True):
        last_ans = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")
        if last_ans:
            prompt = (
                f"Translate the following to **English**. Keep citations like [1] intact.\n\n{last_ans}"
                if target_lang == "English"
                else f"Übersetze den folgenden Text ins **Deutsche**. Zitiere vorhandene Belege wie [1] unverändert.\n\n{last_ans}"
            )
            translated = llm_chat(MODEL_NAME, [{"role": "user", "content": prompt}], temperature=0.0)
            st.session_state.messages.append({"role": "assistant", "content": translated})
            st.rerun()

user_q = st.text_input("Ask your question (English or German)…", key="chat_input")
go = st.button("➤ Send", type="primary")

if go and user_q.strip():
    if user_q.strip().lower() in {"/clear", "clear history", "reset"}:
        st.session_state.messages, st.session_state.last_hits = [], []
        st.toast("History cleared.", icon="🧽")
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": user_q})
    hist = st.session_state.messages[:-1]
    history_text = " \n".join([f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in hist[-(2 * history_k) :]])

    grounded_text, hits, grounded = answer_with_rag(user_q, MODEL_NAME, top_k, temperature, history_text)
    if grounded:
        st.session_state.messages.append({"role": "assistant", "content": grounded_text})
        st.rerun()
    else:
        warn = "⚠️ This answer is **not grounded** in your private documents."
        st.session_state.messages.append({"role": "assistant", "content": f"<div class='warn'>{warn}</div>"})
        out = llm_chat(
            MODEL_NAME,
            [{"role": "system", "content": FALLBACK_PROMPT}, {"role": "user", "content": user_q}],
            temperature=temperature,
        )
        st.session_state.messages.append({"role": "assistant", "content": out})
        st.rerun()

if st.session_state.last_hits:
    render_sources(st.session_state.last_hits)
    if show_debug:
        st.markdown("### Retrieved chunks")
        for i, h in enumerate(st.session_state.last_hits, start=1):
            st.markdown(f"**[{i}]** `{h.source}` *(score {float(h.score):.3f})*")
            st.code(h.text)
