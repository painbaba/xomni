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
    Write-Host "[xomni] Ollama already serving on 127.0.0.1:11434"
    exit 0
}

if (-not (Test-Path $bin)) {
    Write-Host "[xomni] downloading official Ollama build (once, ~130 MB)..."
    $zip = Join-Path $runtimeDir "ollama.zip"
    New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
    Invoke-WebRequest -Uri "https://ollama.com/download/ollama-windows-amd64.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $runtimeDir -Force
    Remove-Item $zip -Force
    if (-not (Test-Path $bin)) {
        Write-Host "[xomni] ERROR: bundled ollama.exe not found after extraction" -ForegroundColor Red
        exit 1
    }
    Write-Host "[xomni] ollama runtime installed: $bin"
}

Write-Host "[xomni] starting ollama serve (detached)..."
Start-Process -FilePath $bin -ArgumentList "serve" -WindowStyle Hidden | Out-Null

$deadline = (Get-Date).AddSeconds(90)
while (-not (Test-Serving)) {
    if ((Get-Date) -gt $deadline) {
        Write-Host "[xomni] WARNING: ollama serve did not answer in 90s — continuing anyway" -ForegroundColor Yellow
        exit 0
    }
    Start-Sleep -Seconds 2
}
Write-Host "[xomni] ollama serving on 127.0.0.1:11434"

$list = & $bin list 2>$null
if ($list -notmatch $defaultModel) {
    Write-Host "[xomni] pulling default local model $defaultModel (first run, ~1.9 GB)..."
    & $bin pull $defaultModel
}
Write-Host "[xomni] local models ready. XOMNI can now route to http://127.0.0.1:11434/v1"
exit 0
