# rag_build_index.py
import os, json
import pandas as pd
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

EXCEL_PATH = "tp_2020conference.xlsx"  # 你的Excel路径
OUT_DIR = "rag_iclr2020_index"
os.makedirs(OUT_DIR, exist_ok=True)

# 1) 读取数据
df = pd.read_excel(EXCEL_PATH)  # 也支持 csv：pd.read_csv(...)
df.columns = [c.strip().lower() for c in df.columns]

required = {"title","abstract","review"}
assert required.issubset(set(df.columns)), f"缺少列：{required - set(df.columns)}"

df = df.sample(n=1000, random_state=42).reset_index(drop=True)

# 2) 预处理文本
def norm_text(x): 
    return "" if pd.isna(x) else str(x).strip()

df["id"] = df.get("id", pd.Series([f"iclr2020_{i}" for i in range(len(df))]))
df["text_for_embed"] = (df["title"].map(norm_text) + " \n\n" + df["abstract"].map(norm_text)).str.strip()
corpus = df["text_for_embed"].tolist()

# 3) 句向量模型（可换成你喜欢的模型）
model_name = "sentence-transformers/all-MiniLM-L6-v2"
encoder = SentenceTransformer(model_name)
emb = encoder.encode(corpus, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)

# 4) 建 FAISS 索引（余弦相似采用内积，因已normalize）
d = emb.shape[1]
index = faiss.IndexFlatIP(d)
index.add(emb)

# 5) 保存索引和元数据
faiss.write_index(index, os.path.join(OUT_DIR, "faiss.index"))

meta = df[["id","title","abstract","review"]].to_dict(orient="records")
with open(os.path.join(OUT_DIR, "meta.jsonl"), "w", encoding="utf-8") as f:
    for m in meta: f.write(json.dumps(m, ensure_ascii=False)+"\n")

with open(os.path.join(OUT_DIR, "encoder.json"), "w") as f:
    json.dump({"model_name": model_name}, f)

print(f"完成：{len(df)} 条入库到 {OUT_DIR}")
