"""FFX Lightning Dodger — CLI. Para la interfaz gráfica: python app_gui.py"""

import argparse
import logging
import sys
import time
from pathlib import Path

from dodger.config import RUTA_CONFIG, Config
from dodger.logger import configurar_logging
from dodger.orquestador import LightningDodger


def _preguntar(texto: str) -> bool:
    return input(f"\n{texto} (s/n): ").strip().lower() == "s"


def _seleccionar_roi(config: Config, ruta: Path, log: logging.Logger) -> bool:
    from herramientas.selector_roi import SelectorROI
    roi = SelectorROI(log).ejecutar()
    if roi is None:
        return False
    config.fijar_roi(roi)
    config.guardar(ruta)
    return True


def _calibrar(config: Config, ruta: Path, log: logging.Logger) -> None:
    from herramientas.calibrar_umbrales import CalibradorUmbrales
    umbrales = CalibradorUmbrales(config, log).ejecutar()
    if umbrales is not None:
        config.actualizar(**umbrales)
        config.guardar(ruta)


def _ejecutar_detector(config: Config, log: logging.Logger) -> None:
    dodger = LightningDodger(config, log)
    dodger.arrancar()
    log.info("Ctrl+C para detener")
    try:
        while dodger.activo:
            time.sleep(0.5)
    except KeyboardInterrupt:
        log.info("🛑 Señal de parada recibida — cerrando...")
    dodger.detener()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FFX Lightning Dodger — esquiva automática de rayos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  python main.py                    # Detector con config.json\n"
            "  python main.py --seleccionar-roi  # Definir zona de captura\n"
            "  python main.py --calibrar         # Calibración de umbrales (presets 1/2/3)\n"
            "  python main.py --config otra.json # Config alternativa\n"
        ),
    )
    parser.add_argument("--config", type=Path, default=RUTA_CONFIG,
                        help=f"Ruta de la config (default: {RUTA_CONFIG.name})")
    parser.add_argument("--seleccionar-roi", action="store_true",
                        help="Selector visual de la zona de captura")
    parser.add_argument("--calibrar", action="store_true",
                        help="Calibración visual de umbrales")
    parser.add_argument("--tecla", type=str, default=None,
                        help="Tecla de dodge solo para esta ejecución (default: la de la config, 'c')")
    parser.add_argument("--debug", action="store_true", help="Logging nivel DEBUG")
    args = parser.parse_args()

    log = configurar_logging(logging.DEBUG if args.debug else logging.INFO)

    if args.config.exists():
        config = Config.cargar(args.config)
    elif args.config == RUTA_CONFIG:
        config = Config.cargar_o_crear(args.config)
    else:
        sys.exit(f"No existe la config: {args.config}")

    if args.seleccionar_roi:
        if not _seleccionar_roi(config, args.config, log):
            print("No se seleccionó ROI. Saliendo.")
            return
        if _preguntar("¿Continuar con calibración de umbrales?"):
            _calibrar(config, args.config, log)
        if not _preguntar("¿Iniciar detector ahora?"):
            return
    elif args.calibrar:
        _calibrar(config, args.config, log)
        if not _preguntar("¿Iniciar detector ahora?"):
            return

    # Overrides solo para esta ejecución (no se guardan)
    if args.tecla:
        config.tecla_dodge = args.tecla

    errores = config.validar()
    if errores:
        sys.exit("Config inválida: " + "; ".join(errores))
    _ejecutar_detector(config, log)


if __name__ == "__main__":
    main()
