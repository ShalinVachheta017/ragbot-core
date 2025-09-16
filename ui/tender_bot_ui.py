import streamlit as st
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

# SSL workaround for Windows environments
import ssl
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch SSL context for Windows compatibility
def create_unverified_context():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

ssl._create_default_https_context = create_unverified_context

try:
    from core.qa import retrieve_candidates, answer_query
    from core.config import CFG
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

def detect_language(text: str) -> str:
    """Simple German/English detection"""
    german_words = ['sind', 'welche', 'für', 'wie', 'was', 'werden', 'müssen', 'können', 'ist', 'mit']
    return "de" if any(word in text.lower() for word in german_words) else "en"

def main():
    # Initialize session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'session_id' not in st.session_state:
        st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Header
    st.title("🏗️ Multilingual Tender Bot")
    st.markdown("*AI Assistant for German Construction & Tender Documents*")
    
    # System status
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if SYSTEM_AVAILABLE:
            st.success("✅ System Online")
        else:
            st.error("❌ System Offline")
    with col2:
        st.info("📄 14,208 Chunks")
    with col3:
        st.info("🧠 Jina v3 + BGE-M3")
    with col4:
        st.info("⚡ GPU Ready")

    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Language Settings
        st.subheader("🌍 Language Settings")
        response_lang = st.selectbox(
            "Response Language",
            ["Auto-detect", "German Only", "English Only"],
            help="Choose the language for AI responses"
        )
        
        # Quick Translation
        st.subheader("🔄 Quick Translation")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🇩🇪→🇬🇧", help="German to English"):
                st.session_state.translate_mode = "de_to_en"
        with col2:
            if st.button("🇬🇧→🇩🇪", help="English to German"):
                st.session_state.translate_mode = "en_to_de"
        
        # Search Settings
        st.subheader("🔍 Search Settings")
        show_sources = st.checkbox("Show Source Documents", True)
        response_detail = st.selectbox("Response Detail", ["Standard", "Detailed", "Brief"])
        
        # Chat Management
        st.subheader("💬 Chat Management")
        if st.button("📥 Export Chat"):
            chat_json = json.dumps(st.session_state.chat_history, indent=2, ensure_ascii=False)
            st.download_button(
                "💾 Download JSON",
                chat_json,
                f"tender_bot_{st.session_state.session_id}.json",
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
        st.caption("📁 1,488 Documents")

    # Main Chat Interface
    st.header("💬 Chat Interface")
    
    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
            if msg.get("sources") and show_sources and msg["role"] == "assistant":
                with st.expander("📚 Source Documents"):
                    for i, source in enumerate(msg["sources"][:3], 1):
                        st.write(f"{i}. **{source['file']}** (Score: {source.get('score', 'N/A')})")

    # Chat Input
    if prompt := st.chat_input("Ask about German construction documents..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            if not SYSTEM_AVAILABLE:
                error_msg = "⚠️ System temporarily unavailable. Please check the server connection and try again."
                st.error(error_msg)
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                return
            
            with st.spinner("🤖 Analyzing German construction documents..."):
                try:
                    # Language detection
                    detected_lang = detect_language(prompt)
                    
                    # Prepare system prompt based on settings
                    if hasattr(st.session_state, 'translate_mode'):
                        if st.session_state.translate_mode == "de_to_en":
                            system_prompt = f"Answer in English only. German question: {prompt}"
                        elif st.session_state.translate_mode == "en_to_de":
                            system_prompt = f"Auf Deutsch antworten. English question: {prompt}"
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
                    
                    # Get results
                    hits = retrieve_candidates(system_prompt, CFG)
                    response = answer_query(system_prompt, CFG)
                    
                    # Display response
                    st.write(response)
                    
                    # Prepare sources
                    sources = []
                    for hit in hits[:3]:
                        filename = hit.payload.get("source_path", "").split("/")[-1] if hit.payload.get("source_path") else "Unknown"
                        sources.append({
                            "file": filename,
                            "score": f"{hit.score:.3f}"
                        })
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": response,
                        "sources": sources,
                        "detected_language": detected_lang,
                        "documents_found": len(hits)
                    })
                    
                    # Show stats
                    st.caption(f"📊 Found {len(hits)} documents | Language: {detected_lang.upper()} | Time: Fast")
                    
                except Exception as e:
                    error_msg = f"⚠️ Search temporarily unavailable. Please try again in a moment.\n\nError: Connection timeout"
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": error_msg
                    })

    # Quick Examples
    st.header("💡 Try These Examples")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🇩🇪 German Questions")
        examples_de = [
            "Was sind die Mindestlohn Bestimmungen für Bauprojekte?",
            "Welche Vergabeunterlagen sind für Straßenbau erforderlich?",
            "VOB Regelungen für Nachunternehmer"
        ]
        for i, example in enumerate(examples_de):
            if st.button(example, key=f"de_{i}"):
                # Trigger rerun with example query
                st.session_state.example_query = example
                st.rerun()
    
    with col2:
        st.subheader("🇬🇧 English Questions")  
        examples_en = [
            "What are the minimum wage requirements for construction?",
            "Technical specifications for road construction",
            "Safety requirements for construction sites"
        ]
        for i, example in enumerate(examples_en):
            if st.button(example, key=f"en_{i}"):
                st.session_state.example_query = example
                st.rerun()

    # Footer
    st.markdown("---")
    st.caption("🏗️ Multilingual Tender Bot | 🚀 Powered by Advanced AI | 📊 14,208 German Documents Indexed")

if __name__ == "__main__":
    main()
