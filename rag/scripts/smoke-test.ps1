param(
    [string]$Python = "python",
    [string]$DataPath = ""
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$defaultDataPath = Join-Path $repoRoot "rag\sample_data"
$resolvedDataPath = if ($DataPath) { Resolve-Path $DataPath } else { $defaultDataPath }

Push-Location $repoRoot
try {
    & $Python -m rag.scripts.smoke_test --path $resolvedDataPath
    if ($LASTEXITCODE -ne 0) {
        throw "Smoke test failed."
    }
} finally {
    Pop-Location
}
