# CLAUDE.md — FFX Lightning Dodger

Contexto persistente para Claude Code. Leer completo antes de cualquier acción.

---

## 1. Qué es el proyecto

App Python que detecta el destello blanco de los rayos en *Final Fantasy X* (Steam, Windows 11, Llanura de los Rayos / Thunder Plains) mediante captura de pantalla + visión por computador, y simula la pulsación de la tecla de esquive con un delay fijo calibrado. Interfaz mínima con customtkinter y distribución como `.exe` (PyInstaller).

- **Plataforma:** Windows 11, monitor principal **3440x1440** (ultrawide). FFX en ventana sin bordes (~1900x1070) a 30 FPS.
- **Tecla de esquive:** `c` (remapeada por el usuario; equivale a X del mando PlayStation).
- **Ubicación:** `D:\__GIT__\ffx-lightning-dodger` (repositorio git, remoto en GitHub).
- **Entorno:** virtualenv en `.venv` (Python 3.12; activar con `.\.venv\Scripts\Activate.ps1`).
- **Uso:** personal, local, sin APIs de Steam, sin lectura/escritura de memoria del proceso.

---

## 2. Modo de trabajo — OBLIGATORIO

- **Idioma:** español ES. Términos técnicos en inglés solo si no tienen traducción.
- **Tono:** directo y técnico. Sin saludos ni preámbulos.
- **Cambios solo bajo petición explícita.** Por defecto, analizar y proponer (fragmento antes/después + archivo:línea).
- Checkpoints al cerrar cada bloque: `[BLOQUE X COMPLETADO]`.
- Marca `DECISIÓN PENDIENTE` cuando algo dependa de una elección del usuario.
- **Anti-sycophancy:** si una decisión técnica es subóptima, dilo antes de seguir. Si la petición es ambigua, pide aclaración antes de actuar.
- Scope: una fase por sesión. No expandir sin confirmación.
- No ejecutar nada que requiera FFX abierto ni que envíe pulsaciones de teclado sin confirmación explícita. Para pruebas automáticas, anular `SimuladorInput._pulsar_tecla`.

---

## 3. Estado funcional — VALIDADO (100 % de esquives en partida)

| Parámetro | Valor | Origen |
|---|---|---|
| `umbral_valor_hsv` | 205 | Calibración visual |
| `confianza_minima` | 0.6 | Ver fórmula en §6 |
| `delay_dodge_ms` | 220 | Media de reacción humana (`calibrar_timing`) |
| `duracion_pulsacion_ms` | 100 | Media de pulsación humana |
| `debounce_ms` | 50 | — |

- Los valores humanos medidos son los óptimos para delay y duración de pulsación.
- Input: **pynput** es el único método que FFX acepta (SendInput por scancode y keybd_event NO funcionan).
- Latencia real captura→pulsación: ~248 ms con delay 220 (≈25 ms de análisis del frame 1903x1080 + 4–13 ms de exceso de `Event.wait` en Windows). El 100 % se validó **con ese sobrecoste incluido**.

**REGLA:** no modificar la lógica de detección (`dodger/detector.py`), el tamaño del frame analizado ni la espera del input (`Event.wait` en `dodger/input_sim.py`) sin recalibrar el delay. Si se reduce el frame o se pasa a espera absoluta, el equivalente es `delay_dodge_ms ≈ 248` desde el `ts` de captura.

---

## 4. Estructura

```
ffx-lightning-dodger/
├── main.py                   # CLI (argparse)
├── app_gui.py                # Entrada de la GUI y del .exe
├── build_exe.ps1             # PyInstaller --onedir --windowed → dist\FFXLightningDodger\
├── config.json               # Config activa (valores validados)
├── requirements.txt          # Versiones fijadas
├── README.md
├── dodger/
│   ├── config.py             # Config dataclass, rutas base (junto al .exe si está congelado), presets
│   ├── estadisticas.py       # EstadisticasDodge + volcado de sesión
│   ├── logger.py             # configurar_logging() una sola vez; logs/ con poda (30 por tipo)
│   ├── captura.py            # calcular_roi(config, sct), capturar_bgr(), hilo CapturaPantalla
│   ├── detector.py           # Lógica de detección ÚNICA: analizar_frame, DetectorDestellos.procesar, loop_deteccion
│   ├── input_sim.py          # SimuladorInput (pynput)
│   └── orquestador.py        # LightningDodger: arrancar() / detener() / activo (no bloquea, sin señales)
├── herramientas/             # Ejecutar como módulo: python -m herramientas.<nombre>
│   ├── selector_roi.py       # Ventana OpenCV; devuelve la ROI, no guarda
│   ├── calibrar_umbrales.py  # Ventana OpenCV con trackbars + presets 1/2/3; devuelve umbrales o None
│   ├── calibrar_timing.py    # Reacción y pulsación humanas
│   ├── medir_destello.py     # Duración del destello e intervalo entre rayos
│   └── test_input.py         # Una pulsación de prueba (ENVÍA TECLA)
├── gui/
│   ├── app.py                # Ventana customtkinter
│   └── log_handler.py        # Log → cola → CTkTextbox
└── monitor/
    └── rendimiento.py        # CPU, RAM, FPS procesados (psutil), DEBUG cada 5 s
```

Fuera de git (`.gitignore`): `.venv/`, `logs/`, `build/`, `dist/`, `*.spec`, `_papelera/` (papelera manual con el monolito antiguo y artefactos obsoletos).

**Principios:** dependencias en una dirección (`gui`/`main` → `orquestador` → componentes → `config`); las herramientas importan de `dodger/`, nunca duplican lógica; las ventanas OpenCV se ejecutan en el hilo principal (la GUI se oculta mientras tanto).

---

## 5. Presets de umbrales (`dodger/config.py`)

| Preset | HSV | Delta | Área | Conf | Debounce | Estado |
|---|---|---|---|---|---|---|
| Validado | 205 | 0.05 | 10 | 0.60 | 50 | ✅ 100 % |
| Sensible | 190 | 0.04 | 10 | 0.55 | 50 | ⚠ sin validar |
| Estricto | 220 | 0.08 | 50 | 0.70 | 300 | ⚠ sin validar |

---

## 6. Deuda técnica conocida

- **Fórmula de confianza:** con el gate `delta ≥ delta_minimo`, el término delta siempre vale 0.3 y el RGB (gris ≥ 240) casi nunca aporta (gris ≤ V). Con `confianza_minima=0.6` equivale a `ratio ≥ 0.075`. Se mantiene tal cual porque está validada. `DECISIÓN PENDIENTE` si se replantea.
- **Coste del análisis:** ~25 ms/frame sobre 33 ms de presupuesto. Reducir el frame (×0.25) lo bajaría a ~2 ms, pero obliga a recalibrar (ver §3).
- **mss 10.1:** nunca abrir una instancia `mss.mss()` anidada dentro de otra en el mismo hilo (error `'_thread._local' object has no attribute 'data'`). Pasar siempre la instancia `sct` abierta.
- **Sin tests automáticos.** La equivalencia del detector se verificó con frames sintéticos contra el monolito original.
- `.exe` sin firmar (captura pantalla + simula teclado): posible falso positivo de antivirus.
- Si FFX se ejecuta como administrador, el dodger también debe hacerlo (UIPI).

---

## 7. Comandos de referencia

```powershell
.\.venv\Scripts\Activate.ps1
python app_gui.py                             # GUI
python main.py --help
python main.py                                # detector con config.json
python main.py --seleccionar-roi
python main.py --calibrar
python main.py --debug                        # + rendimiento cada 5 s
python -m herramientas.calibrar_timing
python -m herramientas.medir_destello
.\build_exe.ps1                               # dist\FFXLightningDodger\FFXLightningDodger.exe
```
