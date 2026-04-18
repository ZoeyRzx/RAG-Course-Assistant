param(
    [string]$Python = "python",
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

if (-not $env:OPENAI_API_KEY) {
    throw "OPENAI_API_KEY is not set."
}

Push-Location $repoRoot
try {
    & $Python -m uvicorn rag.app:app --reload --host $Host --port $Port
} finally {
    Pop-Location
}
