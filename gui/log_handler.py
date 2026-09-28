"""Handler de logging que envía líneas a una cola; la GUI la vacía desde su hilo."""

import logging
from queue import Queue

FORMATO_GUI = logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")


def _solo_bmp(texto: str) -> str:
    """Tk en Windows no pinta bien caracteres fuera del BMP (🎮, 🛑)."""
    return "".join(c for c in texto if ord(c) <= 0xFFFF)


class ColaLogHandler(logging.Handler):
    """Thread-safe: los hilos del dodger escriben, la GUI lee con after()."""

    def __init__(self, cola: Queue):
        super().__init__()
        self.cola = cola
        self.setFormatter(FORMATO_GUI)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.cola.put_nowait(_solo_bmp(self.format(record)).strip())
        except Exception:
            self.handleError(record)
