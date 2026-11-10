import re, os, collections, difflib
from lxml import etree
ORDER = ["무정1장~20장", "무정21장~40장", "무정41장~60장", "무정61장~80장", "무정81장~100장", "무정101장~120장", "무정121장~126장"]
def norm(s):
    s = re.sub(r"\s+", "", s)
    return s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
def txt(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()
raw, rawn, index = [], [], collections.defaultdict(list)
def load(RAW):
    for name in ORDER:
        r = etree.parse(os.path.join(RAW, name + ".xml")).getroot()
        for p in r.iter("paragraph"):
            raw.append((name, txt(p)))
    rawn.extend(norm(t) for _, t in raw)
    for i, t in enumerate(rawn):
        index[t].append(i)
def align(units):
    """구간 XML의 문단(p·l) 순서와 원문 문단 순서를 앞에서부터 맞춘다."""
    ev = []
    if not units:
        return ev
    # 시작 위치: 앞쪽 단위 몇 개가 연속으로 맞는 원문 위치
    start = None
    for k0 in range(min(10, len(units))):
        for g0 in index.get(units[k0], []):
            ok = sum(1 for d in range(1, 4) if k0 + d < len(units) and g0 + d < len(rawn) and units[k0 + d] == rawn[g0 + d])
            if ok >= 2 or (ok >= 1 and len(units) < 4):
                start = g0 - k0; break
        if start is not None:
            break
    g = max(0, start if start is not None else 0)
    k = 0
    while k < len(units):
        t = units[k]
        if not t:
            ev.append({"p": k, "종류": "빈 문단"}); k += 1; continue
        if g < len(rawn) and t == rawn[g]:
            ev.append({"p": k, "종류": "일치", "원문": [g]}); g += 1; k += 1; continue
        if g < len(rawn) and t.startswith(rawn[g]) and len(t) > len(rawn[g]):
            acc, h = "", g
            while h < len(rawn) and len(acc) < len(t):
                acc += rawn[h]; h += 1
            if acc == t:
                ev.append({"p": k, "종류": "원문 여러 문단을 합침", "원문": list(range(g, h))}); g = h; k += 1; continue
        if g < len(rawn) and rawn[g].startswith(t):
            acc, j = "", k
            while j < len(units) and len(acc) < len(rawn[g]):
                acc += units[j]; j += 1
            if acc == rawn[g]:
                ev.append({"p": k, "종류": "원문 한 문단을 쪼갬", "원문": [g], "쪼갠 수": j - k}); g += 1; k = j; continue
        # 앞쪽 원문에서 정확히 같은 문단을 찾으면 그 사이 원문은 빠진 것
        jump = next((j for j in range(g + 1, min(len(rawn), g + 25)) if rawn[j] == t), None)
        if jump is not None:
            for x in range(g, jump):
                ev.append({"p": None, "종류": "원문 문단 누락", "원문": [x], "원문 앞부분": raw[x][1][:40]})
            ev.append({"p": k, "종류": "일치", "원문": [jump]}); g = jump + 1; k += 1; continue
        if g < len(rawn):
            r = difflib.SequenceMatcher(None, rawn[g], t, autojunk=False)
            if r.ratio() >= 0.8:
                ops = [(tag, rawn[g][i1:i2], t[j1:j2]) for tag, i1, i2, j1, j2 in r.get_opcodes() if tag != "equal"]
                ev.append({"p": k, "종류": "글자 차이", "원문": [g], "유사도": round(r.ratio(), 3), "차이": ops[:8]}); g += 1; k += 1; continue
            if g + 1 < len(rawn):
                r2 = difflib.SequenceMatcher(None, rawn[g] + rawn[g + 1], t, autojunk=False)
                if r2.ratio() >= 0.9:
                    ops = [(tag, (rawn[g] + rawn[g + 1])[i1:i2], t[j1:j2]) for tag, i1, i2, j1, j2 in r2.get_opcodes() if tag != "equal"]
                    ev.append({"p": k, "종류": "합침 + 글자 차이", "원문": [g, g + 1], "유사도": round(r2.ratio(), 3), "차이": ops[:8]}); g += 2; k += 1; continue
        ev.append({"p": k, "종류": "원문에 없음", "앞부분": t[:50]}); k += 1
    return ev

