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
