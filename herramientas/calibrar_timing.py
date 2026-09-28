"""Calibrador de timing manual — mide tu reacción y la duración de tu pulsación.

Uso (desde la raíz, con FFX en la Llanura):
    python -m herramientas.calibrar_timing
Pulsa la tecla de esquive como lo harías jugando. Ctrl+C para ver resultados.
Los valores humanos medidos son los óptimos para delay_dodge_ms y duracion_pulsacion_ms.
"""

import time

import mss
from pynput import keyboard

from dodger.captura import calcular_roi, capturar_bgr, describir_roi
from dodger.config import RUTA_CONFIG, Config
from dodger.detector import DetectorDestellos

TIMEOUT_S = 2.0
ESPERA_RELEASE_S = 1.0


def main() -> None:
    config = Config.cargar_o_crear(RUTA_CONFIG)
    tecla = config.tecla_dodge
    estado = {"press": None, "release": None}

    def on_press(key):
        if getattr(key, "char", None) == tecla:
            estado["press"] = time.perf_counter()

    def on_release(key):
        if getattr(key, "char", None) == tecla:
            estado["release"] = time.perf_counter()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release, daemon=True)
    listener.start()

    detector = DetectorDestellos(config)
    reacciones: list[float] = []
    pulsaciones: list[float] = []
    ts_destello = None
    n_destellos = 0

    try:
        with mss.mss() as sct:
            roi = calcular_roi(config, sct)
            print(f"\n  CALIBRADOR DE TIMING | ROI {describir_roi(roi)} | "
                  f"HSV {config.umbral_valor_hsv} | tecla '{tecla}'")
            print(f"  Pulsa '{tecla.upper()}' al ver el destello. Ctrl+C para terminar.\n")

            while True:
                t = time.perf_counter()  # Referencia: inicio de la captura del frame
                frame = capturar_bgr(sct, roi)

                if detector.procesar(frame, t) is not None and ts_destello is None:
                    ts_destello = t
                    n_destellos += 1
                    estado["press"] = estado["release"] = None
                    print(f"  ⚡ Destello #{n_destellos} — ¡pulsa!")

                if ts_destello is not None and estado["press"] is not None:
                    reaccion = (estado["press"] - ts_destello) * 1000
                    if reaccion > 0:
                        t_espera = time.perf_counter()
                        while estado["release"] is None and time.perf_counter() - t_espera < ESPERA_RELEASE_S:
                            time.sleep(0.001)
                        reacciones.append(reaccion)
                        if estado["release"] is not None:
                            duracion = (estado["release"] - estado["press"]) * 1000
                            pulsaciones.append(duracion)
                            print(f"    → Reacción {reaccion:.0f} ms | pulsación {duracion:.0f} ms")
                        else:
                            print(f"    → Reacción {reaccion:.0f} ms | pulsación no medida")
                    ts_destello = None

                if ts_destello is not None and t - ts_destello > TIMEOUT_S:
                    print("    → Sin pulsación (timeout)")
                    ts_destello = None

                restante = config.intervalo_captura - (time.perf_counter() - t)
                if restante > 0:
                    time.sleep(restante)
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()

    _informe(reacciones, pulsaciones)


def _estadistica(valores: list[float]) -> str:
    ordenados = sorted(valores)
    media = sum(valores) / len(valores)
    return (f"mín {ordenados[0]:.0f} | P25 {ordenados[len(ordenados) // 4]:.0f} | "
            f"media {media:.0f} | P75 {ordenados[len(ordenados) * 3 // 4]:.0f} | "
            f"máx {ordenados[-1]:.0f} ms")


def _informe(reacciones: list[float], pulsaciones: list[float]) -> None:
    print("\n" + "=" * 60 + "\n  RESULTADOS\n" + "=" * 60)
    if len(reacciones) < 3:
        print("  Muy pocas mediciones. Repite con al menos 5 rayos.")
        return
    print(f"  Mediciones: {len(reacciones)}")
    print(f"  Reacción  : {_estadistica(reacciones)}")
    if pulsaciones:
        print(f"  Pulsación : {_estadistica(pulsaciones)}")
    print("\n  Valores para config.json (media humana = óptimo validado):")
    print(f'    "delay_dodge_ms": {round(sum(reacciones) / len(reacciones))}')
    if pulsaciones:
        print(f'    "duracion_pulsacion_ms": {round(sum(pulsaciones) / len(pulsaciones))}')


if __name__ == "__main__":
    main()
