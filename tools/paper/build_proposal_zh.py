"""提案中文版（独立文档，忠实翻译 6018_Proposal_Revised2.docx）。

    python tools/build_proposal_zh.py --out ../6018_提案_中文版.docx
"""
from __future__ import annotations

import argparse
import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_report_zh import (  # noqa: E402  (same house style as the Chinese report)
    ACC, BLUE, HEI, MUT, SONG, body, bullets, caption, fz, h, p, table,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def build(out_path):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.2)
    sec.left_margin = sec.right_margin = Cm(2.2)
    st = doc.styles["Normal"]
    st.font.name = SONG
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), SONG)
    st.paragraph_format.line_spacing = 1.4
    st.paragraph_format.space_after = Pt(4)

    # ---------------- 题名
    p(doc, "极端类别不平衡下的黑色素瘤检测", size=18, bold=True, align="center",
      after=2, font=HEI)
    p(doc, "SDSC6018 课程项目提案", size=12, bold=True, align="center", color=ACC, after=6, font=HEI)
    p(doc, "Ke Liu (60909031)　|　Zeyu Fu (59938860)　|　Dong Wang (60934248)　|　Kai Liu (60291367)",
      size=9.5, color=MUT, align="center", after=2)
    p(doc, "香港城市大学 数据科学系", size=9.5, color=MUT, align="center", after=12)

    # ---------------- 摘要
    h(doc, "摘要")
    body(doc,
         "我们计划在 ISIC 2020 皮肤镜数据集上开展一项可复现的研究：该数据集 33,126 张图像中恶性仅占约 "
         "1.8%。在这种不平衡下取得高 AUROC 并不困难，但 AUROC 几乎不能说明模型输出的概率是否可以用于"
         "分诊。我们将在患者级划分下训练迁移学习 CNN，把普通交叉熵与类别平衡损失、focal 损失进行比较，"
         "并把「固定特异度下的敏感度」与「校准」作为主终点。我们还将检验临床元数据（年龄、性别、解剖部位）"
         "是否能改善少数类的校准。")

    h(doc, "关键词")
    p(doc, "黑色素瘤；皮肤病变分类；类别不平衡；校准；ISIC 2020；皮肤镜", size=10, after=8)

    # ---------------- 1
    h(doc, "1　研究问题")
    body(doc,
         "ISIC 2020 包含来自 2,056 名患者的 33,126 张皮肤镜图像，其中仅 584 例恶性、32,542 例良性（少数类"
         "比例 1.76%）。在这种不平衡下，模型可以取得很高的总体准确率，同时漏掉相当比例的黑色素瘤。")

    # ---------------- 2
    h(doc, "2　先前工作")
    body(doc,
         "ISIC 2020 的构建正是为了填补此前皮肤图像数据集的一个缺口：同一患者的多处病灶没有被一致地关联"
         "起来，这使得按图像划分训练与评估时，患者身份会在不同分区之间泄漏。因此该数据集特意提供了患者"
         "标识，正是为了让患者级不交叉评估成为可能。")
    body(doc,
         "近期在该数据集上的应用型工作在划分上确实按患者进行，并通过加权采样处理不平衡，但主指标仍然是 "
         "AUROC，校准并未被当作主终点（Cassidy, 2022）。")
    body(doc,
         "另一条研究脉络开始把校准当作核心而非附属。May 等在有、无数据增强两种设置下于 SIIM-ISIC 2020 上"
         "训练神经网络，并同时比较 AUC 与期望校准误差（ECE），结果显示：即使 AUC 的提升有限甚至不存在，"
         "校准仍可能改善。Dominique 等走得更远，把校准作为 AUROC 公平性评估的补充基准：他们在性别、种族、"
         "年龄各子组上评估 ISIC 2020 挑战赛的头部模型，发现在新数据集上，领先模型「常常高估风险，并表现出"
         "校准问题」。这一发现促使我们采用校准优先的协议，而不是把校准作为事后补充。我们不打算提出新架构；"
         "我们要问的是：评估协议会不会改变结论。")

    # ---------------- 3
    h(doc, "3　数据与方法")
    body(doc,
         "我们将使用 ISIC 2020 训练集，可通过 ISIC Archive 获取——这是一个支持教学与研究的公开档案库。"
         "档案库对每张图像分别定义许可（CC-0、CC-BY 或 CC-BY-NC），获取门槛低。ISIC 2020 训练分区包含 "
         "33,126 张皮肤镜图像，带二分类标签（良性/恶性）以及可用于患者级划分的患者标识。")
    body(doc,
         "我们将利用提供的患者标识，强制实行患者级不交叉的训练/验证/测试划分，因为同一患者的多张图像"
         "否则会让身份跨分区泄漏。图像将缩放到 256×256 或 384×384 并做归一化。我们将在三种训练条件下"
         "微调 EfficientNet-B3 与 ResNet-50：(i) 标准二元交叉熵；(ii) 采用逆患病率权重的类别平衡损失；"
         "(iii) focal 损失。")

    # ---------------- 4
    h(doc, "4　实验评估")
    body(doc,
         "所有数字都在 33,126 张公开训练图的患者级重划分上计算。ISIC 2020 官方测试标签不公开，因此我们的 "
         "AUROC 与挑战赛排行榜不可直接比较——后者还允许训练与测试之间存在图像级重叠。")
    body(doc,
         "主终点将是 80% 特异度下的敏感度，以及针对恶性类的期望校准误差，两者都在留出测试分区上计算。"
         "次终点包括 AUROC、AUPRC 与 Brier 分数。由于少数类样本很少，敏感度与校准指标将报告 2,000 次"
         "患者级 bootstrap 重采样——按患者而不是按图像重采样，以尊重数据的依赖结构。")
    body(doc,
         "消融将包括：EfficientNet-B3 对 ResNet-50；BCE 对类别平衡对 focal 损失；有、无元数据；以及"
         "纯图像与图像＋元数据的校准对比。我们还将针对假想的「转诊皮肤科」阈值做决策曲线分析，把漏诊"
         "黑色素瘤与误转诊之间的权衡显式化。误差分析将按患者年龄段与病灶部位对假阴性分层，并公开精确的"
         "患者级划分清单。")

    # ---------------- 5
    h(doc, "5　时间表")
    table(doc, ["周次", "里程碑", "交付物／检查点"],
          [["第 7 周", "提案定稿并提交", "提案、数据访问确认、划分协议初稿"],
           ["第 8 周", "数据管线与划分清单完成", "患者级不交叉清单冻结；预处理与增强管线可复现；"
                                              "基线 ResNet-50（BCE）训练完成"],
           ["第 9 周", "主实验完成", "EfficientNet-B3 与 ResNet-50 在全部损失条件下训练完成；"
                                   "元数据增强条件完成；在验证集上计算校准与固定特异度敏感度；"
                                   "模型选择锁定"],
           ["第 10 周", "最终评估与误差分析", "留出集评估；2,000 次患者级 bootstrap；决策曲线分析；"
                                          "Grad-CAM 误差图；消融表定稿"],
           ["第 11 周", "报告与展示准备", "完成含全部图表与插图的最终报告；发布代码仓库与划分清单；"
                                       "演示幻灯片与海报定稿"]],
          [2.2, 4.6, 9.0], size=8.8,
          caption_text="表 1　提案时间表（第 7–11 周）。")

    # ---------------- 6
    h(doc, "6　预期产出")
    body(doc,
         "交付物包括：可复现的流水线；一张在「固定特异度下的敏感度」与「校准」两个维度上比较各损失函数的"
         "对照表；一张决策曲线图；以及一篇讨论——讨论 ISIC 2020 的极端不平衡是否会使某些评估选择"
         "（只报 AUROC、按图像划分）产生误导。贡献在于：为一个「头条 AUROC 常在这些控制条件缺席时被报告」"
         "的数据集，提供一个校准优先、患者级不交叉的基准。")

    # ---------------- 7
    h(doc, "7　分工与职责")
    body(doc,
         "Ke Liu（60909031）——项目负责人。方案设计、数据管线、患者级划分、模型训练、损失函数实验、"
         "评估、报告整合。")
    body(doc,
         "Zeyu Fu（59938860）——文献支持。梳理不平衡条件下的黑色素瘤分类与医学影像校准相关文献；"
         "整理参考文献。")
    body(doc,
         "Dong Wang（60934248）——可视化支持。可靠性图、决策曲线、敏感度-特异度权衡图。")
    body(doc,
         "Kai Liu（60291367）——文档与展示支持。划分清单与代码文档、bootstrap 结果核验、幻灯片。")

    # ---------------- 参考文献
    h(doc, "参考文献")
    refs = [
        "[1]（原文空缺）",
        "[2]（原文空缺）",
        "[3]（原文空缺）",
        "[4]（原文空缺）",
        "[5] Cassidy, B., Kendrick, C., Brodzicki, A., Jaworek-Korjakowska, J., & Yap, M. H. (2022). "
        "Analysis of the ISIC image datasets: Usage, benchmarks and recommendations. "
        "Medical Image Analysis, 75, 102305. DOI: 10.1016/j.media.2021.102305.",
    ]
    for r in refs:
        par = doc.add_paragraph()
        pf = par.paragraph_format
        pf.space_after = Pt(3)
        pf.line_spacing = 1.2
        pf.left_indent = Cm(0.8)
        pf.first_line_indent = Cm(-0.8)
        fz(par.add_run(r), SONG, 9)

    # ---------------- 译注
    h(doc, "译注")
    p(doc,
      "本文是对 6018_Proposal_Revised2.docx 的中文翻译，结构与编号（1–7 节、表 1、参考文献）与原文一致，"
      "内容未作增删。原文参考文献一栏只有 [5] 完整，[1]–[4] 为空、另有一处空编号；译文保留空缺并标注"
      "「原文空缺」，未代为补写。正式提交前如需补全，报告正文所用的对应文献为：Rotemberg 等（ISIC 2020 "
      "数据集，arXiv:2008.07360）、Cassidy 等（2022）、Guo 等（温度缩放与校准，ICML 2017）、Lin 等"
      "（focal loss，ICCV 2017）。另：原文 §3 提到 256×256 或 384×384，报告实际只做了 256（显存所限）。",
      size=9, color=MUT, align="justify", first=0.6)

    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "6018_提案_中文版.docx"))
    args = ap.parse_args()
    print("saved", build(args.out))
