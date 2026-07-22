"""Hybrid embeddings for QABuddy.ai.

Prefer BGE-M3 when available; fall back to a local Hugging Face transformer model
for lightweight deployments and low-disk environments.
"""
from .. import config as C

_embedder = None
_transformer = None


def _load_bge():
    """Load BGE-M3 via FlagEmbedding. Only works for actual BGE-M3 models;
    non-BGE-M3 model names raise so the transformer fallback kicks in."""
    if "bge-m3" not in C.EMBED_MODEL.lower():
        raise ImportError(
            f"{C.EMBED_MODEL} is not a BGE-M3 model; "
            "use the transformer fallback for dense-only embeddings")
    from FlagEmbedding import BGEM3FlagModel
    return BGEM3FlagModel(C.EMBED_MODEL, use_fp16=C.USE_FP16)


def _load_transformer():
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(C.EMBED_MODEL, use_fast=True)
    model = AutoModel.from_pretrained(C.EMBED_MODEL)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.eval().to(device)
    return tok, model, torch, device


def get_embedder():
    global _embedder, _transformer
    if _embedder is None and _transformer is None:
        try:
            _embedder = _load_bge()
        except Exception:
            _transformer = _load_transformer()
    return _embedder or _transformer


def embed(texts, batch_size=16):
    """Return (dense_list, sparse_list)."

    dense: list[list[float]]; sparse: list[{'indices': [int], 'values': [float]}]
    """
    emb = get_embedder()
    if isinstance(emb, tuple):
        tok, model, torch, device = emb
        inputs = tok(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            out = model(**inputs)
            hidden = out.last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1)
            summed = (hidden * mask).sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1)
            pooled = summed / counts
            dense = [vec.cpu().tolist() for vec in pooled]
        sparse = [{"indices": [], "values": []} for _ in dense]
        return dense, sparse

    model = emb
    out = model.encode(texts, batch_size=batch_size, max_length=1024,
                       return_dense=True, return_sparse=True, return_colbert_vecs=False)
    dense = [list(map(float, v)) for v in out["dense_vecs"]]
    sparse = []
    for lw in out["lexical_weights"]:
        idx, val = [], []
        for k, v in lw.items():
            idx.append(int(k))
            val.append(float(v))
        sparse.append({"indices": idx, "values": val})
    return dense, sparse


def sparse_top_tokens(sparse, n=5):
    """Human-readable top-n sparse tokens (token text + weight) for the UI."""
    pairs = sorted(zip(sparse["indices"], sparse["values"]), key=lambda p: -p[1])[:n]
    try:
        tok = get_embedder().tokenizer
        return [{"token": tok.decode([i]).strip(), "weight": round(w, 3)} for i, w in pairs]
    except Exception:
        return [{"token": str(i), "weight": round(w, 3)} for i, w in pairs]
