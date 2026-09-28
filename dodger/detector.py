"""Detección de destellos: lógica ÚNICA, usada por el dodger y por todas las herramientas.

La fórmula y los criterios están validados (100 % de esquives con delay 220 ms).
Cualquier cambio que altere el coste o el instante de detección obliga a recalibrar el delay.
"""

import logging
import time
from queue import Empty, Queue
from threading import Event
from typing import Optional

import cv2
import numpy as np

from .config import Config
from .estadisticas import EstadisticasDodge


def analizar_frame(frame: np.ndarray, config: Config,
                   ratio_anterior: float) -> tuple[float, float, np.ndarray]:
    """
    HSV → threshold V → filtro de contornos → ratio de blancura → confianza.

    Returns:
        (ratio_blancura 0–1, confianza 0–1, máscara filtrada)
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    _, mascara = cv2.threshold(hsv[:, :, 2], config.umbral_valor_hsv, 255, cv2.THRESH_BINARY)

    # Filtrar ruido: eliminar contornos con área < mínimo
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mascara_filtrada = np.zeros_like(mascara)
    for contorno in contornos:
        if cv2.contourArea(contorno) >= config.area_minima_pixeles:
            cv2.drawContours(mascara_filtrada, [contorno], -1, 255, -1)

    total = mascara_filtrada.size
    ratio = cv2.countNonZero(mascara_filtrada) / total if total > 0 else 0.0

    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, mascara_rgb = cv2.threshold(gris, config.umbral_blancura_rgb, 255, cv2.THRESH_BINARY)
    ratio_rgb = cv2.countNonZero(mascara_rgb) / total if total > 0 else 0.0

    # Confianza: intensidad HSV + confirmación RGB + cambio brusco
    delta = abs(ratio - ratio_anterior)
    confianza = min(1.0, (
        0.4 * min(1.0, ratio * 10) +
        0.3 * min(1.0, ratio_rgb * 10) +
        0.3 * min(1.0, delta / max(0.01, config.delta_minimo))
    ))
    return ratio, confianza, mascara_filtrada


def centroide(mascara: np.ndarray) -> tuple[int, int]:
    momentos = cv2.moments(mascara)
    if momentos["m00"] > 0:
        return int(momentos["m10"] / momentos["m00"]), int(momentos["m01"] / momentos["m00"])
    return mascara.shape[1] // 2, mascara.shape[0] // 2


class DetectorDestellos:
    """Detector con estado (ratio anterior y debounce). Sin hilos ni colas."""

    def __init__(self, config: Config):
        self.config = config
        self._ratio_anterior = 0.0
        self._ultimo_destello_ts = 0.0
        # Métricas del último frame (para HUD de calibración)
        self.ultimo_ratio = 0.0
        self.ultimo_delta = 0.0
        self.ultima_confianza = 0.0
        self.ultima_mascara: Optional[np.ndarray] = None

    def _es_destello(self, delta: float, confianza: float, ts: float) -> bool:
        # El destello es un INCREMENTO brusco (no decremento ni estático)
        if delta < self.config.delta_minimo:
            return False
        if confianza < self.config.confianza_minima:
            return False
        # Debounce: evitar detecciones duplicadas
        return (ts - self._ultimo_destello_ts) * 1000 >= self.config.debounce_ms

    def procesar(self, frame: np.ndarray, ts: float) -> Optional[dict]:
        """Analiza un frame. Devuelve el evento {ts, ratio, confianza, posicion} o None."""
        ratio, confianza, mascara = analizar_frame(frame, self.config, self._ratio_anterior)
        delta = ratio - self._ratio_anterior

        evento = None
        if self._es_destello(delta, confianza, ts):
            self._ultimo_destello_ts = ts
            evento = {"ts": ts, "ratio": ratio, "confianza": confianza,
                      "posicion": centroide(mascara)}

        self._ratio_anterior = ratio
        self.ultimo_ratio, self.ultimo_delta = ratio, delta
        self.ultima_confianza, self.ultima_mascara = confianza, mascara
        return evento


def loop_deteccion(detector: DetectorDestellos, cola_frames: Queue, cola_eventos: Queue,
                   evento_parar: Event, stats: EstadisticasDodge,
                   log: logging.Logger) -> None:
    """Hilo consumidor: frames → eventos de destello. Descarta frames con lag."""
    config = detector.config
    log.info("Hilo de detección iniciado")
    ultimo_aviso_fatiga = 0.0

    while not evento_parar.is_set():
        try:
            ts, frame = cola_frames.get(timeout=0.5)
        except Empty:
            continue

        # Frame demasiado viejo: drenar toda la cola de golpe
        latencia_captura = (time.perf_counter() - ts) * 1000
        if latencia_captura > config.lag_critico_ms:
            descartados = 1
            while not cola_frames.empty():
                try:
                    cola_frames.get_nowait()
                    descartados += 1
                except Empty:
                    break
            log.warning(f"⚠ Lag: {latencia_captura:.0f}ms — drenados {descartados} frames viejos")
            continue

        evento = detector.procesar(frame, ts)
        stats.frames_procesados += 1

        if evento is not None:
            stats.destellos_detectados += 1
            stats.ultimo_destello_ts = ts
            ultimo_aviso_fatiga = 0.0
            evento["latencia_captura_ms"] = latencia_captura
            cola_eventos.put_nowait(evento)

            cx, cy = evento["posicion"]
            log.info(
                f"⚡ DESTELLO #{stats.destellos_detectados} | "
                f"conf={evento['confianza']:.2f} | pos=({cx},{cy}) | "
                f"lag={latencia_captura:.1f}ms"
            )

        # Aviso periódico si no hay destellos
        if stats.ultimo_destello_ts > 0:
            ahora = time.perf_counter()
            sin_destello = ahora - stats.ultimo_destello_ts
            if (sin_destello > config.timeout_sin_destello_s
                    and ahora - ultimo_aviso_fatiga > 30.0):
                log.warning(f"⏸  Sin destellos en {sin_destello:.0f}s — ¿Sigues en la llanura?")
                ultimo_aviso_fatiga = ahora

    log.info("Hilo de detección finalizado")
