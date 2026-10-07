"""問題生成ロジック v3: 全単元対応 + 連立方程式パターン別 + 途中式ステップ生成."""
import random
from math import gcd


def _fmt_term(coef, var, first):
    if coef == 0:
        return ""
    sign = "+" if coef > 0 else "-"
    a = abs(coef)
    body = var if (a == 1 and var) else (f"{a}{var}" if var else f"{a}")
    if first:
        return f"-{body}" if coef < 0 else body
    return f" {sign} {body}"


def _linear_expr(a, b, first_var="x", second_var="y"):
    s = _fmt_term(a, first_var, True)
    t = _fmt_term(b, second_var, False)
    return (s + t).strip() or "0"


def _lcm(a, b):
    return abs(a * b) // gcd(a, b) if a and b else 0


REN_PATTERNS = {
    "mix": "おまかせミックス",
    "kagen_easy": "加減法・そのまま消去",
    "kagen_standard": "加減法・片方/両方を倍して",
    "daiyun": "代入法",
    "kakko": "かっこ付き",
    "shosu": "小数を含む",
    "bunsu": "分数を含む",
}


def _base_int_solution(rng):
    x0 = rng.randint(-5, 5)
    y0 = rng.randint(-5, 5)
    if x0 == 0 and y0 == 0:
        x0, y0 = 2, 3
    return x0, y0


def _independent_coeffs(rng, lo=1, hi=6):
    while True:
        a1 = rng.randint(lo, hi) * rng.choice([1, -1])
        b1 = rng.randint(lo, hi) * rng.choice([1, -1])
        a2 = rng.randint(lo, hi) * rng.choice([1, -1])
        b2 = rng.randint(lo, hi) * rng.choice([1, -1])
        if a1 * b2 - a2 * b1 != 0:
            return a1, b1, a2, b2


def _steps_kagen(a1, b1, c1, a2, b2, c2, x0, y0):
    """加減法の途中式ステップを組み立てる"""
    steps = [f"①: {_linear_expr(a1,b1)} = {c1}", f"②: {_linear_expr(a2,b2)} = {c2}"]
    L = _lcm(abs(b1), abs(b2))
    m1, m2 = L // abs(b1), L // abs(b2)
    op = "-" if (b1 > 0) == (b2 > 0) else "+"
    if m1 == 1 and m2 == 1:
        steps.append(f"① {op} ② より y を消去する。")
    else:
        steps.append(f"①×{m1} {op} ②×{m2} より y を消去する。")
    coef_x = a1 * m1 + a2 * m2 if op == "+" else a1 * m1 - a2 * m2
    const = c1 * m1 + c2 * m2 if op == "+" else c1 * m1 - c2 * m2
    steps.append(f"{coef_x}x = {const}")
    steps.append(f"x = {x0}")
    steps.append(f"x = {x0} を①に代入して、{a1}×({x0}) + ({b1})y = {c1}")
    steps.append(f"y = {y0}")
    steps.append(f"答え: x = {x0} , y = {y0}")
    return steps


def gen_renritsu(count, difficulty, rng, ren_pattern="mix", **kw):
    problems = []
    for i in range(count):
        pat = ren_pattern
        if pat == "mix":
            pat = rng.choice(["kagen_easy", "kagen_standard", "daiyun", "kakko", "shosu", "bunsu"])
        x0, y0 = _base_int_solution(rng)
        if difficulty == "exam":
            # 入試レベル: 解の絶対値を大きくし、計算負荷を上げる
            x0 = rng.randint(-9, 9) or 7
            y0 = rng.randint(-9, 9) or -6
            if x0 == 0 and y0 == 0:
                x0, y0 = 7, -5
        if pat == "kagen_easy":
            b = rng.randint(1, 4) * rng.choice([1, -1])
            a1, a2 = rng.randint(1, 4), rng.randint(1, 4)
            b1, b2 = (b, b) if rng.random() < 0.5 else (b, -b)
            c1, c2 = a1 * x0 + b1 * y0, a2 * x0 + b2 * y0
            eq1, eq2 = f"{_linear_expr(a1,b1)} = {c1}", f"{_linear_expr(a2,b2)} = {c2}"
            hint = "係数がそろっている! ①±②で1文字消去 (加減法)。"
            steps = _steps_kagen(a1, b1, c1, a2, b2, c2, x0, y0)
            kind = "加減法・基本"
        elif pat == "daiyun":
            # y = ax + b 型を1式に含める
            a = rng.randint(-3, 3) or 2
            b = rng.randint(-5, 5)
            # ②: y = ax + b, ①: 一般式 (解が x0,y0 になるよう c を逆算。y0 = a*x0+b になる必要あり)
            y0 = a * x0 + b
            a1, b1 = rng.randint(1, 5), rng.randint(1, 5) * rng.choice([1, -1])
            c1 = a1 * x0 + b1 * y0
            eq1 = f"{_linear_expr(a1,b1)} = {c1}"
            eq2 = f"y = {_linear_expr(a, b, 'x', '')}".replace("  ", " ").strip()
            hint = "②は y = … の形! ①にそのまま代入 (代入法)。"
            steps = [f"①: {eq1}", f"②: {eq2}",
                     "②を①の y に代入する。", f"{a1}x + ({b1})×({eq2.split('=')[1].strip()}) = {c1}",
                     f"x = {x0}", f"②に代入して y = {y0}", f"答え: x = {x0} , y = {y0}"]
            kind = "代入法"
            c2 = None
            a2, b2, c2 = None, None, None
        elif pat == "kakko":
            a1, b1, a2, b2 = _independent_coeffs(rng, 1, 4)
            c1, c2 = a1 * x0 + b1 * y0, a2 * x0 + b2 * y0
            k1, k2 = rng.randint(2, 3), rng.randint(2, 3)
            eq1 = f"{k1}(x {'+' if b1>=0 else '-'} {abs(b1)}y) + {a1 - k1}x = {c1}".replace("+ -", "- ")
            # 簡易表示: かっこを外す前の形を提示 (整理すると整数係数になる)
            eq1 = f"{k1}(x {b1:+d}y) …を整理すると {_linear_expr(a1,b1)} = {c1}".replace("+ -", "- ")
            eq2 = f"{_linear_expr(a2,b2)} = {c2}"
            hint = "まずかっこを外して整理! 分配法則→同類項まとめ。"
            steps = [f"①のかっこを外す: {_linear_expr(a1,b1)} = {c1}", f"②: {eq2}"] + \
                _steps_kagen(a1, b1, c1, a2, b2, c2, x0, y0)[2:]
            kind = "かっこ付き"
        elif pat == "shosu":
            a1, b1, a2, b2 = _independent_coeffs(rng, 1, 5)
            c1, c2 = a1 * x0 + b1 * y0, a2 * x0 + b2 * y0
            eq1 = f"{a1/10:.1f}x + {b1/10:.1f}y = {c1/10:.1f}".replace("+ -", "- ")
            eq2 = f"{_linear_expr(a2,b2)} = {c2}"
            hint = "小数は×10で整数に! ①の両辺を10倍しよう。"
            steps = [f"①: {eq1}", f"②: {eq2}", f"①×10 → {_linear_expr(a1,b1)} = {c1} …③"] + \
                _steps_kagen(a1, b1, c1, a2, b2, c2, x0, y0)[2:]
            kind = "小数"
        elif pat == "bunsu":
            a1, b1, a2, b2 = _independent_coeffs(rng, 1, 4)
            c1, c2 = a1 * x0 + b1 * y0, a2 * x0 + b2 * y0
            d1, d2 = rng.choice([2, 3]), rng.choice([2, 3])
            eq1 = f"x/{d1} + y/{d2} = {c1}/{d1 * d2} の形を整数化 (分母×{d1*d2})"
            eq1_disp = f"(x/{d1} + y/{d2})×{d1*d2} → {_linear_expr(a1,b1)} = {c1}"
            eq2 = f"{_linear_expr(a2,b2)} = {c2}"
            hint = f"分数は分母の公倍数({d1*d2})をかけて払おう!"
            steps = [f"①の両辺×{d1*d2} → {_linear_expr(a1,b1)} = {c1} …③", f"②: {eq2}"] + \
                _steps_kagen(a1, b1, c1, a2, b2, c2, x0, y0)[2:]
            eq1 = eq1_disp
            kind = "分数"
        else:  # kagen_standard (+exam は係数を大型化)
            lo, hi = (3, 9) if difficulty == "exam" else (1, 6)
            a1, b1, a2, b2 = _independent_coeffs(rng, lo, hi)
            c1, c2 = a1 * x0 + b1 * y0, a2 * x0 + b2 * y0
            eq1, eq2 = f"{_linear_expr(a1,b1)} = {c1}", f"{_linear_expr(a2,b2)} = {c2}"
            hint = "係数をそろえるために何倍するか考えよう。符号ミス注意!"
            steps = _steps_kagen(a1, b1, c1, a2, b2, c2, x0, y0)
            kind = "加減法・標準"
        q = f"{eq1} …①\n{eq2} …②"
        answer = f"x = {x0} , y = {y0}"
        exp = f"[{kind}] " + " / ".join(steps[-3:])
        if difficulty == "exam":
            hint = "【入試】" + hint
            kind = kind + "・入試"
        d = {"no": i + 1, "q": q, "hint": hint, "answer": answer,
             "explanation": exp, "eq1": eq1, "eq2": eq2, "steps": steps, "kind": kind}
        problems.append(d)
    return problems


# ---- 既存: 二次方程式・作図・証明 (ステップ付きに拡張) ----
def gen_niji(count, difficulty, rng, **kw):
    problems = []
    for i in range(count):
        p = rng.randint(-5, 5); q = rng.randint(-5, 5)
        s, pr = -(p + q), p * q
        left = "x²" + _fmt_term(s, "x", False) + _fmt_term(pr, "", False)
        qtext = f"{left.strip()} = 0"
        steps = [f"x²{s:+d}x{pr:+d} = 0".replace("+ -", "- "),
                 f"(x {-p:+d})(x {-q:+d}) = 0".replace("+ -", "- "),
                 f"x = {p}, {q}"]
        problems.append({"no": i + 1, "q": qtext, "hint": "因数分解! (x+□)(x+□)を探そう。",
                         "answer": f"x = {p}, {q}", "explanation": " / ".join(steps),
                         "steps": steps, "kind": "因数分解"})
    return problems


SAKUDAI_PATTERNS = ["線分AB ({n}cm) の垂直二等分線", "∠AOB の二等分線",
                    "点P を通り直線ℓに垂直な直線", "正三角形ABC ({n}cm)"]


def gen_sakuzu(count, difficulty, rng, space="normal", **kw):
    problems = []
    for i in range(count):
        pat = rng.choice(SAKUDAI_PATTERNS); n = rng.randint(3, 7)
        title = pat.format(n=n)
        space_note = "【作図スペース: ゆったり2倍】コンパスがはみ出してもOKな広い枠つき。" if space == "large" else "【作図スペース】コンパスの跡は残すこと。"
        q = f"{title} を作図しなさい。\n{space_note}"
        steps = ["① 中心を決めて弧を描く", "② 交点から等半径の弧", "③ 交点を結ぶ"]
        problems.append({"no": i + 1, "q": q, "hint": "針を刺す点●を大きく! 手順は3ステップ。",
                         "answer": "作図跡ありの直線・半直線", "explanation": " / ".join(steps),
                         "steps": steps, "kind": "作図", "wide_space": space == "large",
                         "fig": ("angle" if "∠AOB" in pat else
                                 ("segment" if "線分AB" in pat else "triangle"))})
    return problems


SHOMEI_PATTERNS = [
    {"title": "二等辺三角形の底角", "q": "△ABCでAB=ACのとき∠B=∠Cを証明せよ。頂角Aの二等分線とBCの交点をMとする。[ア]の合同条件を答えよ。",
     "hint": "△ABMと△ACMで3つの等しい辺・角を探そう。",
     "answer": "△ABM≡△ACM (2辺とその間の角)。よって∠B=∠C。",
     "steps": ["仮定: AB=AC, ∠BAM=∠CAM", "AM共通", "→2辺夾角で合同", "→対応する角が等しい"]},
    {"title": "直角三角形の合同", "q": "∠B=∠E=90°、斜辺AC=DF、AB=DEのとき合同を証明せよ。[ア]の条件を答えよ。",
     "hint": "直角三角形の特別な合同条件2つを思い出そう!",
     "answer": "斜辺と他の1辺がそれぞれ等しい。",
     "steps": ["直角を確認", "斜辺と1辺が等しい", "→HL合同"]},
]


def gen_shomei(count, difficulty, rng, proof_style="fill", **kw):
    problems = []
    for i in range(count):
        p = rng.choice(SHOMEI_PATTERNS)
        style_note = "【穴埋め式】[ア][イ]を埋めて完成させよう。" if proof_style == "fill" else "【自由記述式】全文を書こう。"
        problems.append({"no": i + 1, "q": f"【{p['title']}】\n{p['q']}\n{style_note}",
                         "hint": p["hint"], "answer": p["answer"],
                         "explanation": " / ".join(p["steps"]), "steps": p["steps"], "kind": "証明"})
    return problems


# ---- 追加単元 (計算ドリル・関数・データ系の汎用生成) ----
def gen_drill(count, difficulty, rng, op="+-", title="計算ドリル", **kw):
    problems = []
    top = 20 if difficulty == "basic" else (50 if difficulty == "standard" else (99 if difficulty == "advanced" else 199))
    for i in range(count):
        a, b = rng.randint(2, top), rng.randint(2, top)
        o = rng.choice(list(op))
        if o == "+": q, ans, st = f"{a} + {b} =", a + b, [f"{a}+{b}={a+b}"]
        elif o == "-":
            a, b = max(a, b), min(a, b)
            q, ans, st = f"{a} - {b} =", a - b, [f"{a}-{b}={a-b}"]
        elif o == "×": a, b = rng.randint(2, 9), rng.randint(2, 9); q, ans, st = f"{a} × {b} =", a * b, [f"{a}×{b}={a*b}"]
        else: b = rng.randint(2, 9); a = b * rng.randint(2, 9); q, ans, st = f"{a} ÷ {b} =", a // b, [f"{a}÷{b}={a//b}"]
        problems.append({"no": i + 1, "q": q, "hint": "位取り・符号に注意!", "answer": f"{ans}",
                         "explanation": " / ".join(st), "steps": st, "kind": title})
    return problems


def gen_ichiji(count, difficulty, rng, **kw):
    # 1次方程式 ax + b = c 型
    problems = []
    for i in range(count):
        x0 = rng.randint(-9, 9) or 3
        a = rng.randint(2, 9) * rng.choice([1, -1])
        b = rng.randint(-9, 9)
        c = a * x0 + b
        q = f"{a}x {'+' if b >= 0 else '-'} {abs(b)} = {c}".replace("+ -", "- ")
        steps = [f"{a}x = {c} {'-' if b >= 0 else '+'} {abs(b)} (移項: 符号が変わる)", f"{a}x = {c - b}", f"x = {x0}"]
        problems.append({"no": i + 1, "q": q, "hint": "等号をまたぐと符号が変わる! 移項→両辺÷係数。",
                         "answer": f"x = {x0}", "explanation": " / ".join(steps),
                         "steps": steps, "kind": "1次方程式", "eq1": q, "eq2": ""})
    return problems


def gen_prohirei(count, difficulty, rng, **kw):
    problems = []
    for i in range(count):
        a = rng.choice([2, 3, -2, -3, 4, -4])
        x = rng.randint(1, 6) * rng.choice([1, -1])
        if rng.random() < 0.5:
            q = f"y は x に比例し、x = {x} のとき y = {a * x}。y を x の式で表せ。下のグラフも確認しよう。"
            ans, st = f"y = {a}x", [f"y=axに代入→a={a}"]
            graph = ("line_origin", a, 0)
        else:
            q = f"y は x に反比例し、x = {x} のとき y = {a}。y を x の式で表せ。下のグラフも確認しよう。"
            ans, st = f"y = {x * a}/x", [f"y=a/xに代入→a={x*a}"]
            graph = ("hyperbola", x * a, 0)
        problems.append({"no": i + 1, "q": q, "hint": "比例y=ax / 反比例y=a/x に代入!",
                         "answer": ans, "explanation": " / ".join(st), "steps": st, "kind": "比例・反比例",
                         "graph": graph})
    return problems


def gen_ichijikansu(count, difficulty, rng, **kw):
    problems = []
    for i in range(count):
        a = rng.randint(-4, 4) or 2
        b = rng.randint(-5, 5)
        x = rng.randint(-4, 4)
        q = f"直線 y = {a}x {'+' if b >= 0 else '-'} {abs(b)} について、x = {x} のときの y を求めよ。".replace("+ -", "- ")
        ans = a * x + b
        st = [f"y = {a}×({x}) {'+' if b >= 0 else '-'} {abs(b)}", f"y = {ans}"]
        problems.append({"no": i + 1, "q": q, "hint": "xに代入! 変化の割合は傾きa。",
                         "answer": f"y = {ans}", "explanation": " / ".join(st), "steps": st,
                         "kind": "一次関数", "func_a": a, "func_b": b})
    return problems


from units_extra import (gen_heimen, gen_kukan, gen_data1, gen_hako, gen_kakuritsu,
                          gen_takoshiki, gen_heihokon, gen_nijikansu, gen_soji, gen_en,
                          gen_sanpei, gen_hyohon)

UNIT_META = {
    "中1_正負の数": {"label": "【中1】正の数・負の数", "gen": lambda c, d, r, **k: gen_drill(c, d, r, op="+-", title="正負の数", **k), "area": "数と式",
                      "topics": ["正負の数の意味", "加法・減法", "乗法・除法", "四則混合・利用"]},
    "中1_文字式": {"label": "【中1】文字の式", "gen": lambda c, d, r, **k: gen_drill(c, d, r, op="×÷", title="文字式", **k), "area": "数と式",
                   "topics": ["文字式の表し方", "1次式の加減", "数量の表し方"]},
    "中1_方程式": {"label": "【中1】方程式 (1次方程式)", "gen": gen_ichiji, "area": "数と式",
                   "topics": ["等式の性質", "1次方程式の解き方", "文章題・利用"]},
    "中1_比例反比例": {"label": "【中1】比例と反比例", "gen": gen_prohirei, "area": "関数",
                       "topics": ["関数と変域", "比例のグラフ", "反比例のグラフ", "利用"]},
    "中1_平面図形": {"label": "【中1】平面図形", "gen": gen_heimen, "area": "図形",
                     "topics": ["対頂角・同位角", "おうぎ形", "作図の基礎", "図形の移動"]},
    "中1_作図": {"label": "【中1】基本の作図", "gen": gen_sakuzu, "area": "図形",
                 "topics": ["垂直二等分線", "角の二等分線", "垂線", "正三角形"]},
    "中1_空間図形": {"label": "【中1】空間図形", "gen": gen_kukan, "area": "図形",
                     "topics": ["角柱・円柱の体積", "錐体の体積", "球の体積・表面積", "展開図・投影図"]},
    "中1_データ": {"label": "【中1】データの分析と活用", "gen": gen_data1, "area": "データの活用",
                   "topics": ["平均値・中央値・最頻値", "度数分布・ヒストグラム", "相対度数"]},
    "中2_式と計算": {"label": "【中2】式と計算", "gen": lambda c, d, r, **k: gen_drill(c, d, r, op="+-×", title="式の計算", **k), "area": "数と式",
                      "topics": ["多項式の加減", "単項式の乗除", "文字式の利用", "等式の変形"]},
    "中2_連立方程式": {"label": "【中2】連立二元一次方程式", "gen": gen_renritsu, "area": "数と式",
                       "topics": ["加減法・基本", "加減法・標準", "代入法", "かっこ付き", "小数", "分数", "文章題・利用"]},
    "中2_一次関数": {"label": "【中2】一次関数", "gen": gen_ichijikansu, "area": "関数",
                     "topics": ["変化の割合", "y=ax+bのグラフ", "直線の式", "方程式とグラフ", "利用"]},
    "中2_証明": {"label": "【中2】平行と合同・証明", "gen": gen_shomei, "area": "図形",
                 "topics": ["対頂角・平行線の角", "多角形の内角・外角", "三角形の合同条件", "証明の書き方"]},
    "中2_三角形四角形": {"label": "【中2】三角形と四角形", "gen": gen_shomei, "area": "図形",
                         "topics": ["二等辺三角形", "直角三角形", "平行四辺形の性質と条件"]},
    "中2_箱ひげ図": {"label": "【中2】箱ひげ図とデータの比較", "gen": gen_hako, "area": "データの活用",
                      "topics": ["四分位数・四分位範囲", "箱ひげ図の読み取り", "データの比較"]},
    "中2_確率": {"label": "【中2】確率", "gen": gen_kakuritsu, "area": "データの活用",
                 "topics": ["1つのさいころ", "2つのさいころ", "くじ・玉", "樹形図・表"]},
    "中3_多項式": {"label": "【中3】多項式", "gen": gen_takoshiki, "area": "数と式",
                   "topics": ["展開", "因数分解", "公式の利用", "式の計算の利用"]},
    "中3_平方根": {"label": "【中3】平方根", "gen": gen_heihokon, "area": "数と式",
                   "topics": ["平方根の意味", "根号の計算", "有理数・無理数", "利用"]},
    "中3_二次方程式": {"label": "【中3】二次方程式", "gen": gen_niji, "area": "数と式",
                       "topics": ["平方根を利用した解き方", "解の公式", "因数分解による解き方", "利用"]},
    "中3_2次関数": {"label": "【中3】関数 y=ax²", "gen": gen_nijikansu, "area": "関数",
                    "topics": ["変化の割合", "グラフの特徴", "変域", "利用"]},
    "中3_相似": {"label": "【中3】相似な図形", "gen": gen_soji, "area": "図形",
                 "topics": ["相似比と長さ", "三角形の相似条件", "平行線と線分の比", "中点連結定理", "面積比・体積比"]},
    "中3_円": {"label": "【中3】円", "gen": gen_en, "area": "図形",
               "topics": ["円周角の定理", "円周角の定理の逆", "接線"]},
    "中3_三平方": {"label": "【中3】三平方の定理", "gen": gen_sanpei, "area": "図形",
                   "topics": ["定理と証明", "平面図形への利用", "空間図形への利用"]},
    "中3_標本調査": {"label": "【中3】標本調査", "gen": gen_hyohon, "area": "データの活用",
                     "topics": ["全数調査と標本調査", "標本の抽出", "標本平均と母集団の推定"]},
}


def generate_problems(unit, count=5, difficulty="standard", seed=None, **opts):
    rng = random.Random(seed)
    meta = UNIT_META.get(unit, UNIT_META["中2_連立方程式"])
    count = max(1, min(20, int(count)))
    gen = meta["gen"]
    # 作図用の space_mode -> space に読み替え、その他余分な引数は捨てる
    opts = dict(opts)
    if "space_mode" in opts and "space" not in opts:
        opts["space"] = opts.pop("space_mode")
    else:
        opts.pop("space_mode", None)
    try:
        problems, label = gen(count, difficulty, rng, **opts), meta["label"]
    except TypeError:
        problems, label = gen(count, difficulty, rng), meta["label"]
    if difficulty == "exam":
        # 連立・ドリル以外も入試表示に統一 (数値強化済みのものは重ねない)
        for pb in problems:
            if "・入試" not in (pb.get("kind") or ""):
                pb["kind"] = (pb.get("kind") or "問題") + "・入試"
            if not (pb.get("hint") or "").startswith("【入試】"):
                pb["hint"] = "【入試】時間配分を意識! 見直しまで解き切ろう。" + pb.get("hint", "")
    return problems, label
