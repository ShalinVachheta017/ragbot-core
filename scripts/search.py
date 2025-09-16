from core.qa import retrieve_candidates, answer_query
from core.config import CFG
import torch

def main():
    # 🔧 DEVICE DETECTION - Fix for the NameError
    if torch.cuda.is_available():
        device = 'cuda'
        print(f"✅ Using GPU: {torch.cuda.get_device_name(0)}")
        print(f"✅ GPU Memory: {torch.cuda.get_device_properties(0).total_memory // (1024**3)}GB")
    else:
        device = 'cpu'
        print("⚠️  Using CPU - GPU not available")

    # 📝 GET USER QUERY
    q = input("Query: ").strip()
    if not q:
        print("❌ Empty query provided")
        return

    print(f"🔍 Searching for: '{q}'")
    
    try:
        # 🔍 RETRIEVE CANDIDATES - Functions don't need device parameter
        hits = retrieve_candidates(q, CFG)
        
        print(f"📊 Found {len(hits)} hits (showing top {min(5, len(hits))})")
        
        # 📋 DISPLAY RESULTS
        for i, h in enumerate(hits[:5], 1):
            src = h.payload.get("source_path", "Unknown")
            page = h.payload.get("page_start") or h.payload.get("page")
            score = h.score
            
            # Clean up source path for display
            if src and "/" in src:
                src = src.split("/")[-1]  # Get filename only
            
            page_info = f":p{page}" if page is not None else ""
            print(f"{i}. {score:.3f} | {src}{page_info}")
        
        print("\n" + "="*50)
        print("🤖 GENERATING ANSWER...")
        print("="*50)
        
        # 🤖 GENERATE ANSWER
        answer = answer_query(q, CFG)
        print(answer)
            
    except Exception as e:
        print(f"❌ Search error: {e}")
        print("💡 Make sure your Qdrant server is running and the collection exists")
        
        # Show some diagnostic info
        if "device" in str(e).lower():
            print("🔧 This looks like a device configuration error")
        elif "qdrant" in str(e).lower():
            print("🔧 This looks like a Qdrant connection error")

if __name__ == "__main__":
    main()
