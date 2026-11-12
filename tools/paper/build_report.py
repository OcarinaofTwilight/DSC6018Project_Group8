"""Build the final report DOCX (12 pt Times, single-spaced, 10 pages).

    python tools/build_report.py --out ../SDSC6018_Final_Report.docx
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSETS = os.path.join(ROOT, "report_assets")
SERIF = "Times New Roman"
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x44, 0x44, 0x44)

GROUP = "Group 8"


# ----------------------------------------------------------------- helpers
def set_font(run, name=SERIF, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def para(doc, text="", size=12, bold=False, italic=False, align=None, before=0, after=4,
         spacing=1.0, indent=None, color=None, keep_next=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = spacing
    if indent is not None:
        pf.first_line_indent = Inches(indent)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if keep_next:
        pf.keep_with_next = True
    if text:
        r = p.add_run(text)
        set_font(r, size=size, bold=bold, italic=italic, color=color)
    return p


def rich_para(doc, pieces, size=12, align="justify", before=0, after=4, indent=None):
    """pieces = [(text, bold, italic), ...]"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = 1.0
    if indent is not None:
        pf.first_line_indent = Inches(indent)
    if align == "justify":
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for text, bold, italic in pieces:
        r = p.add_run(text)
        set_font(r, size=size, bold=bold, italic=italic)
    return p


def heading(doc, text, level=1):
    if level == 1:
        p = para(doc, text, size=13, bold=True, before=10, after=4, keep_next=True)
    else:
        p = para(doc, text, size=12, bold=True, italic=True, before=8, after=3, keep_next=True)
    return p


def bullets(doc, items, size=12):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        pf = p.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(2)
        pf.line_spacing = 1.0
        pf.left_indent = Inches(0.3)
        pf.first_line_indent = Inches(-0.18)
        r = p.add_run(it)
        set_font(r, size=size)


def caption(doc, text, size=9.5, after=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(text)
    set_font(r, size=size, color=MUTED)


def table(doc, header, rows, widths, size=9, first_col_bold=False, spans_note=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tbl_pr = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom", "insideH"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "999999")
        borders.append(el)
    for edge in ("left", "right", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tbl_pr.append(borders)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)

    hdr = t.rows[0].cells
    for i, txt in enumerate(header):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(str(txt))
        set_font(r, size=size, bold=True)
        tcpr = hdr[i]._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "EDEDED")
        tcpr.append(shd)

    for row in rows:
        cells = t.add_row().cells
        for i, txt in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(str(txt))
            set_font(r, size=size, bold=(first_col_bold and i == 0))
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Inches(w)
    for i, w in enumerate(widths):
        t.columns[i].width = Inches(w)
    return t


def figure(doc, path, width_in, cap=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(path, width=Inches(width_in))
    if cap:
        caption(doc, cap)


# ----------------------------------------------------------------- document
def build(out_path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.top_margin = Inches(0.85)
    sec.bottom_margin = Inches(0.85)
    sec.left_margin = Inches(0.9)
    sec.right_margin = Inches(0.9)

    st = doc.styles["Normal"]
    st.font.name = SERIF
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), SERIF)
    st.paragraph_format.line_spacing = 1.0
    st.paragraph_format.space_after = Pt(4)

    # footer page number
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    set_font(run, size=9, color=MUTED)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    fp._p.append(fld)

    # ---------------- title block
    para(doc, "SDSC 6018 — Final Project Report · Fall 2026/27", size=10, italic=True,
         align="center", after=2, color=MUTED)
    para(doc, GROUP + "  ·  Ke Liu (60909031) · Zeyu Fu (59938860) · "
              "Dong Wang (60934248) · Kai Liu (60291367)",
         size=10, align="center", after=10, color=MUTED)
    para(doc, "Class-Balanced Losses Do Not Buy Sensitivity: A Calibration-First, "
              "Patient-Disjoint Benchmark on ISIC 2020",
         size=16, bold=True, align="center", after=4)
    para(doc, "Department of Data Science, City University of Hong Kong", size=10.5,
         italic=True, align="center", after=10, color=MUTED)

    # ---------------- abstract
    heading(doc, "Abstract", 1)
    rich_para(doc, [(
        "Melanoma triage models are usually judged by AUROC, but AUROC says nothing about "
        "whether a predicted probability can be acted on. We re-examine the ISIC 2020 "
        "dermoscopy benchmark under a strictly patient-disjoint 70/10/20 split of the 33,126 "
        "public training images (2,056 patients, 1.76% malignant) and ask whether the "
        "class-balanced objectives that are supposed to recover sensitivity actually do so, "
        "and at what cost to calibration. Five EfficientNet-B3/ResNet-50 runs differ only in "
        "the objective (plain BCE, inverse-prevalence BCE, focal loss) or in the addition of "
        "three clinical metadata fields. Endpoints are sensitivity at 80% specificity with the "
        "threshold frozen on validation, class-conditional calibration error, the calibration "
        "slope, and patient-level paired bootstrap intervals (2,000 resamples). Plain BCE is the "
        "strongest model on every axis we measured: AUROC 0.892 [0.865, 0.917], AUPRC 0.140, "
        "sensitivity 0.803 at 80% specificity, and ECE 0.0045. Inverse-prevalence BCE loses "
        "ranking (AUROC \u22120.033, p = 0.032) and is badly over-confident (slope 0.43), while "
        "focal loss is badly under-confident (slope 1.85, ECE 0.136). A single temperature "
        "recovers 79% of focal's calibration error but nothing of inverse-prevalence BCE's, so "
        "the two objectives damage calibration in structurally different ways. Adding age, sex "
        "and anatomical site raises AUPRC by 0.078 (p < 0.001) without changing AUROC. On this "
        "dataset the honest conclusion is negative and useful: class balancing bought neither "
        "sensitivity nor calibration, and only a calibration-first protocol makes that visible."
    , False, False)], size=10.5, after=6)

    # ---------------- 1 introduction
    heading(doc, "1. Introduction", 1)
    para(doc,
         "Dermoscopy triage asks a narrow question: at a fixed false-positive budget, how many "
         "melanomas does the model surface? ISIC 2020 was built for exactly this question and "
         "deliberately ships patient identifiers, because several images of the same lesion, and "
         "several lesions of the same patient, make image-level splitting optimistic "
         "[1, 2]. The dataset is also extreme: 584 of 33,126 training images are malignant "
         "(1.76%), so a model that predicts \u201cbenign\u201d everywhere is 98.2% accurate and "
         "useless.", align="justify")
    para(doc,
         "The standard response to that imbalance is a class-balanced objective \u2014 "
         "inverse-prevalence weighting or focal loss \u2014 on the argument that up-weighting "
         "the minority class buys sensitivity [4, 5]. The argument is usually evaluated with "
         "AUROC, which is invariant to any monotone rescaling of the scores and therefore cannot "
         "show the side effect that matters: reweighting changes the probability scale, not just "
         "the ranking. A model that must be operated at a threshold needs both properties, and "
         "only a calibration-aware protocol reports them separately [3].", align="justify")
    para(doc,
         "We therefore ask three questions that a leaderboard cannot answer. (H1) Do balanced "
         "objectives increase sensitivity at a fixed specificity under a patient-disjoint split? "
         "(H2) Do they degrade calibration, and in which direction? (H3) Is the damage a scale "
         "problem that one scalar can undo, or a structural one?", align="justify")
    para(doc,
         "Our contribution is a protocol and an honest negative result. We freeze one "
         "patient-disjoint split, freeze the operating threshold on validation only, evaluate "
         "with patient-level paired bootstrap intervals, and report calibration in three "
         "complementary ways. Under that protocol the balanced objectives are worse than plain "
         "cross-entropy on sensitivity, ranking and calibration simultaneously; the popular "
         "narrative that balancing is a free trade of calibration for sensitivity does not "
         "survive the measurement.", align="justify")

    # ---------------- 2 related work
    heading(doc, "2. Related Work", 1)
    para(doc,
         "ISIC 2020 (SIIM-ISIC) was released with patient-level metadata precisely so that "
         "patient-disjoint evaluation becomes possible [1]; Cassidy et al. document how earlier "
         "ISIC releases allowed identity leakage between splits and recommend patient-level "
         "protocols and reporting practice [2]. Skin-lesion classifiers based on ImageNet "
         "backbones are the de facto baseline [6, 7], and HAM10000 established the "
         "dermoscopic-label conventions that ISIC inherits [8].", align="justify")
    para(doc,
         "On imbalance, focal loss down-weights easy examples [4] and class-balanced loss "
         "re-weights by effective sample number [5]; both are routinely applied to medical "
         "long-tailed problems. On calibration, Guo et al. show that modern networks are "
         "systematically over-confident and that a single temperature fitted post hoc recovers "
         "much of the gap [3] \u2014 the result our H3 is built on. Decision-curve analysis "
         "makes the missed-melanoma versus false-referral trade-off explicit [9], and the "
         "bootstrap is the standard tool for interval estimation when the sampling unit is the "
         "patient rather than the image [10].", align="justify")
    para(doc,
         "What is missing from this literature, and what we supply, is a comparison in which the "
         "loss is the only thing that changes while the split, the threshold protocol and the "
         "calibration instrumentation are held fixed.", align="justify")

    # ---------------- 3 data
    heading(doc, "3. Data and Preprocessing", 1)
    para(doc,
         "We use the 33,126 dermoscopic images and 2,056 patients of the ISIC 2020 training "
         "partition, with the binary malignant/benign target and the patient identifier. The "
         "official test labels are withheld, so all numbers below come from a patient-disjoint "
         "re-split of the public training images and are not comparable to the challenge "
         "leaderboard, which additionally permitted image-level overlap between training and "
         "evaluation.", align="justify")
    para(doc,
         "The split is generated once and frozen. A deterministic two-stage procedure assigns "
         "patients (not images) to 70/10/20: a seeded greedy pass places each patient in the "
         "split with the largest relative deficit in images and in melanomas, then a swap-repair "
         "pass moves or exchanges patients while the objective, \u03a3(\u0394images/\u03a3images)² "
         "+\u2009\u03a3(\u0394melanomas/\u03a3melanomas)², decreases. Repair matters: greedy "
         "assignment alone drifted test prevalence from 1.76% to 0.56% on a heavy-tailed "
         "synthetic replicate of the same size, because malignant labels concentrate in a few "
         "patients. The resulting manifest is validated (disjoint patient sets, no lesion "
         "spanning two splits, no duplicated image names) and released with its SHA-256 hash.",
         align="justify")

    table(doc, ["Split", "Images", "Patients", "Melanomas", "Prevalence"],
          [["Train", "23,188", "1,437", "409", "1.76%"],
           ["Validation", "3,313", "208", "58", "1.75%"],
           ["Test", "6,625", "411", "117", "1.77%"]],
          widths=[1.3, 1.2, 1.2, 1.2, 1.2], size=9)
    caption(doc, "Table 1. Patient-disjoint split of the public training partition "
                 "(seed 42). The manifest hash is reported in Appendix A.")

    para(doc,
         "Images are resized once to 256\u00d7256 offline and normalised with ImageNet "
         "statistics. Training augmentation is limited to geometric transforms (random resized "
         "crop 0.75\u20131.0, horizontal and vertical flips, rotation \u00b120\u00b0) plus mild "
         "colour jitter (0.15/0.15/0.10/0.03); dermoscopy has no canonical orientation, but "
         "colour is the strongest signal and heavy jitter would remove it. MixUp and CutMix are "
         "deliberately not used: both push predicted probabilities toward the prior and would "
         "confound the calibration measurement. Evaluation uses a resize-to-292 then centre-crop "
         "to 256 pipeline with four-fold flip test-time augmentation.", align="justify")

    # ---------------- 4 methods
    heading(doc, "4. Methods", 1)
    heading(doc, "4.1 Models and training", 2)
    para(doc,
         "Two ImageNet-pretrained backbones are used: EfficientNet-B3 (11.1 M parameters with "
         "the classifier removed, i.e. the 1536-d pooled feature) and ResNet-50 (25.6 M) [6, 7]. "
         "A small head (BatchNorm, dropout 0.3, 1536\u2192256, ReLU, dropout, 256\u21921) emits "
         "a single logit, so that every loss operates on the same quantity and the four "
         "conditions share one training and decoding path. For the metadata condition, age "
         "(scaled, plus a missing-value flag), sex (3 one-hot) and anatomical site (7 one-hot) "
         "form a 13-d vector that is projected to 64-d by an MLP and concatenated with the image "
         "features before the head. The metadata encoder (median age, category vocabulary) is "
         "fitted on the training split only and serialised with the checkpoint.", align="justify")
    para(doc,
         "All runs use AdamW (lr 3e-4, weight decay 1e-4), 5% linear warm-up followed by cosine "
         "decay, gradient clipping at 5, 12 epochs, batch size 16 and mixed precision on a "
         "single RTX 2060 Max-Q (6 GB). One epoch is 23,188 images in about 3.5 minutes. The "
         "checkpoint with the best validation AUPRC is kept; no test data is seen during "
         "training or model selection.", align="justify")

    heading(doc, "4.2 Loss conditions", 2)
    para(doc,
         "Three objectives are trained, and only the objective changes. Plain binary "
         "cross-entropy with logits is the reference. Inverse-prevalence weighting multiplies "
         "positive terms by n_neg / n_pos = 55.7, which is equivalent to declaring one missed "
         "melanoma as costly as 56 false alarms. Focal loss uses \u03b1 = 0.75 and \u03b3 = 2; "
         "the RetinaNet default \u03b1 = 0.25 would down-weight the minority class at 1.76% "
         "prevalence and is therefore inappropriate here [4]. Effective-number weighting "
         "(\u03b2 = 0.9999) is included as an intermediate point between BCE and "
         "inverse-prevalence BCE [5]; it is implemented in the code but was not trained, because "
         "the compute went to the metadata ablation instead.", align="justify")

    table(doc, ["Condition", "Objective / effective positive weight", "What it changes"],
          [["BCE", "pos_weight = 1.0", "nothing (reference)"],
           ["Inv-prev BCE", "pos_weight = 55.7", "gradient scale of every positive"],
           ["Effective number (not trained)", "pos_weight = 22.4 (\u03b2 = 0.9999)", "softer re-weighting \u2014 implemented, not run"],
           ["Focal (\u03b1=0.75, \u03b3=2)", "\u2248 3:1 on easy examples", "down-weights easy negatives"]],
          widths=[1.5, 2.9, 2.6], size=9)
    caption(doc, "Table 2. Loss conditions. Three are trained (BCE, inverse-prevalence, focal); with the ResNet-50 and metadata variants that makes five runs in total. Only the loss "
                 "differs; the data, "
                 "augmentation, schedule and checkpoint rule are identical.")

    heading(doc, "4.3 Evaluation protocol", 2)
    para(doc,
         "Endpoints. The primary endpoint is sensitivity at 80% specificity (Sens@Spec80). The "
         "threshold is the 80th percentile of the validation negative scores, selected once and "
         "then applied unchanged to test; we also report the specificity actually achieved, "
         "because it drifts. Calibration is reported three ways: adaptive (equal-frequency, 15 "
         "bins) expected calibration error; ECE restricted to true melanomas (ECE_pos, "
         "the mean shortfall of a positive's predicted probability from 1); and the calibration "
         "slope b from a logistic regression of the outcome on the predicted logit, where b < 1 "
         "means over-confident and b > 1 under-confident. AUROC, AUPRC, partial AUROC over "
         "FPR \u2264 0.2, Brier score and NLL are secondary. Whole-sample ECE alone would be "
         "misleading at 1.76% prevalence, for the reason quantified in Section 5.4.",
         align="justify")
    para(doc,
         "Uncertainty. Intervals come from 2,000 patient-level bootstrap resamples in which the "
         "same patients are drawn for every model, so that model comparisons use the paired "
         "difference rather than a comparison of two marginal intervals. The threshold is held "
         "fixed inside the resamples; re-estimating it per resample would report a slightly "
         "optimistic sensitivity. Two-sided p-values are the proportion of resamples whose "
         "paired difference falls on the other side of zero.", align="justify")
    para(doc,
         "Post-hoc calibration. A single temperature T is fitted on validation by minimising "
         "NLL and then applied to test. Temperature scaling is strictly monotone, so AUROC, "
         "AUPRC and Sens@Spec80 cannot change: any change in ECE is therefore attributable to "
         "the probability scale alone [3].", align="justify")

    heading(doc, "4.4 Training dynamics and model selection", 2)
    para(doc,
         "Validation AUROC rises quickly and plateaus after epoch 7\u20138 in every condition "
         "(Figure 2, left), while validation AUPRC stays visibly noisy because it is computed on 58 "
         "melanomas (right). We select checkpoints on AUPRC rather than AUROC: AUPRC rewards "
         "putting melanomas at the top of the ranking, which is what the triage endpoint needs. We "
         "also take the noise seriously \u2014 the spread between runs at the same epoch is "
         "comparable to the differences we report between conditions, which is why every comparison "
         "in Section 5 is a paired bootstrap interval and not two point estimates.", align="justify")
    figure(doc, os.path.join(ASSETS, "fig_training.png"), 6.3,
           "Figure 2. Validation metrics per epoch for the five runs. Left: AUROC plateaus after "
           "epoch 8 in every condition. Right: AUPRC (58 validation melanomas) is the checkpoint "
           "selection signal and correspondingly noisy; the epoch-to-epoch swing is why all "
           "comparisons are paired bootstrap intervals.")

    # ---------------- 5 results
    heading(doc, "5. Results", 1)
    heading(doc, "5.1 Plain BCE is the strongest model on every axis", 2)
    para(doc,
         "Table 3 reports the test-set results with the validation-frozen threshold. BCE "
         "achieves AUROC 0.892 [0.865, 0.917], AUPRC 0.140 [0.101, 0.202] against a prevalence "
         "baseline of 0.0177, and sensitivity 0.803 [0.720, 0.884] at 80% specificity, with "
         "calibration error 0.0045 and slope 0.80. Neither balanced objective improves on it.",
         align="justify")

    rows = [
        ["B3 + BCE", "0.892 [.865,.917]", "0.140 [.101,.202]", "0.565", "0.0161",
         "0.0045", "0.90", "0.80", "0.803 [.720,.884]", "0.816"],
        ["B3 + inv-prev BCE", "0.860 [.821,.894]", "0.091 [.066,.128]", "0.513", "0.0327",
         "0.0339", "0.74", "0.43", "0.726 [.640,.812]", "0.829"],
        ["B3 + focal", "0.876 [.847,.903]", "0.169 [.108,.255]", "0.530", "0.0469",
         "0.1355", "0.62", "1.85", "0.812 [.735,.891]", "0.771"],
        ["R50 + BCE", "0.855 [.815,.890]", "0.104 [.069,.157]", "0.497", "0.0166",
         "0.0055", "0.93", "0.65", "0.761 [.664,.849]", "0.799"],
        ["B3 + BCE + meta", "0.889 [.859,.918]", "0.218 [.157,.304]", "0.605", "0.0153",
         "0.0059", "0.84", "0.79", "0.752 [.663,.841]", "0.813"],
    ]
    table(doc, ["Model", "AUROC", "AUPRC", "pAUC", "Brier", "ECE", "ECE_pos",
                "slope", "Sens@Spec80", "spec"],
          rows, widths=[1.28, 1.02, 1.02, 0.5, 0.52, 0.52, 0.46, 0.42, 1.02, 0.42], size=8.4)
    caption(doc, "Table 3. Test-set performance (n = 6,625 images, 117 melanomas, 411 patients). "
                 "Brackets are 95% patient-level bootstrap intervals. ECE is adaptive "
                 "(15 equal-frequency bins); ECE_pos is restricted to true melanomas; "
                 "Sens@Spec80 uses the threshold selected on validation (last column: specificity "
                 "actually achieved). pAUC is over FPR \u2264 0.2.")

    figure(doc, os.path.join(ROOT, "figures", "panel.png"), 6.2,
           "Figure 1. Test-set behaviour. Top-left: reliability (quantile bins) \u2014 focal lies "
           "below the diagonal (under-confident), inverse-prevalence BCE above it "
           "(over-confident). Top-right: ROC \u2014 the curves are close, which is exactly why an "
           "AUROC-only report would have missed the difference between the four objectives. "
           "Bottom-left: sensitivity versus specificity with the 80% operating point marked. "
           "Bottom-right: decision curve; focal is below the treat-none line over its entire "
           "plausible range.")

    heading(doc, "5.2 H1: balancing does not buy sensitivity", 2)
    para(doc,
         "Paired differences against BCE are: focal +0.009 [\u22120.063, +0.088], p = 0.88; "
         "inverse-prevalence \u22120.077 [\u22120.170, +0.019], p = 0.15; ResNet-50 \u22120.043 "
         "[\u22120.121, +0.037], p = 0.35. None is positive and significant. Inverse-prevalence "
         "weighting additionally loses ranking: AUROC \u22120.033 [\u22120.065, \u22120.003], "
         "p = 0.032; AUPRC \u22120.049 [\u22120.097, \u22120.015], p = 0.006. H1 is rejected "
         "with 117 test positives; the interval for focal is wide enough that a small true gain "
         "cannot be excluded, but there is no evidence for the effect the balancing literature "
         "predicts, and the point estimates go the other way.", align="justify")

    heading(doc, "5.3 H2: both objectives damage calibration, in opposite directions", 2)
    para(doc,
         "ECE rises from 0.0045 to 0.0339 under inverse-prevalence BCE (p < 0.001) and to 0.1355 "
         "under focal loss (p < 0.001), a factor of 7.5 and 30. The direction is not the same. "
         "Inverse-prevalence BCE is over-confident (slope 0.43, median predicted probability "
         "0.121 for melanomas and 0.0035 for benign images): the 55.7\u00d7 weight pushes the "
         "whole probability scale up and the reliability curve flattens above the diagonal. "
         "Focal loss is under-confident (slope 1.85, median 0.391 for melanomas and 0.101 for "
         "benign images): down-weighting the easy 98% leaves the model hedging, and its operating "
         "threshold moves from 0.017 to 0.250. Both are visible in the reliability panel of "
         "Figure 1, and neither would be visible from AUROC.", align="justify")

    heading(doc, "5.4 H3: one scalar fixes focal, and does nothing for inverse-prevalence BCE", 2)
    para(doc,
         "A single temperature fitted on validation reduces focal's ECE by 79% (0.1355 \u2192 "
         "0.0284) and its Brier score by 55% (0.0469 \u2192 0.0213), while AUROC, AUPRC and "
         "Sens@Spec80 are unchanged to four decimals \u2014 the signature of a pure scale "
         "problem. For inverse-prevalence BCE the fitted temperature is 1.05 and the ECE does "
         "not move (0.0339 \u2192 0.0351): that model's miscalibration is structural, not a "
         "scale artefact, and cannot be repaired post hoc. The two objectives fail H3 in "
         "opposite ways, which is the most transferable finding of this study.", align="justify")

    figure(doc, os.path.join(ASSETS, "fig_calibration.png"), 6.3,
           "Figure 3. Left: ECE before and after a single validation-fitted temperature, with the "
           "fitted T under each model. Focal loss is repaired (0.136 \u2192 0.028); "
           "inverse-prevalence BCE is not (0.034 \u2192 0.035). Right: reliability in log\u2013log "
           "coordinates, where the 1.8% prevalence region lives; focal sits below the diagonal "
           "(under-confident), inverse-prevalence BCE above it (over-confident).")

    table(doc, ["Model", "T (val)", "ECE before", "ECE after", "Brier before", "Brier after",
                "slope before", "slope after"],
          [["B3 + BCE", "1.04", "0.0045", "0.0044", "0.0161", "0.0161", "0.80", "0.83"],
           ["B3 + inv-prev BCE", "1.05", "0.0339", "0.0351", "0.0327", "0.0325", "0.43", "0.45"],
           ["B3 + focal", "0.27", "0.1355", "0.0284", "0.0469", "0.0213", "1.85", "0.51"],
           ["R50 + BCE", "1.14", "0.0055", "0.0058", "0.0166", "0.0167", "0.65", "0.74"],
           ["B3 + BCE + meta", "1.02", "0.0059", "0.0064", "0.0153", "0.0154", "0.79", "0.81"]],
          widths=[1.3, 0.62, 0.85, 0.85, 0.9, 0.9, 0.8, 0.78], size=8.8)
    caption(doc, "Table 4. Post-hoc temperature scaling, fitted on validation and applied to "
                 "test. AUROC/AUPRC/Sens@Spec80 are identical before and after by construction "
                 "(monotone transform). Focal's slope overshoots past 1 to 0.51: the "
                 "NLL-optimal temperature is sharper than the calibration-optimal one on test.")

    heading(doc, "5.5 Clinical metadata improves ranking in the triage region, not discrimination",
          2)
    para(doc,
         "Adding age, sex and anatomical site leaves AUROC unchanged (0.889 vs 0.892, "
         "\u22120.003 [\u22120.022, +0.019], p = 0.76) but raises AUPRC by 0.078 [0.037, 0.128] "
         "(p < 0.001) and pAUC(FPR \u2264 0.2) from 0.565 to 0.605, while giving the best Brier "
         "score of the five models (0.0153). Sensitivity at 80% specificity is 0.051 lower "
         "[\u22120.120, +0.025], p = 0.21 \u2014 not distinguishable from noise. The pattern is "
         "consistent with the metadata sharpening the upper tail of the ranking (which is what "
         "AUPRC and pAUC reward) without changing global separability, and it does not come with "
         "a measurable calibration benefit.", align="justify")

    heading(doc, "5.6 Decision curves: focal is worse than doing nothing", 2)
    para(doc,
         "At a referral threshold of p\u209c = 0.02 the net benefit is 0.0101 for BCE, 0.0094 for "
         "BCE+meta, 0.0095 for inverse-prevalence BCE and \u22120.0007 for focal, against "
         "\u22120.0024 for referring everyone and 0 for referring nobody. BCE+meta is the best "
         "model for p\u209c \u2265 0.05 (0.0067 vs 0.0056 at 0.05; 0.0047 vs 0.0020 at 0.10), "
         "and inverse-prevalence BCE crosses below zero at p\u209c \u2248 0.10, i.e. it is worse "
         "than not using the model in exactly the range where a triage rule would operate. The "
         "relative ordering of the decision curves differs from the ordering by AUROC, which is "
         "the practical argument for reporting them together.", align="justify")

    heading(doc, "5.7 The threshold does not fully transfer", 2)
    para(doc,
         "Because the operating threshold is chosen on validation and then frozen, the specificity "
         "actually achieved on test is a diagnostic in its own right. For BCE it lands at 0.816 "
         "(target 0.80) and for ResNet-50 at 0.799, but for focal loss it falls to 0.771: the same "
         "threshold over-calls by three percentage points, which on 6,508 negatives is roughly 200 "
         "extra false referrals. That is the operational cost of the under-confidence documented in "
         "Section 5.3, and it is invisible both to AUROC and to any protocol that re-selects the "
         "threshold on test. It also complicates post-hoc calibration: rescaling probabilities "
         "moves where a frozen threshold sits in the score distribution, so threshold and "
         "temperature should be chosen together, on validation, if the two are combined.",
         align="justify")

    heading(doc, "5.8 How much of this survives the validation-to-test transfer", 2)
    para(doc,
         "Because the checkpoint and the threshold are both chosen on 58 validation melanomas, "
         "the test set is the first honest look at every model. Table 5 puts the two side by "
         "side. AUROC transfers well (|\u0394| \u2264 0.034, and the largest gap is in the "
         "model that was selected on the weakest validation AUROC), but AUPRC does not: it drops "
         "by 0.036\u20130.058 for four of the five models and the ordering between BCE and focal "
         "reverses. Sensitivity at the frozen threshold moves by at most 0.071 (inverse-"
         "prevalence BCE gains, focal loses). The practical implication is that a validation "
         "AUPRC of 0.20 is not evidence of a test AUPRC of 0.20, and that \u201cwe picked the "
         "best validation AUPRC\u201d is a weaker claim than it looks at this sample size. We "
         "report the paired test differences, not the validation ranking, for that reason.",
         align="justify")

    table(doc, ["Model", "val AUROC", "test AUROC", "\u0394AUROC", "val AUPRC", "test AUPRC",
                "\u0394AUPRC", "val Sens@80", "test Sens@80"],
          [["B3 + BCE", "0.885", "0.892", "+0.008", "0.197", "0.140", "\u22120.057", "0.793", "0.803"],
           ["B3 + inv-prev BCE", "0.825", "0.860", "+0.034", "0.109", "0.091", "\u22120.017", "0.655", "0.726"],
           ["B3 + focal", "0.882", "0.876", "\u22120.006", "0.176", "0.169", "\u22120.007", "0.845", "0.812"],
           ["R50 + BCE", "0.854", "0.855", "+0.001", "0.160", "0.104", "\u22120.056", "0.759", "0.761"],
           ["B3 + BCE + meta", "0.894", "0.889", "\u22120.005", "0.200", "0.218", "+0.018", "0.810", "0.752"]],
          widths=[1.32, 0.72, 0.74, 0.68, 0.72, 0.74, 0.68, 0.78, 0.78], size=8.2)
    caption(doc, "Table 5. Validation (3,313 images, 58 melanomas) versus test (6,625 images, "
                 "117 melanomas). The threshold is the validation one in both columns, so the "
                 "sensitivity columns differ only through the data, not through re-tuning.")

    # ---------------- 6 error analysis
    heading(doc, "6. Error Analysis", 1)
    para(doc,
         "At the validation-frozen threshold the reference BCE model misses 23 of 117 melanomas "
         "(19.7%). The misses are not borderline cases: their median predicted probability is "
         "0.008 (10th\u201390th percentile 0.003\u20130.015) against 0.084 "
         "(0.025\u20130.268) for detected melanomas, so they sit far below the operating point "
         "of 0.017 and would not be recovered by moving the threshold slightly (Figure 4, left). "
         "This is a confidence failure of the sort H3 is about, not a threshold-tuning problem.",
         align="justify")

    para(doc,
         "Misses concentrate on the extremities and appear to spare older patients. Lower and "
         "upper extremity lesions are missed at 30% (7/23) and 32% (7/22) versus 12% (6/51) on "
         "the torso and 17% (3/18) on head/neck; by age, the miss rate is 33% (7/21) under 40, "
         "20% (6/30) at 41\u201355, 24% (10/42) at 56\u201370 and 0% (0/24) above 70. With 117 "
         "positives these subgroup estimates carry Wilson intervals of roughly \u00b120 "
         "percentage points, so we read them as hypotheses rather than findings: the "
         "extremity-versus-torso contrast is the more stable of the two (26% versus 12%, "
         "n = 45 versus 51) and is consistent with lesions that are photographed at an angle or "
         "partially occluded by hair. The age pattern runs against the dermatology literature and "
         "is most likely a small-sample artefact; we report it because a subgroup analysis "
         "decided upon before looking, and reported whatever it shows, is the only version worth "
         "trusting.", align="justify")

    figure(doc, os.path.join(ASSETS, "fig_errors.png"), 6.3,
           "Figure 4. Where the errors are. Left: distribution of predicted probability for "
           "detected and missed melanomas (log scale) with the operating threshold. Middle and "
           "right: melanoma miss rate by age band and anatomical site, with 95% Wilson intervals "
           "and counts; the \u226470 group has no misses in this test split (0/24).")

    # ---------------- 7 discussion
    heading(doc, "7. Discussion", 1)
    para(doc,
         "Why did balancing fail? Under patient-disjoint splitting and a validation-frozen "
         "threshold, the BCE model already reaches 0.803 sensitivity at 80% specificity: the "
         "remaining errors are lesions whose appearance is genuinely ambiguous, not a minority "
         "class that the loss ignores. Up-weighting positives then acts mostly as noise "
         "injection into the gradient \u2014 409 positives against 22,779 negatives, each "
         "positive now worth 56 \u2014 which inflates the logit scale and costs both ranking "
         "(AUROC \u22120.033) and calibration. Focal loss behaves differently but not better: by "
         "down-weighting the easy majority it keeps the model uncertain on almost everything, "
         "which is a calibration defect even when the ranking survives.", align="justify")
    para(doc,
         "The methodological lesson is that calibration is not one number. Three models here "
         "have whole-sample ECE below 0.006 \u2014 including a model whose ECE_pos is 0.93, "
         "because at 1.76% prevalence a constant 0.017 predictor attains near-zero ECE while "
         "achieving zero sensitivity. Reporting ECE without a class-conditional companion and a "
         "slope reproduces exactly the failure that AUROC-only reporting is criticised for. "
         "Similarly, the fact that the validation threshold transfers to a test specificity of "
         "0.771 for focal (versus 0.816 for BCE) is a real operational cost that neither AUROC "
         "nor a test-side threshold would reveal.", align="justify")

    # ---------------- 8 limitations
    heading(doc, "8. Limitations", 1)
    bullets(doc, [
        "Single split, single seed. The intervals quantify sampling noise at 117 positives, not "
        "run-to-run variance; a five-fold patient-level cross-validation would be the next step.",
        "The test set is a re-split of the public training partition. Absolute numbers are "
        "therefore not comparable to challenge leaderboards, which allowed image-level overlap.",
        "The validation set contains 58 melanomas, so the frozen threshold and the temperature "
        "carry their own estimation noise; this is reflected in the intervals only partially.",
        "Only three metadata fields are used. \u201cDiagnosis\u201d and the tbp_lv_* total-body "
        "features are label-derived or unavailable in a single-dermoscopy workflow and were "
        "excluded to avoid leakage.",
        "No segmentation or Grad-CAM evidence is included; the error analysis is quantitative "
        "only, so we can say where the model fails but not why.",
        "EfficientNet-B3 at 256 px on a 6 GB laptop GPU bounds resolution and batch size; the "
        "384 px regime was not explored.",
    ])

    # ---------------- 9 conclusion
    heading(doc, "9. Conclusion", 1)
    para(doc,
         "Under a patient-disjoint split and a calibration-first protocol, class-balanced losses "
         "did not buy sensitivity on ISIC 2020; they cost ranking and calibration. Inverse-"
         "prevalence weighting is over-confident and structurally miscalibrated \u2014 no "
         "post-hoc scalar helps \u2014 while focal loss is under-confident and largely repairable "
         "by one temperature. Plain BCE with the validation-frozen threshold remains the "
         "strongest and best-calibrated model (AUROC 0.892, Sens@Spec80 0.803, ECE 0.0045), and "
         "adding three clinical fields improves AUPRC by 0.078 without changing AUROC. The open "
         "question is whether the same ordering holds at 384 px and under patient-level "
         "cross-validation; the protocol, the frozen split and the evaluation code are released "
         "so that this can be checked rather than assumed.", align="justify")

    # ---------------- references
    heading(doc, "References", 1)
    refs = [
        "Rotemberg V., Kurtansky N., Betz-Stablein B., et al. A patient-centric dataset of "
        "images and metadata for identifying melanomas using clinical context. arXiv:2008.07360, "
        "2020 (ISIC 2020 / SIIM-ISIC).",
        "Cassidy B., Kendrick C., Brodzicki A., Jaworek-Korjakowska J., Yap M.H. Analysis of the "
        "ISIC image datasets: usage, benchmarks and recommendations. Medical Image Analysis "
        "75:102305, 2022.",
        "Guo C., Pleiss G., Sun Y., Weinberger K.Q. On calibration of modern neural networks. "
        "ICML 2017.",
        "Lin T.-Y., Goyal P., Girshick R., He K., Doll\u00e1r P. Focal loss for dense object "
        "detection. ICCV 2017.",
        "Cui Y., Jia M., Lin T.-Y., Song Y., Belongie S. Class-balanced loss based on effective "
        "number of samples. CVPR 2019.",
        "He K., Zhang X., Ren S., Sun J. Deep residual learning for image recognition. CVPR 2016.",
        "Tan M., Le Q.V. EfficientNet: rethinking model scaling for convolutional neural "
        "networks. ICML 2019.",
        "Tschandl P., Rosendahl C., Kittler H. The HAM10000 dataset, a large collection of "
        "multi-source dermatoscopic images of common pigmented skin lesions. Scientific Data "
        "5:180161, 2018.",
        "Vickers A.J., Elkin E.B. Decision curve analysis: a novel method for evaluating "
        "prediction models. Medical Decision Making 26(6):565\u2013574, 2006.",
        "Efron B., Tibshirani R.J. An Introduction to the Bootstrap. Chapman & Hall, 1993.",
    ]
    for i, r in enumerate(refs, 1):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before = Pt(0)
        pf.space_after = Pt(2)
        pf.line_spacing = 1.0
        pf.left_indent = Inches(0.32)
        pf.first_line_indent = Inches(-0.32)
        run = p.add_run(f"[{i}]  {r}")
        set_font(run, size=9.5)

    # ---------------- appendix
    heading(doc, "Appendix A. Reproducibility", 1)
    para(doc,
         "All experiments use one frozen manifest (seed 42, SHA-256 recorded in "
         "manifests/split_seed42_report.json). Training, evaluation and analysis are scripted: "
         "src/split.py, src/train.py, src/evaluate.py, tools/fit_temperature.py, "
         "tools/bootstrap_frozen.py, src/report.py, src/figures.py. Predictions for every run "
         "are stored as CSV next to the checkpoint, so every table and figure in this report can "
         "be regenerated on a CPU-only machine without retraining. The code repository and the "
         "manifest are shared with the teaching staff as required; hardware was a single "
         "RTX 2060 Max-Q (6 GB), total training 3.4 GPU-hours for the five runs.", align="justify",
         size=10.5)

    heading(doc, "Appendix B. Run configuration", 1)
    table(doc, ["Run", "Backbone", "Objective", "Metadata", "Epochs", "Batch", "Best epoch",
                "Wall-clock"],
          [["b3_bce", "EfficientNet-B3", "BCE", "no", "12", "16", "11", "42 min"],
           ["b3_wbce", "EfficientNet-B3", "inv-prev BCE (55.7)", "no", "12", "16", "11", "47 min"],
           ["b3_focal", "EfficientNet-B3", "focal (\u03b1=0.75, \u03b3=2)", "no", "12", "16", "10", "44 min"],
           ["r50_bce", "ResNet-50", "BCE", "no", "12", "16", "8", "37 min"],
           ["b3_bce_meta", "EfficientNet-B3", "BCE", "yes (13-d)", "12", "16", "10", "43 min"]],
          widths=[1.15, 1.35, 1.65, 0.95, 0.6, 0.55, 0.7, 0.85], size=8.6)
    caption(doc, "Table 6. Everything that differs between the five runs. Common to all: AdamW "
                 "(lr 3e-4, weight decay 1e-4), cosine schedule with 5% warm-up, gradient clipping "
                 "at 5, 256 px input, mixed precision, checkpoint rule = best validation AUPRC.")

    doc.add_page_break()
    heading(doc, "Appendix C. Full test-set metric table", 1)
    table(doc, ["Model", "AUROC", "AUPRC", "pAUC", "Brier", "NLL", "ECE unif.", "ECE ad.",
                "ECE_pos", "slope", "thr."],
          [["B3 + BCE", "0.892", "0.140", "0.565", "0.0161", "0.0679", "0.0044", "0.0045",
            "0.898", "0.80", "0.0170"],
           ["B3 + inv-prev", "0.860", "0.091", "0.513", "0.0327", "0.1166", "0.0315", "0.0339",
            "0.737", "0.43", "0.0350"],
           ["B3 + focal", "0.876", "0.169", "0.530", "0.0469", "0.1916", "0.1355", "0.1355",
            "0.623", "1.85", "0.2495"],
           ["R50 + BCE", "0.855", "0.104", "0.497", "0.0166", "0.0710", "0.0049", "0.0055",
            "0.928", "0.65", "0.0156"],
           ["B3 + BCE + meta", "0.889", "0.218", "0.605", "0.0153", "0.0661", "0.0031", "0.0059",
            "0.841", "0.79", "0.0172"]],
          widths=[1.14, 0.62, 0.62, 0.5, 0.52, 0.5, 0.64, 0.58, 0.62, 0.46, 0.5], size=8.0)
    caption(doc, "Table 7. Every test-set number quoted in this report, with the validation-frozen "
                 "threshold (last column) used for Sens@Spec80. ECE unif./ad. are the equal-width "
                 "and equal-frequency 15-bin variants; ECE_pos is computed on true melanomas only.")

    para(doc,
         "Three columns deserve a note. NLL is reported because it is the quantity the "
         "temperature minimises, so a reader can check the fitted T independently of the ECE. "
         "ECE unif. and ECE ad. are the same estimator with equal-width and equal-frequency "
         "bins: at 1.76% prevalence the equal-width variant is dominated by the bulk of "
         "near-zero predictions and therefore flatters every model, which is why the "
         "equal-frequency variant is the one quoted in the text. thr. is the operating "
         "threshold obtained as the 80th percentile of the validation negative scores and then "
         "applied unchanged to these test predictions; it is listed so that any number in the "
         "second and third decimal place of Sens@Spec80 can be reproduced exactly.",
         align="justify", size=10.5)

    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "SDSC6018_Final_Report.docx"))
    args = ap.parse_args()
    print("saved", build(args.out))
