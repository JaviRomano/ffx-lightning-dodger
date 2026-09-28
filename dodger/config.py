"""Configuración: dataclass, rutas base y presets de umbrales."""

import json
import logging
import math
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path


def directorio_base() -> Path:
    """Carpeta del .exe si está empaquetado; raíz del proyecto si se ejecuta como script."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


RUTA_CONFIG = directorio_base() / "config.json"
DIR_LOGS = directorio_base() / "logs"


@dataclass
class Config:
    """Parámetros del dodger. Los valores por defecto son los validados (100 % de esquives)."""

    # --- Captura ---
    fps_objetivo: int = 30
    roi_porcentaje: float = 0.4
    """Fracción centrada del monitor usada como ROI. Solo si roi_manual es False."""
    roi_manual: bool = False
    roi_top: int = 0
    roi_left: int = 0
    roi_width: int = 0
    roi_height: int = 0

    # --- Detección ---
    umbral_blancura_rgb: int = 240
    umbral_valor_hsv: int = 205
    area_minima_pixeles: int = 10
    delta_minimo: float = 0.05
    confianza_minima: float = 0.6
    debounce_ms: int = 50
    timeout_sin_destello_s: int = 60

    # --- Input ---
    tecla_dodge: str = "c"
    duracion_pulsacion_ms: int = 100
    delay_dodge_ms: int = 220
    """Delay detección→pulsación. Validado con el pipeline actual: si cambia el coste
    del análisis (p. ej. reducir el frame) hay que recalibrarlo."""

    # --- Sistema ---
    lag_critico_ms: int = 150
    """Frames más viejos que esto se descartan."""

    @property
    def intervalo_captura(self) -> float:
        return 1.0 / self.fps_objetivo

    def validar(self) -> list[str]:
        """Devuelve los errores que impiden arrancar el detector."""
        errores = []
        if self.roi_manual and (self.roi_width <= 0 or self.roi_height <= 0):
            errores.append("ROI manual vacía: selecciona la ROI")
        if not self.roi_manual and not 0.1 <= self.roi_porcentaje <= 1.0:
            errores.append("roi_porcentaje fuera de rango (0.1–1.0)")
        if not self.tecla_dodge:
            errores.append("tecla_dodge vacía")
        return errores

    def fijar_roi(self, roi: dict) -> None:
        """Activa la ROI manual con un dict {top, left, width, height}."""
        self.roi_manual = True
        self.roi_top = roi["top"]
        self.roi_left = roi["left"]
        self.roi_width = roi["width"]
        self.roi_height = roi["height"]

    def actualizar(self, **valores) -> None:
        for clave, valor in valores.items():
            if not hasattr(self, clave):
                raise AttributeError(f"Parámetro desconocido: {clave}")
            setattr(self, clave, valor)

    def guardar(self, ruta: Path = RUTA_CONFIG) -> None:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        logging.getLogger("ffx_dodger").info(f"Configuración guardada en: {ruta}")

    @classmethod
    def cargar(cls, ruta: Path = RUTA_CONFIG) -> "Config":
        """Carga desde JSON. Las claves desconocidas se ignoran con aviso."""
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        validos = {campo.name for campo in fields(cls)}
        desconocidas = sorted(set(datos) - validos)
        if desconocidas:
            logging.getLogger("ffx_dodger").warning(
                f"Claves ignoradas en {ruta}: {', '.join(desconocidas)}"
            )
        return cls(**{k: v for k, v in datos.items() if k in validos})

    @classmethod
    def cargar_o_crear(cls, ruta: Path = RUTA_CONFIG) -> "Config":
        if Path(ruta).exists():
            return cls.cargar(ruta)
        config = cls()
        config.guardar(ruta)
        return config


# PRESETS DE UMBRALES

PRESETS_UMBRALES: dict[str, dict] = {
    # Validado en partida: 100 % de esquives
    "Validado": {"umbral_valor_hsv": 205, "area_minima_pixeles": 10,
                 "delta_minimo": 0.05, "confianza_minima": 0.60, "debounce_ms": 50},
    # Sin validar: si no detecta destellos (brillo/gamma bajos)
    "Sensible": {"umbral_valor_hsv": 190, "area_minima_pixeles": 10,
                 "delta_minimo": 0.04, "confianza_minima": 0.55, "debounce_ms": 50},
    # Sin validar: si hay falsos positivos (menús, textos blancos)
    "Estricto": {"umbral_valor_hsv": 220, "area_minima_pixeles": 50,
                 "delta_minimo": 0.08, "confianza_minima": 0.70, "debounce_ms": 300},
}


def nombre_preset(config: Config) -> str:
    """Nombre del preset que coincide con la config, o 'Personalizado'."""
    for nombre, valores in PRESETS_UMBRALES.items():
        if all(math.isclose(getattr(config, k), v) for k, v in valores.items()):
            return nombre
    return "Personalizado"
