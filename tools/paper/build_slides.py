"""Build the 10-minute presentation (16:9) and the A0 poster, both .pptx.

    python tools/build_slides.py --out ../SDSC6018_Presentation.pptx --poster ../SDSC6018_Poster.pptx
"""
from __future__ import annotations

import argparse
import os

from PIL import Image as PILImage
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSETS = os.path.join(ROOT, "report_assets")
PANEL = os.path.join(ROOT, "figures", "panel.png")

GROUP = "Group 8"
AUTHORS = "Ke Liu · Zeyu Fu · Dong Wang · Kai Liu"
NAVY = RGBColor(0x14, 0x3A, 0x5E)
BLUE = RGBColor(0x1F, 0x5C, 0x8B)
GREY = RGBColor(0x55, 0x55, 0x55)
LIGHT = RGBColor(0xF2, 0xF5, 0xF9)
RED = RGBColor(0xA3, 0x2A, 0x1F)
GREEN = RGBColor(0x1E, 0x6B, 0x3A)
SANS = "Segoe UI"
SERIF = "Georgia"


def txbox(slide, l, t, w, h, wrap=True):
    box = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    return box


def set_text(par, text, size, bold=False, color=NAVY, font=SANS, italic=False):
    par.text = ""
    run = par.add_run()
    run.text = text
    f = run.font
    f.name = font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    return par


def add_par(tf, text, size, bold=False, color=NAVY, font=SANS, space_after=6,
            bullet=False, level=0, italic=False, align=PP_ALIGN.LEFT):
    par = tf.paragraphs[0] if (len(tf.paragraphs) == 1 and not tf.paragraphs[0].text
                               and not tf.paragraphs[0].runs) else tf.add_paragraph()
    set_text(par, ("•  " if bullet else "") + text, size, bold, color, font, italic)
    par.level = level
    par.space_after = Pt(space_after)
    par.alignment = align
    return par


def title_slide(prs, title, subtitle):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(3.6))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    box = txbox(s, 0.8, 0.9, 11.7, 1.9)
    add_par(box.text_frame, title, 30, True, RGBColor(0xFF, 0xFF, 0xFF), SERIF)
    add_par(box.text_frame, subtitle, 15, False, RGBColor(0xD8, 0xE2, 0xEE), SANS, space_after=0)
    box2 = txbox(s, 0.8, 4.1, 11.7, 1.2)
    add_par(box2.text_frame, "SDSC 6018 · Final Presentation · Fall 2026/27", 13, True, BLUE)
    add_par(box2.text_frame, f"{GROUP}   ·   {AUTHORS}", 13, False, GREY)
    add_par(box2.text_frame, "Department of Data Science, City University of Hong Kong", 11, False, GREY)
    return s


def content_slide(prs, title, kicker=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bar = s.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = BLUE
    bar.line.fill.background()
    box = txbox(s, 0.55, 0.32, 12.2, 0.9)
    add_par(box.text_frame, title, 22, True, NAVY, SERIF)
    if kicker:
        add_par(box.text_frame, kicker, 11.5, False, GREY, SANS, italic=True, space_after=0)
    return s


def footer(slide, n):
    box = txbox(slide, 11.9, 7.05, 1.0, 0.3)
    add_par(box.text_frame, str(n), 10, False, GREY, SANS, align=PP_ALIGN.RIGHT)
    box2 = txbox(slide, 0.55, 7.05, 8.0, 0.3)
    add_par(box2.text_frame, "Class-balanced losses do not buy sensitivity · ISIC 2020", 9, False, GREY)


def bullets(slide, items, l=0.6, t=1.45, w=6.1, h=5.2, size=15):
    box = txbox(slide, l, t, w, h)
    tf = box.text_frame
    for i, it in enumerate(items):
        if isinstance(it, tuple):
            text, level, bold = it
            add_par(tf, text, size - (1.5 if level else 0), bold=bold, bullet=(level == 0),
                    level=level, space_after=8)
        else:
            add_par(tf, it, size, bullet=True, space_after=9)
    return box


def picture(slide, path, l, t, w=None, h=None):
    if w:
        return slide.shapes.add_picture(path, Inches(l), Inches(t), width=Inches(w))
    return slide.shapes.add_picture(path, Inches(l), Inches(t), height=Inches(h))



def picture_fit(slide, path, l, t, max_w, max_h):
    """Place an image inside a box, preserving aspect ratio."""
    with PILImage.open(path) as im:
        iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    left = l + (max_w - w) / 2
    top = t + (max_h - h) / 2
    return slide.shapes.add_picture(path, Inches(left), Inches(top),
                                    width=Inches(w), height=Inches(h))
def table(slide, header, rows, l, t, widths, size=11, header_fill=NAVY):
    shape = slide.shapes.add_table(len(rows) + 1, len(header), Inches(l), Inches(t),
                                   Inches(sum(widths)), Inches(0.32 * (len(rows) + 1)))
    tbl = shape.table
    for i, wd in enumerate(widths):
        tbl.columns[i].width = Inches(wd)
    for j, txt in enumerate(header):
        cell = tbl.cell(0, j)
        cell.text = ""
        p = cell.text_frame.paragraphs[0]
        set_text(p, str(txt), size, True, RGBColor(0xFF, 0xFF, 0xFF))
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_fill
        cell.margin_left = cell.margin_right = Inches(0.05)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, row in enumerate(rows, 1):
        for j, txt in enumerate(row):
            cell = tbl.cell(i, j)
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            bold = (i == 1)
            set_text(p, str(txt), size, bold, NAVY if not bold else BLUE)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF) if i % 2 else LIGHT
            cell.margin_left = cell.margin_right = Inches(0.05)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    return tbl


def callout(slide, text, l, t, w, h, fill=LIGHT, color=NAVY, size=14):
    box = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    box.fill.solid()
    box.fill.fore_color.rgb = fill
    box.line.color.rgb = RGBColor(0xC8, 0xD3, 0xDE)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.12)
    tf.margin_top = tf.margin_bottom = Inches(0.08)
    add_par(tf, text, size, True, color)
    return box


# ---------------------------------------------------------------------- slides
def build_slides(out):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    n = 0

    title_slide(prs, "Class-balanced losses do not buy sensitivity",
                "A calibration-first, patient-disjoint benchmark on ISIC 2020")

    # 1 motivation
    n += 1
    s = content_slide(prs, "A triage model is a threshold, not an AUROC",
                      "Why the leaderboard metric answers a different question")
    bullets(s, [
        "Dermoscopy triage: at a fixed false-positive budget, how many melanomas surface?",
        "ISIC 2020 is 1.76% malignant (584 / 33,126). Saying \u201cbenign\u201d is 98.2% accurate and useless.",
        "The usual remedy is a class-balanced objective \u2014 inverse-prevalence weighting or focal loss.",
        "These are judged by AUROC, which is invariant to any monotone rescaling of the scores.",
        "So AUROC cannot show the side effect that decides whether a threshold is usable: the probability scale.",
    ], w=6.4)
    callout(s, "AUROC: 0.86\u20130.89 for four different objectives.\n"
               "ECE: 0.0045 \u2192 0.135.\nSame ranking. Unusable probabilities.",
            7.4, 1.45, 5.2, 1.45, fill=RGBColor(0xFD, 0xEC, 0xEA), color=RED, size=15)
    picture_fit(s, PANEL, 7.5, 3.1, 5.2, 3.9)
    footer(s, n)

    # 2 dataset / leakage
    n += 1
    s = content_slide(prs, "Patient, not image, is the sampling unit",
                      "Why an image-level split flatters every metric")
    bullets(s, [
        "33,126 images from 2,056 patients (16 per patient, heavy tail).",
        "Same lesion, same patient: an image-level split leaks identity into test.",
        "We freeze a 70/10/20 patient-disjoint split once (SHA-256 in the repo).",
        "Two-stage balancer: greedy placement + swap repair, so prevalence stays at 1.76%.",
    ], w=6.2)
    table(s, ["Split", "Images", "Patients", "Melanomas", "Prevalence"],
          [["Train", "23,188", "1,437", "409", "1.76%"],
           ["Validation", "3,313", "208", "58", "1.75%"],
           ["Test", "6,625", "411", "117", "1.77%"]],
          0.6, 3.6, [1.3, 1.2, 1.2, 1.2, 1.2], size=12)
    callout(s, "117 test melanomas \u2192 every comparison needs paired intervals, not two headline numbers.",
            0.6, 5.6, 6.0, 1.1, size=13)
    picture_fit(s, os.path.join(ASSETS, "fig_errors.png"), 7.0, 1.6, 5.8, 5.2)
    footer(s, n)

    # 3 protocol
    n += 1
    s = content_slide(prs, "Protocol: freeze everything that could flatter us",
                      "One split, one threshold, paired intervals, three views of calibration")
    bullets(s, [
        ("Threshold: 80th percentile of validation negatives, frozen, then applied to test.", 0, False),
        ("Report the specificity actually achieved \u2014 it drifts.", 1, False),
        ("Calibration: adaptive ECE + ECE on true melanomas + calibration slope b.", 0, False),
        ("b < 1 over-confident, b > 1 under-confident; one number cannot say both.", 1, False),
        ("Uncertainty: 2,000 patient-level bootstrap resamples, same patients for every model.", 0, False),
        ("Paired differences, because two wide intervals can overlap while the difference is real.", 1, False),
        ("Post-hoc: one temperature fitted on validation, monotone \u2192 AUROC/Sens cannot move.", 0, False),
    ], w=6.6, size=14)
    callout(s, "Five runs, one variable each:\nBCE \u00b7 inv-prev BCE \u00b7 focal \u00b7 ResNet-50 \u00b7 BCE+metadata",
            7.6, 1.5, 5.1, 1.5, size=14)
    picture_fit(s, os.path.join(ASSETS, "fig_training.png"), 7.4, 3.3, 5.3, 3.7)
    footer(s, n)

    # 4 headline result
    n += 1
    s = content_slide(prs, "Plain BCE wins on every axis we measured",
                      "Test set, threshold frozen on validation, 95% patient-level bootstrap")
    table(s, ["Model", "AUROC", "AUPRC", "ECE", "slope", "Sens@Spec80"],
          [["B3 + BCE", "0.892", "0.140", "0.0045", "0.80", "0.803 [.720,.884]"],
           ["B3 + inv-prev BCE", "0.860", "0.091", "0.0339", "0.43", "0.726 [.640,.812]"],
           ["B3 + focal", "0.876", "0.169", "0.1355", "1.85", "0.812 [.735,.891]"],
           ["R50 + BCE", "0.855", "0.104", "0.0055", "0.65", "0.761 [.664,.849]"],
           ["B3 + BCE + meta", "0.889", "0.218", "0.0059", "0.79", "0.752 [.663,.841]"]],
          0.55, 1.5, [1.85, 1.05, 1.05, 1.0, 0.85, 2.0], size=12)
    bullets(s, [
        "Balancing does not raise sensitivity: focal +0.009 [\u22120.063, +0.088], inv-prev \u22120.077 [\u22120.170, +0.019].",
        "Inverse-prevalence also loses ranking: AUROC \u22120.033 (p = 0.032), AUPRC \u22120.049 (p = 0.006).",
        "Metadata buys AUPRC (+0.078, p < 0.001) and pAUC, not AUROC or sensitivity.",
    ], l=0.55, t=3.55, w=12.2, size=14)
    footer(s, n)

    # 5 calibration
    n += 1
    s = content_slide(prs, "Two ways to be miscalibrated",
                      "The direction matters \u2014 and it decides whether a scalar can help")
    picture_fit(s, os.path.join(ASSETS, "fig_calibration.png"), 0.4, 1.5, 7.8, 5.3)
    bullets(s, [
        "Inv-prev BCE: slope 0.43, median p = 0.121 for melanomas \u2014 over-confident.",
        "Focal: slope 1.85, median p = 0.391 \u2014 under-confident, threshold moves 0.017 \u2192 0.250.",
        "One temperature: focal ECE \u221279% (0.136 \u2192 0.028); inv-prev unchanged (0.034 \u2192 0.035).",
        "Focal's damage is a scale problem; inv-prev's is structural.",
    ], l=8.3, t=1.6, w=4.5, size=13)
    callout(s, "AUROC, AUPRC and Sens@Spec80 are identical before and after scaling \u2014 to four decimals.",
            8.3, 5.6, 4.5, 1.1, size=12)
    footer(s, n)

    # 6 decision curve
    n += 1
    s = content_slide(prs, "In the operating range, focal is worse than doing nothing",
                      "Decision-curve net benefit, refer-to-dermatology")
    bullets(s, [
        "At p\u209c = 0.02: BCE 0.0101, BCE+meta 0.0094, inv-prev 0.0095, focal \u22120.0007 (treat-all \u22120.0024).",
        "BCE+meta is best for p\u209c \u2265 0.05 \u2014 the region a triage rule would actually use.",
        "Inv-prev crosses below zero at p\u209c \u2248 0.10: no threshold where it helps.",
        "The ordering by net benefit is not the ordering by AUROC.",
    ], w=6.1, size=14)
    picture_fit(s, os.path.join(ASSETS, "fig_decision.png"), 7.0, 1.5, 5.8, 5.2)
    footer(s, n)

    # 7 error analysis
    n += 1
    s = content_slide(prs, "The misses are confident, not borderline",
                      "Where the reference model fails, and whether a threshold could rescue it")
    picture_fit(s, os.path.join(ASSETS, "fig_errors.png"), 0.4, 1.6, 8.3, 5.2)
    bullets(s, [
        "23 / 117 melanomas missed (19.7%).",
        "Missed: median p = 0.008 (0.003\u20130.015); detected: 0.084 (0.025\u20130.268).",
        "Extremities 30\u201332% vs torso 12%.",
        "Age pattern (\u22640: 33%, >70: 0%) is 117-positive noise \u2014 reported because it was pre-specified.",
    ], l=8.9, t=1.6, w=3.9, size=12.5)
    footer(s, n)

    # 8 takeaways
    n += 1
    s = content_slide(prs, "Takeaways", "What we would tell the next team")
    bullets(s, [
        "On this dataset, class balancing bought neither sensitivity nor calibration; it cost both.",
        "AUROC-only reporting hides it. Report Sens@Spec80 with a frozen threshold plus two calibration views.",
        "Calibration is not one number: whole-sample ECE is 0.0045 for a model whose melanoma-conditional ECE is 0.90.",
        "Threshold portability is a metric: focal's frozen threshold loses 3 points of specificity on test.",
        "Next: 384 px, 5-fold patient-level CV, and a segmentation-based look at the extremity misses.",
    ], w=7.4, size=15)
    callout(s, "Reproducible: frozen manifest + SHA-256, 5 run directories, predictions as CSV,\n"
               "every table and figure regenerated on CPU without retraining.",
            8.1, 2.2, 4.7, 1.6, size=12.5)
    callout(s, "3.4 GPU-hours on one 6 GB laptop GPU.", 8.1, 4.2, 4.7, 0.8, size=13)
    footer(s, n)

    # 9 questions
    n += 1
    s = content_slide(prs, "Thank you \u2014 questions", None)
    bullets(s, [
        "Group: " + GROUP + "  \u00b7  " + AUTHORS,
        "Code and frozen split shared with teaching staff.",
        "Backup slides: per-epoch curves, run configuration, full metric table.",
    ], w=10.5, size=15)
    footer(s, n)

    prs.save(out)
    return out


# ---------------------------------------------------------------------- poster
def build_poster(out):
    """A0 portrait poster on a fixed row grid.

    The layout is explicit rows/columns rather than stacked panels: on a poster the panels
    must line up, and estimating text height to place the next panel is what makes that go
    wrong. Each row has a fixed band, and figures are fitted into their band with
    `picture_fit`, so nothing can overrun.
    """
    prs = Presentation()
    W, H = 33.1, 46.8
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    s = prs.slides.add_slide(prs.slide_layouts[6])

    M = 1.15                     # page margin
    GAP = 0.55
    COL = (W - 2 * M - 2 * GAP) / 3     # column width ~9.75

    band = s.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(4.9))
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.line.fill.background()

    box = txbox(s, M, 0.55, W - 2 * M, 2.0)
    add_par(box.text_frame, "Class-balanced losses do not buy sensitivity", 58, True,
            RGBColor(0xFF, 0xFF, 0xFF), SERIF)
    add_par(box.text_frame, "A calibration-first, patient-disjoint benchmark on ISIC 2020",
            30, False, RGBColor(0xD8, 0xE2, 0xEE))

    box = txbox(s, M, 3.2, W - 2 * M, 1.4)
    add_par(box.text_frame, f"{GROUP}   ·   {AUTHORS}", 25, True, RGBColor(0xFF, 0xFF, 0xFF))
    add_par(box.text_frame, "Department of Data Science, City University of Hong Kong  ·  SDSC 6018",
            18, False, RGBColor(0xC8, 0xD3, 0xDE))

    def panel(x, y, w, h, title, body_size=20, gap_after_title=1.05):
        box = s.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        box.line.color.rgb = RGBColor(0xD5, 0xDD, 0xE5)
        tb = txbox(s, x + 0.28, y + 0.26, w - 0.56, 0.75)
        add_par(tb.text_frame, title, 23, True, BLUE)
        return txbox(s, x + 0.28, y + gap_after_title, w - 0.56, h - gap_after_title - 0.2).text_frame

    def fill(tf, items, size=20, after=13, bullet=True):
        for it in items:
            add_par(tf, it, size, bullet=bullet, space_after=after, color=RGBColor(0x22, 0x22, 0x22))

    # ---------------- row 1
    r1, h1 = 5.5, 7.8
    tf = panel(M, r1, COL, h1, "The question")
    fill(tf, [
        "Triage is a threshold question: at a fixed false-positive budget, how many melanomas surface?",
        "ISIC 2020: 33,126 images, 2,056 patients, 584 malignant (1.76%). \u201cAlways benign\u201d is 98.2% accurate.",
        "Balanced objectives are argued to buy sensitivity \u2014 and are judged by AUROC.",
        "AUROC is blind to the probability scale, which is exactly what a threshold consumes.",
    ])

    x2 = M + COL + GAP
    tf = panel(x2, r1, COL, h1, "Protocol")
    fill(tf, [
        "One frozen 70/10/20 patient-disjoint split (SHA-256 released).",
        "Threshold = 80th percentile of validation negatives, frozen, applied to test.",
        "2,000 patient-level paired bootstrap resamples; threshold fixed inside resamples.",
        "Calibration in three views: adaptive ECE, ECE on true melanomas, calibration slope.",
        "Five runs, one variable each: BCE / inv-prev BCE / focal / ResNet-50 / BCE+metadata.",
        "Split sizes: 23,188 / 3,313 / 6,625 images \u00b7 1,437 / 208 / 411 patients \u00b7 409 / 58 / 117 melanomas.",
    ])

    x3 = x2 + COL + GAP
    tf = panel(x3, r1, COL, h1 + 1.2, "Plain BCE is the strongest model")
    add_par(tf, "Test set \u00b7 6,625 images \u00b7 117 melanomas \u00b7 95% patient-level bootstrap",
            15, italic=True, color=GREY, space_after=8)
    table(s, ["Model", "AUROC", "AUPRC", "ECE", "slope", "Sens@Spec80"],
          [["B3 + BCE", "0.892", "0.140", "0.0045", "0.80", "0.803"],
           ["B3 + inv-prev", "0.860", "0.091", "0.0339", "0.43", "0.726"],
           ["B3 + focal", "0.876", "0.169", "0.1355", "1.85", "0.812"],
           ["R50 + BCE", "0.855", "0.104", "0.0055", "0.65", "0.761"],
           ["B3 + BCE + meta", "0.889", "0.218", "0.0059", "0.79", "0.752"]],
          x3 + 0.28, r1 + 2.35, [2.75, 1.45, 1.45, 1.35, 1.05, 1.75], size=13)



    # ---------------- row 2: calibration
    r2 = 13.9
    picture_fit(s, os.path.join(ASSETS, "fig_calibration.png"), M, r2, 19.6, 6.8)
    tf = panel(M + 20.1, r2, W - 2 * M - 20.1, 6.8, "Two ways to be miscalibrated")
    fill(tf, [
        "Inv-prev BCE: slope 0.43, median p = 0.121 on melanomas \u2014 over-confident.",
        "Focal: slope 1.85, median p = 0.391 \u2014 under-confident; its threshold moves 0.017 \u2192 0.250.",
        "One temperature fitted on validation removes 79% of focal's ECE (0.136 \u2192 0.028) and none of inv-prev's (0.034 \u2192 0.035).",
        "Focal's damage is a scale problem; inv-prev's is structural.",
    ], size=18, after=10)

    # ---------------- row 3: errors
    r3 = 21.4
    tf = panel(M, r3, 11.3, 7.0, "The misses are confident")
    fill(tf, [
        "23 of 117 melanomas missed (19.7%) at the frozen threshold.",
        "Missed lesions: median p = 0.008 (0.003\u20130.015). Detected: 0.084 (0.025\u20130.268).",
        "They are not rescued by moving the threshold \u2014 a confidence failure, not a tuning problem.",
        "Extremities 30\u201332% miss rate vs torso 12%.",
        "Age pattern (\u22640: 33%, >70: 0/24) is 117-positive noise; reported because it was pre-specified.",
    ], size=17.5, after=8)
    picture_fit(s, os.path.join(ASSETS, "fig_errors.png"), M + 11.9, r3, W - 2 * M - 11.9, 7.2)

    # ---------------- row 4: why / decision / limitations
    r4 = 29.4
    tf = panel(M, r4, COL, 5.9, "Why balancing fails here")
    fill(tf, [
        "Under patient-disjoint evaluation BCE already reaches 0.803 sensitivity; the remaining errors are ambiguous lesions, not a neglected minority.",
        "Up-weighting 409 positives against 22,779 negatives injects gradient noise and inflates the logit scale: ranking and calibration both pay.",
        "Focal keeps the model uncertain on almost everything \u2014 a calibration defect even when the ranking holds.",
    ], size=18, after=9)

    tf = panel(x2, r4, COL, 5.9, "Decision curve")
    fill(tf, [
        "At p\u209c = 0.02: net benefit 0.0101 (BCE), 0.0094 (BCE+meta), 0.0095 (inv-prev), \u22120.0007 (focal), against \u22120.0024 for refer-all.",
        "Focal is worse than not using a model across the plausible range.",
        "BCE+meta leads for p\u209c \u2265 0.05 \u2014 the region a triage rule would use.",
    ], size=18, after=9)

    tf = panel(x3, r4, COL, 5.9, "Limitations")
    fill(tf, [
        "One split, one seed: intervals capture sampling noise, not run-to-run variance.",
        "Test is a re-split of public training data \u2014 not leaderboard-comparable.",
        "58 validation melanomas: the frozen threshold and temperature carry estimation noise.",
        "256 px, B3/R50 only; no Grad-CAM \u2014 we can say where the model fails, not why.",
    ], size=17.5, after=8)

    # ---------------- row 5: takeaway
    r5 = 35.9
    tf = panel(M, r5, W - 2 * M - 10.6, 4.9, "Takeaway")
    fill(tf, [
        "On this dataset, class balancing bought neither sensitivity nor calibration \u2014 it cost both, and AUROC-only reporting hides it.",
        "Report Sens@Spec80 with a frozen threshold, plus class-conditional ECE and the calibration slope; whole-sample ECE cannot see the failure.",
        "Threshold portability is itself a metric: focal's frozen threshold loses three points of specificity on test.",
    ], size=21, after=12)
    tf = panel(W - M - 10.6, r5, 10.6, 4.9, "Cost")
    fill(tf, [
        "5 training runs \u00b7 12 epochs each",
        "3.4 GPU-hours on one 6 GB RTX 2060 Max-Q",
        "Every table and figure regenerates on CPU from saved predictions",
    ], size=16, after=10)

    foot = txbox(s, M, H - 1.55, W - 2 * M, 0.9)
    add_par(foot.text_frame,
            "Frozen manifest + SHA-256, five run directories and per-image predictions released with the code.",
            15, False, GREY)

    prs.save(out)
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "SDSC6018_Presentation.pptx"))
    ap.add_argument("--poster", default=os.path.join(ROOT, "SDSC6018_Poster.pptx"))
    args = ap.parse_args()
    print("saved", build_slides(args.out))
    print("saved", build_poster(args.poster))
