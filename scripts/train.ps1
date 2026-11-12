<#
    train.ps1 -- run one experiment (or all five) locally, writing into the workspace.

    用法:
        powershell -ExecutionPolicy Bypass -File scripts\train.ps1 -Smoke
        powershell -ExecutionPolicy Bypass -File scripts\train.ps1 -Run b3_bce
        powershell -ExecutionPolicy Bypass -File scripts\train.ps1 -All
        powershell -ExecutionPolicy Bypass -File scripts\train.ps1 -Run b3_bce -Resume

    排查用开关:
        -Workers 0        绕开 Windows 多进程 DataLoader
        -NoPretrained     不下载 ImageNet 权重（只验证管线，指标不可用）
        -HfMirror         timm 从 hf-mirror.com 取权重（国内网络常用）

    每个 run 一个目录：S:\...\runs\<name>\{log.csv,last.pt,best.pt,cfg.json,console.log}
    中断（关机、断电、Ctrl+C）后重跑同一条命令并加 -Resume 即可接着练。
#>
param(
    [ValidateSet("b3_bce", "b3_wbce", "b3_focal", "b3_cb", "r50_bce", "b3_bce_meta")]
    [string]$Run = "b3_bce",
    [switch]$All,
    [switch]$Smoke,
    [switch]$Resume,
    [int]$Batch = 16,
    [int]$Epochs = 12,
    [int]$Workers = 4,
    [int]$ImgSize = 256,
    [switch]$NoPretrained,
    [switch]$HfMirror
)

. "$PSScriptRoot\_common.ps1"
Assert-Python
Assert-Manifest
$null = Assert-Images

$jobs = [ordered]@{
    b3_bce      = @{ model = "efficientnet_b3"; loss = "bce";   meta = $false }
    b3_wbce     = @{ model = "efficientnet_b3"; loss = "wbce";  meta = $false }
    b3_focal    = @{ model = "efficientnet_b3"; loss = "focal"; meta = $false }
    b3_cb       = @{ model = "efficientnet_b3"; loss = "cb";    meta = $false }
    r50_bce     = @{ model = "resnet50";        loss = "bce";   meta = $false }
    b3_bce_meta = @{ model = "efficientnet_b3"; loss = "bce";   meta = $true  }
}
$order = @("b3_bce", "b3_wbce", "b3_focal", "r50_bce", "b3_bce_meta")
if ($All) { $queue = $order } else { $queue = @($Run) }

foreach ($name in $queue) {
    $cfg = $jobs[$name]
    $outDir = Join-Path $Runs $name
    if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
    $log = Join-Path $outDir "console.log"

    $argv = @("src\train.py",
              "--manifest", $Manifest,
              "--img-dir", $Img256,
              "--out-dir", $outDir,
              "--model", $cfg.model,
              "--loss", $cfg.loss,
              "--img-size", $ImgSize,
              "--batch-size", $Batch,
              "--workers", $Workers,
              "--epochs", $Epochs)
    if ($cfg.meta) { $argv += "--meta" }
    if ($Resume) { $argv += "--resume" }
    if ($NoPretrained) { $argv += "--no-pretrained" }
    if ($HfMirror) { $env:HF_ENDPOINT = "https://hf-mirror.com" }
    if ($Smoke) {
        # 就地改写，不要追加：重复的 --epochs 只有最后一个生效，但日志里会很难看
        $outDir = Join-Path $Runs "_smoke"
        foreach ($pair in @(@("--epochs", "1"), @("--out-dir", $outDir))) {
            $idx = [array]::IndexOf($argv, $pair[0])
            if ($idx -ge 0) { $argv[$idx + 1] = $pair[1] } else { $argv += @($pair[0], $pair[1]) }
        }
        $argv += @("--limit-batches", "5")
        if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
        $log = Join-Path $outDir "console.log"
    }

    Write-Step "$name  ->  $outDir"
    $quoted = $argv | ForEach-Object { if ($_ -match '\s') { '"{0}"' -f $_ } else { $_ } }
    $line = '"{0}" {1}' -f $PyExe, ($quoted -join ' ')
    Write-Host $line -ForegroundColor DarkGray
    if ($NoPretrained) { Write-Host "（本次不加载 ImageNet 预训练权重，仅用于排查）" -ForegroundColor Yellow }
    if ($HfMirror) { Write-Host "（HF_ENDPOINT=$env:HF_ENDPOINT）" -ForegroundColor Yellow }

    Push-Location $Repo
    $t0 = Get-Date
    # 关键：交给 cmd 把 stderr 并进 stdout。直接 `& python ... 2>&1 | Tee-Object` 时，
    # PowerShell 会把每行 stderr 包成 ErrorRecord，配合 _common.ps1 的
    # $ErrorActionPreference="Stop" 就在第一行 traceback 处中断，真正的异常被吞掉。
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    cmd /c "$line 2>&1" | Tee-Object -FilePath $log -Append
    $code = $LASTEXITCODE
    $ErrorActionPreference = $oldEap
    Pop-Location
    $mins = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)

    if ($code -ne 0) {
        Write-Host ""
        Write-Host "退出码 $code，用时 $mins 分钟。完整日志：$log" -ForegroundColor Red
        Write-Host "最后 30 行：" -ForegroundColor Red
        if (Test-Path $log) { Get-Content $log -Tail 30 }
        if (-not $All) { exit $code }
    } else {
        Write-Host "$name 完成，用时 $mins 分钟" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "训练阶段结束。下一步：scripts\eval.ps1" -ForegroundColor Green
