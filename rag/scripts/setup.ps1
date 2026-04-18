param(
    [string]$Python = "python"
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$requirementsPath = Join-Path $repoRoot "rag\requirements.txt"

Push-Location $repoRoot
try {
    & $Python -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
} finally {
    Pop-Location
}
