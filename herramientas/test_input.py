"""Prueba de input: envía UNA pulsación de la tecla de esquive con pynput.

Uso:
    python -m herramientas.test_input
Tienes 5 s para poner el foco en la ventana objetivo (Notepad o FFX).
SendInput por scancode y keybd_event se descartaron: FFX no los acepta.
"""

import time

from pynput.keyboard import Controller

from dodger.config import RUTA_CONFIG, Config

CUENTA_ATRAS_S = 5


def main() -> None:
    config = Config.cargar_o_crear(RUTA_CONFIG)
    tecla = config.tecla_dodge
    print(f"Pon el foco en la ventana objetivo. Se pulsará '{tecla}' "
          f"durante {config.duracion_pulsacion_ms} ms.")
    for i in range(CUENTA_ATRAS_S, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    teclado = Controller()
    teclado.press(tecla)
    time.sleep(config.duracion_pulsacion_ms / 1000.0)
    teclado.release(tecla)
    print("✓ Pulsación enviada")


if __name__ == "__main__":
    main()
