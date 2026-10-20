# -*- coding: utf-8 -*-
"""Comandos sugeridos según lo elegido (PL5: «Suggested Commands» de Plasticity).

Al elegir una cara, una arista, un perfil o un cuerpo en la vista aparece una tira corta, junto a la barra de
navegación, con los comandos que aplican; un clic ejecuta el comando con lo elegido. Es la misma lista que el
clic derecho (menú radial) muestra debajo, pero siempre visible. Se oculta si no hay nada elegido, si hay un comando
abierto o si se está dibujando un boceto. Una cara PLANA además ofrece «Extruir cara».
"""
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton

MAXIMO = 6
# Por tipo de lo elegido, en orden de prioridad (claves de `ui/comandos.CATALOGO`).
SUGERIDOS = {
    "cara_plana": ("extruir_cara",),
    "cara": ("pulsar_tirar", "desfase", "vaciado", "aspecto", "medir"),
    "arista": ("empalme_3d", "chaflan_3d", "desfase", "medir"),
    "perfil": ("extruir", "revolucion"),
    "cuerpo": ("mover_copiar", "aspecto", "material_fisico", "quitar"),
}


def tipos_de_seleccion(seleccion):
    """Tipos de lo elegido, más el pseudo-tipo «cara_plana» si alguna cara elegida es plana (tiene plano)."""
    hits = list(seleccion or [])
    tipos = {h["tipo"] for h in hits}
    if any(h.get("tipo") == "cara" and h.get("plano") is not None for h in hits):
        tipos.add("cara_plana")
    return tipos


def comandos_sugeridos(tipos, disponibles, maximo=MAXIMO):
    """Claves de los comandos que aplican a la selección de `tipos`, sin repetir y solo los que están en
    `disponibles`; con `maximo=None`, todos."""
    claves = [c for tipo, lista in SUGERIDOS.items() if tipo in tipos for c in lista]
    claves = [c for c in dict.fromkeys(claves) if c in disponibles]
    return claves if maximo is None else claves[:maximo]


class TiraSugerencias(QFrame):
    """La tira de botones. `acciones`: dict clave → QAction de la ventana; se usan su título, su ícono y su globo, y
    el clic dispara la acción."""

    def __init__(self, acciones, parent=None):
        super().__init__(parent)
        self.setObjectName("tira_sugerencias")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.acciones = acciones
        self.claves = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(4)
        self.hide()

    def mostrar_para(self, tipos):
        """Arma los botones de los `tipos` elegidos (conjunto vacío = ocultar). Devuelve las claves mostradas."""
        claves = comandos_sugeridos(tipos, self.acciones)
        if claves != self.claves:
            self.claves = claves
            lay = self.layout()
            while lay.count():
                lay.takeAt(0).widget().deleteLater()
            for clave in claves:
                a = self.acciones[clave]
                b = QToolButton(self)
                b.setText(a.property("titulo"))
                b.setIcon(a.icon())
                b.setIconSize(QSize(18, 18))
                b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                b.setToolTip(a.toolTip())
                b.clicked.connect(a.trigger)
                lay.addWidget(b)
        self.setVisible(bool(claves))
        self.adjustSize()
        return claves
