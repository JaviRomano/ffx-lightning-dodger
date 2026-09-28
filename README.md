# FFX Lightning Dodger

Herramienta de automatizacion de videojuegos basada en vision por computador, escrita en Python.

## Descripcion

Automatizacion en tiempo real que detecta un patron visual en pantalla y ejecuta una respuesta de input de forma automatica. El sistema usa una arquitectura multi-hilo: un hilo se encarga de la captura de pantalla, otro de la deteccion del patron y otro de la simulacion de input, ejecutandose de forma concurrente para minimizar la latencia.

En concreto, detecta el destello en la llanura de los rayos en *Final Fantasy X* (Steam) y pulsa la tecla de esquive con un delay fijo calibrado. Solo lee pixeles de pantalla y simula teclado: sin APIs de Steam ni acceso a memoria del proceso.

## Stack

Python, OpenCV, mss (captura de pantalla), pynput (simulacion de input), customtkinter (interfaz), psutil (rendimiento), PyInstaller (ejecutable).

## Caracteristicas

Arquitectura multi-hilo con captura de pantalla, deteccion de patrones y simulacion de input ejecutandose de forma concurrente.<br>
Calibracion manual de la region de interes (ROI), del umbral HSV y del nivel de confianza, para ajustar la deteccion a las condiciones reales del juego, con presets prefijados.<br>
Delay de esquive de 220 ms y pulsacion de 100 ms, calibrados a partir del tiempo de reaccion humano: 100 % de esquives en las pruebas.<br>
Interfaz grafica minima y distribucion como ejecutable de Windows.

## Contexto

Este proyecto nace de un ejercicio de ingenieria inversa practica: entender el comportamiento visual de un sistema externo y construir sobre el una solucion de automatizacion fiable.

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uso

**Interfaz grafica**

```powershell
python app_gui.py
```

1. **Seleccionar ROI**: arrastra un rectangulo sobre la ventana de FFX (ENTER confirmar, R reiniciar, ESC cancelar).
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
python -m herramientas.calibrar_timing   # mide tu reaccion y tu pulsacion
python -m herramientas.medir_destello    # duracion del destello e intervalo entre rayos
python -m herramientas.test_input        # envia una pulsacion de prueba
```

## Generar el .exe

```powershell
.\build_exe.ps1
```

Resultado: `dist\FFXLightningDodger\FFXLightningDodger.exe`, con `config.json` y `logs\` junto al ejecutable.

- Si FFX se ejecuta como administrador, el .exe tambien debe hacerlo (Windows bloquea el input simulado entre niveles de privilegio).
- Un .exe sin firmar que captura pantalla y simula teclado puede ser marcado por el antivirus: excluye la carpeta si ocurre.

## Estructura

```
main.py            CLI
app_gui.py         Entrada de la GUI y del .exe
dodger/            Nucleo: config, captura, detector, input, orquestador, logging, estadisticas
herramientas/      Selector de ROI, calibraciones, medicion y prueba de input
gui/               Ventana customtkinter
monitor/           Rendimiento (psutil)
```

Logs y resumenes de sesion en `logs/` (se conservan los 30 mas recientes de cada tipo).

## Nota

Proyecto con fines educativos y de demostracion tecnica de vision por computador en tiempo real.
