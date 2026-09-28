"""Estadísticas de sesión y volcado a archivo."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EstadisticasDodge:
    """Contadores de la sesión. Cada campo lo escribe un único hilo."""

    destellos_detectados: int = 0      # hilo Detector
    frames_procesados: int = 0         # hilo Detector
    pulsaciones_enviadas: int = 0      # hilo Input
    latencias_ms: list = field(default_factory=list)  # hilo Input
    inicio: float = field(default_factory=time.perf_counter)
    ultimo_destello_ts: float = 0.0    # hilo Detector

    @property
    def latencia_media_ms(self) -> float:
        if not self.latencias_ms:
            return 0.0
        return sum(self.latencias_ms) / len(self.latencias_ms)

    @property
    def latencia_p95_ms(self) -> float:
        if not self.latencias_ms:
            return 0.0
        ordenadas = sorted(self.latencias_ms)
        return ordenadas[min(int(len(ordenadas) * 0.95), len(ordenadas) - 1)]

    @property
    def tiempo_activo_s(self) -> float:
        return time.perf_counter() - self.inicio

    def resumen(self) -> str:
        return (
            f"\n{'═' * 55}\n"
            f"  ESTADÍSTICAS DE SESIÓN\n"
            f"{'─' * 55}\n"
            f"  Destellos detectados : {self.destellos_detectados}\n"
            f"  Pulsaciones enviadas : {self.pulsaciones_enviadas}\n"
            f"  Latencia media       : {self.latencia_media_ms:.1f} ms\n"
            f"  Latencia P95         : {self.latencia_p95_ms:.1f} ms\n"
            f"  Tiempo activo        : {self.tiempo_activo_s:.0f} s\n"
            f"{'═' * 55}"
        )

    def volcar(self, ruta: Path, config: dict) -> None:
        """Escribe el resumen y la config usada."""
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(self.resumen())
            f.write(f"\n\nConfig: {json.dumps(config, indent=2, ensure_ascii=False)}\n")
