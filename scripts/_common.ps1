<#
    _common.ps1 -- shared paths for the local (Windows) ISIC-2020 workflow.

    Everything lives beside the cloned repo (data/, runs/, results/, .cache/) so that
    neither the pip cache nor the 30 GB of images end up in your home folder.

    Dot-source it from the other scripts:   . "$PSScriptRoot\_common.ps1"
#>

$ErrorActionPreference = "Stop"

# Repo = the cloned repository; data/, runs/, results/ live beside it.
$Repo     = Split-Path $PSScriptRoot -Parent
$ProjRoot = Split-Path $Repo -Parent
$Data     = Join-Path $ProjRoot "data"
$Img1024  = Join-Path $Data "train"                 # 1024 px originals (only if you download them)
$Img256   = Join-Path $Data "train_256"             # what training actually reads
$Runs     = Join-Path $ProjRoot "runs"
$Results  = Join-Path $ProjRoot "results"
$Figures  = Join-Path $ProjRoot "figures"
$Cache    = Join-Path $ProjRoot ".cache"
$Secrets  = Join-Path $ProjRoot "secrets"
$Venv     = Join-Path $Repo ".venv"
$PyExe    = Join-Path $Venv "Scripts\python.exe"
$Manifest = Join-Path $Repo "manifests\split_seed42.csv"

# Keep every download cache off C:. timm weights -> TORCH_HOME, pip wheels -> PIP_CACHE_DIR.
$env:PIP_CACHE_DIR    = Join-Path $Cache "pip"
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:TORCH_HOME       = Join-Path $Cache "torch"
$env:HF_HOME          = Join-Path $Cache "hf"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8       = "1"
# 下载已改用 tools\kaggle_download.py（Bearer，不碰 ~/.kaggle）。若某处仍 import kaggle，
# 1.7.x 会在 import 时 os.makedirs(~/.kaggle)，在部分机器上直接 WinError 5；指到工作区即可。
$env:KAGGLE_CONFIG_DIR = Join-Path $Cache "kaggle"

# PowerShell 5.1 用系统代码页(GBK)解码子进程的 stdout，Python 输出 UTF-8 时会变成
# 「鈶?璁?」这类乱码。把解码改成 UTF-8，中文报告才看得懂。
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
} catch {
    Write-Host "（控制台没能切到 UTF-8：中文可能显示为乱码，但日志文件本身正确）" -ForegroundColor Yellow
}

foreach ($d in @($Data, $Runs, $Results, $Figures, $Cache, $Secrets)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host ("== " + $Text) -ForegroundColor Cyan
}

function Assert-Python {
    if (-not (Test-Path $PyExe)) {
        throw "找不到 $PyExe -- 先运行 scripts\setup.ps1 建虚拟环境。"
    }
}
function Assert-Manifest {
    if (-not (Test-Path $Manifest)) {
        throw "找不到划分清单 $Manifest -- 先运行 scripts\data.ps1（它会在体检后生成）。"
    }
}

function Assert-Images {
    if (-not (Test-Path $Img256)) {
        throw "找不到 256 px 图片目录 $Img256 -- 先运行 scripts\data.ps1。"
    }
    $n = (Get-ChildItem $Img256 -Filter *.jpg -File -Recurse | Measure-Object).Count
    if ($n -lt 1000) {
        throw "$Img256 里只有 $n 张图，像是没下载完。"
    }
    return $n
}

function Get-KaggleToken {
    $envTok = $env:KAGGLE_API_TOKEN
    if ($envTok) { return $envTok.Trim() }

    $f = Join-Path $Secrets "access_token"
    if (-not (Test-Path $f)) {
        throw "没有 Kaggle 令牌。请把 KGAT_... 一行存成文件：$f"
    }
    # 最常见的错法：把 access_token 建成了文件夹。Get-Content 对文件夹报的是
    # "访问被拒绝"，很容易误判成权限问题，所以先判类型。
    if (Test-Path $f -PathType Container) {
        throw ("$f 是一个【文件夹】而不是文件 —— 这正是 Get-Content 报『访问被拒绝』的原因。`n" +
               "  Remove-Item `"$f`" -Recurse -Force`n" +
               "  然后用记事本新建同名【文件】，里面只放一行 KGAT_...")
    }
    $tok = Get-Content $f -Raw
    if ($null -eq $tok) { $tok = "" }
    $tok = $tok.Trim()
    if (-not $tok) { throw "$f 是空文件。把 KGAT_... 那一行粘进去保存。" }
    if (-not ($tok -match '^KGAT_[A-Za-z0-9_\-]+$')) {
        $head = $tok.Substring(0, [Math]::Min(6, $tok.Length))
        throw ("$f 的内容不像令牌（长度 $($tok.Length)，前 6 位 '$head'）。`n" +
               "  应只有一行、以 KGAT_ 开头、纯 ASCII：到 kaggle.com/settings/api 重新 Generate New Token。")
    }
    return $tok
}

Write-Host "项目根目录 : $ProjRoot"
Write-Host "代码       : $Repo"
Write-Host "数据       : $Data"
Write-Host "输出       : $Runs"
