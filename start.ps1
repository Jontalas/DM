$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Host 'Crónicas: http://127.0.0.1:8787'
Write-Host 'IA: configura OLLAMA_MODEL y ejecuta Ollama antes de iniciar.'
python server.py
