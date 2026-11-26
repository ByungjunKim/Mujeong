# 『무정』 그래프 v1 → 벡터 DB 꾸러미 (13주차 실습 B 노트 2–3번과 같은 방법)
import os, re, json, gzip, hashlib, time, sys
import numpy as np, pandas as pd
from sentence_transformers import SentenceTransformer
BASE = sys.argv[1] if len(sys.argv) > 1 else "graph/v1/"
OUT = sys.argv[2] if len(sys.argv) > 2 else "rag/v1"
ENCODER_ID = "intfloat/multilingual-e5-small"
CHUNK_TOKENS, OVERLAP = 350, 40
def read(name):
    df = pd.read_csv(BASE + name, dtype=str, keep_default_na=False)
    for c in ("seq", "order"):
        if c in df: df[c] = df[c].astype(int)
    return df
P = read("nodes_Paragraph.csv"); U = read("nodes_Utterance.csv"); PERSON = read("nodes_Person.csv")
MENTION = read("rels_MENTIONED_IN_Person_Paragraph.csv")
P["ch"] = P.chapter.astype(int)
NAME = dict(zip(PERSON.id, PERSON.name))
encoder = SentenceTransformer(ENCODER_ID); tok = encoder.tokenizer
def split_long(text):
    off = tok(text, add_special_tokens=False, return_offsets_mapping=True, verbose=False)["offset_mapping"]
    if len(off) <= CHUNK_TOKENS: return [text]
    parts, start = [], 0
    while True:
        end = min(start + CHUNK_TOKENS, len(off))
        parts.append(text[(off[start][0] if start else 0):(off[end][0] if end < len(off) else len(text))])
        if end == len(off): return parts
        start += CHUNK_TOKENS - OVERLAP
who_in = MENTION.groupby("end")["start"].agg(lambda s: list(dict.fromkeys(s))).to_dict()
P["persons"] = P.id.map(lambda i: [NAME.get(x, x) for x in who_in.get(i, [])])
chunks = []
for row in P.itertuples():
    parts = split_long(row.text)
    for k, part in enumerate(parts, 1):
        head = f"[{row.ch}장 · 등장: {', '.join(row.persons[:6])}] " if row.persons else f"[{row.ch}장] "
        chunks.append({"pid": row.id, "ch": int(row.ch), "order": int(row.order), "part": k, "parts": len(parts),
                       "persons": row.persons, "text": part, "embed_text": head + part})
def enc(texts, bs):
    return encoder.encode(["passage: " + t for t in texts], batch_size=bs, normalize_embeddings=True, show_progress_bar=True).astype("float32")
t0 = time.time()
vecs = enc([c["embed_text"] for c in chunks], 16); vecsU = enc(list(U.text), 32)
print("encode sec", round(time.time() - t0))
os.makedirs(OUT, exist_ok=True)
np.save(f"{OUT}/paragraph_vectors.f16.npy", vecs.astype("float16"))
np.save(f"{OUT}/utterance_vectors.f16.npy", vecsU.astype("float16"))
with gzip.open(f"{OUT}/chunks.json.gz", "wt", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
man = {"이름": "『무정』 벡터 DB v1 (그래프 v1에서 만듦)", "만든 날": time.strftime("%Y-%m-%d"),
       "저본": "graph/v1/ (통합본 v1, 2026-11-23 동결)", "임베딩 모델": ENCODER_ID, "차원": int(vecs.shape[1]),
       "접두어": {"문서": "passage: ", "질문": "query: "}, "정규화": "L2 (내적 = 코사인 유사도)", "저장 형식": "float16 .npy (읽은 뒤 float32로 바꿔 쓰기)",
       "청킹": f"문단 = 청크, {CHUNK_TOKENS}토큰 넘는 문단만 {CHUNK_TOKENS}/{OVERLAP}으로 나눔, 청크 앞에 '[n장 · 등장: 인물…]' 이름표",
       "문단 청크 수": len(chunks), "발화 수": int(len(U)), "발화 순서": "nodes_Utterance.csv의 행 순서",
       "파일": {n: {"bytes": os.path.getsize(f"{OUT}/{n}"), "sha256": sha(f"{OUT}/{n}")} for n in ["paragraph_vectors.f16.npy", "utterance_vectors.f16.npy", "chunks.json.gz"]}}
json.dump(man, open(f"{OUT}/MANIFEST.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(man, ensure_ascii=False, indent=1))
