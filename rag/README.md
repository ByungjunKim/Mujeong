# rag — 그래프에서 만든 벡터 DB

- `v1/`: 그래프 v1(`graph/v1/`, 통합본 v1 · 2026-11-23 동결)의 문단 · 발화를 미리 임베딩해 둔 꾸러미 (2026-11-26)
- 쓰임: Colab 실습에서 임베딩 계산을 기다리지 않고 바로 내려받아 쓰기 (13주차 실습 B 노트 2–3번과 같은 방법으로 만듦)
- 그래프가 바뀌면 `rag/v2/`처럼 새 폴더에 다시 만들기: `python rag/tools/build_vectors.py graph/v2/ rag/v2`

| 파일 | 내용 |
|---|---|
| `v1/paragraph_vectors.f16.npy` | 문단 청크 2,184개 × 384차원 (float16, 길이 1로 정규화) |
| `v1/utterance_vectors.f16.npy` | 발화 1,954개 × 384차원 — `graph/v1/nodes_Utterance.csv`의 행 순서 |
| `v1/chunks.json.gz` | 청크 목록: `pid`(문단 ID) · `ch` · `order` · `part` · `persons`(등장 인물) · `text` · `embed_text`(이름표 붙인 글) |
| `v1/MANIFEST.json` | 모델 · 청킹 방법 · 파일 크기와 sha256 |

- 임베딩 모델: [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small) — 문서 앞에 `passage: `, 질문 앞에 `query: ` 붙이기
- 청킹: 문단 = 청크, 350토큰 넘는 문단만 350/40으로 나눔, 청크 앞에 `[16장 · 등장: 이형식, 박영채]` 이름표
- 읽는 법
```python
import numpy as np, json, gzip, urllib.request
B = "https://raw.githubusercontent.com/ByungjunKim/Mujeong/main/rag/v1/"
for n in ["paragraph_vectors.f16.npy", "utterance_vectors.f16.npy", "chunks.json.gz"]:
    urllib.request.urlretrieve(B + n, n)
vecs = np.load("paragraph_vectors.f16.npy").astype("float32")
chunks = json.load(gzip.open("chunks.json.gz", "rt", encoding="utf-8"))
```
- 이용 조건: 데이터 CC BY 4.0, 코드는 저장소의 LICENSE-CODE
