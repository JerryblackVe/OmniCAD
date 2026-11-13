# -*- coding: utf-8 -*-
"""
P-149 · Vista previa en vivo de Preferencias › Asas y superposiciones: un visor chico con un cuerpo de ejemplo y las
asas REALES de `manipuladores.py` (flecha de distancia con su caja de valor, anillo de ángulo y punto de radio), la
cara elegida, el resaltado al pasar el cursor y el cuerpo nuevo de la vista previa. Lee `estilo_asas`, así que cambia
al instante cuando la página escribe un valor; no se puede arrastrar (es solo para mirar).
"""
from types import SimpleNamespace

import numpy as np
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .. import api
from ..timeline.parametros import ANGULO, LONGITUD
from . import estilo_asas
from . import manipuladores as mp
from .comando import ContextoComando

# grupo del estilo → (identidad del asa que se resalta, sub-asa); «cajas» muestra la caja de valor de la flecha
ASA_DE_GRUPO = {"flechas": ("flecha:distancia", "flecha"), "cajas": ("flecha:distancia", "flecha"),
                "anillo": ("angulo:angulo", "asa"), "puntos": ("flecha:radio", "flecha")}


class _ComandoEjemplo:
    """Lo que el gestor pide de un comando: tres asas sobre la cara de arriba del cuerpo de ejemplo."""
    CLAVE = "ejemplo_asas"

    def __init__(self, arriba, lado):
        self.arriba, self.lado = np.asarray(arriba, float), np.asarray(lado, float)

    def manipuladores(self, ctx, valores):
        z = np.array([0.0, 0.0, 1.0])
        return [mp.Flecha("distancia", self.arriba, z),
                mp.AnilloAngulo("angulo", self.arriba, np.array([0.0, 1.0, 0.0]), z, sigue=("distancia", z, False)),
                mp.AsaRadial("radio", self.lado, np.array([1.0, 0.0, 0.0]), factor=0.5)]


class _PanelEjemplo:
    """Lo mínimo de un panel de comando que pide `GestorManipuladores`."""
    TIPOS = {"distancia": LONGITUD, "angulo": ANGULO, "radio": LONGITUD}

    def __init__(self, visor, ctx, comando):
        self.visor, self.ctx, self.comando = visor, ctx, comando
        self.campos = [SimpleNamespace(clave=k, tipo=t) for k, t in self.TIPOS.items()]
        self.valores = {"distancia": "8 mm", "angulo": "25 deg", "radio": "6 mm"}

    def set_valor(self, clave, texto):
        self.valores[clave] = texto


class VistaPreviaAsas(QWidget):
    """El visor de ejemplo. `resaltar(grupo)` pone el asa de ese grupo como si el cursor estuviera encima."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from .visor3d import Visor3D
        s = api.Sesion()
        for args in ({"length": 44, "width": 30, "height": 14, "name": "Base"},
                     {"length": 16, "width": 16, "height": 10, "x": 34, "name": "Nuevo"}):
            api.llamar(s, "create_box", args)
        self._doc = s.doc
        estado = s.doc.estado_final
        self._cids = list(estado.cuerpos)
        self.visor = Visor3D(self)
        self.visor.setMinimumSize(360, 300)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.visor)
        self.visor.set_modelo(estado)
        self.visor.vista("iso")
        self.visor.encuadrar()
        self.visor.distancia *= 0.8
        self.visor.objetivo = self.visor.objetivo + np.array([0.0, 0.0, 12.0])      # sube la mira: las asas de arriba entran
        ctx = ContextoComando(self._doc)
        self._panel = _PanelEjemplo(self.visor, ctx, _ComandoEjemplo((0, 0, 14), (22, 0, 14)))
        self.gestor = mp.GestorManipuladores(self._panel)
        self.visor.removeEventFilter(self.gestor)          # solo para mirar: el ratón no arrastra nada
        self._tris = self._triangulos_de_caras(estado)
        self.gestor.actualizar()
        self.resaltar("flechas")

    @staticmethod
    def _triangulos_de_caras(estado):
        from ..nucleo import geometria as geo
        from ..nucleo import referencias as refs
        forma = next(iter(estado.cuerpos.values())).forma
        salida = {}
        for cara in refs.subformas(forma, "cara"):
            f = refs.firma_cara(cara)
            n = f.get("normal")
            if n is not None and n[2] > 0.99:
                salida["arriba"] = geo.teselar(cara)[0]
            elif n is not None and n[1] > 0.99:
                salida["lado"] = geo.teselar(cara)[0]
        return salida

    def resaltar(self, grupo):
        """El asa de `grupo` queda como con el cursor encima (y con su caja de valor); otros grupos, sin asa."""
        ident = ASA_DE_GRUPO.get(grupo)
        self.gestor._hover = ident
        self.refrescar(grupo)

    def refrescar(self, grupo=None):
        """Rehace todo con el estilo vigente: asas, cuerpo nuevo de la vista previa, selección y resaltado."""
        v = self.visor
        estado = self._doc.estado_final
        nuevo = self._cids[-1]
        v.opacidad = {nuevo: estilo_asas.opacidad("previa")}
        v.set_modelo(estado, apariencias={nuevo: estilo_asas.rgb("previa")})
        arriba = self._tris.get("arriba")
        v.set_capa("seleccion", [("tris", arriba, None, 0.45)] if arriba is not None else None)
        lado = self._tris.get("lado")
        v._hover_ent = {"dibujo": [("tris", lado, None, 0.45)]} if lado is not None and grupo == "resaltado" else None
        self.gestor.redibujar()
        v.update()
