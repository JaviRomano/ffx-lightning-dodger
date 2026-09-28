"""Orquestador: arranca y detiene los hilos. No bloquea ni registra señales (apto para GUI)."""

import logging
from dataclasses import asdict
from datetime import datetime
from queue import Queue
from threading import Event, Thread
from typing import Callable, Optional

from monitor.rendimiento import MonitorRendimiento

from .captura import CapturaPantalla
from .config import DIR_LOGS, Config
from .detector import DetectorDestellos, loop_deteccion
from .estadisticas import EstadisticasDodge
from .input_sim import SimuladorInput


class LightningDodger:
    """Ciclo de vida: arrancar() → (activo) → detener(). Se puede repetir."""

    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.log = logger
        self.evento_parar = Event()
        self.stats = EstadisticasDodge()
        self.rendimiento: Optional[MonitorRendimiento] = None
        self._hilos: list[Thread] = []

    @property
    def activo(self) -> bool:
        return any(hilo.is_alive() for hilo in self._hilos)

    def _banner(self) -> None:
        c = self.config
        roi = (f"{c.roi_width}x{c.roi_height} en ({c.roi_left}, {c.roi_top})"
               if c.roi_manual else f"{c.roi_porcentaje * 100:.0f}% centro")
        self.log.info(
            f"⚡ FFX LIGHTNING DODGER — ACTIVO | tecla '{c.tecla_dodge}' | "
            f"delay {c.delay_dodge_ms}ms | pulsación {c.duracion_pulsacion_ms}ms | "
            f"HSV {c.umbral_valor_hsv} | conf≥{c.confianza_minima} | ROI {roi}"
        )

    def _proteger(self, nombre: str, funcion: Callable[[], None]) -> None:
        """Si un hilo falla, se registra y se para todo (nunca queda medio sistema vivo)."""
        try:
            funcion()
        except Exception:
            self.log.exception(f"Error en hilo '{nombre}' — deteniendo el dodger")
            self.evento_parar.set()

    def arrancar(self) -> None:
        """Crea colas, componentes e hilos nuevos y los arranca. No bloquea."""
        if self.activo:
            raise RuntimeError("El dodger ya está activo")
        errores = self.config.validar()
        if errores:
            raise ValueError("; ".join(errores))

        self.evento_parar = Event()
        self.stats = EstadisticasDodge()
        cola_frames: Queue = Queue(maxsize=10)
        cola_eventos: Queue = Queue(maxsize=50)

        captura = CapturaPantalla(self.config, cola_frames, self.evento_parar, self.log)
        detector = DetectorDestellos(self.config)
        input_sim = SimuladorInput(self.config, cola_eventos, self.evento_parar,
                                   self.stats, self.log)
        self.rendimiento = MonitorRendimiento(self.stats, self.evento_parar, self.log)

        objetivos = [
            ("Captura", captura.loop_captura),
            ("Detector", lambda: loop_deteccion(detector, cola_frames, cola_eventos,
                                                self.evento_parar, self.stats, self.log)),
            ("Input", input_sim.loop_input),
            ("Rendimiento", self.rendimiento.loop),
        ]

        self._banner()
        self._hilos = [
            Thread(target=self._proteger, args=(nombre, funcion), name=nombre, daemon=True)
            for nombre, funcion in objetivos
        ]
        for hilo in self._hilos:
            hilo.start()
            self.log.debug(f"Hilo '{hilo.name}' arrancado")

    def detener(self) -> str:
        """Para los hilos, vuelca la sesión a logs/ y devuelve el resumen."""
        if not self._hilos:
            return ""
        self.evento_parar.set()
        for hilo in self._hilos:
            hilo.join(timeout=3.0)
            if hilo.is_alive():
                self.log.warning(f"Hilo '{hilo.name}' no terminó a tiempo")
        self._hilos = []

        resumen = self.stats.resumen()
        self.log.info(resumen)
        DIR_LOGS.mkdir(parents=True, exist_ok=True)
        ruta = DIR_LOGS / f"sesion_{datetime.now():%Y%m%d_%H%M%S}.txt"
        self.stats.volcar(ruta, asdict(self.config))
        self.log.info(f"Resumen guardado en: {ruta}")
        return resumen
