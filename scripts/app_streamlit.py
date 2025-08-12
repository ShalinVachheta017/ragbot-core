"""
RAG Bot (Local): Qdrant + Ollama
- Multilingual (EN/DE) via E5 embeddings + your local Ollama model
- Chat-style UI with short-term memory (last K turns)
- Download buttons for cited documents
- OOD (out-of-domain) fallback to general chat with disclaimer
- Command cues: translate / explain / summarize / /clear
"""

from __future__ import annotations

import os
import json
from dataclasses import asdict
from typing import List, Dict, Any, Tuple

import streamlit as st
from langdetect import detect
import ollama  # pip install ollama

from rag_qdrant import (
    search,
    abs_source_path,
    QDRANT_URL,
    QDRANT_COLLECTION,
)

# ---------------- Page / Theme ----------------
st.set_page_config(page_title="RAG Bot (Local)", page_icon="🧠", layout="wide")

CUSTOM_CSS = """
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
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------- Sidebar ----------------
st.sidebar.title("Settings")

def list_local_models() -> List[str]:
    try:
        resp = ollama.list()
        # new API returns .models; old returned dict
        models = resp.models if hasattr(resp, "models") else resp.get("models", [])
        names = [m.model for m in models] if models and hasattr(models[0], "model") else [m["name"] for m in models]
        # put your common small models first if present
        preferred = ["qwen2.5:1.5b", "llama3.2:1b", "phi3:mini", "mistral:7b"]
        ordered = [m for m in preferred if m in names] + [m for m in names if m not in preferred]
        return ordered or ["qwen2.5:1.5b"]
    except Exception:
        return ["qwen2.5:1.5b"]

MODEL_NAME = st.sidebar.selectbox("Ollama model", list_local_models(), index=0)
top_k = st.sidebar.slider("Top-K passages", 1, 20, 5)
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
history_k = st.sidebar.slider("Use last K turns as memory", 3, 10, 5)
show_debug = st.sidebar.checkbox("Show retrieved chunks", value=False)

st.sidebar.write("---")
left, mid = st.sidebar.columns(2)
with left:
    if st.button("🧹 Clear history", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_hits = []
        st.toast("History cleared.", icon="🧽")
with mid:
    # Export chat to Markdown
    if "messages" not in st.session_state:
        st.session_state.messages = []
    md = "\n\n".join([f"**{m['role'].title()}**: {m['content']}" for m in st.session_state.messages])
    st.download_button("⬇️ Export chat (.md)", data=md, file_name="chat.md", mime="text/markdown", use_container_width=True)

st.sidebar.write("---")
st.sidebar.caption(f"Qdrant: `{QDRANT_URL}`  \nCollection: `{QDRANT_COLLECTION}`")

# ---------------- Session State ----------------
if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = []

if "last_hits" not in st.session_state:
    st.session_state.last_hits = []  # store last retrieved hits for translation/explain

# ---------------- Helpers ----------------
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
    """
    Turn hits into a numbered context string and a serializable metadata list for UI.
    """
    ctx_lines = []
    items = []
    for i, h in enumerate(hits, start=1):
        ctx_lines.append(f"[{i}] {h.text}")
        items.append({"i": i, "source": h.source, "score": round(float(h.score), 3)})
    return "\n\n".join(ctx_lines), items

def augmentation_from_history(history: List[Dict[str, str]], k: int) -> str:
    """
    Concatenate last k turns (user + assistant) to give light conversational context.
    """
    if not history:
        return ""
    tail = history[-(2*k):]  # roughly k exchanges
    lines = []
    for m in tail:
        prefix = "User:" if m["role"] == "user" else "Assistant:"
        lines.append(f"{prefix} {m['content']}")
    return "\n".join(lines)

def classify_intent(q: str) -> str:
    ql = q.strip().lower()
    if ql in {"/clear", "clear history", "reset"}:
        return "clear"
    # command cues
    if ql.startswith(("/translate", "translate ", "übersetze", "uebersetze")):
        return "translate"
    if any(ql.startswith(x) for x in ("explain", "erklaere", "erkläre")):
        return "explain"
    if any(ql.startswith(x) for x in ("summarize", "zusammenfassen", "fasse zusammen")):
        return "summarize"
    return "rag"

def llm_chat(model: str, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    resp = ollama.chat(model=model, messages=messages, options={"temperature": temperature})
    return resp["message"]["content"]

def answer_with_rag(query: str, model: str, top_k: int, temperature: float, history_text: str) -> Tuple[str, List[Any], bool]:
    """
    Try RAG first. If retrieval is weak, return (answer, hits, grounded=False) for fallback path.
    """
    hits = search(query, top_k=top_k)
    st.session_state.last_hits = hits

    # Very simple “weak” heuristic: no hits or low top score
    weak = (not hits) or (hits and float(hits[0].score) < 0.58)

    context_str, _ = build_context(hits if hits else [])
    # Build the prompt for the LLM
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history_text:
        messages.append({"role": "user", "content": f"(Recent conversation)\n{history_text}"})
    messages.append({"role": "user", "content": f"Context:\n{context_str}\n\nQuestion:\n{query}"})

    if not weak:
        txt = llm_chat(model, messages, temperature=temperature)
        return txt, hits, True
    else:
        return "", hits, False

def translate_text(text: str, model: str, to_lang: str) -> str:
    if to_lang.lower().startswith("en"):
        prompt = f"Translate the following to **English**. Keep citations like [1] intact.\n\n{text}"
    else:
        prompt = f"Übersetze den folgenden Text ins **Deutsche**. Zitiere vorhandene Belege wie [1] unverändert.\n\n{text}"
    return llm_chat(model, [{"role": "user", "content": prompt}], temperature=0.0)

def render_sources(hits):
    if not hits:
        return
    st.subheader("Sources")
    for i, h in enumerate(hits, start=1):
        with st.container(border=True):
            path = abs_source_path(h.source)
            col1, col2 = st.columns([0.84, 0.16])
            with col1:
                st.markdown(
                    f"<div class='citation'>"
                    f"<span class='score'>[{i}] score {float(h.score):.3f}</span> &nbsp;&nbsp;{h.source}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col2:
                try:
                    with open(path, "rb") as f:
                        st.download_button(
                            f"Download [{i}]",
                            data=f,
                            file_name=os.path.basename(path),
                            mime="application/pdf",
                            use_container_width=True,
                        )
                except Exception:
                    st.button("Missing file", disabled=True, use_container_width=True)

# ---------------- Header ----------------
st.title("RAG Bot (Local): Qdrant + Ollama")

# Quick tip row
with st.container(border=True):
    st.caption(
        "Tip: ensure Qdrant is healthy (`curl http://127.0.0.1:6333/readyz`) and your collection is populated. "
        "Use natural English or German. Commands: `translate ...`, `explain ...`, `summarize ...`, `/clear`."
    )

# ---------------- Chat UI ----------------
# Render prior messages
for m in st.session_state.messages:
    klass = "user-bubble" if m["role"] == "user" else "assistant-bubble"
    st.markdown(f"<div class='chat-bubble {klass}'>{m['content']}</div>", unsafe_allow_html=True)

# Translate last answer button
col_a, col_b, col_c = st.columns([0.32, 0.22, 0.46])
with col_a:
    target_lang = st.radio("Translate last answer to:", ["English", "Deutsch"], horizontal=True)
with col_b:
    disabled = not any(m["role"] == "assistant" for m in st.session_state.messages)
    if st.button("🌐 Translate last answer", disabled=disabled, use_container_width=True):
        # find last assistant message
        last_ans = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "assistant"), "")
        if last_ans:
            translated = translate_text(last_ans, MODEL_NAME, "en" if target_lang == "English" else "de")
            st.session_state.messages.append({"role": "assistant", "content": translated})
            st.rerun()

# Input box (chat style)
user_q = st.text_input("Ask your question (English or German)…", key="chat_input")
go = st.button("➤ Send", type="primary")

if go and user_q.strip():
    intent = classify_intent(user_q)

    if intent == "clear":
        st.session_state.messages = []
        st.session_state.last_hits = []
        st.toast("History cleared.", icon="🧽")
        st.rerun()

    # Log user message
    st.session_state.messages.append({"role": "user", "content": user_q})

    # Light memory
    history_text = augmentation_from_history(st.session_state.messages[:-1], history_k)

    if intent in {"translate", "explain", "summarize"}:
        # operate on last assistant message if available
        last_ans = next((m["content"] for m in reversed(st.session_state.messages[:-1]) if m["role"] == "assistant"), "")
        if not last_ans:
            st.session_state.messages.append(
                {"role": "assistant", "content": "I don't have a previous answer to operate on."}
            )
            st.rerun()

        if intent == "translate":
            # choose target by detecting last answer language
            try:
                lang = detect(last_ans)
            except Exception:
                lang = "de"
            target = "en" if lang.startswith("de") else "de"
            out = translate_text(last_ans, MODEL_NAME, target)
        elif intent == "explain":
            out = llm_chat(
                MODEL_NAME,
                [{"role": "user", "content": f"Explain the following answer more clearly:\n\n{last_ans}"}],
                temperature=temperature,
            )
        else:  # summarize
            out = llm_chat(
                MODEL_NAME,
                [{"role": "user", "content": f"Summarize the following answer in 3 bullets:\n\n{last_ans}"}],
                temperature=temperature,
            )
        st.session_state.messages.append({"role": "assistant", "content": out})
        st.rerun()

    # ---------- RAG attempt ----------
    grounded_text, hits, grounded = answer_with_rag(
        query=user_q, model=MODEL_NAME, top_k=top_k, temperature=temperature, history_text=history_text
    )

    if grounded:
        st.session_state.messages.append({"role": "assistant", "content": grounded_text})
        st.rerun()
    else:
        # ---------- Fallback ----------
        warn = "⚠️ This answer is **not grounded** in your private documents."
        st.session_state.messages.append({"role": "assistant", "content": f"<div class='warn'>{warn}</div>"})

        # Provide a general-chat answer
        fallback_messages = [{"role": "system", "content": FALLBACK_PROMPT}]
        if history_text:
            fallback_messages.append({"role": "user", "content": f"(Recent conversation)\n{history_text}"})
        fallback_messages.append({"role": "user", "content": user_q})
        out = llm_chat(MODEL_NAME, fallback_messages, temperature=temperature)
        st.session_state.messages.append({"role": "assistant", "content": out})
        st.rerun()

# After response render sources + debug
if st.session_state.last_hits:
    render_sources(st.session_state.last_hits)
    if show_debug:
        st.markdown("### Retrieved chunks")
        for i, h in enumerate(st.session_state.last_hits, start=1):
            st.markdown(f"**[{i}]** `{h.source}` &nbsp;&nbsp; *score {float(h.score):.3f}*")
            st.code(h.text)
