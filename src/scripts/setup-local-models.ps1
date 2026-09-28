$ErrorActionPreference = "Stop"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  Write-Error "Ollama is not installed. Install it from https://ollama.com/download/windows and rerun this script."
}

Write-Host "Starting Ollama and downloading local IBM Granite models..."
$service = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $service) {
  Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep -Seconds 3
}

ollama pull granite4:3b
ollama pull granite3.2-vision:2b

Write-Host "Local models are ready. Run the API from backend with: npm start"
