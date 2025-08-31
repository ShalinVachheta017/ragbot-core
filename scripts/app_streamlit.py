"""
RAG Bot (Local): Qdrant + Ollama
- E5 embeddings + DTAD-aware filtering in search
- Robust UI: unique keys for download buttons
"""
from __future__ import annotations
import os
from typing import List, Dict, Any, Tuple
import streamlit as st
from langdetect import detect
import ollama

from rag_qdrant import search, abs_source_path, QDRANT_COLLECTION
from config import QDRANT_URL

# ------------- Page / Theme -------------
st.set_page_config(page_title="RAG Bot (Local)", page_icon="🧠", layout="wide")
st.markdown("""
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
""", unsafe_allow_html=True)

# ------------- Sidebar -------------
st.sidebar.title("Settings")

def list_local_models() -> List[str]:
    try:
        resp = ollama.list()
        models = resp.models if hasattr(resp, "models") else resp.get("models", [])
        names = [m.model for m in models] if models and hasattr(models[0], "model") else [m["name"] for m in models]
        preferred = ["qwen2.5:1.5b", "llama3.2:1b", "phi3:mini", "mistral:7b"]
        return [m for m in preferred if m in names] + [m for m in names if m not in preferred]
    except Exception:
        return ["qwen2.5:1.5b"]

MODEL_NAME = st.sidebar.selectbox("Ollama model", list_local_models(), index=0)
top_k = st.sidebar.slider("Top-K passages", 1, 20, 8)            # default 8
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
    st.download_button("⬇️ Export chat (.md)", data=md, file_name="chat.md", mime="text/markdown", use_container_width=True)

st.sidebar.write("---")
st.sidebar.caption(f"Qdrant: `{QDRANT_URL}`  \nCollection: `{QDRANT_COLLECTION}`")

# ------------- Session State -------------
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = []
if "last_hits" not in st.session_state:
    st.session_state.last_hits = []

# ------------- Prompts & helpers -------------
SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question using ONLY the provided context. "
    "Cite sources with bracket numbers like [1], [2] that match the context list. "
    "If the answer isn't in the context, say you don't know.\n"
    "You can answer in English or German depending on the user's request."
)
FALLBACK_PROMPT = (
    "You are a friendly assistant. The user might be asking something outside of the provided documents. "
    "Provide a helpful answer, but do not invent facts about the private tender data."
)

def build_context(hits) -> Tuple[str, List[Dict[str, Any]]]:
    ctx_lines, items = [], []
    for i, h in enumerate(hits, start=1):
        ctx_lines.append(f"[{i}] {h.text}")
        items.append({"i": i, "source": h.source, "score": round(float(h.score), 3)})
    return "\n\n".join(ctx_lines), items

def augmentation_from_history(history: List[Dict[str, str]], k: int) -> str:
    if not history: return ""
    tail = history[-(2*k):]
    lines = []
    for m in tail:
        prefix = "User:" if m["role"] == "user" else "Assistant:"
        lines.append(f"{prefix} {m['content']}")
    return "\n".join(lines)

def llm_chat(model: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    resp = ollama.chat(model=model, messages=messages, options={"temperature": temperature})
    return resp["message"]["content"]

def answer_with_rag(query: str, model: str, top_k: int, temperature: float, history_text: str):
    hits = search(query, top_k=top_k)
    st.session_state.last_hits = hits
    weak = (not hits) or (float(hits[0].score) < 0.58)

    context_str, _ = build_context(hits if hits else [])
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history_text:
        messages.append({"role": "user", "content": f"(Recent conversation)\n{history_text}"})
    messages.append({"role": "user", "content": f"Context:\n{context_str}\n\nQuestion:\n{query}"})

    if not weak:
        return llm_chat(model, messages, temperature), hits, True
    return "", hits, False

def translate_text(text: str, model: str, to_lang: str) -> str:
    prompt = (f"Translate the following to **English**. Keep citations like [1] intact.\n\n{text}"
              if to_lang.lower().startswith("en")
              else f"Übersetze den folgenden Text ins **Deutsche**. Zitiere vorhandene Belege wie [1] unverändert.\n\n{text}")
    return llm_chat(model, [{"role": "user", "content": prompt}], temperature=0.0)

def render_sources(hits):
    if not hits: return
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
                if path.exists():
                    data = path.read_bytes()
                    st.download_button(
                        f"Download [{i}]",
                        data=data,
                        file_name=os.path.basename(path),
                        mime="application/pdf",
                        key=f"dl_{i}_{os.path.basename(path)}",  # unique key per widget
                        use_container_width=True,
                    )
                else:
                    st.button("Missing file", disabled=True, use_container_width=True)

# ------------- Header + chat UI -------------
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
            translated = translate_text(last_ans, MODEL_NAME, "en" if target_lang == "English" else "de")
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
    # Light memory
    hist = st.session_state.messages[:-1]
    history_text = (" \n".join([f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in hist[-(2*history_k):]]))

    # RAG
    grounded_text, hits, grounded = answer_with_rag(user_q, MODEL_NAME, top_k, temperature, history_text)
    if grounded:
        st.session_state.messages.append({"role": "assistant", "content": grounded_text})
        st.rerun()
    else:
        warn = "⚠️ This answer is **not grounded** in your private documents."
        st.session_state.messages.append({"role": "assistant", "content": f"<div class='warn'>{warn}</div>"})
        out = llm_chat(MODEL_NAME, [{"role": "user", "content": user_q}], temperature=temperature)
        st.session_state.messages.append({"role": "assistant", "content": out})
        st.rerun()

if st.session_state.last_hits:
    render_sources(st.session_state.last_hits)
    if show_debug:
        st.markdown("### Retrieved chunks")
        for i, h in enumerate(st.session_state.last_hits, start=1):
            st.markdown(f"**[{i}]** `{h.source}` *(score {float(h.score):.3f})*")
            st.code(h.text)
