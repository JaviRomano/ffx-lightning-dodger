"""CPU, RAM y FPS procesados del proceso (psutil). Log DEBUG cada 5 s."""

import logging
import time
from threading import Event

try:
    import psutil
except ImportError:  # Opcional: sin psutil el monitor no hace nada
    psutil = None

from dodger.estadisticas import EstadisticasDodge

INTERVALO_S = 5.0


class MonitorRendimiento:
    """Últimos valores en cpu_pct, ram_mb y fps (los lee la GUI)."""

    def __init__(self, stats: EstadisticasDodge, evento_parar: Event, logger: logging.Logger):
        self.stats = stats
        self.evento_parar = evento_parar
        self.log = logger
        self.cpu_pct = 0.0
        self.ram_mb = 0.0
        self.fps = 0.0

    def loop(self) -> None:
        if psutil is None:
            self.log.debug("psutil no instalado: monitor de rendimiento desactivado")
            return

        proceso = psutil.Process()
        nucleos = psutil.cpu_count() or 1
        proceso.cpu_percent(None)  # Primera llamada: fija la referencia
        frames_prev = self.stats.frames_procesados
        t_prev = time.perf_counter()

        while not self.evento_parar.wait(INTERVALO_S):
            ahora = time.perf_counter()
            frames = self.stats.frames_procesados
            self.fps = (frames - frames_prev) / (ahora - t_prev)
            self.cpu_pct = proceso.cpu_percent(None) / nucleos
            self.ram_mb = proceso.memory_info().rss / 2**20
            frames_prev, t_prev = frames, ahora

            self.log.debug(
                f"Rendimiento: CPU {self.cpu_pct:.0f}% | RAM {self.ram_mb:.0f} MB | "
                f"{self.fps:.1f} FPS procesados"
            )
