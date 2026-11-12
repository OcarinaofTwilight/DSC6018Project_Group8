"""中文版讲稿与答辩手册（独立文档）。

    python tools/build_talk_script_zh.py --out ../SDSC6018_讲稿_中文版.docx
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

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SONG = "宋体"
HEI = "黑体"
ACC = RGBColor(0x14, 0x3A, 0x5E)
BLUE = RGBColor(0x1F, 0x5C, 0x8B)
MUT = RGBColor(0x55, 0x55, 0x55)
RED = RGBColor(0xA3, 0x2A, 0x1F)

CPM = 240          # 中文演讲语速（字/分钟）
GROUP_LINE = "第 8 组 · Ke Liu · Zeyu Fu · Dong Wang · Kai Liu"


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


def p(doc, text="", size=10.5, bold=False, color=None, align=None, before=0, after=5,
      spacing=1.45, font=SONG, italic=False, indent=None, keep=False):
    par = doc.add_paragraph()
    pf = par.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = spacing
    if indent is not None:
        pf.left_indent = Cm(indent)
    if keep:
        pf.keep_with_next = True
    if align == "center":
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = par.add_run(text)
    fz(r, font, size, bold, color, italic)
    return par


def h1(doc, t):
    return p(doc, t, size=15, bold=True, color=ACC, font=HEI, before=16, after=6, keep=True)


def h2(doc, t):
    return p(doc, t, size=11.5, bold=True, color=BLUE, font=HEI, before=10, after=3, keep=True)


def cue(doc, t):
    return p(doc, "▸ " + t, size=9, font=HEI, color=MUT, italic=True, after=4)


def say(doc, t):
    return p(doc, t, size=10.5, align="justify", after=8, spacing=1.55)


def bullets(doc, items):
    for it in items:
        par = doc.add_paragraph(style="List Bullet")
        pf = par.paragraph_format
        pf.space_after = Pt(3)
        pf.line_spacing = 1.4
        pf.left_indent = Cm(0.85)
        pf.first_line_indent = Cm(-0.45)
        import re as _re
        for piece in _re.split(r"(\*\*.+?\*\*)", it):
            if not piece:
                continue
            bold = piece.startswith("**") and piece.endswith("**") and len(piece) > 4
            fz(par.add_run(piece[2:-2] if bold else piece), SONG, 10.5, bold=True if bold else None)


def table(doc, header, rows, widths, size=9.5):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, txt in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        par = cell.paragraphs[0]
        fz(par.add_run(str(txt)), HEI, size, True, ACC)
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
            fz(cells[i].paragraphs[0].add_run(str(txt)), SONG, size)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ------------------------------------------------------------------ 逐页台词
SLIDES = [
    (1, "Ke Liu", 20, "标题页",
     "各位老师上午好，我们是第 8 组：Ke Liu、Zeyu Fu、Dong Wang、Kai Liu。我们的问题很窄，"
     "也有点刺人：被广泛推荐的那套类别平衡损失，一旦按临床真正会用的方式去衡量，到底能不能让"
     "黑色素瘤分诊模型变好？",
     "站直，不要念标题页。这句只负责把注意力从屏幕拉到人身上。"),
    (2, "Ke Liu", 65, "分诊模型是阈值，不是 AUROC",
     "问题在一页之内。分诊模型不是一个排序，它是一个阈值：在固定的误报预算下——比如每 100 个良性"
     "病灶我们接受 20 次误报——模型能捞出多少恶性。ISIC 2020 的 33,126 张训练图里只有 584 张恶性，"
     "占 1.76%，所以一个「全判良性」的模型准确率 98.2%，完全没用。标准对策是类别平衡：逆患病率加权，"
     "或者 focal loss；而标准的报告方式是 AUROC。但 AUROC 对分数任何单调变换都不变——你把每个概率"
     "平方，AUROC 纹丝不动——所以它在结构上看不见真正决定阈值能不能用的那个副作用：概率尺度。我们"
     "五个 run 的 AUROC 从 0.855 到 0.892；ECE 从 0.0045 到 0.135，差三十倍。排序几乎一样，概率不能用。",
     "说「把每个概率平方」时用手比一下；说 0.0045 到 0.135 时指右上红框。"),
    (3, "Ke Liu", 65, "抽样单位是患者，不是图像",
     "有一个设计决定改变了后面所有数字：划分的单位。这 33,126 张图来自 2,056 名患者，平均每人 16 张；"
     "同一个病灶拍两次，看起来几乎一样。如果按图像划分，测试集里就有这位患者的另一张病灶，所有指标"
     "都被抬高。ISIC 2020 特意给出患者标识，就是为了避免这件事，所以我们冻结一份患者级不交叉的 "
     "70/10/20，之后再也不动；哈希随代码发布。把患病率调正花了两个阶段：贪心分配会漂，因为恶性标签"
     "集中在少数患者身上，所以加了交换修复。结果是 23,188、3,313、6,625 张，三段患病率都是 1.76%。"
     "代价是测试集只剩 117 例恶性——这就是后面每个比较都用配对 bootstrap 区间、而不是两个头条数字的"
     "原因。协议和主结果交给 Zeyu。",
     "屏幕右下角是误差图，这一页不要讲，留给 Kai。交接句放慢，然后退到侧边。"),
    (4, "Zeyu Fu", 65, "协议：能讨好我们的东西全部冻住",
     "谢谢 Ke。我们的协议只有一条原则：凡是可能让结果好看的，全部冻住。阈值取验证集阴性分数的 80 "
     "分位，只选一次，之后原样用到测试集；同时报告实际达到的特异度，因为它会漂。校准报三个口径，"
     "因为一个数说不清：等频 ECE、只在真恶性上算的 ECE、以及校准斜率。斜率小于一是过度自信，大于一"
     "是自信不足——等下两种都会出现。不确定性用患者级重采样，不是图像，2,000 次，每次对所有模型抽"
     "同一批患者，所以比较的是配对差值；阈值在每次重采样里保持固定，因为逐次重估会把敏感度报得偏"
     "乐观。最后是事后温度缩放：一个在验证集上拟合的标量。它是单调变换，所以 AUROC 和敏感度不可能变"
     "——这正好让它成为一个干净的检验：损坏是尺度问题，还是结构问题。",
     "这页是方法论核心，语速放慢。手依次落在「阈值 / 校准 / 不确定性」三块上。"),
    (5, "Zeyu Fu", 65, "普通 BCE 在每一项上都最好",
     "这是主表，也是整个故事。测试集，阈值在验证集冻结，区间来自患者级 bootstrap。普通 BCE：AUROC "
     "0.892、AUPRC 0.140（随机基线是患病率 0.018）、80% 特异度下敏感度 0.803、ECE 0.0045。逆患病率 "
     "BCE：AUROC 0.860，低 0.033，p 等于 0.032；AUPRC 0.091；敏感度 0.726；ECE 0.034。focal：敏感度 "
     "0.812——比 BCE 高 0.009，区间从 −0.063 到 +0.088，与零不可区分——但 ECE 0.136，差三十倍。同样的"
     "损失换成 ResNet-50，AUROC 0.855，所以这不是 EfficientNet 特有的现象。元数据：AUPRC 升到 0.218，"
     "p 小于 0.001，AUROC 不变。所以第一个假设——平衡能买来敏感度——被否证：没有任何一个平衡目标超过"
     "普通交叉熵，其中一个连排序都赔了。它对校准做了什么，交给 Dong。",
     "全场的「钱页」，语速最慢。每读一个数字停半秒，让评委抬头。"),
    (6, "Dong Wang", 80, "两种失准，方向相反",
     "谢谢 Zeyu。有意思的地方是：两个平衡损失都破坏了校准，但方向相反，而这个区别决定你能不能修。"
     "左图是一个温度前后的 ECE；右图是对数-对数坐标下的可靠性曲线，因为在 1.8% 患病率下所有事情都"
     "发生在 0.1 以下。逆患病率 BCE 是紫色，在对角线上方：斜率 0.43，恶性的中位预测概率 0.121，良性 "
     "0.0035。把正样本加权 55 倍，等于把整条尺度往上推。focal 是绿色，在对角线下方：斜率 1.85，恶性 "
     "0.391，良性 0.101。压低容易的 98%，模型就对几乎所有样本都含糊。再看温度：对 focal，它抹掉了 79% "
     "的 ECE，从 0.136 到 0.028，Brier 也降了 55%，而 AUROC、AUPRC、敏感度小数点后四位完全不变。对"
     "逆患病率，拟合出的温度是 1.05，ECE 几乎不动。所以 focal 的损坏是尺度问题，一个标量就能修；"
     "逆患病率的是结构性的，任何事后的分数映射都修不了。",
     "这一页最容易讲混：先说颜色（紫=过度自信、绿=自信不足），再给数字。"),
    (7, "Dong Wang", 65, "在运行区间里，focal 比不做还差",
     "交回给 Kai 之前的最后一个结果：这在临床上意味着什么。决策曲线画的是净收益对转诊阈值——也就是"
     "你愿意把多大风险的人转给皮肤科。在 0.02 处，BCE 是 0.0101，元数据 0.0094，逆患病率 0.0095，"
     "focal 是 −0.0007，而「全部转诊」是 −0.0024、「不转诊」是 0。也就是说在整段合理区间里，focal "
     "都不如不用模型。从 0.05 往上元数据模型最好：0.05 处 0.0067 对 0.0056，0.10 处 0.0047 对 0.0020"
     "——而这正是分诊规则会运行的区间。逆患病率在 0.10 左右穿过零线，不存在它有利的阈值。注意：这个"
     "排序和 AUROC 的排序并不一致。误差在哪里，交给 Kai。",
     "「不如不用模型」是全场最容易被追问的判断，说完停一秒。"),
    (8, "Kai Liu", 80, "漏掉的是「确信的良性」，不是边界样本",
     "谢谢 Dong。先讲失效模式，再给结论。参照模型 BCE 在冻结阈值下漏掉 117 例中的 23 例，19.7%。左图"
     "是被检出与被漏诊恶性的预测概率分布，对数坐标。漏诊的并不是边界样本：中位数 0.008，而被检出的是 "
     "0.084；操作阈值是 0.017，它们远在阈值之下，把阈值稍微挪一挪救不回来。这是信心失败——正好是温度"
     "实验分离出来的那个机制。中图和右图按年龄段与部位拆开。四肢的漏诊率是 30% 到 32%，躯干是 12%；"
     "样本量 45 对 51，所以这个对比是比较稳的，也与「拍摄角度倾斜或被毛发遮挡」的现象一致。年龄：40 岁"
     "以下 33%，70 岁以上 24 例里 0 例漏诊。这个我们不信——117 例阳性下 Wilson 区间宽约 20 个百分点"
     "——但这个子组分析是在看结果之前定下的，所以它是什么样，我们就报什么样。",
     "主动承认 70 岁以上那组不可信，比被问出来强得多。语气要平，不要辩解。"),
    (9, "Kai Liu", 60, "三条结论",
     "三条。第一：在这份数据上，类别平衡既没买到敏感度，也没保住校准，两者都赔了；只报 AUROC 会把"
     "这件事藏起来。第二：要报冻结阈值下的敏感度，再加上类别条件校准与斜率——一个全样本 ECE 只有 "
     "0.0045 的模型，它的 ECE_pos 是 0.90：在这个患病率下，一个恒输出 0.017 的预测器看起来「校准很好」，"
     "敏感度为零。第三：阈值可迁移性本身就是一个指标——focal 的验证阈值到测试集上掉了三个百分点特异度，"
     "约等于多出 200 次误转诊。下一步：384 像素、患者级五折交叉验证、以及针对四肢漏诊的分割分析。代码、"
     "冻结划分与逐图预测都已发布，每一张表都能在 CPU 上重算出来。",
     "三条结论用手指数出来，一条一句，不要连读。最后一句是可信度背书。"),
    (10, "Kai Liu", 10, "谢谢，提问",
     "谢谢各位，我们很乐意回答问题。",
     "说完站定，不要立刻回头指屏幕，等评委开口。"),
]

QA = [
    ("定位", [
        ("这和已有工作（Cassidy 2022、挑战赛报告）有什么不同？",
         "贡献不是新模型——提案里就写明了这一点。贡献是协议：一份冻结的患者级划分、一个在验证集冻结的"
         "阈值、三种校准口径（含类别条件 ECE 与斜率）、以及患者级配对区间。在这套协议下，平衡文献的核心"
         "主张并不成立，而我们把这件事显式地写出来，而不是藏在 AUROC 后面。"),
        ("所以你们的结论就是「什么都不用改」？",
         "不是。我们改的是报告方式：冻结阈值的敏感度 + 类别条件校准 + 斜率 + 配对差值。模型侧的建议是"
         "「默认不要动损失」，除非你有证据表明排序没受影响。"),
    ]),
    ("假设", [
        ("为什么把操作点定在 80% 特异度？",
         "这是一个预算，不是发现：全转诊无法运行，80% 大约等于每 5 个良性转 1 个。我们先定死它，好让五个"
         "模型在同一预算下比较；同时给出完整的敏感度-特异度曲线和决策曲线，预算不同的读者可以自己读。"),
        ("只跑 12 epoch、不做 early stopping，对平衡损失公平吗？",
         "这是我们用两晚算力所能做到的最公平设置：调度、学习率、batch、增强完全相同，且都是以 BCE 调出来的；"
         "选 checkpoint 的规则对五个模型一致（验证 AUPRC）。诚实的保留是：重加权目标偏爱更小的学习率——"
         "预实验里逆患病率 BCE 在 3e-4 会发散、需要 1e-4——所以它的一部分劣势可能来自优化而不是目标函数。"
         "这一点写进了局限。"),
        ("为什么只用一个划分、一个种子？",
         "因为区间刻画的是 117 例阳性带来的抽样噪声，而不是 run 之间的方差；五次训练在一块 6 GB 笔记本显卡"
         "上已经 3.4 GPU·小时。患者级五折交叉验证是我们第一个要补的，报告里也写了。划分冻结并哈希，所以"
         "实验可精确复现，只是不是一个集成。"),
        ("为什么用 256 像素？",
         "6 GB 显存。384 时 batch 掉到 12、每个 epoch 时间约翻倍，文献里的收益是 0.5–1 个 AUROC 点。而我们"
         "的效应量是 0.01–0.03，区间宽度 ±0.02，换分辨率不会改变结论。"),
    ]),
    ("评估选择", [
        ("你们 AUROC 比排行榜 0.94 低很多，是模型不行吗？",
         "两者不可比。官方测试集标签不公开，我们的测试集是 33,126 张公开训练图的患者级重划分；而排行榜允许"
         "训练与测试之间存在图像级重叠，同一患者的多处病灶会把所有指标抬高。这也是报告里那句「不与排行榜"
         "直接可比」的由来。"),
        ("既然有 AUPRC，为什么还要 ECE？",
         "因为 AUPRC 是排序指标，而阈值吃的是概率。你完全可以排序很好、但概率尺度把操作点推到 0.25 而不是 "
         "0.017——focal 就是这样。AUPRC 看不见这件事，ECE 和斜率看得见。"),
        ("ECE 对分箱和样本量很敏感，凭什么下结论？",
         "我们报三种：等宽、等频 15 箱、以及只在真恶性上的 ECE，再加上与分箱无关的校准斜率。focal 在四个"
         "口径下都最差。另外还报 Brier 与 NLL，它们是 proper scoring rule，排序不依赖任何分箱选择。"),
        ("阈值来自 58 例验证恶性，test 的敏感度会不会虚高？",
         "方向是反的：阈值不含测试标签、原样应用，误差通常是偏保守。剩下的是：我们在重采样中固定阈值，"
         "所以区间没有完全覆盖阈值选择噪声。若每次重估阈值，区间会略宽——0.838 [0.739, 0.908] 对 0.803 "
         "[0.720, 0.884]——比较结论不变。"),
        ("温度为什么不在 test 上拟合？",
         "在 test 上拟合就是用测试标签。在验证集上拟合一个标量是保守做法；在 test 上只会让 focal 更好看，"
         "而对逆患病率这个真正有意思的案例没有任何改变。"),
        ("温度缩放不也把阈值挪了吗？",
         "是的，这是真实的运行细节：排序不变，所以 AUROC 和按分位数定义的敏感度不动；但冻结在概率空间的"
         "阈值会偏移。如果部署事后校准，必须在校准之后重新在验证集上定阈值。报告里写明了这一点。"),
    ]),
    ("真实场景", [
        ("换一家医院、换一台相机，这套东西还成立吗？",
         "这是域偏移，而我们自己的实验就是一个小预演：同一患病率下 AUPRC 从验证集 0.197 掉到测试集 0.140，"
         "AUROC 几乎不动。要报的诊断量是斜率与截距：斜率偏离 1 就说明尺度没有迁移过去，即使排序还在。"),
        ("临床上该用哪个阈值？",
         "取决于转诊能力，所以我们给曲线而不是一个点。如果能接受大约十个转一个，BCE 加元数据在 0.05 以上"
         "净收益最高；阈值很低时几个模型接近，而 focal 永远不可用。"),
        ("漏诊和误诊的代价怎么平衡？",
         "决策曲线把这个兑换率显式化：阈值 0.10 意味着你认为一次漏诊约等于九次误转诊。我们不替临床定这个"
         "比率，只展示每种选择的结果。"),
        ("1:56 的不平衡，加权真的一无是处吗？",
         "如果你需要低阈值下的高召回，而且事后愿意重标定，它可能有价值——但我们的结果说它可能在排序上也有"
         "代价，所以不是免费交易。更温和的有效样本数加权在提案的预实验里位于两者之间，是我们第一个要补的。"),
        ("元数据为什么没有提升 AUROC？",
         "年龄、性别、部位都是粗粒度信息，它们锐化排序的上尾——这就是 AUPRC 和 pAUC 的增益——但不改变"
         "全局可分性。它们还有 6–10% 缺失，且编码器只在训练集上拟合。"),
        ("公平性怎么考虑？肤色呢？",
         "ISIC 2020 没有肤色标签，无法按 Fitzpatrick 分型分层。我们按年龄和解剖部位分层，可操作的差异是"
         "解剖部位：四肢的漏诊率大约是躯干的两倍。下一步是用按部位平衡的采样或部位专属阈值。"),
        ("多给你算力，你先改什么？",
         "先做患者级五折交叉验证，让区间包含 run 方差而不只是抽样噪声；然后 384 像素；再做分割模型去看"
         "四肢漏诊。我不会换骨干——排序差异远小于区间的分辨率。"),
        ("如果我只看一句话，你希望是哪句？",
         "「在这份数据上，平衡损失是拿排序和校准去换一个并不存在的敏感度增益」——而且这件事只有把阈值"
         "冻住、把校准分开报才看得见。"),
    ]),
]

POSTER = {
    "15": "我们重新检验了「不平衡数据要加权」这条标准建议。在患者级不交叉划分下，平衡损失没有提高敏感度"
          "——普通交叉熵在每一项上最好——而且它破坏校准，两种损失还是两个不同的方向。",
    "60": "黑色素瘤分诊是阈值问题，不是排序问题，所以我们在 80% 特异度下量敏感度，阈值在验证集冻结，"
          "外加三种校准口径。五次训练只改损失。普通 BCE：AUROC 0.892、AUPRC 0.140、敏感度 0.803、"
          "ECE 0.0045。逆患病率 BCE 连排序都掉，AUROC 低 0.033、p 等于 0.032，而且过度自信。focal "
          "自信不足、ECE 0.136，一个温度抹掉其中 79%；同样的温度对逆患病率毫无作用。所以一个坏在尺度、"
          "一个坏在结构。加入年龄、性别、部位把 AUPRC 从 0.140 提到 0.218，AUROC 不变。",
    "3": [
        ("第一栏：问题与协议",
         "问题是「平衡有没有买来敏感度」。回答它需要一套不能讨好自己的协议：患者级不交叉划分、验证集冻结"
         "阈值、患者级配对 bootstrap、三种校准口径。"),
        ("第二栏：主表与三个假设",
         "表上 BCE 在 AUROC、AUPRC、ECE、敏感度四项都最好。H1 被否：focal +0.009，区间跨零。H2 成立但"
         "方向相反。H3 分裂：focal 可修，逆患病率不可修。校准图解释了为什么——紫线在对角线上方、绿线在下方。"),
        ("第三栏：误差与结论",
         "117 例漏 23 例，而且是「确信的漏诊」，中位概率 0.008，不是边界样本；四肢漏诊率约是躯干的两倍。"
         "结论：报冻结阈值下的敏感度、加类别条件校准，并把阈值可迁移性当成一个指标。"),
    ],
}


def build(out_path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.0)
    sec.left_margin = sec.right_margin = Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name = SONG
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), SONG)
    st.paragraph_format.line_spacing = 1.45

    p(doc, "SDSC 6018 · 期末汇报", size=9.5, color=MUT, align="center", after=2)
    p(doc, "讲稿与答辩手册（中文版）", size=20, bold=True, color=ACC, align="center", after=4, font=HEI)
    p(doc, GROUP_LINE, size=10.5, color=BLUE, align="center", after=2)
    p(doc, "10 分钟演讲 + 提问 · 海报场次 · 2026/27 秋季", size=9.5, color=MUT,
      align="center", after=12)

    h1(doc, "0　这份稿子怎么用")
    bullets(doc, [
        "这是英文稿的中文对照版：**逻辑与数字完全一致**，用于小组内部对词、复盘，或需要中文演练时使用。"
        "正式上台仍建议用英文稿（SDSC6018_Talk_Script.docx），因为课程以英文授课。",
        f"按 {CPM} 字/分钟排练。每页标了秒数，全稿约 2,300 字，正常语速正好 10 分钟。",
        "每段只需记住第一句和交接句，中间的细节允许按记忆改写；数字必须背准，尤其是 0.803、0.0045、"
        "0.033 和 1.85 这四个。",
        "标注「▸」的是舞台提示，只给自己看，不念出来。",
    ])

    h1(doc, "1　时间与分工")
    p(doc, "课程要求每位成员都要讲一部分。四段各 2 分 30 秒，界线正好落在幻灯片切换处。",
      size=10, after=6)
    table(doc, ["幻灯片", "时间", "讲者", "内容", "中文台词量"],
          [["1–3", "0:00 – 2:30", "Ke Liu", "开场、为什么 AUROC 不够、患者级划分", "约 570 字"],
           ["4–5", "2:30 – 5:00", "Zeyu Fu", "协议、主结果表（钱页）", "约 480 字"],
           ["6–7", "5:00 – 7:30", "Dong Wang", "两种失准、决策曲线", "约 560 字"],
           ["8–10", "7:30 – 10:00", "Kai Liu", "误差分析、三条结论、收尾", "约 600 字"]],
          [2.2, 3.2, 2.4, 7.6, 2.4])

    h1(doc, "2　逐页讲稿")
    for n, owner, secs, title, text, cn in SLIDES:
        h2(doc, f"幻灯片 {n} · {title}　—　{owner}，{secs} 秒")
        cue(doc, cn)
        say(doc, text)
        p(doc, f"中文 {len(text)} 字 ≈ {len(text) / CPM * 60:.0f} 秒（按 240 字/分钟，"
                f"与英文稿的差别来自语言密度）", size=8.5, color=MUT, italic=True, after=10)

    h1(doc, "3　Q&A 应答库")
    p(doc, "final draft 说明会就三件事提问：你的假设、你的评估选择、以及方法在真实条件下的表现。"
           "下面按这三类组织，共 18 问；每题只记第一句，后面的细节现场展开。",
      size=10, after=8)
    for group, items in QA:
        h2(doc, group)
        for q, a in items:
            p(doc, "问：" + q, size=10, bold=True, color=BLUE, after=2, font=HEI, keep=True)
            p(doc, "答：" + a, size=10, align="justify", after=8, indent=0.6)

    p(doc, "回答策略：先给结论，再给一个数字，最后给界线（我们的结论到哪为止）。不确定的问题就说"
           "「这个我们没有测，我们会这样做」。", size=10, color=RED, italic=True, after=10)

    h1(doc, "4　海报讲稿")
    h2(doc, "4.1　15 秒版（有人只是路过）")
    say(doc, POSTER["15"])
    h2(doc, "4.2　60 秒版（默认，站到海报前就用这一版）")
    say(doc, POSTER["60"])
    h2(doc, "4.3　3 分钟版（对方明显有兴趣时，按栏推进）")
    for label, text in POSTER["3"]:
        p(doc, label, size=10, bold=True, color=BLUE, after=2, font=HEI)
        say(doc, text)
    h2(doc, "4.4　指图说话的四句")
    bullets(doc, [
        "指着主表：这五个数字是测试集上的，阈值来自验证集并冻结；方括号是 2,000 次患者级 bootstrap 区间。",
        "指着校准图：紫线在对角线上方（过度自信），绿线在下方（自信不足）；右图用对数坐标，因为 1.8% 全在 0.1 以下。",
        "被问「哪个模型最好」：BCE 在四项指标上最好；如果只看高召回区间的净收益，BCE 加元数据在 0.05 以上更好。",
        "被问「能推广吗」：能推广的是方法——冻结阈值、类别条件校准、配对区间；数值属于这份数据和这块 6 GB 显卡。",
    ])

    h1(doc, "5　排练清单")
    bullets(doc, [
        "第 1 遍（不计时）：各自念自己的段落，只求顺口；改过的句子直接写进幻灯片备注栏。",
        "第 2 遍（计时）：四段连排，记录每段实际用时；超 15 秒就在该段删一句。",
        "第 3 遍（只练交接）：反复练四句——「协议和主结果交给 Zeyu」「它对校准做了什么，交给 Dong」"
        "「误差在哪里，交给 Kai」「我们很乐意回答问题」。",
        "第 4 遍（无稿）：只看幻灯片讲，允许小数错一位，不允许逻辑断层。",
        "答辩演练：两人一组，随机抽 5 题互问，30 秒内答完；答不出就说界线。",
        "时间不够：先删第 7 页的第二组数字，再删第 9 页的 384 px 计划；不能删第 5 页主表和第 9 页第一条结论。",
    ])

    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "SDSC6018_讲稿_中文版.docx"))
    args = ap.parse_args()
    print("saved", build(args.out))
