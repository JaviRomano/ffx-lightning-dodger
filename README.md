# FFX Lightning Dodger

Detecta el destello de los rayos en *Final Fantasy X* (Steam, Llanura de los Rayos) por captura de pantalla y pulsa la tecla de esquive con un delay fijo calibrado.

- Solo lee píxeles de pantalla y simula teclado (pynput). Sin APIs de Steam ni acceso a memoria.
- Valores validados (100 % de esquives): HSV 205, confianza 0.6, delay 220 ms, pulsación 100 ms.

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso

**Interfaz gráfica**

```powershell
python app_gui.py
```

1. **Seleccionar ROI**: arrastra un rectángulo sobre la ventana de FFX (ENTER confirmar, R reiniciar, ESC cancelar).
2. **Calibrar** (opcional): teclas 1/2/3 aplican los presets Validado/Sensible/Estricto; ENTER/S guarda, ESC/Q cancela.
3. **INICIAR** y haz clic en la ventana de FFX para darle el foco.

**CLI**

```powershell
python main.py                    # detector con config.json
python main.py --seleccionar-roi
python main.py --calibrar
python main.py --debug            # incluye CPU/RAM/FPS cada 5 s
```

**Herramientas**

```powershell
python -m herramientas.calibrar_timing   # mide tu reacción y tu pulsación
python -m herramientas.medir_destello    # duración del destello e intervalo entre rayos
python -m herramientas.test_input        # envía una pulsación de prueba
```

## Generar el .exe

```powershell
.\build_exe.ps1
```

Resultado: `dist\FFXLightningDodger\FFXLightningDodger.exe`, con `config.json` y `logs\` junto al ejecutable.

- Si FFX se ejecuta como administrador, el .exe también debe hacerlo (Windows bloquea el input simulado entre niveles de privilegio).
- Un .exe sin firmar que captura pantalla y simula teclado puede ser marcado por el antivirus: excluye la carpeta si ocurre.

## Estructura

```
main.py            CLI
app_gui.py         Entrada de la GUI y del .exe
dodger/            Núcleo: config, captura, detector, input, orquestador, logging, estadísticas
herramientas/      Selector de ROI, calibraciones, medición y prueba de input
gui/               Ventana customtkinter
monitor/           Rendimiento (psutil)
```

Logs y resúmenes de sesión en `logs/` (se conservan los 30 más recientes de cada tipo).
