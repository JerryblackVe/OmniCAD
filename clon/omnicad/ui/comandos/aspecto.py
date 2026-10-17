# -*- coding: utf-8 -*-
"""
MODIFICAR › Aspecto (tecla A), como el panel de Fusion: «Aplicar a» cuerpos o caras, «En este diseño» (miniaturas con su
menú), la biblioteca con buscador, familias y pestañas, el selector rápido y el Editor de materiales.

Lo que se elige se ve en el modelo al instante (`ventana._previa_aspecto`, sin tocar el documento); «Cancelar» lo
descarta y «Aceptar» lo escribe con las mismas funciones que las herramientas `set_appearance`, `edit_appearance` y
`manage_appearance` (`timeline/aspectos_doc.py`), en UN paso de deshacer.
"""
import copy

from ... import api
from ...nucleo import geometria as geo
from ...timeline import aspectos_doc as ad
from ..aspectos_ui import PanelAspectos, RadiosAplicarA
from ..comando import Comando, ErrorComando, Personalizado, Seleccion, Texto


def _rgb_de(texto):
    texto = (texto or "").strip().lstrip("#")
    if not texto:
        return None
    try:
        if len(texto) != 6:
            raise ValueError(texto)
        return [int(texto[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    except ValueError as e:
        raise ErrorComando("El color tiene que tener el formato #rrggbb.") from e


class Aspecto(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "aspecto", "Aspecto", "aspecto", "A"
    AYUDA = ("Cambia el aspecto de cuerpos o de caras: color, aspereza, translucidez… (no cambia el material físico). "
             "Elegí uno de la biblioteca o de «En este diseño» y se ve al instante; Aceptar lo aplica, Cancelar lo descarta.")
    SIN_OP, PREVIA = True, False
    MODIFICADORES = {}

    @staticmethod
    def verificar(ctx):
        from .modificar import _con_cuerpos
        return _con_cuerpos(ctx)

    def campos(self, ctx):
        return [Personalizado("aplicar_a", "", self._radios, "cuerpos", ancho_completo=True),
                Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None,
                          visible_si=lambda v: v.get("aplicar_a") != "caras"),
                Seleccion("caras", "Caras", {"cara"}, maximo=None, visible_si=lambda v: v.get("aplicar_a") == "caras"),
                Personalizado("aspecto", "", self._panel, None, ancho_completo=True),
                Texto("hex", "Color personalizado (#rrggbb)", "", visible_si=lambda v: False)]

    # ------------------------------------------------------------ widgets
    def _radios(self, panel):
        w = RadiosAplicarA(panel.valores.get("aplicar_a") or "cuerpos")
        w.cambiado.connect(lambda valor: (self._cambiar_foco(panel, valor), panel._cambiar("aplicar_a", valor)))
        return w

    @staticmethod
    def _cambiar_foco(panel, valor):
        """Al cambiar entre cuerpos y caras, la selección activa pasa al campo que corresponde."""
        panel.valores["aplicar_a"] = valor
        panel._actualizar_visibles()
        panel._activar(next((c for c in panel.campos if c.clave == ("caras" if valor == "caras" else "cuerpos")), None))

    def _panel(self, panel):
        w = PanelAspectos(ad.lista(panel.ctx.doc))
        w.usados = {a["id"] for a in w.diseno if any(ad.usos(panel.ctx.doc, a["id"]))}
        w.cambiado.connect(lambda: self._avisar(panel, w))
        self._widget_panel = w
        return w

    @staticmethod
    def _avisar(panel, w):
        panel.valores["aspecto"] = copy.deepcopy(w.elegido)
        panel._cambiar("diseno", copy.deepcopy(w.diseno))

    # ------------------------------------------------------------ vista previa (sin tocar el documento)
    @staticmethod
    def _objetivos(v):
        """([ids de cuerpos], [(id de cuerpo, referencia de cara)]) de lo elegido según «Aplicar a»."""
        if v.get("aplicar_a") == "caras":
            return [], [(h["ref"]["cuerpo"], h["ref"]) for h in v.get("caras") or []]
        return list(dict.fromkeys(h["ref"]["cuerpo"] for h in v.get("cuerpos") or [])), []

    def _previa(self, v, doc):
        previa = {"cuerpos": {}, "caras": []}
        originales = {a["id"]: a for a in ad.lista(doc)}
        for a in v.get("diseno") or []:           # un aspecto del diseño editado: quienes lo usan ya lo muestran
            o = originales.get(a["id"])
            if o is not None and o != a:
                cuerpos, caras = ad.usos(doc, a["id"])
                previa["cuerpos"].update({c: a["color"] for c in cuerpos})
                previa["caras"] += [(c, r, a["color"]) for c, r in caras]
        rgb = _rgb_de(v.get("hex")) or (v["aspecto"]["color"] if v.get("aspecto") else None)
        if rgb is not None:
            cuerpos, caras = self._objetivos(v)
            previa["cuerpos"].update({c: rgb for c in cuerpos})
            previa["caras"] += [(c, r, rgb) for c, r in caras]
        return previa

    def mostrar(self, v, ctx):
        ventana = ctx.ventana
        if ventana is None:
            return
        ventana._previa_aspecto = self._previa(v, ctx.doc)
        ventana._refrescar_visibilidad()

    def al_cerrar(self, ctx):
        ventana = ctx.ventana
        if ventana is not None and ventana._previa_aspecto:
            ventana._previa_aspecto = {}
            ventana._refrescar_visibilidad()

    # ------------------------------------------------------------ Aceptar
    def aplicar(self, v, ctx):
        doc = ctx.doc
        cuerpos, caras = self._objetivos(v)
        rgb = _rgb_de(v.get("hex"))
        elegido = v.get("aspecto")
        diseno = v.get("diseno")
        hay_cambios = diseno is not None and diseno != ad.lista(doc)
        if (rgb is not None or elegido is not None) and not (cuerpos or caras):
            raise ErrorComando("Seleccioná las caras." if v.get("aplicar_a") == "caras" else "Seleccioná los cuerpos.")
        if rgb is None and elegido is None and not hay_cambios:
            raise ErrorComando("Elegí un aspecto de la biblioteca o de «En este diseño».")
        with api.Sesion(doc).transaccion():          # un solo paso de deshacer para todo lo que hace Aceptar
            try:
                ad.aplicar_panel(doc, diseno if hay_cambios else None, elegido, cuerpos, caras, rgb)
            except geo.ErrorGeometria as e:
                raise ErrorComando(str(e)) from e

