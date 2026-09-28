"""Simulación de la pulsación de esquive con pynput (único método que FFX acepta)."""

import logging
import time
from queue import Empty, Queue
from threading import Event

from pynput.keyboard import Controller

from .config import Config
from .estadisticas import EstadisticasDodge


class SimuladorInput:
    """Espera delay_dodge_ms tras cada evento y pulsa la tecla configurada."""

    def __init__(self, config: Config, cola_eventos: Queue, evento_parar: Event,
                 stats: EstadisticasDodge, logger: logging.Logger):
        self.config = config
        self.cola_eventos = cola_eventos
        self.evento_parar = evento_parar
        self.stats = stats
        self.log = logger
        self._controlador = None

    def _pulsar_tecla(self) -> float:
        """press + release. Devuelve la duración real en ms."""
        if self._controlador is None:
            self._controlador = Controller()

        tecla = self.config.tecla_dodge
        t0 = time.perf_counter()
        self._controlador.press(tecla)
        time.sleep(self.config.duracion_pulsacion_ms / 1000.0)
        self._controlador.release(tecla)
        return (time.perf_counter() - t0) * 1000

    def loop_input(self) -> None:
        delay_ms = self.config.delay_dodge_ms
        delay_s = delay_ms / 1000.0
        self.log.info(
            f"Hilo de input iniciado — tecla: '{self.config.tecla_dodge}' | delay: {delay_ms}ms"
        )

        while not self.evento_parar.is_set():
            try:
                evento = self.cola_eventos.get(timeout=0.5)
            except Empty:
                continue

            # Delay validado tal cual (Event.wait): no cambiar sin recalibrar
            self.evento_parar.wait(timeout=delay_s)
            if self.evento_parar.is_set():
                break

            latencia_total = (time.perf_counter() - evento["ts"]) * 1000
            self._pulsar_tecla()
            self.stats.pulsaciones_enviadas += 1
            self.stats.latencias_ms.append(latencia_total)

            self.log.info(
                f"🎮 DODGE #{self.stats.pulsaciones_enviadas} | "
                f"delay={delay_ms}ms | latencia_total={latencia_total:.0f}ms"
            )
            if self.stats.pulsaciones_enviadas % 10 == 0:
                self.log.info(self.stats.resumen())

        self.log.info("Hilo de input finalizado")
