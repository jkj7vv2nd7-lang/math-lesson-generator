from flask import Flask, request, send_file, render_template, Response
import docx
from docx.shared import Inches, Pt, RGBColor, Mm, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.oxml import OxmlElement
import io
import json
import os
import random
import sys
import tempfile

from templates import generate_problems, UNIT_META, REN_PATTERNS

if getattr(sys, "frozen", False):
    # PyInstaller EXE: テンプレートは展開先、保存データはEXE隣に置く
    BASE = os.path.dirname(sys.executable)
    MEIPASS = getattr(sys, "_MEIPASS", BASE)
    TEMPLATE_DIR = os.path.join(MEIPASS, "templates")
elif os.environ.get("VERCEL"):
    # Vercel (読み取り専用FS): 保存データは /tmp に置く
    BASE = "/tmp/mathgen"
    TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_DIR = os.path.join(BASE, "templates")
STOCK_DIR = os.path.join(BASE, "figure_stock")
os.makedirs(STOCK_DIR, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATE_DIR)

FONT_JAPANESE = "UD デジタル 教科書体 NK-R"
FONT_LATIN = "Cambria Math"

DIFF_LABEL = {"basic": "基礎", "standard": "標準", "advanced": "発展", "exam": "入試",
              "multi": "基礎＋標準 同時"}
PRINT_LABEL = {"full": "レイアウト通り", "ans_blank": "答空欄", "expl_blank": "解説空欄",
               "both_blank": "答・解説空欄"}
TEMPLATE_LABEL = {"pattern_a": "パターンA: 1行完結型", "pattern_b": "パターンB: 左右分割型",
                  "pattern_c": "パターンC: 定期テスト型(2段+右端集約)"}
SUPPORT_LABEL = {"none": "指定なし", "calc_step": "計算手順ヒントあり",
                 "visual": "ポイント解説あり", "yutori": "ゆったり解答欄",
                 "draw_space": "作図ゆったり拡大", "proof_fill": "証明穴埋め足場"}
PAPER_SIZES = {"A4": (210, 297), "B5": (182, 257), "B4": (257, 364), "A3": (297, 420)}


def set_run_font(run, font_size=10.5, is_italic=False, is_bold=False, color=None):
    run.font.size = Pt(font_size)
    run.bold = is_bold
    run.italic = is_italic
    if color is not None:
        run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    for old in rPr.findall(qn('w:rFonts')):
        rPr.remove(old)
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), FONT_LATIN)
    rFonts.set(qn('w:hAnsi'), FONT_LATIN)
    rFonts.set(qn('w:eastAsia'), FONT_JAPANESE)
    rFonts.set(qn('w:cs'), FONT_LATIN)
    rPr.append(rFonts)


def escape_xml(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def add_system_equations(paragraph, eq1_text, eq2_text):
    try:
        omml_xml = (
            '<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
            'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<m:oMath><m:d><m:dPr>'
            '<m:begChr m:val="{"/>'
            '<m:endChr m:val=""/>'
            '<m:separate m:val="0"/>'
            '</m:dPr><m:e><m:eqArr>'
            f'<m:e><m:r><m:t>{escape_xml(eq1_text)}</m:t></m:r></m:e>'
            f'<m:e><m:r><m:t>{escape_xml(eq2_text)}</m:t></m:r></m:e>'
            '</m:eqArr></m:e></m:d></m:oMath></m:oMathPara>'
        )
        paragraph._p.append(parse_xml(omml_xml))
    except Exception:
        run = paragraph.add_run("｛ " + eq1_text + " / " + eq2_text)
        set_run_font(run, font_size=11)


def shade_cell(cell, color="F8F9FA"):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def apply_paper(doc, paper, orient, margin="std"):
    w_mm, h_mm = PAPER_SIZES.get(paper, PAPER_SIZES["A4"])
    m = {"narrow": 0.4, "std": 0.6, "wide": 0.9}.get(margin, 0.6)
    for section in doc.sections:
        section.top_margin = Inches(m)
        section.bottom_margin = Inches(m)
        section.left_margin = Inches(m)
        section.right_margin = Inches(m)
        if orient == "landscape":
            section.orientation = WD_ORIENT.LANDSCAPE
            section.page_width, section.page_height = Mm(h_mm), Mm(w_mm)
        else:
            section.orientation = WD_ORIENT.PORTRAIT
            section.page_width, section.page_height = Mm(w_mm), Mm(h_mm)


def make_prop_graph(kind, a, b=0):
    """比例(y=ax)・反比例(y=a/x)・2次関数(y=ax²)のグラフPNG。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        fig, ax = plt.subplots(figsize=(3.2, 3.2), dpi=150)
        ax.axhline(0, color="black", linewidth=1)
        ax.axvline(0, color="black", linewidth=1)
        ax.grid(True, linestyle="--", alpha=0.5)
        if kind == "hyperbola":
            xs1 = np.linspace(0.5, 6, 200); xs2 = np.linspace(-6, -0.5, 200)
            ax.plot(xs1, a / xs1, linewidth=2)
            ax.plot(xs2, a / xs2, linewidth=2)
            ax.set_xlim(-6, 6); ax.set_ylim(-10, 10)
            ax.set_title(f"y = {a}/x")
        elif kind == "parabola":
            xs = np.linspace(-5, 5, 400)
            ax.plot(xs, a * xs ** 2, linewidth=2)
            ax.set_xlim(-6, 6); ax.set_ylim(-2, 12)
            ax.set_title(f"y = {a}x2")
        else:  # line_origin
            xs = list(range(-6, 7))
            ax.plot(xs, [a * x for x in xs], linewidth=2)
            ax.set_xlim(-6, 6); ax.set_ylim(-10, 10)
            ax.set_title(f"y = {a}x")
        ax.set_xlabel("x"); ax.set_ylabel("y")
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path
    except Exception:
        return None


def make_graph_image(a, b, seed=0):
    """一次関数 y=ax+b のグラフPNGを生成してパスを返す。失敗時はNone。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(3.2, 3.2), dpi=150)
        xs = list(range(-6, 7))
        ys = [a * x + b for x in xs]
        ax.axhline(0, color="black", linewidth=1)
        ax.axvline(0, color="black", linewidth=1)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.plot(xs, ys, linewidth=2)
        ax.set_xlim(-6, 6); ax.set_ylim(-10, 10)
        ax.set_xlabel("x"); ax.set_ylabel("y")
        ax.set_title(f"y = {a}x + {b}")
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path
    except Exception:
        return None


def make_unit_figure(unit, pb):
    """単元別の簡易図 (円・相似・箱ひげ図・直角三角形)。PNGパス or None。"""
    if unit not in ("中3_円", "中3_相似", "中2_箱ひげ図", "中3_三平方", "中2_三角形四角形",
                    "中2_証明", "中1_平面図形", "中1_空間図形", "中1_作図"):
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        fig, ax = plt.subplots(figsize=(3.0, 2.6), dpi=150)
        ax.set_aspect("equal")
        ax.axis("off")
        if unit == "中3_円":
            circ = plt.Circle((0.5, 0.5), 0.35, fill=False, linewidth=2)
            ax.add_patch(circ)
            ax.plot([0.5], [0.5], marker="o", markersize=4)
            ax.text(0.5, 0.46, "O", fontsize=10)
            ax.plot([0.5, 0.78], [0.5, 0.68], linewidth=1.5)
            ax.plot([0.5, 0.78], [0.5, 0.32], linewidth=1.5)
            ax.text(0.82, 0.5, "A", fontsize=10)
        elif unit in ("中3_相似", "中2_三角形四角形", "中2_証明"):
            ax.plot([0.1, 0.4, 0.1, 0.1], [0.1, 0.1, 0.5, 0.1], linewidth=2)
            ax.plot([0.55, 0.95, 0.55, 0.55], [0.1, 0.1, 0.7, 0.1], linewidth=2, linestyle="--")
            for t, x, y in [("A", 0.08, 0.55), ("B", 0.05, 0.08), ("C", 0.42, 0.08)]:
                ax.text(x, y, t, fontsize=10)
        elif unit == "中1_平面図形":
            import math as _m
            ang = 90
            fg = pb.get("fig")
            if isinstance(fg, tuple) and fg[0] == "sector":
                ang = fg[2]
            th = _m.radians(ang)
            wedge = patches.Wedge((0.5, 0.4), 0.35, 0, ang, fill=False, linewidth=2)
            ax.add_patch(wedge)
            ax.plot([0.5, 0.85], [0.4, 0.4], linewidth=1.5)
            ax.plot([0.5, 0.5 + 0.35 * _m.cos(th)], [0.4, 0.4 + 0.35 * _m.sin(th)], linewidth=1.5)
            ax.text(0.48, 0.36, "O", fontsize=10)
        elif unit == "中1_空間図形":
            fg = pb.get("fig", ("cube", 0, 0))
            kind3 = fg[0] if isinstance(fg, tuple) else "cube"
            if kind3 == "sphere":
                ax.add_patch(plt.Circle((0.5, 0.5), 0.3, fill=False, linewidth=2))
                ax.plot([0.5, 0.5], [0.5, 0.8], linewidth=1, linestyle=":")
                ax.text(0.52, 0.65, "r", fontsize=10)
            elif kind3 == "pyramid":
                ax.plot([0.2, 0.8, 0.8, 0.2, 0.2], [0.2, 0.2, 0.2, 0.2, 0.2], linewidth=2)
                ax.plot([0.2, 0.5], [0.2, 0.8], linewidth=2)
                ax.plot([0.8, 0.5], [0.2, 0.8], linewidth=2)
                ax.plot([0.2, 0.8], [0.2, 0.2], linewidth=1, linestyle=":")
            else:  # cube wireframe
                s, back = 0.4, 0.12
                for ox, oy in [(0.2, 0.25), (0.2 + back, 0.25 + back)]:
                    ax.add_patch(patches.Rectangle((ox, oy), s, s, fill=False, linewidth=2,
                                                   linestyle="--" if ox > 0.2 else "-"))
                for dx, dy in [(0, 0), (s, 0), (0, s), (s, s)]:
                    ax.plot([0.2 + dx, 0.2 + back + dx], [0.25 + dy, 0.25 + back + dy],
                            linewidth=1, linestyle=":")
        elif unit == "中1_作図":
            fg = pb.get("fig", "angle")
            kind4 = fg if isinstance(fg, str) else fg[0]
            if kind4 == "segment":
                ax.plot([0.15, 0.85], [0.5, 0.5], linewidth=2)
                ax.plot([0.15], [0.5], marker="o", markersize=7)
                ax.plot([0.85], [0.5], marker="o", markersize=7)
                ax.text(0.12, 0.55, "A", fontsize=11)
                ax.text(0.87, 0.55, "B", fontsize=11)
            elif kind4 == "triangle":
                ax.plot([0.3, 0.7, 0.5, 0.3], [0.3, 0.3, 0.7, 0.3], linewidth=2)
                for t, x, y in [("A", 0.25, 0.28), ("B", 0.72, 0.28), ("C", 0.5, 0.73)]:
                    ax.text(x, y, t, fontsize=11)
            else:  # angle AOB
                ax.plot([0.3, 0.3], [0.3, 0.8], linewidth=2)
                ax.plot([0.3, 0.85], [0.3, 0.3], linewidth=2)
                ax.plot([0.3], [0.3], marker="o", markersize=7)
                for t, x, y in [("O", 0.25, 0.25), ("A", 0.27, 0.82), ("B", 0.87, 0.28)]:
                    ax.text(x, y, t, fontsize=11)
        elif unit == "中2_箱ひげ図":
            ax.set_xlim(0, 10)
            ax.axis("on")
            vals = sorted([1 + (pb["no"] * 7 + i * 13) % 80 / 10 for i in range(9)])
            ax.boxplot([vals], vert=False, widths=0.4)
        else:  # 三平方
            ax.plot([0.15, 0.75, 0.15, 0.15], [0.15, 0.15, 0.65, 0.15], linewidth=2)
            sq = patches.Rectangle((0.15, 0.15), 0.1, 0.1, fill=False, linewidth=1.5)
            ax.add_patch(sq)
            for t, x, y in [("A", 0.1, 0.7), ("B", 0.1, 0.08), ("C", 0.78, 0.08)]:
                ax.text(x, y, t, fontsize=10)
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path
    except Exception:
        return None


def make_unit_figure_step2(unit, pb):
    """2段階図の「後」(補助線あり)。相似=対応辺の印、円=中心角の線、三平方=高さの補助線。"""
    if unit not in ("中3_相似", "中3_円", "中3_三平方"):
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(3.0, 2.6), dpi=150)
        ax.set_aspect("equal")
        ax.axis("off")
        if unit == "中3_相似":
            ax.plot([0.1, 0.4, 0.1, 0.1], [0.1, 0.1, 0.5, 0.1], linewidth=2)
            ax.plot([0.55, 0.95, 0.55, 0.55], [0.1, 0.1, 0.7, 0.1], linewidth=2, linestyle="--")
            ax.plot([0.1, 0.55], [0.3, 0.4], linewidth=1.5, linestyle=":")
            ax.text(0.3, 0.38, "AUX", fontsize=9)
        elif unit == "中3_円":
            circ = plt.Circle((0.5, 0.5), 0.35, fill=False, linewidth=2)
            ax.add_patch(circ)
            ax.plot([0.5], [0.5], marker="o", markersize=4)
            ax.plot([0.5, 0.78], [0.5, 0.68], linewidth=1.5)
            ax.plot([0.5, 0.78], [0.5, 0.32], linewidth=1.5)
            ax.plot([0.5, 0.5], [0.5, 0.85], linewidth=1.5, linestyle=":", color="red")
            ax.text(0.52, 0.7, "AUX", fontsize=9, color="red")
        else:  # 三平方: 高さの補助線
            ax.plot([0.15, 0.75, 0.15, 0.15], [0.15, 0.15, 0.65, 0.15], linewidth=2)
            ax.plot([0.15, 0.45], [0.65, 0.15], linewidth=1.5, linestyle=":", color="red")
            ax.text(0.2, 0.5, "AUX", fontsize=9, color="red")
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        return path
    except Exception:
        return None


def get_params(form):
    unit = form.get("unit", "中2_連立方程式")
    if unit not in UNIT_META:
        unit = "中2_連立方程式"
    template_type = form.get("template_type", "pattern_b")
    if template_type not in ("pattern_a", "pattern_b", "pattern_c"):
        template_type = "pattern_b"
    support_tag = form.get("support_tag", "none")
    if support_tag not in SUPPORT_LABEL:
        support_tag = "none"
    try:
        count = int(form.get("count", "5"))
    except ValueError:
        count = 5
    count = max(1, min(20, count))
    difficulty = form.get("difficulty", "standard")
    if difficulty not in DIFF_LABEL:
        difficulty = "standard"
    include_answers = form.get("include_answers", "yes") == "yes"
    seed_raw = (form.get("seed") or "").strip()
    seed = int(seed_raw) if seed_raw.lstrip("-").isdigit() else None
    ren_pattern = form.get("ren_pattern", "mix")
    if ren_pattern not in REN_PATTERNS:
        ren_pattern = "mix"
    paper = form.get("paper", "A4")
    if paper not in PAPER_SIZES:
        paper = "A4"
    orient = form.get("orient", "portrait")
    if orient not in ("portrait", "landscape"):
        orient = "portrait"
    test_name = (form.get("test_name") or "").strip() or "数学学習プリント"
    fiscal_year = (form.get("fiscal_year") or "").strip() or "R8"
    proof_style = form.get("proof_style", "fill")
    space_mode = "large" if support_tag == "draw_space" else "normal"
    if support_tag == "proof_fill":
        proof_style = "fill"
    images = [f for f in (form.getlist("stock_img") if hasattr(form, "getlist") else []) if f]
    topic = (form.get("topic") or "").strip()
    print_pattern = form.get("print_pattern", "full")
    if print_pattern not in PRINT_LABEL:
        print_pattern = "full"
    variant = form.get("variant", "A")
    if variant not in ("A", "B"):
        variant = "A"
    blankify = form.get("blankify", "no") == "yes"
    font_size = form.get("font_size", "std")
    if font_size not in ("small", "std", "large"):
        font_size = "std"
    margin = form.get("margin", "std")
    if margin not in ("narrow", "std", "wide"):
        margin = "std"
    ans_width = form.get("ans_width", "std")
    if ans_width not in ("narrow", "std", "wide"):
        ans_width = "std"
    cover = form.get("cover", "no") == "yes"
    try:
        points = int(form.get("points", "0") or 0)
    except ValueError:
        points = 0
    # 連立方程式: 題材選択をパターンに反映
    if unit == "中2_連立方程式" and topic:
        _map = {"加減法・基本": "kagen_easy", "加減法・標準": "kagen_standard", "代入法": "daiyun",
                "かっこ付き": "kakko", "小数": "shosu", "分数": "bunsu"}
        if topic in _map:
            ren_pattern = _map[topic]
    return {"unit": unit, "template_type": template_type, "support_tag": support_tag,
            "count": count, "difficulty": difficulty, "include_answers": include_answers,
            "seed": seed, "ren_pattern": ren_pattern, "paper": paper, "orient": orient,
            "test_name": test_name, "fiscal_year": fiscal_year, "proof_style": proof_style,
            "space_mode": space_mode, "images": images, "topic": topic,
            "print_pattern": print_pattern, "variant": variant, "blankify": blankify,
            "font_size": font_size, "margin": margin, "ans_width": ans_width,
            "cover": cover, "points": points}


def apply_edits(problems, form):
    """プレビュー画面で編集された q/hint/answer を問題リストに反映する。
    フィールド名: q_<no>, hint_<no>, ans_<no>。空欄は元の値のまま。"""
    get = form.get if hasattr(form, "get") else lambda k, d="": d
    for pb in problems:
        no = pb["no"]
        q = get(f"q_{no}", "")
        h = get(f"hint_{no}", "")
        a = get(f"ans_{no}", "")
        if isinstance(q, str) and q.strip():
            pb["q"] = q.strip()
            pb["q_edited"] = True
            # 連立OMML用に2行形式なら eq1/eq2 も更新を試みる
            lines = [ln.strip() for ln in q.strip().splitlines() if ln.strip()]
            if len(lines) >= 2 and ("=" in lines[0] and "=" in lines[1]):
                pb["eq1"] = lines[0].rstrip("…①").rstrip("…1").strip()
                pb["eq2"] = lines[1].rstrip("…②").rstrip("…2").strip()
        if isinstance(h, str) and h.strip():
            pb["hint"] = h.strip()
        if isinstance(a, str) and a.strip():
            pb["answer"] = a.strip()
    return problems


def _gen_problems(p):
    seed = p.get("seed")
    if p.get("variant") == "B" and seed is not None:
        seed = seed + 7919  # Bパターン=別数値の類題
    kw = {"ren_pattern": p["ren_pattern"], "proof_style": p["proof_style"],
          "space_mode": p["space_mode"]}
    if p.get("topic"):
        kw["topic"] = p["topic"]
    if p.get("difficulty") == "multi":
        # 基礎＋標準を同時生成 (基礎→標準の順)
        probs1, label = generate_problems(p["unit"], p["count"], "basic", seed, **dict(kw))
        s2 = (seed + 517) if seed is not None else None
        probs2, _ = generate_problems(p["unit"], p["count"], "standard", s2, **dict(kw))
        for pb in probs1:
            pb["sec"] = "基礎"
        n = len(probs1)
        for i, pb in enumerate(probs2):
            pb["no"] = n + i + 1
            pb["sec"] = "標準"
        return probs1 + probs2, label
    return generate_problems(p["unit"], p["count"], p["difficulty"], seed, **kw)


def blankify_text(s):
    """穴埋め変換: 数字を□に置換 (エディタ機能)"""
    import re
    return re.sub(r"[0-9]+", "□", s)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", units=UNIT_META, ren_patterns=REN_PATTERNS,
                           stock_files=sorted(os.listdir(STOCK_DIR)))


@app.route("/preview", methods=["POST"])
def preview():
    p = get_params(request.form)
    problems, label = _gen_problems(p)
    p["seed"] = request.form.get("seed", "")
    return render_template("index.html", units=UNIT_META, ren_patterns=REN_PATTERNS,
                           stock_files=sorted(os.listdir(STOCK_DIR)),
                           preview=True, problems=problems, unit_label=label, **p)


def _write_question_cell(cell_q, pb, p, font_size_q):
    pq = cell_q.paragraphs[0]
    sec_pre = f"[{pb['sec']}] " if pb.get("sec") else ""
    run_no = pq.add_run(f"問{pb['no']}{sec_pre}" + (f" [{pb.get('kind','')}] " if pb.get("kind") else " "))
    set_run_font(run_no, font_size=font_size_q, is_bold=True)
    blank = p.get("blankify", False)
    if p["unit"] == "中2_連立方程式" and pb.get("eq1") and pb.get("eq2") and not pb.get("q_edited"):
        run_pre = pq.add_run("次の連立方程式を解きなさい。")
        set_run_font(run_pre, font_size=font_size_q)
        e1, e2 = pb["eq1"], pb["eq2"]
        if blank:
            e1, e2 = blankify_text(e1), blankify_text(e2)
        add_system_equations(pq, e1, e2)
    elif p["unit"] == "中1_方程式" and pb.get("eq1") and not pb.get("q_edited"):
        run_pre = pq.add_run("次の方程式を解きなさい。 ")
        set_run_font(run_pre, font_size=font_size_q)
        eq = blankify_text(pb["eq1"]) if blank else pb["eq1"]
        run_q = pq.add_run(eq)
        set_run_font(run_q, font_size=font_size_q + 1)
    else:
        disp = blankify_text(pb["q"]) if blank else pb["q"]
        for i, line in enumerate(disp.split("\n")):
            if i > 0:
                pq.add_run().add_break()
            set_run_font(pq.add_run(line), font_size=font_size_q)
    # 関数グラフを自動添付 (一次関数・比例・反比例・2次関数)
    if pb.get("func_a") is not None:
        img = make_graph_image(pb["func_a"], pb["func_b"], seed=pb["no"])
        if img:
            try:
                pr = cell_q.add_paragraph()
                pr.add_run().add_picture(img, width=Inches(1.8))
            finally:
                try:
                    os.remove(img)
                except OSError:
                    pass
    elif pb.get("graph") is not None:
        g = pb["graph"]
        img = make_prop_graph(g[0], g[1], g[2] if len(g) > 2 else 0)
        if img:
            try:
                pr = cell_q.add_paragraph()
                pr.add_run().add_picture(img, width=Inches(1.8))
            finally:
                try:
                    os.remove(img)
                except OSError:
                    pass
    # 単元図 (円・相似・箱ひげ図・三平方) を自動添付 + 2段階図 (補助線の前後)
    if pb.get("func_a") is None:
        fig = make_unit_figure(p["unit"], pb)
        if fig:
            try:
                pr = cell_q.add_paragraph()
                set_run_font(pr.add_run("【図1: 問題の図】"), font_size=9, is_bold=True)
                pr = cell_q.add_paragraph()
                pr.add_run().add_picture(fig, width=Inches(2.0))
                fig2 = make_unit_figure_step2(p["unit"], pb)
                if fig2:
                    try:
                        pr2 = cell_q.add_paragraph()
                        set_run_font(pr2.add_run("【図2: 補助線を引いた後(板書用)】"), font_size=9,
                                     is_bold=True, color=RGBColor(0xC5, 0x30, 0x30))
                        pr3 = cell_q.add_paragraph()
                        pr3.add_run().add_picture(fig2, width=Inches(2.0))
                    finally:
                        try:
                            os.remove(fig2)
                        except OSError:
                            pass
            finally:
                try:
                    os.remove(fig)
                except OSError:
                    pass
    if p["support_tag"] in ("calc_step", "visual", "draw_space", "proof_fill") and pb.get("hint"):
        p_hint = cell_q.add_paragraph()
        set_run_font(p_hint.add_run("※ " + pb["hint"]), font_size=8.5, is_italic=True,
                     color=RGBColor(0x4A, 0x55, 0x68))
    # 作図ゆったり枠
    if pb.get("wide_space") or p["support_tag"] == "draw_space":
        ps = cell_q.add_paragraph()
        set_run_font(ps.add_run("┌ 作図スペース (ゆったり・コンパス用) ──────"), font_size=9)
        for _ in range(6):
            pl = cell_q.add_paragraph()
            set_run_font(pl.add_run("│"), font_size=9, color=RGBColor(0xA0, 0xAE, 0xC0))


def _write_answer_cell(cell_a, pb, p):
    pa = cell_a.paragraphs[0]
    if p["support_tag"] == "proof_fill" and "証明" in (pb.get("kind") or ""):
        set_run_font(pa.add_run("【証明欄(穴埋め)】\n[ア]＿＿＿ [イ]＿＿＿\n"), font_size=10)
    elif p.get("print_pattern") == "full":
        # 模範解答用: 解答欄に答え入り
        set_run_font(pa.add_run("【解答】\n"), font_size=10, is_bold=True)
        set_run_font(pa.add_run(pb.get("answer", "")), font_size=11, is_bold=True)
    else:
        set_run_font(pa.add_run("【解答欄】\n"), font_size=10, is_bold=True)
    lines = 5 if p["support_tag"] in ("yutori", "draw_space") else 3
    for _ in range(lines):
        pp = cell_a.paragraphs[0].parent if False else cell_a.add_paragraph()
        set_run_font(pp.add_run("＿＿＿＿＿＿＿＿＿＿"), font_size=8,
                     color=RGBColor(0xA0, 0xAE, 0xC0))
    shade_cell(cell_a, "F8F9FA")


def build_docx(p, problems, unit_label):
    doc = docx.Document()
    apply_paper(doc, p["paper"], p["orient"], p.get("margin", "std"))
    if p.get("cover"):
        # 定期テスト表紙: テスト名・注意書き・配点チェック
        total = (p.get("points") or 0) * len(problems)
        ct = doc.add_paragraph()
        ct.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_run_font(ct.add_run(f"【{p['test_name']}】"), font_size=22, is_bold=True)
        cm = doc.add_paragraph()
        cm.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_run_font(cm.add_run(f"{unit_label}  {p['fiscal_year']}  時間50分  100点満点"),
                     font_size=12)
        cn = doc.add_paragraph()
        set_run_font(cn.add_run("【注意】答えはすべて解答欄に書くこと。途中式も採点対象。"),
                     font_size=11, is_bold=True)
        cp = doc.add_paragraph()
        chk = "○ 合計100点" if total == 100 else f"△ 合計{total}点(1問{p.get('points',0)}点×{len(problems)}問: 100点に調整してください)"
        set_run_font(cp.add_run(f"配点チェック: {chk}"), font_size=11,
                     color=None if total == 100 else RGBColor(0xC5, 0x30, 0x30))
        doc.add_page_break()
    t = doc.add_paragraph()
    set_run_font(t.add_run(f"【{p['test_name']}】{p.get('variant','A')} {unit_label} ({DIFF_LABEL[p['difficulty']]}・{len(problems)}問)"),
                 font_size=15, is_bold=True)
    m = doc.add_paragraph()
    m.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_run_font(m.add_run(f"{p['fiscal_year']}  年 組 氏名［　　　　　］  月 日  点数［  /  ］"),
                 font_size=10)
    g = doc.add_paragraph()
    set_run_font(g.add_run("≪めあて≫ 手順を確認しながら、ミスなく解こう。途中の式も必ず書こう。"),
                 font_size=10, is_bold=True)
    base_q = 11 if p["support_tag"] != "yutori" else 12.5
    font_size_q = {"small": base_q - 1.5, "std": base_q, "large": base_q + 2}.get(
        p.get("font_size", "std"), base_q)

    if p["template_type"] == "pattern_a":
        for pb in problems:
            pp = doc.add_paragraph()
            set_run_font(pp.add_run(f"問{pb['no']}  "), font_size=font_size_q, is_bold=True)
            if p["unit"] == "中2_連立方程式" and pb.get("eq1") and not pb.get("q_edited"):
                set_run_font(pp.add_run("答【　　　　】 "), font_size=font_size_q)
                add_system_equations(pp, pb["eq1"], pb["eq2"])
            else:
                set_run_font(pp.add_run(pb["q"].replace("\n", "　") + "  答【　　　　】"), font_size=font_size_q)
            if p["support_tag"] != "none" and pb.get("hint"):
                ph = doc.add_paragraph()
                set_run_font(ph.add_run("※ " + pb["hint"]), font_size=9, is_italic=True)
    elif p["template_type"] == "pattern_c":
        # 定期テスト型: 左2問領域 + 右端解答集約 (3列テーブル)
        table = doc.add_table(rows=1, cols=3)
        table.style = "Table Grid"
        table.autofit = False
        hdr = table.rows[0].cells
        for cell, txt in zip(hdr, ["問題(左)", "問題(右)", "解答欄(右端集約)"]):
            cell.text = ""
            set_run_font(cell.paragraphs[0].add_run(txt), font_size=10, is_bold=True)
            shade_cell(cell, "E2E8F0")
        # 問題を左右に振り分け、解答欄は右端に行集約
        halves = [problems[i::2] for i in range(2)]
        n = max(len(halves[0]), len(halves[1]))
        for r in range(n):
            row = table.add_row().cells
            for c in range(2):
                if r < len(halves[c]):
                    _write_question_cell(row[c], halves[c][r], p, font_size_q - 1)
                else:
                    set_run_font(row[c].paragraphs[0].add_run(""), font_size=9)
            # 右端: 対応する解答枠
            cell_ans = row[2]
            cell_ans.text = ""
            for c in range(2):
                if r < len(halves[c]):
                    pb = halves[c][r]
                    pa = cell_ans.add_paragraph()
                    set_run_font(pa.add_run(f"問{pb['no']} 答［　　　］"), font_size=10)
            shade_cell(cell_ans, "FFF7E6")
    else:
        table = doc.add_table(rows=1, cols=2)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        hdr_q, hdr_a = table.rows[0].cells
        hdr_q.text = ""; hdr_a.text = ""
        set_run_font(hdr_q.paragraphs[0].add_run("問題"), font_size=11, is_bold=True)
        set_run_font(hdr_a.paragraphs[0].add_run("解答欄・途中式"), font_size=11, is_bold=True)
        shade_cell(hdr_q, "E2E8F0"); shade_cell(hdr_a, "E2E8F0")
        # 解答欄幅の調整
        _aw = {"narrow": (4.7, 2.1), "std": (4.2, 2.6), "wide": (3.5, 3.3)}.get(
            p.get("ans_width", "std"), (4.2, 2.6))
        table.columns[0].width = Inches(_aw[0])
        table.columns[1].width = Inches(_aw[1])
        for pb in problems:
            row = table.add_row().cells
            _write_question_cell(row[0], pb, p, font_size_q)
            _write_answer_cell(row[1], pb, p)

    # 取り込み図ストックの添付
    for img_name in p["images"]:
        safe = os.path.basename(img_name)
        full = os.path.join(STOCK_DIR, safe)
        if os.path.isfile(full):
            try:
                pd = doc.add_paragraph()
                set_run_font(pd.add_run(f"【参考図: {safe}】"), font_size=10, is_bold=True)
                doc.add_picture(full, width=Inches(3.0))
            except Exception:
                pass

    # ルーブリック (観点別評価表)
    doc.add_paragraph()
    pr = doc.add_paragraph()
    set_run_font(pr.add_run("【観点別ルーブリック (配点例)】"), font_size=12, is_bold=True)
    rub = doc.add_table(rows=1, cols=4)
    rub.style = "Table Grid"
    for cell, txt in zip(rub.rows[0].cells, ["観点", "知識・技能", "思考・判断・表現", "主体的に学習に取り組む態度"]):
        cell.text = ""
        set_run_font(cell.paragraphs[0].add_run(txt), font_size=9, is_bold=True)
        shade_cell(cell, "E2E8F0")
    for row_txt in [["配点(例)", "60点: 答えの正誤", "30点: 途中式・理由の説明", "10点: 振り返りの記述"],
                    ["Aの目安", "全問正答", "根拠(定理・式変形)を説明", "学びを言葉化"],
                    ["Bの目安", "概ね正答", "一部説明可", "要点のみ記述"]]:
        row = rub.add_row().cells
        for cell, txt in zip(row, row_txt):
            cell.text = ""
            set_run_font(cell.paragraphs[0].add_run(txt), font_size=9)

    # 模範解答ページ (途中式つき。印刷パターンで空欄化=スペース保持)
    if p["include_answers"]:
        doc.add_page_break()
        pa_t = doc.add_paragraph()
        set_run_font(pa_t.add_run("【模範解答・途中式】(先生用)"), font_size=13, is_bold=True)
        blank_ans = p.get("print_pattern") in ("ans_blank", "both_blank")
        blank_expl = p.get("print_pattern") in ("expl_blank", "both_blank")
        for pb in problems:
            pp = doc.add_paragraph()
            ans_txt = "［　　　　　　］" if blank_ans else pb['answer']
            set_run_font(pp.add_run(f"問{pb['no']} 答え: {ans_txt}"), font_size=10.5, is_bold=True)
            if not blank_expl:
                for st in pb.get("steps", [])[:8]:
                    ps = doc.add_paragraph(style="List Bullet")
                    set_run_font(ps.add_run(st), font_size=9.5, color=RGBColor(0x4A, 0x55, 0x68))
            else:
                for _ in range(2):
                    ps = doc.add_paragraph()
                    set_run_font(ps.add_run("＿＿＿＿＿＿＿＿＿＿＿＿"), font_size=9,
                                 color=RGBColor(0xA0, 0xAE, 0xC0))
    foot = doc.add_paragraph()
    foot.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_run_font(foot.add_run(f"MathLessonGenerator / {p['fiscal_year']} {p['test_name']} / {unit_label}"),
                 font_size=8, is_italic=True)
    return doc


def studyaid_text(problems, unit_label):
    lines = [f"【{unit_label}】StudyAid流し込み用テキスト", ""]
    for pb in problems:
        lines.append(f"問{pb['no']} {pb['q'].replace(chr(10), ' ')}")
        lines.append(f"答 {pb['answer']}")
        lines.append("")
    lines.append("※ 数式はStudyAidの文章枠に貼り付け後、TeX/数式設定を適用してください。")
    return "\n".join(lines)


def _save_record(p, problems, label):
    try:
        from smart_tools import db_save
        db_save({"unit": p["unit"], "unit_label": label, "topic": p.get("topic", ""),
                 "difficulty": p["difficulty"], "count": p["count"], "seed": p.get("seed"),
                 "variant": p.get("variant", "A"), "test_name": p.get("test_name", ""),
                 "problems": [{"no": pb["no"], "q": pb["q"], "answer": pb.get("answer", ""),
                               "kind": pb.get("kind", "")} for pb in problems]})
    except Exception:
        pass


@app.route("/generate_word", methods=["POST"])
def generate_word():
    p = get_params(request.form)
    if p["seed"] is None:
        p["seed"] = random.randint(1, 99999)
    problems, label = _gen_problems(p)
    problems = apply_edits(problems, request.form)
    _save_record(p, problems, label)
    doc = build_docx(p, problems, label)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    fname = f"{p['fiscal_year']}_{p['test_name']}_{p['unit']}_{TEMPLATE_LABEL[p['template_type']][:4]}.docx"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.route("/studyaid", methods=["POST"])
def studyaid():
    p = get_params(request.form)
    problems, label = _gen_problems(p)
    problems = apply_edits(problems, request.form)
    txt = studyaid_text(problems, label)
    return Response(txt, mimetype="text/plain; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=StudyAid_import.txt"})


@app.route("/generate_pdf", methods=["POST"])
def generate_pdf():
    from exporters import build_pdf
    p = get_params(request.form)
    if p["seed"] is None:
        p["seed"] = random.randint(1, 99999)
    problems, label = _gen_problems(p)
    problems = apply_edits(problems, request.form)
    title = f"【{p['test_name']}】 {label} ({DIFF_LABEL[p['difficulty']]}・{len(problems)}問)"
    buf = build_pdf(title, problems, f"{p['fiscal_year']} 年 組 氏名 / 点数")
    return send_file(buf, as_attachment=True, download_name=f"{p['test_name']}_{p['unit']}.pdf",
                     mimetype="application/pdf")


@app.route("/generate_pptx", methods=["POST"])
def generate_pptx():
    from exporters import build_pptx
    p = get_params(request.form)
    if p["seed"] is None:
        p["seed"] = random.randint(1, 99999)
    problems, label = _gen_problems(p)
    problems = apply_edits(problems, request.form)
    title = f"【{p['test_name']}】 {label} ({DIFF_LABEL[p['difficulty']]})"
    buf = build_pptx(title, problems, p["test_name"])
    return send_file(buf, as_attachment=True, download_name=f"{p['test_name']}_{p['unit']}.pptx",
                     mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@app.route("/upload_fig", methods=["POST"])
def upload_fig():
    f = request.files.get("fig")
    if not f or not f.filename:
        return "ファイルがありません", 400
    safe = os.path.basename(f.filename)
    if not safe.lower().endswith((".png", ".jpg", ".jpeg")):
        return "png/jpgのみ対応です", 400
    f.save(os.path.join(STOCK_DIR, safe))
    return render_template("index.html", units=UNIT_META, ren_patterns=REN_PATTERNS,
                           stock_files=sorted(os.listdir(STOCK_DIR)), uploaded=safe)


PAGE_HEAD = """<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{t}</title>
<style>body{{font-family:sans-serif;background:#f4f7f6;margin:0;padding:20px;color:#333}}
.c{{max-width:900px;margin:0 auto;background:#fff;padding:24px;border-radius:10px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #cbd5e0;padding:8px;font-size:14px;text-align:left}}
input,select{{padding:8px;font-size:14px;margin:2px}} .btn{{background:#3182ce;color:#fff;border:none;
border-radius:6px;padding:10px 18px;font-weight:bold;cursor:pointer;margin-top:8px}}</style></head>
<body><div class="c"><h2>{t}</h2><p><a href="/">← トップに戻る</a></p>"""


@app.route("/history", methods=["GET"])
def history():
    from smart_tools import db_search
    q = request.args.get("q", "")
    recs = db_search(keyword=q)
    rows = "".join(
        f"<tr><td>{r.get('time','')}</td><td>{r.get('unit_label','')}<br>{r.get('test_name','')}"
        f" {r.get('variant','A')}・{r.get('difficulty','')}</td>"
        f"<td>seed={r.get('seed','')}</td></tr>" for r in recs[:50])
    return (PAGE_HEAD.format(t="問題DB・履歴検索") +
            f"<form method='get'>検索 <input name='q' value='{q}'>"
            "<button class='btn'>検索</button></form>"
            f"<p>{len(recs)}件</p><table><tr><th>日時</th><th>内容</th><th>再現キー</th></tr>{rows}</table>"
            "<p>再生成はトップ画面で同じ単元・seedを入力してください。</p></div></body></html>")


@app.route("/remedial", methods=["GET", "POST"])
def remedial():
    from smart_tools import guess_mistake
    body = ""
    if request.method == "POST":
        unit = request.form.get("unit", "中2_連立方程式")
        correct = request.form.get("correct", "")
        student = request.form.get("student", "")
        g = guess_mistake(unit, correct, student)
        probs, label = generate_problems(unit, 3, "basic", random.randint(1, 99999))
        items = "".join(f"<tr><td>問{pb['no']}</td><td>{pb['q'].replace(chr(10),'<br>')}</td>"
                        f"<td>{pb['answer']}</td></tr>" for pb in probs)
        body = ("<h3>誤答推定</h3><ul>" + "".join(f"<li>{x}</li>" for x in g["causes"]) +
                f"</ul><p>対策: {g['remedy']}</p><h3>補習プリント(基本3問)</h3>"
                f"<table><tr><th></th><th>問題</th><th>答</th></tr>{items}</table>")
    opts = "".join(f"<option>{k}</option>" for k in UNIT_META)
    return (PAGE_HEAD.format(t="誤答分析→補習プリント") +
            f"<form method='post'>単元 <select name='unit'>{opts}</select><br>"
            "正答 <input name='correct' size='30' placeholder='例: x = 3 , y = 2'><br>"
            "生徒解答 <input name='student' size='30' placeholder='例: x = 3'><br>"
            "<button class='btn'>診断する</button></form>" + body + "</div></body></html>")


@app.route("/scores", methods=["GET", "POST"])
def scores():
    from smart_tools import shoken
    body = ""
    if request.method == "POST":
        c, cf = request.form.get("c", "0"), request.form.get("cf", "60")
        s, sf = request.form.get("s", "0"), request.form.get("sf", "30")
        warns = []
        try:
            if not (0 <= float(c) <= float(cf)):
                warns.append(f"知識・技能の得点{c}が0〜{cf}の範囲外です")
            if not (0 <= float(s) <= float(sf)):
                warns.append(f"思考・判断・表現の得点{s}が0〜{sf}の範囲外です")
            if float(cf) + float(sf) != 100:
                warns.append(f"満点合計が{float(cf)+float(sf):.0f}点です(100点でない場合は確認)")
        except ValueError:
            warns.append("数字で入力してください")
        r = shoken(c, cf, s, sf, request.form.get("t", "B"))
        whtml = ("<ul>" + "".join(f"<li style='color:#c53030;'>⚠ {w}</li>" for w in warns) +
                 "</ul>") if warns else "<p>○ 入力チェックOK</p>"
        body = f"{whtml}<h3>所見文案</h3><p>{r['bun']}</p>"
    return (PAGE_HEAD.format(t="観点別集計→所見文案") +
            "<form method='post'>知識・技能 <input name='c' size='5'>/満点<input name='cf' size='5' value='60'><br>"
            "思考・判断・表現 <input name='s' size='5'>/満点<input name='sf' size='5' value='30'><br>"
            "主体性 <select name='t'><option>A</option><option selected>B</option><option>C</option></select><br>"
            "<button class='btn'>所見を作る</button></form>" + body + "</div></body></html>")


@app.route("/diagnosis", methods=["GET"])
def diagnosis():
    from smart_tools import prereq_chain
    unit = request.args.get("unit", "中2_連立方程式")
    chain = prereq_chain(unit)
    items = "".join(f"<li>{UNIT_META[u]['label'] if u in UNIT_META else u}</li>" for u in chain)
    opts = "".join(f"<option value='{k}'{' selected' if k == unit else ''}>{v['label']}</option>"
                   for k, v in UNIT_META.items())
    return (PAGE_HEAD.format(t="つまずき遡り診断") +
            f"<form method='get'>単元 <select name='unit' onchange='this.form.submit()'>{opts}</select></form>"
            f"<p>つまずいたらこの順に戻りましょう:</p><ol>{items or '<li>前提なし</li>'}</ol>"
            "</div></body></html>")


@app.route("/textbook", methods=["GET"])
def textbook():
    from smart_tools import textbook_search
    q = request.args.get("q", "")
    recs = textbook_search(q)
    rows = "".join(f"<tr><td>{r['pub']}</td><td>中{r['grade']}</td><td>p.{r['pages']}</td>"
                    f"<td>{UNIT_META.get(r['unit'], {}).get('label', r['unit'])}</td></tr>" for r in recs)
    return (PAGE_HEAD.format(t="教科書ページ対応") +
            f"<form method='get'>出版社・学年・ページで検索 <input name='q' value='{q}'>"
            "<button class='btn'>検索</button></form>"
            f"<table><tr><th>出版社</th><th>学年</th><th>ページ</th><th>単元</th></tr>{rows}</table>"
            "</div></body></html>")


@app.route("/tablet", methods=["POST", "GET"])
def tablet():
    if request.method == "GET":
        return (PAGE_HEAD.format(t="タブレット配信用") +
                "<p>トップ画面でプレビュー後に表示される配信用ページです。</p></div></body></html>")
    p = get_params(request.form)
    problems, label = _gen_problems(p)
    problems = apply_edits(problems, request.form)
    cards = "".join(
        f"<div style='border:1px solid #cbd5e0;border-radius:8px;padding:12px;margin:10px 0;font-size:18px'>"
        f"<b>問{pb['no']}</b><br>{pb['q'].replace(chr(10), '<br>')}</div>" for pb in problems)
    qr = ""
    try:
        import qrcode, socket
        ip = socket.gethostbyname(socket.gethostname())
        url = f"http://{ip}:5000/tablet"
        img = qrcode.make(url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        import base64
        b64 = base64.b64encode(buf.getvalue()).decode()
        qr = (f"<p>同一Wi-Fi内の端末用QR (配信用URL): {url}</p>"
              f"<img src='data:image/png;base64,{b64}' width='160'>")
    except Exception:
        qr = "<p>※ QR生成には qrcode が必要です</p>"
    return (PAGE_HEAD.format(t=f"配信: {label}") + cards + qr + "</div></body></html>")


@app.route("/library/export", methods=["GET"])
def library_export():
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if os.path.isfile(os.path.join(BASE, "problems_db.json")):
            z.write(os.path.join(BASE, "problems_db.json"), "problems_db.json")
        for fn in sorted(os.listdir(STOCK_DIR)):
            fp = os.path.join(STOCK_DIR, fn)
            if os.path.isfile(fp):
                z.write(fp, f"figure_stock/{fn}")
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="gakkyu_library.zip",
                     mimetype="application/zip")


@app.route("/library/import", methods=["POST"])
def library_import():
    import zipfile
    f = request.files.get("lib")
    if not f or not f.filename:
        return "zipファイルがありません", 400
    try:
        z = zipfile.ZipFile(f.stream)
        names = z.namelist()
        if "problems_db.json" in names:
            raw = json.loads(z.read("problems_db.json").decode("utf-8"))
            if isinstance(raw, list):
                from smart_tools import db_load, db_save
                for r in raw[:200]:
                    if isinstance(r, dict) and "unit" in r:
                        db_save({k: r.get(k) for k in
                                 ("unit", "unit_label", "topic", "difficulty", "count",
                                  "seed", "variant", "test_name", "problems") if k in r})
        n = 0
        for nm in names:
            if nm.startswith("figure_stock/") and not nm.endswith("/"):
                safe = os.path.basename(nm)
                if safe.lower().endswith((".png", ".jpg", ".jpeg")):
                    with open(os.path.join(STOCK_DIR, safe), "wb") as out:
                        out.write(z.read(nm))
                    n += 1
    except Exception as e:
        return f"取り込み失敗: {e}", 400
    return (PAGE_HEAD.format(t="学年共有ライブラリ") +
            f"<p>取り込み完了: DB統合＋図{n}件</p></div></body></html>")


@app.route("/flash", methods=["GET", "POST"])
def flash():
    if request.method == "GET":
        opts = "".join(f"<option value='{k}'>{v['label']}</option>" for k, v in UNIT_META.items())
        return (PAGE_HEAD.format(t="フラッシュ小テスト") +
                f"<form method='post'>単元 <select name='unit'>{opts}</select> "
                "問題数 <select name='count'><option>5</option><option>10</option></select> "
                "制限秒/問 <select name='sec'><option>30</option><option>60</option></select> "
                "<button class='btn'>スタート</button></form></div></body></html>")
    p = get_params(request.form)
    problems, label = _gen_problems(p)
    cards = "".join(
        f"<div class='card' data-i='{i}' style='display:none;border:2px solid #3182ce;border-radius:10px;"
        f"padding:20px;margin:10px 0;font-size:22px'>"
        f"<b>問{pb['no']}</b><br>{pb['q'].replace(chr(10), '<br>')}"
        f"<br><button class='btn' onclick='this.nextElementSibling.style.display=\"block\"'>答えを見る</button>"
        f"<div style='display:none;color:#2f855a;'><b>{pb['answer']}</b></div></div>"
        for i, pb in enumerate(problems))
    sec = request.form.get("sec", "30")
    return (PAGE_HEAD.format(t=f"フラッシュ: {label}") +
            f"<p>残り <b id='t'>{sec}</b> 秒 / <span id='pos'>1</span>/{len(problems)}問 "
            "<button class='btn' onclick='next()'>つぎへ →</button> "
            "<label><input type='checkbox' id='sh' checked>ランダム順</label></p>" +
            cards +
            f"""<script>let order=[...Array({len(problems)}).keys()];
function shuffle(a){{for(let i=a.length-1;i>0;i--){{let j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}}}}
let idx=0,left={sec},timer=null;
function show(){{document.querySelectorAll('.card').forEach(c=>c.style.display='none');
document.querySelector('.card[data-i="'+order[idx]+'"]').style.display='block';
document.getElementById('pos').textContent=idx+1;left={sec};document.getElementById('t').textContent=left;}}
function next(){{idx=(idx+1)%order.length;show();}}
if(document.getElementById('sh').checked)shuffle(order);
show();timer=setInterval(()=>{{left--;document.getElementById('t').textContent=left;
if(left<=0)next();}},1000);
document.getElementById('sh').onchange=e=>{{if(e.target.checked)shuffle(order);idx=0;show();}};
</script></div></body></html>""")


if os.environ.get("VERCEL"):
    # Vercelは全リクエストを /api/index/<path> で渡すため、同名ルートを二重登録する
    _n = [0]

    def _dup():
        for _r in list(app.url_map.iter_rules()):
            if _r.rule.startswith("/api/index"):
                continue
            _suffix = "" if _r.rule == "/" else _r.rule
            for _t in {"/api/index" + _suffix} | ({"/api/index/"} if _suffix == "" else set()):
                _n[0] += 1
                try:
                    app.add_url_rule(
                        _t, endpoint=f"{_r.endpoint}_vx{_n[0]}",
                        view_func=app.view_functions[_r.endpoint],
                        methods=sorted(_r.methods - {"HEAD", "OPTIONS"}))
                except Exception:
                    pass

    _dup()
    del _dup, _n


if __name__ == "__main__":
    print("--------------------------------------------------")
    print(" MathLessonGenerator (StudyAid超え仕様)")
    print(" ブラウザ: http://127.0.0.1:5000")
    print(" 終了は Ctrl+C (EXEはウィンドウを閉じる)")
    print("--------------------------------------------------")
    if getattr(sys, "frozen", False):
        import threading
        import webbrowser
        threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
