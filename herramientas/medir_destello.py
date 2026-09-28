"""Medidor de la duración del destello y del intervalo entre rayos.

Uso (desde la raíz, con FFX en la Llanura):
    python -m herramientas.medir_destello
Espera varios rayos y pulsa Ctrl+C para ver resultados.
"""

import time

import mss

from dodger.captura import calcular_roi, capturar_bgr, describir_roi
from dodger.config import RUTA_CONFIG, Config
from dodger.detector import DetectorDestellos

RATIO_FIN = 0.001
"""Por debajo de este ratio se considera que el destello terminó."""


def main() -> None:
    config = Config.cargar_o_crear(RUTA_CONFIG)
    detector = DetectorDestellos(config)
    rayos: list[dict] = []
    inicio = None
    pico = 0.0

    try:
        with mss.mss() as sct:
            roi = calcular_roi(config, sct)
            print(f"\n  MEDIDOR DE DESTELLO | ROI {describir_roi(roi)} | HSV {config.umbral_valor_hsv}")
            print("  Esperando rayos... Ctrl+C para terminar.\n")

            while True:
                t = time.perf_counter()
                evento = detector.procesar(capturar_bgr(sct, roi), t)
                ratio = detector.ultimo_ratio

                if inicio is None and evento is not None:
                    inicio, pico = t, ratio
                elif inicio is not None and ratio >= RATIO_FIN:
                    pico = max(pico, ratio)
                elif inicio is not None:
                    rayos.append({"inicio": inicio, "fin": t, "duracion_ms": (t - inicio) * 1000})
                    print(f"  ⚡ Rayo #{len(rayos):>3d} | destello {rayos[-1]['duracion_ms']:>6.1f} ms "
                          f"| pico {pico:.3f}")
                    inicio = None

                restante = config.intervalo_captura - (time.perf_counter() - t)
                if restante > 0:
                    time.sleep(restante)
    except KeyboardInterrupt:
        pass

    print("\n" + "=" * 55 + "\n  RESULTADOS\n" + "=" * 55)
    if len(rayos) < 2:
        print("  Muy pocos rayos. Espera al menos 3–5.")
        return

    duraciones = [r["duracion_ms"] for r in rayos]
    intervalos = [(b["inicio"] - a["fin"]) for a, b in zip(rayos, rayos[1:])]
    print(f"  Rayos medidos: {len(rayos)} (resolución ±{config.intervalo_captura * 1000:.0f} ms)")
    print(f"  Destello : mín {min(duraciones):.0f} | media {sum(duraciones) / len(duraciones):.0f} "
          f"| máx {max(duraciones):.0f} ms")
    print(f"  Intervalo: mín {min(intervalos):.1f} | media {sum(intervalos) / len(intervalos):.1f} "
          f"| máx {max(intervalos):.1f} s")


if __name__ == "__main__":
    main()
