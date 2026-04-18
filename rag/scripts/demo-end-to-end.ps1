param(
    [string]$Python = "python",
    [string]$DataPath = "",
    [string]$Question = "What chunk size and overlap are recommended for a first RAG system?",
    [int]$TopK = 3
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$defaultDataPath = Join-Path $repoRoot "rag\sample_data"
$resolvedDataPath = if ($DataPath) { Resolve-Path $DataPath } else { $defaultDataPath }

if (-not $env:OPENAI_API_KEY) {
    throw "OPENAI_API_KEY is not set."
}

Push-Location $repoRoot
try {
    Write-Host "== Smoke test =="
    & $Python -m rag.scripts.smoke_test --path $resolvedDataPath
    if ($LASTEXITCODE -ne 0) {
        throw "Smoke test failed."
    }

    Write-Host "`n== Build index =="
    & $Python -m rag.cli build-index $resolvedDataPath
    if ($LASTEXITCODE -ne 0) {
        throw "Index build failed."
    }

    Write-Host "`n== List documents =="
    & $Python -m rag.cli list-docs
    if ($LASTEXITCODE -ne 0) {
        throw "Listing documents failed."
    }

    Write-Host "`n== Query =="
    & $Python -m rag.cli query $Question --top-k $TopK
    if ($LASTEXITCODE -ne 0) {
        throw "Query failed."
    }
} finally {
    Pop-Location
}
