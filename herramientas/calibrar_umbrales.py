"""Calibración de umbrales en OpenCV con presets (teclas 1/2/3).

Usa el MISMO detector que el dodger: lo que marca DESTELLO aquí es lo que dispararía la tecla.
"""

import logging
import time
from dataclasses import replace
from typing import Optional

import cv2
import mss

from dodger.captura import calcular_roi, capturar_bgr
from dodger.config import PRESETS_UMBRALES, Config, nombre_preset
from dodger.detector import DetectorDestellos

ANCHO_VISTA = 960
DESTELLO_VISIBLE_S = 0.5
TECLAS_PRESET = {ord("1"): "Validado", ord("2"): "Sensible", ord("3"): "Estricto"}
CAMPOS_UMBRALES = ("umbral_valor_hsv", "area_minima_pixeles", "delta_minimo",
                   "confianza_minima", "debounce_ms")
FUENTE = cv2.FONT_HERSHEY_SIMPLEX

# Trackbar → (campo, máximo, factor de escala entero)
TRACKBARS = {
    "Umbral HSV V": ("umbral_valor_hsv", 255, 1),
    "Area min": ("area_minima_pixeles", 200, 1),
    "Delta min x100": ("delta_minimo", 50, 100),
    "Conf min x100": ("confianza_minima", 100, 100),
}


class CalibradorUmbrales:
    """ENTER/S guarda, ESC/Q o cerrar ventana cancela. No escribe en disco: devuelve los valores."""

    VENTANA = "FFX Calibracion de umbrales"

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = replace(config)  # Copia: el original no cambia hasta confirmar
        self.log = logger

    def _crear_trackbars(self) -> None:
        for nombre, (campo, maximo, factor) in TRACKBARS.items():
            valor = int(round(getattr(self.config, campo) * factor))
            cv2.createTrackbar(nombre, self.VENTANA, valor, maximo, lambda _: None)

    def _leer_trackbars(self) -> None:
        for nombre, (campo, _, factor) in TRACKBARS.items():
            valor = cv2.getTrackbarPos(nombre, self.VENTANA)
            if campo == "area_minima_pixeles":
                valor = max(1, valor)
            elif campo == "delta_minimo":
                valor = max(1, valor)  # delta 0 dispararía con cualquier ruido
            setattr(self.config, campo, valor / factor if factor != 1 else valor)

    def _aplicar_preset(self, nombre: str) -> None:
        self.config.actualizar(**PRESETS_UMBRALES[nombre])
        for trackbar, (campo, _, factor) in TRACKBARS.items():
            cv2.setTrackbarPos(trackbar, self.VENTANA, int(round(getattr(self.config, campo) * factor)))
        self.log.info(f"Preset aplicado: {nombre}")

    def _componer_vista(self, frame, detector: DetectorDestellos, escala: float,
                        destello: bool):
        vista = cv2.resize(frame, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
        mascara = cv2.resize(detector.ultima_mascara, (vista.shape[1], vista.shape[0]),
                             interpolation=cv2.INTER_NEAREST)
        overlay = vista.copy()
        overlay[mascara > 0] = (0, 0, 255)
        vista = cv2.addWeighted(vista, 0.6, overlay, 0.4, 0)

        c = self.config
        lineas = [
            (f"Preset: {nombre_preset(c)}   [1] Validado  [2] Sensible  [3] Estricto", (255, 255, 255)),
            (f"Ratio {detector.ultimo_ratio:.3f} | Delta {detector.ultimo_delta:+.3f} "
             f"(min {c.delta_minimo:.2f}) | Conf {detector.ultima_confianza:.2f} "
             f"(min {c.confianza_minima:.2f})", (255, 255, 255)),
            ("DESTELLO" if destello else "---", (0, 255, 0) if destello else (160, 160, 160)),
        ]
        y = 28
        for texto, color in lineas:
            cv2.putText(vista, texto, (10, y), FUENTE, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(vista, texto, (10, y), FUENTE, 0.6, color, 1, cv2.LINE_AA)
            y += 26
        pie = "ENTER/S = guardar   ESC/Q = cancelar"
        cv2.putText(vista, pie, (10, vista.shape[0] - 12), FUENTE, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(vista, pie, (10, vista.shape[0] - 12), FUENTE, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        return vista

    def ejecutar(self) -> Optional[dict]:
        """Devuelve {campo: valor} de los umbrales si se guarda, o None si se cancela."""
        self.log.info("Calibración: 1/2/3 presets | ENTER/S guardar | ESC/Q cancelar")
        cv2.namedWindow(self.VENTANA, cv2.WINDOW_AUTOSIZE)
        self._crear_trackbars()

        detector = DetectorDestellos(self.config)  # Comparte self.config: ve los trackbars al vuelo
        ts_destello = float("-inf")
        mostrada = False
        guardar = False

        try:
            with mss.mss() as sct:
                roi = calcular_roi(self.config, sct)
                escala = min(1.0, ANCHO_VISTA / roi["width"])

                while True:
                    if mostrada and cv2.getWindowProperty(self.VENTANA, cv2.WND_PROP_VISIBLE) < 1:
                        break  # Cerrada con la X = cancelar

                    self._leer_trackbars()
                    frame = capturar_bgr(sct, roi)
                    ts = time.perf_counter()
                    if detector.procesar(frame, ts) is not None:
                        ts_destello = ts

                    vista = self._componer_vista(frame, detector, escala,
                                                 ts - ts_destello < DESTELLO_VISIBLE_S)
                    cv2.imshow(self.VENTANA, vista)
                    mostrada = True

                    tecla = cv2.waitKey(16) & 0xFF
                    if tecla in TECLAS_PRESET:
                        self._aplicar_preset(TECLAS_PRESET[tecla])
                    elif tecla in (13, ord("s"), ord("S")):
                        guardar = True
                        break
                    elif tecla in (27, ord("q"), ord("Q")):
                        break
        except Exception as e:
            self.log.error(f"Error en calibración: {e}", exc_info=True)
            guardar = False
        finally:
            cv2.destroyAllWindows()
            cv2.waitKey(1)

        if not guardar:
            self.log.info("Calibración cancelada: sin cambios")
            return None

        valores = {campo: getattr(self.config, campo) for campo in CAMPOS_UMBRALES}
        self.log.info(f"Umbrales calibrados ({nombre_preset(self.config)}): {valores}")
        return valores
