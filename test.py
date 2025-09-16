#%%
import torch
print("CUDA:", torch.cuda.is_available())

# %%
import fitz, qdrant_client, transformers, sentence_transformers, streamlit
print("✅ core deps OK")
# %%
where python
python -c "import sys; print(sys.executable)"
pip --version

# %%

import core, core.config
print("core imported from:", core.__file__)
print("EMBED_MODEL:", core.config.EMBED_MODEL_NAME)

# %%

import torch; print("CUDA available:", torch.cuda.is_available(), "| device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")

# %%
from qdrant_client import QdrantClient
c = QdrantClient(url="http://localhost:6333")
print(c.count("tender_docs_m-e5-large_v1", exact=True))


# %%
import sentence_transformers, qdrant_client, ollama
print('✅ Core deps OK')
# %%
from FlagEmbedding import FlagReranker
from sentence_transformers import SentenceTransformer  
print('✅ All dependencies ready for Jina v3 + Reranker!')

# %%# %%
try:
    from FlagEmbedding import FlagReranker
    from sentence_transformers import SentenceTransformer
    
    # Test model loading
    reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)
    print('✅ FlagEmbedding and SentenceTransformer imports successful!')
    print('✅ Reranker model loaded successfully!')
except ImportError as e:
    print('❌ Import Error:', e)
    print('💡 Try: pip install FlagEmbedding')
except Exception as e:
    print('❌ Error:', e)

# %%
!pip install FlagEmbedding
# %%

from sentence_transformers import SentenceTransformer
m = SentenceTransformer("jinaai/jina-embeddings-v3", trust_remote_code=True)
print("raw dim:", m.get_sentence_embedding_dimension())        # → 1024
print("cropped dim should be 512 in your code")
# %%
import sentence_transformers, transformers, huggingface_hub
print("ST:", sentence_transformers.__version__)
print("TF:", transformers.__version__)
print("HF:", huggingface_hub.__version__)
# %%

from sentence_transformers import SentenceTransformer
m = SentenceTransformer('jinaai/jina-embeddings-v3', trust_remote_code=True)
print('✅ Model loaded successfully, dimension:', m.get_sentence_embedding_dimension())

# %%
from sentence_transformers import SentenceTransformer
print('Loading Jina v3...')
m = SentenceTransformer('jinaai/jina-embeddings-v3', trust_remote_code=True)
print('✅ Success! Dimension:', m.get_sentence_embedding_dimension())
print('Model loaded successfully')


# %%
from sentence_transformers import SentenceTransformer
print('Loading Jina v3...')
m = SentenceTransformer('jinaai/jina-embeddings-v3', trust_remote_code=True)
print('✅ Success! Dimension:', m.get_sentence_embedding_dimension())
# %%
from sentence_transformers import SentenceTransformer
import os
# Temporarily bypass cache issues
os.environ['TRANSFORMERS_CACHE'] = 'C:/temp/fresh_cache'
print('Loading Jina v3 with fresh cache...')
m = SentenceTransformer('jinaai/jina-embeddings-v3', trust_remote_code=True, cache_folder='C:/temp/fresh_cache')
print('✅ Success! Dimension:', m.get_sentence_embedding_dimension())
# %%
import torch

# In your _embed method, add after processing batches:
if torch.cuda.is_available():
    torch.cuda.empty_cache()  # Clear memory after each file

# %%
