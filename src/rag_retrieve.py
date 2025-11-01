# rag_retrieve.py
import os, json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

INDEX_DIR = "data/rag_iclr2020_index"

def load_meta():
    metas = []
    with open(os.path.join(INDEX_DIR, "meta.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            metas.append(json.loads(line))
    return metas

def load_encoder():
    with open(os.path.join(INDEX_DIR, "encoder.json"), "r") as f:
        m = json.load(f)
    return SentenceTransformer(m["model_name"])

def retrieve_topk(title:str, abstract:str, k:int=2):
    text = (title or "").strip() + "\n\n" + (abstract or "").strip()
    enc = load_encoder()
    q = enc.encode([text], convert_to_numpy=True, normalize_embeddings=True)
    index = faiss.read_index(os.path.join(INDEX_DIR, "faiss.index"))
    D, I = index.search(q, k)  # 内积分数
    metas = load_meta()
    results = []
    for score, idx in zip(D[0], I[0]):
        m = metas[idx]
        results.append({"score": float(score), **m})
    return results

def get_topk_reviews(title: str, abstract: str, k: int = 2, dedup: bool = True):
    """
    获取最相似的 k 篇论文的 review 文本
    - title, abstract: 查询论文内容
    - k: 返回的相似论文数量
    - dedup: 是否根据标题去重
    返回: list[str]
    """
    results = retrieve_topk(title, abstract, k)
    reviews = []
    seen_titles = set()

    for item in results:
        t = item["title"].strip().lower()
        if dedup and t in seen_titles:
            continue
        seen_titles.add(t)
        if item.get("review"):
            reviews.append(item["review"])
            print(f"  - Retrieved review from: {item['title']} (score: {item['score']:.4f})")
    return reviews

if __name__ == "__main__":
    # 示例测试
    query_title = "Convolutional Conditional Neural Processes | OpenReview"
    query_abstract = (
        "We introduce the Convolutional Conditional Neural Process (ConvCNP)..."
    )

    top_reviews = get_topk_reviews(query_title, query_abstract, k=2)
    print(json.dumps(top_reviews, ensure_ascii=False, indent=2))