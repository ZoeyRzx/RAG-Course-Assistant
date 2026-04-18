param(
  [int]$Port = 5173,
  [string]$Root = (Split-Path -Parent $MyInvocation.MyCommand.Path)
)

$ErrorActionPreference = "Stop"

function Get-ContentType([string]$path) {
  switch ([System.IO.Path]::GetExtension($path).ToLowerInvariant()) {
    ".html" { "text/html; charset=utf-8" }
    ".js" { "application/javascript; charset=utf-8" }
    ".css" { "text/css; charset=utf-8" }
    ".json" { "application/json; charset=utf-8" }
    ".png" { "image/png" }
    ".jpg" { "image/jpeg" }
    ".jpeg" { "image/jpeg" }
    ".svg" { "image/svg+xml" }
    ".ico" { "image/x-icon" }
    default { "application/octet-stream" }
  }
}

function Write-HttpResponse(
  [System.Net.Sockets.NetworkStream]$stream,
  [int]$statusCode,
  [string]$statusText,
  [byte[]]$body,
  [string]$contentType
) {
  $header = @(
    "HTTP/1.1 $statusCode $statusText"
    "Content-Type: $contentType"
    "Content-Length: $($body.Length)"
    "Connection: close"
    ""
    ""
  ) -join "`r`n"

  $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($header)
  $stream.Write($headerBytes, 0, $headerBytes.Length)
  if ($body.Length -gt 0) {
    $stream.Write($body, 0, $body.Length)
  }
}

$rootFullPath = [System.IO.Path]::GetFullPath($Root)
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
$listener.Start()

Write-Host "Serving $rootFullPath on http://localhost:$Port"
Write-Host "Press Ctrl+C to stop."

try {
  while ($true) {
    $client = $listener.AcceptTcpClient()
    try {
      $stream = $client.GetStream()
      $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::ASCII, $false, 1024, $true)

      $requestLine = $reader.ReadLine()
      if ([string]::IsNullOrWhiteSpace($requestLine)) {
        continue
      }

      while (($line = $reader.ReadLine()) -ne "") {
      }

      $parts = $requestLine.Split(" ")
      if ($parts.Length -lt 2) {
        $body = [System.Text.Encoding]::UTF8.GetBytes("Bad Request")
        Write-HttpResponse -stream $stream -statusCode 400 -statusText "Bad Request" -body $body -contentType "text/plain; charset=utf-8"
        continue
      }

      $rawPath = $parts[1]
      $requestPath = $rawPath.Split("?")[0].TrimStart("/")
      if ([string]::IsNullOrWhiteSpace($requestPath)) {
        $requestPath = "index.html"
      }

      $candidatePath = Join-Path $rootFullPath ($requestPath -replace "/", "\")
      $resolvedPath = [System.IO.Path]::GetFullPath($candidatePath)

      if (-not $resolvedPath.StartsWith($rootFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        $body = [System.Text.Encoding]::UTF8.GetBytes("Forbidden")
        Write-HttpResponse -stream $stream -statusCode 403 -statusText "Forbidden" -body $body -contentType "text/plain; charset=utf-8"
        continue
      }

      if (-not (Test-Path -LiteralPath $resolvedPath -PathType Leaf)) {
        $body = [System.Text.Encoding]::UTF8.GetBytes("Not Found")
        Write-HttpResponse -stream $stream -statusCode 404 -statusText "Not Found" -body $body -contentType "text/plain; charset=utf-8"
        continue
      }

      $bytes = [System.IO.File]::ReadAllBytes($resolvedPath)
      $contentType = Get-ContentType -path $resolvedPath
      Write-HttpResponse -stream $stream -statusCode 200 -statusText "OK" -body $bytes -contentType $contentType
    }
    finally {
      $client.Close()
    }
  }
}
finally {
  $listener.Stop()
}
