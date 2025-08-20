# scripts/app_streamlit.py
import os
import textwrap
import requests
import streamlit as st
import re


# absolute import so it works when run via `streamlit run scripts/app_streamlit.py`
try:
    from scripts.rag_qdrant import search, info, Hit
except ImportError:
    # fallback if run from inside scripts/
    import sys, os
    sys.path.append(os.path.dirname(__file__))
    from rag_qdrant import search, info, Hit


# ---------- Page ----------
st.set_page_config(page_title="VergabeNerd RAG (Qdrant)", layout="wide")
st.title("VergabeNerd — Local RAG (Qdrant DB)")

# ---------- Sidebar ----------
meta = info()
st.sidebar.subheader("Backend")
st.sidebar.write(f"**Qdrant:** {meta['qdrant_url']}")
st.sidebar.write(f"**Collection:** {meta['collection']}")
st.sidebar.write(f"**Embedder:** {meta['embed_model']}")
st.sidebar.write(f"**Reranker:** {meta['rerank_model']}")

top_k = st.sidebar.slider("Top-K results", min_value=3, max_value=20, value=7)
initial_top_k = st.sidebar.slider("Initial candidates (for rerank)", min_value=10, max_value=200, value=50, step=10)
lang_only_de = st.sidebar.checkbox("German-only retrieval (lang=de)", value=False)

st.sidebar.markdown("---")
use_llm = st.sidebar.checkbox("Compose answer via Ollama", value=False)
ollama_model = st.sidebar.text_input("Ollama model", value=os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"))

st.sidebar.markdown("---")
cpv = st.sidebar.text_input("Filter: CPV code (exact match)", value="")
filename = st.sidebar.text_input("Filter: filename contains", value="")

st.sidebar.markdown("---")
show_payload = st.sidebar.checkbox("Show raw payload", value=False)

# ---------- Input ----------
query = st.text_input("🔎 Your question", value="", placeholder="Ask about a tender…")


# ---------- Helpers ----------
def build_filters():
    f = {}
    if lang_only_de:
        f["lang"] = "de"
    if cpv.strip():
        f["cpv"] = cpv.strip()
    return f or None


def call_ollama(model: str, prompt: str) -> str:
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except Exception as e:
        return f"[LLM error: {e}]"


def make_prompt(q: str, hits: list[Hit]) -> str:
    # Build numbered context for stable [1], [2], ...
    ctx_lines = []
    for i, h in enumerate(hits, 1):
        ctx_lines.append(f"[{i}] {h.source} | score={h.score:.3f}\n{h.text}")
    ctx_text = "\n\n".join(ctx_lines)

    q_lower = q.lower()

    # ---- Intent: deadline + submission form ----
    if re.search(r"(angebots(abgabe)?frist|submission deadline|deadline for submission)", q_lower):
        return f"""
You are a careful assistant. Use ONLY the CONTEXT to answer the QUESTION.

TASK
- Extract two items if present:
  1) Angebotsabgabefrist / submission deadline (date + time)
  2) Form der Angebotsabgabe / submission channel (eVergabe portal / email / postal / in person)
- If one item is NOT present, write: "not specified in the provided context".

RULES
- Never invent information; quote exact dates/times as written.
- After every fact, include bracket citations like [1], [2] that refer to the numbered CONTEXT items.
- Answer concisely in the language of the QUESTION.

QUESTION
{q}

CONTEXT
{ctx_text}

FORMAT
- Form: <portal/email/postal/...> [n]
- Frist: <DD.MM.YYYY, HH:MM> [n]
""".strip()

    # ---- Intent: award criteria (Zuschlagskriterien) ----
    if re.search(r"(zuschlagskriterien|award criteria)", q_lower):
        return f"""
You are a careful assistant. Use ONLY the CONTEXT to answer the QUESTION.

TASK
- Extract the award criteria and their weights if available.
- If a weight is not stated, write "Gewichtung nicht angegeben" (or "weight not specified").
- Return a clean bullet list.

RULES
- Do not invent values; only use what is in CONTEXT.
- Include bracket citations [n] for each bullet, pointing to the numbered CONTEXT items.
- Answer in the language of the QUESTION.

QUESTION
{q}

CONTEXT
{ctx_text}

FORMAT
- <Criterion>: <XX% / Gewichtung nicht angegeben> [n]
""".strip()

    # ---- Generic fallback ----
    return f"""
You are a careful assistant. Use ONLY the CONTEXT to answer the QUESTION.

TASK
- Answer the QUESTION concisely using facts from CONTEXT.
- Prefer bullet points. Quote exact dates/numbers as written.
- If information is missing, write "not specified in the provided context".

RULES
- Never invent information.
- Include bracket citations like [1], [2] after the facts.

QUESTION
{q}

CONTEXT
{ctx_text}
""".strip()

    # numbered context so bracket citations [1], [2] are stable
    ctx_lines = []
    for i, h in enumerate(hits, 1):
        ctx_lines.append(f"[{i}] {h.source} | score={h.score:.3f}\n{h.text}")
    ctx_text = "\n\n".join(ctx_lines)

    return f"""
You are a careful assistant. Use ONLY the CONTEXT to answer the QUESTION.

TASK
- Extract two items if present in the context:
  1) Angebotsabgabefrist / submission deadline (date + time)
  2) Form der Angebotsabgabe / submission channel (eVergabe portal / email / postal / in person)
- If one item is NOT present in the context, write: "not specified in the provided context".

RULES
- Never invent information; quote exact dates/times as written.
- After every fact, include bracket citations like [1], [2] that refer to the numbered CONTEXT items.
- Answer concisely in the language of the QUESTION.

QUESTION
{q}

CONTEXT
{ctx_text}

FORMAT
- Form: <portal/email/postal/...> [n]
- Frist: <DD.MM.YYYY, HH:MM> [n]
""".strip()


# ---------- Action ----------
if query:
    with st.spinner("Searching…"):
        filters = build_filters()
        hits = search(query, top_k=top_k, initial_top_k=initial_top_k, filters=filters, rerank=True)

        # client-side filename filter (contains)
        if filename.strip():
            hits = [h for h in hits if filename.lower() in (h.source or "").lower()]

    # layout: results (left) | answer (right)
    cols = st.columns([2, 1])

    with cols[0]:
        st.subheader("Top results")
        if not hits:
            st.warning("No results found. Try relaxing filters or re-embedding.")
        else:
            for i, h in enumerate(hits, 1):
                # keep a stable label (no score in title) to avoid React/DOM issues
                title = f"[{i}] {h.source}"
                with st.expander(title, expanded=(i == 1)):
                    st.caption(f"score = {h.score:.3f}")
                    st.write(h.text)
                    if show_payload:
                        st.json(h.payload)

    with cols[1]:
        st.subheader("Answer")
        if not hits:
            st.info("Ask a question or relax filters to see answers.")
        elif use_llm:
            prompt = make_prompt(query, hits)
            answer = call_ollama(ollama_model, prompt)
            st.write(answer)
        else:
            st.info("Enable “Compose answer via Ollama” in the sidebar to generate an answer.\n\n"
                    "This panel currently shows retrieval only.")
else:
    st.info("Enter a question to search your local tender corpus.")
