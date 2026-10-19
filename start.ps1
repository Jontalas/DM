$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Host 'Crónicas: http://127.0.0.1:8787'
Write-Host 'Configura Firebase y ANTHROPIC_API_KEY en las variables de entorno antes de iniciar.'
python server.py
