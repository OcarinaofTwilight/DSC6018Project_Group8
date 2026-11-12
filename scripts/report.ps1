<#
    report.ps1 -- bootstrap tables and the four figures, no GPU needed.

    用法:
        powershell -ExecutionPolicy Bypass -File scripts\report.ps1
        powershell -ExecutionPolicy Bypass -File scripts\report.ps1 -Boot 2000
#>
param(
    [int]$Boot = 2000,
    [double]$Spec = 0.80
)

. "$PSScriptRoot\_common.ps1"
Assert-Python

$preds = @(Get-ChildItem $Runs -Directory |
           Where-Object { $_.Name -notlike "_*" -and (Test-Path (Join-Path $_.FullName "test_preds.csv")) })
if ($preds.Count -eq 0) { throw "没有找到 test_preds.csv。先跑 scripts\eval.ps1。" }
Write-Host ("找到 {0} 个 run: {1}" -f $preds.Count, (($preds | ForEach-Object { $_.Name }) -join ", "))

Push-Location $Repo

Write-Step "配对 bootstrap -> results\"
& $PyExe "src\report.py" --runs (Join-Path $Runs "*") --out $Results --n-boot $Boot --spec $Spec
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "report.py 失败" }

Write-Step "四张图 -> figures\panel.png"
$patterns = $preds | ForEach-Object { Join-Path $_.FullName "test_preds.csv" }
& $PyExe "src\figures.py" --preds @patterns --out-dir $Figures
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "figures.py 失败" }

Pop-Location

Write-Host ""
Write-Host "结果在 $Results，图在 $Figures" -ForegroundColor Green
Write-Host "报告里要用的三张表：results_long.csv / diffs.csv / results.md" -ForegroundColor Green
