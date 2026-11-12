"""中文版项目报告（独立文档，与原英文报告互不依赖）。

    python tools/build_report_zh.py --out ../SDSC6018_项目报告_中文版.docx
"""
from __future__ import annotations

import argparse
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSETS = os.path.join(ROOT, "report_assets")
SONG = "宋体"
HEI = "黑体"
IN = RGBColor(0x1A, 0x1A, 0x1A)
ACC = RGBColor(0x14, 0x3A, 0x5E)
BLUE = RGBColor(0x1F, 0x5C, 0x8B)
MUT = RGBColor(0x4A, 0x4A, 0x4A)

GROUP = "第 8 组"
NAMES = "Ke Liu (60909031) · Zeyu Fu (59938860) · Dong Wang (60934248) · Kai Liu (60291367)"


def fz(run, name=SONG, size=None, bold=None, color=None, italic=None):
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


def p(doc, text="", size=10.5, bold=False, color=IN, align=None, first=0.0,
      before=0, after=4, spacing=1.4, font=SONG, italic=False):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = spacing
    if first:
        pf.first_line_indent = Cm(first)
    if align == "center":
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text)
    fz(r, font, size, bold, color, italic)
    return par


def h(doc, text, level=1):
    size = {1: 14, 2: 11.5}[level]
    return p(doc, text, size=size, bold=True, color=ACC if level == 1 else BLUE,
             before=12 if level == 1 else 8, after=4, font=HEI)


def body(doc, text):
    return p(doc, text, align="justify", first=0.74)


def bullets(doc, items):
    for it in items:
        par = doc.add_paragraph(style="List Bullet")
        pf = par.paragraph_format
        pf.space_after = Pt(2)
        pf.line_spacing = 1.35
        pf.left_indent = Cm(0.85)
        pf.first_line_indent = Cm(-0.45)
        r = par.add_run(it)
        fz(r, SONG, 10.5)


def caption(doc, text):
    return p(doc, text, size=8.8, color=MUT, before=3, after=8, spacing=1.15)


def table(doc, header, rows, widths, size=8.6, caption_text=None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False          # -> w:tblLayout type="fixed"; without it LO re-flows columns
    t.autofit = False
    tbl_pr = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom", "insideH"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "999999")
        borders.append(el)
    for edge in ("left", "right", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tbl_pr.append(borders)
    # fixed layout + explicit table width: without this LibreOffice recomputes the column
    # widths and every numeric cell wraps mid-number
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    tbl_w = OxmlElement("w:tblW")
    tbl_w.set(qn("w:type"), "dxa")
    tbl_w.set(qn("w:w"), str(int(sum(widths) * 567)))
    tbl_pr.append(tbl_w)
    # default cell margins are ~0.19 cm per side, which is enough to wrap "0.0161" in a
    # 1.2 cm column; shrink them so the numbers stay on one line
    margins = OxmlElement("w:tblCellMar")
    for side in ("left", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), "34")          # 0.06 cm
        el.set(qn("w:type"), "dxa")
        margins.append(el)
    tbl_pr.append(margins)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)

    for i, txt in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        par = cell.paragraphs[0]
        par.paragraph_format.space_after = Pt(1)
        par.paragraph_format.line_spacing = 1.05
        r = par.add_run(str(txt))
        fz(r, HEI, size, True, ACC)
        tcpr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "EDEDED")
        tcpr.append(shd)

    for row in rows:
        cells = t.add_row().cells
        for i, txt in enumerate(row):
            cells[i].text = ""
            par = cells[i].paragraphs[0]
            par.paragraph_format.space_after = Pt(1)
            par.paragraph_format.line_spacing = 1.05
            r = par.add_run(str(txt))
            fz(r, SONG, size, i == 0)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
    if caption_text:
        caption(doc, caption_text)
    return t


def figure(doc, path, width_cm, cap):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(6)
    par.paragraph_format.space_after = Pt(2)
    par.add_run().add_picture(path, width=Cm(width_cm))
    caption(doc, cap)


def build(out_path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    sec.left_margin = sec.right_margin = Cm(2.2)
    st = doc.styles["Normal"]
    st.font.name = SONG
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), SONG)
    st.paragraph_format.line_spacing = 1.4
    st.paragraph_format.space_after = Pt(4)

    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run()
    fz(run, SONG, 8.5, color=MUT)
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    fp._p.append(fld)

    # ---------------- 题名区
    p(doc, "SDSC 6018 期末项目报告 · 2026/27 秋季", size=9.5, color=MUT, align="center", after=2)
    p(doc, f"{GROUP}　·　{NAMES}", size=9.5, color=MUT, align="center", after=10)
    p(doc, "类别平衡损失没有换来敏感度", size=18, bold=True, align="center", after=2, font=HEI)
    p(doc, "——ISIC 2020 上的校准优先、患者级不交叉基准", size=13, bold=True,
      align="center", after=4, font=HEI, color=ACC)
    p(doc, "香港城市大学 数据科学系", size=9.5, color=MUT, align="center", after=12)

    # ---------------- 摘要
    h(doc, "摘要")
    p(doc,
      "皮肤镜分诊模型通常以 AUROC 评判，但 AUROC 并不回答「这个概率能不能直接拿来定阈值」。我们在"
      "严格的患者级不交叉 70/10/20 划分（33,126 张公开训练图、2,056 名患者、恶性占 1.76%）下重新检验"
      " ISIC 2020：被广泛推荐的类别平衡目标函数，是否真的把敏感度买了回来，代价又是什么。五次训练只在"
      "目标函数（普通 BCE、逆患病率加权 BCE、focal）或是否拼接三项临床元数据上不同。主终点是「80% 特异度」"
      "下的敏感度（阈值在验证集上选定后冻结）、类别条件校准误差与校准斜率，并给出 2,000 次患者级配对"
      " bootstrap 区间。结果是负面的，而且清晰：普通 BCE 在每一项指标上都最好——AUROC 0.892 [0.865, "
      "0.917]、AUPRC 0.140、敏感度 0.803、ECE 0.0045。逆患病率 BCE 连排序都变差（AUROC −0.033，"
      "p = 0.032），并且严重过度自信（斜率 0.43）；focal 则严重自信不足（斜率 1.85，ECE 0.136）。"
      "一个温度参数能收回 focal 79% 的校准误差，却完全收不回逆患病率的——两者的损坏机理不同：一个坏在"
      "尺度，一个坏在结构。加入年龄、性别、部位三项元数据把 AUPRC 提高 0.078（p < 0.001），但不改变"
      " AUROC。在这一数据上，诚实的结论是：类别平衡既没买到敏感度，也没保住校准，而只有校准优先的协议"
      "才能让这一点显形。",
      align="justify", first=0.74, after=8)

    # ---------------- 1 引言
    h(doc, "1　研究问题")
    body(doc,
         "皮肤镜分诊要回答的是一个很窄的问题：在固定的误报预算下，模型能捞出多少恶性？ISIC 2020 正是为"
         "这个问题构建的，并且刻意提供了患者标识——因为同一皮损的多张照片、同一位患者的多处皮损，会让"
         "按图像划分的评估系统性乐观[1, 2]。数据本身也极端：33,126 张训练图里只有 584 张恶性（1.76%），"
         "所以一个「全判良性」的模型准确率 98.2%，却毫无用处。")
    body(doc,
         "标准对策是类别平衡目标函数——逆患病率加权或 focal loss——理由是提高少数类权重能换回敏感度"
         "[4, 5]。而这个理由通常用 AUROC 来验证，AUROC 对分数的任何单调变换都不变，因此它在结构上无法"
         "呈现真正决定阈值可用性的副作用：概率尺度。一个要按阈值运行的模型需要同时具备排序能力和概率"
         "可用性，只有校准优先的协议才把两者分开报告[3]。")
    body(doc,
         "我们因此提三个排行榜无法回答的问题。(H1) 在患者级不交叉划分下，平衡目标是否提高了固定特异度"
         "下的敏感度？(H2) 是否损害校准，往哪个方向？(H3) 这种损害是一个标量能修的尺度问题，还是结构性"
         "问题？")
    body(doc,
         "本文的贡献是一套协议与一个诚实的负结果：冻结一份患者级划分、冻结阈值、用配对区间比较、用三种"
         "口径报告校准。在这套协议下，平衡目标在敏感度、排序、校准三方面同时更差；「平衡损失是用校准换"
         "敏感度的免费交易」这一流行叙述，经不起测量。")

    # ---------------- 2 相关工作
    h(doc, "2　相关工作")
    body(doc,
         "ISIC 2020（SIIM-ISIC）在发布时就附带患者级元数据，正是为了让患者级不交叉评估成为可能[1]；"
         "Cassidy 等系统分析了历代 ISIC 数据集的划分问题，指出按图像划分会让同一身份跨训练与测试，并"
         "建议以患者为单位报告[2]。皮肤病变分类的基线长期是 ImageNet 预训练骨干[6, 7]，HAM10000 则确立"
         "了 ISIC 沿用的皮肤镜标注口径[8]。")
    body(doc,
         "在长尾问题上，focal loss 通过压低易样本梯度[4]，类别平衡损失则按有效样本数重新加权[5]，两者"
         "在医学长尾任务中被大量套用。在校准方面，Guo 等指出现代网络系统性过度自信，而一个事后拟合的"
         "温度标量即可收回大部分差距[3]——这正是本文 H3 的基础。决策曲线把「漏诊」与「误转诊」的兑换"
         "关系显式化[9]；当抽样单位是患者而不是图像时，bootstrap 是估计区间的标准工具[10]。")
    body(doc,
         "现有文献缺的正是本文提供的东西：在划分方式、阈值协议与校准仪器的全部条件固定不变的前提下，"
         "只让损失函数变化，然后比较。")

    # ---------------- 3 数据
    h(doc, "3　数据与预处理")
    body(doc,
         "使用 ISIC 2020 训练分区的 33,126 张皮肤镜图像、2,056 名患者，标签为恶性/良性二分类，并带有"
         "患者标识。官方测试集标签不公开，因此本文所有数字都来自公开训练图的患者级重划分，不与挑战赛"
         "排行榜直接可比——排行榜允许训练与测试之间存在图像级重叠。")
    body(doc,
         "划分只生成一次并冻结。两阶段确定性过程把患者（不是图像）分到 70/10/20：第一阶段按种子顺序把"
         "每位患者放进「图像数相对亏空 + 恶性例数相对亏空」最大的划分；第二阶段做局部搜索（移动或交换"
         "患者），只接受让目标函数 Σ(Δ图像/Σ图像)² + Σ(Δ恶性/Σ恶性)² 下降的改动。修复阶段不是可选项："
         "在同等规模的合成重尾数据上，只做贪心会把测试集患病率从 1.76% 漂到 0.56%，因为恶性标签集中在"
         "少数患者身上。最终清单经过断言校验（患者集合两两不交、同一皮损不跨划分、图像名不重复），"
         "并以 SHA-256 哈希随代码发布。")
    table(doc, ["划分", "图像数", "患者数", "恶性数", "患病率"],
          [["训练", "23,188", "1,437", "409", "1.76%"],
           ["验证", "3,313", "208", "58", "1.75%"],
           ["测试", "6,625", "411", "117", "1.77%"]],
          [2.2, 2.6, 2.6, 2.6, 2.6],
          caption_text="表 1　公开训练分区的患者级不交叉划分（seed 42）。清单哈希见附录 A。")
    body(doc,
         "图像一次性离线缩放到 256×256，用 ImageNet 统计量归一化。训练增强仅限几何变换（随机缩放裁剪 "
         "0.75–1.0、水平与垂直翻转、±20° 旋转）与轻度颜色抖动（0.15/0.15/0.10/0.03）：皮肤镜没有正"
         "方向，但颜色是最强判别信号，抖动过重会抹掉「深黑/深棕」这一关键线索。评估用「先放大到 292 再"
         "中心裁到 256」加四向翻转 TTA。")

    # ---------------- 4 方法
    h(doc, "4　方法")
    h(doc, "4.1　模型与训练", 2)
    body(doc,
         "两个 ImageNet 预训练骨干：EfficientNet-B3（去掉分类头后 11.1 M 参数，输出 1536 维池化特征）与 "
         "ResNet-50（25.6 M）[6, 7]。小头部由 BatchNorm、dropout 0.3、1536→256、ReLU、dropout、256→1 "
         "组成，输出单个 logit，使不同损失作用于同一对象、共用同一条训练与解码路径。元数据条件把年龄"
         "（归一化值 + 缺失标志）、性别（3 维 one-hot）、部位（7 维 one-hot）组成 13 维向量，经 MLP 投到 "
         "64 维后与图像特征拼接；元数据编码器只在训练集上拟合并与 checkpoint 一起序列化。")
    body(doc,
         "五次训练共用 AdamW（lr 3e-4、weight decay 1e-4）、5% 线性 warm-up + cosine 衰减、梯度裁剪 5、"
         "12 epoch、batch 16、混合精度，单卡 RTX 2060 Max-Q（6 GB）。每个 epoch 23,188 张图约 3.5 分钟。"
         "按验证集 AUPRC 选最佳 checkpoint；训练与选型过程中从未接触测试集。")
    h(doc, "4.2　损失条件", 2)
    body(doc,
         "只改变目标函数。普通带 logits 的二元交叉熵作参照。逆患病率加权把正样本权重乘以 n_neg/n_pos = "
         "55.7，等价于「漏掉一例恶性相当于 56 次误报」。focal 取 α = 0.75、γ = 2；RetinaNet 默认的 "
         "α = 0.25 在 1.76% 患病率下会反过来压低少数类权重，不适合这里[4]。有效样本数加权（β = 0.9999）"
         "作为 BCE 与逆患病率之间的中间点[5]；它在代码中已实现但未训练，算力全部投给了元数据消融。")
    table(doc, ["条件", "目标函数／有效正样本权重", "改变了什么"],
          [["BCE", "pos_weight = 1.0", "无（参照）"],
           ["逆患病率 BCE", "pos_weight = 55.7", "每个正样本的梯度尺度"],
           ["有效样本数（未训练）", "pos_weight = 22.4（β = 0.9999）", "较温和的重加权——已实现但未运行"],
           ["focal (α=0.75, γ=2)", "易样本上约 3:1", "压低易负样本"]],
          [3.6, 5.4, 4.7],
          caption_text="表 2　损失条件。实际训练三种（BCE、逆患病率、focal），加上 ResNet-50 与元数据两个变体共五次运行；有效样本数加权在代码中实现但未训练。数据、增强、调度与 checkpoint 规则完全相同。")
    h(doc, "4.3　评价协议", 2)
    body(doc,
         "主终点是 80% 特异度下的敏感度（Sens@Spec80）。阈值取验证集阴性分数的 80 分位，选定一次后"
         "原样用于测试，同时报告实际达到的特异度，因为它会漂。校准分三个口径：等频 15 箱的自适应 ECE；"
         "只在真恶性上计算的 ECE_pos（正样本预测概率距离 1 的平均亏欠）；以及对预测 logit 做 logistic "
         "回归得到的校准斜率 b（b < 1 过度自信，b > 1 自信不足）。次要指标为 AUROC、AUPRC、FPR ≤ 0.2 的"
         "部分 AUC、Brier 与 NLL。在 1.76% 患病率下只报全样本 ECE 会产生误导，第 5.4 节给出定量说明。")
    body(doc,
         "区间来自 2,000 次患者级 bootstrap：每次对所有模型抽取同一批患者，因此模型比较用的是配对差值，"
         "而不是两个边缘区间是否重叠。阈值在每次重采样中保持固定；若逐次重新估计，报出的敏感度会略偏"
         "乐观。双侧 p 值取配对差值落在零另一侧的重采样比例。")
    body(doc,
         "事后再校准：在验证集上按 NLL 最小化拟合单一温度 T，再应用到测试集。温度缩放是严格单调变换，"
         "因此 AUROC、AUPRC 与 Sens@Spec80 不可能改变；ECE 的任何变化都只能归因于概率尺度[3]。")
    h(doc, "4.4　训练动态与模型选择", 2)
    body(doc,
         "各条件的验证 AUROC 在 7–8 个 epoch 后进入平台（图 2 左），而验证 AUPRC 因为只有 58 例恶性而"
         "明显抖动（右）。我们按 AUPRC 而不是 AUROC 选 checkpoint：AUPRC 奖励把恶性排到前列，正是分诊"
         "终点需要的；但它同时是噪声最大的信号——同一 epoch 内不同 run 的差距，与我们报告的组间差异同"
         "量级。这就是第 5 节所有比较都用配对 bootstrap 区间、而不用两个点估计相减的原因。")
    figure(doc, os.path.join(ASSETS, "fig_training.png"), 16.2,
           "图 2　五个 run 的逐 epoch 验证指标。左：AUROC 在 8 个 epoch 后基本平台化；"
           "右：AUPRC（58 例验证恶性）是选型信号，也因此抖动明显。")

    # ---------------- 5 结果
    h(doc, "5　结果")
    h(doc, "5.1　普通 BCE 在每一项指标上都最好", 2)
    body(doc,
         "表 3 给出测试集结果，阈值来自验证集并冻结。BCE 的 AUROC 为 0.892 [0.865, 0.917]，AUPRC 0.140 "
         "[0.101, 0.202]（随机基线即患病率 0.0177），敏感度 0.803 [0.720, 0.884]，ECE 0.0045，斜率 0.80。"
         "两个平衡目标没有一个超过它。")
    table(doc, ["模型", "AUROC", "AUPRC", "pAUC", "Brier", "ECE", "ECEpos", "斜率", "Sens@Spec80", "特异度"],
          [["B3 + BCE", "0.892 [.865,.917]", "0.140 [.101,.202]", "0.565", "0.0161", "0.0045", "0.90", "0.80", "0.803 [.720,.884]", "0.816"],
           ["B3 + 逆患病率", "0.860 [.821,.894]", "0.091 [.066,.128]", "0.513", "0.0327", "0.0339", "0.74", "0.43", "0.726 [.640,.812]", "0.829"],
           ["B3 + focal", "0.876 [.847,.903]", "0.169 [.108,.255]", "0.530", "0.0469", "0.1355", "0.62", "1.85", "0.812 [.735,.891]", "0.771"],
           ["R50 + BCE", "0.855 [.815,.890]", "0.104 [.069,.157]", "0.497", "0.0166", "0.0055", "0.93", "0.65", "0.761 [.664,.849]", "0.799"],
           ["B3 + BCE + 元数据", "0.889 [.859,.918]", "0.218 [.157,.304]", "0.605", "0.0153", "0.0059", "0.84", "0.79", "0.752 [.663,.841]", "0.813"]],
          [2.5, 2.15, 2.15, 1.0, 1.2, 1.2, 1.3, 0.9, 2.15, 1.2], size=7.5,
          caption_text="表 3　测试集表现（6,625 张图、117 例恶性、411 名患者）。方括号为 95% 患者级 bootstrap "
                       "区间；ECE 为等频 15 箱；ECE_pos 只在真恶性上计算；Sens@Spec80 使用验证集冻结的阈值，"
                       "末列为实际达到的特异度。")
    figure(doc, os.path.join(ROOT, "figures", "panel.png"), 15.6,
           "图 1　测试集行为。左上为可靠性图（等频分箱）：focal 在对角线下方（自信不足），逆患病率在上方"
           "（过度自信）。右上 ROC 曲线彼此贴近，这正是只报 AUROC 会错过四者差别的原因。左下为敏感度-"
           "特异度曲线并标出 80% 操作点；右下为决策曲线，focal 在整个合理区间低于「不干预」线。")

    h(doc, "5.2　H1：平衡没有买来敏感度", 2)
    body(doc,
         "相对 BCE 的配对差值：focal +0.009 [−0.063, +0.088]，p = 0.88；逆患病率 −0.077 [−0.170, +0.019]，"
         "p = 0.15；ResNet-50 −0.043 [−0.121, +0.037]，p = 0.35。没有任何一个为正且显著。逆患病率还额外"
         "丢了排序：AUROC −0.033 [−0.065, −0.003]，p = 0.032；AUPRC −0.049 [−0.097, −0.015]，p = 0.006。"
         "在 117 例测试恶性的条件下，H1 被否证；focal 的区间足够宽，不能完全排除一个很小的真实增益，但"
         "没有证据支持平衡文献所预期的效应，且点估计方向相反。")

    h(doc, "5.3　H2：两种损失以相反方向破坏校准", 2)
    body(doc,
         "逆患病率 BCE 把 ECE 从 0.0045 抬到 0.0339（p < 0.001），focal 抬到 0.1355（p < 0.001），分别是"
         "7.5 倍和 30 倍。方向并不相同：逆患病率过度自信（斜率 0.43，恶性中位预测概率 0.121，良性 0.0035），"
         "55.7 倍的权重把整条概率尺度推高，可靠性曲线在对角线上方摊平；focal 则自信不足（斜率 1.85，恶性"
         "0.391，良性 0.101），压低 98% 易样本之后模型对几乎所有样本都含糊，其操作阈值从 0.017 移到 0.250。"
         "两者都能在图 1 的可靠性面板中看到，而两者都无法从 AUROC 看出。")

    h(doc, "5.4　H3：一个标量修好 focal，修不好逆患病率", 2)
    body(doc,
         "在验证集上拟合的单一温度把 focal 的 ECE 降低 79%（0.1355 → 0.0284）、Brier 降低 55%"
         "（0.0469 → 0.0213），而 AUROC、AUPRC 与 Sens@Spec80 小数点后四位完全不变——这是纯粹的尺度问题"
         "的特征。对逆患病率 BCE，拟合出的温度是 1.05，ECE 基本不动（0.0339 → 0.0351）：它的失准是结构性"
         "的，事后无法用分数映射修复。两个目标以相反的方式未通过 H3，这是本研究最具迁移价值的发现。")
    figure(doc, os.path.join(ASSETS, "fig_calibration.png"), 16.2,
           "图 3　左：单一温度缩放前后的 ECE，模型名下方为拟合出的 T；focal 被修复（0.136 → 0.028），"
           "逆患病率没有（0.034 → 0.035）。右：对数-对数坐标下的可靠性曲线，1.8% 患病率所在的低概率区间；"
           "focal 在下方（自信不足），逆患病率在上方（过度自信）。")
    table(doc, ["模型", "T（验证集）", "缩放前 ECE", "缩放后 ECE", "缩放前 Brier", "缩放后 Brier", "缩放前斜率", "缩放后斜率"],
          [["B3 + BCE", "1.04", "0.0045", "0.0044", "0.0161", "0.0161", "0.80", "0.83"],
           ["B3 + 逆患病率", "1.05", "0.0339", "0.0351", "0.0327", "0.0325", "0.43", "0.45"],
           ["B3 + focal", "0.27", "0.1355", "0.0284", "0.0469", "0.0213", "1.85", "0.51"],
           ["R50 + BCE", "1.14", "0.0055", "0.0058", "0.0166", "0.0167", "0.65", "0.74"],
           ["B3 + BCE + 元数据", "1.02", "0.0059", "0.0064", "0.0153", "0.0154", "0.79", "0.81"]],
          [3.2, 1.9, 2.1, 2.1, 2.2, 2.2, 2.0, 2.1], size=8.0,
          caption_text="表 4　事后再校准：温度在验证集拟合、应用到测试集。由于是单调变换，AUROC/AUPRC/"
                       "Sens@Spec80 前后必然相同。focal 的斜率越过 1 落到 0.51，说明 NLL 最优温度比校准最优"
                       "温度更「锐」。")

    h(doc, "5.5　元数据提升的是分诊区间的排序，不是整体分辨力", 2)
    body(doc,
         "加入年龄、性别、部位后 AUROC 不变（0.889 对 0.892，−0.003 [−0.022, +0.019]，p = 0.76），但 AUPRC "
         "提高 0.078 [0.037, 0.128]（p < 0.001），pAUC(FPR ≤ 0.2) 从 0.565 升到 0.605，并取得五个模型中最好的 "
         "Brier（0.0153）。80% 特异度下的敏感度低 0.051 [−0.120, +0.025]，p = 0.21，与噪声不可区分。这一"
         "模式与「元数据锐化了排序的上尾、但不改变全局可分性」一致，而且并没有带来可测量的校准收益。")

    h(doc, "5.6　决策曲线：focal 比不做还差", 2)
    body(doc,
         "在转诊阈值 p_t = 0.02 处，净收益为 BCE 0.0101、元数据 0.0094、逆患病率 0.0095、focal −0.0007，"
         "而「全部转诊」为 −0.0024、「不转诊」为 0。也就是说 focal 在整个合理阈值区间内都不如不使用模型。"
         "p_t ≥ 0.05 之后元数据模型最好（0.05 处 0.0067 对 0.0056；0.10 处 0.0047 对 0.0020），而这正是"
         "分诊规则会运行的区间；逆患病率在 p_t ≈ 0.10 处穿过零线，不存在它有利的阈值。决策曲线的排序与 "
         "AUROC 的排序并不一致，这是同时报告两者的实践理由。")

    h(doc, "5.7　阈值并不能完全迁移", 2)
    body(doc,
         "由于阈值在验证集选定后冻结，测试集上实际达到的特异度本身就是诊断量。BCE 落在 0.816（目标 0.80），"
         "ResNet-50 落在 0.799，而 focal 掉到 0.771：同一阈值多叫了三到四个百分点，在 6,508 个阴性样本上"
         "约等于多出 200 次误转诊。这是 5.3 节所记录的自信不足的操作代价，AUROC 看不见，任何在测试集上"
         "重新选阈值的做法也看不见。它还与事后校准相互纠缠：概率被重标定之后，冻结在概率空间的阈值会"
         "整体偏移，因此若两者同时使用，应当在验证集上「先温度、后阈值」一起选定。")

    h(doc, "5.8　从验证到测试，还剩多少", 2)
    body(doc,
         "checkpoint 与阈值都在 58 例验证恶性上选定，测试集才是第一次诚实的检验。表 5 并排给出两侧。"
         "AUROC 迁移良好（|Δ| ≤ 0.034，且最大差距出现在验证 AUROC 最弱的模型上），但 AUPRC 不然：五个"
         "模型中有四个下降 0.036–0.058，BCE 与 focal 的名次还发生了互换；冻结阈值下的敏感度最多移动 0.071"
         "（逆患病率上升，focal 下降）。实践含义是：验证集上 AUPRC 0.20 并不等于测试集上 0.20，「我们选了"
         "验证 AUPRC 最好的模型」这句话在这一样本量下比看上去要弱。这也是我们只报配对测试差值、不报验证"
         "集名次的理由。")
    table(doc, ["模型", "验证 AUROC", "测试 AUROC", "ΔAUROC", "验证 AUPRC", "测试 AUPRC", "ΔAUPRC", "验证 Sens@80", "测试 Sens@80"],
          [["B3 + BCE", "0.885", "0.892", "+0.008", "0.197", "0.140", "−0.057", "0.793", "0.803"],
           ["B3 + 逆患病率", "0.825", "0.860", "+0.034", "0.109", "0.091", "−0.017", "0.655", "0.726"],
           ["B3 + focal", "0.882", "0.876", "−0.006", "0.176", "0.169", "−0.007", "0.845", "0.812"],
           ["R50 + BCE", "0.854", "0.855", "+0.001", "0.160", "0.104", "−0.056", "0.759", "0.761"],
           ["B3 + BCE + 元数据", "0.894", "0.889", "−0.005", "0.200", "0.218", "+0.018", "0.810", "0.752"]],
          [3.2, 2.0, 2.0, 1.7, 2.0, 2.0, 1.7, 2.1, 2.1], size=8.0,
          caption_text="表 5　验证集（3,313 张、58 例恶性）与测试集（6,625 张、117 例恶性）对照。两列的阈值"
                       "都是验证集那一个，因此敏感度列只反映数据变化，不含重新调阈值。")

    # ---------------- 6 误差分析
    h(doc, "6　误差分析")
    body(doc,
         "在冻结阈值下，参照模型 BCE 漏掉 117 例恶性中的 23 例（19.7%）。漏诊者并不是边界样本：其中位"
         "预测概率为 0.008（10–90 分位 0.003–0.015），而被检出的恶性为 0.084（0.025–0.268），远低于 0.017 "
         "的操作阈值，微小调整阈值并不能救回它们。这是信心失败，正是 H3 所刻画的机制，而不是阈值调参"
         "问题。")
    body(doc,
         "漏诊集中在四肢，并在老年组消失。下肢与上肢的漏诊率为 30%（7/23）与 32%（7/22），躯干 12%（6/51）、"
         "头颈 17%（3/18）；按年龄看，40 岁以下 33%（7/21）、41–55 岁 20%（6/30）、56–70 岁 24%（10/42）、"
         "70 岁以上 0%（0/24）。在 117 例恶性下，这些子组的 Wilson 区间宽约 ±20 个百分点，因此我们把它们"
         "当作假设而不是结论：其中较稳的是四肢与躯干之比（26% 对 12%，样本量 45 对 51），与「拍摄角度倾斜"
         "或毛发遮挡」的现象一致。年龄模式与皮肤科文献相反，最可能是小样本假象；我们仍然报告它，因为这个"
         "子组分析是在看结果之前定下的——先定后看、无论结果如何都报，才是唯一值得相信的版本。")
    figure(doc, os.path.join(ASSETS, "fig_errors.png"), 16.2,
           "图 4　误差分布。左：被检出与被漏诊恶性的预测概率分布（对数坐标）及操作阈值；中、右：按年龄段"
           "与解剖部位的漏诊率，误差棒为 95% Wilson 区间，柱下为「漏诊数/总数」；70 岁以上组在本测试集中"
           "无漏诊（0/24）。")

    # ---------------- 7 讨论
    h(doc, "7　讨论")
    body(doc,
         "为什么平衡在这里失效？在患者级不交叉划分与冻结阈值下，BCE 已经达到 80% 特异度下 0.803 的敏感度："
         "剩下的错误是外观本身模糊的病灶，而不是被损失忽略的少数类。此时提高正样本权重主要等价于往梯度里"
         "注入噪声——409 个正样本对 22,779 个负样本，每个正样本值 56 个负样本——它抬高 logit 尺度，同时"
         "损失排序（AUROC −0.033）与校准。focal 行为不同但并不更好：压低易多数类之后，模型对几乎所有样本"
         "都保持不确定，即使排序得以维持，这也是校准缺陷。")
    body(doc,
         "方法论的教训是：校准不是一个数。本文有三个模型的全样本 ECE 低于 0.006——其中一个的 ECE_pos 是 "
         "0.93，因为在 1.76% 患病率下一个恒输出 0.017 的预测器 ECE 近乎为零，敏感度为零。只报 ECE 而不配"
         "类别条件版本与斜率，复制的正是「只报 AUROC」被批评的那种失败。同理，验证集阈值迁移到测试集后"
         "focal 的特异度只有 0.771（BCE 为 0.816），这是 AUROC 与「在测试集上重选阈值」都不会暴露的真实"
         "运行成本。")

    # ---------------- 8 局限
    h(doc, "8　局限")
    bullets(doc, [
        "单次划分、单个随机种子。区间刻画的是 117 例阳性带来的抽样噪声，不是不同 run 之间的方差；"
        "患者级五折交叉验证是下一步。",
        "测试集是公开训练分区的重划分，绝对数值不与允许图像级重叠的排行榜可比。",
        "验证集只有 58 例恶性，冻结阈值与温度本身带估计噪声，这一点只被区间部分吸收。",
        "元数据只用了三个字段；diagnosis 与 tbp_lv_* 系列属于标签派生或单次皮肤镜场景不可得，为避免"
        "泄漏而被排除。",
        "没有分割或 Grad-CAM 证据，误差分析是定量的：我们知道模型在哪里失败，但不知道原因。",
        "256 px、6 GB 笔记本显卡限制了分辨率与 batch；384 px 区间未做探索。",
    ])

    # ---------------- 9 结论
    h(doc, "9　结论")
    body(doc,
         "在患者级不交叉划分与校准优先的协议下，类别平衡损失在 ISIC 2020 上既没有买来敏感度，也没有保住"
         "校准，而是两者都赔了。逆患病率加权过度自信且结构性失准——事后标量无效；focal 自信不足且基本可"
         "由一个温度修复。普通 BCE 配冻结阈值仍是最好且校准最好的模型（AUROC 0.892、Sens@Spec80 0.803、"
         "ECE 0.0045），加入三项临床字段把 AUPRC 提高 0.078 而不改变 AUROC。尚待回答的是：这一排序在 384 px "
         "与患者级交叉验证下是否依然成立。协议、冻结划分与评估代码已经公开，使这个问题可以被检验，而不是"
         "被假定。")

    # ---------------- 参考文献
    h(doc, "参考文献")
    refs = [
        "Rotemberg V., Kurtansky N., Betz-Stablein B., et al. A patient-centric dataset of images and "
        "metadata for identifying melanomas using clinical context. arXiv:2008.07360, 2020.",
        "Cassidy B., Kendrick C., Brodzicki A., Jaworek-Korjakowska J., Yap M.H. Analysis of the ISIC "
        "image datasets: usage, benchmarks and recommendations. Medical Image Analysis 75:102305, 2022.",
        "Guo C., Pleiss G., Sun Y., Weinberger K.Q. On calibration of modern neural networks. ICML 2017.",
        "Lin T.-Y., Goyal P., Girshick R., He K., Dollár P. Focal loss for dense object detection. ICCV 2017.",
        "Cui Y., Jia M., Lin T.-Y., Song Y., Belongie S. Class-balanced loss based on effective number of "
        "samples. CVPR 2019.",
        "He K., Zhang X., Ren S., Sun J. Deep residual learning for image recognition. CVPR 2016.",
        "Tan M., Le Q.V. EfficientNet: rethinking model scaling for convolutional neural networks. ICML 2019.",
        "Tschandl P., Rosendahl C., Kittler H. The HAM10000 dataset. Scientific Data 5:180161, 2018.",
        "Vickers A.J., Elkin E.B. Decision curve analysis. Medical Decision Making 26(6):565–574, 2006.",
        "Efron B., Tibshirani R.J. An Introduction to the Bootstrap. Chapman & Hall, 1993.",
    ]
    for i, r in enumerate(refs, 1):
        par = doc.add_paragraph()
        pf = par.paragraph_format
        pf.space_after = Pt(2)
        pf.line_spacing = 1.2
        pf.left_indent = Cm(0.8)
        pf.first_line_indent = Cm(-0.8)
        run = par.add_run(f"[{i}]　{r}")
        fz(run, SONG, 8.8)

    # ---------------- 附录
    h(doc, "附录 A　可复现性")
    p(doc,
      "全部实验共用一份冻结清单（seed 42，SHA-256 记录于 manifests/split_seed42_report.json）。训练、评估与"
      "分析均已脚本化：src/split.py、src/train.py、src/evaluate.py、tools/fit_temperature.py、"
      "tools/bootstrap_frozen.py、src/report.py、src/figures.py。每个 run 的逐图预测以 CSV 形式与 checkpoint "
      "并存，因此本文所有表格与图都能在纯 CPU 机器上重新生成，无需重训。代码与本报告引用的划分清单已按"
      "要求向教学人员开放；硬件为单卡 RTX 2060 Max-Q（6 GB），五次训练合计 3.4 GPU·小时。",
      align="justify", first=0.74, size=9.5)

    h(doc, "附录 B　运行配置")
    table(doc, ["run", "骨干", "目标函数", "元数据", "epoch", "batch", "最佳 epoch", "墙钟时间"],
          [["b3_bce", "EfficientNet-B3", "BCE", "无", "12", "16", "11", "42 分钟"],
           ["b3_wbce", "EfficientNet-B3", "逆患病率 BCE（55.7）", "无", "12", "16", "11", "47 分钟"],
           ["b3_focal", "EfficientNet-B3", "focal（α=0.75, γ=2）", "无", "12", "16", "10", "44 分钟"],
           ["r50_bce", "ResNet-50", "BCE", "无", "12", "16", "8", "37 分钟"],
           ["b3_bce_meta", "EfficientNet-B3", "BCE", "有（13 维）", "12", "16", "10", "43 分钟"]],
          [2.6, 3.2, 4.0, 2.2, 1.4, 1.4, 1.8, 2.2], size=8.2,
          caption_text="表 6　五次运行的全部差异。共同设置：AdamW（lr 3e-4、wd 1e-4）、5% warm-up + cosine、"
                       "梯度裁剪 5、256 px、混合精度、按验证 AUPRC 选 checkpoint。")

    h(doc, "附录 C　完整测试集指标表")
    table(doc, ["模型", "AUROC", "AUPRC", "pAUC", "Brier", "NLL", "ECE 等宽", "ECE 等频", "ECEpos", "斜率", "阈值"],
          [["B3 + BCE", "0.892", "0.140", "0.565", "0.0161", "0.0679", "0.0044", "0.0045", "0.898", "0.80", "0.0170"],
           ["B3 + 逆患病率", "0.860", "0.091", "0.513", "0.0327", "0.1166", "0.0315", "0.0339", "0.737", "0.43", "0.0350"],
           ["B3 + focal", "0.876", "0.169", "0.530", "0.0469", "0.1916", "0.1355", "0.1355", "0.623", "1.85", "0.2495"],
           ["R50 + BCE", "0.855", "0.104", "0.497", "0.0166", "0.0710", "0.0049", "0.0055", "0.928", "0.65", "0.0156"],
           ["B3 + BCE + 元数据", "0.889", "0.218", "0.605", "0.0153", "0.0661", "0.0031", "0.0059", "0.841", "0.79", "0.0172"]],
          [2.9, 1.3, 1.3, 1.1, 1.3, 1.3, 1.6, 1.6, 1.6, 1.1, 1.3], size=7.8,
          caption_text="表 7　正文引用的全部测试集数字，末列为 Sens@Spec80 所用的验证集冻结阈值。表中同时列出"
                       "等宽与等频两种 ECE，以及只在真恶性上计算的 ECE_pos。")

    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "SDSC6018_项目报告_中文版.docx"))
    args = ap.parse_args()
    print("saved", build(args.out))
