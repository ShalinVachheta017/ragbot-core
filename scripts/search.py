from core.qa import retrieve_candidates, answer_query
from core.config import CFG

if __name__ == "__main__":
    q = input("Query: ").strip()
    hits = retrieve_candidates(q, CFG)
    print(f"hits={len(hits)} (showing top {min(5, len(hits))})")
    for h in hits[:5]:
        src = h.payload.get("source_path")
        page = h.payload.get("page")
        print(f"{h.score:.3f} | {src}{f':p{page}' if page is not None else ''}")
    print("\n--- Answer ---")
    print(answer_query(q, CFG))
