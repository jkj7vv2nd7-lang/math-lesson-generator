"""スライド(pptx)・PDF出力."""
import io
import os
import tempfile

FONT_JP = "UD Digi Kyokasho N-R"
FONT_JP_BOLD = "UD Digi Kyokasho N-B"
FONT_TTC_R = r"C:\Windows\Fonts\UDDigiKyokashoN-R.ttc"
FONT_TTC_B = r"C:\Windows\Fonts\UDDigiKyokashoN-B.ttc"
# 同梱フォント (Windows外・Vercel用。IPAライセンスで再配布可)
REPO_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "ipaexg.ttf")


def _style_pptx_runs(text_frame, size, bold=False):
    """スライドの全 run に教科書体 (和文フォント) とサイズを適用する。"""
    from pptx.util import Pt
    from pptx.oxml.ns import qn
    for para in text_frame.paragraphs:
        for run in para.runs:
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.name = FONT_JP
            try:
                rPr = run._r.get_or_add_rPr()
                for tag in ("a:latin", "a:ea"):
                    for old in rPr.findall(qn(tag)):
                        rPr.remove(old)
                for tag in ("a:latin", "a:ea"):
                    el = rPr.makeelement(qn(tag), {})
                    el.set("typeface", FONT_JP)
                    rPr.append(el)
            except Exception:
                pass


def build_pptx(title, problems, test_name=""):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    # タイトルスライド
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    _title_shape = slide.shapes.title or slide.shapes.add_textbox(
        Inches(0.5), Inches(0.5), Inches(12), Inches(1))
    tx = _title_shape.text_frame
    tx.text = title
    _style_pptx_runs(tx, 28, bold=True)
    # 問題スライド (1問1スライド、最大10枚)
    for pb in problems[:10]:
        s = prs.slides.add_slide(prs.slide_layouts[5])
        tb = s.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(4)).text_frame
        tb.word_wrap = True
        p = tb.paragraphs[0]
        p.text = f"問{pb['no']} [{pb.get('kind','')}]"
        for line in pb["q"].split("\n")[:6]:
            p2 = tb.add_paragraph()
            p2.text = line
        _style_pptx_runs(tb, 20)
        # 問題に指定された取り込み図 (右下に配置)
        if pb.get("user_fig_path") and os.path.isfile(pb["user_fig_path"]):
            try:
                s.shapes.add_picture(pb["user_fig_path"], Inches(9.0), Inches(4.3),
                                     width=Inches(3.5))
            except Exception:
                pass
        # ヒント
        ph = s.shapes.add_textbox(Inches(0.5), Inches(4.6), Inches(12.3), Inches(1)).text_frame
        ph.word_wrap = True
        ph.paragraphs[0].text = "ヒント: " + pb.get("hint", "")
        _style_pptx_runs(ph, 14)
        # 解答はスライド本文には出さず、発表者ノートに入れる (投影しても答えが見えない)
        try:
            notes = s.notes_slide
            notes.placeholders[1].text_frame.text = "答: " + pb.get("answer", "")
        except Exception:
            pass
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf


def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    ok_r = ok_b = False
    try:
        pdfmetrics.registerFont(TTFont("Kyokasho", FONT_TTC_R, subfontIndex=0))
        ok_r = True
    except Exception:
        pass
    try:
        pdfmetrics.registerFont(TTFont("Kyokasho-B", FONT_TTC_B, subfontIndex=0))
        ok_b = True
    except Exception:
        pass
    # Windows外では同梱のIPAexゴシックを使う (リポジトリ同梱 or pip同梱)
    if not ok_r:
        cands = [REPO_FONT]
        try:
            import japanize_matplotlib as _jm
            cands.append(os.path.join(os.path.dirname(os.path.abspath(_jm.__file__)),
                                      "fonts", "ipaexg.ttf"))
        except Exception:
            pass
        for _fp in cands:
            if os.path.isfile(_fp):
                try:
                    pdfmetrics.registerFont(TTFont("Kyokasho", _fp))
                    ok_r = True
                    break
                except Exception:
                    continue
    return ok_r


def build_pdf(title, problems, meta_line=""):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    _register_fonts()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm)
    from reportlab.pdfbase.pdfmetrics import getRegisteredFontNames
    font = "Kyokasho" if "Kyokasho" in getRegisteredFontNames() else "Helvetica"
    font_b = "Kyokasho-B" if "Kyokasho-B" in getRegisteredFontNames() else font
    st_title = ParagraphStyle("t", fontName=font_b, fontSize=16, leading=22)
    st_h = ParagraphStyle("h", fontName=font, fontSize=11, leading=16)
    st_b = ParagraphStyle("b", fontName=font, fontSize=10, leading=15)

    def esc(s):
        # 問題文などは reportlab のマークアップとして解釈されないようエスケープする
        return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    story = [Paragraph(esc(title), st_title), Paragraph(esc(meta_line), st_h), Spacer(1, 6*mm)]
    for pb in problems:
        q = esc(pb["q"]).replace("\n", "<br/>")
        story.append(Paragraph(f"問{pb['no']} [{esc(pb.get('kind',''))}]<br/>{q}", st_b))
        story.append(Spacer(1, 2*mm))
        # 問題に指定された取り込み図を、その問題の位置に差し込む
        if pb.get("user_fig_path") and os.path.isfile(pb["user_fig_path"]):
            try:
                iw, ih = ImageReader(pb["user_fig_path"]).getSize()
                w = 55 * mm
                h = w * ih / iw if iw else w
                h = min(h, 80 * mm)
                story.append(RLImage(pb["user_fig_path"], width=w, height=h))
                story.append(Spacer(1, 2*mm))
            except Exception:
                pass
        story.append(Paragraph(f"ヒント: {esc(pb.get('hint',''))}", st_b))
        story.append(Spacer(1, 4*mm))
    # ルーブリック
    story.append(Paragraph("【観点別ルーブリック】知識・技能60 / 思考・判断・表現30 / 主体性10", st_h))
    # 模範解答は問題と分け、末尾にまとめる (配布物に答えを同居させない)
    story.append(PageBreak())
    story.append(Paragraph("【模範解答】(先生用)", st_title))
    story.append(Spacer(1, 4*mm))
    for pb in problems:
        story.append(Paragraph(f"問{pb['no']} 答: {esc(pb.get('answer',''))}", st_b))
        story.append(Spacer(1, 2*mm))
    doc.build(story)
    buf.seek(0)
    return buf
