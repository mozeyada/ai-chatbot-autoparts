import json
from sentence_transformers import SentenceTransformer, util

# Load an embedding model once (MiniLM is small & free)
_embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def load_faq(path: str):
    with open(path, "r") as f:
        data = json.load(f)
    # add embeddings for quick similarity search
    for item in data:
        item["embedding"] = _embedder.encode(item["question"], convert_to_tensor=True)
    return data

def get_best_answer(faq_data, user_msg, threshold: float = 0.6):
    """Return the best‑matching FAQ answer or None."""
    user_emb = _embedder.encode(user_msg, convert_to_tensor=True)
    best_score, best_ans = 0.0, None
    for item in faq_data:
        score = util.cos_sim(user_emb, item["embedding"]).item()
        if score > best_score:
            best_score, best_ans = score, item["answer"]
    return best_ans if best_score >= threshold else None
