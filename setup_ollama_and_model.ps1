# setup_ollama_and_model.ps1
# Automates silent installation of Ollama, starts service, pulls model, and verifies setup

$ErrorActionPreference = "Stop"

$installerPath = Join-Path $env:TEMP "OllamaSetup.exe"
$ollamaDir = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
$ollamaExe = Join-Path $ollamaDir "ollama.exe"

Write-Host ">>> Checking Ollama installer at: $installerPath"
if (-not (Test-Path $installerPath)) {
    throw "OllamaSetup.exe not found at $installerPath. Wait for download to complete."
}

Write-Host ">>> Running silent InnoSetup installer..."
$installerArgs = "/VERYSILENT /NORESTART /SUPPRESSMSGBOXES"
$proc = Start-Process -FilePath $installerPath -ArgumentList $installerArgs -PassThru
$proc.WaitForExit()

if ($proc.ExitCode -ne 0) {
    throw "Ollama installation failed with exit code $($proc.ExitCode)"
}
Write-Host ">>> Ollama installed successfully."

# Update PATH
if (Test-Path $ollamaDir) {
    $currentPath = $env:PATH -split ';'
    if ($ollamaDir -notin $currentPath) {
        $env:PATH = "$ollamaDir;$env:PATH"
        Write-Host ">>> Added $ollamaDir to session PATH."
    }
}

# Start Ollama service if not already running
Write-Host ">>> Checking Ollama service..."
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction SilentlyContinue
    Write-Host ">>> Ollama service is already running."
} catch {
    Write-Host ">>> Starting Ollama background server..."
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# Verify API ping
$retries = 10
$ready = $false
for ($i = 0; $i -lt $retries; $i++) {
    try {
        $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2
        Write-Host ">>> Ollama API is responsive."
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    throw "Failed to communicate with Ollama at http://localhost:11434"
}

# Check for model and pull
$targetModel = if ($env:AI_MODEL) { $env:AI_MODEL } else { "llama3.2:3b" }
Write-Host ">>> Pulling model: $targetModel (please wait)..."
& $ollamaExe pull $targetModel

Write-Host ">>> Ollama setup complete! Installed models:"
& $ollamaExe list
