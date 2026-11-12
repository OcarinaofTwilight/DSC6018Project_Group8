"""Build the speaking script (DOCX) and inject presenter notes into both decks.

    python tools/build_talk_script.py \
        --docx ../SDSC6018_Talk_Script.docx \
        --slides ../SDSC6018_Presentation.pptx --poster ../SDSC6018_Poster.pptx
"""
from __future__ import annotations

import argparse
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from pptx import Presentation

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERIF = "Times New Roman"
SANS = "Microsoft YaHei"
ACCENT = RGBColor(0x14, 0x3A, 0x5E)
BLUE = RGBColor(0x1F, 0x5C, 0x8B)
GREY = RGBColor(0x55, 0x55, 0x55)
RED = RGBColor(0xA3, 0x2A, 0x1F)
GREEN = RGBColor(0x1E, 0x6B, 0x3A)

WPM = 135          # comfortable presentation pace for non-native speakers
GROUP_LINE = "Group 8 · Ke Liu · Zeyu Fu · Dong Wang · Kai Liu"


# ------------------------------------------------------------------ docx helpers
def fonts(run, name, size=None, bold=None, italic=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def para(doc, text="", font=SERIF, size=11, bold=False, italic=False, color=None,
         before=0, after=5, align=None, indent=None, spacing=1.15):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = spacing
    if indent is not None:
        pf.left_indent = Cm(indent)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if text:
        r = p.add_run(text)
        fonts(r, font, size, bold, italic, color)
    return p


def h1(doc, text):
    p = para(doc, text, font=SANS, size=16, bold=True, color=ACCENT, before=16, after=8)
    return p


def h2(doc, text):
    return para(doc, text, font=SANS, size=12, bold=True, color=BLUE, before=10, after=4)


def cue(doc, text):
    return para(doc, "▸ " + text, font=SANS, size=9.5, italic=True, color=GREY, after=6)


def script(doc, text):
    return para(doc, text, font=SERIF, size=11.5, after=8, spacing=1.25)


def bullets(doc, items, font=SANS, size=10):
    import re as _re
    for it in items:
        if not it:
            continue
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        for piece in _re.split(r"(\*\*.+?\*\*)", it):
            if not piece:
                continue
            bold = piece.startswith("**") and piece.endswith("**") and len(piece) > 4
            r = p.add_run(piece[2:-2] if bold else piece)
            fonts(r, font, size, bold=True if bold else None)


def table(doc, header, rows, widths, size=9.5, font=SANS):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, txt in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        r = p.add_run(str(txt))
        fonts(r, font, size, bold=True, color=ACCENT)
        tcpr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "DCE6F2")
        tcpr.append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, txt in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.paragraph_format.line_spacing = 1.1
            r = p.add_run(str(txt))
            fonts(r, font, size)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


# ------------------------------------------------------------------ the script
SLIDES = [
    # (slide_no, owner, seconds, title, english_script, chinese_cue, cut_line)
    (1, "Ke Liu", 20, "Title",
     "Good morning. We are Group 8: Ke Liu, Zeyu Fu, Dong Wang and Kai Liu. Our question is "
     "narrow and, I think, uncomfortable: does the class-balanced loss that everyone recommends "
     "actually make a melanoma triage model better, once you measure the thing a clinician "
     "would use?",
     "站直，不要读标题页上的字。这句只负责把注意力从屏幕拉到人身上。",
     "可删：\"and, I think, uncomfortable\""),
    (2, "Ke Liu", 65, "A triage model is a threshold, not an AUROC",
     "Here is the problem in one slide. A triage model is not a ranking, it is a threshold: at a "
     "fixed false-positive budget — say we accept twenty false alarms per hundred benign lesions "
     "— we ask how many melanomas the model surfaces. ISIC 2020 has 584 malignant images out of "
     "33,126, that is 1.76%, so a model that answers \"benign\" to everything is 98.2% accurate "
     "and completely useless. The standard remedy is a class-balanced objective: inverse-"
     "prevalence weighting, or focal loss. And the standard way to report it is AUROC. But AUROC "
     "is invariant to any monotone rescaling of the scores — square every probability and AUROC "
     "does not move — so it structurally cannot show the side effect that decides whether the "
     "threshold is usable: the probability scale. In our five runs AUROC spans 0.855 to 0.892. "
     "ECE spans 0.0045 to 0.135, a factor of thirty. Same ranking; unusable probabilities.",
     "说到 \"square every probability\" 时用手比一下；说到 0.0045 到 0.135 时指向右上红色框。",
     "可删：\"square every probability and AUROC does not move\""),
    (3, "Ke Liu", 65, "Patient, not image, is the sampling unit",
     "One design decision changes every number after this: the unit of splitting. These 33,126 "
     "images come from 2,056 patients, about sixteen images each, and the same lesion photographed "
     "twice looks extremely similar. If you split by image, the test set contains the patient's "
     "other lesion and every metric is inflated. ISIC 2020 ships patient identifiers precisely so "
     "this is avoidable, so we freeze one patient-disjoint 70/10/20 split and never touch it "
     "again; the hash is in the repository. Getting prevalence right took two passes: greedy "
     "assignment drifts, because malignant labels concentrate in a few patients, so we added a "
     "swap-repair stage. The result is 23,188, 3,313 and 6,625 images, 1.76% malignant in all "
     "three. That leaves 117 melanomas in test, which is why every comparison you will see is a "
     "paired bootstrap interval, not two headline numbers. Zeyu has the protocol and the main "
     "result.",
     "第 3 页右下是误差分解图，不要在这里讲，留给 Kai。交接句说慢一点，然后退到侧边。",
     "可删：\"the hash is in the repository\"（但组号那页仍有，无信息损失不大）"),
    (4, "Zeyu Fu", 65, "Protocol: freeze everything that could flatter us",
     "Thanks Ke. Our protocol follows one rule: freeze everything that could flatter us. The "
     "threshold is the eightieth percentile of the validation negative scores, chosen once, then "
     "applied unchanged to test — and we report the specificity actually achieved, because it "
     "drifts. For calibration we report three things, because one number cannot say it: equal-"
     "frequency ECE, ECE computed only on true melanomas, and the calibration slope. Slope below "
     "one means over-confident, above one under-confident, and you will see both. For uncertainty "
     "we resample patients, not images, two thousand times, the same patients for every model, so "
     "comparisons are paired differences; the threshold stays fixed inside each resample, because "
     "re-estimating it would report a slightly optimistic sensitivity. Finally, post-hoc "
     "temperature scaling: one scalar fitted on validation. It is monotone, so AUROC and "
     "sensitivity cannot change — which makes it a clean test of whether the damage is a scale "
     "problem or a structural one.",
     "语速放慢，这页是方法论核心。手指依次落在\"threshold / calibration / uncertainty\"三块。",
     "可删：\"because it drifts\" 之后的补充"),
    (5, "Zeyu Fu", 65, "Plain BCE wins on every axis we measured",
     "This is the main table and it is the whole story. Test set, threshold frozen on validation, "
     "intervals from the patient bootstrap. Plain BCE: AUROC 0.892, AUPRC 0.140 against a "
     "prevalence baseline of 0.018, sensitivity 0.803 at eighty percent specificity, ECE 0.0045. "
     "Inverse-prevalence BCE: AUROC 0.860, that is 0.033 lower with p equal 0.032; AUPRC 0.091; "
     "sensitivity 0.726; ECE 0.034. Focal loss: sensitivity 0.812 — plus 0.009 over BCE with an "
     "interval from minus 0.063 to plus 0.088, so indistinguishable from zero — but ECE 0.136, "
     "thirty times worse. ResNet-50 with the same loss gives 0.855 AUROC, so this is not an "
     "EfficientNet artefact. And metadata: AUPRC rises to 0.218 with p below 0.001, AUROC "
     "unchanged. So our first hypothesis, that balancing buys sensitivity, is rejected: no "
     "balanced objective beats plain cross-entropy, and one of them loses ranking as well. Dong "
     "will show what it does to calibration.",
     "这一页是全场的钱页，语速最慢。每读一个数字停半秒，让评委抬头。",
     "可删：ResNet-50 那一句（但会失去\"不是 backbone 特异\"的防线，尽量保留）"),
    (6, "Dong Wang", 80, "Two ways to be miscalibrated",
     "Thank you Zeyu. The interesting part is that both balanced losses damage calibration, but "
     "in opposite directions, and that distinction decides whether you can repair it. Left panel "
     "is ECE before and after one temperature. Right panel is reliability in log-log coordinates, "
     "because at 1.8% prevalence everything happens below 0.1. Inverse-prevalence BCE, in purple, "
     "sits above the diagonal: slope 0.43, median predicted probability 0.121 for malignant "
     "lesions and 0.0035 for benign ones. Weighting positives fifty-five times pushes the whole "
     "scale up. Focal loss, in green, sits below the diagonal: slope 1.85, median 0.391 for "
     "melanomas and 0.101 for benign. Down-weighting the easy ninety-eight percent leaves the "
     "model hedging on almost everything. Now the temperature: for focal it removes seventy-nine "
     "percent of the ECE, 0.136 to 0.028, and fifty-five percent of the Brier score, while AUROC, "
     "AUPRC and sensitivity are identical to four decimal places. For inverse-prevalence BCE the "
     "fitted temperature is 1.05 and the ECE does not move. So focal's damage is a scale problem "
     "that one scalar repairs; inverse-prevalence's is structural, and no post-hoc map of the "
     "score will fix it.",
     "这是最难的一页，两个方向容易讲混。先说颜色（紫=过度自信，绿=自信不足），再给数字。",
     "可删：\"and fifty-five percent of the Brier score\"；可删 Brier 那句但保留 T 值"),
    (7, "Dong Wang", 65, "In the operating range, focal is worse than doing nothing",
     "Last result before Kai: what this means in the clinic. The decision curve plots net benefit "
     "against the referral threshold, the probability at which you would send someone to a "
     "dermatologist. At 0.02, BCE gives 0.0101, metadata 0.0094, inverse-prevalence 0.0095, and "
     "focal minus 0.0007 — against minus 0.0024 for referring everyone and zero for referring "
     "nobody. So focal is worse than not using a model across the whole plausible range. Metadata "
     "leads from 0.05 upwards: 0.0067 against 0.0056 at 0.05, and 0.0047 against 0.0020 at 0.10, "
     "which is the region a triage rule would actually live in. Inverse-prevalence crosses below "
     "zero at about 0.10, so there is no threshold where it helps. And note that this ordering is "
     "not the ordering by AUROC. Kai will close with where the errors are.",
     "\"worse than not using a model\" 这句是全场最容易被追问的判断，说完停一秒。",
     "可删：\"and 0.0047 against 0.0020 at 0.10\"（保留 0.05 那组即可）"),
    (8, "Kai Liu", 80, "The misses are confident, not borderline",
     "Thanks Dong. Failure modes, then our conclusions. The reference BCE model misses 23 of 117 "
     "melanomas at the frozen threshold — 19.7%. The left panel is the predicted-probability "
     "distribution for detected and missed melanomas on a log scale. The misses are not "
     "borderline: median 0.008, against 0.084 for detected ones. The operating threshold is "
     "0.017, so they sit well below it, and moving the threshold slightly does not rescue them. "
     "This is a confidence failure — exactly the mechanism the temperature experiment isolated. "
     "Middle and right panels break the miss rate down. Extremities are missed at thirty to "
     "thirty-two percent against twelve percent on the torso: 45 cases against 51, so that is the "
     "more stable contrast, and it is consistent with lesions photographed at an angle or partly "
     "occluded. Age: thirty-three percent under forty, and zero of twenty-four above seventy. We "
     "do not believe that one — with 117 positives the Wilson interval is about twenty points "
     "wide — but we fixed the subgroup analysis before looking, so we report it as it came out.",
     "主动承认 >70 岁那组不可信，比被问出来好得多。语气要平，不要辩解。",
     "可删：\"45 cases against 51\"；不可删\"we fixed the analysis before looking\"（这是诚信点）"),
    (9, "Kai Liu", 60, "Takeaways",
     "Three takeaways. One: on this dataset class balancing bought neither sensitivity nor "
     "calibration — it cost both, and AUROC-only reporting hides it. Two: report sensitivity at a "
     "frozen threshold, plus class-conditional calibration and the slope, because whole-sample "
     "ECE is 0.0045 for a model whose melanoma-conditional ECE is 0.90 — at this prevalence a "
     "constant 0.017 predictor looks calibrated and has zero sensitivity. Three: threshold "
     "portability is itself a metric; focal's validation threshold loses three points of "
     "specificity on test, about two hundred extra referrals. Next: 384 pixels, five-fold "
     "patient-level cross-validation, and a segmentation-based look at the extremity misses. The "
     "code, the frozen split and per-image predictions are released, so every table regenerates "
     "on a CPU.",
     "三条 takeaway 用手指数出来，一条一句，不要连读。最后一句\"regenerates on a CPU\"是可信度背书。",
     "可删：\"about two hundred extra referrals\"；可删最后的 384 px 计划"),
    (10, "Kai Liu", 10, "Thank you",
     "Thank you — we are happy to take questions.",
     "说完站定，不要立刻回头指屏幕。等评委开口。",
     ""),
]


QA = [
    ("定位 · positioning", [
        ("这和已有工作（Cassidy 2022、挑战赛报告）有什么不同？",
         "What is new here compared with existing work on ISIC 2020?",
         "Not a new model — the proposal is explicit about that. The contribution is the "
         "protocol: one frozen patient-disjoint split, a threshold frozen on validation, three "
         "views of calibration including a class-conditional term and a slope, and paired "
         "patient-level intervals. Under that protocol the headline claim of the balancing "
         "literature does not survive, and the paper makes that visible instead of hiding it "
         "behind AUROC."),
    ]),
    ("假设类 · assumptions", [
        ("为什么把操作点定在 80% 特异度？这个数字有依据吗？",
         "Why 80% specificity?", 
         "It is a budget, not a discovery: a triage rule that refers everyone cannot be operated, "
         "and 80% keeps roughly one in five benign lesions referred. We fix it a priori so that "
         "five models are compared at the same budget, and we also report the full sensitivity-"
         "specificity curve and the decision curve, so a reader with a different budget can read "
         "the answer off Figure 1."),
        ("只跑 12 epoch、不做 early stopping，会不会对平衡损失不公平？",
         "Single hyper-parameter set — is that fair to the balanced losses?",
         "It is the fairest thing we could do with two nights of compute: identical schedule, "
         "learning rate, batch size and augmentation, chosen with BCE, and the checkpoint rule is "
         "best validation AUPRC for all five. The honest caveat is that a reweighted objective "
         "prefers a smaller learning rate — in our pilot runs inverse-prevalence BCE diverged at "
         "3e-4 and needed 1e-4 — so part of its deficit may be optimisation, not the objective. "
         "We state that in the limitations."),
        ("为什么只用一个 split、一个 seed？",
         "Why a single split and a single seed?",
         "Because the intervals we report are about sampling noise at 117 positives, not about "
         "run-to-run variance, and five runs already cost 3.4 GPU-hours on one 6 GB laptop GPU. "
         "A five-fold patient-level cross-validation is the first thing we would add, and we say "
         "so. The split is frozen and hashed, so the experiment is exactly repeatable even if it "
         "is not an ensemble."),
        ("为什么用 256 像素而不是 384？",
         "Why 256 px?",
         "6 GB of VRAM. At 384 the batch falls to 12 and the epoch time roughly doubles, for "
         "0.5–1 AUROC point in the literature. Given that our effect sizes are 0.01–0.03 AUROC "
         "and our intervals are ±0.02, resolution would have changed nothing about the "
         "conclusion."),
    ]),
    ("评估选择 · evaluation choices", [
        ("你们的 AUROC 比 leaderboard 的 0.94 低很多，是模型不行吗？",
         "Your AUROC is far below the 0.94 leaderboard — is the model weak?",
         "Neither: the numbers are not comparable. The official ISIC 2020 test labels are "
         "withheld, so our test set is a patient-disjoint re-split of the 33,126 public training "
         "images, while the leaderboard permitted image-level overlap between train and test. "
         "Multiple lesions from the same patient inflate every metric. Our sentence in the paper "
         "is: all numbers are computed on a patient-disjoint re-split and are not directly "
         "comparable to the challenge leaderboard."),
        ("既然已经报了 AUPRC，为什么还需要 ECE？",
         "Why report ECE at all if you have AUPRC?",
         "Because AUPRC is a ranking metric and a threshold is a probability. You can rank "
         "perfectly and still have a probability scale that puts the operating point at 0.25 "
         "instead of 0.017 — which is exactly what focal loss did. AUPRC cannot see that; ECE and "
         "the slope can."),
        ("ECE 对分箱数和样本量很敏感，你们怎么保证结论不是分箱造成的？",
         "ECE is sensitive to binning — is your conclusion an artefact?",
         "We report three variants: equal-width, equal-frequency fifteen bins, and ECE on true "
         "melanomas only, plus the calibration slope, which is bin-free. Focal is worst on all "
         "four. We also report Brier and NLL, which are proper scoring rules, so the ranking of "
         "models does not depend on any binning choice."),
        ("阈值是在 58 例验证集上选的，这会不会让 test 的敏感度虚高？",
         "Your threshold comes from 58 validation melanomas — is the test sensitivity optimistic?",
         "It is the honest direction: the threshold is chosen without test labels and applied "
         "unchanged, so any error is usually pessimism. The remaining issue is that we hold the "
         "threshold fixed inside the bootstrap, so the interval under-covers threshold noise. When "
         "we re-estimate the threshold in every resample the interval widens slightly — 0.838 "
         "[0.739, 0.908] versus 0.803 [0.720, 0.884] — and the comparisons do not change."),
        ("温度缩放是在 val 上拟合的，为什么不在 test 上拟合？",
         "Why fit the temperature on validation?",
         "Fitting on test is using the test labels. One scalar fitted on validation is the "
         "conservative version; fitting on test would only make focal look better, and would not "
         "change the conclusion for inverse-prevalence BCE, which is the interesting case."),
        ("温度缩放不是把阈值也一起改了吗？",
         "Doesn't temperature scaling move the threshold too?",
         "Yes, and that is a real operational subtlety: the ranking is unchanged, so AUROC and "
         "sensitivity at a quantile-defined threshold are identical, but a threshold frozen in "
         "probability space shifts. If you deploy post-hoc calibration, you must re-derive the "
         "threshold after it — on validation, with the temperature already applied. We say this "
         "in the paper."),
    ]),
    ("真实场景 · realistic conditions", [
        ("换一家医院、换一台相机，这套东西还成立吗？",
         "How would this behave on a new hospital's images?",
         "That is domain shift, and our own experiment is a small preview: AUPRC dropped from "
         "0.197 on validation to 0.140 on test at the same prevalence, while AUROC barely moved. "
         "The diagnostic to report is the slope and intercept — a slope away from one tells you "
         "the scale did not transfer, even when the ranking did."),
        ("临床上该用哪个阈值？",
         "What operating point would you deploy?",
         "It depends on referral capacity, which is why we give the curve rather than a point. If "
         "you can tolerate referring about one in ten, BCE plus metadata has the highest net "
         "benefit from 0.05 upward. At very low thresholds the models are close, and focal is "
         "never usable."),
        ("漏诊和误诊的代价怎么平衡？",
         "How do you weigh a missed melanoma against a false alarm?",
         "The decision curve makes the exchange rate explicit: at a threshold of 0.10 you are "
         "declaring that one missed melanoma is worth about nine false referrals. We do not "
         "choose that rate for the clinic; we show the consequence of each choice."),
        ("1:56 的不平衡，加权真的一无是处吗？",
         "With 1:56 imbalance, is reweighting never right?",
         "It can be right if you need recall at a low threshold and you recalibrate afterwards — "
         "but our result says it may also cost ranking, not just scale, so it is not a free "
         "trade. The effective-number weighting, which is milder, sat between the two in the "
         "proposal's pilot; it is the first thing we would add here."),
        ("元数据为什么没提升 AUROC？",
         "Why did metadata not improve AUROC?",
         "Age, sex and site are coarse; they sharpen the upper tail of the ranking — that is the "
         "AUPRC and pAUC gain — without changing global separability. They also have 6–10% "
         "missingness, and the encoder is fitted on the training split only."),
        ("公平性怎么考虑？肤色呢？",
         "What about fairness, e.g. skin tone?",
         "ISIC 2020 has no skin-tone labels, so we cannot stratify by Fitzpatrick type. We "
         "stratify by age and anatomical site, and the actionable disparity is anatomical: "
         "extremity lesions are missed at roughly twice the torso rate. That is where we would "
         "invest next, with a site-balanced sampler or site-specific thresholds."),
        ("如果给你更多算力，你会先改哪一件事？",
         "With more compute, what would you change first?",
         "Five-fold patient-level cross-validation, so the intervals include run variance rather "
         "than only sampling noise, then 384 px, then a segmentation model for the extremity "
         "lesions. I would not add a new backbone — the ranking differences are far below the "
         "resolution of our intervals."),
    ]),
]


POSTER = {
    "15s": (
        "We re-tested the standard advice for imbalanced melanoma data. On a patient-disjoint "
        "split, class-balanced losses did not raise sensitivity — plain cross-entropy was best on "
        "every axis — and they damaged calibration, in two different ways."),
    "60s": (
        "Melanoma triage is a threshold problem, not a ranking problem, so we measured sensitivity "
        "at 80% specificity with the threshold frozen on validation, plus three views of "
        "calibration. Five runs differ only in the objective. Plain BCE reaches 0.892 AUROC, 0.140 "
        "AUPRC and 0.803 sensitivity at 80% specificity, with ECE 0.0045. Inverse-prevalence BCE "
        "loses ranking, 0.033 AUROC with p equal 0.032, and is over-confident. Focal loss is "
        "under-confident, ECE 0.136, and a single temperature removes 79% of that — while for "
        "inverse-prevalence BCE the same scalar removes nothing. So one objective hurts the scale, "
        "the other hurts the structure. Adding age, sex and site lifts AUPRC from 0.140 to 0.218 "
        "without changing AUROC."),
    "3min": [
        ("第一栏 · 问题与协议",
         "The question: does balancing buy sensitivity? The answer needs a protocol that cannot "
         "flatter the model — patient-disjoint split, threshold frozen on validation, paired "
         "patient bootstrap, three calibration views."),
        ("第二栏 · 主表与三个假设",
         "The table: BCE wins on AUROC, AUPRC, ECE and sensitivity. H1 rejected, focal is plus "
         "0.009 with an interval that spans zero. H2 holds in opposite directions. H3 splits: "
         "focal is repairable, inverse-prevalence is not. The calibration panel shows why — "
         "purple above the diagonal, green below."),
        ("第三栏 · 误差与结论",
         "23 of 117 missed, and they are confident misses at median 0.008, not borderline ones; "
         "extremities roughly twice the torso rate. Takeaway: report sensitivity at a frozen "
         "threshold plus class-conditional calibration, and treat threshold portability as a "
         "metric."),
    ],
    "panel_answers": [
        ("指着主表", "这五个数字是 test 上的，阈值来自 val 并冻结；括号里是 2000 次患者级 bootstrap。"),
        ("指着校准图", "紫线在对角线上方（过度自信），绿线在下方（自信不足）；右图是对数坐标，因为 1.8% 都在 0.1 以下。"),
        ("被问\"所以哪个模型最好\"", "BCE 在四个指标上最好；如果只看高召回区间的净收益，BCE+元数据 在 0.05 以上更好。"),
        ("被问\"这个结论能推广吗\"", "能推广的是方法：冻结阈值 + 类别条件校准 + 配对区间。数值是这份数据、这个 6 GB 卡上的。"),
    ],
}


# ------------------------------------------------------------------ builders
def build_docx(out_path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(1.9)
    sec.left_margin = sec.right_margin = Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name = SERIF
    st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), SANS)

    para(doc, "SDSC 6018 · Final Presentation", font=SANS, size=10, color=GREY, align="center")
    para(doc, "讲稿与答辩手册 · Speaker Script & Q&A", font=SANS, size=22, bold=True,
         color=ACCENT, align="center", after=4)
    para(doc, GROUP_LINE, font=SANS, size=11, color=BLUE, align="center", after=2)
    para(doc, "10-minute talk + Q&A · poster session · Fall 2026/27", font=SANS, size=10,
         color=GREY, align="center", after=14)

    # how to use
    h1(doc, "0　怎么用这份稿子")
    bullets(doc, [
        "**逐字稿用英文写，舞台提示用中文。** 英文是上台要说的原话；中文是你脑子里的动作指令，不要念出来。",
        "**按 %.0f 词/分钟排练。** 每页旁标了秒数，全稿约 1,300 词，正常语速正好 10 分钟。" % WPM,
        "**先背第一句和最后一句。** 每段只有开头一句和交接句必须一字不差，中间允许按记忆改写。",
        "**标了「可删」的句子**是超时时的泄压阀；按顺序删，删完仍能自洽（每处最多删约 8 秒）。",
        "**每页的讲稿也写进了 .pptx 的备注栏**：用 PowerPoint 演示者视图就能看到，不必背纸。",
    ])

    h1(doc, "1　时间与分工")
    para(doc, "课程要求每位成员都要讲一部分。四段各 2 分 30 秒，界线正好落在幻灯片切换处，交接不会卡。",
         font=SANS, size=10, after=6)
    rows = [
        ["1–3", "0:00 – 2:30", "Ke Liu", "开场、为什么 AUROC 不够、患者级划分", "150 s"],
        ["4–5", "2:30 – 5:00", "Zeyu Fu", "协议、主结果表（钱页）", "130 s"],
        ["6–7", "5:00 – 7:30", "Dong Wang", "两种失准、决策曲线", "145 s"],
        ["8–10", "7:30 – 10:00", "Kai Liu", "误差分析、takeaways、收尾", "150 s"],
    ]
    table(doc, ["幻灯片", "时间", "讲者", "内容", "台词量"], rows, [2.2, 3.0, 2.4, 7.4, 1.8])
    para(doc, "合计约 1,300 词台词 → 135 词/分钟 = 9 分 40 秒，留 20 秒给翻页和停顿。",
         font=SANS, size=9.5, italic=True, color=GREY, after=8)

    # per-slide script
    h1(doc, "2　逐页讲稿")
    for n, owner, secs, title, text, cn, cut in SLIDES:
        h2(doc, f"Slide {n} · {title}　—　{owner}，{secs}s")
        cue(doc, cn)
        script(doc, text)
        words = len(text.split())
        note = f"字数 {words} → 约 {words / WPM * 60:.0f} 秒"
        if cut:
            note += f"　｜　{cut}"
        para(doc, note, font=SANS, size=9, italic=True, color=GREY, after=10)

    # Q&A
    h1(doc, "3　Q&A 应答库")
    para(doc, "final draft 明确说会问三件事：你的假设、你的评估选择、以及方法在真实条件下如何表现。"
              "下面按这三类组织，共 18 问。**每题只记第一句**，后面的细节允许现场展开。",
         font=SANS, size=10, after=8)
    for group, items in QA:
        h2(doc, group)
        for cn_q, en_q, answer in items:
            qp = para(doc, f"Q（{cn_q}）／ {en_q}", font=SANS, size=10, bold=True,
                      color=BLUE, after=2)
            qp.paragraph_format.keep_with_next = True
            para(doc, answer, font=SERIF, size=10.5, after=8, indent=0.4)

    para(doc, "回答策略：先给一句结论，再给一个数字，最后给一个界线（我们的结论到哪为止）。"
              "不确定的问题就说「we did not test that, and here is how we would」。",
         font=SANS, size=10, italic=True, color=RED, after=10)

    # poster
    h1(doc, "4　Poster 讲稿")
    h2(doc, "4.1　15 秒版（路过的人）")
    script(doc, POSTER["15s"])
    h2(doc, "4.2　60 秒版（默认，站到海报前就用这一版）")
    script(doc, POSTER["60s"])
    h2(doc, "4.3　3 分钟版（对方明显有兴趣时，按栏推进）")
    for label, text in POSTER["3min"]:
        para(doc, label, font=SANS, size=10, bold=True, color=BLUE, after=2)
        script(doc, text)
    h2(doc, "4.4　指图说话的四句")
    bullets(doc, [f"{a}：{b}" for a, b in POSTER["panel_answers"]], size=10)

    # rehearsal
    h1(doc, "5　排练清单")
    bullets(doc, [
        "**第 1 遍（不计时）**：每人念自己的段落，只求顺口；把改过的句子直接写进备注栏。",
        "**第 2 遍（计时）**：四段连着走，记录每段实际用时；超 15 秒就在该段删一句「可删」。",
        "**第 3 遍（只练交接）**：练四次交接的六个字——\"Zeyu has the protocol\"、\"Dong will show\"、"
        "\"Kai will close\"、\"we are happy to take questions\"。",
        "**第 4 遍（无稿）**：只看幻灯片讲一遍，允许数字说错一位小数，不允许逻辑断层。",
        "**答辩演练**：两人一组，一人随机抽 5 题问，另一人 30 秒内答完；答不出就说界线。",
        "",
        "时间不够时，第一个删的是 Slide 7 的第二个数字组，第二个删的是 Slide 9 的 384 px 计划；"
        "**绝对不能删**的是 Slide 5 的主表和 Slide 9 的第一条 takeaway。",
    ])

    doc.save(out_path)
    return out_path


def inject_notes(slides_path, poster_path):
    prs = Presentation(slides_path)
    by_index = {n: (owner, secs, text) for n, owner, secs, _t, text, _cn, _c in SLIDES}
    for i, slide in enumerate(prs.slides, start=1):
        if i not in by_index:
            continue
        owner, secs, text = by_index[i]
        notes = f"[{owner} · {secs}s]\n\n{text}"
        slide.notes_slide.notes_text_frame.text = notes
    prs.save(slides_path)

    if poster_path and os.path.exists(poster_path):
        pp = Presentation(poster_path)
        s = pp.slides[0]
        s.notes_slide.notes_text_frame.text = (
            "POSTER · 60-second pitch\n\n" + POSTER["60s"] +
            "\n\n--- 15 s ---\n" + POSTER["15s"])
        pp.save(poster_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", default=os.path.join(ROOT, "SDSC6018_Talk_Script.docx"))
    ap.add_argument("--slides", default=os.path.join(ROOT, "SDSC6018_Presentation.pptx"))
    ap.add_argument("--poster", default=os.path.join(ROOT, "SDSC6018_Poster.pptx"))
    args = ap.parse_args()
    print("saved", build_docx(args.docx))
    inject_notes(args.slides, args.poster)
    print("notes injected into slides and poster")
