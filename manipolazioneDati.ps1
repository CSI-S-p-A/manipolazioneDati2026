$ProjectDir = $PSScriptRoot

Write-Host "`n--- Pulling latest changes from Git..."
Set-Location $ProjectDir
git pull

Write-Host "`n--- Running main.py..."
uv run main.py

Write-Host "`n--- Done. Press Enter to exit."
Read-Host
