"""Ventana principal: ROI, calibración, iniciar/detener, contadores y log.

Las ventanas OpenCV (ROI y calibración) se ejecutan en el hilo principal con la ventana
CTk oculta: cv2.imshow desde otro hilo con mainloop activo es frágil en Windows.
"""

import logging
from queue import Empty, Queue

import customtkinter as ctk

from dodger.config import RUTA_CONFIG, Config, nombre_preset
from dodger.logger import configurar_logging
from dodger.orquestador import LightningDodger
from gui.log_handler import ColaLogHandler
from herramientas.calibrar_umbrales import CalibradorUmbrales
from herramientas.selector_roi import SelectorROI

MAX_LINEAS_LOG = 300
REFRESCO_LOG_MS = 100
REFRESCO_STATS_MS = 500
COLOR_ACTIVO = "#2fa84f"
COLOR_DETENIDO = "#8a8a8a"
COLOR_ERROR = "#d9534f"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FFX Lightning Dodger")
        self.geometry("460x580")
        self.minsize(420, 480)

        self.cola_log: Queue = Queue()
        self.log = configurar_logging()
        self.log.addHandler(ColaLogHandler(self.cola_log))

        # 'cfg' y no 'config': CTk ya tiene un método config()
        self.cfg = Config.cargar_o_crear(RUTA_CONFIG)
        self.dodger = LightningDodger(self.cfg, self.log)
        self._activo = False

        self._construir()
        self._refrescar_config()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.after(REFRESCO_LOG_MS, self._volcar_log)
        self.after(REFRESCO_STATS_MS, self._tick)

    # ── Construcción ──────────────────────────────────────────────

    def _construir(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self.lbl_estado = ctk.CTkLabel(self, text="● DETENIDO", text_color=COLOR_DETENIDO,
                                       font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_estado.grid(row=0, column=0, padx=16, pady=(14, 6), sticky="w")

        marco = ctk.CTkFrame(self)
        marco.grid(row=1, column=0, padx=16, pady=6, sticky="ew")
        marco.grid_columnconfigure(0, weight=1)

        self.lbl_roi = ctk.CTkLabel(marco, anchor="w")
        self.lbl_roi.grid(row=0, column=0, padx=10, pady=(10, 4), sticky="ew")
        self.btn_roi = ctk.CTkButton(marco, text="Seleccionar ROI", width=130,
                                     command=self._seleccionar_roi)
        self.btn_roi.grid(row=0, column=1, padx=10, pady=(10, 4))

        self.lbl_umbrales = ctk.CTkLabel(marco, anchor="w")
        self.lbl_umbrales.grid(row=1, column=0, padx=10, pady=4, sticky="ew")
        self.btn_calibrar = ctk.CTkButton(marco, text="Calibrar", width=130,
                                          command=self._calibrar)
        self.btn_calibrar.grid(row=1, column=1, padx=10, pady=4)

        self.lbl_timing = ctk.CTkLabel(marco, anchor="w", text_color=COLOR_DETENIDO)
        self.lbl_timing.grid(row=2, column=0, columnspan=2, padx=10, pady=(4, 10), sticky="ew")

        self.btn_iniciar = ctk.CTkButton(self, text="▶  INICIAR", height=48,
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         fg_color=COLOR_ACTIVO, hover_color="#258a40",
                                         command=self._alternar)
        self.btn_iniciar.grid(row=2, column=0, padx=16, pady=(10, 4), sticky="ew")

        self.lbl_aviso = ctk.CTkLabel(self, text="Tras iniciar, haz clic en la ventana de FFX",
                                      text_color=COLOR_DETENIDO, font=ctk.CTkFont(size=11))
        self.lbl_aviso.grid(row=3, column=0, padx=16, sticky="w")

        self.lbl_stats = ctk.CTkLabel(self, text="", anchor="w", justify="left")
        self.lbl_stats.grid(row=4, column=0, padx=16, pady=4, sticky="ew")

        self.txt_log = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=11),
                                      wrap="none", state="disabled")
        self.txt_log.grid(row=5, column=0, padx=16, pady=(4, 16), sticky="nsew")

    def _refrescar_config(self) -> None:
        c = self.cfg
        roi = (f"{c.roi_width}x{c.roi_height} en ({c.roi_left}, {c.roi_top})"
               if c.roi_manual else f"{c.roi_porcentaje * 100:.0f}% centro (automática)")
        self.lbl_roi.configure(text=f"ROI: {roi}")
        self.lbl_umbrales.configure(
            text=f"Umbrales: {nombre_preset(c)} (HSV {c.umbral_valor_hsv}, conf {c.confianza_minima:.2f})")
        self.lbl_timing.configure(
            text=f"Tecla '{c.tecla_dodge}' · delay {c.delay_dodge_ms} ms · "
                 f"pulsación {c.duracion_pulsacion_ms} ms")

    # ── Herramientas OpenCV ───────────────────────────────────────

    def _con_ventana_oculta(self, funcion):
        self.withdraw()
        self.update()
        try:
            return funcion()
        finally:
            self.deiconify()
            self.lift()

    def _seleccionar_roi(self) -> None:
        roi = self._con_ventana_oculta(lambda: SelectorROI(self.log).ejecutar())
        if roi is not None:
            self.cfg.fijar_roi(roi)
            self.cfg.guardar(RUTA_CONFIG)
            self._refrescar_config()

    def _calibrar(self) -> None:
        umbrales = self._con_ventana_oculta(lambda: CalibradorUmbrales(self.cfg, self.log).ejecutar())
        if umbrales is not None:
            self.cfg.actualizar(**umbrales)
            self.cfg.guardar(RUTA_CONFIG)
            self._refrescar_config()

    # ── Ciclo del detector ────────────────────────────────────────

    def _alternar(self) -> None:
        if self._activo:
            self._detener()
        else:
            self._iniciar()

    def _iniciar(self) -> None:
        try:
            self.dodger.arrancar()
        except (ValueError, RuntimeError) as e:
            self.log.error(f"No se puede iniciar: {e}")
            self._pintar_estado("● ERROR", COLOR_ERROR)
            return
        self._activo = True
        self._pintar_estado("● ACTIVO", COLOR_ACTIVO)
        self.btn_iniciar.configure(text="■  DETENER", fg_color=COLOR_ERROR, hover_color="#b94541")
        for boton in (self.btn_roi, self.btn_calibrar):
            boton.configure(state="disabled")

    def _detener(self, por_error: bool = False) -> None:
        self.dodger.detener()
        self._activo = False
        if por_error:
            self._pintar_estado("● ERROR — revisa el log", COLOR_ERROR)
        else:
            self._pintar_estado("● DETENIDO", COLOR_DETENIDO)
        self.btn_iniciar.configure(text="▶  INICIAR", fg_color=COLOR_ACTIVO, hover_color="#258a40")
        for boton in (self.btn_roi, self.btn_calibrar):
            boton.configure(state="normal")

    def _pintar_estado(self, texto: str, color: str) -> None:
        self.lbl_estado.configure(text=texto, text_color=color)

    def _tick(self) -> None:
        if self._activo:
            if not self.dodger.activo:
                self.log.error("El detector se detuvo inesperadamente")
                self._detener(por_error=True)
            else:
                s = self.dodger.stats
                texto = (f"Destellos {s.destellos_detectados} · Pulsaciones {s.pulsaciones_enviadas}"
                         f" · Latencia media {s.latencia_media_ms:.0f} ms")
                r = self.dodger.rendimiento
                if r is not None and r.fps > 0:
                    texto += f"\nCPU {r.cpu_pct:.0f}% · RAM {r.ram_mb:.0f} MB · {r.fps:.1f} FPS"
                self.lbl_stats.configure(text=texto)
        self.after(REFRESCO_STATS_MS, self._tick)

    # ── Log ───────────────────────────────────────────────────────

    def _volcar_log(self) -> None:
        lineas = []
        try:
            while len(lineas) < 200:
                lineas.append(self.cola_log.get_nowait())
        except Empty:
            pass

        if lineas:
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", "\n".join(lineas) + "\n")
            total = int(self.txt_log.index("end-1c").split(".")[0])
            if total > MAX_LINEAS_LOG:
                self.txt_log.delete("1.0", f"{total - MAX_LINEAS_LOG}.0")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        self.after(REFRESCO_LOG_MS, self._volcar_log)

    def _cerrar(self) -> None:
        if self._activo:
            self.dodger.detener()
        self.destroy()


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()
