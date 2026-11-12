# -*- coding: utf-8 -*-
"""Local-run guide: Windows + RTX 2060 Max-Q 6 GB, everything under S:\\CityUStudy."""
from __future__ import annotations

from docx.shared import Pt

from docx_kit import ACCENT, ACCENT2, BODY, MUTED, _fonts


def cover(k):
    doc = k.doc
    for _ in range(3):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)

    p = doc.add_paragraph()
    p.alignment = 1
    r = p.add_run("SDSC6018 · LOCAL RUN GUIDE")
    _fonts(r, BODY)
    r.font.size = Pt(10)
    r.bold = True
    r.font.color.rgb = ACCENT2

    p = doc.add_paragraph()
    p.alignment = 1
    p.paragraph_format.space_before = Pt(10)
    r = p.add_run("本机跑完整个项目")
    _fonts(r, BODY)
    r.font.size = Pt(26)
    r.bold = True
    r.font.color.rgb = ACCENT

    p = doc.add_paragraph()
    p.alignment = 1
    r = p.add_run("Windows + Ryzen 9 4900HS + RTX 2060 Max-Q 6 GB")
    _fonts(r, BODY)
    r.font.size = Pt(14)
    r.font.color.rgb = ACCENT2

    p = doc.add_paragraph()
    p.alignment = 1
    p.paragraph_format.space_before = Pt(6)
    r = p.add_run("数据、权重、缓存、结果全部放在 S: 盘工作区内")
    _fonts(r, BODY)
    r.font.size = Pt(11)
    r.font.color.rgb = MUTED

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(24)
    k.table(
        ["项目", "内容"],
        [
            ["适用机型", "Ryzen 9 4900HS（8C/16T）· RTX 2060 Max-Q 6 GB · 驱动 617.42 · sm_75"],
            ["操作系统", "Windows 10 / 11（命令行用 PowerShell）"],
            ["工作区", "`S:\\CityUStudy\\DSC6018_Project\\`（S: 剩余 ≈ 77 GB，C: 只剩 ≈ 20 GB）"],
            ["代码", "`melanoma_calib/`（含 `scripts/` 六个 PowerShell 脚本）"],
            ["配套文档", "`6018_Tutorial_Implementation_v2.docx`（方法与指标原理）；本文只讲「在本机怎么跑」"],
            ["预计总耗时", "装环境 40 分钟 · 取数 30 分钟–2 小时 · 训练两个晚上 · 评估与作图 30 分钟"],
        ],
        widths=[3.0, 13.2],
        size=9.2,
    )

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    k.tip(
        "先看第 0 章的算力账，确认「这台机器够用」再动手。"
        "如果你只想尽快看到第一个数字，直接跳到附录 A 的五条命令。"
    )
    k.page_break()


def ch0(k):
    k.h1("0", "先说结论：这台机器够跑完")

    k.p(
        "结论：**够，而且比免费 Colab 更省心**。整个项目需要的算力是约 10 个 GPU·小时，"
        "你的 2060 Max-Q 能提供大约 30–40 张/秒的训练吞吐，"
        "五个实验跑完是两个晚上——而且没有 4 小时断线、没有每日配额、随时可以 Ctrl+C 再 `--resume`。"
    )
    k.p(
        "唯一真正的限制是 **6 GB 显存**，它决定了 batch size 和分辨率，下面第 0.2 节给边界。",
        after=6,
    )

    k.h2("0.1　需求 vs 你有的")
    k.table(
        ["项", "项目要求", "你的机器", "判定"],
        [
            ["GPU", "支持 FP16、≥6 GB 显存（B3@256, batch 16）",
             "RTX 2060 Max-Q 6144 MiB，sm_75（Turing，有 tensor core）", "✅ 刚好够"],
            ["CPU", "≥4 核（DataLoader 喂图）", "Ryzen 9 4900HS，8 核 16 线程", "✅ 富余"],
            ["内存", "≥16 GB（workers=4 + 页缓存）", "建议确认一下；8 GB 就把 `--workers` 降到 2", "⚠️ 待确认"],
            ["磁盘", "≥15 GB（256 px 版）/ ≥45 GB（1024 原图 + 缩放）", "S: 剩余 77 GB", "✅"],
            ["Python", "3.9–3.12", "已装 3.10.8", "✅"],
            ["驱动", "任意支持 CUDA 12 的版本", "617.42", "✅"],
        ],
        widths=[1.6, 5.6, 6.6, 2.4],
        size=8.4,
        caption="表 0-1　硬件核对。6 GB 是唯一的硬边界，其余都有余量",
    )
    k.p(
        "顺带纠正一个小地方：你的 CPU 是 **4900HS**（35 W 版本），不是 4900H（45 W）。"
        "两者多核性能差约 10–15%，对训练影响很小——真正的瓶颈在 GPU 和显存上。",
        size=10,
    )

    k.h2("0.2　6 GB 显存的边界：能跑什么、不能跑什么")
    k.table(
        ["配置", "显存占用（估）", "结论"],
        [
            ["EfficientNet-B3 @256，batch 16，AMP", "≈5.2–6.0 GB", "✅ 推荐起点；OOM 就降到 12"],
            ["EfficientNet-B3 @256，batch 32，AMP", "≈9–11 GB", "❌ 放不下（Colab T4 的 16 GB 才行）"],
            ["EfficientNet-B3 @384，batch 12，AMP", "≈7–9 GB", "❌ 放不下；本机放弃 384 这条支线"],
            ["ResNet-50 @256，batch 32，AMP", "≈5.5–6.5 GB", "⚠️ 用 batch 24 更稳"],
            ["B3 @256 + 13 维元数据，batch 16", "≈5.4–6.1 GB", "✅ 元数据头只多约 20 K 参数"],
        ],
        widths=[6.6, 4.2, 5.4],
        size=8.4,
        caption="表 0-2　显存预算。数字是按参数/激活估算的量级，装好后用 tools/bench_local.py 实测确认",
    )
    k.warn(
        "不要开 `--img-size 384`。它在 T4 上只是慢 2.2 倍，在你的 6 GB 上直接 OOM；"
        "而这个分支对结论没有影响（第 0.3 节的时间表本来就是按 256 排的）。"
    )

    k.h2("0.3　时间账：两个晚上")
    k.table(
        ["实验", "模型 / 损失", "每 epoch", "12 epoch", "什么时候跑"],
        [
            ["`b3_bce`", "B3 / BCE", "≈10–13 min", "≈2.2–2.6 h", "第一晚 ①"],
            ["`b3_wbce`", "B3 / 逆患病率", "≈10–13 min", "≈2.2–2.6 h", "第一晚 ②"],
            ["`b3_focal`", "B3 / focal", "≈10–13 min", "≈2.2–2.6 h", "第二晚 ①"],
            ["`r50_bce`", "R50 / BCE", "≈5–6 min", "≈1.0–1.2 h", "第二晚 ②"],
            ["`b3_bce_meta`", "B3 / BCE + 元数据", "≈10–13 min", "≈2.3–2.7 h", "第二晚 ③"],
            ["合计", "5 个 run", "—", "≈9.5–11 h", "两个通宵，或分三晚"],
        ],
        widths=[3.2, 4.4, 2.8, 2.8, 3.0],
        size=8.4,
        caption="表 0-3　训练时间预算。吞吐按 2060 Max-Q 约 30–40 张/秒估（23,188 张/epoch）",
    )
    k.why(
        "为什么不用「一半的训练」？因为结论方向由**同一个模型**在三种损失间的差值决定，"
        "不同模型跑不同 epoch 会让差值混进训练程度的影响。宁可少做一个消融，也不要让两个条件不等长。"
    )

    k.h2("0.4　和 Colab 方案的差别")
    k.table(
        ["", "免费 Colab（T4 16 GB）", "本机（2060 Max-Q 6 GB）"],
        [
            ["单次会话", "约 4 小时硬中断", "想跑多久跑多久"],
            ["配额", "每天几小时，用完不给卡", "无（只费电）"],
            ["batch", "32 @256", "16 @256（慢约 2 倍/步，但步数不变）"],
            ["数据", "每次重下或挂 Drive（15 GB 不够放原图）", "下一次，永久放 S:"],
            ["中断代价", "最多丢一个 epoch，且可能当天没卡", "最多丢一个 epoch，立刻能续"],
            ["额外麻烦", "挂载、令牌、运行时重置", "Windows 电源/休眠/杀毒 + 驱动"],
        ],
        widths=[3.4, 6.4, 6.4],
        size=8.4,
        caption="表 0-4　两边真正的差别是「配额」与「机器要开着」，不是算力",
    )
    k.p(
        "本机唯一的新麻烦都在第 8 章那张排错表里：休眠把训练挂起、Defender 扫 33,000 个文件、"
        "Windows 的 DataLoader 多进程。这三条预处理掉，剩下的和 Colab 完全一样。",
    )
    k.page_break()


def ch1(k):
    k.h1("1", "目录：所有东西都放 S:")

    k.p(
        "你的 C: 只剩 20 GB，而 torch 的 CUDA 轮子加数据就能吃掉 35 GB——"
        "所以这篇文档里所有路径都指向 `S:\\CityUStudy\\DSC6018_Project\\`，包括 pip 缓存和 timm 权重缓存。"
    )
    k.code(
        "S:\\CityUStudy\\DSC6018_Project\\\n"
        "  melanoma_calib\\                 代码（10 个模块 + tests + tools + scripts）\n"
        "    .venv\\                        Python 3.10 虚拟环境（torch 装在这里，≈6 GB）\n"
        "    scripts\\                      setup / data / train / eval / report 五个脚本\n"
        "    manifests\\split_seed42.csv    冻结的患者级划分（含 sha256）\n"
        "  data\\                           图像与元数据\n"
        "    train.csv                     官方元数据（33,126 行）\n"
        "    train_256\\                    训练实际读取的 256 px 图（≈3.5 GB）\n"
        "  runs\\                           每个实验一个目录\n"
        "    b3_bce\\  b3_wbce\\  b3_focal\\  r50_bce\\  b3_bce_meta\\\n"
        "  results\\                        三张结果表\n"
        "  figures\\panel.png               四联图\n"
        "  secrets\\access_token            Kaggle 令牌（一行 KGAT_...，不要提交）\n"
        "  .cache\\pip  .cache\\torch        pip 轮子缓存与 timm 预训练权重",
        title="工作区结构",
    )
    k.table(
        ["环境变量", "指向", "为什么必须改"],
        [
            ["`PIP_CACHE_DIR`", "`S:\\...\\.cache\\pip`", "默认在 C:\\Users\\…\\AppData，torch 轮子会留 2–3 GB"],
            ["`TORCH_HOME`", "`S:\\...\\.cache\\torch`", "timm 的 ImageNet 权重默认下到 C: 的用户目录"],
            ["`HF_HOME`", "`S:\\...\\.cache\\hf`", "以防某个依赖改用 huggingface hub"],
            ["`KAGGLE_API_TOKEN`", "读 `secrets\\access_token`", "令牌文件也不必落在 C:"],
        ],
        widths=[3.8, 5.2, 7.2],
        size=8.4,
        caption="表 1-1　`scripts\\_common.ps1` 已经替你设好前三个，第四个在 data.ps1 里读",
    )
    k.p(
        "脚本用 `$PSScriptRoot` 定位自己，所以**从哪个目录调用都行**，不用先 `cd`。"
        "但 Python 侧我仍然全部传绝对路径（`--img-dir`、`--out-dir`），避免上次那种「换个目录就找不到文件」的问题。",
    )
    k.page_break()


def ch2(k):
    k.h1("2", "第 1 步：装环境（约 40 分钟）")

    k.h2("2.1　先确认三件事")
    k.code(
        "py -3.10 -V                     # 期望 Python 3.10.x\n"
        "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv\n"
        "Get-PSDrive S | Select-Object Used,Free      # 期望 Free > 40 GB",
        title="PowerShell",
    )
    k.p(
        "如果 `py -3.10` 不存在，去 python.org 装 3.10 并勾选 py launcher；"
        "`nvidia-smi` 找不到说明驱动没装好，先装 NVIDIA 驱动（617.42 已足够新）。",
    )

    k.h2("2.2　一键装：scripts\\setup.ps1")
    k.p(
        "它做四件事：在 S: 建虚拟环境、装 **CUDA 版** torch、装 timm/`huggingface_hub`/matplotlib、"
        "验证 GPU 并试建一次 EfficientNet-B3（顺带把 ImageNet 权重下下来）。",
        after=4,
    )
    k.code(
        "cd S:\\CityUStudy\\DSC6018_Project\\melanoma_calib\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\setup.ps1\n"
        "\n"
        "# 下载慢时换 PyPI 镜像（torch 仍走官方 index，见下）\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\setup.ps1 `\n"
        "    -PipIndex https://pypi.tuna.tsinghua.edu.cn/simple",
        title="PowerShell",
    )
    k.warn(
        "**PyPI 上的 torch 是 CPU 版**（Windows 默认不带 CUDA）。直接 `pip install torch` 会装出"        "一个 `cuda available: False` 的环境，然后你会花半天怀疑驱动。必须走 "
        "`--index-url https://download.pytorch.org/whl/cu124`——脚本已经这么写了。"
    )
    k.p("等价的纯手工命令（想自己控制时用）：", after=2)
    k.code(
        "py -3.10 -m venv .venv\n"
        ".venv\\Scripts\\python.exe -m pip install --upgrade pip\n"
        "set PIP_CACHE_DIR=S:\\CityUStudy\\DSC6018_Project\\.cache\\pip\n"
        "set TORCH_HOME=S:\\CityUStudy\\DSC6018_Project\\.cache\\torch\n"
        ".venv\\Scripts\\python.exe -m pip install torch torchvision `\n"
        "    --index-url https://download.pytorch.org/whl/cu124\n"
        ".venv\\Scripts\\python.exe -m pip install \"timm==1.0.9\" huggingface_hub pandas numpy matplotlib Pillow",
        title="cmd（每行单独执行）",
    )

    k.h2("2.3　验证：三个数字都对才算装好")
    k.code(
        ".venv\\Scripts\\python.exe -c \"import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))\"",
        title="PowerShell",
    )
    k.code(
        "2.5.1+cu124  12.4  True  NVIDIA GeForce RTX 2060 with Max-Q Design",
        title="期望输出（版本号可能更新，关键是 True 和卡名）",
    )

    k.h2("2.4　基准：把「估计」换成「实测」")
    k.p(
        "`tools/bench_local.py` 不下载权重、不碰数据，只跑几十步前向反向，测出峰值显存与吞吐。"
        "这一步决定了你该用 batch 16 还是 12，也决定了第 0.3 节那张时间表要不要修正。",
        after=4,
    )
    k.code(
        ".venv\\Scripts\\python.exe tools\\bench_local.py --sweep --img-size 256",
        title="PowerShell · 约 1 分钟",
    )
    k.code(
        "gpu      : NVIDIA GeForce RTX 2060 with Max-Q Design  6.0 GB  sm_75\n"
        "settings : efficientnet_b3 @ 256px, amp=fp16, meta=False\n"
        "\n"
        "batch  32 : OOM\n"
        "batch  24 : OOM\n"
        "batch  16 :   34.2 img/s   peak  5.61 GB   epoch(23,188)  11.3 min   12 epochs 135.6 min\n"
        "batch  12 :   31.8 img/s   peak  4.42 GB   epoch(23,188)  12.2 min   12 epochs 145.9 min\n"
        "batch   8 :   27.5 img/s   peak  3.21 GB   epoch(23,188)  14.1 min   12 epochs 168.7 min",
        title="预期输出形状（数值是你的机器实测值，我这边没有 GPU 无法代跑）",
    )
    k.check(
        "把「没有 OOM 的最大 batch」和「它对应的 12 epochs 分钟数」抄进表 0-3，"
        "然后用 `scripts\\train.ps1 -Batch <那个值>` 训练。若 16 就 OOM，用 12——不要为此改分辨率。"
    )
    k.why(
        "为什么 batch 从 16 降到 12 吞吐只掉 7%？因为 6 GB 的卡在 256² 上主要受显存带宽限制，"
        "而不是 batch 大小；只要 batch ≥8，AMP 的 tensor core 利用率就够。这也是为什么「降 batch」比「降分辨率」划算。"
    )

    k.h2("2.5　装环境阶段的四个坑")
    k.table(
        ["症状", "原因", "处理"],
        [
            ["`torch.cuda.is_available()` 是 False", "装成了 CPU 版 torch", "卸掉重装：`pip uninstall -y torch`，再按 2.2 走官方 index"],
            ["`OSError: [WinError 126] 找不到指定的模块`", "缺 VC++ 运行库或 torch 与 Python 版本不匹配", "装 Microsoft VC++ 2015-2022 x64 运行库；确认 venv 是 3.10"],
            ["`pip` 下载停在 40% 不动", "到 download.pytorch.org 的链路慢", "换镜像：`https://mirror.sjtu.edu.cn/pytorch-wheels/cu124`"],
            ["装完 C: 少了好几 GB", "缓存没重定向", "删 `C:\\Users\\<你>\\AppData\\Local\\pip\\cache`；确认 `PIP_CACHE_DIR` 生效"],
        ],
        widths=[5.0, 5.2, 6.0],
        size=8.3,
        caption="表 2-1　装环境阶段的四个坑",
    )
    k.page_break()


def ch3(k):
    k.h1("3", "第 2 步：取数据（30 分钟 – 2 小时）")

    k.h2("3.1　令牌：一行 KGAT_，放 S: 盘")
    k.p(
        "打开 <https://www.kaggle.com/settings/api> → **Generate New Token** → 复制得到的 `KGAT_...`，"
        "存成**文件**（不是文件夹）——路径如下，内容只有一行，不带引号、不带中文、不多行：",
        after=4,
    )
    k.code(
        "S:\\CityUStudy\\DSC6018_Project\\secrets\\access_token",
        title="文件位置（内容就是那一行 KGAT_...）",
    )
    k.p("两种建法，任选一种（都保证它是**文件**而不是目录）：", after=4)
    k.code(
        "# A. 一行写完（把自己那串粘进去，注意是单引号）\n"
        "Set-Content -Path S:\\CityUStudy\\DSC6018_Project\\secrets\\access_token `\n"
        "            -Value 'KGAT_你的令牌' -Encoding ascii -NoNewline\n"
        "\n"
        "# B. 记事本：新建【文本文件】，文件名写 access_token（去掉 .txt）\n"
        "notepad S:\\CityUStudy\\DSC6018_Project\\secrets\\access_token\n"
        "\n"
        "# 验证：必须是 True / True，且前 6 位是 KGAT_\n"
        "$f = 'S:\\CityUStudy\\DSC6018_Project\\secrets\\access_token'\n"
        "(Test-Path $f -PathType Leaf); ((Get-Content $f -Raw).Trim() -match '^KGAT_[A-Za-z0-9_-]+$')",
        title="PowerShell",
    )
    k.warn(
        "**最常见的错法**：把 `access_token` 建成了**文件夹**。这时 `Get-Content` 报的是"
        "「对路径…的访问被拒绝 / UnauthorizedAccessException」，看起来像权限问题，其实是类型问题——"
        "PowerShell 读目录时报的就是「访问被拒绝」。判据一行：`Test-Path $f -PathType Leaf` 为 False 就是文件夹。"
        "修法：`Remove-Item $f -Recurse -Force` 之后按上面 A 或 B 重建。",
        extra="access_token 是文件夹",
    )
    k.p(
        "脚本会读它并设成 `KAGGLE_API_TOKEN` 环境变量，所以令牌不必进 `C:\\Users\\<你>\\.kaggle\\`。"
        "⚠️ 这个文件等价于密码：不要提交、不要贴进聊天；`secrets/` 已经在 `.gitignore` 里。",
        size=10,
    )
    k.p("还要做一步网页操作：打开比赛页 <https://www.kaggle.com/c/siim-isic-melanoma-classification> → 点 **Join / Accept Rules**，否则下载 `train.csv` 会 403。", size=10)

    k.h2("3.2　两条路线，先跑哪条")
    k.table(
        ["路线", "下载量", "耗时", "适合"],
        [
            ["`-Route 256`（推荐）", "≈3.5 GB", "10–30 分钟", "先跑通全流程；训练只需要 256 px"],
            ["`-Route 1024`", "≈30 GB", "1–3 小时（含缩放 20–40 分钟）", "以后想试 384 px，或想自己重做缩放"],
        ],
        widths=[4.4, 3.2, 3.6, 5.0],
        size=8.4,
        caption="表 3-1　两条取数路线。建议先 256，把流程跑通再考虑 1024",
    )

    k.h2("3.3　一键取数：scripts\\data.ps1")
    k.code(
        "cd S:\\CityUStudy\\DSC6018_Project\\melanoma_calib\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\data.ps1              # 256 px\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\data.ps1 -Route 1024  # 原图 + 缩放",
        title="PowerShell",
    )
    k.p("它按顺序做五件事，每步都会打印结果：", after=4)
    k.steps([
        "读 `secrets\\access_token` 并校验（必须是**文件**、非空、形如 `KGAT_...`）。",
        "下 `train.csv`（元数据）并解压到 `data\\`。",
        "下图像：256 路线直接解压到 `data\\train_256`（自动把层级不一致的 `train` 目录搬正）；"
        "1024 路线下到 `data\\train` 再调 `resize_images.py` 缩到 256。",
        "跑 `tools\\inspect_data.py`：行数 33,126、阳性 584、患者 2,056，缺图立即失败。",
        "跑 `src\\split.py`：生成 `manifests\\split_seed42.csv` 并打印 sha256。",
    ])
    k.why(
        "下载用的是自带的 `tools\\kaggle_download.py`，**不是** `kaggle` 命令行。原因是 kaggle 1.7.x "
        "在 `import` 时就会 `os.makedirs(C:\\Users\\<你>\\.kaggle)`，在部分机器上直接 `PermissionError: [WinError 5]`，"
        "而且 1.7.x 还不认 `KGAT_` 令牌。自带下载器只用标准库 `urllib` 发一个 `Authorization: Bearer` 请求，"
        "没有 `~/.kaggle`、没有版本约束、30 GB 也能 `--resume` 续传。"
    )
    k.code(
        "        images  patients  melanomas  prevalence\n"
        "train  22784.0    1581.0      385.0      0.0169\n"
        "val     3304.0     287.0       85.0      0.0257\n"
        "test    7038.0     188.0      114.0      0.0162\n"
        "sha256   -> 7703ba50...",
        title="第 5 步的预期输出（真实数据形状相同，数值略有出入）",
    )
    k.tip(
        "**把 sha256 抄下来**，写进 README 和报告 Methods。它是「所有实验用的是同一份划分」的唯一凭据，"
        "也是这个项目最便宜的可复现性证明。"
    )

    k.h2("3.4　取数阶段的坑")
    k.table(
        ["症状", "原因", "处理"],
        [
            ["`403 Forbidden`", "没在比赛页 Accept Rules", "网页点 Join 后重跑"],
            ["`401 Unauthorized`", "令牌无效或粘错", "确认 `secrets\\access_token` 只有一行、`isascii()` 为真"],
            ["`Get-Content : 对路径…access_token 的访问被拒绝`", "`access_token` 是**文件夹**而不是文件",
             "`Test-Path $f -PathType Leaf` 为 False 即是；删掉后用 `Set-Content` 重建"],
            ["`PermissionError: [WinError 5] … \\.kaggle`", "kaggle 1.7.x 在 import 时往用户目录建 `.kaggle`，被系统策略拒绝",
             "不用 kaggle CLI：`tools\\kaggle_download.py` 走 Bearer，无需该目录（`_common.ps1` 也已把 `KAGGLE_CONFIG_DIR` 指到 S:）"],
            ["`no *.jpg files under ...`", "解压层级不是 `train`", "`Get-ChildItem data -Recurse -Directory -Depth 2` 看真实层级"],
            ["`train.csv` 只有几十行", "下成了 sample_submission", "删掉重下，确认 33,126 行"],
            ["磁盘满", "1024 路线 + 输出", "S: 需要 ≥45 GB；`-Route 256` 只要 15 GB"],
        ],
        widths=[5.0, 4.8, 6.4],
        size=8.3,
        caption="表 3-2　取数阶段的五个坑",
    )
    k.page_break()


def ch4(k):
    k.h1("4", "第 3 步：冒烟测试（5 分钟）")

    k.p(
        "在花两个晚上之前，先用 5 分钟走完「训练 → 验证 → 存盘 → 续训」的全流程。"
        "它抓的是路径、显存、权重下载、元数据列名这类问题。",
    )
    k.code(
        "powershell -ExecutionPolicy Bypass -File scripts\\train.ps1 -Smoke -Batch 16",
        title="PowerShell",
    )
    k.code(
        "== b3_bce  ->  S:\\CityUStudy\\DSC6018_Project\\runs\\_smoke\n"
        "n_pos=408  n_neg=22780  pos:neg = 1:55.8\n"
        "  bce     : pos_weight = 1.0\n"
        "  ...\n"
        "efficientnet_b3: 11.1M total / 11.1M trainable\n"
        "100%|##########| 5/5 [00:12<00:00]\n"
        "epoch 00 loss 0.0612 auroc 0.8712 auprc 0.2084 sens80 0.312 * (41s)\n"
        "done. best val_auprc = 0.2084",
        title="预期输出形状（5 个 batch 就结束；数字随初始化变化）",
    )
    k.check(
        "`runs\\_smoke\\` 下出现 `log.csv`、`last.pt`、`best.pt`、`cfg.json`、`console.log` 五个文件。"
        "再跑一次同命令加 `-Resume`，应打印 `resumed at epoch 1`。"
    )
    k.warn(
        "冒烟若报 `CUDA out of memory`，把 `-Batch` 降到 12 重试；还不行就 8。"
        "**不要**改成 128 分辨率来省显存——那会让所有数字失去可比性。"
    )
    k.h2("4.1　三条排查开关")
    k.p(
        "冒烟失败时不要盲猜，按下面顺序二分。三个开关都能和 `-Smoke` 组合：",
        after=4,
    )
    k.table(
        ["开关", "作用", "在排除什么"],
        [
            ["`-Workers 0`", "关闭多进程 DataLoader", "Windows 下的 `spawn` / 句柄 / 卡死问题"],
            ["`-NoPretrained`", "跳过 ImageNet 权重，随机初始化", "huggingface.co 下载不通；只验证管线，指标不可用"],
            ["`-HfMirror`", "设 `HF_ENDPOINT=https://hf-mirror.com`", "国内网络取不到 timm 权重（最省事的修法）"],
        ],
        widths=[3.2, 6.0, 7.2],
        size=8.4,
        caption="表 4-1　排查开关。先 `-NoPretrained` 确认代码没问题，再 `-HfMirror` 把权重拿下来",
    )
    k.code(
        "# 1) 先证明「不是代码问题」：不联网也能跑完 5 个 batch\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\train.ps1 -Smoke -NoPretrained -Workers 0\n"
        "\n"
        "# 2) 再证明「权重能拿到」\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\train.ps1 -Smoke -HfMirror\n"
        "\n"
        "# 3) 都通过后再跑正式的一小时级别训练\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\train.ps1 -Run b3_bce -Batch 16",
        title="PowerShell",
    )
    k.why(
        "`train.ps1` 现在用 `cmd /c \"... 2>&1\"` 把 Python 的 stderr 并进 stdout 再 tee。"
        "之前的写法是 `& python ... 2>&1 | Tee-Object`：PowerShell 会把**每一行 stderr** 包成 ErrorRecord，"
        "配合 `_common.ps1` 里的 `$ErrorActionPreference = \"Stop\"`，脚本在第一行 `Traceback (most recent call last):` "
        "处就终止了——真正的异常行根本没打印出来。失败时它还会额外打印 `console.log` 的最后 30 行。"
    )
    k.p(
        "如果仍然只看到一行 traceback，直接在仓库目录跑原始命令，让 Python 自己输出到终端：",
        after=2,
    )
    k.code(
        "cd S:\\CityUStudy\\DSC6018_Project\\melanoma_calib\n"
        ".venv\\Scripts\\python.exe src\\train.py `\n"
        "  --manifest manifests\\split_seed42.csv `\n"
        "  --img-dir S:\\CityUStudy\\DSC6018_Project\\data\\train_256 `\n"
        "  --out-dir S:\\CityUStudy\\DSC6018_Project\\runs\\_smoke `\n"
        "  --epochs 1 --limit-batches 5 --batch-size 16 --workers 0",
        title="PowerShell · 看完整 traceback 的最小命令",
    )
    k.page_break()


def ch5(k):
    k.h1("5", "第 4 步：五个实验（两个晚上）")

    k.h2("5.1　一条命令跑一个实验")
    k.code(
        "powershell -ExecutionPolicy Bypass -File scripts\\train.ps1 -Run b3_bce -Batch 16",
        title="PowerShell",
    )
    k.p(
        "`scripts\\train.ps1` 把 run 名映射到「模型 / 损失 / 是否用元数据」，"
        "并固定把输出写到 `runs\\<name>\\`，同时在 `console.log` 里留一份控制台记录。",
        after=4,
    )
    k.table(
        ["run 名", "模型", "损失", "元数据", "预计"],
        [
            ["`b3_bce`", "efficientnet_b3", "bce", "无", "2.2–2.6 h"],
            ["`b3_wbce`", "efficientnet_b3", "wbce（逆患病率）", "无", "2.2–2.6 h"],
            ["`b3_focal`", "efficientnet_b3", "focal", "无", "2.2–2.6 h"],
            ["`r50_bce`", "resnet50", "bce", "无", "1.0–1.2 h"],
            ["`b3_bce_meta`", "efficientnet_b3", "bce", "有", "2.3–2.7 h"],
            ["`b3_cb`", "efficientnet_b3", "cb（有效样本数）", "无", "2.2–2.6 h（加分项）"],
        ],
        widths=[3.4, 4.4, 4.2, 2.2, 3.4],
        size=8.4,
        caption="表 5-1　五个必需 + 一个加分。加 `-All` 会按顺序跑前五个",
    )

    k.h2("5.2　两个晚上的排法")
    k.table(
        ["时间", "做什么", "备注"],
        [
            ["第一晚 20:00", "`-Run b3_bce`", "参照线，最想先看到数字"],
            ["第一晚 23:00", "`-Run b3_wbce`", "主假设；睡觉前启动，第二天早上收"],
            ["第二天 09:00", "看两个 `log.csv`，确认 val AUROC 落在 0.85–0.92", "超出就排查（表 8-1）"],
            ["第二晚 19:00", "`-Run b3_focal`", ""],
            ["第二晚 22:00", "`-Run r50_bce`", "最便宜的消融，先跑"],
            ["第二晚 23:30", "`-Run b3_bce_meta`", "睡觉前启动"],
            ["第三天 09:00", "`scripts\\eval.ps1`", "约 20 分钟（含 TTA 推理）"],
        ],
        widths=[3.2, 8.0, 5.0],
        size=8.4,
        caption="表 5-2　三晚的排法。机器不用关，但电源、休眠、更新要先处理（5.4 节）",
    )

    k.h2("5.3　中断了怎么办")
    k.p(
        "免费 Colab 会断线，本机也会：关机、Windows 更新、蓝屏、你不小心合盖。"
        "流程固定成三步：",
        after=4,
    )
    k.steps([
        "看进度：`Get-Content runs\\b3_bce\\log.csv -Tail 3` 确认最后一个完成的 epoch。",
        "续训：`scripts\\train.ps1 -Run b3_bce -Batch 16 -Resume`。学习率按全局 step 续，不会重新 warmup。",
        "只有 `last.pt` 损坏时才从头跑；`log.csv` 会追加，不会重复写表头。",
    ])

    k.h2("5.4　跑之前必须处理的四件事")
    k.table(
        ["事项", "命令 / 操作", "不做的后果"],
        [
            ["插电 + 高性能电源计划", "设置 → 电源 → 最佳性能；`powercfg /change standby-timeout-ac 0`", "合盖或闲置 15 分钟后训练被挂起"],
            ["关闭 Windows 自动更新重启", "设置 → Windows 更新 → 暂停更新 7 天", "跑到第 9 个 epoch 被重启杀掉"],
            ["Defender 排除数据与 runs 目录", "Windows 安全中心 → 病毒防护 → 排除项，加 `S:\\CityUStudy\\DSC6018_Project`", "33,000 次文件扫描，吞吐掉 30–50%"],
            ["垫高机身 / 别放床上", "—", "Max-Q 在 65 W 上限下会热降频，吞吐掉 20%+"],
        ],
        widths=[4.2, 6.6, 5.4],
        size=8.3,
        caption="表 5-3　四件「不做就白跑」的事",
    )
    k.tip(
        "训练期间别开游戏/浏览器硬件加速——显存被别的程序占着，B3@batch16 会直接 OOM。"
        "先 `nvidia-smi` 看一眼 `Memory-Usage`，剩 6 GB 再启动。"
    )
    k.page_break()


def ch6(k):
    k.h1("6", "第 5 步：评估与温度缩放（20 分钟）")

    k.p(
        "训练完的 `best.pt` 不直接进报告。要先在 val 和 test 上各推理一次（4 向翻转 TTA），"
        "再用 val 拟合一个温度标量、应用到 test——这是「校准能不能修」这个问题的唯一证据。",
    )
    k.code(
        "powershell -ExecutionPolicy Bypass -File scripts\\eval.ps1",
        title="PowerShell · 对 runs\\ 下所有含 best.pt 的目录逐个处理",
    )
    k.p("每个 run 目录会多出五个文件：", after=4)
    k.table(
        ["文件", "内容"],
        [
            ["`val_preds.csv`", "3,313 行：image_name / patient_id / target / prob"],
            ["`test_preds.csv`", "6,625 行，同上"],
            ["`test_preds_metrics.json`", "该模型在 test 上的完整指标（含校准斜率）"],
            ["`test_preds_temp.csv`", "温度缩放后的 test 预测"],
            ["`temperature.json`", "最优 T，以及缩放前后的指标对照"],
        ],
        widths=[5.0, 11.2],
        size=8.4,
        caption="表 6-1　评估阶段的产品。后两个是「温度缩放」这个第四条件",
    )
    k.code(
        "run            : S:\\CityUStudy\\DSC6018_Project\\runs\\b3_wbce\n"
        "optimal T (val): 2.41   (over-confident before scaling)\n"
        "1/T            : 0.415   should be close to cal_slope before scaling (0.41)\n"
        "\n"
        "metric              before     after     delta\n"
        "auroc               0.8891    0.8891   +0.0000\n"
        "auprc               0.2714    0.2714   +0.0000\n"
        "brier               0.0171    0.0163   -0.0008\n"
        "ece_adaptive15      0.0412    0.0131   -0.0281\n"
        "sens_at_spec80      0.4786    0.4786   +0.0000\n"
        "cal_slope           0.4102    0.9881   +0.5779",
        title="预期输出（数字是示意；两个 +0.0000 是理论保证，不是巧合）",
    )
    k.why(
        "AUROC / AUPRC / Sens@Spec80 在缩放前后**必然完全不变**，因为温度缩放是严格单调变换。"
        "所以只要 `after` 那三行有任何一位不同，就说明代码错了（比如对 test 重算了阈值）。"
        "这是这两步最有用的一条自检。"
    )
    k.p(
        "T 与斜率的关系：`1/T ≈ 缩放前的 cal_slope`。上例 1/2.41 = 0.415，斜率 0.410——对得上，"
        "说明校准损坏主要来自「尺度」；如果两者差很多，说明还有系统性的先验偏移（截距 ≠ 0）。",
    )
    k.page_break()


def ch7(k):
    k.h1("7", "第 6 步：结果表与图（10 分钟）")

    k.code(
        "powershell -ExecutionPolicy Bypass -File scripts\\report.ps1 -Boot 2000",
        title="PowerShell · CPU 即可，约 1–2 分钟",
    )
    k.table(
        ["输出", "内容", "写报告时用在哪"],
        [
            ["`results\\results_long.csv`", "每个模型 × 每个指标：点估计 + 95% CI", "核心结果表"],
            ["`results\\diffs.csv`", "与参照模型的配对差值、CI、双侧 p", "「谁更好」的唯一合法证据"],
            ["`results\\results.md`", "上面两张的 markdown 版", "直接粘进报告"],
            ["`results\\summary.json`", "含校准斜率/截距的完整指标", "附录与复核"],
            ["`figures\\panel.png`", "可靠性图 / ROC / 敏感度-特异度 / 决策曲线", "报告 §5 的四联图"],
        ],
        widths=[4.6, 7.0, 4.6],
        size=8.4,
        caption="表 7-1　最后一步的五个产出",
    )
    k.p(
        "这一步之前的所有中间产物都在 `runs\\` 里，所以**图可以反复重画**，不需要再碰 GPU。"
        "报告写到一半发现图不好看，改 `src\\figures.py` 重跑这条命令即可。",
    )
    k.check(
        "`diffs.csv` 的 `contrast` 以参照模型（默认 `b3_bce`）开头；"
        "每个模型的点估计都落在自己的 CI 内；`panel.png` 四张子图都非空。"
    )
    k.page_break()


def ch8(k):
    k.h1("8", "本地排错表")

    k.table(
        ["症状", "原因", "处理"],
        [
            ["`CUDA out of memory`（冒烟就出现）", "batch 太大", "`-Batch 12`；关掉占显存的程序；`nvidia-smi` 确认空载"],
            ["`Traceback` 只打印第一行就中断", "PowerShell 把 stderr 当 ErrorRecord + `$ErrorActionPreference=Stop`",
             "已修：`train.ps1` 改用 `cmd /c \"... 2>&1\"`；或按 4.1 直接跑原始 python 命令"],
            ["`RuntimeError: Hugging Face hub model specified but package not installed`",
             "**不是没装**：`huggingface_hub 2.x` 删掉了 timm 1.0.9 依赖的 `repo_type_and_id_from_hf_id`，"
             "timm 把这个 ImportError 吞掉后报成「没装」",
             "已由 `src/hf_compat.py` 在导入时补回该符号（对 0.2x/2.x 都有效，无需降级）；"
             "验证 `python -c \"import sys;sys.path.insert(0,'src');import models; from timm.models import _hub; print(_hub._has_hf_hub)\"`"],
            ["`OSError … huggingface.co` / 下载权重卡住", "timm 取 ImageNet 权重需要访问 HF", "`-HfMirror`；或先 `-NoPretrained` 验证管线"],
            ["日志中文变乱码（`鈶?璁?`）", "PowerShell 5.1 用 GBK 解码 Python 的 UTF-8 输出",
             "已修：`_common.ps1` 把 `[Console]::OutputEncoding` 设为 UTF-8；日志文件本身一直是对的"],
            ["训练到第 3 个 epoch 变慢一半", "热降频或 Defender 扫描", "垫高散热；把 `S:\\CityUStudy\\DSC6018_Project` 加进 Defender 排除项"],
            ["合盖后回来发现训练停在第 k epoch", "休眠挂起了进程", "`powercfg /change standby-timeout-ac 0`；`-Resume` 续训"],
            ["`RuntimeError: DataLoader worker ... exited unexpectedly`", "Windows 下多进程 + 显存/文件句柄", "`-Workers 2`；仍失败则 0（慢 20%）"],
            ["`BrokenPipeError` / 训练进程莫名消失", "终端被关掉，子进程随之终止", "用 `Start-Process` 独立窗口，或训练时别关终端"],
            ["`torch.cuda.is_available()` False", "CPU 版 torch 或驱动问题", "重装 cu124 轮子；`nvidia-smi` 能跑说明驱动 OK"],
            ["`FileNotFoundError: ...best.pt`", "run 名拼错或训练没完成", "`Get-ChildItem runs -Recurse -Filter best.pt`"],
            ["val AUROC 只有 0.6–0.7", "图像与标签错位（最常见）", "`tools\\inspect_data.py --img-dir ...` 重新体检"],
            ["两个实验数字完全相同", "第二次复用了第一次的 `--out-dir`", "确认 run 名不同；`cfg.json` 里能看到 `model/loss`"],
            ["`kaggle` 命令找不到", "装到系统 Python 而不是 venv", "用 `.venv\\Scripts\\python.exe -m kaggle ...`"],
            ["磁盘满", "1024 原图 + 中间产物", "只保留 `data\\train_256`，删 `data\\train`（原图）"],
            ["想换分辨率重跑", "—", "不要。256 是协议的一部分，换分辨率所有数字不可比"],
        ],
        widths=[5.4, 4.6, 6.2],
        size=8.2,
        caption="表 8-1　本地特有的十二个故障。前四条几乎必然遇到",
    )
    k.page_break()


def ch9(k):
    k.h1("9", "检查清单")

    items = [
        ("01", "`py -3.10 -V` 与 `nvidia-smi` 都正常"),
        ("02", "虚拟环境在 `S:\\...\\melanoma_calib\\.venv`，不在 C:"),
        ("03", "`torch.cuda.is_available()` 为 True，卡名是 RTX 2060"),
        ("04", "`tools\\bench_local.py --sweep` 跑过，知道最大 batch 与每 epoch 分钟数"),
        ("05", "`secrets\\access_token` 只有一行 `KGAT_`，且没有提交到仓库"),
        ("06", "`data\\train.csv` 33,126 行，`data\\train_256` 有 33,126 张图"),
        ("07", "`tools\\inspect_data.py` 打印 `[ok] no blocking problem found`"),
        ("08", "`manifests\\split_seed42.csv` 已生成，sha256 已记录"),
        ("09", "`-Smoke` 通过，`runs\\_smoke` 里有五个文件"),
        ("10", "`-Resume` 能从 epoch k 接续"),
        ("11", "电源计划为高性能、休眠已关、更新已暂停、Defender 已排除"),
        ("12", "五个 run 目录都有 `log.csv`/`last.pt`/`best.pt`/`cfg.json`"),
        ("13", "`b3_bce` 的 val AUROC 落在 0.85–0.92"),
        ("14", "每个 run 都有 `val_preds.csv` 与 `test_preds.csv`"),
        ("15", "温度缩放的 AUROC/AUPRC/Sens 三行 delta 全为 0.0000"),
        ("16", "`1/T` 与缩放前 `cal_slope` 大致相等"),
        ("17", "`results\\diffs.csv` 是配对差值，不是「两个 CI 是否重叠」"),
        ("18", "`figures\\panel.png` 四张子图都非空"),
        ("19", "报告 Methods 写了 sha256、阈值来自 val、温度来自 val"),
        ("20", "`runs\\` 与 `data\\` 都不在 C: 盘"),
    ]
    k.table(["#", "检查项", "☑"], [[n, t, "☐"] for n, t in items],
            widths=[1.0, 13.4, 1.8], size=8.4, caption="表 9-1　20 项本地交付检查")
    k.check("20 项全勾之后，报告里的每个数字都能在 `runs\\` 里找到对应文件。")
    k.page_break()


def appendix(k):
    k.h1("附录 A", "五条命令跑完全程")

    k.code(
        "# 0) 一次性：建环境（40 分钟，主要在下 torch）\n"
        "cd S:\\CityUStudy\\DSC6018_Project\\melanoma_calib\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\setup.ps1\n"
        "\n"
        "# 1) 一次性：取数 + 体检 + 冻结划分（10–30 分钟）\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\data.ps1\n"
        "\n"
        "# 2) 冒烟（5 分钟）\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\train.ps1 -Smoke\n"
        "\n"
        "# 3) 训练（两个晚上；中断就用 -Resume 续）\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\train.ps1 -Run b3_bce -Batch 16\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\train.ps1 -All -Batch 16\n"
        "\n"
        "# 4) 评估 + 温度缩放（20 分钟）\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\eval.ps1\n"
        "\n"
        "# 5) 结果表 + 四联图（2 分钟）\n"
        "powershell -ExecutionPolicy Bypass -File scripts\\report.ps1",
        title="全部命令",
    )

    k.h1("附录 B", "和 Colab 版要改的六处")
    k.table(
        ["项", "Colab 教程里的写法", "本机写法"],
        [
            ["路径", "`/content/...` 与 `/content/drive/MyDrive/...`", "`S:\\CityUStudy\\DSC6018_Project\\...`"],
            ["batch", "`--batch-size 32`", "`--batch-size 16`（6 GB 显存）"],
            ["workers", "`--workers 2`", "`--workers 4`（8 核 16 线程）"],
            ["凭证", "`~/ .kaggle/access_token`", "`secrets\\access_token` + 环境变量"],
            ["续训", "重连后 `--resume`", "同样，但还要先 `powercfg` 关休眠"],
            ["分辨率", "384 可选", "**放弃 384**（OOM）"],
        ],
        widths=[2.4, 7.2, 6.6],
        size=8.4,
        caption="表 B-1　六处差异。方法与指标口径完全不变，所以两份文档的结论可以直接互引",
    )
    k.p("—— 本机跑通之后，方法与指标口径去看 `6018_Tutorial_Implementation_v2.docx` ——",
        align="center", before=14)
