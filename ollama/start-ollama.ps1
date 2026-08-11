# ============================================================
#  XOMNI bundled Ollama starter (Windows PowerShell)
#  Gives users LOCAL models with zero extra installs:
#    1. Downloads the official portable Ollama build ONCE
#       (~130 MB) into .\runtime\ if missing.
#    2. Starts `ollama serve` detached on 127.0.0.1:11434.
#    3. Pulls the default small model (qwen2.5:3b, ~1.9 GB)
#       on first run so local inference works offline.
#  Idempotent: if Ollama is already serving, it does nothing.
# ============================================================
$ErrorActionPreference = "Stop"
$runtimeDir = Join-Path $PSScriptRoot "runtime"
$bin = Join-Path $runtimeDir "ollama.exe"
$portUrl = "http://127.0.0.1:11434/v1/models"
$defaultModel = "qwen2.5:3b"

function Test-Serving {
    try {
        $r = Invoke-WebRequest -Uri $portUrl -TimeoutSec 3 -UseBasicParsing
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

if (Test-Serving) {
    Write-Host "[XOMNI] Ollama already serving on 127.0.0.1:11434"
    exit 0
}

if (-not (Test-Path $bin)) {
    Write-Host "[XOMNI] downloading official Ollama build (once, ~130 MB)..."
    $zip = Join-Path $runtimeDir "ollama.zip"
    New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
    Invoke-WebRequest -Uri "https://ollama.com/download/ollama-windows-amd64.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $runtimeDir -Force
    Remove-Item $zip -Force
    if (-not (Test-Path $bin)) {
        Write-Host "[XOMNI] ERROR: bundled ollama.exe not found after extraction" -ForegroundColor Red
        exit 1
    }
    Write-Host "[XOMNI] ollama runtime installed: $bin"
}

Write-Host "[XOMNI] starting ollama serve (detached)..."
Start-Process -FilePath $bin -ArgumentList "serve" -WindowStyle Hidden | Out-Null

$deadline = (Get-Date).AddSeconds(90)
while (-not (Test-Serving)) {
    if ((Get-Date) -gt $deadline) {
        Write-Host "[XOMNI] WARNING: ollama serve did not answer in 90s — continuing anyway" -ForegroundColor Yellow
        exit 0
    }
    Start-Sleep -Seconds 2
}
Write-Host "[XOMNI] ollama serving on 127.0.0.1:11434"

$list = & $bin list 2>$null
if ($list -notmatch $defaultModel) {
    Write-Host "[XOMNI] pulling default local model $defaultModel (first run, ~1.9 GB)..."
    & $bin pull $defaultModel
}
Write-Host "[XOMNI] local models ready. XOMNI can now route to http://127.0.0.1:11434/v1"
exit 0
