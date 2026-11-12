<#
    data.ps1 -- download ISIC 2020 into the workspace, then verify + split.

    用法:
        powershell -ExecutionPolicy Bypass -File scripts\data.ps1                 # 256 px 版（约 3.5 GB）
        powershell -ExecutionPolicy Bypass -File scripts\data.ps1 -Route 1024     # 原图（约 30 GB）+ 本地缩放

    令牌: 把 kaggle 页面生成的 KGAT_... 一行存到
          <project-root>\secrets\access_token
#>
param(
    [ValidateSet("256", "1024")]
    [string]$Route = "256",
    [string]$Dataset256  = "cdeotte/jpeg-melanoma-256x256",
    [string]$Dataset1024 = "cdeotte/melanoma-1024x1024",
    [switch]$ForceDownload,
    [switch]$SkipSplit
)

. "$PSScriptRoot\_common.ps1"
Assert-Python

$tokenFile = Join-Path $Secrets "access_token"
$tok = Get-KaggleToken                     # 校验：必须是文件、非空、形如 KGAT_...
Write-Host ("令牌长度 {0}，前 5 位 {1}" -f $tok.Length, $tok.Substring(0, 5))
$DL = Join-Path $Repo "tools\kaggle_download.py"
$COMP = "siim-isic-melanoma-classification"

# ---------------------------------------------------------------- metadata
$csv = Join-Path $Data "train.csv"
if ((-not (Test-Path $csv)) -or $ForceDownload) {
    Write-Step "下载 train.csv（元数据）"
    # 用自带的 Bearer 下载器，不依赖 kaggle CLI（1.7 版会在 import 时往 ~/.kaggle 写目录）
    & $PyExe $DL --api-path "competitions/data/download/$COMP/train.csv" `
        --out (Join-Path $Data "train.csv.zip") --unzip --dest $Data --resume --token-file $tokenFile
    if ($LASTEXITCODE -ne 0) {
        throw "下载 train.csv 失败：看上面的 HTTP 码。403 就去比赛页点 Join/Accept Rules，401 就重新生成令牌。"
    }
}

# ---------------------------------------------------------------- images
if ($Route -eq "256") {
    $target = $Img256
    if ((Test-Path $target) -and ((Get-ChildItem $target -Filter *.jpg -File | Measure-Object).Count -gt 1000)) {
        Write-Step "256 px 图片已存在，跳过下载"
    } else {
        Write-Step "下载 256 px 图片（约 3.5 GB）"
        & $PyExe $DL --api-path "datasets/download/$Dataset256" `
            --out (Join-Path $Data "img256.zip") --unzip --dest $Data --resume --token-file $tokenFile
        if ($LASTEXITCODE -ne 0) {
            Write-Host "数据集 $Dataset256 下载失败。可用候选（自己挑一个传给 -Dataset256）：" -ForegroundColor Yellow
            & $PyExe $DL --list-datasets "melanoma 256" --token-file $tokenFile
            throw "换成上面列出的数据集名：scripts\data.ps1 -Dataset256 <owner/slug>"
        }
        # 社区包常见解压层级差异：把找到的 train 目录统一到 $Img256
        if (-not (Test-Path $target)) {
            $found = Get-ChildItem $Data -Directory -Recurse -Depth 2 |
                     Where-Object { $_.Name -eq "train" -and (Get-ChildItem $_.FullName -Filter *.jpg -File | Select-Object -First 1) } |
                     Select-Object -First 1
            if ($found) {
                Write-Host "找到图片目录 $($found.FullName) -> 重命名为 $target"
                Move-Item $found.FullName $target
            }
        }
    }
} else {
    if ((Test-Path $Img256) -and ((Get-ChildItem $Img256 -Filter *.jpg -File | Measure-Object).Count -gt 1000)) {
        Write-Step "256 px 图片已存在，跳过下载与缩放"
    } else {
        if (-not (Test-Path $Img1024)) {
            Write-Step "下载 1024 px 原图（约 30 GB，几十分钟到几小时）"
            & $PyExe $DL --api-path "datasets/download/$Dataset1024" `
                --out (Join-Path $Data "img1024.zip") --unzip --dest $Data --resume --token-file $tokenFile
            if ($LASTEXITCODE -ne 0) {
                Write-Host "数据集 $Dataset1024 下载失败。候选列表：" -ForegroundColor Yellow
                & $PyExe $DL --list-datasets "melanoma" --token-file $tokenFile
                throw ("换个名字重跑，例如 scripts\data.ps1 -Route 1024 -Dataset1024 <owner/slug>；" +
                       "或先用 -Route 256 把流程跑通。")
            }
            # 解压层级可能多套一层：找到真正含 jpg 的上级目录并统一到 $Img1024
            if (-not (Test-Path $Img1024)) {
                $first = Get-ChildItem $Data -Filter *.jpg -File -Recurse -Depth 3 |
                         Select-Object -First 1
                if ($first) {
                    $dir = Split-Path $first.FullName -Parent
                    if ($dir -ne $Img1024) {
                        Write-Host "图片实际在 $dir -> 统一到 $Img1024"
                        Move-Item $dir $Img1024
                    }
                }
            }
        }
        Write-Step "缩放到 256（CPU，约 20–40 分钟；中断后重跑会跳过已完成）"
        & $PyExe (Join-Path $Repo "tools\resize_images.py") --src $Img1024 --dst $Img256 --size 256
    }
}

$n = Assert-Images
Write-Step "图片就绪：$n 张 -> $Img256"

# ---------------------------------------------------------------- verify + split
Write-Step "数据体检（八个问题）"
& $PyExe (Join-Path $Repo "tools\inspect_data.py") --csv $csv --img-dir $Img256
if ($LASTEXITCODE -ne 0) { throw "体检没通过，先修数据再继续。" }

if (-not $SkipSplit) {
    Write-Step "生成患者级划分并冻结 sha256"
    Push-Location $Repo
    & $PyExe "src\split.py" --csv $csv --out $Manifest --seed 42
    Pop-Location
    Write-Host ""
    Write-Host "把上面打印的 sha256 写进报告 Methods 和 README。" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "数据阶段完成。下一步：scripts\train.ps1 -Smoke" -ForegroundColor Green
