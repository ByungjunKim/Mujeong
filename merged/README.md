# merged/ — 『무정』 1–126장 통합 TEI

| 파일 · 폴더 | 내용 |
|---|---|
| `무정_통합본_v2.xml` | **함께 고치는 파일** (2026-11-24~). v1의 사본에서 시작했다. 본문은 v1과 같고 머리 부분에 기록 한 줄이 늘어, 본문 행 번호는 v1 + 1 |
| `무정_통합본_v1.xml` | 2026-11-23 동결. `graph/v1/`의 저본. 고치지 않는다 |
| `기록/v1_최종검수_2026-11-23.md` | v1 최종 검수: 원문 대조 · 참조 · 구간별로 남은 일 |
| `기록/v1_변경기록.md` | v0 → v1에서 바뀐 것(11주차 회의 결정) |
| `기록/v1_검증_*.json` · `기록/v1_변환기록_2026-11-12.json` | 원문 대조 결과(생성 시점 11/12 · 동결 시점 11/23)와 v1 생성 실행 기록 |
| `tools/` | `inspect_sections` → `build_idmap` → `merge_sections` → `validate_merged` 순서로 통합본을 만들고 검사한다. `make_v1.py`는 v0 → v1, `tei2graph.py`는 속성 그래프 CSV, `tei2crm.py`는 CIDOC CRM(rdflib 필요) |
| `이전판/v0/` | 통합본 v0, v0 검증 · 병합 보고, v0 최종점검 보고(11/10), ID 대조표 · 공통 등록부 초안, v0 기준 CIDOC CRM |

- 저본은 위키문헌 [『무정』](https://ko.wikisource.org/wiki/%EB%AC%B4%EC%A0%95). 헤더에 작가 · 작품 식별자(ISNI · Wikidata · 민백)와 하위 문서 7개 주소가 있고, 각 장 `<div>`의 `@source`가 그 장이 실린 하위 문서 주소다.
- 원문 대조는 KNoTE 저장소 `rawdata/`에 수집된 위키문헌 7개 파일(1,977문단)과 한다: `python tools/validate_merged.py 무정_통합본_v2.xml <KNoTE>/rawdata`
- 스키마 검증은 tei_all(TEI P5 4.12.0) RelaxNG.

데이터는 CC BY 4.0, 코드는 저장소의 LICENSE-CODE를 따른다.
