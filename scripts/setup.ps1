<#
    setup.ps1 -- one-time environment build for the local ISIC-2020 workflow.

    用法（在仓库目录下）:
        powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

    做什么:
      1. 在 S:\...\melanoma_calib\.venv 建虚拟环境（不污染 C: 的 Python）
      2. 装 CUDA 版 torch（默认 PyPI 的 torch 是 CPU 版，必须走 pytorch 官方 index）
      3. 装 timm + huggingface_hub + pandas / matplotlib / Pillow
      4. 验证 torch.cuda 能看到 GPU，并试建一次 EfficientNet-B3（确认权重链路通）
      5. 跑一次显存/吞吐基准，给出本机每 epoch 的估计
#>
param(
    [string]$TorchIndex = "https://download.pytorch.org/whl/cu124",
    [string]$PipIndex   = "",          # 例：https://pypi.tuna.tsinghua.edu.cn/simple
    [switch]$SkipBench,
    [switch]$SkipWeights              # 离线环境：跳过权重下载验证
)

. "$PSScriptRoot\_common.ps1"

# 1) 虚拟环境
if (Test-Path $PyExe) {
    Write-Step "虚拟环境已存在：$Venv"
} else {
    Write-Step "创建虚拟环境 $Venv"
    & py -3.10 -m venv $Venv
    if (-not (Test-Path $PyExe)) { throw "建虚拟环境失败。确认 Python 3.10：py -3.10 -V" }
}

Write-Step "升级 pip"
& $PyExe -m pip install --upgrade pip

$mirror = @()
if ($PipIndex) { $mirror = @("-i", $PipIndex) }

Write-Step "安装 CUDA 版 torch（约 2.5 GB，第一次会久）"
& $PyExe -m pip install torch torchvision --index-url $TorchIndex @mirror
if ($LASTEXITCODE -ne 0) {
    Write-Host "cu124 装不上，退回 cu121 再试一次..." -ForegroundColor Yellow
    & $PyExe -m pip install torch torchvision --index-url "https://download.pytorch.org/whl/cu121" @mirror
}

Write-Step "安装其余依赖"
# huggingface_hub 必须装，而且必须是 0.25.x：timm 1.0.9 依赖的 repo_type_and_id_from_hf_id
# 在 huggingface_hub 2.x 已被移除，缺它 timm 会误报 "package not installed"。
& $PyExe -m pip install "timm==1.0.9" "huggingface_hub>=0.23" "pandas>=2.0" "numpy>=1.24" "matplotlib>=3.7" "Pillow>=10.0" @mirror

Write-Step "验证 timm 能走 HF hub（hf_compat 会补齐 huggingface_hub 2.x 缺的符号）"
Push-Location $Repo
& $PyExe -c @"
import sys; sys.path.insert(0, 'src')
import hf_compat, timm, huggingface_hub
from timm.models import _hub
print('timm', timm.__version__, '| hf_hub', huggingface_hub.__version__,
      '| shim', hf_compat.PATCHED, '| _has_hf_hub', _hub._has_hf_hub)
if not _hub._has_hf_hub:
    raise SystemExit('timm 仍然看不到 HF hub：见 src/hf_compat.py')
"@
Pop-Location
if ($LASTEXITCODE -ne 0) { throw "timm 与 huggingface_hub 仍不兼容，见 src/hf_compat.py 的注释。" }

Write-Step "验证 GPU + 预训练权重可加载"
& $PyExe -c @"
import torch, timm, huggingface_hub
print('torch      :', torch.__version__)
print('cuda build :', torch.version.cuda)
print('available  :', torch.cuda.is_available())
if not torch.cuda.is_available():
    raise SystemExit('CUDA 不可用：装了 CPU 版 torch，或驱动太旧')
p = torch.cuda.get_device_properties(0)
print('device     :', p.name, f'{p.total_memory/1024**3:.1f} GB', f'sm_{p.major}{p.minor}')
print('timm       :', timm.__version__)
print('hf_hub     :', huggingface_hub.__version__)
"@

if (-not $SkipWeights) {
    Write-Step "下载并试建 EfficientNet-B3（首次约 50 MB，验证权重链路）"
    & $PyExe -c @"
import timm
m = timm.create_model('efficientnet_b3', pretrained=True, num_classes=0)
print('weights ok:', sum(p.numel() for p in m.parameters()) / 1e6, 'M params')
"@
    if ($LASTEXITCODE -ne 0) {
        Write-Host "权重下载失败：设 `$env:HF_ENDPOINT='https://hf-mirror.com' 后重试；或加 -SkipWeights 先跳过。" -ForegroundColor Yellow
    }
}

if (-not $SkipBench) {
    Write-Step "显存/吞吐基准（batch 16 @256，约 30 秒）"
    & $PyExe (Join-Path $Repo "tools\bench_local.py") --batch-size 16 --img-size 256
}

Write-Step "自检（25 项，不需要数据和 GPU）"
Push-Location $Repo
& $PyExe tests\test_all.py
Pop-Location

Write-Host ""
Write-Host "环境就绪。下一步：scripts\data.ps1" -ForegroundColor Green
