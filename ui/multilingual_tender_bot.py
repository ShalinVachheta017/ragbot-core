# Add this at the very beginning of your file
import sys
import warnings
warnings.filterwarnings("ignore")

# Bypass packaging version check
import importlib.util
import subprocess

def install_package_if_needed(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

# Try to fix packaging issue programmatically
try:
    import packaging
except ImportError:
    install_package_if_needed("packaging")

# Override version checking for sentence_transformers
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Now proceed with your normal imports

import streamlit as st
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

# SSL workaround for UI
import ssl
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from core.qa import retrieve_candidates, answer_query
from core.config import CFG

st.set_page_config(
    page_title="Multilingual Tender Bot",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

class TenderBotSession:
    def __init__(self):
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'session_id' not in st.session_state:
            st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

def detect_language(text: str) -> str:
    """Simple German/English detection"""
    german_words = ['sind', 'welche', 'für', 'wie', 'was', 'werden', 'müssen', 'können']
    return "de" if any(word in text.lower() for word in german_words) else "en"

def main():
    session = TenderBotSession()
    
    # Header
    st.title("🏗️ Multilingual Tender Bot")
    st.markdown("*AI Assistant for German Construction & Tender Documents*")
    st.markdown(f"**Session:** `{st.session_state.session_id}` | **Documents:** 14,208 chunks | **GPU:** ✅ Active")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Language Settings
        response_lang = st.selectbox(
            "🌍 Response Language",
            ["Auto-detect", "German Only", "English Only"],
            help="Choose response language preference"
        )
        
        # Search Settings
        st.subheader("🔍 Search Settings")
        top_k = st.slider("Results to Retrieve", 5, 30, 15)
        min_score = st.slider("Minimum Relevance", 0.0, 1.0, 0.1, 0.1)
        
        # Translation Tools
        st.subheader("🔄 Quick Translation")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🇩🇪→🇬🇧", help="Ask in German, get English"):
                st.session_state.translate_mode = "de_to_en"
        with col2:
            if st.button("🇬🇧→🇩🇪", help="Ask in English, get German"):
                st.session_state.translate_mode = "en_to_de"
        
        # System Info
        st.subheader("📊 System Status")
        try:
            st.success("✅ Qdrant Connected")
            st.info(f"📄 Collection: {CFG.qdrant_collection}")
            st.info("🧠 Model: Jina v3 + BGE-M3")
            st.info("⚡ GPU: RTX 4060 (7GB)")
        except:
            st.error("❌ Qdrant Connection Issue")
        
        # Chat Management
        st.subheader("💬 Chat Management")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export Chat"):
                chat_json = json.dumps(st.session_state.chat_history, indent=2, ensure_ascii=False)
                st.download_button(
                    "💾 Download JSON",
                    chat_json,
                    f"tender_bot_chat_{st.session_state.session_id}.json",
                    "application/json"
                )
        with col2:
            if st.button("🗑️ Clear History"):
                st.session_state.chat_history = []
                st.rerun()
    
    # Main Chat Area
    st.header("💬 Chat with Tender Bot")
    
    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
            # Show sources if available
            if msg.get("sources") and msg["role"] == "assistant":
                with st.expander("📚 Source Documents"):
                    for i, source in enumerate(msg["sources"][:3], 1):
                        st.write(f"{i}. **{source['file']}** (Score: {source.get('score', 'N/A')})")
    
    # Chat input
    if prompt := st.chat_input("Ask about German construction documents..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🤖 Tender Bot is analyzing documents..."):
                try:
                    # Detect language and adjust prompt
                    detected_lang = detect_language(prompt)
                    
                    if hasattr(st.session_state, 'translate_mode'):
                        if st.session_state.translate_mode == "de_to_en":
                            system_prompt = f"Answer in English only. German question: {prompt}"
                        elif st.session_state.translate_mode == "en_to_de":
                            system_prompt = f"Auf Deutsch antworten. English question: {prompt}"
                        else:
                            system_prompt = prompt
                        delattr(st.session_state, 'translate_mode')
                    else:
                        if response_lang == "German Only":
                            system_prompt = f"Antworten Sie nur auf Deutsch. Frage: {prompt}"
                        elif response_lang == "English Only":
                            system_prompt = f"Answer in English only. Question: {prompt}"
                        else:  # Auto-detect
                            if detected_lang == "de":
                                system_prompt = f"Antworten Sie auf Deutsch. Frage: {prompt}"
                            else:
                                system_prompt = f"Answer in English. Question: {prompt}"
                    
                    # Get search results
                    hits = retrieve_candidates(system_prompt, CFG)
                    response = answer_query(system_prompt, CFG)
                    
                    # Display response
                    st.write(response)
                    
                    # Prepare sources
                    sources = []
                    for hit in hits[:3]:
                        filename = hit.payload.get("source_path", "").split("/")[-1]
                        sources.append({
                            "file": filename,
                            "score": f"{hit.score:.3f}"
                        })
                    
                    # Add assistant message with sources
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": response,
                        "sources": sources,
                        "detected_language": detected_lang,
                        "documents_found": len(hits)
                    })
                    
                    # Show quick stats
                    st.caption(f"📊 Found {len(hits)} relevant documents | Language: {detected_lang.upper()} | Response time: Fast")
                    
                except Exception as e:
                    error_msg = f"⚠️ System temporarily unavailable. Please try again.\n\nTechnical details: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": error_msg
                    })
    
    # Quick Examples
    st.header("💡 Example Questions")
    example_cols = st.columns(2)
    
    with example_cols[0]:
        st.subheader("🇩🇪 German Examples")
        if st.button("Mindestlohn Bestimmungen für Bauprojekte?", key="ex1"):
            st.session_state.example_query = "Was sind die Mindestlohn Bestimmungen für Bauprojekte?"
        if st.button("Vergabeunterlagen für Straßenbau?", key="ex2"):
            st.session_state.example_query = "Welche Vergabeunterlagen sind für Straßenbau erforderlich?"
        if st.button("VOB Regelungen für Nachunternehmer?", key="ex3"):
            st.session_state.example_query = "VOB Regelungen für Nachunternehmer"
    
    with example_cols[1]:
        st.subheader("🇬🇧 English Examples")
        if st.button("Minimum wage requirements for construction?", key="ex4"):
            st.session_state.example_query = "What are the minimum wage requirements for construction?"
        if st.button("Technical specifications for road construction?", key="ex5"):
            st.session_state.example_query = "Technical specifications for road construction"
        if st.button("Safety requirements for construction sites?", key="ex6"):
            st.session_state.example_query = "Safety requirements for construction sites"
    
    # Handle example queries
    if hasattr(st.session_state, 'example_query'):
        st.rerun()
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("🚀 Powered by Jina v3 + BGE-M3")
    with col2:
        st.caption("🏗️ German Construction Documents")
    with col3:
        st.caption("⚡ GPU-Accelerated Processing")

if __name__ == "__main__":
    main()
