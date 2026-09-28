"""Captura de pantalla con mss: cálculo de ROI y hilo productor de frames."""

import logging
import time
from queue import Empty, Queue
from threading import Event

import mss
import numpy as np

from .config import Config


def calcular_roi(config: Config, sct) -> dict:
    """ROI para mss. Recibe la instancia ya abierta: abrir otra anidada rompe mss 10.x."""
    if config.roi_manual:
        return {
            "top": config.roi_top,
            "left": config.roi_left,
            "width": config.roi_width,
            "height": config.roi_height,
        }

    mon = sct.monitors[1]  # Monitor principal
    ancho = int(mon["width"] * config.roi_porcentaje)
    alto = int(mon["height"] * config.roi_porcentaje)
    return {
        "top": mon["top"] + (mon["height"] - alto) // 2,
        "left": mon["left"] + (mon["width"] - ancho) // 2,
        "width": ancho,
        "height": alto,
    }


def describir_roi(roi: dict) -> str:
    return f"{roi['width']}x{roi['height']} en ({roi['left']}, {roi['top']})"


def capturar_bgr(sct, roi: dict) -> np.ndarray:
    """mss devuelve BGRA; se descarta el alfa para OpenCV."""
    return np.array(sct.grab(roi))[:, :, :3]


class CapturaPantalla:
    """Hilo de captura a fps_objetivo. Alimenta la cola con (timestamp, frame_bgr)."""

    def __init__(self, config: Config, cola_frames: Queue,
                 evento_parar: Event, logger: logging.Logger):
        self.config = config
        self.cola = cola_frames
        self.evento_parar = evento_parar
        self.log = logger

    def loop_captura(self) -> None:
        intervalo = self.config.intervalo_captura
        frames_capturados = 0
        frames_descartados = 0
        t_inicio_fps = time.perf_counter()

        self.log.info("Hilo de captura iniciado")

        try:
            # mss debe instanciarse en el mismo hilo que lo usa
            with mss.mss() as sct:
                roi = calcular_roi(self.config, sct)
                self.log.info(f"ROI: {describir_roi(roi)}")

                while not self.evento_parar.is_set():
                    t_frame = time.perf_counter()
                    frame = capturar_bgr(sct, roi)
                    ts = time.perf_counter()

                    # Cola llena: descartar el frame MÁS VIEJO para que entre el más reciente
                    if self.cola.full():
                        try:
                            self.cola.get_nowait()
                            frames_descartados += 1
                        except Empty:
                            pass
                    self.cola.put_nowait((ts, frame))
                    frames_capturados += 1

                    elapsed = time.perf_counter() - t_inicio_fps
                    if elapsed >= 5.0:
                        fps_real = frames_capturados / elapsed
                        if frames_descartados > 0:
                            self.log.debug(
                                f"Captura: {fps_real:.1f} FPS | "
                                f"{frames_descartados} frames descartados (cola llena)"
                            )
                            frames_descartados = 0
                        else:
                            self.log.debug(f"Captura: {fps_real:.1f} FPS")
                        frames_capturados = 0
                        t_inicio_fps = time.perf_counter()

                    t_dormir = intervalo - (time.perf_counter() - t_frame)
                    if t_dormir > 0:
                        time.sleep(t_dormir)

        except Exception as e:
            self.log.error(f"Error en hilo de captura: {e}", exc_info=True)
            self.evento_parar.set()

        self.log.info("Hilo de captura finalizado")
