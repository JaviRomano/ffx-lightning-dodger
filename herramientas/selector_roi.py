"""Selector visual de ROI: ventana OpenCV sobre una captura del monitor principal."""

import logging
from typing import Optional

import cv2
import mss
import numpy as np

ANCHO_MAX_DISPLAY = 1200
FUENTE = cv2.FONT_HERSHEY_SIMPLEX


def _texto(img: np.ndarray, texto: str, pos: tuple[int, int],
           color: tuple[int, int, int], escala: float) -> None:
    """Texto con contorno negro para que se lea sobre cualquier fondo."""
    cv2.putText(img, texto, pos, FUENTE, escala, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, texto, pos, FUENTE, escala, color, 1, cv2.LINE_AA)


class SelectorROI:
    """Arrastra un rectángulo sobre FFX. ENTER confirma, R reinicia, ESC cancela."""

    VENTANA = "Seleccionar ROI - arrastra un rectangulo sobre FFX"

    def __init__(self, logger: logging.Logger):
        self.log = logger
        self._arrastrando = False
        self._inicio = (0, 0)
        self._fin = (0, 0)
        self._seleccionada = False
        self._escala = 1.0

    def _callback_raton(self, evento, x, y, flags, param) -> None:
        if evento == cv2.EVENT_LBUTTONDOWN:
            self._arrastrando = True
            self._inicio = self._fin = (x, y)
            self._seleccionada = False
        elif evento == cv2.EVENT_MOUSEMOVE and self._arrastrando:
            self._fin = (x, y)
        elif evento == cv2.EVENT_LBUTTONUP:
            self._arrastrando = False
            self._fin = (x, y)
            # Tamaño mínimo para evitar clics accidentales
            dx = abs(self._fin[0] - self._inicio[0])
            dy = abs(self._fin[1] - self._inicio[1])
            self._seleccionada = dx > 10 and dy > 10

    def _roi_relativa(self) -> dict:
        """Rectángulo actual en píxeles reales, relativo al monitor."""
        (x1, y1), (x2, y2) = self._inicio, self._fin
        return {
            "left": int(min(x1, x2) / self._escala),
            "top": int(min(y1, y2) / self._escala),
            "width": int(abs(x2 - x1) / self._escala),
            "height": int(abs(y2 - y1) / self._escala),
        }

    def ejecutar(self) -> Optional[dict]:
        """Devuelve la ROI {top, left, width, height} en coordenadas de pantalla, o None."""
        self.log.info("Selector de ROI: arrastra sobre FFX | ENTER confirmar | R reiniciar | ESC cancelar")

        with mss.mss() as sct:
            mon = sct.monitors[1]
            imagen = np.array(sct.grab(mon))[:, :, :3]

        alto, ancho = imagen.shape[:2]
        self._escala = min(ANCHO_MAX_DISPLAY, ancho) / ancho
        base = cv2.resize(imagen, (int(ancho * self._escala), int(alto * self._escala)),
                          interpolation=cv2.INTER_AREA)
        self.log.info(f"Pantalla: {ancho}x{alto} → display {base.shape[1]}x{base.shape[0]}")

        cv2.namedWindow(self.VENTANA, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.VENTANA, self._callback_raton)
        confirmada = False

        try:
            while True:
                display = base.copy()

                if self._arrastrando or self._seleccionada:
                    p1, p2 = self._inicio, self._fin
                    overlay = display.copy()
                    cv2.rectangle(overlay, p1, p2, (0, 255, 0), -1)
                    cv2.addWeighted(overlay, 0.2, display, 0.8, 0, display)
                    cv2.rectangle(display, p1, p2, (0, 255, 0), 2)
                    r = self._roi_relativa()
                    _texto(display, f"{r['width']}x{r['height']} en ({r['left']}, {r['top']})",
                           (min(p1[0], p2[0]), max(15, min(p1[1], p2[1]) - 8)), (0, 255, 0), 0.6)

                _texto(display, "Arrastra para seleccionar | ENTER=confirmar | R=reiniciar | ESC=cancelar",
                       (10, display.shape[0] - 15), (255, 255, 255), 0.5)

                cv2.imshow(self.VENTANA, display)
                tecla = cv2.waitKey(30) & 0xFF

                if tecla == 13 and self._seleccionada:
                    confirmada = True
                    break
                if tecla in (ord("r"), ord("R")):
                    self._seleccionada = False
                    self._inicio = self._fin = (0, 0)
                elif tecla == 27:
                    break
                elif cv2.getWindowProperty(self.VENTANA, cv2.WND_PROP_VISIBLE) < 1:
                    break  # Cerrada con la X
        finally:
            cv2.destroyAllWindows()
            cv2.waitKey(1)

        if not confirmada:
            self.log.info("Selección de ROI cancelada")
            return None

        r = self._roi_relativa()
        roi = {"top": mon["top"] + r["top"], "left": mon["left"] + r["left"],
               "width": r["width"], "height": r["height"]}
        self.log.info(f"ROI seleccionada: {roi['width']}x{roi['height']} en ({roi['left']}, {roi['top']})")
        return roi
