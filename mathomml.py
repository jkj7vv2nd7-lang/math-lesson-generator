"""数式表記 → Word数式 (OMML) 変換器 & プレビュー用 TeX 変換.

アプリが生成する数式表記 (例: "x/2 + y/3 = 7/6", "√(3²+4²)=5", "弧 8/3πcm")
を解析し、分数 (m:f)・根号 (m:rad)・上付き (m:sSup)・括弧 (m:d) の
構造化された OMML に変換する。日本語の文章が混ざる文字列は、
数式らしい部分だけを切り分けて (split_segments) 変換できる。

対応パターン (生成器の実測に基づく):
  - 分数: 12/5, x/2, 7/6, a/x など「主項 / 主項」
  - 根号: √25, √x, √(3²+4²)
  - 累乗: x², cm³, r³ (ユニコード上付き) と x^2 形式
  - 連立: 呼び出し側で eqArr に組み込む (math_nodes_xml を使う)
  - ±, π, ×, ÷, ∠, △, ℓ, °, 比例 (a:b の ':' は文章側に残る)
"""
import re

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_SUP_MAP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
            "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
_UNITS = ("cm", "mm", "km", "kg")
_BINOPS = set("+-=×÷<>→")


# ---------------------------------------------------------------- tokenizer
def _tokenize(s):
    """数式チャンク文字列をトークン列にする。"""
    toks = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == " ":
            i += 1
            continue
        if c in "0123456789" or (c == "." and i + 1 < n and s[i + 1] in "0123456789"):
            j = i
            while j < n and (s[j] in "0123456789" or s[j] == "."):
                j += 1
            toks.append(("num", s[i:j]))
            i = j
            continue
        if c == "√":
            toks.append(("sqrt", c))
            i += 1
            continue
        if c in _SUP_MAP:
            j, d = i, ""
            while j < n and s[j] in _SUP_MAP:
                d += _SUP_MAP[s[j]]
                j += 1
            toks.append(("sup", d))
            i = j
            continue
        if c == "^":
            j, d = i + 1, ""
            while j < n and s[j].isdigit():
                d += s[j]
                j += 1
            if d:
                toks.append(("sup", d))
                i = j
                continue
            toks.append(("op", c))
            i += 1
            continue
        if c == "(":
            toks.append(("lp", c))
            i += 1
            continue
        if c == ")":
            toks.append(("rp", c))
            i += 1
            continue
        if c == "/":
            toks.append(("slash", c))
            i += 1
            continue
        if c.isascii() and c.isalpha():
            unit = None
            for u in _UNITS:
                if s.startswith(u, i):
                    after = s[i + len(u)] if i + len(u) < n else ""
                    if not (after.isascii() and after.isalpha()):
                        unit = u
                        break
            if unit:
                toks.append(("unit", unit))
                i += len(unit)
                continue
            toks.append(("var", c))
            i += 1
            continue
        toks.append(("op", c))
        i += 1
    return toks


# ------------------------------------------------------------------- parser
class _Parser:
    def __init__(self, toks):
        self.toks = toks
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def next(self):
        t = self.peek()
        self.i += 1
        return t


def _wrap(node):
    return node if isinstance(node, list) else [node]


def _parse_seq(p, stop_rp=False):
    items = []
    while True:
        k, v = p.peek()
        if k is None:
            break
        if k == "rp":
            if stop_rp:
                break
            p.next()
            items.append(("txt", ")"))
            continue
        if k == "op" and v != "±":
            p.next()
            items.append(("op", v))
            continue
        items.append(_parse_factor(p))
    return items


def _parse_factor(p):
    base = _parse_primary(p)
    k, _ = p.peek()
    if k == "slash":
        p.next()
        den = _parse_primary(p)
        base = ("frac", _wrap(base), _wrap(den))
        k, _ = p.peek()
    if k == "sup":
        _, d = p.next()
        base = ("sup", _wrap(base), d)
    return base


def _parse_primary(p):
    k, v = p.next()
    if k == "num":
        return ("txt", v)
    if k == "var":
        return ("var", v)
    if k == "unit":
        return ("unit", v)
    if k == "sqrt":
        k2, _ = p.peek()
        if k2 == "lp":
            p.next()
            body = _parse_seq(p, stop_rp=True)
            if p.peek()[0] == "rp":
                p.next()
            return ("rad", body)
        inner = _parse_primary(p)
        k3, d = p.peek()
        if k3 == "sup":
            p.next()
            inner = ("sup", _wrap(inner), d)
        return ("rad", _wrap(inner))
    if k == "lp":
        body = _parse_seq(p, stop_rp=True)
        if p.peek()[0] == "rp":
            p.next()
        return ("group", body)
    # 'op' (例: ±) や想定外はそのままテキストとして扱う
    return ("txt", v or "")


def parse_math(text):
    """数式チャンク文字列を AST (ノードのリスト) にする。"""
    return _parse_seq(_Parser(_tokenize(text)))


# ------------------------------------------------------------- OMML builder
def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _run_xml(text, size=None, bold=False, color=None, sty=None):
    parts = ["<m:r>"]
    if sty:
        parts.append(f'<m:rPr><m:sty m:val="{sty}"/></m:rPr>')
    wr = ['<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/>']
    if bold:
        wr.append("<w:b/>")
    if size:
        wr.append(f'<w:sz w:val="{int(round(size * 2))}"/>')
    if color:
        wr.append(f'<w:color w:val="{color}"/>')
    wr.append("</w:rPr>")
    parts.append("".join(wr))
    parts.append(f'<m:t xml:space="preserve">{_esc(text)}</m:t></m:r>')
    return "".join(parts)


def _op_text(nodes, idx):
    """二項演算子の前後スペースを決める (先頭・演算子の直後は詰める)。"""
    op = nodes[idx][1]
    if op in _BINOPS:
        if idx == 0 or nodes[idx - 1][0] == "op":
            return op
        return f" {op} "
    return op


def _nodes_xml(nodes, size=None, bold=False, color=None):
    kw = {"size": size, "bold": bold, "color": color}
    out = []
    for idx, node in enumerate(nodes):
        t = node[0]
        if t == "txt":
            out.append(_run_xml(node[1], **kw))
        elif t == "var":
            out.append(_run_xml(node[1], **kw))
        elif t == "unit":
            out.append(_run_xml(node[1], sty="p", **kw))
        elif t == "op":
            out.append(_run_xml(_op_text(nodes, idx), **kw))
        elif t == "frac":
            out.append("<m:f><m:num>" + _nodes_xml(node[1], **kw) +
                       "</m:num><m:den>" + _nodes_xml(node[2], **kw) +
                       "</m:den></m:f>")
        elif t == "rad":
            out.append('<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>' +
                       _nodes_xml(node[1], **kw) + "</m:e></m:rad>")
        elif t == "sup":
            out.append("<m:sSup><m:e>" + _nodes_xml(node[1], **kw) +
                       "</m:e><m:sup>" + _run_xml(node[2], **kw) + "</m:sup></m:sSup>")
        elif t == "group":
            out.append("<m:d><m:e>" + _nodes_xml(node[1], **kw) + "</m:e></m:d>")
    return "".join(out)


def math_nodes_xml(text, size=None, bold=False, color=None):
    """数式文字列 → oMath の中身 (m:e 等に埋め込む用) の XML。"""
    return _nodes_xml(parse_math(text), size=size, bold=bold, color=color)


def omath_xml(text, size=None, bold=False, color=None):
    """数式文字列 → <m:oMath> 要素まるごとの XML (段落へ追加する用)。"""
    return (f'<m:oMath xmlns:m="{M_NS}" xmlns:w="{W_NS}">'
            + math_nodes_xml(text, size=size, bold=bold, color=color)
            + "</m:oMath>")


# ------------------------------------------------------- 文章と数式の切り分け
_MATH_CHARS = set("0123456789.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  "+-=×÷*/^_()<>:,±√πℓ△∠°□→…%'")
_MATH_CHARS |= set(_SUP_MAP.keys())
_STRONG = set("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ√π±ℓ")
_STRONG |= set(_SUP_MAP.keys())


def split_segments(text):
    """文字列を [(is_math, segment), ...] に切り分ける。

    日本語などの文章部分は is_math=False、数式らしい部分は True。
    スペースは両隣が数式のときだけ数式側に含める。"""
    if not text:
        return []
    cls = []
    for ch in text:
        if ch == " ":
            cls.append("S")
        elif ch in _MATH_CHARS:
            cls.append("M")
        else:
            cls.append("T")
    # スペースの帰属を決める (前後の非スペース文字が両方 M なら M)
    for i, c in enumerate(cls):
        if c != "S":
            continue
        prev = next((cls[j] for j in range(i - 1, -1, -1) if cls[j] != "S"), "T")
        nxt = next((cls[j] for j in range(i + 1, len(cls)) if cls[j] != "S"), "T")
        cls[i] = "M" if (prev == "M" and nxt == "M") else "T"
    segs = []
    cur, cur_cls = "", None
    for ch, c in zip(text, cls):
        if c != cur_cls:
            if cur:
                segs.append((cur_cls == "M", cur))
            cur, cur_cls = ch, c
        else:
            cur += ch
    if cur:
        segs.append((cur_cls == "M", cur))
    # 数式らしい要素 (数字・文字・√など) を含まない M セグメントは文章に戻す
    out = []
    for is_math, seg in segs:
        if is_math and not any(ch in _STRONG for ch in seg):
            is_math = False
        if out and out[-1][0] == is_math:
            out[-1] = (is_math, out[-1][1] + seg)
        else:
            out.append((is_math, seg))
    return out


# ---------------------------------------------------------------- TeX 変換
_TEX_ESCAPE = {"#": r"\#", "$": r"\$", "%": r"\%", "&": r"\&",
               "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "\\": r"\backslash "}
_TEX_SYMBOLS = {"π": r"\pi", "×": r"\times", "÷": r"\div", "±": r"\pm",
                "ℓ": r"\ell", "△": r"\triangle", "∠": r"\angle",
                "→": r"\rightarrow", "…": r"\dots", "□": r"\square", "°": r"{}^\circ"}


def _nodes_tex(nodes):
    out = []
    for idx, node in enumerate(nodes):
        t = node[0]
        if t in ("txt", "var", "unit"):
            out.append("".join(_TEX_ESCAPE.get(ch, ch) for ch in node[1]))
        elif t == "op":
            op = node[1]
            if op in _TEX_SYMBOLS:
                out.append(_TEX_SYMBOLS[op])
            elif op in _BINOPS:
                out.append(_op_text(nodes, idx).replace("-", "-"))
            else:
                out.append(_TEX_ESCAPE.get(op, op))
        elif t == "frac":
            out.append(r"\frac{" + _nodes_tex(node[1]) + "}{" + _nodes_tex(node[2]) + "}")
        elif t == "rad":
            out.append(r"\sqrt{" + _nodes_tex(node[1]) + "}")
        elif t == "sup":
            out.append(_nodes_tex(node[1]) + "^{" + node[2] + "}")
        elif t == "group":
            out.append(r"\left(" + _nodes_tex(node[1]) + r"\right)")
    return "".join(out)


import re as _re

_TEX_CMD = _re.compile(r"(\\(?:pi|times|div|pm|ell|triangle|angle|rightarrow|dots|square))(?=[a-zA-Z])")


def math_to_tex(text):
    """数式チャンク文字列 → TeX 文字列。"""
    # π などの記号は txt ノードにも現れるため後処理でも置換する
    tex = _nodes_tex(parse_math(text))
    for k, v in _TEX_SYMBOLS.items():
        tex = tex.replace(k, v)
    # \pi の直後に英字が続くと別コマンドと誤認されるためスペースを入れる
    tex = _TEX_CMD.sub(r"\1 ", tex)
    return tex


def _html_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def mathjax_html(text):
    """文章混じりの文字列 → MathJax 用 HTML (数式部分だけ \\(...\\) で囲む)。"""
    parts = []
    for is_math, seg in split_segments(text):
        if is_math:
            parts.append("\\(" + math_to_tex(seg) + "\\)")
        else:
            parts.append(_html_escape(seg))
    return "".join(parts)
