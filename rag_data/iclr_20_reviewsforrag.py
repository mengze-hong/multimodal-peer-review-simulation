import pandas as pd
import json, os

# === 输入输出路径 ===
excel_file = "tp_2020conference.xlsx"
output_file = "iclr_2020/paired_data.jsonl"

# === 读取 Excel ===
df = pd.read_excel(excel_file)

# 检查列名
required_cols = ["title", "abstract", "paper_decision_comment"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns in Excel: {missing}")

# === 生成 RAG 数据 ===
records = []
for i, row in df.iterrows():
    title = str(row["title"]).strip()
    abstract = str(row["abstract"]).strip()
    review = str(row["paper_decision_comment"]).strip()

    if title and abstract and review and review.lower() != "nan":
        records.append({
            "id": f"iclr2020_{i}",
            "title": title,
            "abstract": abstract,
            "review": review
        })

# === 保存为 JSONL ===
output_dir = os.path.dirname(output_file)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)

with open(output_file, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"已保存 {len(records)} 条数据到 {output_file}")
