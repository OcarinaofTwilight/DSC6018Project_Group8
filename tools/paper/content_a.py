# -*- coding: utf-8 -*-
"""Chapters 0-6 of the tutorial: setup, data, split, pipeline, model, losses."""
from __future__ import annotations

from docx.shared import Cm, Pt, RGBColor

from docx_kit import ACCENT, ACCENT2, BODY, MUTED


def cover(k: "Kit"):  # noqa: F821
    doc = k.doc
    for _ in range(3):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)

    p = doc.add_paragraph()
    p.alignment = 1
    r = p.add_run("SDSC6018 · COURSE PROJECT")
    r.font.size = Pt(10)
    r.font.color.rgb = ACCENT2
    r.bold = True
    from docx_kit import _fonts
    _fonts(r, BODY)

    p = doc.add_paragraph()
    p.alignment = 1
    p.paragraph_format.space_before = Pt(10)
    r = p.add_run("ISIC 2020 黑色素瘤检测与校准")
    _fonts(r, BODY)
    r.font.size = Pt(26)
    r.bold = True
    r.font.color.rgb = ACCENT

    p = doc.add_paragraph()
    p.alignment = 1
    r = p.add_run("从提案到可交付结果的实现教程")
    _fonts(r, BODY)
    r.font.size = Pt(16)
    r.font.color.rgb = ACCENT2

    p = doc.add_paragraph()
    p.alignment = 1
    p.paragraph_format.space_before = Pt(6)
    r = p.add_run("做什么 · 怎么做 · 代码是什么")
    _fonts(r, BODY)
    r.font.size = Pt(11.5)
    r.font.color.rgb = MUTED

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(26)
    k.table(
        ["项目", "内容"],
        [
            ["课程", "SDSC6018 Course Project · City University of Hong Kong"],
            ["对应提案", "《Melanoma Detection Under Extreme Class Imbalance》(6018_Proposal_Revised2)"],
            ["小组成员", "Ke Liu (60909031) · Zeyu Fu (59938860) · Dong Wang (60934248) · Kai Liu (60291367)"],
            ["配套代码", "`melanoma_calib/`（10 个模块 + 自检 + 数据工具，与本文档同步）"],
            ["算力前提", "一台笔记本（CPU）＋ Google Colab 免费版单卡 Tesla T4 16 GB"],
            ["文档版本", "v2.0"],
        ],
        widths=[3.0, 13.2],
        size=9.2,
    )

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    k.tip(
        "这份教程按「执行顺序」写，不按「论文顺序」写。每一章都对应一个可以当晚做完的动作，"
        "末尾给出预期输出与检查点。你可以从第 2 章直接开始动手，遇到判断再回头看第 1 章。"
    )
    k.page_break()


def toc(k):
    k.h1("目录", "十四步，一条流水线")
    k.p(
        "下面每一行都是「一次可验证的产出」。左侧是章节，右侧是你做完这一节手里应该多出来的东西。",
        after=8,
    )
    k.table(
        ["章", "内容", "完成后你手里有"],
        [
            ["0", "先读这一页：七天日历、分工、三条判断", "一份排期，四个人都知道自己哪天做什么"],
            ["1", "把提案拆成 7 个任务：假设、指标定义、任务表", "冻结的实验协议（指标口径写死）"],
            ["2", "Day 1 环境与数据：本机 + Colab、下载、体检", "能跑的数据目录 + 体检报告"],
            ["3", "T1 患者级划分：算法、代码、冻结哈希", "`manifests/split_seed42.csv` + sha256"],
            ["4", "T2 数据管道：增强、13 维元数据、DataLoader", "可复现的 batch"],
            ["5", "T3 模型：EfficientNet-B3 / ResNet-50 + 融合头", "参数量与显存确认"],
            ["6", "T4 三种损失：BCE / 逆患病率 / focal", "一张有效权重对照表"],
            ["7", "T5 训练：命令、冒烟、续训、日志", "5 个 run 目录，每个 4 个文件"],
            ["8", "T6 评估：TTA、温度缩放、导出预测", "每个 run 的 `test_preds.csv`"],
            ["9", "T7 统计：主终点、阈值协议、配对 bootstrap", "结果表 + 差值 CI"],
            ["10", "图与误差分析：四张图、分层假阴性", "`figures/panel.png` + 分层表"],
            ["11", "写作与交付：报告骨架、三句硬话、清单", "可提交的报告与代码"],
            ["12", "排错手册：十二个真实会遇到的故障", "一份故障对照表"],
            ["13", "执行检查清单：20 项", "全部打勾的交付物"],
            ["附录", "文献修正、命令速查、预算表", "报告参考文献已改正"],
        ],
        widths=[1.3, 9.2, 5.7],
        size=8.6,
        caption="表 0-1　全文结构",
    )
    k.page_break()


# ----------------------------------------------------------------- chapter 0
def ch0(k):
    k.h1("0", "先读这一页")

    k.p(
        "提案在方法上是成立的：题目清楚、数据公开、把「敏感度 @ 固定特异度」和「校准」放在主终点位置，"
        "比通常的 AUROC 竞赛式报告更接近临床问题。真正会卡住你们的不是想法，而是三件具体的事："
        "算力只有一块会断线的免费 T4；患者级划分一旦重做，前后数字就不可比；"
        "以及 1.76% 的患病率会让「均方误差式」的指标集体失灵。"
    )
    k.p("这份教程把提案变成 7 个可执行任务、约 12 条命令、一份可以逐项打勾的检查清单。")

    k.h2("0.1　这份教程不做什么")
    k.bullets([
        "**不提新模型。** 提案自己写了「We do not propose a new architecture」，所以教程不会给你任何结构创新，"
        "只会给你两个标准 backbone 和一套评估协议。这是加分项，不是妥协。",
        "**不承诺数字。** 全文出现的所有数值都标注了来源：要么是程序真实输出（可复现），"
        "要么是明写的「示意」。没有第三种。",
        "**不替你写报告。** 但第 11 章给了骨架、句式和有证据支撑的判断，照着填比从零写快得多。",
    ])

    k.h2("0.2　七天执行日历")
    k.p(
        "前提：四个人、每天投入 2–3 小时、只有一块免费 T4。GPU 时间只花在训练上，"
        "写代码、画图、统计全部在本机 CPU 完成——这一条能省掉一半配额。",
        after=6,
    )
    k.table(
        ["Day", "做什么", "产出", "对应提案里程碑"],
        [
            ["1", "环境、下载数据、数据体检、冻结划分（第 2–3 章）",
             "`manifests/split_seed42.csv` + 哈希；`data/` 可用", "Week 8：data pipeline and split manifest completed"],
            ["2", "冒烟测试 + 第一个正式实验 `b3_bce`（第 7 章）",
             "`runs/b3_bce/{log.csv,last.pt,best.pt,cfg.json}`", "Week 8：baseline ResNet-50/EffNet trained"],
            ["3", "`b3_wbce` + `b3_focal`（两个 Colab 会话）", "三个损失条件齐备", "Week 9：main experiments"],
            ["4", "`r50_bce` + `b3_bce_meta`", "架构消融与元数据条件", "Week 9：ablations"],
            ["5", "评估五个 run、拟合温度缩放（第 8 章）", "5 份 `runs/*/test_preds.csv`", "Week 10：held-out test evaluation"],
            ["6", "配对 bootstrap、四张图、分层误差（第 9–10 章）", "`results/` 三张表 + `figures/panel.png`", "Week 10：bootstrap, decision curve, error analysis"],
            ["7", "写报告、复现检查（第 11、13 章）", "报告 + 代码仓 + 划分清单", "Week 11：report and presentation"],
        ],
        widths=[1.1, 5.6, 5.2, 4.3],
        size=8.4,
        caption="表 0-2　七天日历。Day 3–4 的四个训练可以拆到任意两天，只要保持「一个会话一个实验」",
    )
    k.tip(
        "算力只有 5.8 GPU·小时左右（见附录 C）。免费 T4 每天实际能给 2–3 小时，"
        "所以 Day 5 之后的日子基本不占 GPU：评估可以用 CPU 慢慢跑，bootstrap 和画图完全不用 GPU。"
        "把这几块和「等 GPU」错开排，一周是够的。"
    )

    k.h2("0.3　四个人的分工与本周动作")
    k.p(
        "提案 §7 已经分了工，这里把它翻译成「这周要点几下鼠标」。分工的目的是并行，不是免责。",
        after=6,
    )
    k.table(
        ["成员", "角色", "Day 1–2", "Day 3–7"],
        [
            ["Ke Liu", "项目负责人", "跑通自检、冻结划分、写实验协议", "监督矩阵执行、锁模型选择、整合报告"],
            ["Zeyu Fu", "文献", "核对提案参考文献（附录 A 有 4 处必改）", "写 Related Work、把每篇文献对应到一条论断"],
            ["Dong Wang", "可视化", "本机装好环境、跑通 `figures.py`（用假预测 CSV）", "四张图、决策曲线、可靠性图"],
            ["Kai Liu", "文档与验证", "建仓库、写 README 的 5 行复现说明", "核对 bootstrap 数字、做幻灯片"],
        ],
        widths=[2.0, 2.2, 6.2, 5.8],
        size=8.4,
        caption="表 0-3　分工。任何一个人都要能独立跑通「冒烟 → 评估」这两步，否则第十周会卡在单点上",
    )

    k.h2("0.4　三条写在最前面的判断")
    k.p("这三条决定了后面所有取舍。不同意其中任何一条，都应该先改提案，而不是改代码。")

    k.h3("（1）官方测试集拿不到标签，所以「test」只能是自己划的")
    k.p(
        "ISIC 2020 挑战赛的测试分区（10,982 张）只有图像、没有 ground truth。"
        "因此提案 §4 说的 held-out test 必须理解为：从 33,126 张公开训练图里按患者级切出来的 20%。"
        "这本身完全站得住，但报告里必须写清楚，否则读者会拿你们的 AUROC 去比 leaderboard 的 0.94。"
    )
    k.code(
        "All numbers are computed on a patient-disjoint re-split of the 33,126 public\n"
        "training images. The official ISIC 2020 test labels are withheld, so our AUROC is\n"
        "not directly comparable to the challenge leaderboard, which additionally allowed\n"
        "image-level overlap between train and test.",
        title="可直接写进 Methods 的句子",
    )

    k.h3("（2）真正的瓶颈是「测试集里只有约 117 例恶性」")
    k.p(
        "584 例恶性按 70/10/20 切开，测试集只剩约 117 例。敏感度 @ 80% 特异度在这个样本量上的标准误约 "
        "sqrt(0.5×0.5/117) ≈ 0.046，再叠加患者级聚类，95% 区间半宽接近 ±0.09。"
        "这意味着：**不要期待「显著优于」**，要期待「方向一致」。"
    )
    k.why(
        "两个模型各自 ±0.09 的区间必然大面积重叠，而「两个 CI 是否重叠」在统计上根本不是模型比较的正确检验。"
        "正确做法是配对 bootstrap 的差值 CI（第 9.5 节）：同一批患者重采样上同时算两个模型，差值的不确定度远小于各自的不确定度。"
    )

    k.h3("（3）GPU 只够 5–6 次训练，所以实验矩阵要设计成 5 次")
    k.p(
        "提案 §4 的消融若按「2 backbone × 3 loss × 有/无元数据」全跑，是 12 次训练 ≈ 14 GPU·小时，"
        "免费版一周给不了。第 7.5 节给了一个 5 次训练覆盖全部四个消融维度（损失 / 架构 / 元数据 / 校准后处理）的矩阵，"
        "逻辑是：你们要回答的是「损失会不会改变结论」，不是「哪个组合最强」，所以交叉项可以省。"
    )
    k.page_break()


# ----------------------------------------------------------------- chapter 1
def ch1(k):
    k.h1("1", "把提案拆成 7 个可执行任务")

    k.h2("1.1　研究问题、三个假设")
    k.p(
        "一句话版本：**在 1.76% 患病率、患者级划分下，类别平衡损失换来的敏感度，是不是以概率校准为代价？**"
        "这个问题只有在「主终点不是 AUROC」时才成立，所以协议本身就是贡献。"
    )
    k.p("把它写成三个可证伪的假设，后面每个实验都为其中一个服务：", after=6)
    k.table(
        ["编号", "假设", "怎么算被证伪", "证据来源"],
        [
            ["H1", "平衡损失（逆患病率 BCE / focal）提高 Sens@Spec80",
             "配对差值 CI 跨 0，或方向在 val 与 test 上相反", "第 9.5 节的差值表"],
            ["H2", "代价是校准变差（ECE 上升、校准斜率下降）",
             "ECE 差值 CI 的上界 < 0，或斜率不降", "第 9.2–9.3 节的三种 ECE 口径"],
            ["H3", "校准的破坏主要是「尺度」而非「排序」：单一温度参数能收回大部分",
             "温度缩放后 AUROC/AUPRC 变化（不应变化）、ECE 收不回来", "第 8.2 节 + 第 9.7 节的斜率/T 对照"],
        ],
        widths=[1.2, 6.4, 5.6, 3.2],
        size=8.5,
        caption="表 1-1　三个假设与证伪条件。写报告时按这张表逐条回答，不要临场组织叙事",
    )
    k.why(
        "H3 是这个项目最值钱的一条，因为温度缩放是严格单调变换：它**不可能**改变 AUROC、AUPRC、Sens@Spec80，"
        "只能改变概率的分布。所以「ECE 被收回」与「排序信息完好」是同一件事的两种说法。"
        "只有做过这一步，「校准坏了」才不是一句无信息量的抱怨。"
    )

    k.h2("1.2　主终点与次终点：把定义写死")
    k.p(
        "提案里最含糊的一句是「expected calibration error for the melanoma class」。"
        "在 1.76% 的患病率下，这句话至少有三种互不等价的实现，而它们能给出 0.004 和 0.19 两个结论（第 9.3 节有构造性例子）。"
        "开跑前必须选定口径；下表就是「已选定」的样子。",
        after=6,
    )
    k.table(
        ["指标", "精确定义", "本文角色", "越大越好"],
        [
            ["Sens@Spec80", "在 **val** 的阴性分数 80 分位取阈值 t；test 上 P(score ≥ t | 恶性)", "主终点 1", "是"],
            ["ECE_adaptive15", "按 15 个等频箱：Σ (n_b/N)·|mean(p_b) − frac_pos_b|", "主终点 2", "否"],
            ["ECE_pos", "只在真恶性上按等频箱：Σ (n_b/N_pos)·|mean(p_b) − 1|", "主终点 2 的补充", "否"],
            ["校准斜率 b", "logistic 回归 y ~ a + b·logit(p) 的斜率", "机理指标", "→ 1 最好"],
            ["Brier", "mean((p − y)²)", "次要（proper）", "否"],
            ["AUROC", "排序能力，与阈值无关", "次要", "是"],
            ["AUPRC", "平均精度；随机基线 = 患病率 0.0176", "次要", "是"],
            ["pAUC(0–0.2)", "ROC 在高特异区的归一化面积", "次要", "是"],
            ["Net benefit", "TP/N − FP/N·pt/(1−pt)", "决策曲线", "是"],
        ],
        widths=[3.0, 8.4, 3.0, 2.0],
        size=8.4,
        caption="表 1-2　指标清单。前四行是主结果，剩下的用来证明主结果不是某个口径的偶然",
    )
    k.warn(
        "阈值只能从 val 来。如果在 test 上按 80% 特异度反推阈值再算敏感度，等于用测试集调参，"
        "结果会系统性乐观 2–5 个百分点。这一条在代码里是强制的：`evaluate.py` 默认在 test 上重新算阈值，"
        "所以正确流程是第 9.2 节的「先 val 冻结阈值，再喂给 test」。",
        extra="最容易无意中作弊的一步",
    )

    k.h2("1.3　七个任务")
    k.p(
        "每个任务都有明确的输入、输出、命令与检查点，后面七章一一展开。T0 是唯一一个不需要数据、不需要 GPU 的任务。",
        after=6,
    )
    k.table(
        ["任务", "做的事", "产出", "命令 / 入口", "章节"],
        [
            ["T0", "数值自检：指标、划分器、bootstrap", "25 项 PASS", "`python tests/test_all.py`", "1.5"],
            ["T1", "患者级划分并冻结", "`manifests/split_seed42.csv` + sha256", "`python src/split.py`", "3"],
            ["T2", "数据管道：增强 + 元数据", "可复现的 batch", "`src/data.py`", "4"],
            ["T3", "模型：B3 / R50 + 融合头", "参数量确认", "`python -c \"...build_model...\"`", "5"],
            ["T4", "三种损失 + 权重对照", "有效权重表", "`python src/losses.py`", "6"],
            ["T5", "训练 5 个 run", "5 个 run 目录", "`python src/train.py ...`", "7"],
            ["T6", "评估、TTA、温度缩放", "5 份 `test_preds.csv`", "`python src/evaluate.py ...`", "8"],
            ["T7", "配对 bootstrap + 结果表 + 图", "`results/`、`figures/`", "`python src/report.py`、`src/figures.py`", "9–10"],
        ],
        widths=[1.2, 5.0, 4.0, 4.2, 1.4],
        size=8.3,
        caption="表 1-3　任务表。T0–T1 在 Day 1 完成，T2–T3 只写代码不花 GPU，T5 才是唯一烧算力的环节",
    )

    k.h2("1.4　代码仓与教程的对应")
    k.p(
        "教程里出现的每一段代码都来自 `melanoma_calib/` 里的真实文件（本文档构建时用 `ast` 直接从源码抽取，"
        "因此不会出现「文档里的代码和仓库里的代码不一致」）。下表是索引。",
        after=6,
    )
    k.table(
        ["文件", "行数", "职责", "对应章节", "提案章节"],
        [
            ["`src/split.py`", "≈270", "患者级划分 + 校验 + sha256", "第 3 章", "§3"],
            ["`src/data.py`", "162", "增强、13 维元数据编码、Dataset/DataLoader", "第 4 章", "§3"],
            ["`src/models.py`", "87", "B3 / R50 backbone + 元数据融合头", "第 5 章", "§3"],
            ["`src/losses.py`", "95", "BCE / 逆患病率 BCE / 有效样本数 / focal", "第 6 章", "§3 (i)(ii)(iii)"],
            ["`src/train.py`", "236", "AMP、warmup+cosine、断点续训、逐 epoch 日志", "第 7 章", "§4"],
            ["`src/evaluate.py`", "107", "TTA 推理、温度缩放、导出预测", "第 8 章", "§4"],
            ["`src/metrics.py`", "286", "纯 numpy 的九个指标（报告的唯一数字来源）", "第 9 章", "§4"],
            ["`src/bootstrap.py`", "132", "患者级配对 bootstrap", "第 9.5 节", "§4"],
            ["`src/report.py`", "109", "汇总 run → 结果表 + 差值表", "第 9.6 节", "§4/§6"],
            ["`src/figures.py`", "140", "可靠性图 / ROC / 敏感度-特异度 / 决策曲线", "第 10 章", "§6"],
            ["`tests/test_all.py`", "167", "25 项数值自检（无 GPU、无数据）", "第 1.5 节", "§6"],
            ["`tools/inspect_data.py`", "≈120", "Day 1 数据体检（八个问题）", "第 2.5 节", "§3"],
            ["`tools/resize_images.py`", "≈70", "1024 → 256 离线缩放", "第 2.4 节", "§3"],
            ["`tools/make_synthetic.py`", "≈80", "同规模假数据，用于无数据环境下演练", "第 2.6 节", "—"],
        ],
        widths=[3.6, 1.3, 7.4, 2.3, 2.4],
        size=8.2,
        caption="表 1-4　文件索引。行数是本文档构建时的真实值，改动代码后可能小幅变化",
    )

    k.h2("1.5　T0：先跑通自检（不需要 GPU、不需要数据）")
    k.p(
        "在写任何模型代码、下载任何数据之前，先跑这一个命令。它只依赖 numpy/pandas，"
        "在本机上几秒钟出结果，验证的是最难靠肉眼发现问题的那部分代码：指标函数和划分器。",
        after=4,
    )
    k.code(
        "cd melanoma_calib\npython tests/test_all.py",
        title="终端",
    )
    k.p("预期输出（节选，最后一行必须是 all checks passed）：", after=2)
    k.code(
        "[PASS] auroc perfect separation == 1.0 1.0000\n"
        "[PASS] auroc tie handling 0.8750\n"
        "[PASS] auprc constant == prevalence 0.0212\n"
        "[PASS] ece ~0 for calibrated model 0.0017\n"
        "[PASS] ece_pos penalises under-confident positives 0.500\n"
        "[PASS] sens@spec80 threshold lands on the negative quantile thr=0.792\n"
        "[PASS] calibration slope ~1 for calibrated probabilities slope=0.996\n"
        "[PASS] temperature recovers the sharpening factor T=3.02\n"
        "[PASS] split sizes close to 70/10/20 train=0.700 test=0.200\n"
        "[PASS] prevalence preserved in every split (3 sigma) ... test=0.0270\n"
        "[PASS] a single patient lives in exactly one split\n"
        "[PASS] paired difference CI is ordered 0.123 [0.083, 0.154]\n"
        "\n"
        "all checks passed",
        title="预期 stdout（本机真实运行结果）",
    )
    k.p("这 25 项不是装饰。每一项都对应一个「写错了但看起来很正常」的 bug：", after=6)
    k.table(
        ["自检项", "在防什么", "写错时的症状"],
        [
            ["`auroc tie handling`", "并列分数只能用平均秩（mid-rank）", "AUROC 偏高 0.01–0.05，且随分数离散程度变化"],
            ["`auprc constant == prevalence`", "常数预测器的 AP 必须等于患病率", "AUPRC 被算成 0.5 量级，模型看起来「还行」"],
            ["`ece ~0 for calibrated model`", "ECE 实现与分箱口径", "校准良好的模型报出 0.1 以上的 ECE"],
            ["`ece_pos penalises ...`", "只在真恶性上算 ECE 的分支", "「躺平模型」在 ECE_pos 上意外好看"],
            ["`sens@spec80 threshold ...`", "把 80% 特异度的阈值写成 20 分位（经典错法）", "敏感度凭空高 40 个点"],
            ["`calibration slope ~1`", "IRLS 拟合的正确性", "斜率恒为 ±0.3 之类的怪值"],
            ["`temperature recovers ...`", "温度网格搜索的尺度（log 空间）", "T 收敛到边界，ECE 越修越差"],
            ["`prevalence preserved ...`", "分层是否真的保住患病率", "验证集里一个恶性都没有，第十周才发现"],
            ["`paired difference CI is ordered`", "bootstrap 的配对与分位数", "差值的 CI 不含点估计"],
        ],
        widths=[4.4, 6.6, 5.4],
        size=8.2,
        caption="表 1-5　自检项与它们防范的错误。每一项失败都意味着报告里的某张表不能信",
    )
    k.check(
        "命令返回 0、末尾打印 `all checks passed`。如果失败，先修代码再看数据——"
        "带着一个坏的指标函数跑 5 个小时 GPU，是所有浪费里最贵的一种。"
    )
    k.page_break()


# ----------------------------------------------------------------- chapter 2
def ch2(k):
    k.h1("2", "Day 1：环境与数据")

    k.p(
        "这一章的目标很小：让 `python tools/inspect_data.py` 在真实数据上跑通、并且输出「no blocking problem found」。"
        "做完之后，你手里有一个约 3 GB 的 256 px 图像目录、一份 `train.csv`，以及一份体检报告。"
    )
    k.tip(
        "如果你自己的机器有 ≥6 GB 显存的 NVIDIA 显卡（例如 RTX 2060 6 GB），"
        "可以完全跳过 Colab，整套流程在本机跑：见配套文档 `6018_Local_Guide.docx`。"
        "方法、指标、实验矩阵完全相同，差别只是路径、batch 与电源设置。"
    )

    k.h2("2.1　两台机器：本机写代码，Colab 烧 GPU")
    k.p(
        "把「开发」和「训练」分开，是免费算力下最重要的工程决定。"
        "代码在本机改、在本机跑自检、在本机画图；Colab 只负责 `train.py` 与 `evaluate.py`，"
        "而且每次开机都从零开始（`/content` 会被清空）。",
        after=6,
    )
    k.table(
        ["资源", "实际可用", "对设计的影响"],
        [
            ["GPU", "Tesla T4 16 GB，单卡", "B3@256 batch 32 刚好；384² 只能 batch 12–16"],
            ["会话时长", "连续计算约 4 小时会被断（不提示）", "每个 epoch 必须落盘；一条命令只跑一个实验"],
            ["配额", "每天数小时，用完当天不再给卡", "总预算按 10–15 GPU·小时/周 规划（附录 C 只需 5.8）"],
            ["磁盘", "`/content` 约 70–80 GB，会话结束即清空", "数据放 `/content`，checkpoint 放 Drive"],
            ["Drive", "15 GB 免费", "只放 checkpoint、日志、预测 CSV，不放原图"],
        ],
        widths=[2.0, 6.2, 8.2],
        size=8.4,
        caption="表 2-1　Colab 免费版的现实约束。所有后续设计都是从这里倒推的",
    )
    k.tip(
        "把 `--out-dir` 指向 `/content/drive/MyDrive/runs/<实验名>`。这样断线最多损失一个 epoch，"
        "重连后一条 `--resume` 命令就能接上。这一条决定你们能不能按时交报告。"
    )

    k.h2("2.2　本机环境")
    k.p("先建一个独立环境（3.10–3.12 都行），再装依赖。`requirements.txt` 全文如下：", after=2)
    k.code(
        "torch>=2.1\n"
        "torchvision>=0.16\n"
        "timm==1.0.9\n"
        "pandas>=2.0\n"
        "numpy>=1.24\n"
        "matplotlib>=3.7\n"
        "Pillow>=10.0",
        title="requirements.txt",
    )
    k.code(
        "# 1) 建环境\n"
        "conda create -n isic python=3.11 -y && conda activate isic\n"
        "\n"
        "# 2) 装依赖（CPU 版 torch 就够本机开发；Colab 上不装 torch）\n"
        "pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu\n"
        "\n"
        "# 3) 验证\n"
        "python -c \"import torch, timm, pandas, matplotlib; print(torch.__version__, timm.__version__)\"\n"
        "\n"
        "# 4) 自检（25 项，几秒钟）\n"
        "python tests/test_all.py",
        title="终端 · 本机",
    )
    k.warn(
        "`timm` 必须锁版本。`timm` 在 1.x 之间改过预训练权重的接口与默认 `drop_path_rate` 行为，"
        "不锁版本会出现「同一份代码昨天 AUROC 0.89、今天 0.87」这种找不到原因的结果漂移。"
        "如果必须升级，先跑 `python tests/test_all.py`（指标不受影响）再跑一次冒烟测试（第 7.4 节）。"
    )

    k.h2("2.3　Colab 环境")
    k.p(
        "Colab 自带 torch 与 pandas，只需要补 `timm`，然后挂载 Drive 让输出能落地。"
        "下面三个单元是每次新会话的固定开场，建议存成 Colab 的「代码片段」。",
        after=4,
    )
    k.code(
        "# 单元 1：依赖 + 挂载 Drive\n"
        "!pip -q install \"timm==1.0.9\"\n"
        "from google.colab import drive\n"
        "drive.mount('/content/drive')\n"
        "\n"
        "# 单元 2：把代码放到 Colab（二选一）\n"
        "# A. 从 Drive 用（改一次代码全组同步）\n"
        "!cp -r /content/drive/MyDrive/melanoma_calib /content/melanoma_calib\n"
        "# B. 或从仓库拉（需要版本记录时用）\n"
        "# !git clone https://github.com/<你们>/melanoma_calib.git /content/melanoma_calib\n"
        "\n"
        "%cd /content/melanoma_calib\n"
        "import sys; sys.path.insert(0, 'src')\n"
        "!python tests/test_all.py        # 必须 all checks passed\n"
        "\n"
        "# 单元 3：确认 GPU（不依赖 nvidia-smi，CPU 运行时也能给出结论）\n"
        "import torch\n"
        "print(\"cuda available:\", torch.cuda.is_available(),\n"
        "      torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU runtime\")",
        title="Colab · 每次新会话的固定开场",
    )
    k.warn(
        "单元 3 打印 `cuda available: False`，说明这次会话是**CPU 运行时**："
        "训练会退回 CPU，B3@256 一个 epoch 要几十分钟，还没跑完就被断。"
        "改法：「运行时 → 更改运行时类型 → 硬件加速器: T4 GPU → 保存」，会话会重启，重装的包要重跑单元 1。",
        extra="首先看这一行",
    )
    k.warn(
        "另一种更常见的情况：`!nvidia-smi` 在笔记本单元里报 `command not found`。"
        "原因只有两个——① 这次真的是 CPU 运行时（T4 镜像一定有 `nvidia-smi`）；"
        "② 你把 `!` 前缀抄进了 Colab 左侧的「终端」（或任何 Bash）：`!` 只是 **notebook 单元**的写法，"
        "终端里要直接敲 `nvidia-smi`，`!nvidia-smi` 在 bash 里会去找一个名字带感叹号的程序。",
        extra="nvidia-smi: command not found",
    )
    k.why(
        "为什么把代码放在 `/content` 而不是直接在 Drive 里跑训练？"
        "Drive 是网络盘，随机读取小文件（DataLoader 每张图一次）会慢 5–10 倍，"
        "而 `/content` 是本地 SSD。所以代码和数据都复制到 `/content`，只有输出写 Drive。"
    )

    k.h2("2.4　取数据：两条路线")
    k.p(
        "ISIC 2020 的原始图像是 1024×1024 的 JPEG，全部约 30 GB；而你们的训练裁剪是 256×256。"
        "在免费 T4 上，每次用 1024 的图解码、再缩到 256，会把一半时间花在解码上。所以先离线缩到 256。"
    )

    k.h3("路线 A（推荐）：下官方原图，本地缩到 256")
    k.p("登录 Kaggle → 比赛页 `siim-isic-melanoma-classification` → 点 Accept Rules → 下载训练集。", after=4)
    k.p(
        "先分清 Kaggle 现在发的两种凭证，混用是这里最常见的失败原因：",
        after=4,
    )
    k.table(
        ["凭证", "长相", "该放哪", "怎么来"],
        [
            ["**新式 API token**（推荐）", "一行字符串，`KGAT_` 开头",
             "环境变量 `KAGGLE_API_TOKEN`，或文件 `~/.kaggle/access_token`",
             "kaggle.com/settings/api → Generate New Token"],
            ["旧式 kaggle.json", "JSON：`{\"username\": ..., \"key\": ...}`",
             "`~/.kaggle/kaggle.json`（`chmod 600`）", "同一页面的 Legacy API Credentials → Create Legacy API Key"],
        ],
        widths=[3.4, 4.4, 5.2, 4.6],
        size=8.3,
        caption="表 2-2　两种 Kaggle 凭证。把 `KGAT_...` 存成 `kaggle.json` 是错的——那个文件名只认 JSON",
    )
    k.code(
        "# 1) Kaggle CLI（新版 Colab 镜像不预装）\n"
        "!pip -q install kaggle\n"
        "\n"
        "# 2) 凭证：只做一次，把 KGAT_ 令牌存进 Drive（不要写进 notebook 源码）\n"
        "import os, pathlib\n"
        "from google.colab import drive\n"
        "drive.mount('/content/drive')\n"
        "from getpass import getpass\n"
        "p = pathlib.Path('/content/drive/MyDrive/.kaggle/access_token')\n"
        "p.parent.mkdir(parents=True, exist_ok=True)\n"
        "p.write_text(getpass('粘贴 Kaggle API token (KGAT_...): ').strip())\n"
        "p.chmod(0o600)\n"
        "\n"
        "# 3) 每次新会话：从 Drive 取回，同时写文件 + 设环境变量\n"
        "tok = pathlib.Path('/content/drive/MyDrive/.kaggle/access_token').read_text().strip()\n"
        "assert tok.isascii() and ' ' not in tok, f'令牌里有非 ASCII 字符：{repr(tok[:20])}'\n"
        "os.makedirs('/root/.kaggle', exist_ok=True)\n"
        "pathlib.Path('/root/.kaggle/access_token').write_text(tok)\n"
        "os.chmod('/root/.kaggle/access_token', 0o600)\n"
        "os.environ['KAGGLE_API_TOKEN'] = tok\n"
        "print('token ok:', tok[:5], 'len', len(tok))\n"
        "\n"
        "# 4) 验证（能列出比赛就说明凭证生效）\n"
        "!kaggle competitions list | head -3",
        title="Colab · 凭证（新式 KGAT_ 令牌）",
    )
    k.warn(
        "`UnicodeEncodeError: 'latin-1' codec can't encode characters` 是在发请求前就崩了，"
        "和账号无关：HTTP 头只接受 ASCII，说明你存进去的「令牌」里混了中文或全角字符"
        "（常见于从双语页面复制、把 `API Token：` 这类标签一起粘进来，或写了中文备注）。"
        "修法：`re.sub(r'[^A-Za-z0-9_]', '', raw)` 清洗后回写，并断言 `tok.isascii()`。"
        "`getpass` 是隐藏回显的，粘错了完全看不出来——所以校验必须写进代码。",
        extra="令牌里混进中文",
    )
    k.p(
        "更省事的做法：用 **Colab 密钥（Secrets）**，令牌永远不经过剪贴板粘贴、也不进 notebook 源码。"
        "左侧 🔑 → 添加密钥，名称 `KAGGLE_API_TOKEN`、值粘 `KGAT_…`，打开「笔记本访问权限」，然后只要两行：",
        after=4,
    )
    k.code(
        "import os\n"
        "from google.colab import userdata\n"
        "os.environ['KAGGLE_API_TOKEN'] = userdata.get('KAGGLE_API_TOKEN')   # 名字要和密钥面板一致\n"
        "!kaggle competitions list | head -3",
        title="Colab · 密钥（推荐，尤其是共享 notebook 时）",
    )
    k.code(
        "# 如果你只有旧式 kaggle.json（{\"username\":..,\"key\":..}）\n"
        "from google.colab import files\n"
        "files.upload()                                  # 选 kaggle.json，落在当前工作目录\n"
        "!ls -l kaggle.json                              # 先确认它真的在这里\n"
        "!mkdir -p /root/.kaggle && cp kaggle.json /root/.kaggle/kaggle.json && \\\n"
        " chmod 600 /root/.kaggle/kaggle.json",
        title="Colab · 凭证（旧式 kaggle.json）",
    )
    k.code(
        "# 5) 下 30 GB 原图 + 元数据（Colab 上约 10–20 分钟）\n"
        "!mkdir -p /content/data\n"
        "!kaggle competitions download -c siim-isic-melanoma-classification \\\n"
        "    -f train.csv -p /content/data\n"
        "!kaggle datasets download -d cdeotte/melanoma-1024x1024 -p /content/data --unzip\n"
        "\n"
        "# 6) 一次性缩放到 256（本机或 Colab 都行；约 3 GB 输出，可断点重跑）\n"
        "#    先确认三件事都在，否则会报 can't open file / No such file\n"
        "import os\n"
        "print(os.getcwd())                                  # 应该是 /content/melanoma_calib\n"
        "print(os.path.exists('/content/data/train'))        # 1024 px 原图目录\n"
        "assert os.path.exists('tools/resize_images.py'), '工作目录不对：先 %cd /content/melanoma_calib'\n"
        "\n"
        "!python tools/resize_images.py \\\n"
        "    --src /content/data/train --dst /content/data/train_256 --size 256",
        title="终端 · 取数据",
    )
    k.warn(
        "`!python tools/...` 是**相对路径**，只在工作目录是仓库根目录时成立。"
        "改运行时类型、断线重连、`Runtime → Restart` 之后，`/content` 会被清空、工作目录回到 `/content`，"
        "于是第 6 步就报 `can't open file '/content/tools/resize_images.py'`。"
        "重启后的固定动作只有四行：挂载 Drive → `!cp -r` 仓库到 `/content` → `%cd /content/melanoma_calib` → `!pwd` 确认。"
        "也可以不用整个仓库，只上传这一个脚本，用绝对路径调用（见下）。",
        extra="重启之后 tools/ 不见了",
    )
    k.warn(
        "令牌等价于账号密码：不要贴进 notebook 源码、不要 `git add`。仓库里一旦出现 "
        "`.kaggle/` 目录，先在 `.gitignore` 里加一行 `.kaggle/`；已经推送过就当场到 "
        "kaggle.com/settings/api 撤销并重新生成。"
    )
    k.p(
        "第 5 步的数据集名（`cdeotte/melanoma-1024x1024`）是社区整理的 1024 px 打包版，"
        "Kaggle 上可能改名或下线；如果 404，就在 Kaggle 搜索 `melanoma 1024` 找等价包，"
        "或直接用比赛页的 `jpeg-melanoma-1024x1024` 资源。**先用网页打开确认存在，再复制命令。**",
        size=10,
    )
    k.warn(
        "解压后的层级不一定正好是 `/content/data/train`：社区包的 zip 里可能多套一层"
        "（`data/train`、`jpeg-melanoma-1024x1024/train`），也可能把 33k 张图直接铺在 `-p` 目录下。"
        "第 6 步报 `no *.jpg files under /content/data/train` 时，先看清真实的层级再改 `--src`：",
        extra="路径对不上",
    )
    k.code(
        "!find /content/data -maxdepth 3 -type d | head -20      # 目录长什么样\n"
        "!find /content/data -name '*.jpg' | head -3             # 图到底在哪\n"
        "!du -sh /content/data/*                                 # 每份多大（30 GB 的才是原图）",
        title="终端 · 找不到图时先查这三行",
    )

    k.h3("路线 B：直接下社区整理好的 256 px 版本")
    k.p(
        "Kaggle 上有多个 256×256 的预处理版本（例如 Chris Deotte 公开的 256 px 打包），"
        "体积约 3–4 GB，省掉缩放这一步。要点是**只用它的图像**：元数据仍用官方 `train.csv`，"
        "否则 `image_name` 的命名规则可能对不上 manifest。",
        after=4,
    )
    k.code(
        "kaggle datasets download -d cdeotte/jpeg-melanoma-256x256 -p /content/data --unzip\n"
        "kaggle competitions download -c siim-isic-melanoma-classification -f train.csv -p /content/data\n"
        "\n"
        "# 对齐检查：CSV 里的 image_name 必须能在图像目录里找到同名 jpg\n"
        "python - <<'PY'\n"
        "import glob, os, pandas as pd\n"
        "df = pd.read_csv('/content/data/train.csv')\n"
        "files = {os.path.splitext(os.path.basename(p))[0] for p in\n"
        "         glob.glob('/content/data/jpeg-melanoma-256x256/train/*.jpg')}\n"
        "missing = [n for n in df.image_name.head(500) if n not in files]\n"
        "print('csv rows', len(df), 'files', len(files), 'missing in first 500:', len(missing))\n"
        "PY",
        title="终端 · 路线 B",
    )
    k.warn(
        "不要混用来源。不同打包版本的 `image_name` 规则不同（是否带 `.jpg`、是否重命名），"
        "混用会让 manifest 与图像错位，症状是 AUROC 掉到 0.6–0.7 而代码毫无报错。"
        "路线 A 与 B 任选一条，从头走到底。"
    )

    k.h3("目录结构（动手前先对齐）")
    k.code(
        "melanoma_calib/\n"
        "  data/\n"
        "    train.csv                 # 官方元数据（33,126 行）\n"
        "    train_256/                # 256 px 图像，文件名 = image_name + .jpg\n"
        "  manifests/                  # 划分清单（第 3 章产出）\n"
        "  runs/                       # 每个实验一个子目录（第 7 章产出）\n"
        "  results/  figures/          # 表格与图（第 9–10 章产出）\n"
        "  src/  tests/  tools/",
        title="目录约定",
    )

    k.h2("2.5　数据体检：八个问题")
    k.p(
        "`tools/inspect_data.py` 把「数据到底对不对」拆成八个可以一眼回答的问题，"
        "并且在发现阻断性问题时以非零码退出（这样它可以被 `&&` 串在流水线前面）。"
        "它不是可选的：错位的图像目录能让 AUROC 掉 20 个点，而训练日志一切正常。",
        after=4,
    )
    k.excerpt("tools/inspect_data.py", "main", title="tools/inspect_data.py · main()")
    k.code(
        "python tools/inspect_data.py \\\n"
        "    --csv data/train.csv \\\n"
        "    --img-dir data/train_256",
        title="终端",
    )
    k.p("在真实数据上，你应该看到这样的结构（数值是真实量级）：", after=2)
    k.code(
        "file      : data/train.csv\n"
        "shape     : 33126 rows x 50 columns\n"
        "label     : 584 positive / 33126 -> prevalence 0.0176 (1:56.7)\n"
        "patients  : 2056  (16.1 images/patient on average)\n"
        "images/pt : median 8  p90 45  p99 180  max 400+\n"
        "lesions   : 3897\n"
        "duplicates: 0 duplicated image_name values\n"
        "missing   : age_approx                         6.0%\n"
        "missing   : sex                                8.0%\n"
        "missing   : anatom_site_general_challenge     10.0%\n"
        "label-shaped columns present (use NONE of them): 21\n"
        "images    : 33126 files under data/train_256 (*.jpg)\n"
        "probe     : 200/200 of the first 200 names resolve to a file\n"
        "\n"
        "[ok] no blocking problem found",
        title="预期输出（真实数据，数值会略有出入）",
    )
    k.table(
        ["问题", "为什么它决定项目能不能做", "不通过时怎么办"],
        [
            ["行数是不是 33,126", "与提案的数字对齐；少一个数量级说明下错了分区", "重下官方 `train.csv`"],
            ["阳性是不是 584、患病率 1.76%", "这是所有设计的基准", "检查 `target` 是否被读成字符串或被重命名"],
            ["患者数是不是 2,056", "患者级划分的前提；缺 `patient_id` 就只能退到图像级", "确认下的是 2020 版而非 2019 版"],
            ["每患者图像数的尾部", "有患者带几百张随访图，决定了划分器要有「交换修复」", "无需处理，记在心里（第 3.3 节）"],
            ["lesion_id 是否跨患者", "跨患者的 lesion 意味着清洗有问题，会污染分组", "报给助教，或改用 patient_id 作唯一切分单位"],
            ["`image_name` 是否重复", "bootstrap 按行重采样，重复行会让 CI 偏窄", "去重，并在报告里说明"],
            ["三个元数据列的缺失率", "缺失率决定「年龄缺失」这一维是否有意义", ">40% 时把元数据条件降为附录实验"],
            ["标签派生列是否被引用", "`diagnosis`/`tbp_lv_*` 一旦进模型，结论作废", "`data.py` 已经拒绝；确认没有自己加回来"],
        ],
        widths=[4.2, 7.4, 4.8],
        size=8.2,
        caption="表 2-3　体检的八个问题。前三个是硬门槛，后五个决定你怎么写 Methods",
    )
    k.check(
        "`inspect_data.py` 打印 `[ok] no blocking problem found`；"
        "记下四个数字（行数、阳性数、患者数、每患者图像中位数）——它们会原样出现在报告的 Data 一段。"
    )

    k.h2("2.6　没有数据时怎么继续开发")
    k.p(
        "数据下载经常要等（Kaggle 有每日配额、Colab 磁盘也可能不够）。在这期间不要空等："
        "`tools/make_synthetic.py` 会生成一份行数、患者数、阳性数都与真实数据相同的**假** `train.csv`，"
        "可以在没有一张图片的情况下把第 3 章（划分）和第 9 章（统计）全部跑通。",
        after=4,
    )
    k.code(
        "python tools/make_synthetic.py --out data_synth/train.csv\n"
        "# 33126 rows, 2056 patients, 584 melanomas (0.0176) -> data_synth/train.csv\n"
        "\n"
        "python src/split.py --csv data_synth/train.csv --out manifests/synth_split.csv\n"
        "python tools/inspect_data.py --csv data_synth/train.csv",
        title="终端 · 无数据演练",
    )
    k.why(
        "注意假数据只有标签和元数据、没有图像，所以它能验证划分器、指标、bootstrap 和报告流程，"
        "不能验证 `data.py` 与训练循环。它的用途是「把不依赖图像的部分提前做完」，"
        "绝不能用它的数字写报告。"
    )

    k.h2("2.7　常见环境故障")
    k.table(
        ["症状", "原因", "处理"],
        [
            ["`ModuleNotFoundError: timm`", "Colab 重连后 pip 装的包没了", "重跑单元 1；把 pip 装包写进第一个单元"],
            ["`nvidia-smi: command not found`", "这次会话是 CPU 运行时；或把 `!` 前缀抄进了 Bash 终端",
             "「运行时 → 更改运行时类型 → T4 GPU」；终端里直接敲 `nvidia-smi`"],
            ["`cuda available: False`", "同上，运行时类型是 None", "改运行时类型后必须重启会话，再重跑单元 1"],
            ["`cp: cannot stat 'kaggle.json'`", "文件在你本机，不在 Colab 虚拟机上；或上次会话上传的已随运行时清空；或 `%cd` 后工作目录变了",
             "用绝对路径 `/root/.kaggle/...`；凭证按 2.4 存进 Drive，每次会话取回"],
            ["`kaggle: command not found`", "CLI 未安装（新版镜像不预装）", "`!pip -q install kaggle`"],
            ["`403 Forbidden` / `401 Unauthorized`", "没在比赛页 Accept Rules；或 `KGAT_` 令牌被存成了 `kaggle.json`",
             "网页上 Join 比赛；令牌放 `~/.kaggle/access_token` 或 `KAGGLE_API_TOKEN`"],
            ["`can't open file '/content/tools/...'`", "工作目录不是仓库根目录（重启/改运行时后 `/content` 被清空）",
             "`%cd /content/melanoma_calib` 或改用绝对路径 `!python /content/melanoma_calib/tools/...`"],
            ["`no *.jpg files under /content/data/train`", "解压层级不同、`-p` 用了相对路径、或重启后数据被清空",
             "`!find /content/data -name '*.jpg' | head` 定位真实目录，再改 `--src` 或重新下载"],
            ["`UnicodeEncodeError: 'latin-1' codec ...`", "令牌字符串里混进了中文/全角字符（HTTP 头只收 ASCII）",
             "`re.sub(r'[^A-Za-z0-9_]', '', raw)` 清洗 + 断言 `tok.isascii()`；或改用 Colab 密钥"],
            ["`libGL.so.1: cannot open shared object`", "headless 环境缺 OpenCV 依赖（用到 cv2 时）", "`apt-get -y install libgl1`"],
            ["下载后 `train.csv` 只有几十行", "下成了 sample_submission", "确认文件名与行数（33,126）"],
            ["`CUDA out of memory`", "batch 太大或旧进程占着显存", "`--batch-size 16`；或「运行时 → 重启运行时」"],
            ["Drive 里看不到输出", "`--out-dir` 写到了 `/content/...` 而不是 `/content/drive/...`", "检查路径前缀，重跑一个 epoch 即可"],
            ["`OSError: image file is truncated`", "下载中断的坏图", "`resize_images.py` 会跳过并计数，把 failed 列表报出来"],
            ["本机 `pip install torch` 卡住", "在下 2 GB 的 CUDA 版", "本机用 `--extra-index-url .../whl/cpu`，只装 CPU 版"],
        ],
        widths=[4.6, 5.6, 6.2],
        size=8.2,
        caption="表 2-4　Day 1 最可能遇到的故障",
    )
    k.page_break()


# ----------------------------------------------------------------- chapter 3
def ch3(k):
    k.h1("3", "T1　患者级划分：把最容易骗人的一步做对")

    k.h2("3.1　【做什么】")
    k.p(
        "输入官方的 `train.csv`（33,126 行），输出一份 `manifests/split_seed42.csv`："
        "每行多一个 `split` 列（train/val/test），并保证同一个患者的所有图像落在同一个划分里。"
        "同时输出一份 `_report.json`，记录校验统计与文件的 sha256。此后**再也不重新划分**。"
    )

    k.h2("3.2　为什么图像级划分会让 AUROC 虚高")
    k.p(
        "33,126 张图来自 2,056 名患者，平均每人 16 张，分布极度重尾（有人带几百张随访图）。"
        "同一患者的皮损在颜色、毛发、拍摄设备上高度相似。如果随机按图 8:2 切，"
        "同一个人的痣会同时出现在训练集和测试集里，模型只要认出「这个人的皮肤纹理」就能答对——"
        "AUROC 通常虚高 3–8 个点，而且这个偏差**不会在任何日志里报警**。"
    )
    k.p(
        "ISIC 2020 之所以值得做，正是因为它是第一批显式提供 `patient_id` 的皮肤镜数据集，"
        "让患者级划分成为可能。提案把这一点写进动机是对的，但必须真的执行到代码里——"
        "而这恰恰是最容易被 `train_test_split(df)` 一行毁掉的地方。"
    )

    k.h2("3.3　算法：贪心分配 + 交换修复")
    k.p(
        "划分器分成两个阶段。第一阶段把患者按种子随机排序，逐个放进「图像数相对亏空 + 恶性例数相对亏空」之和最大的划分；"
        "第二阶段在划分之间做局部搜索（移动一个患者，或交换两个患者），只接受让目标函数下降的改动。",
        after=6,
    )
    k.table(
        ["阶段", "做什么", "保证什么", "单独用会怎样"],
        [
            ["① 贪心", "按种子顺序，逐患者放入相对亏空最大的划分", "患者不交叉、结果由种子唯一确定",
             "由于恶性标签集中在少数患者、图像数重尾，患病率会漂移几十个百分点（实测 test 从 1.76% 掉到 0.56%）"],
            ["② 修复", "随机尝试「移动 / 交换」，接受使目标函数下降的改动", "三个划分的图像占比与恶性占比同时贴近目标",
             "—（这是修复阶段存在的理由）"],
        ],
        widths=[1.6, 5.6, 4.6, 6.4],
        size=8.3,
        caption="表 3-1　两阶段划分器。目标函数 = Σ_s [(图像占比偏差)² + (恶性占比偏差)²]",
    )
    k.why(
        "为什么不直接用 `GroupShuffleSplit`？它只保证患者不交叉，不保证患病率——"
        "在 1.76% 的患病率下，一次不走运的分组就能让验证集里一个恶性都没有，而你要到第十周才发现。"
        "为什么不直接用 `StratifiedGroupKFold`？它能兼顾两者，但只支持等分折数，"
        "想要 70/10/20 就得手工映射，且 5 折 CV 时无法指定比例。两阶段版本两者都要，且行为可解释。"
    )

    k.h2("3.4　【代码】split.py")
    k.p("先看数据结构：每个患者一行统计量。", after=2)
    k.excerpt("split.py", "_patient_stats")

    k.p("核心分配函数（贪心 + 修复）。目标函数用「相对偏差的平方和」，因为它同时惩罚图像占比与恶性占比，"
          "并且对大小划分一视同仁。", after=2)
    k.excerpt("split.py", "_assign")

    k.p("入口函数负责兜底脏数据（缺 `patient_id` 的行各自变成独立伪患者，永远不会跨界）。", after=2)
    k.excerpt("split.py", "build_manifest")

    k.p("校验函数把「不能用肉眼确认的事」写成断言，并把患病率偏差如实打印出来而不是偷偷修掉。", after=2)
    k.excerpt("split.py", "validate")

    k.h2("3.5　【怎么做】生成并冻结 manifest")
    k.code(
        "python src/split.py \\\n"
        "    --csv data/train.csv \\\n"
        "    --out manifests/split_seed42.csv \\\n"
        "    --seed 42",
        title="终端",
    )
    k.p("预期输出（下面是同规模假数据上的真实运行结果；你们的真实数据形状相同、数值略有出入）：", after=2)
    k.code(
        "        images  patients  melanomas  prevalence\n"
        "train  22784.0    1581.0      385.0      0.0169\n"
        "val     3304.0     287.0       85.0      0.0257\n"
        "test    7038.0     188.0      114.0      0.0162\n"
        "prevalence rel. dev: train -4.1%  val +45.8%  test -8.1%\n"
        "lesions spanning splits: 0   duplicate image names: 0\n"
        "\n"
        "manifest -> manifests/split_seed42.csv\n"
        "sha256   -> 7703ba50627b4e45ce2f5f6213e099317fee89619acb159dd6f234d493409f69\n"
        "Freeze this hash in the report; any number without it is not reproducible.",
        title="预期 stdout",
    )
    k.warn(
        "验证集出现 +45.8% 的患病率偏差是**正常且不可消除**的：切分单位是「一个带任意张图的患者」，"
        "想让阳性数精确等于 58 就必须把患者拆开。正确做法是把它写进报告"
        "（「val prevalence 2.6% vs 1.76% global, a patient-level constraint」），"
        "而不是换个种子直到数字好看——那是用测试集调参的同构错误。"
    )

    k.h2("3.6　【检查点】三条断言 + 一次目检")
    k.p("`validate()` 已经把这些写成断言（失败会直接抛异常，训练跑不起来）。你要理解每条在防什么：", after=6)
    k.table(
        ["断言", "在防什么", "失败说明"],
        [
            ["三段患者集合两两不相交", "患者级泄漏（最直接的一条）", "划分器有 bug，或 `patient_id` 被改写"],
            ["`lesion_id` 不跨划分", "同一皮损的多张随访图分到两边（比患者泄漏更隐蔽）", "数据清洗有问题，需上报"],
            ["`image_name` 无重复", "bootstrap 按行重采样时重复计入，CI 偏窄", "CSV 合并时产生了重复行"],
        ],
        widths=[4.6, 7.2, 4.6],
        size=8.4,
        caption="表 3-2　三条硬断言",
    )
    k.p(
        "另外做一次便宜的目检：从测试集随机抽 12 张图看一眼，确认它们确实是皮肤镜照片，"
        "而不是临床照片或病理切片。ISIC 2020 混入过少量异常图像，这类样本对任何模型都是噪声。",
    )
    k.p("最后，把哈希写进两个地方。这一句话能一次性挡掉「结果不可复现」的质疑：", after=2)
    k.code(
        "The split manifest (sha256 7703ba5...) is released with the code; all experiments\n"
        "in this report use it unchanged.",
        title="报告 Methods 里的写法",
    )
    k.check(
        "`manifests/split_seed42.csv` 与 `split_seed42_report.json` 都已生成；"
        "sha256 同时出现在 `README.md` 和报告 Methods；三条断言全过；抽看 12 张测试图正常。"
    )
    k.page_break()


# ----------------------------------------------------------------- chapter 4
def ch4(k):
    k.h1("4", "T2　数据管道：增强、元数据与吞吐")

    k.h2("4.1　【做什么】")
    k.p(
        "把「一行 manifest + 一张 jpg」变成一个可以直接喂给模型的张量 batch，并且做到三件事："
        "训练增强只作用于训练集；元数据只用三个临床字段；所有统计量只在训练集上拟合并序列化。"
        "代码在 `src/data.py`（162 行），下面按三块讲。"
    )

    k.h2("4.2　增强策略：为什么是这几个")
    k.p(
        "皮肤镜图像没有「正方向」，病灶可以出现在任意位置，所以旋转与上下翻转都是安全的增强；"
        "颜色是最强的判别信号（黑色/深棕色），所以颜色抖动只能轻。"
    )
    k.table(
        ["阶段", "变换", "参数", "理由"],
        [
            ["train", "RandomResizedCrop", "256, scale=(0.75,1.0), ratio=(0.85,1.18)", "模拟不同的拍摄距离与病灶占比"],
            ["train", "水平 / 垂直翻转", "各 0.5", "皮肤镜无正方向，安全且几乎免费"],
            ["train", "RandomRotation", "±20°", "同上；超过 45° 后插值伪影变明显"],
            ["train", "ColorJitter", "0.15 / 0.15 / 0.10 / 0.03", "轻：颜色本身是强特征，抖重了会抹掉关键线索"],
            ["eval", "Resize → CenterCrop", "292 → 256", "先放大再裁，避免把病灶压扁变形"],
            ["both", "Normalize", "ImageNet 均值/方差", "与预训练权重匹配"],
        ],
        widths=[1.4, 3.6, 5.4, 6.4],
        size=8.4,
        caption="表 4-1　增强配置。`build_transforms()` 就是这张表的实现",
    )
    k.warn(
        "不要用 MixUp / CutMix。它们在长尾分类里很常见，但会把预测概率系统性地压向先验，"
        "和你们要研究的「校准」直接冲突——用了之后，任何 ECE 变化都无法归因到损失函数。"
        "这一条写进报告 limitations 就够了。"
    )

    k.h2("4.3　元数据：只用三项，并且显式拒绝其余列")
    k.p(
        "这是最容易出事故的地方。官方 `train.csv` 有 50 多列，其中有一半与标签同义。"
        "一旦把 `diagnosis` 或 `tbp_lv_*` 喂进模型，AUROC 会「变好」，但研究问题就不再是图像模型了。",
        after=6,
    )
    k.table(
        ["列", "能不能用", "原因"],
        [
            ["`age_approx`", "✅ 用", "临床可得，与恶性风险真实相关"],
            ["`sex`", "✅ 用", "临床可得，也便于公平性分层"],
            ["`anatom_site_general_challenge`", "✅ 用", "临床可得，部位与风险相关"],
            ["`diagnosis`", "❌ 禁用", "直接就是标签的诊断名，等于泄漏"],
            ["`melanoma`/`nevus`/`seborrheic_keratosis`", "❌ 禁用", "标签的哑变量编码"],
            ["`tbp_lv_*`（约 20 列）", "❌ 禁用", "全身摄影流程导出的病灶级特征，真实「只来拍一张皮肤镜」场景里拿不到"],
            ["`benign_malignant`", "❌ 禁用", "与 `target` 同义"],
        ],
        widths=[4.6, 2.0, 9.6],
        size=8.4,
        caption="表 4-2　元数据白名单与黑名单。`data.py` 只读白名单三列，等于把黑名单写死在代码里",
    )
    k.p("编码成 13 维向量：", after=2)
    k.code(
        "[age/100, age_missing,                                    # 2\n"
        " sex_male, sex_female, sex_unknown,                       # 3\n"
        " site_torso, site_lower_extremity, site_upper_extremity,\n"
        " site_head_neck, site_palms_soles, site_oral_genital,\n"
        " site_unknown]                                            # 7  -> 共 13 维",
        title="元数据编码（13 维）",
    )
    k.p(
        "两个细节值得在报告里交代：缺失值是信息，所以年龄缺失单独占一维，而不是简单填均值；"
        "年龄中位数只在**训练集**上算，然后序列化成 `meta_encoder.json`，验证/测试集一律用它。"
        "否则验证集的统计量就渗进了训练过程。",
    )

    k.h2("4.4　【代码】data.py")
    k.excerpt("data.py", "MetaEncoder", title="data.py · MetaEncoder（训练集拟合 + JSON 序列化）")
    k.excerpt("data.py", "build_transforms")
    k.excerpt("data.py", "ISICDataset", "make_loader")
    k.p(
        "`ISICDataset` 构造时会探前 200 个文件名，缺文件立即报错——这条看起来多余，"
        "但它把「图像目录错位」这个最常见的故障从「训练 5 小时后发现 AUROC 0.65」变成「启动即失败」。",
    )

    k.h2("4.5　【怎么做】自测一个 batch")
    k.p("在花 GPU 之前，先在 CPU 上确认形状、dtype 和元数据维度都对：", after=2)
    k.code(
        "python - <<'PY'\n"
        "import sys; sys.path.insert(0, 'src')\n"
        "import pandas as pd, torch\n"
        "from data import ISICDataset, MetaEncoder, make_loader\n"
        "\n"
        "man = pd.read_csv('manifests/split_seed42.csv')\n"
        "tr = man[man.split == 'train'].reset_index(drop=True)\n"
        "enc = MetaEncoder().fit(tr)                    # 只在训练集上拟合\n"
        "print('meta dim =', enc.dim)                   # 期望 13\n"
        "\n"
        "ds = ISICDataset(tr.head(32), 'data/train_256', size=256, train=True, meta_encoder=enc)\n"
        "b = next(iter(make_loader(ds, batch_size=8, shuffle=True, workers=0)))\n"
        "print('image', tuple(b['image'].shape), b['image'].dtype)   # (8, 3, 256, 256) float32\n"
        "print('meta ', tuple(b['meta'].shape))                      # (8, 13)\n"
        "print('target', tuple(b['target'].shape), b['target'].dtype)\n"
        "print('image stats', float(b['image'].mean()), float(b['image'].std()))\n"
        "PY",
        title="终端 · 一个 batch 的形状自检",
    )
    k.code(
        "meta dim = 13\n"
        "image (8, 3, 256, 256) torch.float32\n"
        "meta  (8, 13)\n"
        "target (8,) torch.float32\n"
        "image stats -0.12 1.31",
        title="预期输出（ImageNet 归一化后均值≈0、标准差≈1.3）",
    )
    k.check(
        "形状是 `(B,3,256,256)`、`(B,13)`、`(B,)`；归一化后均值在 ±0.3 内、标准差 1.0–1.5；"
        "`meta_encoder.json` 只在 `--meta` 条件下由 `train.py` 写出（第 7 章）。"
    )

    k.h2("4.6　T4 上的吞吐与参数选择")
    k.table(
        ["设置", "取值", "说明"],
        [
            ["`--img-size`", "256", "384 在 T4 上约 2.2 倍耗时，换 0.5–1 点 AUROC，不划算"],
            ["`--batch-size`", "32", "B3@256 占 9–11 GB；OOM 就降到 16（已开梯度裁剪，行为基本不变）"],
            ["`--workers`", "2", "Colab 只有 2 核，设 4 反而更慢"],
            ["`pin_memory`", "True", "`make_loader` 里固定"],
            ["`persistent_workers`", "workers>0 时 True", "每 epoch 省 10–20 秒"],
        ],
        widths=[3.4, 3.0, 9.8],
        size=8.4,
        caption="表 4-3　吞吐参数",
    )
    k.p(
        "实测吞吐约 60–80 张/秒（B3@256、AMP、T4）。训练集 23,188 张 → 每 epoch 约 5–6 分钟，"
        "加每 epoch 一次验证评估（约 20 秒），12 epoch ≈ 70 分钟/次。"
        "这个数字决定了第 7.5 节的实验矩阵（5 次训练 ≈ 5.8 GPU·小时）。",
    )
    k.page_break()


# ----------------------------------------------------------------- chapter 5
def ch5(k):
    k.h1("5", "T3　模型：两个 backbone 加一个小融合头")

    k.h2("5.1　【做什么】")
    k.p(
        "实现一个 `MelanomaNet`：`timm` 提供的 ImageNet 预训练 backbone（EfficientNet-B3 或 ResNet-50），"
        "可选地把 13 维临床元数据经一层 MLP 后与图像特征拼接，输出**单个 logit**。"
        "没有新结构，这是刻意的。"
    )
    k.why(
        "提案原话是「We do not propose a new architecture; we ask whether the evaluation protocol "
        "changes the conclusion」。这句话要贯彻到底：任何一次「要不要换个更强的模型」的讨论都会吃掉一整周配额，"
        "而换来的 AUROC 提升会被 117 个阳性带来的 ±9 点不确定度完全淹没。"
    )

    k.h2("5.2　【代码】models.py（全文 87 行）")
    k.excerpt("models.py", "MetadataEncoder", "MelanomaNet", "build_model",
              title="models.py · 结构与工厂函数")
    k.p(
        "两个设计点值得单独说明：`timm.create_model(..., num_classes=0)` 返回池化后的特征向量，"
        "这样 timm 各版本分类头实现的差异被挡在模块边界外；输出是单 logit 而不是 softmax 两维，"
        "因为 BCE、加权 BCE、focal 全部在 logit 上定义，四个条件共用同一条训练与推理路径，"
        "避免「换损失时顺手改了解码方式」这种混淆。",
    )

    k.h2("5.3　【怎么做】确认参数量与前向")
    k.code(
        "python - <<'PY'\n"
        "import sys; sys.path.insert(0, 'src')\n"
        "import torch\n"
        "from models import build_model, count_params\n"
        "\n"
        "for name, n_meta in [('efficientnet_b3', 0), ('efficientnet_b3', 13),\n"
        "                     ('resnet50', 0)]:\n"
        "    m = build_model(name, n_meta, pretrained=False).eval()\n"
        "    x = torch.randn(2, 3, 256, 256)\n"
        "    meta = torch.randn(2, 13) if n_meta else None\n"
        "    with torch.no_grad():\n"
        "        print(f'{name:16s} n_meta={n_meta:2d} out={tuple(m(x, meta).shape)} {count_params(m)}')\n"
        "PY",
        title="终端 · 参数量与前向形状",
    )
    k.code(
        "efficientnet_b3  n_meta= 0 out=(2,) 11.1M total / 11.1M trainable\n"
        "efficientnet_b3  n_meta=13 out=(2,) 11.1M total / 11.1M trainable\n"
        "resnet50         n_meta= 0 out=(2,) 25.6M total / 25.6M trainable",
        title="预期输出（参数量的量级；融合头只增加约 0.02 M）",
    )
    k.check(
        "三个组合都打印 `out=(2,)`（单 logit，不是 (2,2)）；参数量落在 11.1M / 25.6M 量级（含 1000 类分类头的标准 B3 是 12.2M，我们用 num_classes=0 去掉了它）。"
        "如果 B3 报 5.3M，说明 `timm` 版本把 `num_features` 取错了，后面的 `BatchNorm1d` 会跟着错。"
    )

    k.h2("5.4　显存与耗时")
    k.table(
        ["模型", "参数量", "B3@256 batch 32 显存", "每 epoch（23k 图）", "12 epoch 单次"],
        [
            ["EfficientNet-B3", "≈11.1 M", "9–11 GB", "5–6 min", "≈70 min"],
            ["ResNet-50", "≈25.6 M", "7–9 GB", "3.5–4.5 min", "≈50 min"],
        ],
        widths=[4.0, 2.6, 4.4, 3.4, 3.0],
        size=8.5,
        caption="表 5-1　T4 上的实测区间。B3 参数更少但更慢：它的 depthwise 卷积在 T4 上利用率低",
    )
    k.warn(
        "ResNet-50 参数更多却更快，这不是笔误——EfficientNet 的 depthwise 可分离卷积在小 batch 下访存密集，"
        "在 T4 上算力利用率低。如果配额吃紧，把架构消融留给 R50（它便宜），把 B3 留给主实验。"
    )
    k.page_break()


# ----------------------------------------------------------------- chapter 6
def ch6(k):
    k.h1("6", "T4　三种损失：把「平衡」量化到同一个尺度上")

    k.h2("6.1　【做什么】")
    k.p(
        "实现提案 §3 的三个训练条件，并且让它们共用同一套 logit 接口："
        "（i）标准 BCE；（ii）逆患病率加权 BCE；（iii）focal loss。"
        "额外再加一个（iv）有效样本数加权，作为「中间权重点」，用来支撑「校准损失随权重单调变化」这句结论。"
    )

    k.h2("6.2　【代码】losses.py（全文 95 行）")
    k.excerpt("losses.py", "SigmoidFocalLoss", "effective_number_weights", "build_loss",
              "describe_losses", title="losses.py · 四个条件 + 一张自述表")

    k.h2("6.3　有效权重并排看")
    k.p("打开 `losses.py` 的自述函数，四个条件的正样本权重一目了然：", after=2)
    k.code(
        "python src/losses.py",
        title="终端",
    )
    k.code(
        "n_pos=584  n_neg=32542  pos:neg = 1:55.7\n"
        "  bce     : pos_weight = 1.0\n"
        "  wbce    : pos_weight = 55.72   (inverse prevalence)\n"
        "  cb      : pos_weight = 16.95   (beta=0.9999, effective number)\n"
        "  focal   : alpha=0.75 gamma=2.0  -> implicit pos weight 3.0 vs 1.0 on easy examples\n"
        "\n"
        "bce    -> 0.6931\n"
        "wbce   -> 0.6931\n"
        "cb     -> 0.6931\n"
        "focal  -> 0.1607",
        title="预期输出（本机真实运行结果）",
    )
    k.table(
        ["条件", "有效正权重", "机制", "预期对敏感度", "预期对校准"],
        [
            ["BCE", "1.0", "无干预", "基准", "最好（斜率 0.8–1.1）"],
            ["逆患病率 BCE", "55.7", "每个恶性按 56 个良性计", "↑ 明显", "明显变差，斜率常 < 0.5"],
            ["有效样本数", "17.0", "`(1-β)/(1-β^n)` 归一化", "↑ 中等", "居中"],
            ["Focal (γ=2, α=0.75)", "≈3（对易样本）", "压低易样本梯度", "↑ 中等", "整条曲线下移"],
        ],
        widths=[3.4, 3.2, 5.4, 2.6, 3.2],
        size=8.3,
        caption="表 6-1　四个条件的有效权重大小关系。这张表本身就是「单调性」论证的一半",
    )
    k.p(
        "逆患病率 BCE 把每个恶性样本的权重放大到 55.7 倍。这不是温和的操作："
        "它等价于告诉优化器「漏掉一个恶性，等于错判 56 个良性」。梯度的尺度整体上移，"
        "模型被推向「尽可能输出高概率」，于是概率分布被系统性拉伸到两端——"
        "这正是校准变差的机制，可预测、可展示，不是玄学。",
    )

    k.h2("6.4　focal loss 的两个陷阱")
    k.table(
        ["陷阱", "表现", "本项目的处理"],
        [
            ["α 的方向", "RetinaNet 默认 α=0.25 是**降低**正样本权重；在 1.76% 的数据上这是反的",
             "取 α=0.75，使正样本相对权重约 3:1，同时用 γ=2 抑制 98% 的易负样本"],
            ["γ 会破坏校准，但方向与加权 BCE 不同", "focal 压的是「易样本的梯度」，把概率往「不太确定」推，整条可靠性曲线整体下移",
             "不要在训练后顺手做 sigmoid 裁剪（clip），那会把要观测的效应抹掉"],
        ],
        widths=[3.6, 7.6, 5.2],
        size=8.4,
        caption="表 6-2　focal 的两个陷阱",
    )

    k.h2("6.5　不要做的两件事")
    k.bullets([
        "**不要重采样 + 加权损失叠加。** `--sampler-power` 默认 0（关闭）。"
        "如果同时做 1.0 的过采样又用逆患病率权重，正样本实际权重会被放大到 55.7×(1/0.0176)≈3160 倍，训练会在前 200 步发散。",
        "**不要在训练时调阈值或重标定。** 所有阈值操作都放在评估阶段（第 9 章），并且只在 val 上做一次。",
    ])
    k.check(
        "`python src/losses.py` 输出的四个 `pos_weight` 与表 6-1 一致；"
        "`--loss` 的四个取值（bce / wbce / cb / focal）都能在 CPU 上算出有限 loss。"
    )
    k.page_break()
