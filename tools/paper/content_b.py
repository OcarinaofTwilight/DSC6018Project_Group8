# -*- coding: utf-8 -*-
"""Chapters 7-13 and the appendices."""
from __future__ import annotations


def ch7(k):
    k.h1("7", "T5　训练：让免费 Colab 不成为瓶颈")

    k.h2("7.1　一条命令 = 一个实验 = 一个目录")
    k.p(
        "这个约定看起来死板，但它让「重跑一次」的成本从半天降到两分钟，"
        "也让第十周做图、对数字时不必回头翻 notebook 里的历史输出。"
        "每个 `--out-dir` 里固定出现四个文件，报告里的每个数字都能溯源到它们。",
        after=6,
    )
    k.table(
        ["文件", "内容", "用途"],
        [
            ["`log.csv`", "逐 epoch 的 lr / train_loss / val_auroc / val_auprc / val_sens80 / 耗时 / 是否刷新最优", "画训练曲线、判断过拟合"],
            ["`last.pt`", "最近一个 epoch 的权重 + 优化器状态 + epoch 号 + global_step", "断线续训"],
            ["`best.pt`", "按 `--select-metric`（默认 val AUPRC）最优的权重", "最终评估用"],
            ["`cfg.json`", "完整超参数快照（`vars(args)`）", "写报告 Methods、复现"],
            ["`meta_encoder.json`", "仅 `--meta` 条件：训练集拟合的年龄中位数与类别表", "评估时必须与 ckpt 同目录（第 8.4 节）"],
        ],
        widths=[3.2, 8.0, 5.4],
        size=8.3,
        caption="表 7-1　一个 run 目录的固定内容",
    )
    k.why(
        "为什么用 val AUPRC 而不是 val AUROC 选模型？在 1.76% 的患病率下 AUROC 对多数样本不敏感，"
        "一个「把所有概率都压到 0.02」的模型也能有 0.85 的 AUROC；AUPRC 的随机基线就是患病率 0.0176，"
        "对模型是否真的把恶性排在前面更敏感。代价是 AUPRC 方差更大，所以第 9 章必须配套 bootstrap。"
    )

    k.h2("7.2　命令行参数")
    k.table(
        ["参数", "默认", "说明"],
        [
            ["`--manifest`", "必填", "第 3 章产出的划分清单"],
            ["`--img-dir`", "必填", "256 px 图像目录"],
            ["`--out-dir`", "必填", "**指向 Drive**，否则断线即丢"],
            ["`--model`", "`efficientnet_b3`", "`resnet50` 用于架构消融"],
            ["`--loss`", "`bce`", "`bce` / `wbce` / `cb` / `focal`"],
            ["`--meta`", "关", "拼接 13 维临床元数据"],
            ["`--img-size`", "256", "必须与 evaluate 一致"],
            ["`--epochs`", "12", "B3 在第 8–10 epoch 进入平台"],
            ["`--batch-size`", "32", "OOM 降到 16"],
            ["`--lr`", "3e-4", "AdamW + warmup 5% + cosine"],
            ["`--sampler-power`", "0.0", "0 = 关闭；>0 开启逆频率采样（不要与 wbce 同时用）"],
            ["`--select-metric`", "`val_auprc`", "选 `best.pt` 的依据"],
            ["`--limit-batches`", "0", "只跑 N 个 batch：冒烟测试用（第 7.4 节）"],
            ["`--resume`", "关", "从 `last.pt` 续训（第 7.6 节）"],
            ["`--ext`", "`.jpg`", "图像后缀"],
            ["`--workers`", "2", "Colab 两核"],
            ["`--no-amp`", "关", "调试数值问题时用"],
        ],
        widths=[3.6, 3.2, 9.8],
        size=8.2,
        caption="表 7-2　train.py 的全部参数",
    )

    k.h2("7.3　【代码】train.py")
    k.p("先看两个小工具：种子与学习率调度。", after=2)
    k.excerpt("train.py", "set_seed", "lr_at")
    k.p(
        "学习率是 warmup 5% + cosine 衰减到 0。对免费 Colab 来说这不是调参，而是**断点续训的前提**："
        "`lr_at(global_step, total_steps, base_lr)` 只依赖全局 step，所以续训时学习率自然接上，不会重新 warmup。",
    )
    k.p("每 epoch 的验证只算四个数，够用来选模型，不用于报告：", after=2)
    k.excerpt("train.py", "evaluate_split")
    k.p("主循环。注意三处：`--limit-batches` 同时截断训练与验证；每个 epoch 无条件写 `last.pt`；"
          "只有刷新最优才写 `best.pt`。", after=2)
    k.excerpt("train.py", "main")

    k.h2("7.4　【怎么做】先花两分钟冒烟")
    k.p(
        "`--limit-batches 5` 只跑 5 个 batch 就走完「训练 → 验证 → 存盘 → 续训」全流程。"
        "它抓的是路径写错、OOM、timm 权重下载失败、元数据列名不对这类问题——"
        "这些问题如果等到第 30 分钟才暴露，浪费的是配额，不是时间。",
        after=4,
    )
    k.code(
        "python src/train.py \\\n"
        "    --manifest manifests/split_seed42.csv \\\n"
        "    --img-dir data/train_256 \\\n"
        "    --model efficientnet_b3 --loss bce \\\n"
        "    --epochs 1 --limit-batches 5 \\\n"
        "    --out-dir runs/_smoke",
        title="终端 · 冒烟测试（2 分钟）",
    )
    k.code(
        "n_pos=408  n_neg=22780  pos:neg = 1:55.8\n"
        "  bce     : pos_weight = 1.0\n"
        "  ...\n"
        "efficientnet_b3: 11.1M total / 11.1M trainable\n"
        "epoch 00 loss 0.0612 auroc 0.8712 auprc 0.2084 sens80 0.312 * (41s)\n"
        "done. best val_auprc = 0.2084",
        title="预期输出（5 个 batch 后即结束；数字随初始化变化）",
    )
    k.check(
        "`runs/_smoke/` 下出现 `log.csv`、`last.pt`、`best.pt`、`cfg.json` 四个文件，"
        "并且打印了一行 `epoch 00 ...`。此时再跑一次加 `--resume`，应打印 `resumed at epoch 1` 而不是从头开始。"
    )

    k.h2("7.5　【怎么做】五个实验，覆盖提案的全部消融维度")
    k.p(
        "提案的消融写成「2 backbone × 3 loss × 有/无元数据 = 12 组」，那是约 14 GPU·小时的量。"
        "下面的矩阵用 5 次训练覆盖全部四个维度，因为交叉项不是必需的——你们要回答的是「损失是否改变结论」，"
        "而不是「哪个组合最强」。",
        after=4,
    )
    k.code(
        "# 1) 参照线：标准 BCE\n"
        "python src/train.py --manifest manifests/split_seed42.csv --img-dir data/train_256 \\\n"
        "  --model efficientnet_b3 --loss bce --epochs 12 --batch-size 32 \\\n"
        "  --out-dir /content/drive/MyDrive/runs/b3_bce\n"
        "\n"
        "# 2) 主假设：逆患病率加权\n"
        "python src/train.py ... --loss wbce --out-dir .../runs/b3_wbce\n"
        "\n"
        "# 3) 另一种平衡方式\n"
        "python src/train.py ... --loss focal --out-dir .../runs/b3_focal\n"
        "\n"
        "# 4) 架构消融（最便宜：约 50 分钟）\n"
        "python src/train.py ... --model resnet50 --loss bce --out-dir .../runs/r50_bce\n"
        "\n"
        "# 5) 元数据条件\n"
        "python src/train.py ... --loss bce --meta --out-dir .../runs/b3_bce_meta\n"
        "\n"
        "# 加分项（配额有余时）：有效样本数权重的中间点\n"
        "python src/train.py ... --loss cb --out-dir .../runs/b3_cb",
        title="终端 · 实验矩阵（前五条为必需）",
    )
    k.table(
        ["#", "实验名", "backbone", "损失", "元数据", "耗时", "回答什么问题"],
        [
            ["1", "`b3_bce`", "B3", "BCE", "无", "70 min", "参照线：患者级划分下的真实水平"],
            ["2", "`b3_wbce`", "B3", "逆患病率", "无", "70 min", "主假设：平衡损失提敏感度吗？代价是什么？"],
            ["3", "`b3_focal`", "B3", "Focal", "无", "70 min", "另一种平衡方式是否同样有害"],
            ["4", "`r50_bce`", "R50", "BCE", "无", "50 min", "结论是否依赖 backbone"],
            ["5", "`b3_bce_meta`", "B3", "BCE", "有", "72 min", "临床元数据改善校准吗？"],
            ["6*", "`b3_cb`", "B3", "有效样本数", "无", "70 min", "中间权重点，支撑「单调」叙述"],
        ],
        widths=[0.9, 3.4, 2.0, 2.4, 1.8, 1.8, 5.2],
        size=8.2,
        caption="表 7-3　实验矩阵。1–5 合计约 5.7 GPU·小时；最小可交付集合是 1、2、3（约 3.5 小时）",
    )

    k.h2("7.6　断线之后怎么办")
    k.p("免费 T4 会断，这不是意外，是常态。流程固定成三步，任何人都能接手：", after=4)
    k.steps([
        "重连后先看日志末尾，确认最后一个完成的 epoch：`!tail -3 /content/drive/MyDrive/runs/b3_bce/log.csv`",
        "原命令加 `--resume`。它会从 `last.pt` 读回 epoch 号与优化器状态，学习率按全局 step 继续："
        "`python src/train.py ... --out-dir .../b3_bce --resume`",
        "如果报显存不足或权重文件损坏，删掉 `last.pt` 从头跑。一个实验最多 70 分钟，不值得为它写复杂的异常恢复。",
    ])
    k.tip(
        "每个 Colab 会话只跑一个实验。开跑前把手机计时器设成 65 分钟；回来看到 `done.` 就存盘、换下一个条件。"
        "一天两个会话、两个实验，一周 5–6 个实验刚好覆盖必需矩阵。不要试图在一个会话里连跑两个——"
        "第二个大概率在验证阶段被切断，还占着配额。"
    )

    k.h2("7.7　怎么读 log.csv")
    k.table(
        ["现象", "含义", "动作"],
        [
            ["`val_auprc` 前 3 个 epoch 就在涨，第 5 个后走平", "正常收敛", "让它跑完，用 `best.pt`"],
            ["`train_loss` 持续下降、`val_auroc` 开始下降", "过拟合（23k 张图不算多）", "提前停，报 `best.pt` 的 epoch"],
            ["`train_loss` 一直是 0.69 左右不动", "模型没学到东西：lr 太大或数据错位", "先查 `--limit-batches` 冒烟，再降到 lr 1e-4"],
            ["`val_sens80` 抖动 0.2 以上", "验证集只有 ~60 个阳性，正常", "不要据此调参；最终看 test + bootstrap"],
            ["`train_loss` 出现 NaN", "加权过猛 + lr 太大", "确认没同时开 `--sampler-power`；lr 降到 1e-4"],
            ["每个 epoch 时间从 5 分钟涨到 10 分钟", "Drive 写入变慢或 worker 退化", "把 `--out-dir` 指回 Drive 根下，别用深层嵌套目录"],
        ],
        widths=[6.0, 5.4, 5.0],
        size=8.3,
        caption="表 7-4　训练日志的六种典型形态",
    )
    k.page_break()


def ch8(k):
    k.h1("8", "T6　评估：TTA、温度缩放与导出预测")

    k.h2("8.1　【做什么】")
    k.p(
        "对每个 run 的 `best.pt` 在指定划分上推理，输出一份 `test_preds.csv`（每张图一行："
        "`image_name, patient_id, target, prob`）。这份 CSV 是后面所有统计与图的唯一输入——"
        "也就是说，**断网、没 GPU、只剩笔记本时，报告照样能写完**。"
    )

    k.h2("8.2　【代码】evaluate.py")
    k.p(
        "推理默认开启 4 向翻转 TTA（原图 + 水平 + 垂直 + 双翻转），把四次概率取平均。"
        "皮肤镜没有正方向，翻转不会改变语义，所以这是最安全的一种 TTA。",
        after=2,
    )
    k.excerpt("evaluate.py", "predict", "infer_split")
    k.p("温度缩放只有两个函数：在 val 上网格搜索一个标量 T 使 NLL 最小，再把它应用到 test。", after=2)
    k.excerpt("evaluate.py", "fit_temperature", "apply_temperature")
    k.p(
        "它的价值在于把「校准坏」拆成「尺度坏」还是「排序坏」：温度缩放是严格单调变换，"
        "所以 AUROC、AUPRC、Sens@Spec80 一个都不会变。如果它能把 ECE 从 0.19 拉回 0.05，"
        "结论就是「平衡损失只破坏了概率尺度，排序信息完好」；拉不回来则说明校准问题是结构性的。"
        "两种结论都很值钱，而且只有做了这一步才能区分。",
    )

    k.h2("8.3　【怎么做】三条命令")
    k.code(
        "# 1) 测试集预测（含 4 向 TTA）\n"
        "python src/evaluate.py --manifest manifests/split_seed42.csv --img-dir data/train_256 \\\n"
        "  --ckpt /content/drive/MyDrive/runs/b3_bce/best.pt \\\n"
        "  --split test --out /content/drive/MyDrive/runs/b3_bce/test_preds.csv\n"
        "\n"
        "# 2) 验证集预测（温度缩放要在 val 上拟合，所以 val 也必须有预测）\n"
        "python src/evaluate.py ... --split val --out /content/drive/MyDrive/runs/b3_bce/val_preds.csv\n"
        "\n"
        "# 3) 用 val 拟合 T，再套到 test（本机 CPU 即可，秒级）\n"
        "python - <<'PY'\n"
        "import sys, pandas as pd; sys.path.insert(0, 'src')\n"
        "from evaluate import fit_temperature, apply_temperature\n"
        "\n"
        "d = 'runs/b3_wbce'\n"
        "va = pd.read_csv(f'{d}/val_preds.csv'); te = pd.read_csv(f'{d}/test_preds.csv')\n"
        "T = fit_temperature(va)                  # 单个标量\n"
        "print('optimal T =', round(T, 3))        # T>1 说明原模型过自信\n"
        "apply_temperature(te, T).to_csv(f'{d}/test_preds_temp.csv', index=False)\n"
        "PY",
        title="终端",
    )
    k.code(
        "{\n"
        "  \"n\": 6625, \"n_pos\": 117, \"prevalence\": 0.01766,\n"
        "  \"auroc\": 0.8907, \"auprc\": 0.2714, \"pauc_fpr20\": 0.6421,\n"
        "  \"brier\": 0.0171, \"nll\": 0.0812,\n"
        "  \"ece_uniform15\": 0.0046, \"ece_adaptive15\": 0.0128, \"ece_pos\": 0.6120,\n"
        "  \"sens_at_spec80\": 0.4786, \"spec_achieved\": 0.8012, \"threshold\": 0.1384,\n"
        "  \"cal_slope\": 0.8834, \"cal_intercept\": 0.0612\n"
        "}\n"
        "predictions -> runs/b3_bce/test_preds.csv",
        title="预期输出（结构固定，数值是示意；你自己的数字会不同）",
    )
    k.check(
        "每个 run 目录下都有 `test_preds.csv`（6,625 行 = test 的图像数）和 `test_preds_metrics.json`；"
        "行数、阳性数、患者数与第 3 章的 manifest 一致。"
    )

    k.h2("8.4　三个必须避开的坑")
    k.table(
        ["坑", "症状", "原因与处理"],
        [
            ["`--img-size` 与训练不一致", "指标掉 3–8 点，无报错", "训练 256 → 评估也必须 256（`cfg.json` 里有记录）"],
            ["`meta_encoder.json` 不在 ckpt 同目录", "`FileNotFoundError`，或元数据维度对不上", "它由 `train.py` 写在 `--out-dir` 里；移动 ckpt 时要一起移动"],
            ["在 test 上拟合温度/选阈值", "结果系统性乐观 2–5 点", "T 与阈值都只在 val 上得到；test 只被「应用」一次"],
        ],
        widths=[4.6, 4.6, 7.2],
        size=8.4,
        caption="表 8-1　评估阶段的三个坑",
    )
    k.warn(
        "`evaluate.py --split test` 会在 test 上**重新算**一个 80% 特异度阈值并打印敏感度。"
        "那是给「快速看一眼」用的，不能当主结果。主结果的阈值必须来自 val（第 9.2 节给出代码）。"
        "这也是为什么 val 的预测文件一定要保留。"
    )
    k.page_break()


def ch9(k):
    k.h1("9", "T7　指标、阈值协议与配对 bootstrap")

    k.h2("9.1　【做什么】")
    k.p(
        "把 5 份 `test_preds.csv` 变成报告里的三张表：每个模型的点估计 + 95% CI、模型之间的配对差值 CI、"
        "以及一张可直接粘进 markdown 的表。全程 CPU，不碰 GPU。"
    )
    k.p(
        "实现全在 `src/metrics.py`（286 行，纯 numpy，无 sklearn 依赖）。"
        "为什么要自己写：这些函数是报告里所有数字的唯一来源，必须能逐行读懂、能被自检覆盖。",
    )

    k.h2("9.2　阈值协议：最容易无意中作弊的一步")
    k.table(
        ["做法", "是否可接受", "后果"],
        [
            ["在 test 上找 80% 特异度对应的阈值，再在 test 上算敏感度", "❌ 不可接受", "等于用测试集调参，系统性乐观 2–5 点"],
            ["在 val 上选阈值并冻结，在 test 上算敏感度", "✅ 主结果", "诚实；含阈值估计噪声，必须体现在 CI 里"],
            ["在 test 上做 oracle 阈值，仅作上界报告", "△ 敏感性分析", "用来量化「阈值迁移」的代价，须明确标注 oracle"],
        ],
        widths=[7.0, 2.6, 6.8],
        size=8.4,
        caption="表 9-1　三种阈值来源。两者之差本身是个有意思的量：oracle 明显更好说明概率尺度在划分间漂移了",
    )
    k.p("实现只有三行，但有一个经典写反的地方：", after=2)
    k.excerpt("metrics.py", "threshold_at_specificity", "sens_at_spec")
    k.warn(
        "把 `np.quantile(neg, spec)` 写成 `np.quantile(neg, 1 - spec)`，阈值会落在阴性分布的 20 分位而不是 80 分位，"
        "敏感度从 0.35 直接变成 0.75。这个错误在代码审查里几乎看不出来，"
        "所以在 `tests/test_all.py` 里专门有一个用例（`sens@spec80 threshold lands on the negative quantile`）。",
        extra="一行写反，敏感度凭空高 40 点",
    )

    k.h2("9.3　为什么必须报三种校准口径")
    k.p(
        "设想一个「躺平」模型：对每一张图都输出 p = 0.02。三种口径给出三个完全不同的故事：",
        after=6,
    )
    k.table(
        ["口径", "躺平模型的取值", "说明了什么"],
        [
            ["全样本等宽 ECE", "≈ 0.002", "「看起来完美校准」——因为 98% 的样本确实是良性，|0.02 − 0.0176| 很小。这个数会骗人"],
            ["ECE_pos（只在真恶性上算）", "≈ 0.98", "误差接近极限：真恶性被当成 2% 的概率"],
            ["校准斜率", "≈ 0", "根本没有区分度。斜率 0 直接暴露问题"],
            ["AUROC（对照）", "0.5", "唯一不骗人的排序指标"],
        ],
        widths=[4.4, 3.0, 9.0],
        size=8.4,
        caption="表 9-2　常数预测器 p=0.02 在四种口径下的取值。这张表就是「为什么不能只报全样本 ECE」的证明",
    )
    k.p("实现（三种口径由同一个函数的不同参数给出）：", after=2)
    k.excerpt("metrics.py", "ece", "calibration_slope")
    k.p("可直接写进报告的观察：", after=2)
    k.code(
        "Under 1.8% prevalence, whole-sample ECE is nearly invariant to model quality: a\n"
        "constant 0.02 predictor attains ECE < 0.01 while achieving zero sensitivity. We\n"
        "therefore report class-conditional ECE and the calibration slope as primary\n"
        "calibration endpoints, and treat whole-sample ECE as descriptive only.",
        title="报告 §Results 的第一段可以这样开头",
    )

    k.h2("9.4　其余指标：一条命令算齐")
    k.p("`summary()` 是唯一被 `evaluate.py` 与 `report.py` 共用的打包函数，保证「同一个数在两处相同」：", after=2)
    k.excerpt("metrics.py", "auroc", "auprc", "brier", "net_benefit", "summary")

    k.h2("9.5　患者级配对 bootstrap")
    k.p(
        "两个设计决定决定了 CI 是否可信。**按患者重采样，不按图像**：同一患者的图像不独立，"
        "图像级 bootstrap 会把 CI 宽度低估约 sqrt(每患者图像数) 倍。**必须配对**："
        "第 b 次重采样对所有模型抽到的是同一批患者，于是 metric_A(b) − metric_B(b) 就是配对差值，"
        "取 2.5/97.5 分位得到差值的 CI。",
    )
    k.why(
        "「比较两个各自很宽的 CI 是否重叠」在统计上不是模型比较的正确检验，而且在 n=117 时几乎永远不会判为显著，"
        "会把真实效应藏起来。配对差值的功效高得多：同一批患者上的共同波动被消掉了。"
    )
    k.excerpt("bootstrap.py", "patient_bootstrap", "to_frame")

    k.h2("9.6　【怎么做】一条命令出三张表")
    k.code(
        "python src/report.py --runs \"runs/*\" --out results --n-boot 2000 --seed 42",
        title="终端（CPU，约 1–2 分钟）",
    )
    k.p("输出（下面是三个模型的真实运行结果，但**预测值是我为演示造的**，所以数字只能看格式）：", after=2)
    k.code(
        "found: b3_bce, b3_focal, b3_wbce\n"
        "7038 images, 114 melanomas, 188 patients\n"
        "\n"
        "model      auprc                auroc                ece_adaptive15       sens_at_spec80\n"
        "b3_bce     0.365 [0.196,0.790]  0.907 [0.840,0.934]  0.009 [0.007,0.198]  0.851 [0.708,0.912]\n"
        "b3_focal   0.438 [0.320,0.819]  0.914 [0.824,0.942]  0.017 [0.013,0.126]  0.868 [0.658,0.939]\n"
        "b3_wbce    0.365 [0.184,0.813]  0.916 [0.833,0.944]  0.046 [0.039,0.108]  0.877 [0.680,0.942]\n"
        "\n"
        "wrote -> results/results_long.csv, diffs.csv, results.md, summary.json",
        title="示例输出（表头已裁到四个指标；CI 是 2000 次患者级 bootstrap 的 95% 百分位区间）",
    )
    k.table(
        ["文件", "内容", "用在哪"],
        [
            ["`results_long.csv`", "model × metric：点估计 + CI", "报告的核心表 / 附录"],
            ["`diffs.csv`", "与参照模型的配对差值、CI、双侧 p", "「谁更好」的唯一合法证据"],
            ["`results.md`", "上两者的 markdown 版", "直接粘进报告"],
            ["`summary.json`", "含校准斜率与截距的完整指标", "附录 / 复核"],
        ],
        widths=[3.8, 6.4, 6.2],
        size=8.4,
        caption="表 9-3　report.py 的四个输出",
    )

    k.h2("9.7　结果表长什么样，以及三条解读纪律")
    k.table(
        ["模型", "Sens@Spec80", "ECE_adaptive", "ECE_pos", "校准斜率", "AUROC", "AUPRC"],
        [
            ["B3 + BCE", "0.38 [0.29, 0.47]", "0.014 [0.008, 0.022]", "0.61", "0.92", "0.891 [0.874, 0.907]", "0.27"],
            ["B3 + 逆患病率", "0.46 [0.36, 0.55]", "0.041 [0.028, 0.058]", "0.44", "0.41", "0.889 [0.871, 0.906]", "0.31"],
            ["B3 + Focal", "0.44 [0.34, 0.53]", "0.028 [0.017, 0.041]", "0.52", "0.63", "0.893 [0.876, 0.909]", "0.30"],
            ["R50 + BCE", "0.36 [0.27, 0.45]", "0.016 [0.010, 0.024]", "0.63", "0.88", "0.884 [0.866, 0.901]", "0.26"],
            ["B3 + BCE + 元数据", "0.40 [0.31, 0.49]", "0.011 [0.006, 0.018]", "0.58", "1.02", "0.899 [0.882, 0.915]", "0.29"],
        ],
        widths=[3.4, 2.8, 3.0, 1.6, 1.6, 3.0, 1.6],
        size=8.0,
        caption="表 9-4　核心结果表模板（**数字是示意**，用来确认格式与解读方式，不是你们的结果）",
    )
    k.bullets([
        "**不要写「A 的 CI 与 B 的 CI 重叠，所以无差异」。** 这是错的说法，也是审阅者最常抓的点。"
        "正确说法来自差值：`delta = +0.081 [+0.012, +0.154], p = 0.021`。",
        "**不要对 ECE 做「越小越好」的排序。** ECE 不是严格 proper scoring rule，对分箱与样本量敏感。"
        "跨模型比较 ECE 时必须同时给 Brier 与 NLL，因为它们是 proper 的、可以放心排序。",
        "**校准斜率 0.41 要解释。** 它不是「校准差了 41%」，而是「模型输出的 logit 需要乘 2.4 才能匹配真实频率」——"
        "这正是温度缩放会做的事（T≈2.4）。两处数字应该能对上；对不上说明有一处算错了。",
    ])
    k.check(
        "`results/` 下四个文件齐全；`diffs.csv` 里 `contrast` 以参照模型开头；"
        "每个模型的 `sens_at_spec80` 点估计都落在自己的 CI 内；校准斜率与第 8.3 节拟合出的 T 互为倒数关系（1/T ≈ slope）。"
    )
    k.page_break()


def ch10(k):
    k.h1("10", "图表与误差分析")

    k.h2("10.1　四张必备图")
    k.table(
        ["图", "函数", "要传达的唯一信息", "常见错误"],
        [
            ["可靠性图", "`reliability_diagram`", "逆患病率模型的点系统性偏离对角线", "用等宽箱 → 所有点挤在左端一条竖线上，什么也看不出（用等频箱）"],
            ["ROC", "`roc_curve`", "三条曲线几乎重合 → AUROC 对损失不敏感", "只画曲线不标 AUROC，读者无法比较"],
            ["敏感度-特异度曲线", "`sensitivity_specificity_curve`", "高特异区的分离度比 ROC 明显", "漏掉 80% 处的标记点，主终点在图上找不到"],
            ["决策曲线", "`decision_curve`", "收益集中在低阈值（高召回）区段", "纵轴范围开太大，把差异压平"],
        ],
        widths=[3.0, 4.6, 5.4, 5.8],
        size=8.2,
        caption="表 10-1　四张图各自只负责一句话。一张图想说两件事，就说明还没想清楚",
    )
    k.p("生成方式（不需要 GPU，只要有预测 CSV，断线了也能补图）：", after=2)
    k.code(
        "python src/figures.py --preds \"runs/*/test_preds.csv\" --out-dir figures/\n"
        "# -> figures/panel.png  (2x2, 300 dpi)\n"
        "# 同时把每个模型的完整指标字典打印一遍，便于核对图与表是同一份数据",
        title="终端",
    )
    k.p("可靠性图是这个项目的招牌图，值得单独做一张大图：横轴预测概率、纵轴实测恶性率、画对角线。"
          "如果再把 bootstrap 的 95% 带画上去，「逆患病率模型的曲线在对角线上方还是下方、偏多少」"
          "就变成可以直接指认的事实，而不是一句形容词。", after=4)
    k.excerpt("figures.py", "reliability_diagram", "decision_curve")
    k.why(
        "决策曲线要同时画两条参照线：`treat all`（全部转诊）与 `treat none`（净收益恒为 0）。"
        "有临床价值的区间是模型曲线同时高于这两条的那一段。报告里要写的是**区间宽度**，不是单个点："
        "「逆患病率 BCE 在 pt ∈ [0.03, 0.12] 上净收益高于 BCE 与全部转诊，但在 pt > 0.15 后低于 BCE」——"
        "这样的句子才叫解释。"
    )

    k.h2("10.2　分层误差分析：把假阴性拆开看")
    k.p(
        "提案要求「stratify false negatives by patient age band and lesion site」。"
        "实现上不需要重新训练，直接在测试集预测表上做交叉表：",
        after=2,
    )
    k.code(
        "python - <<'PY'\n"
        "import pandas as pd\n"
        "pred = pd.read_csv('runs/b3_bce/test_preds.csv')\n"
        "man  = pd.read_csv('manifests/split_seed42.csv')\n"
        "pred = pred.merge(man[['image_name', 'age_approx',\n"
        "                       'anatom_site_general_challenge']], on='image_name')\n"
        "\n"
        "pred['age_band'] = pd.cut(pred.age_approx, [0, 40, 55, 70, 100],\n"
        "                          labels=['<=40', '41-55', '56-70', '>70'])\n"
        "pred['missed'] = (pred.target == 1) & (pred.prob < 0.5)\n"
        "\n"
        "print('阳性数按年龄段:'); print(pred[pred.target == 1].age_band.value_counts().sort_index())\n"
        "print('漏诊率按年龄段:'); print(pd.crosstab(pred.age_band, pred.missed,\n"
        "                                          normalize='index').round(3))\n"
        "print('漏诊率按部位:'); print(pd.crosstab(pred.anatom_site_general_challenge,\n"
        "                                        pred.missed, normalize='index').round(3))\n"
        "PY",
        title="终端 · 分层假阴性",
    )
    k.warn(
        "这一步必须**在看结果之前**决定做。如果先看到「老年组漏诊率高」再回头补这个分析，"
        "就变成了事后挑选。现在写下来，无论结果如何都报——「未发现明显分层差异」同样是有价值的结论。"
    )

    k.h2("10.3　Grad-CAM 只用来做定性说明")
    k.p(
        "提案把 Grad-CAM 误差面板列进交付物。它的作用是让读者相信模型在看病灶，"
        "而不是在拍「皮肤镜的黑色圆形边框」或「尺子刻度」——这类伪影在皮肤镜数据里非常常见。"
        "但不要从 Grad-CAM 推因果结论：它没有定量含义，无法支撑「模型学到了 X」这种句子。"
    )
    k.p("正确的写法是：挑 8 张假阴性，按「有明显病灶却被忽略」和「病灶本来就不明显」两类各 4 张，配一句：", after=2)
    k.code(
        "In 5 of 8 false negatives the saliency map covered the lesion but the predicted\n"
        "probability remained below 0.2, suggesting a confidence rather than an attention\n"
        "failure.",
        title="这类描述有信息量，因为它和校准主题直接相关",
    )
    k.check(
        "`figures/panel.png` 已生成且四张子图都非空；分层表已打印；"
        "Grad-CAM 面板的每张图都有对应的预测概率标注（否则无法区分「没看见」与「看见了但不敢报」）。"
    )
    k.page_break()


def ch11(k):
    k.h1("11", "写作与交付：把数字变成报告")

    k.h2("11.1　报告骨架（直接对应提案六节）")
    k.table(
        ["节", "写什么", "素材来源", "页数"],
        [
            ["1 Introduction", "极端不平衡下 AUROC 足够但概率不可用；研究问题三句话", "提案 §1 + 第 0.4 节", "0.8"],
            ["2 Related Work", "患者级划分的必要性；校准作为一等指标；平衡损失的已知副作用", "提案 §2 + 附录 A", "1.0"],
            ["3 Data & Methods", "数据、划分（含 sha256）、增强、模型、三种损失、阈值协议", "第 2–8 章", "2.0"],
            ["4 Experiments", "实验矩阵、预算、每个条件的超参数（`cfg.json` 汇总）", "第 7 章 + 表 7-3", "1.5"],
            ["5 Results", "核心表、四张图、决策曲线、温度缩放、分层误差", "第 9–10 章", "3.0"],
            ["6 Discussion", "校准是尺度还是结构；图像级划分的后果；局限", "第 1.1、8.2、9.7 节", "1.5"],
        ],
        widths=[3.2, 7.4, 4.6, 1.4],
        size=8.4,
        caption="表 11-1　六节骨架。参考文献与图表目录另计",
    )

    k.h2("11.2　三句可以写进 Discussion 的硬话")
    k.p("报告的说服力来自敢下判断，而不是罗列数字。下面三句是这个项目最有价值的落点，每一句都需要对应证据：", after=4)
    k.table(
        ["判断", "证据", "写法要点"],
        [
            ["「在 1.76% 的患病率下，全样本 ECE 不是校准指标」",
             "§9.3 的构造性例子 + 你们实测的 ECE_uniform 与 ECE_pos 差距",
             "先给反例（常数 0.02 预测器 ECE<0.01），再给实测，最后给结论"],
            ["「平衡损失买到的是敏感度，付的是概率尺度」",
             "配对差值：Sens@Spec80 +X 点、斜率从 0.9 掉到 0.4、温度缩放收回 Y%",
             "三个数字缺一不可；只说「变差了」等于没说"],
            ["「患者级划分让所有数字下降 Z 点，但没改变模型排序」",
             "（可选）同一模型在 image-level vs patient-level 划分下各跑一次",
             "这是提案 §6 那句「evaluation choices misleading」最有力的证据"],
        ],
        widths=[5.6, 6.0, 5.0],
        size=8.2,
        caption="表 11-2　三句硬话与证据要求。第三句需要额外一次训练（约 70 分钟），配额宽裕时做",
    )

    k.h2("11.3　审阅者会问的六个问题")
    k.table(
        ["问题", "怎么答"],
        [
            ["「你的 AUROC 为什么比 leaderboard 低 5 个点？」", "官方测试集标签不公开；且排行榜允许图像级重叠。引用 §0.4 的那段英文"],
            ["「为什么不用 AUPRC 当主终点？」", "AUPRC 很好，但「敏感度 @ 固定特异度」直接对应临床可操作阈值；AUPRC 保留为次要"],
            ["「ECE 怎么算的？为什么不是 15 个等宽箱？」", "主口径是等频 15 箱 + ECE_pos + 校准斜率；等宽箱在 p≈0 处会被 98% 的良性样本压成一箱"],
            ["「阈值是在测试集上选的吧？」", "在 val 上选并冻结；另报 oracle 阈值作上界，两者之差就是阈值迁移代价"],
            ["「为什么只有 5 个实验？」", "免费 T4 每周 10–15 GPU·小时；5 次覆盖全部四个消融维度，交叉项不是研究问题"],
            ["「元数据为什么只用三个字段？」", "`diagnosis`/`tbp_lv_*` 是标签派生或真实场景不可得，用了就是泄漏；详见 `data.py` 的注释"],
        ],
        widths=[6.4, 9.8],
        size=8.4,
        caption="表 11-3　六个必然会问的问题，事先准备好一段话",
    )

    k.h2("11.4　交付物清单")
    k.table(
        ["交付物", "形态", "检查方式"],
        [
            ["代码仓", "`melanoma_calib/`，含 `src/`、`tests/`、`tools/`", "`python tests/test_all.py` 全过"],
            ["划分清单", "`manifests/split_seed42.csv` + `_report.json`（含 sha256）", "哈希与报告 Methods 一致"],
            ["训练产物", "5 个 run 目录，每个 4–5 个文件", "`log.csv` 有 12 行；`best.pt` 存在"],
            ["预测", "每个 run 的 `test_preds.csv`（+ `val_preds.csv`）", "行数 = 对应划分图像数"],
            ["结果表", "`results/{results_long,diffs}.csv`、`results.md`、`summary.json`", "点估计落在 CI 内"],
            ["图", "`figures/panel.png` + 分层误差表", "四张子图都非空"],
            ["报告", "PDF，六节 + 附录", "含 sha256、阈值协议、局限"],
            ["幻灯片", "10–12 页（Kai 负责）", "核心表 + 可靠性图 + 决策曲线"],
        ],
        widths=[3.0, 7.6, 5.6],
        size=8.4,
        caption="表 11-4　交付物。代码与划分清单要真的开源/打包，否则「可复现」只是一句话",
    )
    k.page_break()


def ch12(k):
    k.h1("12", "排错手册")

    k.p(
        "下面十二条按「出现频率 × 排查成本」排序。每一条都是本项目实际会遇到的，"
        "前三条几乎必然发生。",
        after=6,
    )
    k.table(
        ["#", "症状", "最可能的原因", "处理"],
        [
            ["1", "第一个实验 val AUROC 只有 0.6–0.7", "图像目录与 `image_name` 错位（最常见）；或 label 列读错",
             "跑 `tools/inspect_data.py --img-dir ...`；再随机取 5 张图连同文件名与 label 一起打印"],
            ["2", "`CUDA out of memory`", "batch 太大；或上一个进程还占着显存", "`--batch-size 16`；「运行时 → 重启运行时」"],
            ["3", "训练中途断开，`log.csv` 停在 epoch k", "免费 T4 的常态", "`--resume` 接着跑（第 7.6 节）；下次把 `--out-dir` 指向 Drive"],
            ["4", "`pos_weight` 生效后 loss 变 NaN", "加权过猛 + lr 太大，或同时开了 `--sampler-power`", "lr→1e-4；确认 `--sampler-power 0`"],
            ["5", "评估指标比训练日志里的 val 低一截", "评估用了 TTA 但训练时没用（正常，TTA 通常小涨）；或 `--img-size` 不一致", "先核对 `cfg.json`；TTA 增益应在 ±0.01 内"],
            ["6", "`report.py` 报 `no runs with test_preds.csv found`", "`--runs` 的通配符没展开，或 run 目录缺 `test_preds.csv`", "用绝对路径；先 `ls runs/*/test_preds.csv`"],
            ["7", "`diffs.csv` 为空", "`--reference` 指定的模型不在一对名字里", "不传 `--reference`，默认取第一个 run"],
            ["8", "Bootstrap CI 宽到 ±0.2", "测试集阳性太少，或用了图像级重采样", "确认是患者级（`patient_col='patient_id'`）；必要时做 5 折 CV 汇总"],
            ["9", "可靠性图所有点挤在左端一条竖线", "用了等宽箱", "`mode='quantile'`（默认已是等频，检查是否手改成 uniform）"],
            ["10", "温度缩放后 ECE 反而变大", "T 在 test 上拟合，或在 val 上拟合后忘了应用", "T 必须来自 val；应用时对 logit 除以 T 再 sigmoid"],
            ["11", "`meta_encoder.json` 找不到", "ckpt 被单独复制走了", "它与 ckpt 同目录；一起搬运"],
            ["12", "同一份代码两次跑出不同 AUROC", "`cudnn.benchmark=True`（预期内）或 timm 版本漂移", "差异应在 ±0.005 内；超出就核对 `timm` 版本与 `cfg.json`"],
        ],
        widths=[0.9, 4.4, 5.4, 5.5],
        size=8.1,
        caption="表 12-1　十二个故障。第 1 条最隐蔽：训练一切正常，只是数字不对",
    )

    k.h2("12.1　配额不够时的降级顺序")
    k.p("按「损失多少信息」从最不痛到最痛排序：", after=4)
    k.steps([
        "降 epoch 到 8（−25% 时间）：B3 通常在第 8 epoch 已进平台，AUROC 损失约 0.003。",
        "降分辨率到 224（−20% 时间）：AUROC 损失约 0.005–0.01，对结论方向无影响。",
        "跳过 ResNet-50：放弃架构消融，在 limitations 里说明。",
        "把三次损失实验缩到各 6 epoch：能看方向，但绝对值不可信，必须在报告里标注。",
    ])
    k.warn(
        "**不要通过缩小测试集来解决算力问题。** 测试集从 20% 缩到 10% 会让阳性数从 117 降到 58，"
        "CI 半宽变成 ±15 点，那时任何结论都不可信——这比少做一次消融严重得多。"
    )
    k.page_break()


def ch13(k):
    k.h1("13", "执行检查清单")

    k.p(
        "按顺序勾。每一条都对应一个具体的失败模式，不是形式主义。"
        "建议直接复制成一个 markdown 文件放在仓库根目录，做完一个勾一个。",
        after=6,
    )
    items = [
        ("01", "`python tests/test_all.py` 25 项全过（本机，无 GPU）"),
        ("02", "训练集 `train.csv` 行数 33,126，含 `patient_id` 列"),
        ("03", "阳性 584 例、患病率 1.76%，与提案一致"),
        ("04", "`tools/inspect_data.py` 通过，四个基准数字已记录"),
        ("05", "`split.py` 已生成 manifest，sha256 写进 README 与报告 Methods"),
        ("06", "三条断言全过：患者不交叉、lesion 不跨划分、`image_name` 无重复"),
        ("07", "抽看 12 张测试集图像，确认是皮肤镜照片"),
        ("08", "`meta_encoder.json` 只在训练集上拟合，且已序列化"),
        ("09", "元数据只用 `age_approx` / `sex` / `anatom_site_general_challenge`"),
        ("10", "`--limit-batches 5` 冒烟测试通过，四个文件都写出"),
        ("11", "`--resume` 能从 epoch k 接续，学习率没有重新 warmup"),
        ("12", "第一个实验 `b3_bce` 的 val AUROC 落在 0.85–0.92"),
        ("13", "五个 run 目录齐全，每个都有 `log.csv`/`last.pt`/`best.pt`/`cfg.json`"),
        ("14", "每个 run 都有 `test_preds.csv` 与 `val_preds.csv`"),
        ("15", "阈值只在 val 上选取，test 只应用一次"),
        ("16", "报告了实际达到的特异度，而不只是目标 0.80"),
        ("17", "三种 ECE 口径都算了，并解释了为什么主指标不是等宽 ECE"),
        ("18", "校准斜率与最优温度 T 对得上（斜率倒数 ≈ T）"),
        ("19", "bootstrap 是患者级且配对，报的是差值 CI 而不是两个 CI 是否重叠"),
        ("20", "`figures/panel.png` 可在无 GPU 环境从预测 CSV 重新生成"),
    ]
    rows = [[n, t, "☐"] for n, t in items]
    k.table(["#", "检查项", "☑"], rows, widths=[1.0, 13.4, 1.8], size=8.4,
            caption="表 13-1　20 项交付检查")
    k.check(
        "20 项全部打勾之后，报告里的每个数字都能在仓库里找到对应的文件与命令。"
        "这时再写 Discussion——顺序反了，就会写出无法被自己的代码支持的句子。"
    )
    k.page_break()


def appendix(k):
    k.h1("附录 A", "参考文献修正与必补四篇")
    k.p(
        "提案的参考文献有三处必须改、四处必须补。改完之后 Related Work 的说服力会明显不同——"
        "现在的 [3] 期刊名是错的，[4] 处于「不可引用」状态，审阅者一眼就能看到。",
        after=6,
    )
    k.table(
        ["原编号", "问题", "处理"],
        [
            ["[3]", "期刊名写成 Journal of Medical Extensible Learning and Applications (JMELA)，"
                    "实为 MELBA（Journal of Machine Learning for Biomedical Imaging）",
             "按正确信息重写，核对 DOI 与 arXiv 号"],
            ["[4]", "无年份、无期刊/会议、无 DOI/arXiv 号，不可引用", "补齐；它只支撑「多模态融合」一句，删掉不影响论证"],
            ["[6]", "「ISIC 2020 class distribution: 584/33,126」是数据事实，不是文献", "移入正文或 Data 一节的脚注，从参考文献中删除"],
        ],
        widths=[1.6, 8.6, 6.0],
        size=8.4,
        caption="表 A-1　三处必须改",
    )
    k.p("必须补充的四篇（每一篇都对应报告里一个具体论断）：", after=6)
    k.table(
        ["文献", "用途"],
        [
            ["Lin et al. *Focal Loss for Dense Object Detection*, ICCV 2017", "focal loss 的原始定义与 α/γ 语义；说明为什么 α 不能照抄 0.25"],
            ["Cui et al. *Class-Balanced Loss Based on Effective Number of Samples*, CVPR 2019", "支撑 `cb` 条件；解释为什么逆患病率加权是「过冲」"],
            ["Guo et al. *On Calibration of Modern Neural Networks*, ICML 2017", "ECE 与温度缩放的出处；「深度网络系统性过自信」这一前提"],
            ["Cassidy et al. *Analysis of the ISIC image datasets*, MedIA 2022", "数据集沿革与「患者级标注为何重要」（提案已引，保留）"],
        ],
        widths=[7.4, 8.8],
        size=8.4,
        caption="表 A-2　四篇必补",
    )

    k.h1("附录 B", "命令速查")
    k.code(
        "# 0) 自检（无 GPU，几秒）\n"
        "python tests/test_all.py\n"
        "\n"
        "# 1) 数据体检\n"
        "python tools/inspect_data.py --csv data/train.csv --img-dir data/train_256\n"
        "\n"
        "# 2) 1024 -> 256（一次性，可断点重跑）\n"
        "python tools/resize_images.py --src data/train --dst data/train_256 --size 256\n"
        "\n"
        "# 3) 划分并冻结\n"
        "python src/split.py --csv data/train.csv --out manifests/split_seed42.csv --seed 42\n"
        "\n"
        "# 4) 冒烟（2 分钟）\n"
        "python src/train.py --manifest manifests/split_seed42.csv --img-dir data/train_256 \\\n"
        "  --epochs 1 --limit-batches 5 --out-dir runs/_smoke\n"
        "\n"
        "# 5) 五个正式实验\n"
        "for LOSS in bce wbce focal; do\n"
        "  python src/train.py --manifest manifests/split_seed42.csv --img-dir data/train_256 \\\n"
        "    --model efficientnet_b3 --loss $LOSS --epochs 12 --batch-size 32 \\\n"
        "    --out-dir /content/drive/MyDrive/runs/b3_$LOSS\n"
        "done\n"
        "python src/train.py ... --model resnet50 --loss bce --out-dir .../runs/r50_bce\n"
        "python src/train.py ... --loss bce --meta --out-dir .../runs/b3_bce_meta\n"
        "\n"
        "# 6) 断线续训\n"
        "python src/train.py ... --out-dir .../runs/b3_bce --resume\n"
        "\n"
        "# 7) 评估（每个 run 跑 val 与 test 各一次）\n"
        "python src/evaluate.py --manifest manifests/split_seed42.csv --img-dir data/train_256 \\\n"
        "  --ckpt runs/b3_bce/best.pt --split test --out runs/b3_bce/test_preds.csv\n"
        "\n"
        "# 8) 结果表 + 配对 bootstrap\n"
        "python src/report.py --runs \"runs/*\" --out results --n-boot 2000\n"
        "\n"
        "# 9) 四张图\n"
        "python src/figures.py --preds \"runs/*/test_preds.csv\" --out-dir figures\n"
        "\n"
        "# 10) 无数据演练（等下载时用）\n"
        "python tools/make_synthetic.py --out data_synth/train.csv\n"
        "python src/split.py --csv data_synth/train.csv --out manifests/synth_split.csv",
        title="全部命令，按执行顺序",
    )

    k.h1("附录 C", "时间与算力预算")
    k.table(
        ["阶段", "内容", "GPU 时间", "墙钟时间"],
        [
            ["Day 1", "环境、数据下载、缩放到 256、目检、划分冻结", "0", "3–4 h"],
            ["Day 2", "冒烟 + `b3_bce` 全量", "1.2 h", "半天（含断线重连）"],
            ["Day 3", "`b3_wbce` + `b3_focal`", "2.4 h", "一天两个会话"],
            ["Day 4", "`r50_bce` + `b3_bce_meta`", "2.0 h", "一天两个会话"],
            ["Day 5", "评估 5 个 run、拟合温度缩放", "0.2 h", "半天（CPU 为主）"],
            ["Day 6–7", "bootstrap、四张图、分层误差、写报告", "0", "1–2 天"],
            ["合计（必需）", "", "≈ 5.8 GPU·h", "5 个工作日"],
        ],
        widths=[2.2, 7.4, 3.4, 3.6],
        size=8.4,
        caption="表 C-1　预算。免费 T4 每天 2–3 小时可用，5.8 小时需要 2–3 天的配额",
    )
    k.p(
        "如果只做最小可交付集合（三个损失条件、一个 backbone），GPU 时间是 3.5 小时；"
        "加上架构与元数据两个条件才到 5.8 小时。两种情况都能支撑提案的核心结论，区别只在消融的完整度。",
    )
    k.p("—— 全文完 ——", align="center", color=None, before=18)
