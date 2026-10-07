"""StudyAid超えの新規機能群: 問題DB・誤答推定・集計所見・遡り診断・教科書対応."""
import json
import os
import sys
import time

if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)
elif os.environ.get("VERCEL"):
    BASE = "/tmp/mathgen"
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
try:
    os.makedirs(BASE, exist_ok=True)
except OSError:
    pass
DB_PATH = os.path.join(BASE, "problems_db.json")
MAX_RECORDS = 200


def db_save(record):
    try:
        data = db_load()
    except Exception:
        data = []
    record["time"] = time.strftime("%Y-%m-%d %H:%M")
    data.insert(0, record)
    data = data[:MAX_RECORDS]
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
    return record


def db_load():
    if not os.path.isfile(DB_PATH):
        return []
    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def db_search(keyword="", unit=""):
    out = []
    for r in db_load():
        blob = (r.get("unit_label", "") + " " + r.get("topic", "") + " " +
                r.get("test_name", "") + " " + " ".join(p.get("q", "") for p in r.get("problems", [])[:3]))
        if unit and r.get("unit") != unit:
            continue
        if keyword and keyword not in blob:
            continue
        out.append(r)
    return out


# ---- 誤答推定 (数学固有のヒューリスティクス) ----
def guess_mistake(unit, correct, student):
    """正答・生徒解答の文字列から誤答パターンを推定する。"""
    c, s = (correct or ""), (student or "")
    notes = []
    if unit in ("中2_連立方程式", "中1_方程式"):
        if "-" in c and "+" in s or "+" in c and "-" in s:
            notes.append("符号ミス(移項・加減)の可能性が高いです")
        if "y" in c and "y" not in s:
            notes.append("代入し忘れ・片方の文字だけ求めた可能性")
        if not notes:
            notes.append("途中式の計算ミス(分配・通分)の可能性")
        remedy = "同型の基本問題で途中式の書き方を確認しましょう"
    elif "因数分解" in (c + s) or unit in ("中3_多項式", "中3_二次方程式"):
        notes.append("符号の組み合わせミス(和と積の取り違え)の可能性")
        remedy = "和と積を先に書くスモールステップで確認しましょう"
    elif unit in ("中3_平方根",):
        notes.append("±の抜け・√の外し忘れの可能性")
        remedy = "x²=k型は±を確認しましょう"
    else:
        notes.append("計算・読み取りミスの可能性")
        remedy = "同型の基本問題で手順を確認しましょう"
    return {"causes": notes, "remedy": remedy}


# ---- 観点別集計→所見文案 ----
def shoken(chisiki, chisiki_full, shiko, shiko_full, taido):
    try:
        r1 = float(chisiki) / float(chisiki_full) * 100
    except (ValueError, ZeroDivisionError):
        r1 = 0
    try:
        r2 = float(shiko) / float(shiko_full) * 100
    except (ValueError, ZeroDivisionError):
        r2 = 0
    def hyo(r):
        return "A" if r >= 80 else ("B" if r >= 50 else "C")
    h1, h2 = hyo(r1), hyo(r2)
    bun = (f"知識・技能{h1}(得点率{r1:.0f}%)、思考・判断・表現{h2}(得点率{r2:.0f}%)、"
           f"主体的に学習に取り組む態度[{taido}]。")
    if h1 == "A" and h2 == "A":
        bun += "基礎・応用ともに安定しており、次の単元への接続が期待できます。"
    elif h2 in ("B", "C"):
        bun += "途中式や理由の説明を丁寧に書く練習を続けましょう。"
    else:
        bun += "基本の計算・用語の定着を優先し、反復で確実にしましょう。"
    return {"bun": bun, "h1": h1, "h2": h2}


# ---- 遡り診断マップ ----
PREREQ = {
    "中2_連立方程式": ["中1_方程式", "中1_文字式", "中1_正負の数"],
    "中2_一次関数": ["中1_比例反比例", "中1_方程式"],
    "中2_証明": ["中1_平面図形", "中1_作図"],
    "中3_二次方程式": ["中3_多項式", "中1_方程式"],
    "中3_多項式": ["中2_式と計算", "中1_文字式"],
    "中3_相似": ["中2_証明", "中1_平面図形"],
    "中3_三平方": ["中3_平方根", "中2_証明"],
    "中3_円": ["中2_証明", "中1_平面図形"],
    "中3_2次関数": ["中2_一次関数", "中1_比例反比例"],
    "中3_平方根": ["中1_正負の数", ],
    "中2_確率": ["中1_データ", ],
    "中2_箱ひげ図": ["中1_データ", ],
}


def prereq_chain(unit):
    chain, seen, cur = [], set(), unit
    while cur in PREREQ and cur not in seen:
        seen.add(cur)
        nxt = [u for u in PREREQ[cur] if u not in seen]
        chain.extend(nxt)
        cur = nxt[0] if nxt else ""
    return chain


# ---- 教科書ページ対応 (代表例: 要望があれば拡張) ----
TEXTBOOK = [
    {"pub": "東京書籍", "grade": 2, "pages": "34-52", "unit": "中2_連立方程式", "topic": ""},
    {"pub": "東京書籍", "grade": 2, "pages": "53-88", "unit": "中2_一次関数", "topic": ""},
    {"pub": "東京書籍", "grade": 2, "pages": "89-120", "unit": "中2_証明", "topic": ""},
    {"pub": "啓林館", "grade": 2, "pages": "36-54", "unit": "中2_連立方程式", "topic": ""},
    {"pub": "東京書籍", "grade": 3, "pages": "30-55", "unit": "中3_二次方程式", "topic": ""},
    {"pub": "東京書籍", "grade": 1, "pages": "100-130", "unit": "中1_作図", "topic": ""},
]


def textbook_search(keyword):
    out = []
    for r in TEXTBOOK:
        blob = r["pub"] + str(r["grade"]) + r["pages"] + r["unit"]
        if (not keyword) or (keyword in blob):
            out.append(r)
    return out
