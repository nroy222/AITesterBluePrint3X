"""Central config: .env secrets + config.yaml tunables + resolved paths."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

CHAPTER_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(CHAPTER_ROOT / ".env")


def _load_yaml(name):
    p = CHAPTER_ROOT / name
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


CFG = _load_yaml("config.yaml")
GLOSSARY = _load_yaml("glossary.yaml").get("terms", {})

<<<<<<< HEAD
DATA_DIR = Path(os.getenv("DATA_PATH", str(CHAPTER_ROOT / "data")))
=======
DATA_DIR = CHAPTER_ROOT / "data"
>>>>>>> 1d8a556 (Initial commit)
MANIFEST_PATH = DATA_DIR / ".ingest_manifest.json"

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
USE_FP16 = os.getenv("BGE_USE_FP16", "1") == "1"
QDRANT_URL = os.getenv("QDRANT_URL", "").strip()
QDRANT_PATH = str((CHAPTER_ROOT / os.getenv("QDRANT_PATH", "./qdrant_data")).resolve())
COLLECTION = os.getenv("QDRANT_COLLECTION", "qabuddy_kb")
<<<<<<< HEAD
DENSE_DIM = int(os.getenv("EMBED_DIM", "1024" if EMBED_MODEL.startswith("BAAI/bge-m3") else "384"))

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("OPENROUTER_API_KEY")
=======
DENSE_DIM = int(os.getenv("DENSE_DIM", "1024"))

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

def _is_valid_api_key(key: str | None) -> bool:
    if not key:
        return False
    key = key.strip()
    return key and not key.lower().startswith("your_")

LLM_API_KEY = (
    os.getenv("LLM_API_KEY") if _is_valid_api_key(os.getenv("LLM_API_KEY")) else None
) or (
    os.getenv("GROQ_API_KEY") if _is_valid_api_key(os.getenv("GROQ_API_KEY")) else None
) or (
    os.getenv("OPENROUTER_API_KEY") if _is_valid_api_key(os.getenv("OPENROUTER_API_KEY")) else None
)
>>>>>>> 1d8a556 (Initial commit)

PORT = int(os.getenv("PORT", 5080))


def cfg(path, default=None):
    """cfg('retrieval.top_k', 6) -> value from config.yaml with a fallback."""
    node = CFG
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node
