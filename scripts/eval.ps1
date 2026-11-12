<#
    eval.ps1 -- test/val predictions for every finished run, plus temperature scaling.

    用法:
        powershell -ExecutionPolicy Bypass -File scripts\eval.ps1
        powershell -ExecutionPolicy Bypass -File scripts\eval.ps1 -Run b3_bce -NoTta

    输出（每个 run 目录内）:
        val_preds.csv  test_preds.csv  test_preds_metrics.json
        test_preds_temp.csv  temperature.json        <- 温度缩放条件
#>
param(
    [string]$Run = "",
    [switch]$NoTta,
    [int]$Batch = 32,
    [int]$Workers = 4,
    [int]$ImgSize = 256
)

. "$PSScriptRoot\_common.ps1"
Assert-Python
Assert-Manifest
$null = Assert-Images

$all = @(Get-ChildItem $Runs -Directory |
         Where-Object { $_.Name -notlike "_*" -and (Test-Path (Join-Path $_.FullName "best.pt")) })
if ($Run) { $all = $all | Where-Object { $_.Name -eq $Run } }
if ($all.Count -eq 0) { throw "没有找到含 best.pt 的 run 目录（$Runs）。先跑 scripts\train.ps1。" }

foreach ($d in $all) {
    $name = $d.Name
    $ckpt = Join-Path $d.FullName "best.pt"
    foreach ($split in @("val", "test")) {
        $out = Join-Path $d.FullName "${split}_preds.csv"
        Write-Step "$name / $split"
        $argv = @("src\evaluate.py",
                  "--manifest", $Manifest,
                  "--img-dir", $Img256,
                  "--ckpt", $ckpt,
                  "--split", $split,
                  "--img-size", $ImgSize,
                  "--batch-size", $Batch,
                  "--workers", $Workers,
                  "--out", $out)
        if ($NoTta) { $argv += "--no-tta" }
        Push-Location $Repo
        & $PyExe @argv
        $code = $LASTEXITCODE
        Pop-Location
        if ($code -ne 0) { throw "$name 的 $split 评估失败" }
    }

    Write-Step "$name / 温度缩放（val 拟合 -> test 应用）"
    & $PyExe (Join-Path $Repo "tools\fit_temperature.py") --run-dir $d.FullName
}

Write-Host ""
Write-Host "评估完成。下一步：scripts\report.ps1" -ForegroundColor Green
