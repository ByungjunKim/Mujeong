# merged/ — 『무정』 1–126장 통합본 (v0, 2026-11-10)

13개 구간(TEI/)을 하나로 합친 통합 TEI와 점검 결과다. 11주차(11/10) 인물 등록부 통합 회의 전 검토용이며, 회의 결정을 반영해 v1을 다시 만든다.

- `무정_통합본_v0.xml` : 통합본. tei_all(TEI P5 4.12.0) 검증 통과. 공통 ID 초안 적용, 정해지지 않은 ID는 `S구간시작_원래ID`(임시).
- `최종점검_보고.md` : 검사 다섯 가지의 결과와 구간별 수정 제안.
- `무정_통합본_v0_검증.json` · `무정_통합본_v0_병합보고.json` : 원문(KNoTE rawdata 1,977문단) 대조 · 참조 검사 · 병합 기록.
- `id_map_초안.csv` : 구간 ID → 공통 ID(제안). 회의에서 `회의 결정` 칸을 채워 `id_map.csv`로 저장한다.
- `공통_인물_등록부_초안.csv` · `공통_장소기관_등록부_초안.csv` : 공통 등록부 초안.
- `crm/mujeong_crm.ttl` : 통합본을 CIDOC CRM 7.1 어휘로 바꾼 RDF(Turtle, 트리플 30,069개). 작중 인물은 `mjo:Character` ⊂ E89, 실존 인물은 E21, 화자는 `mjo:has_speaker` ⊂ P67. `crm/mujeong_crm_report.json`에 정의역 · 치역 검사 결과(위반 0). 이름공간 IRI는 임시다.
- `tools/` : 다시 만드는 스크립트. inspect_sections → build_idmap → merge_sections → validate_merged 순서. 속성 그래프 CSV는 `tei2graph.py`, CIDOC CRM은 `tei2crm.py`(rdflib 필요).

원문 글자는 61–70의 복사 흔적(장 번호 · 곧은 큰따옴표) 제거 말고는 바꾸지 않았다. 데이터는 CC BY 4.0, 코드는 저장소의 LICENSE-CODE를 따른다.
