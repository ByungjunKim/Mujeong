"""구간별 등록부를 묶어 공통 ID 초안(id_map.csv)과 인물·장소 등록부 초안(master_*.csv), 쟁점 목록을 만든다.

원칙
- 자동으로 묶는 것은 '이름이 글자 그대로 같은 경우'와, 아래 MASTER 표의 별칭에 이름이 들어 있는 경우뿐이다.
- '노파' '부인' '어머니'처럼 여러 사람을 가리킬 수 있는 말로는 묶지 않는다 → 결정 필요로 남긴다.
- 공통 ID 표기는 TEI Agent 전문 실행본 방식(성+이름 로마자 머리글자: LHS, SWS, KJH …)을 따른다.
"""
import json, csv, re, collections, sys

J = json.load(open(sys.argv[1], encoding="utf-8"))
OUT = sys.argv[2]

def nz(s):
    return re.sub(r"[\s·()（）]", "", s or "")

# (공통 ID, 공통 이름, 종류, 별칭(이 이름이 등록부 이름 목록에 있으면 묶음), 메모)
MASTER = [
    ("LHS", "이형식", "person", "이형식|형식|이형식씨|형식씨|이형식군|미스터리|이선생|형식이", "주인공, 경성학교 영어 교사. 전문 실행본 ID"),
    ("PYC", "박영채", "person", "박영채|영채|영채씨|계월향|월향", "기명 계월향(월향)"),
    ("KSH", "김선형", "person", "김선형|선형|선형이|선형씨|善馨|박선형", "김장로의 딸. 82장 '박선형'은 원문 표기"),
    ("SWS", "신우선", "person", "신우선|우선|신주사|우선이", "전문 실행본 ID. 부사 '우선'과 구별"),
    ("KJH", "김장로", "person", "김장로|김광현|김장로의|김장로는", "본명 김광현(1–10·91–100 등록부). 전문 실행본 ID KJH"),
    ("KJH_W", "김장로의 부인", "person", "김장로부인|장로의부인|김장로의부인|김장로의 부인", ""),
    ("PJS", "박진사", "person", "박진사|박선생|박교장", "영채의 부친. '박응진'(1–10 PES)과 같은 인물인지 결정 필요"),
    ("GWH", "계월화", "person", "계월화|월화|솔이", "평양 기생, 영채의 언니뻘. 51–60 YC에 '월화'가 섞여 있음"),
    ("BMS", "배명식", "person", "배명식|배학감|배명식씨", "경성학교 학감"),
    ("HSM", "함상모", "person", "함상모|함교장", ""),
    ("KJY", "김종렬", "person", "김종렬|종렬|종렬군|김종렬군", "경성학교 학생"),
    ("LHK", "이희경", "person", "이희경|희경|희경군|이희경군", "경성학교 학생"),
    ("KHS", "김현수", "person", "김현수|현수", "김윤수의 아들"),
    ("KYS", "김윤수", "person", "김윤수", ""),
    ("KNJ", "김남작", "person", "김남작|경성학교주김남작", "경성학교 교주"),
    ("YSA", "윤순애", "person", "윤순애|순애|박순애", "선형의 동무. 71–80·101–110은 '박순애'로 등록 → 성 확인 필요"),
    ("KBU", "김병욱", "person", "김병욱|병욱|병욱이|병옥", "'병옥'은 원문 오기로 보임(확인 필요)"),
    ("KBG", "김병국", "person", "김병국|병국|병국이|황주김병국", "병욱의 오빠"),
    ("KBG_W", "김병국의 부인", "person", "김병국의처|병국의부인|김병국의부인", ""),
    ("KBU_F", "병욱의 부친", "person", "김병욱의부친|병욱의아버지", ""),
    ("KBU_M", "병욱의 모친", "person", "김병욱의모친|병욱의어머니", ""),
    ("KBU_GM", "병욱의 조모", "person", "김병욱의조모|병욱의조모|김병국의조모", ""),
    ("HMS", "한목사", "person", "한목사", ""),
    ("GH", "계향", "person", "계향|계향이", "평양 칠성문 밖에서 만난 기생 아이"),
    ("KUR", "김운룡", "person", "김운룡|김운룡(金雲龍)", ""),
    ("KUR_W", "김운룡의 부인", "person", "김운룡의부인", ""),
    ("KY", "경애", "person", "경애|경애씨", ""),
    ("TNP", "동경 주인 노파", "person", "동경의주인노파", ""),
    ("HNP", "형식의 하숙집 노파", "person", "노파(형식의서울하숙집)|형식의하숙집주인노파|형식의주인노파|형식의주인하고있던노파", "명시적으로 '형식의 하숙집'이라 적힌 것만 자동으로 묶음"),
    ("YNP", "영채의 노파", "person", "노파(영채의집)|영채의노파|영채의집노파", "영채를 기른 기생 어미. 명시적인 것만 자동으로 묶음"),
    ("YC_FATHER", "영채의 아버지", "person", "영채의부친|영채의아버지", "PJS와 같은 인물 → 회의에서 PJS로 합칠지 결정"),
    ("YC_BROTHERS", "영채의 두 오라비", "personGrp", "영채의오라비|영채의오라버니", ""),
    ("SWS_W", "신우선의 아내", "person", "신우선의아내", ""),
    ("JESUS", "예수", "person", "예수|십자가에달린예수", "작품 밖 인물"),
    ("CHUNHYANG", "춘향", "person", "춘향", "작품 밖 인물(『춘향전』)"),
    ("IDORYEONG", "이도령", "person", "이도령|김도령|책방도령", "작품 밖 인물(『춘향전』)"),
]
GENERIC = set(nz(x) for x in """나 내 내가 그 자기 부인 마님 어머니 어머님 모친 부친 아버지 아버님 노파 주인 주인노파 선생 선생님 학생 학생들 교사
교원들 형님 언니 오빠 동생 처녀 계집아이 아씨 미상 남자 젊은 사람 젊은사람 젊은남자 어떤남자 어떤여자 노인 의사 의원 차장 순사
간수 서장 태모 조모 할머니 대감 영감쟁이 문객 어미 어멈 아내 딸 누이 형 형수 오라비 조부 서조모 고모 외숙모 전처 새서방 악한
그악한 계집 기생 기생들 소년 사내아이 부인들 교장 어떤교사 한교사 역부 개""".split())

HINT = {("101-110", "MTH"): "KBU_M", ("101-110", "FTH"): "KBU_F", ("101-110", "GM"): "KBU_GM",
        ("81-90", "YC_FATHER"): "PJS/YC_FATHER", ("41-50", "PS"): "PJS", ("1-10", "PES"): "PJS?",
        ("31-40", "YC-FATHER"): "PJS/YC_FATHER", ("1-10", "NOPA"): "HNP", ("21-30", "NOPA"): "HNP",
        ("31-40", "NP"): "YNP", ("51-60", "NP"): "YNP", ("91-100", "NP"): "YNP"}
alias = {}
for mid, name, kind, al, note in MASTER:
    for a in al.split("|"):
        alias.setdefault(nz(a), mid)

rows = []
for s in J["sections"]:
    sec, reg, used = s["구간"], s["등록부"], s["사용 횟수"]
    for i, v in reg.items():
        names = v["names"] or [i]
        rows.append({"구간": sec, "구간 ID": i, "종류": v["kind"], "이름들": " | ".join(names), "첫 이름": names[0],
                     "성별": v.get("sex") or "", "사용 횟수": used.get(i, 0), "등록부 메모": (v.get("note") or "")[:80]})

# 1) 별칭 표로 묶기 (사람만)
for r in rows:
    r["공통 ID(제안)"], r["근거"] = "", ""
    if r["종류"] not in ("person", "personGrp"):
        continue
    names = [nz(n) for n in r["이름들"].split(" | ")]
    hits = [alias[n] for n in names if n in alias]
    # 첫 이름이 일치하면 우선, 아니면 다른 이름. 여러 공통 ID에 걸리면 결정 필요
    first = alias.get(nz(r["첫 이름"]))
    cand = sorted(set(hits))
    if first and (len(cand) == 1 or first in cand):
        r["공통 ID(제안)"] = first
        r["근거"] = "별칭 일치" + ("" if len(cand) == 1 else f" — 다른 후보도 걸림: {'/'.join(c for c in cand if c != first)}")
    elif len(cand) == 1 and nz(r["첫 이름"]) not in GENERIC:
        r["공통 ID(제안)"] = cand[0]; r["근거"] = "별칭 일치(첫 이름 아님)"
    elif cand:
        r["근거"] = "결정 필요 — 후보: " + "/".join(cand)

# 2) 나머지: 첫 이름이 글자 그대로 같고 일반 명사가 아니면 자동으로 묶기 (사람·장소·기관 모두)
groups = collections.defaultdict(list)
for r in rows:
    if r["공통 ID(제안)"] or r["근거"].startswith("결정 필요"):
        continue
    key = (r["종류"] if r["종류"] in ("place", "org") else "person", nz(r["첫 이름"]))
    groups[key].append(r)
taken = {m[0] for m in MASTER}
auto_master = {}
for (kind, key), rs in groups.items():
    secs0 = {r["구간"] for r in rs}
    if kind == "person" and (key in GENERIC or not key):
        if len(secs0) > 1:
            for r in rs:
                hint = HINT.get((r["구간"], r["구간 ID"]))
                r["근거"] = "결정 필요 — 일반 명칭이 " + f"{len(secs0)}개 구간에 있음" + (f" · 후보 {hint}" if hint else "")
            continue
        for r in rs:  # 한 구간에만 있는 일반 명칭: 구간 접두어를 붙여 따로 둔다
            hint = HINT.get((r["구간"], r["구간 ID"]))
            if hint:
                r["근거"] = f"결정 필요 — 후보 {hint}"; continue
            mid = "S" + r["구간"].split("-")[0] + "_" + re.sub(r"[^A-Za-z0-9_]", "_", r["구간 ID"]).upper()
            r["공통 ID(제안)"] = mid; r["근거"] = "한 구간 · 일반 명칭(구간 번호를 붙여 따로 둠)"
            taken.add(mid); auto_master[mid] = (r["첫 이름"], "person")
        continue
    ids = collections.Counter()
    for r in rs:
        ids[r["구간 ID"]] += r["사용 횟수"] + 1
    best = sorted(ids, key=lambda x: (-ids[x], -len(x), x))[0]
    best = re.sub(r"[^A-Za-z0-9_]", "_", best).upper().strip("_") or "X"
    if kind in ("place", "org") and not best.startswith(("PL", "ORG")):
        best = ("PL_" if kind == "place" else "ORG_") + best
    mid, n = best, 2
    while mid in taken:
        mid = f"{best}_{n}"; n += 1
    taken.add(mid)
    secs = {r["구간"] for r in rs}
    for r in rs:
        r["공통 ID(제안)"] = mid
        r["근거"] = ("이름 일치 · " if len(secs) > 1 else "한 구간에만 · ") + f"{len(secs)}개 구간"
    auto_master[mid] = (rs[0]["첫 이름"], kind)

for r in rows:
    r["회의 결정"] = ""
    r["메모"] = ""

cols = ["구간", "구간 ID", "종류", "이름들", "사용 횟수", "공통 ID(제안)", "근거", "회의 결정", "메모", "성별", "등록부 메모"]
order = {s["구간"]: k for k, s in enumerate(J["sections"])}
rows.sort(key=lambda r: (r["종류"] not in ("person", "personGrp"), not r["근거"].startswith("결정 필요"), r["공통 ID(제안)"] or "~", order[r["구간"]], -r["사용 횟수"]))
with open(OUT + "/id_map_초안.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

# 공통 등록부 초안
master = collections.OrderedDict()
for mid, name, kind, al, note in MASTER:
    master[mid] = {"공통 ID": mid, "공통 이름": name, "종류": kind, "별칭": "", "등장 구간": "", "구간 ID들": "", "사용 횟수": 0, "메모": note, "출처": "교강사 별칭 표"}
for mid, (name, kind) in auto_master.items():
    master[mid] = {"공통 ID": mid, "공통 이름": name, "종류": kind, "별칭": "", "등장 구간": "", "구간 ID들": "", "사용 횟수": 0, "메모": "", "출처": "이름 자동 일치"}
for mid in master:
    rs = [r for r in rows if r["공통 ID(제안)"] == mid]
    al = []
    for r in rs:
        for n in r["이름들"].split(" | "):
            if n and n not in al:
                al.append(n)
    secs = []
    for r in rs:
        if r["구간"] not in secs:
            secs.append(r["구간"])
    master[mid].update({"별칭": " | ".join(al[:14]), "등장 구간": ", ".join(secs),
                        "구간 ID들": ", ".join(sorted({f"{r['구간 ID']}" for r in rs})), "사용 횟수": sum(r["사용 횟수"] for r in rs)})
mcols = ["공통 ID", "공통 이름", "종류", "사용 횟수", "등장 구간", "구간 ID들", "별칭", "메모", "출처"]
ms = [m for m in master.values() if m["사용 횟수"] > 0 or m["출처"] == "교강사 별칭 표"]
for kind, fn in [(("person", "personGrp"), "공통_인물_등록부_초안.csv"), (("place", "org"), "공통_장소기관_등록부_초안.csv")]:
    sel = sorted([m for m in ms if m["종류"] in kind], key=lambda m: (m["출처"] != "교강사 별칭 표", -m["사용 횟수"]))
    with open(OUT + "/" + fn, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=mcols); w.writeheader(); w.writerows(sel)

# 쟁점: 같은 구간 ID가 구간마다 다른 공통 ID로 간 경우(= ID 충돌)
coll = collections.defaultdict(set)
for r in rows:
    if r["공통 ID(제안)"]:
        coll[r["구간 ID"]].add((r["공통 ID(제안)"], r["구간"], r["첫 이름"]))
clash = {k: sorted(v) for k, v in coll.items() if len({x[0] for x in v}) > 1}
json.dump({"충돌": clash,
           "결정 필요": [{k: r[k] for k in ("구간", "구간 ID", "이름들", "사용 횟수", "근거")} for r in rows if r["근거"].startswith("결정 필요")]},
          open(OUT + "/쟁점.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
c = collections.Counter("결정 필요" if r["근거"].startswith("결정 필요") else ("별칭" if "별칭" in r["근거"] else ("이름 일치" if "이름 일치" in r["근거"] else "한 구간")) for r in rows)
print("행", len(rows), dict(c))
print("공통 인물", sum(1 for m in ms if m["종류"] in ("person", "personGrp")), "공통 장소·기관", sum(1 for m in ms if m["종류"] in ("place", "org")))
print("ID 충돌", len(clash)); [print(" ", k, v) for k, v in list(clash.items())[:40]]
