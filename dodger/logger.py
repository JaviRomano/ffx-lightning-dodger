"""Logging: consola (si existe), un archivo por sesión en logs/ y poda de archivos viejos."""

import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import DIR_LOGS

NOMBRE_LOGGER = "ffx_dodger"
MAX_ARCHIVOS = 30
"""Archivos conservados por tipo (ffx_dodger_*.log y sesion_*.txt)."""

FORMATO = logging.Formatter(
    "[%(asctime)s.%(msecs)03d] %(levelname)-5s │ %(message)s", datefmt="%H:%M:%S"
)


def configurar_logging(nivel: int = logging.INFO, dir_logs: Path = DIR_LOGS) -> logging.Logger:
    """Configura el logger una sola vez; las llamadas posteriores lo devuelven sin tocarlo."""
    logger = logging.getLogger(NOMBRE_LOGGER)
    if logger.handlers:
        return logger

    logger.setLevel(nivel)
    logger.propagate = False

    # En el .exe sin consola sys.stdout es None
    if sys.stdout is not None:
        # Consolas no UTF-8 (cp1252): sustituir ⚡/│ en vez de lanzar UnicodeEncodeError
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(errors="replace")
        consola = logging.StreamHandler(sys.stdout)
        consola.setFormatter(FORMATO)
        logger.addHandler(consola)

    dir_logs.mkdir(parents=True, exist_ok=True)
    podar_archivos(dir_logs)
    archivo = logging.FileHandler(
        dir_logs / f"ffx_dodger_{datetime.now():%Y%m%d_%H%M%S}.log", encoding="utf-8"
    )
    archivo.setFormatter(FORMATO)
    logger.addHandler(archivo)

    return logger


def podar_archivos(dir_logs: Path) -> None:
    """Conserva solo los MAX_ARCHIVOS más recientes de cada tipo."""
    for patron in ("ffx_dodger_*.log", "sesion_*.txt"):
        for viejo in sorted(dir_logs.glob(patron))[:-MAX_ARCHIVOS]:
            try:
                viejo.unlink()
            except OSError:
                pass
