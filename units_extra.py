"""追加単元生成器: 図形・データ・関数系の全単元カバー用."""
import random


def gen_heimen(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        t = topic or rng.choice(["対頂角・同位角", "おうぎ形", "作図の基礎"])
        if "おうぎ形" in t:
            r = rng.randint(3, 9); a = rng.choice([30, 45, 60, 90, 120])
            out.append({"no": i+1, "q": f"半径 {r}cm、中心角 {a}°のおうぎ形の弧の長さと面積を求めよ。下の図も確認しよう。",
                        "hint": "弧=2πr×a/360、面積=πr²×a/360。",
                        "answer": f"弧 {2*r*a/360:.1f}πcm、面積 {r*r*a/360:.1f}πcm²",
                        "explanation": f"弧=2π×{r}×{a}/360、面積=π×{r}²×{a}/360。",
                        "steps": [f"弧=2π×{r}×{a}/360", f"面積=π×{r}²×{a}/360"], "kind": "おうぎ形",
                        "fig": ("sector", r, a)})
        elif "対頂角" in t or "同位角" in t:
            a = rng.randint(30, 150)
            out.append({"no": i+1, "q": f"2直線の交わる角の1つが {a}°のとき、対頂角と隣り合う角を求めよ。",
                        "hint": "対頂角は等しい。隣は180°からひく。",
                        "answer": f"対頂角 {a}°、隣 {180-a}°",
                        "explanation": f"対頂角={a}°、隣=180-{a}={180-a}°。",
                        "steps": [f"対頂角={a}°", f"隣=180-{a}={180-a}°"], "kind": "角度"})
        else:
            out.append({"no": i+1, "q": "直線ℓ上の点Oを通り、ℓに垂直な直線を作図する手順を書け。",
                        "hint": "O中心の弧→2交点から等半径の弧→結ぶ。",
                        "answer": "垂線の作図 (手順3ステップ)",
                        "explanation": "①O中心で弧 ②2点から等半径 ③結ぶ。",
                        "steps": ["O中心で弧", "2点から等半径", "結ぶ"], "kind": "作図の基礎"})
    return out


def gen_kukan(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        t = topic or rng.choice(["角柱・円柱の体積", "錐体の体積", "球の体積・表面積"])
        if "錐体" in t:
            a = rng.randint(3, 6); h = rng.randint(4, 10)
            out.append({"no": i+1, "q": f"底面積 {a*a}cm²、高さ {h}cmの角錐の体積を求めよ。下の図も確認しよう。",
                        "hint": "錐体=柱体×1/3。",
                        "answer": f"{a*a*h/3:.1f}cm³",
                        "explanation": f"{a*a}×{h}÷3。",
                        "steps": [f"{a*a}×{h}÷3"], "kind": "錐体の体積",
                        "fig": ("pyramid", a, h)})
        elif "球" in t:
            r = rng.choice([3, 4, 5, 6])
            out.append({"no": i+1, "q": f"半径 {r}cmの球の体積と表面積を求めよ。下の図も確認しよう。",
                        "hint": "体積=4/3πr³、表面積=4πr²。",
                        "answer": f"体積 {4*r**3/3:.1f}πcm³、表面積 {4*r*r}πcm²",
                        "explanation": f"体積=4/3π×{r}³、表面積=4π×{r}²。",
                        "steps": [f"体積=4/3π×{r}³", f"表面積=4π×{r}²"], "kind": "球",
                        "fig": ("sphere", r, 0)})
        else:
            r = rng.randint(2, 5); h = rng.randint(4, 10)
            out.append({"no": i+1, "q": f"底面の半径 {r}cm、高さ {h}cmの円柱の体積と表面積を求めよ。下の図も確認しよう。",
                        "hint": "体積=πr²h、表面積=2πr²+2πrh。",
                        "answer": f"体積 {r*r*h}πcm³、表面積 {2*r*r+2*r*h}πcm²",
                        "explanation": f"体積=π×{r}²×{h}、表面積=2π×{r}²+2π×{r}×{h}。",
                        "steps": [f"体積=π×{r}²×{h}", f"表面積=2π{r}²+2π{r}{h}"], "kind": "柱体の体積",
                        "fig": ("cube", r, h)})
    return out


def gen_data1(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        t = topic or rng.choice(["平均値・中央値・最頻値", "度数分布・ヒストグラム", "相対度数"])
        if "平均" in t:
            n = 5
            vals = sorted(rng.randint(10, 30) for _ in range(n))
            mean = sum(vals) / n
            s = "、".join(map(str, vals))
            out.append({"no": i+1, "q": f"データ {s} の平均値・中央値・最頻値を求めよ(最頻値はなければ「なし」)。",
                        "hint": "平均=合計÷個数、中央値=真ん中。",
                        "answer": f"平均 {mean:.1f}、中央値 {vals[n//2]}",
                        "explanation": f"合計{sum(vals)}÷{n}={mean:.1f}、中央{vals[n//2]}。",
                        "steps": [f"合計{sum(vals)}÷{n}", f"中央{vals[n//2]}"], "kind": "代表値"})
        elif "相対" in t:
            d = rng.randint(20, 40); tot = rng.choice([50, 100])
            out.append({"no": i+1, "q": f"全度数 {tot} のうち階級の度数が {d} のとき相対度数を求めよ。",
                        "hint": "相対度数=度数÷合計。",
                        "answer": f"{d/tot:.2f}",
                        "explanation": f"{d}÷{tot}={d/tot:.2f}。",
                        "steps": [f"{d}÷{tot}"], "kind": "相対度数"})
        else:
            out.append({"no": i+1, "q": "ヒストグラムで最も度数の高い階級を何というか。またその読み取りの注意点を書け。",
                        "hint": "山の頂上に注目。階級の幅に注意。",
                        "answer": "最頻階級。階級幅・境界に注意して読む。",
                        "explanation": "頂点=最頻階級。",
                        "steps": ["頂点を確認"], "kind": "ヒストグラム"})
    return out


def gen_hako(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        vals = sorted(rng.sample(range(10, 60), 9))
        q1, med, q3 = vals[2], vals[4], vals[6]
        out.append({"no": i+1, "q": f"データ {vals} の最小値・第1四分位数・中央値・第3四分位数・最大値を求め、箱ひげ図の要点を書け。",
                    "hint": "小さい方から1/4・1/2・3/4の位置。四分位範囲=Q3-Q1。",
                    "answer": f"最小{vals[0]}、Q1{q1}、中央{med}、Q3{q3}、最大{vals[-1]}、範囲{q3-q1}",
                    "explanation": f"Q1={q1}、中央={med}、Q3={q3}、範囲={q3-q1}。",
                    "steps": [f"Q1={q1}", f"中央={med}", f"Q3={q3}"], "kind": "箱ひげ図"})
    return out


def gen_kakuritsu(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        t = topic or rng.choice(["1つのさいころ", "2つのさいころ", "くじ・玉"])
        if "2つ" in t:
            tgt = rng.randint(2, 12)
            n = sum(1 for a in range(1, 7) for b in range(1, 7) if a + b == tgt)
            out.append({"no": i+1, "q": f"2つのさいころを投げ、出た目の和が {tgt} になる確率を求めよ。",
                        "hint": "表36通り中の当てはまりを数える。",
                        "answer": f"{n}/36 = {n//__import__('math').gcd(n,36)}/{36//__import__('math').gcd(n,36)}",
                        "explanation": f"36通り中{n}通り。",
                        "steps": ["36通りを整理", f"該当{n}通り"], "kind": "確率"})
        elif "くじ" in t or "玉" in t:
            tot = rng.choice([5, 6, 8, 10]); win = rng.randint(1, tot - 1)
            import math
            g = math.gcd(win, tot)
            out.append({"no": i+1, "q": f"{tot}本中あたり{win}本のくじを1本引くとき、あたりの確率を求めよ。",
                        "hint": "確率=あたり÷全体。",
                        "answer": f"{win//g}/{tot//g}",
                        "explanation": f"{win}÷{tot}。",
                        "steps": [f"{win}÷{tot}"], "kind": "確率"})
        else:
            m = rng.randint(1, 6)
            import math
            g = math.gcd(1, 6)
            out.append({"no": i+1, "q": f"さいころを1回投げ、{m}の目が出る確率を求めよ。",
                        "hint": "6通りのうち1通り。",
                        "answer": "1/6",
                        "explanation": "1÷6。",
                        "steps": ["6通り中1通り"], "kind": "確率"})
    return out


def gen_takoshiki(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        t = topic or rng.choice(["展開", "因数分解", "公式の利用"])
        a, b = rng.randint(1, 9), rng.randint(1, 9)
        if "因数" in t:
            out.append({"no": i+1, "q": f"x² + {a+b}x + {a*b} を因数分解せよ。",
                        "hint": "足して和・かけて積の2数eh.",
                        "answer": f"(x + {a})(x + {b})",
                        "explanation": f"和{a+b}・積{a*b}→{a},{b}。",
                        "steps": [f"和{a+b}・積{a*b}", f"(x+{a})(x+{b})"], "kind": "因数分解"})
        else:
            out.append({"no": i+1, "q": f"(x + {a})(x + {b}) を展開せよ。",
                        "hint": "分配→同類項まとめ。",
                        "answer": f"x² + {a+b}x + {a*b}",
                        "explanation": f"x²+({a}+{b})x+{a*b}。",
                        "steps": [f"x²+({a}+{b})x+{a*b}"], "kind": "展開"})
    return out


def gen_heihokon(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        t = topic or rng.choice(["平方根の意味", "根号の計算", "有理数・無理数"])
        if "計算" in t:
            a = rng.randint(2, 9)
            out.append({"no": i+1, "q": f"√{a*a} の値を求めよ。また √{a}×√{a} を計算せよ。",
                        "hint": "√a²=a (a>0)。",
                        "answer": f"{a}、{a}",
                        "explanation": f"√{a*a}={a}。",
                        "steps": [f"√{a*a}={a}"], "kind": "平方根"})
        elif "有理数" in t:
            out.append({"no": i+1, "q": "√2、√4、0.5、-3 のうち有理数と無理数に分けよ。",
                        "hint": "分数・整数・有限小数=有理数。",
                        "answer": "有理数: √4、0.5、-3 / 無理数: √2",
                        "explanation": "√4=2は整数。",
                        "steps": ["√4=2"], "kind": "有理数・無理数"})
        else:
            k = rng.choice([4, 9, 16, 25])
            out.append({"no": i+1, "q": f"x² = {k} を解け。平方根の意味を確認しよう。",
                        "hint": "x=±√k。マイナス忘れ注意。",
                        "answer": f"x = ±{int(k**0.5)}",
                        "explanation": f"x=±√{k}。",
                        "steps": [f"x=±√{k}"], "kind": "平方根"})
    return out


def gen_nijikansu(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        a = rng.choice([1, 2, 3, -1, -2]) or 1
        x = rng.randint(-3, 3)
        out.append({"no": i+1, "q": f"関数 y = {a}x² について、x = {x} のときの y を求めよ。グラフの形の特徴も書け。",
                    "hint": "代入だけ。a>0で下に凸、a<0で上に凸。",
                    "answer": f"y = {a*x*x}",
                    "explanation": f"y={a}×({x})²={a*x*x}。",
                    "steps": [f"y={a}×({x})²"], "kind": "y=ax²",
                    "graph": ("parabola", a, 0)})
    return out


def gen_soji(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        t = topic or rng.choice(["相似比と長さ", "面積比・体積比", "中点連結定理"])
        if "面積" in t or "体積" in t:
            k = rng.randint(2, 3)
            out.append({"no": i+1, "q": f"相似比が 1:{k} の2つの図形で、小さい方の面積が 6cm² のとき大きい方の面積を求めよ。",
                        "hint": "面積比=相似比の2乗。",
                        "answer": f"{6*k*k}cm²",
                        "explanation": f"面積比1:{k*k}→6×{k*k}。",
                        "steps": [f"面積比1:{k*k}"], "kind": "面積比"})
        elif "中点" in t:
            b = rng.randint(6, 12)
            out.append({"no": i+1, "q": f"三角形の2辺の中点を結ぶ線分と底辺 {b}cm の関係を書き、線分の長さを求めよ。",
                        "hint": "中点連結: 平行で長さは半分。",
                        "answer": f"{b/2:.1f}cm、底辺に平行",
                        "explanation": f"{b}÷2={b/2}。",
                        "steps": [f"{b}÷2"], "kind": "中点連結定理"})
        else:
            k = rng.randint(2, 3); l = rng.randint(3, 8)
            out.append({"no": i+1, "q": f"相似比 1:{k} で、対応する辺が {l}cm のとき相手の辺を求めよ。",
                        "hint": "対応する辺の比=相似比。",
                        "answer": f"{l*k}cm",
                        "explanation": f"{l}×{k}={l*k}。",
                        "steps": [f"{l}×{k}"], "kind": "相似比"})
    return out


def gen_en(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        c = rng.choice([40, 50, 60, 70, 80])
        out.append({"no": i+1, "q": f"弧に対する中心角が {c*2}°のとき円周角を求めよ。逆に円周角 {c}°の中心角も書け。",
                    "hint": "円周角=中心角÷2。",
                    "answer": f"円周角 {c}°、中心角 {c*2}°",
                    "explanation": f"{c*2}÷2={c}。",
                    "steps": [f"{c*2}÷2={c}"], "kind": "円周角"})
    return out


def gen_sanpei(count, difficulty, rng, topic=None, **kw):
    out = []
    triples = [(3, 4, 5), (5, 12, 13), (6, 8, 10)]
    for i in range(count):
        a, b, c = rng.choice(triples)
        hide = rng.choice(["c", "b"])
        if hide == "c":
            out.append({"no": i+1, "q": f"直角をはさむ2辺が {a}cm、{b}cm の直角三角形の斜辺を求めよ。",
                        "hint": "c²=a²+b²。",
                        "answer": f"{c}cm",
                        "explanation": f"√({a}²+{b}²)=√{a*a+b*b}={c}。",
                        "steps": [f"√({a}²+{b}²)={c}"], "kind": "三平方の定理"})
        else:
            out.append({"no": i+1, "q": f"斜辺 {c}cm、1辺 {a}cm の直角三角形の残りの辺を求めよ。",
                        "hint": "b²=c²-a²。",
                        "answer": f"{b}cm",
                        "explanation": f"√({c}²-{a}²)={b}。",
                        "steps": [f"√({c}²-{a}²)={b}"], "kind": "三平方の定理"})
    return out


def gen_hyohon(count, difficulty, rng, topic=None, **kw):
    out = []
    for i in range(count):
        m = rng.randint(150, 170)
        out.append({"no": i+1, "q": f"全校生徒から無作為に抽出した20人の身長の標本平均が {m}cm のとき、母集団の平均の推定値を書け。全数調査との違いも書け。",
                    "hint": "標本平均≒母平均。無作為が条件。",
                    "answer": f"約{m}cm。全数=全員、標本=一部。",
                    "explanation": f"推定値約{m}cm。",
                    "steps": [f"推定約{m}cm"], "kind": "標本調査"})
    return out
