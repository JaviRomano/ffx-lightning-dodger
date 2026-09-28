# Genera dist\FFXLightningDodger\FFXLightningDodger.exe (modo carpeta: arranque rápido, menos falsos positivos de antivirus)
# Uso: .\build_exe.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
.\.venv\Scripts\Activate.ps1

pyinstaller --noconfirm --clean --onedir --windowed `
    --name FFXLightningDodger `
    --collect-data customtkinter `
    app_gui.py

# La config vive junto al .exe (no dentro del paquete) para poder editarla
Copy-Item config.json dist\FFXLightningDodger\ -Force
Write-Host "OK -> dist\FFXLightningDodger\FFXLightningDodger.exe"
