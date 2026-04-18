param(
    [string]$Python = "python",
    [string]$DataPath = ""
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$defaultDataPath = Join-Path $repoRoot "rag\sample_data"
$resolvedDataPath = if ($DataPath) { Resolve-Path $DataPath } else { $defaultDataPath }

if (-not $env:OPENAI_API_KEY) {
    throw "OPENAI_API_KEY is not set."
}

Push-Location $repoRoot
try {
    & $Python -m rag.cli build-index $resolvedDataPath
    if ($LASTEXITCODE -ne 0) {
        throw "Index build failed."
    }
} finally {
    Pop-Location
}
