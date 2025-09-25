# tender_bot_ui.py
import streamlit as st
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys

# make 'core' importable when running this file directly
sys.path.append(str(Path(__file__).parent.parent))

# ---- optional SSL workaround for some Windows envs ----
import ssl, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_unverified_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx
ssl._create_default_https_context = create_unverified_context
# -------------------------------------------------------

try:
    from core.qa import retrieve_candidates, answer_query
    from core.config import CFG
    from core.search import count_points, is_alive
    SYSTEM_AVAILABLE = True
except Exception as e:
    SYSTEM_AVAILABLE = False
    st.error(f"⚠️ System temporarily unavailable: {e}")

st.set_page_config(
    page_title="Multilingual Tender Bot",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -------------------------- helpers --------------------------

def detect_language(text: str) -> str:
    """Very light DE/EN heuristic (kept from your version)."""
    german_words = ['sind', 'welche', 'für', 'wie', 'was', 'werden', 'müssen', 'können', 'ist', 'mit']
    return "de" if any(word in text.lower() for word in german_words) else "en"

def translate_text(text: str, target_lang: str) -> str:
    """
    Simple translation via Ollama (best-effort).
    target_lang: 'en' or 'de'
    """
    prompt = (
        f"Translate to English. Keep citations like [1] intact.\n\n{text}"
        if target_lang == "en"
        else f"Übersetze ins Deutsche. Zitate wie [1] unverändert lassen.\n\n{text}"
    )
    try:
        import ollama
        out = ollama.chat(model=getattr(CFG, "llm_model", "qwen2.5:1.5b"),
                          messages=[{"role": "user", "content": prompt}],
                          options={"temperature": 0.0})
        return out["message"]["content"].strip()
    except Exception:
        return text  # fall back to original if translation unavailable


# -------------------------- UI header --------------------------

st.title("🏗️ Multilingual Tender Bot")
st.markdown("*AI Assistant for German Construction & Tender Documents*")

col1, col2, col3, col4 = st.columns(4)
with col1:
    if SYSTEM_AVAILABLE and is_alive():
        st.success("✅ System Online")
    else:
        st.error("❌ System Offline")
with col2:
    try:
        pts = count_points() if SYSTEM_AVAILABLE and is_alive() else -1
        st.info(f"📄 {pts if pts >= 0 else 'n/a'} Chunks")
    except Exception:
        st.info("📄 n/a Chunks")
with col3:
    st.info("🧠 Jina v3 + BGE-M3")
with col4:
    try:
        import torch
        st.info("⚡ GPU Ready" if torch.cuda.is_available() else "⚠️ CPU Mode")
    except Exception:
        st.info("⚠️ Unknown Accelerator")

# -------------------------- sidebar --------------------------

with st.sidebar:
    st.header("⚙️ Configuration")

    # Language Settings
    st.subheader("🌍 Language Settings")
    response_lang = st.selectbox(
        "Response Language",
        ["Auto-detect", "German Only", "English Only"],
        help="Choose the language for AI responses"
    )

    # Quick Translation (applies to the *next* answer)
    st.subheader("🔄 Quick Translation")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🇩🇪→🇬🇧", help="Translate next answer DE→EN"):
            st.session_state.translate_mode = "de_to_en"
    with c2:
        if st.button("🇬🇧→🇩🇪", help="Translate next answer EN→DE"):
            st.session_state.translate_mode = "en_to_de"

    # Search / Answer settings
    st.subheader("🔍 Search Settings")
    show_sources = st.checkbox("Show Source Documents", True)
    response_detail = st.selectbox("Response Detail", ["Standard", "Detailed", "Brief"])

    # Chat Management
    st.subheader("💬 Chat Management")
    if st.button("📥 Export Chat"):
        chat_json = json.dumps(st.session_state.get("chat_history", []), indent=2, ensure_ascii=False)
        st.download_button(
            "💾 Download JSON",
            chat_json,
            f"tender_bot_{st.session_state.get('session_id', 'session')}.json",
            "application/json"
        )

    if st.button("🗑️ Clear History"):
        st.session_state.chat_history = []
        st.rerun()

    # System Info
    st.subheader("📊 System Info")
    st.caption("🚀 Jina v3 Embeddings")
    st.caption("🎯 BGE-M3 Reranker")
    st.caption("🔍 Tesseract OCR")
    st.caption("📁 Collection: " + getattr(CFG, "qdrant_collection", "(unset)"))

# -------------------------- state --------------------------

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'session_id' not in st.session_state:
    st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# -------------------------- history render --------------------------

st.header("💬 Chat Interface")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("sources") and show_sources and msg["role"] == "assistant":
            with st.expander("📚 Source Documents"):
                for i, source in enumerate(msg["sources"][:3], 1):
                    st.write(f"{i}. **{source['file']}** (Score: {source.get('score', 'N/A')})")


# -------------------------- chat input / flow --------------------------

prompt = st.chat_input("Ask about German construction documents...")
if prompt:
    # show user message
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # now answer
    with st.chat_message("assistant"):
        if not SYSTEM_AVAILABLE or not is_alive():
            error_msg = "⚠️ System temporarily unavailable. Please check the Qdrant server and try again."
            st.error(error_msg)
            st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
        else:
            with st.spinner("🤖 Analyzing German construction documents..."):
                try:
                    # 1) use the *raw user prompt* for RETRIEVAL (critical fix)
                    hits = retrieve_candidates(prompt, CFG)

                    # 2) build an answer query that controls only the *generation* style/language
                    answer_text = prompt
                    # response language preference
                    if response_lang == "German Only":
                        answer_text += " Bitte antworte auf Deutsch."
                    elif response_lang == "English Only":
                        answer_text += " Answer in English."

                    # response verbosity
                    if response_detail == "Detailed":
                        answer_text += " Provide a detailed answer."
                    elif response_detail == "Brief":
                        answer_text += " Provide a brief answer."

                    response = answer_query(answer_text, CFG)

                    # 3) optional one-shot translation of the final answer (if user pressed quick toggle)
                    tl = st.session_state.pop("translate_mode", None)
                    if tl == "de_to_en":
                        # only translate if it seems German
                        if detect_language(response) == "de":
                            response = translate_text(response, "en")
                    elif tl == "en_to_de":
                        if detect_language(response) == "en":
                            response = translate_text(response, "de")

                    # 4) display answer
                    st.write(response)

                    # 5) prepare source cards
                    sources = []
                    for hit in hits[:3]:
                        src = hit.payload.get("source_path") or ""
                        filename = Path(src).name if src else "Unknown"
                        sources.append({"file": filename, "score": f"{float(hit.score):.3f}"})

                    # 6) record assistant turn
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response,
                        "sources": sources,
                        "detected_language": detect_language(prompt),
                        "documents_found": len(hits),
                    })

                    st.caption(f"📊 Found {len(hits)} documents | Time: Fast")
                except Exception as e:
                    error_msg = f"⚠️ Search temporarily unavailable.\n\nError: {e}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})


# -------------------------- examples --------------------------

st.header("💡 Try These Examples")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🇩🇪 German Questions")
    for i, example in enumerate([
        "Was sind die Mindestlohn-Bestimmungen für Bauprojekte?",
        "Welche Vergabeunterlagen sind für Straßenbau erforderlich?",
        "VOB-Regelungen für Nachunternehmer",
    ]):
        if st.button(example, key=f"de_{i}"):
            st.session_state.chat_history.append({"role": "user", "content": example})
            # Immediately answer so the button acts like a query
            st.session_state.chat_history.append({"role": "assistant", "content": "Bitte Frage oben erneut senden (Demo-Knopf)."})
            st.rerun()

with col2:
    st.subheader("🇬🇧 English Questions")
    for i, example in enumerate([
        "What are the minimum wage requirements for construction?",
        "Technical specifications for road construction",
        "Safety requirements for construction sites",
    ]):
        if st.button(example, key=f"en_{i}"):
            st.session_state.chat_history.append({"role": "user", "content": example})
            st.session_state.chat_history.append({"role": "assistant", "content": "Please re-send the question in the chat box (demo button)."})
            st.rerun()

# -------------------------- footer --------------------------

st.markdown("---")
st.caption("🏗️ Multilingual Tender Bot | 🚀 Jina v3 + (optional) BGE-M3 | 🧠 RAG over German tender docs")
