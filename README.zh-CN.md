# melanoma_calib

**类别平衡损失没有换来敏感度** —— ISIC 2020 上的校准优先、患者级不交叉基准。

*English: [README.md](README.md)*

SDSC 6018 期末项目 · 第 8 组 · Ke Liu, Zeyu Fu, Dong Wang, Kai Liu（香港城市大学 数据科学系）

---

## 结论速览

测试集 6,625 张 / 117 例恶性 / 411 名患者；阈值在验证集冻结后原样应用；方括号为 95% 患者级 bootstrap。

| 模型 | AUROC | AUPRC | ECE | 校准斜率 | Sens@Spec80 |
|---|---|---|---|---|---|
| **B3 + BCE** | **0.892** [.865,.917] | 0.140 [.101,.202] | **0.0045** | 0.80 | **0.803** [.720,.884] |
| B3 + 逆患病率 BCE | 0.860 | 0.091 | 0.0339 | 0.43 | 0.726 |
| B3 + focal | 0.876 | 0.169 | 0.1355 | 1.85 | 0.812 |
| R50 + BCE | 0.855 | 0.104 | 0.0055 | 0.65 | 0.761 |
| B3 + BCE + 元数据 | 0.889 | **0.218** | 0.0059 | 0.79 | 0.752 |

一句话：**平衡损失既没买到敏感度，也没保住校准**；逆患病率 BCE 过度自信且结构性失准，focal 自信不足但一个温度可修。详见 `results/results.md` 与报告。

## 这个仓库里有什么

| 有 | 说明 |
|---|---|
| `src/` | 划分、数据、模型、损失、训练、评估、指标、bootstrap、汇总、作图 |
| `tools/` | 取数、缩放、数据体检、温度拟合、冻结阈值 bootstrap、图件生成 |
| `scripts/` | PowerShell 一键流程（Windows 本机） |
| `tests/` | 38 项自检（指标/划分/下载器），不需要 GPU 与数据 |
| `manifests/` | **冻结的患者级划分**（33,126 行，SHA-256 见 `split_seed42_report.json`） |
| `runs/<run>/` | 五个 run 的 `val_preds.csv` / `test_preds.csv` / `*_metrics.json` / `temperature.json` |
| `results/` | `summary.json`、`results_long.csv`、`diffs.csv`（配对差值）、`bootstrap_frozen.json` |
| `figures/`、`report_assets/` | 报告用的四张图 |

| 没有 | 为什么 |
|---|---|
| 图像数据（约 1.4 GB） | 受 Kaggle 账号与许可限制，按下面的「取数」自取 |
| 模型权重（每个 43–94 MB） | 可重训（约 45 分钟/次），且单个文件接近 GitHub 上限 |
| 报告/幻灯片源文件 | 由 `tools/paper/` 生成，产物不随仓库发布 |

## 5 分钟自检（不需要显卡、不需要数据）

```bash
pip install -r requirements.txt
python tests/test_all.py             # 指标 / 划分器 / bootstrap 的数值自检
python tests/test_kaggle_download.py # 下载器自检（本地起 HTTP 服务，不需要账号）
```

最后一行应为 `all checks passed`。

## 不算训练，原地重算所有表格与图（纯 CPU）

这是组员「复测」最快的方式——`runs/` 里已经有逐图预测：

```bash
python src/report.py --runs "runs/*" --out results/          # 主表 + 配对差值
python src/figures.py --preds "runs/*/test_preds.csv" --out-dir figures/
python tools/bootstrap_frozen.py                             # 冻结阈值的配对区间
python tools/make_report_assets.py                           # 报告四联图
```

**注意**：`src/report.py` 在每次重采样里重估阈值（略乐观）；报告用的是
`tools/bootstrap_frozen.py`（阈值冻结），两者的差别在报告 §4.3 与附录里有说明。

## 完整复现（需要 ≥6 GB 显存）

```bash
# 1) 取数：Kaggle 账号 -> Settings -> Create New Token，把 token 存成 secrets/kaggle_token
python tools/kaggle_download.py --list                       # 先看数据集是否可见
python tools/kaggle_download.py --out data/train             # 支持断点续传
python tools/inspect_data.py --csv data/train.csv --img-dir data/train   # 数据体检，八问
python tools/resize_images.py --src data/train --dst data/train_256      # 1024 -> 256，可重跑

# 2) 冻结划分（可跳过，直接用 manifests/split_seed42.csv）
python src/split.py --csv data/train.csv --out manifests/split_seed42.csv --seed 42

# 3) 冒烟（2 分钟，验证路径 / 显存 / 权重下载）
python src/train.py --manifest manifests/split_seed42.csv --img-dir data/train_256 \
    --epochs 1 --limit-batches 5 --out-dir runs/_smoke

# 4) 五次训练（单卡 RTX 2060 Max-Q，合计约 3.4 GPU·小时）
python src/train.py --manifest manifests/split_seed42.csv --img-dir data/train_256 \
    --model efficientnet_b3 --loss bce   --epochs 12 --batch-size 16 --out-dir runs/b3_bce
python src/train.py ... --loss wbce  --out-dir runs/b3_wbce
python src/train.py ... --loss focal --out-dir runs/b3_focal
python src/train.py ... --model resnet50 --out-dir runs/r50_bce
python src/train.py ... --meta      --out-dir runs/b3_bce_meta

# 5) 评估 + 温度缩放（4 向翻转 TTA）
python src/evaluate.py --manifest manifests/split_seed42.csv --img-dir data/train_256 \
    --ckpt runs/b3_bce/best.pt --split test --out runs/b3_bce/test_preds.csv
python tools/fit_temperature.py --run-dir runs/b3_bce

# 6) 汇总与作图
python src/report.py --runs "runs/*" --out results/
python src/figures.py --preds "runs/*/test_preds.csv" --out-dir figures/
```

Windows 上也可以用 `scripts/` 里的一键脚本（`setup.ps1 → data.ps1 → train.ps1 → eval.ps1 → report.ps1`）。
这些脚本按「仓库 + 同级 data/runs/results 目录」定位路径（见 `scripts/_common.ps1`），
换机器只需把仓库放到任意目录即可，不会把缓存写到 C:。

## 目录

```
src/split.py        患者级划分：贪心 + 交换修复、断言校验、SHA-256（无 sklearn 依赖）
src/data.py         增强、13 维元数据编码（训练集拟合并序列化）、Dataset/DataLoader
src/models.py       timm backbone + 元数据融合头，单 logit 输出
src/losses.py       BCE / 逆患病率 BCE / 有效样本数 / focal
src/train.py        AMP、warmup+cosine、断点续训、逐 epoch CSV
src/evaluate.py     TTA 推理、temperature scaling、导出预测
src/metrics.py      纯 numpy：AUROC/AUPRC/pAUC/Brier/NLL/ECE/校准斜率/Sens@Spec/决策曲线
src/bootstrap.py    患者级配对 bootstrap，差值 CI
src/report.py       汇总所有 run -> results_long.csv / diffs.csv / results.md
src/figures.py      可靠性图 / ROC / 敏感度-特异度 / 决策曲线
tools/inspect_data.py     数据体检（八个问题，阻断性问题非零退出）
tools/resize_images.py    1024 -> 256 离线缩放（可断点重跑）
tools/kaggle_download.py  纯标准库 Bearer 下载器（不依赖 kaggle 包）
tools/fit_temperature.py  验证集拟合温度、应用到测试集
tools/bootstrap_frozen.py 阈值冻结的配对 bootstrap
tools/make_report_assets.py  报告四联图（纯 matplotlib）
tools/make_synthetic.py   同规模假数据：没数据时也能演练划分与统计
tools/bench_local.py      本机吞吐基准
tools/paper/              报告与幻灯片的生成脚本（build_report / build_slides / ...）
```

## 设计要点（为什么这样写）

| 决定 | 原因 |
|---|---|
| 患者级划分 + SHA-256 冻结 | 同一患者的多张图高度相似；按图切分会让 AUROC 虚高 3–8 点 |
| 划分器 = 贪心 + 交换修复 | 只做贪心时，重尾的患者规模会让患病率漂移（实测 test 1.76%→0.56%） |
| 阈值只在验证集选取并冻结 | 在测试集上找 80% 特异度再算敏感度 = 用测试集调参 |
| ECE 三种口径 + 校准斜率 | 1.76% 患病率下，全样本 ECE 被 98% 良性主导，常数预测器也能 <0.01 |
| 患者级**配对** bootstrap | 图像级重采样低估 CI；比较两个独立 CI 是否重叠会低估真实差异 |
| 温度缩放作为 H3 的操作化 | 单调变换，AUROC/Sens 不变，可判定失准是「尺度」还是「结构性」 |
| 元数据只用 age / sex / site | `diagnosis`、`tbp_lv_*` 是标签派生或临床不可得，用了就是泄漏 |

## 环境

Python 3.10.8 · PyTorch 2.6.0+cu124 · timm 1.0.9 · 单卡 RTX 2060 Max-Q（6 GB）
五次训练合计 3.4 GPU·小时；所有汇总与作图可在纯 CPU 上完成。

`timm 1.0.9` 会 `import huggingface_hub.repo_type_and_id_from_hf_id`，该符号在 hf_hub 2.x 被移除。
`src/hf_compat.py` 在 import timm 之前把它补回去，因此 0.2x 与 2.x 都能跑，无需降级。

## 已知限制

单次划分、单个随机种子（区间只含抽样噪声，不含 run 间方差）；仅 256 px；无 Grad-CAM；
有效样本数加权条件已实现但未训练（算力投给了元数据消融）。这些在报告的 §8 都写明了。

## 上传到 GitHub

仓库已经整理成可直接推送的形态（无 `.venv`、无数据、无权重、无凭据）。

```bash
cd melanoma_calib_github
git init -b main
git add .
git status                      # 确认没有 data/、runs/**/*.pt、secrets/
git commit -m "ISIC 2020 calibration-first benchmark: code, frozen split, predictions"
git remote add origin git@github.com:<org>/<repo>.git
git push -u origin main
```

两点提醒：

* **不要开 Git LFS**。`runs/**/*.pt` 已被 `.gitignore` 排除；权重（43–94 MB）建议放
  Release 或网盘，不要进历史。
* 若组员在 Windows 上克隆后跑 `scripts/*.ps1`，第一次需
  `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` 建 venv。

`docs/` 里放了由本仓库产出的两份报告 PDF（英文／中文），方便新加入的人先看结论再看代码。

## 引用与许可

```bibtex
@misc{melanoma_calib2026,
  title  = {Class-Balanced Losses Do Not Buy Sensitivity: A Calibration-First,
            Patient-Disjoint Benchmark on ISIC 2020},
  author = {Liu, Ke and Fu, Zeyu and Wang, Dong and Liu, Kai},
  year   = {2026},
  note   = {SDSC 6018 course project, City University of Hong Kong}
}
```

课程项目，仅供组内复测与教学使用。未附开源许可证（默认保留所有权利）；如需公开采用，
请自行添加 MIT 或 Apache-2.0 并补一份 LICENSE。
