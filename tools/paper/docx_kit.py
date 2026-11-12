"""DOCX toolkit for the ISIC-2020 tutorial.

Two things it does that plain python-docx does not:

* `Kit.excerpt(path, *names)` pulls code *out of the real source files* with `ast`, so a
  listing in the document cannot drift from the code that ships in `src/`.
* four admonition styles (`tip` / `warn` / `check` / `why`) that keep a long procedural
  document readable.
"""
from __future__ import annotations

import ast
import os
import re
import textwrap

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

BODY = "Microsoft YaHei"
CODE = "Consolas"
INK = RGBColor(0x1A, 0x1A, 0x1A)
ACCENT = RGBColor(0x14, 0x3A, 0x5E)
ACCENT2 = RGBColor(0x1F, 0x5C, 0x8B)
MUTED = RGBColor(0x5A, 0x5A, 0x5A)
RED = RGBColor(0xA3, 0x2A, 0x1F)
GREEN = RGBColor(0x1E, 0x6B, 0x3A)

KINDS = {
    # label, fill, border, label colour
    "tip":   ("关键操作", "FFF4E5", "E0A040", RGBColor(0x8A, 0x55, 0x12)),
    "warn":  ("坑", "FDECEA", "D4574A", RED),
    "check": ("检查点", "EDF6EE", "5B9E6B", GREEN),
    "why":   ("为什么", "EEF2F7", "8FA8C4", ACCENT2),
}

# exact line spacing keeps mixed CJK / inline-code runs on an even baseline grid
BODY_LINE = Pt(15.6)
LIST_LINE = Pt(14.6)
BOX_LINE = Pt(15.0)


def _fonts(run, name, east=None):
    """Set latin + east-asian fonts explicitly (python-docx only sets w:ascii)."""
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(attr), name)
    rf.set(qn("w:eastAsia"), east or name)


def _shade(el, fill):
    ppr = el.get_or_add_pPr() if hasattr(el, "get_or_add_pPr") else el
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    ppr.append(shd)


def _border_left(par, color="9BB7D4", size=18):
    ppr = par._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), str(size))
    left.set(qn("w:space"), "6")
    left.set(qn("w:color"), color)
    pbdr.append(left)
    ppr.append(pbdr)


def _keep(par, with_next=True):
    par.paragraph_format.keep_with_next = with_next


def src_count(text):
    return len([ln for ln in text.split("\n") if ln.strip()])


class Kit:
    def __init__(self, title_header: str = "", page_numbers: bool = True):
        self.doc = Document()
        self.src_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
        self.tools_root = os.path.abspath(os.path.dirname(__file__))
        self._setup(title_header, page_numbers)

    # ------------------------------------------------------------------ setup
    def _setup(self, header_text, page_numbers):
        doc = self.doc
        sec = doc.sections[0]
        sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
        sec.top_margin, sec.bottom_margin = Cm(2.1), Cm(1.9)
        sec.left_margin, sec.right_margin = Cm(2.2), Cm(2.2)
        sec.header_distance, sec.footer_distance = Cm(1.1), Cm(1.0)

        n = doc.styles["Normal"]
        n.font.name = BODY
        n.font.size = Pt(10.5)
        n.font.color.rgb = INK
        n.element.rPr.rFonts.set(qn("w:eastAsia"), BODY)
        n.paragraph_format.line_spacing = BODY_LINE
        n.paragraph_format.space_after = Pt(5)

        for name, size, color, before, after in [
            ("Heading 1", 16.5, ACCENT, 22, 9),
            ("Heading 2", 12.5, ACCENT2, 14, 5),
            ("Heading 3", 11, ACCENT2, 10, 4),
        ]:
            st = doc.styles[name]
            st.font.name = BODY
            st.font.size = Pt(size)
            st.font.bold = True
            st.font.color.rgb = color
            st.element.rPr.rFonts.set(qn("w:eastAsia"), BODY)
            st.paragraph_format.space_before = Pt(before)
            st.paragraph_format.space_after = Pt(after)
            st.paragraph_format.keep_with_next = True

        if header_text:
            hp = sec.header.paragraphs[0]
            hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            r = hp.add_run(header_text)
            r.font.size = Pt(7.5)
            r.font.color.rgb = MUTED
            _fonts(r, BODY)
            ppr = hp._p.get_or_add_pPr()
            pbdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "4")
            bottom.set(qn("w:space"), "2")
            bottom.set(qn("w:color"), "C9D3DE")
            pbdr.append(bottom)
            ppr.append(pbdr)

        if page_numbers:
            fp = sec.footer.paragraphs[0]
            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = fp.add_run()
            run.font.size = Pt(8)
            run.font.color.rgb = MUTED
            fld = OxmlElement("w:fldSimple")
            fld.set(qn("w:instr"), "PAGE")
            fp._p.append(fld)

    # ------------------------------------------------------------------ text
    def h1(self, number, text):
        p = self.doc.add_heading(level=1)
        r = p.add_run(f"{number}　{text}")
        _fonts(r, BODY)
        r.font.size = Pt(16.5)
        r.font.color.rgb = ACCENT
        r.bold = True
        return p

    def h2(self, text):
        p = self.doc.add_heading(level=2)
        r = p.add_run(text)
        _fonts(r, BODY)
        r.font.size = Pt(12.5)
        r.font.color.rgb = ACCENT2
        r.bold = True
        return p

    def h3(self, text):
        p = self.doc.add_heading(level=3)
        r = p.add_run(text)
        _fonts(r, BODY)
        r.font.size = Pt(11)
        r.font.color.rgb = ACCENT2
        r.bold = True
        return p

    def p(self, text="", size=10.5, after=5, before=0, color=None, align=None, indent=None):
        par = self.doc.add_paragraph()
        self._rich(par, text, size=size)
        par.paragraph_format.space_after = Pt(after)
        par.paragraph_format.space_before = Pt(before)
        if indent is not None:
            par.paragraph_format.left_indent = Cm(indent)
        if align == "center":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if color is not None:
            for r in par.runs:
                r.font.color.rgb = color
        return par

    def _rich(self, par, text, size=10.5, color=None):
        """Inline **bold** and `code`."""
        for piece in re.split(r"(\*\*.+?\*\*|`[^`]+`)", text):
            if not piece:
                continue
            is_code = piece.startswith("`") and piece.endswith("`") and len(piece) > 2
            if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
                r = par.add_run(piece[2:-2])
                r.bold = True
                _fonts(r, BODY)
                r.font.size = Pt(size)
            elif is_code:
                r = par.add_run(piece[1:-1])
                _fonts(r, CODE, BODY)
                r.font.size = Pt(size - 1.1)
                r.font.color.rgb = RGBColor(0x22, 0x3A, 0x52)
            else:
                r = par.add_run(piece)
                _fonts(r, BODY)
                r.font.size = Pt(size)
            if color is not None:
                r.font.color.rgb = color
        return par

    def bullets(self, items, size=10.5, marker="•"):
        for it in items:
            par = self.doc.add_paragraph()
            par.paragraph_format.left_indent = Cm(0.72)
            par.paragraph_format.first_line_indent = Cm(-0.38)
            par.paragraph_format.space_after = Pt(2)
            par.paragraph_format.line_spacing = LIST_LINE
            r = par.add_run(f"{marker} ")
            _fonts(r, BODY)
            r.font.size = Pt(size)
            self._rich(par, it, size=size)

    def steps(self, items, size=10.5):
        for i, it in enumerate(items, 1):
            par = self.doc.add_paragraph()
            par.paragraph_format.left_indent = Cm(0.85)
            par.paragraph_format.first_line_indent = Cm(-0.85)
            par.paragraph_format.space_after = Pt(3)
            par.paragraph_format.line_spacing = LIST_LINE
            r = par.add_run(f"{i}. ")
            _fonts(r, BODY)
            r.bold = True
            r.font.size = Pt(size)
            r.font.color.rgb = ACCENT2
            self._rich(par, it, size=size)

    def caption(self, text, after=3):
        par = self.doc.add_paragraph()
        self._rich(par, text, size=8.6)
        for r in par.runs:
            r.bold = True
            r.font.color.rgb = MUTED
            r.font.size = Pt(8.6)
        par.paragraph_format.space_before = Pt(6)
        par.paragraph_format.space_after = Pt(after)
        _keep(par)
        return par

    # ------------------------------------------------------------------ blocks
    def code(self, text, title=None, size=8.2, max_lines=24):
        """Shaded monospace block, split into page-friendly chunks.

        A single 130-line paragraph would be one shading rectangle that a page break
        cuts through (no padding at the top of the continuation). Chunking keeps every
        visible block self-contained while still looking like one listing.
        """
        if title:
            cap = self.doc.add_paragraph()
            r = cap.add_run(title)
            _fonts(r, CODE, BODY)      # latin in Consolas, CJK in the body font
            r.font.size = Pt(8)
            r.bold = True
            r.font.color.rgb = RGBColor(0x33, 0x55, 0x77)
            cap.paragraph_format.space_before = Pt(6)
            cap.paragraph_format.space_after = Pt(1)
            _keep(cap)
        lines = text.rstrip("\n").split("\n")
        chunks = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]
        for ci, chunk in enumerate(chunks):
            par = self.doc.add_paragraph()
            pf = par.paragraph_format
            pf.space_before = Pt(1) if ci == 0 else Pt(0)
            pf.space_after = Pt(9) if ci == len(chunks) - 1 else Pt(0)
            pf.left_indent = Cm(0.3)
            pf.line_spacing = 1.0
            _shade(par._p, "F5F7FA")
            _border_left(par, "B9C8D8", 16)
            run = par.add_run()
            for i, line in enumerate(chunk):
                if i:
                    run.add_break()
                run.add_text(line)
            _fonts(run, CODE, BODY)
            run.font.size = Pt(size)
        return None

    def admonition(self, kind, label_extra, text):
        label, fill, border, lcolor = KINDS[kind]
        par = self.doc.add_paragraph()
        pf = par.paragraph_format
        pf.space_before = Pt(4)
        pf.space_after = Pt(9)
        pf.left_indent = Cm(0.15)
        pf.right_indent = Cm(0.1)
        pf.line_spacing = BOX_LINE
        _shade(par._p, fill)
        _border_left(par, border, 26)
        r = par.add_run(f"{label}{(' · ' + label_extra) if label_extra else ''}　")
        r.bold = True
        _fonts(r, BODY)
        r.font.size = Pt(9.8)
        r.font.color.rgb = lcolor
        self._rich(par, text, size=10)
        return par

    def tip(self, text, extra=""):
        return self.admonition("tip", extra, text)

    def warn(self, text, extra=""):
        return self.admonition("warn", extra, text)

    def check(self, text, extra=""):
        return self.admonition("check", extra, text)

    def why(self, text, extra=""):
        return self.admonition("why", extra, text)

    def table(self, header, rows, widths=None, size=8.6, caption=None, zebra=True,
              header_fill="DCE6F2", align_center=False, bold_first_col=False):
        if caption:
            self.caption(caption, after=2)
        t = self.doc.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        tbl_pr = t._tbl.tblPr
        borders = OxmlElement("w:tblBorders")
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "A9B7C6")
            borders.append(el)
        tbl_pr.append(borders)
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tbl_pr.append(layout)
        if widths:
            tbl_w = OxmlElement("w:tblW")
            tbl_w.set(qn("w:type"), "dxa")
            tbl_w.set(qn("w:w"), str(int(sum(widths) * 567)))
            tbl_pr.append(tbl_w)

        hdr = t.rows[0].cells
        for i, txt in enumerate(header):
            hdr[i].text = ""
            par = hdr[i].paragraphs[0]
            par.paragraph_format.space_after = Pt(1)
            par.paragraph_format.line_spacing = 1.05
            r = par.add_run(str(txt))
            r.bold = True
            _fonts(r, BODY)
            r.font.size = Pt(size)
            r.font.color.rgb = ACCENT
            tcpr = hdr[i]._tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), header_fill)
            tcpr.append(shd)
        tr_pr = t.rows[0]._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:tblHeader"))     # repeat header across pages

        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for ci, txt in enumerate(row):
                cells[ci].text = ""
                par = cells[ci].paragraphs[0]
                par.paragraph_format.space_after = Pt(1)
                par.paragraph_format.line_spacing = 1.1
                self._rich(par, str(txt), size=size)
                for r in par.runs:
                    r.font.size = Pt(size)
                    if bold_first_col and ci == 0:
                        r.bold = True
                if align_center:
                    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if zebra and ri % 2 == 1:
                    tcpr = cells[ci]._tc.get_or_add_tcPr()
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear")
                    shd.set(qn("w:color"), "auto")
                    shd.set(qn("w:fill"), "F6F8FB")
                    tcpr.append(shd)
            tr_pr = t.rows[-1]._tr.get_or_add_trPr()
            tr_pr.append(OxmlElement("w:cantSplit"))  # keep one row on one page

        if widths:
            for i, w in enumerate(widths):
                t.columns[i].width = Cm(w)
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)
        gap = self.doc.add_paragraph()
        gap.paragraph_format.space_after = Pt(1)
        gap.paragraph_format.line_spacing = 0.6
        return t

    def image(self, path, width_cm, caption=None):
        if caption:
            self.caption(caption, after=2)
        self.doc.add_picture(path, width=Cm(width_cm))
        self.doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ------------------------------------------------------------------ source
    def _src_path(self, rel):
        for cand in (os.path.join(self.src_root, rel),
                     os.path.join(self.tools_root, rel),
                     os.path.abspath(os.path.join(self.tools_root, "..", rel))):
            if os.path.exists(cand):
                return cand
        raise FileNotFoundError(rel)

    def excerpt(self, rel, *names, title=None, docstring=False, size=8.2):
        """Embed source of one or more functions / classes / methods, verbatim."""
        path = self._src_path(rel)
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        tree = ast.parse(src)
        lines = src.split("\n")
        blocks = []
        for name in names:
            node = self._find(tree, name)
            if node is None:
                raise KeyError(f"{name} not found in {rel}")
            start = node.lineno - 1
            end = node.end_lineno
            if (not docstring) and node.body and isinstance(node.body[0], ast.Expr) \
                    and isinstance(getattr(node.body[0], "value", None), ast.Constant) \
                    and isinstance(node.body[0].value.value, str):
                start = node.body[0].end_lineno
                if start >= end:
                    start = node.lineno - 1
            blocks.append("\n".join(lines[start:end]))
        body = textwrap.dedent("\n\n".join(b.rstrip() for b in blocks))
        head = title or f"{rel} · {' / '.join(names)}"
        n = body.count("\n") + 1
        self.code(body, title=f"{head}    （{n} 行，取自 {rel}）", size=size)

    @staticmethod
    def _find(tree, qualname):
        node = tree
        for part in qualname.split("."):
            found = None
            for child in getattr(node, "body", []):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                        and child.name == part:
                    found = child
                    break
            if found is None:
                return None
            node = found
        return node

    def file_lines(self, rel):
        with open(self._src_path(rel), "r", encoding="utf-8") as fh:
            return src_count(fh.read())
