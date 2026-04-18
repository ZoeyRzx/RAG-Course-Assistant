param(
    [string]$Python = "python",
    [string]$Question = "What is retrieval-augmented generation?",
    [int]$TopK = 3
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

if (-not $env:OPENAI_API_KEY) {
    throw "OPENAI_API_KEY is not set."
}

Push-Location $repoRoot
try {
    & $Python -m rag.cli query $Question --top-k $TopK
    if ($LASTEXITCODE -ne 0) {
        throw "Query failed."
    }
} finally {
    Pop-Location
}
