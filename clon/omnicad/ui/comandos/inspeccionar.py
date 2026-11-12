# -*- coding: utf-8 -*-
"""Comandos de INSPECCIONAR: Medir, Interferencia y los análisis que quedan guardados en el navegador (sección, cebra,
mapa de entorno, desmoldeo, curvatura, peine, isocurva, accesibilidad, radio mínimo y centro de masa)."""
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QColorDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
                               QMessageBox, QProgressDialog, QPushButton, QTableWidget, QTableWidgetItem, QToolButton,
                               QVBoxLayout, QWidget)

from ...nucleo import analisis as an
from ...nucleo import geometria as geo
from ...timeline import entidades as ent
from ...timeline.ops_chapa import cuerpos_del_modelo
from ...timeline.analisis_vista import COLOR_SECCION, _segmentos, centro_de_masa
from ...timeline.parametros import ANGULO, ErrorExpresion, TEXTO, unidad_de
from .. import analisis_vista, formato
from ..formulario import armar_cabecera
from ..iconos import icono
from .comunes import campos_cebra, campos_iso, campos_mapa, params_cebra, params_iso, params_mapa
from ..comando import (Botones, Casilla, Comando, Deslizador, DosTopes, Entero, ErrorComando, Expresion, Info, Opciones,
                       Personalizado, Seleccion, hit_desde_ref, hits, ref1)
from . import registrar

GEOMETRIA = {"cara", "arista", "vertice", "punto", "curva_boceto", "perfil", "centro_masa"}
FILTROS_MEDIR = {"geometria": ("Filtra la selección en caras, aristas o vértices.", "ec_cara"),
                 "cuerpos": ("Filtra la selección en cuerpos.", "cuerpo"),
                 "componentes": ("Filtra la selección en componentes.", "componente")}
PRECISIONES = {d: f"0.{'123456789'[:d]}" if d else "0" for d in range(9)}
SECUNDARIAS = {"ninguno": "Ninguno", "cm": "cm", "m": "m", "pulg": "pulg.", "ft": "ft"}
DELTAS = {"ninguno": ("Ninguno", "ana_ninguno"), "comp1": ("Sistema del componente 1", "componente"),
          "comp2": ("Sistema del componente 2", "cuerpo"), "global": ("Sistema global", "scu")}
_COLOR_RESALTE = (1.0, 0.85, 0.2)


def _entrada(hit, estado):
    """Lo que entiende analisis.medir: forma OCC o punto."""
    if hit["ref"].get("tipo") == "centro_masa":
        return np.asarray(hit["punto"], float)
    e = ent.resolver(hit["ref"], estado)
    if e.forma is not None:
        return e.forma
    if e.punto is not None:
        return np.asarray(e.punto, float)
    raise ErrorComando("Esa selección no se puede medir.")


def _n(x, dec=3):
    return formato.numero(float(x), miles=True) if hasattr(formato, "numero") else f"{x:.{dec}f}"


def _mm(x, potencia=1):
    """Un valor del modelo (mm, mm², mm³) con la unidad de longitud del documento: «1.575 in»."""
    return f"{_n(formato.longitud(float(x), potencia))} {formato.sufijo(potencia)}"


def _vec(v):
    return "(" + "; ".join(_n(formato.longitud(float(c))) for c in v) + ")"


class _Valor(QPushButton):
    """Un valor de Resultados: pasar por encima lo resalta en el lienzo y el clic lo copia."""
    sobre = Signal(bool)

    def enterEvent(self, e):
        self.sobre.emit(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.sobre.emit(False)
        super().leaveEvent(e)


class _FilaResultado:
    def __init__(self, nombre, texto, copiar, resalte, tabla):
        self.nombre, self.texto, self.copiar, self.resalte = QLabel(nombre), texto, copiar, resalte
        self.valor = _Valor(texto, flat=True, toolTip="Clic: copiar el valor")
        self.valor.setStyleSheet("text-align: left; padding: 0;")
        self.valor.setFocusPolicy(Qt.NoFocus)
        self.valor.clicked.connect(lambda: QApplication.clipboard().setText(self.copiar))
        self.valor.sobre.connect(lambda dentro: tabla.resaltar.emit(self.resalte if dentro else None))


class _TablaResultados(QWidget):
    """Secciones Selección 1, Selección 2 y Resultados de Medir: cada valor resalta su medida y se copia con un clic."""
    resaltar = Signal(object)                    # primitivas de `visor.set_capa`, o None

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(300)
        self.filas, self._titulos = [], []
        self.marco = QVBoxLayout(self)
        self.marco.setContentsMargins(0, 6, 0, 0)
        self.marco.setSpacing(2)
        self.marco.addStretch(1)

    def titulos(self):
        return " · ".join(t.text() for t in self._titulos)

    def poner(self, secciones):
        """`secciones`: [(título, [(nombre, texto, texto a copiar, resalte)])]."""
        while self.marco.count() > 1:
            w = self.marco.takeAt(0).widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.filas, self._titulos = [], []
        i = 0
        for titulo, filas in secciones:
            rotulo = QLabel(titulo, objectName="grupo_cmd")
            self._titulos.append(rotulo)
            self.marco.insertWidget(i, rotulo)
            i += 1
            for nombre, texto, copiar, resalte in filas:
                f = _FilaResultado(nombre, texto, copiar, resalte, self)
                fila = QWidget()
                h = QHBoxLayout(fila)
                h.setContentsMargins(0, 0, 0, 0)
                f.nombre.setFixedWidth(120)
                h.addWidget(f.nombre)
                h.addWidget(f.valor, 1)
                self.marco.insertWidget(i, fila)
                i += 1
                self.filas.append(f)


class Medir(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "medir", "Medir", "medir", "I"
    AYUDA = "Mide distancias, ángulos, longitudes, áreas y volúmenes de lo que elijas."
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"
    MODIFICADORES = {"Ctrl": "forzar al punto", "Mayús": "ocultar los puntos"}

    def campos(self, ctx):
        prefs = getattr(ctx.ventana, "prefs", None)
        guardada = prefs["medir/secundarias"] if prefs is not None else "ninguno"
        return [Seleccion("a", "Selección 1", GEOMETRIA, oculta=True), Seleccion("b", "Selección 2", GEOMETRIA, minimo=0, oculta=True),
                Botones("filtro", "Filtro de selección", FILTROS_MEDIR),
                Opciones("precision", "Precisión", PRECISIONES, 3),
                Opciones("secundarias", "Unidades secundarias", SECUNDARIAS, guardada if guardada in SECUNDARIAS else "ninguno"),
                Personalizado("borrar", "Borrar selección", self._boton_borrar),
                Casilla("forzado", "Mostrar puntos de forzado", visible_si=lambda v: v.get("filtro") == "geometria",
                        ayuda="Ctrl fija al punto; Mayús los oculta."),
                Casilla("centro", "Centro a centro", ayuda="Mide entre los centros de dos círculos, arcos o cilindros."),
                Botones("delta", "XYZ Delta", DELTAS, visible_si=lambda v: self._dos_puntos(v)),
                Personalizado("resultados", "", self._tabla, ancho_completo=True)]

    @staticmethod
    def _dos_puntos(v):
        tipos = {h.get("tipo") for h in (v.get("a") or []) + (v.get("b") or [])}
        return bool(v.get("a")) and bool(v.get("b")) and tipos <= {"vertice", "punto", "punto_boceto", "forzado", "centro_masa"}

    def _boton_borrar(self, panel):
        b = QToolButton(toolTip="Vacía la selección")
        b.setIcon(icono("deshacer"))
        b.clicked.connect(lambda: self._borrar(panel))
        return b

    def _tabla(self, panel):
        t = _TablaResultados()
        t.resaltar.connect(lambda p: panel.visor.set_capa("medida_resalte", p))
        return t

    @staticmethod
    def _borrar(panel):
        panel.valores["a"], panel.valores["b"] = [], []
        panel._activar(panel._por_clave["a"])
        panel._refrescar_seleccion()
        panel._actualizar_visibles()
        panel._programar()

    def preparar_panel(self, panel):
        self._panel = panel
        panel.boton_cancelar.hide()              # Fusion: Medir solo tiene Cerrar
        self._aplicar_filtro(panel)

    def _aplicar_filtro(self, panel):
        v = panel.valores
        if v["filtro"] == "geometria":
            filtros = GEOMETRIA | ({"forzado"} if v.get("forzado") else set())
        else:
            filtros = {"cuerpo"}
        panel._por_clave["a"].filtros = panel._por_clave["b"].filtros = set(filtros)
        panel._activar(panel.activa)

    def al_cambiar(self, panel, clave):
        if clave in ("filtro", "forzado"):
            self._aplicar_filtro(panel)
        elif clave == "secundarias" and getattr(panel.ctx.ventana, "prefs", None) is not None:
            panel.ctx.ventana.prefs["medir/secundarias"] = panel.valores["secundarias"]

    def ajustar_hit(self, campo, hit, ctx, visor):
        panel = getattr(self, "_panel", None)
        self._reiniciar = campo.clave == "b" and panel is not None and bool(panel.valores.get("b"))
        if panel is None or panel.valores.get("filtro") != "componentes" or hit.get("tipo") != "cuerpo":
            return None
        comp = ctx.estado.cuerpos[hit["ref"]["cuerpo"]].componente
        return hit_desde_ref({"tipo": "componente", "componente": comp}, ctx.estado) if comp else None

    def al_elegir(self, panel, clave):
        """El tercer clic empieza una medida nueva: lo elegido pasa a ser la Selección 1."""
        if clave == "b" and getattr(self, "_reiniciar", False) and panel.valores.get("b"):
            panel.valores["a"], panel.valores["b"] = panel.valores["b"], []
            panel._activar(panel._por_clave["b"])
            panel._refrescar_seleccion()
            panel._actualizar_visibles()

    def _datos(self, v, ctx):
        if not v.get("a"):
            return None
        a = _entrada(v["a"][0], ctx.estado)
        b = _entrada(v["b"][0], ctx.estado) if v.get("b") else None
        return an.medir(a, b, centro_a_centro=bool(v.get("centro")))

    # ------------------------------------------------------------ texto de los valores
    @staticmethod
    def _valor(v, x, potencia=1):
        """(texto, lo que se copia) de un valor del modelo: la unidad del documento, y la secundaria entre paréntesis."""
        d = int(v.get("precision", 3))
        principal = f"{formato.longitud(float(x), potencia):.{d}f}"
        return f"{principal} {formato.sufijo(potencia)}{an.texto_secundario(x, potencia, d, v.get('secundarias', 'ninguno'))}", principal

    def _filas_entidad(self, info, v, dibujo):
        """Filas de una selección, según la tabla de `Measure reference`."""
        filas = []

        def fila(nombre, x, potencia=1):
            filas.append((nombre, *self._valor(v, x, potencia), dibujo))

        if info.get("posicion") is not None:
            for nombre, c in zip(("Posición X", "Posición Y", "Posición Z"), info["posicion"], strict=True):
                fila(nombre, c)
        for clave, nombre in (("largo", "Longitud"), ("radio", "Radio"), ("diametro", "Diámetro")):
            if info.get(clave) is not None:
                fila(nombre, info[clave])
        if info.get("area") is not None:
            fila("Área", info["area"], 2)
        if info.get("perimetro") is not None:
            fila("Largo del bucle", info["perimetro"])
        if info.get("volumen") is not None:
            fila("Volumen", info["volumen"], 3)
        if info.get("centro") is not None and info.get("superficie") != "cilindro":
            for nombre, c in zip(("Centro X", "Centro Y", "Centro Z"), info["centro"], strict=True):
                fila(nombre, c)
        return filas

    def _matriz(self, hit, ctx):
        """Rotación del sistema de coordenadas del componente de lo elegido (identidad si no está en uno o se juntó con otra)."""
        ref = hit["ref"]
        comp = ref.get("componente")
        if comp is None and ref.get("cuerpo") in ctx.estado.cuerpos:
            comp = ctx.estado.cuerpos[ref["cuerpo"]].componente
        m = ctx.estado.componentes.get(comp, {}).get("matriz")
        return np.identity(3) if m is None else np.asarray(m, float)[:3, :3]

    def _deltas(self, r, v, ctx):
        """[(eje, valor, inicio, fin)] de XYZ Delta en el sistema elegido; [] si está en Ninguno."""
        modo = v.get("delta", "ninguno")
        if modo == "ninguno" or not self._dos_puntos(v) or r is None or r.get("delta") is None:
            return []
        rot = np.identity(3) if modo == "global" else self._matriz(v["a" if modo == "comp1" else "b"][0], ctx)
        local = rot.T @ np.asarray(r["delta"], float)
        salida, p = [], np.asarray(r["punto_a"], float)
        for i, eje in enumerate("XYZ"):
            q = p + rot[:, i] * local[i]
            salida.append((eje, float(local[i]), p, q))
            p = q
        return salida

    def _secciones(self, v, ctx):
        """Lo que muestra Resultados: [(título, filas)]. Vacío sin selección."""
        r = self._datos(v, ctx)
        if r is None:
            return []
        linea = lambda pa, pb: [("lineas", np.array([pa, pb], float), _COLOR_RESALTE, 4.0)]  # noqa: E731
        secciones = []
        for clave, titulo in (("a", "Selección 1"), ("b", "Selección 2")):
            if isinstance(r.get(clave), dict):
                hit = v[clave][0]
                from ..formulario import describir_ref
                dibujo = [(p[0], p[1], _COLOR_RESALTE, *p[3:]) for p in hit.get("dibujo") or []]
                secciones.append((f"{titulo} · {describir_ref(hit['ref'], ctx)}", self._filas_entidad(r[clave], v, dibujo)))
        filas = []
        if "distancia" in r:
            lado = linea(r["punto_a"], r["punto_b"])
            filas.append(("Distancia", *self._valor(v, r["distancia"]), lado))
            for eje, valor, p, q in self._deltas(r, v, ctx):
                filas.append((f"{eje} Delta", *self._valor(v, valor), linea(p, q)))
            cc = r.get("centro_a_centro")
            if cc is not None:
                lado = linea(cc["punto_a"], cc["punto_b"])
                filas += [("Centro a centro", *self._valor(v, cc["distancia"]), lado),
                          ("Mínima", *self._valor(v, cc["minima"]), lado), ("Máxima", *self._valor(v, cc["maxima"]), lado)]
        if r.get("angulo") is not None:
            d = int(v.get("precision", 3))
            filas.append(("Ángulo", f"{r['angulo']:.{d}f} deg", f"{r['angulo']:.{d}f}", linea(r["punto_a"], r["punto_b"])))
        if filas:
            secciones.append(("Resultados", filas))
        return secciones

    def construir(self, v, ctx):
        return None

    # ------------------------------------------------------------ cota guía en la vista (como Fusion)
    @staticmethod
    def _tam_flecha(visor, punto):
        """Largo de las flechas en mm para que se vean de ~12 px en pantalla."""
        from ..manipuladores import mm_por_px
        try:
            return float(mm_por_px(visor, punto)) * 12.0
        except Exception:  # noqa: BLE001 — sin cámara (pruebas), un tamaño fijo
            return 2.0

    def cota(self, r, v, ctx, visor=None, color=analisis_vista.COLOR_COTA):
        """Cota guía de un resultado de `an.medir`: {"capas", "etiquetas"} (ver `analisis_vista.cota_guia`).
        Dos selecciones: la distancia mínima entre los puntos más cercanos (y el ángulo, si lo hay). Una sola:
        largo de una arista recta, Ø de lo circular, área de una cara, posición de un punto o volumen."""
        vacio = {"capas": [], "etiquetas": []}
        if not r:
            return vacio
        vista = np.asarray(visor.R[2], float) if visor is not None and hasattr(visor, "R") else None

        def tam(p):
            return self._tam_flecha(visor, p) if visor is not None else 2.0
        if r.get("punto_a") is not None and r.get("punto_b") is not None:
            pa, pb = np.asarray(r["punto_a"], float), np.asarray(r["punto_b"], float)
            texto = self._valor(v, r["distancia"])[0]
            if r.get("angulo") is not None and r["angulo"] > 1e-6:
                texto += f" · {_n(r['angulo'])}°"
            c = analisis_vista.cota_guia(pa, pb, texto, tam((pa + pb) / 2), vista, color)
            for eje, valor, p, q in self._deltas(r, v, ctx):         # XYZ Delta también en el lienzo
                c["capas"].append(("lineas", np.array([p, q]), color, 1.5))
                c["etiquetas"].append(((p + q) / 2, f"{eje} {self._valor(v, valor)[0]}"))
            return c
        info = r.get("a") or {}
        hit = (v.get("a") or [None])[0]
        if info.get("centro") is not None and info.get("radio"):
            centro = np.asarray(info["centro"], float)
            return analisis_vista.cota_diametro(centro, info["radio"], info.get("eje") or info.get("normal"),
                                                f"Ø {self._valor(v, info['diametro'])[0]}", tam(centro), vista, color)
        if info.get("tipo") == "arista":
            poli = np.asarray(geo.polilinea_arista(_entrada(hit, ctx.estado)), float)
            if info.get("direccion") is not None:          # recta: cota de punta a punta
                return analisis_vista.cota_guia(poli[0], poli[-1], self._valor(v, info["largo"])[0], tam(poli[0]),
                                                vista, color)
            from ..visor3d import _segmentos
            return {"capas": [("lineas", _segmentos([poli]), color, 2.5)],
                    "etiquetas": [(poli[len(poli) // 2], self._valor(v, info["largo"])[0])]}
        if info.get("posicion") is not None:
            p = np.asarray(info["posicion"], float)
            return {"capas": [("puntos", np.array([p]), color, 9)], "etiquetas": [(p, _vec(p))]}
        if info.get("tipo") == "cara":
            if hit and hit.get("punto") is not None:
                p = np.asarray(hit["punto"], float)        # donde se hizo clic sobre la cara
            else:
                from ..manipuladores import centroide
                p = centroide(_entrada(hit, ctx.estado))
            return {"capas": [], "etiquetas": [(p, self._valor(v, info["area"], 2)[0])]}
        if info.get("volumen") is not None and info.get("centro_masa") is not None:
            p = np.asarray(info["centro_masa"], float)
            return {"capas": [("puntos", np.array([p]), color, 8)], "etiquetas": [(p, self._valor(v, info["volumen"], 3)[0])]}
        return vacio

    def mostrar(self, v, ctx):
        self._v, self._ctx = v, ctx
        visor = ctx.ventana.visor if ctx.ventana else None
        panel = getattr(self, "_panel", None)
        if panel is not None:
            panel.widgets["resultados"].poner(self._secciones(v, ctx))
        if visor is None:
            return
        if not getattr(self, "_escuchando", False):        # valor en vivo de lo que está bajo el cursor
            visor.entidad_sobre.connect(self._sobre)
            self._escuchando = True
        self._limpiar(visor, "medida_previa")
        self._limpiar(visor, "medida")
        c = self.cota(self._datos(v, ctx), v, ctx, visor)
        visor.set_capa("medida", c["capas"])
        visor.set_etiquetas("medida", c["etiquetas"])

    def _sobre(self, hit):
        """Con la primera selección hecha, lo que está bajo el cursor se mide en vivo (cota celeste con «≈»),
        antes de hacer el segundo clic."""
        ctx, v = getattr(self, "_ctx", None), getattr(self, "_v", None)
        visor = ctx.ventana.visor if ctx is not None and ctx.ventana else None
        if visor is None:
            return
        self._limpiar(visor, "medida_previa")
        if hit is None or not v or not v.get("a") or v.get("b") or hit.get("ref") == v["a"][0].get("ref"):
            return
        try:
            r = an.medir(_entrada(v["a"][0], ctx.estado), _entrada(hit, ctx.estado),
                         centro_a_centro=bool(v.get("centro")))
            c = self.cota(r, {**v, "a": v["a"], "b": [hit]}, ctx, visor, analisis_vista.COLOR_COTA_PREVIA)
        except Exception:  # noqa: BLE001 — lo que no se puede medir simplemente no muestra la cota previa
            return
        visor.set_capa("medida_previa", c["capas"])
        visor.set_etiquetas("medida_previa", [(p, f"≈ {t}") for p, t in c["etiquetas"]])

    @staticmethod
    def _limpiar(visor, capa):
        visor.set_capa(capa, None)
        visor.set_etiquetas(capa, None)

    def aplicar(self, v, ctx):
        pass

    def al_cerrar(self, ctx):
        self._panel = None
        if ctx.ventana:
            visor = ctx.ventana.visor
            if getattr(self, "_escuchando", False):
                try:
                    visor.entidad_sobre.disconnect(self._sobre)
                except (RuntimeError, TypeError):
                    pass
                self._escuchando = False
            for capa in ("medida", "medida_previa", "medida_resalte"):
                self._limpiar(visor, capa)


_COLORES_GRUPO = ((0.30, 0.75, 0.35), (0.90, 0.35, 0.35), (0.35, 0.40, 0.90), (0.95, 0.70, 0.20), (0.70, 0.40, 0.85), (0.25, 0.75, 0.75))
_COLUMNAS = ["Grupos", "Quitar volumen", "Volumen", "Objetivo (cortar)", "⇄", "Herramienta (conservar)"]


class _Numero(QTableWidgetItem):
    """Celda que ordena por su número (UserRole), no por el texto."""

    def __lt__(self, otra):
        return float(self.data(Qt.UserRole)) < float(otra.data(Qt.UserRole))


class _ResultadosInterferencia(QFrame):
    """Resultados de interferencia: tabla ordenable, Mostrar todas las interferencias y Quitar volumen (Aceptar corta el
    volumen del Objetivo, con un paso en el timeline; OmniCAD no tiene modo directo, así que queda a elección)."""

    def __init__(self, comando, panel, grupos):
        super().__init__(panel.parent() or panel.visor)
        self.comando, self.panel, self.grupos = comando, panel, grupos
        self.setObjectName("panel_comando")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(min(760, max(self.parent().width() - 24, 420)))
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        cab, ico, titulo = armar_cabecera(self, panel.cancelar)
        ico.setPixmap(icono("interferencia").pixmap(18, 18))
        titulo.setText("RESULTADOS DE INTERFERENCIA")
        v.addWidget(cab)
        self.tabla = t = QTableWidget(len(grupos), len(_COLUMNAS))
        t.setHorizontalHeaderLabels(_COLUMNAS)
        t.verticalHeader().hide()
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        t.setFixedHeight(min(40 + 30 * len(grupos), 240))
        for i, g in enumerate(grupos):
            self._llenar(i, g)
        t.setSortingEnabled(True)
        t.itemSelectionChanged.connect(comando.pintar_grupos)
        v.addWidget(t)
        pie = QHBoxLayout()
        pie.setContentsMargins(10, 4, 10, 8)
        self.mostrar_todas = QCheckBox("Mostrar todas las interferencias", checked=True)
        self.mostrar_todas.toggled.connect(comando.pintar_grupos)
        pie.addWidget(self.mostrar_todas)
        pie.addStretch(1)
        self.boton_ok = QPushButton("Aceptar", objectName="boton_primario")
        self.boton_ok.clicked.connect(self._aceptar)
        boton_cancelar = QPushButton("Cancelar")
        boton_cancelar.clicked.connect(self.close)
        pie.addWidget(self.boton_ok)
        pie.addWidget(boton_cancelar)
        v.addLayout(pie)
        self.adjustSize()
        self.move((self.parent().width() - self.width()) // 2, max(12, self.parent().height() - self.height() - 48))
        self.show()
        self.raise_()

    def _llenar(self, fila, g):
        t = self.tabla
        coincidente = g["coincidente"]

        def celda(texto, columna, item=None):
            item = item or QTableWidgetItem(texto)
            item.setText(texto)
            if coincidente:                                    # como en Fusion: los nombres van en gris claro
                item.setForeground(QColor(150, 150, 150))
            t.setItem(fila, columna, item)
            return item

        grupo = celda(str(fila + 1), 0, _Numero())
        grupo.setData(Qt.UserRole, fila)
        quitar = celda("", 1, QTableWidgetItem())
        quitar.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | (Qt.NoItemFlags if coincidente else Qt.ItemIsUserCheckable))
        if not coincidente:
            quitar.setCheckState(Qt.Unchecked)
        volumen = celda(_mm(g["volumen"], 3), 2, _Numero())
        volumen.setData(Qt.UserRole, float(g["volumen"]))
        celda(g["nombre_a"], 3)
        celda(g["nombre_b"], 5)
        cambiar = QToolButton(text="⇄", toolTip="Cambiar Objetivo y Herramienta", enabled=not coincidente)
        cambiar.clicked.connect(lambda: self._cambiar(g))
        t.setCellWidget(fila, 4, cambiar)

    def _fila_de(self, g):
        i = self.grupos.index(g)
        return next(f for f in range(self.tabla.rowCount()) if self.tabla.item(f, 0).data(Qt.UserRole) == i)

    def _cambiar(self, g):
        g["a"], g["b"], g["nombre_a"], g["nombre_b"] = g["b"], g["a"], g["nombre_b"], g["nombre_a"]
        f = self._fila_de(g)
        self.tabla.item(f, 3).setText(g["nombre_a"])
        self.tabla.item(f, 5).setText(g["nombre_b"])

    def elegidos(self):
        """Los grupos a dibujar: todos con Mostrar todas; si no, el de la fila elegida."""
        if self.mostrar_todas.isChecked():
            return list(self.grupos)
        return [self.grupos[self.tabla.item(i.row(), 0).data(Qt.UserRole)] for i in self.tabla.selectionModel().selectedRows()]

    def _aceptar(self):
        from ...api import llamar
        from ...api.sesion import Sesion
        pares = [{"target": g["a"], "tool": g["b"]} for g in self.grupos
                 if self.tabla.item(self._fila_de(g), 1).checkState() == Qt.Checked]
        ctx = self.panel.ctx
        if pares:
            r = llamar(Sesion(ctx.doc), "remove_interference", {"pairs": pares})
            if not r["ok"]:
                self.panel._mostrar(r["mensaje"])
                return
        self.panel.aceptar()

    def closeEvent(self, e):
        self.comando.dialogo = None
        self.comando.pintar_grupos()
        super().closeEvent(e)


class Interferencia(Comando):
    CLAVE, TITULO, ICONO = "interferencia", "Interferencia", "interferencia"
    AYUDA = "Busca volúmenes donde los cuerpos se superponen."
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"
    dialogo = None

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Cuerpos o componentes", {"cuerpo", "componente"}, minimo=0, maximo=None,
                          ayuda="Sin selección: todos los cuerpos."),
                Casilla("coincidentes", "Incluir caras coincidentes"),
                Personalizado("calcular", "Calcular", self._boton_calcular)]

    def _boton_calcular(self, panel):
        b = QPushButton("Calcular")
        b.setIcon(icono("interferencia"))
        b.clicked.connect(lambda: self.calcular(panel))
        return b

    def _cuerpos(self, v, ctx):
        """{id: forma} de lo elegido: cuerpos y los de cada componente; sin nada, todos los sólidos del modelo."""
        ids = []
        for h in v.get("cuerpos") or []:
            if h["ref"].get("tipo") == "componente":
                ids += [c for c, cu in ctx.estado.cuerpos.items() if cu.componente == h["ref"]["componente"]]
            else:
                ids.append(h["ref"]["cuerpo"])
        ids = ids or [c.id for c in cuerpos_del_modelo(ctx.estado)]
        return {c: ctx.estado.cuerpos[c].forma for c in dict.fromkeys(ids) if c in ctx.estado.cuerpos
                and getattr(ctx.estado.cuerpos[c], "tipo", "solido") == "solido"}

    def _grupos(self, v, ctx):
        """Pares de `an.interferencias` con el nombre como en Fusion: el del componente, o «Componente - Cuerpo» dentro de uno."""
        estado = ctx.estado
        res = an.interferencias(self._cuerpos(v, ctx), caras_coincidentes=bool(v.get("coincidentes")))

        def nombre(c, otro):
            if not c.componente:
                return c.nombre
            comp = estado.componentes.get(c.componente, {}).get("nombre", c.componente)
            return comp if c.componente != otro.componente else f"{comp} - {c.nombre}"
        for r in res:
            ca, cb = estado.cuerpos[r["a"]], estado.cuerpos[r["b"]]
            r["nombre_a"], r["nombre_b"] = nombre(ca, cb), nombre(cb, ca)
        return res

    def calcular(self, panel):
        self._panel = panel
        grupos = self._grupos(panel.valores, panel.ctx)
        if self.dialogo is not None:
            self.dialogo.close()
        if not grupos:
            QMessageBox.information(panel, "Interferencia", "No se detectaron interferencias.")
            return
        self.dialogo = _ResultadosInterferencia(self, panel, grupos)
        self.pintar_grupos()

    def pintar_grupos(self):
        """Grupos con colores que rotan; las caras coincidentes solo con su contorno."""
        ctx = getattr(self, "_panel", None) and self._panel.ctx
        if not ctx or ctx.ventana is None:
            return
        prims = []
        for g in (self.dialogo.elegidos() if self.dialogo is not None else []):
            color = _COLORES_GRUPO[self.dialogo.grupos.index(g) % len(_COLORES_GRUPO)]
            if geo.esta_vacia(g["forma"]):
                continue
            if g["coincidente"]:
                prims.append(("lineas", _segmentos(geo.polilineas_aristas(g["forma"])), color, 2.0))
            else:
                prims.append(("tris", geo.teselar(g["forma"])[0], color, 0.7))
        ctx.ventana.visor.set_capa("medida", prims)

    def construir(self, v, ctx):
        return None

    def al_cerrar(self, ctx):
        if self.dialogo is not None:
            d, self.dialogo = self.dialogo, None
            d.deleteLater()
        if ctx.ventana:
            ctx.ventana.visor.set_capa("medida", None)


class BuscarSimilares(Comando):
    CLAVE, TITULO, ICONO = "buscar_similares", "Buscar componentes similares", "buscar_similares"
    AYUDA = "Lista los componentes del diseño con la misma geometría o muy parecida a la del cuerpo elegido."
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"
    _ESTADOS = {"duplicate": "duplicado", "highly_similar": "muy similar", "similar": "similar"}

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Componente (un cuerpo suyo)", {"cuerpo"}),
                Info("resultado", "Componentes similares", self._resultado)]

    def _resultado(self, v, ctx):
        from ...api.errores import ErrorAPI
        from ...api.herramientas_similares import buscar_similares
        if not v.get("cuerpo"):
            return "Elegí un cuerpo del componente."
        componente = ctx.estado.cuerpo(v["cuerpo"][0]["ref"]["cuerpo"]).componente
        if not componente:
            return "Ese cuerpo no está en un componente: ENSAMBLAR › Nuevo componente lo crea."
        try:
            encontrados, comparados = buscar_similares(ctx.estado, componente)
        except ErrorAPI as e:
            return e.mensaje
        coincidencias = encontrados[0]["matches"] if encontrados else []
        if not coincidencias:
            return f"Ningún otro componente se parece (se compararon {comparados})."
        return "\n".join(f"{c['name']}: {self._ESTADOS[c['status']]}" for c in coincidencias)

    def construir(self, v, ctx):
        return None


class ReconocerFunciones(Comando):
    CLAVE, TITULO, ICONO = "reconocer_funciones", "Reconocer funciones", "reconocer_funciones"
    AYUDA = ("Encuentra los agujeros, empalmes, chaflanes, extrusiones, revoluciones, simetrías y patrones de un cuerpo "
             "sin historial (por ejemplo, importado) y los lista. Con «Rehacer en el timeline», Aceptar vuelve los "
             "agujeros, empalmes y chaflanes pasos paramétricos (el cuerpo queda igual).")
    SIN_OP, TEXTO_ACEPTAR = True, "Aceptar"
    _TEXTO = {"hole": "Agujeros", "fillet": "Empalmes", "chamfer": "Chaflanes", "extrude": "Extrusión",
              "revolve": "Revolución", "mirror": "Simetrías", "circular_pattern": "Patrones circulares",
              "rectangular_pattern": "Patrones rectangulares"}
    _CASILLAS = (("hole", "agujeros", "Agujeros"), ("fillet", "empalmes", "Empalmes"),
                 ("chamfer", "chaflanes", "Chaflanes"), ("extrude", "extrusion", "Extrusión"),
                 ("revolve", "revolucion", "Revolución"), ("mirror", "simetria", "Simetría"),
                 ("circular_pattern", "patron_circular", "Patrón circular"),
                 ("rectangular_pattern", "patron_rectangular", "Patrón rectangular"))

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Cuerpo sólido", {"cuerpo"}),
                *(Casilla(c, texto, True, grupo="Qué reconocer") for _t, c, texto in self._CASILLAS),
                Casilla("rehacer", "Rehacer en el timeline", False, grupo="Rehacer",
                        ayuda="Aceptar crea los pasos Agujero, Empalme y Chaflán que rehacen lo encontrado."),
                Casilla("rehacer_extrusion", "Rehacer la extrusión (reemplaza el cuerpo)", False, grupo="Rehacer",
                        visible_si=lambda v: bool(v.get("rehacer")),
                        ayuda="Si el cuerpo es un prisma, lo vuelve boceto + extrusión (los agujeros pasantes quedan en el boceto)."),
                Info("resultado", "Funciones encontradas", self._resultado, grupo="Resultado")]

    def _tipos(self, v):
        return [t for t, c, _texto in self._CASILLAS if v.get(c)]

    def _resultado(self, v, ctx):
        from ...api import llamar
        from ...api.sesion import Sesion
        if not v.get("cuerpo"):
            return "Elegí un cuerpo sólido."
        tipos = self._tipos(v)
        if not tipos:
            return "Marcá qué reconocer."
        r = llamar(Sesion(ctx.doc), "find_features", {"body": v["cuerpo"][0]["ref"]["cuerpo"], "types": tipos})
        if not r["ok"]:
            return r["mensaje"]
        r = r["result"]
        lineas = []
        for tipo, texto in self._TEXTO.items():
            hallados = [f for f in r["features"] if f["type"] == tipo]
            if not hallados:
                continue
            if tipo == "hole":
                detalle = ", ".join(f"Ø{f['diameter']:g}" + (" pasante" if f["through"] else f" prof. {f['depth']:g}")
                                    for f in hallados)
            elif tipo == "fillet":
                detalle = ", ".join(sorted({f"R{f['radius']:g}" for f in hallados}))
            elif tipo == "chamfer":
                detalle = ", ".join(sorted({f"{f['width']:g} mm a {f['angle']:g}°" for f in hallados}))
            elif tipo == "extrude":
                detalle = ", ".join(f"{f['distance']:g} mm" for f in hallados)
            elif tipo == "revolve":
                detalle = ", ".join(f"{f['angle']:g}°" for f in hallados)
            else:
                detalle = ", ".join(f"{f['count']} × {self._TEXTO[f['feature']].lower()}" for f in hallados)
            lineas.append(f"{texto}: {len(hallados)} ({detalle})")
        return "\n".join(lineas) or "No se encontró ninguna función."

    def construir(self, v, ctx):
        return None

    def aplicar(self, v, ctx):
        from ...api import llamar
        from ...api.sesion import Sesion
        if not v.get("rehacer"):
            return
        if not v.get("cuerpo"):
            raise ErrorComando("Elegí un cuerpo sólido.")
        tipos = [t for t in self._tipos(v) if t in ("hole", "fillet", "chamfer")]
        if v.get("rehacer_extrusion"):
            tipos = ["extrude", *tipos]
        if not tipos:
            raise ErrorComando("Marcá agujeros, empalmes o chaflanes para rehacer.")
        r = llamar(Sesion(ctx.doc), "rebuild_features", {"body": v["cuerpo"][0]["ref"]["cuerpo"], "types": tipos})
        if not r["ok"]:
            raise ErrorComando(r["mensaje"])
        if hasattr(ctx.ventana, "statusBar") and r["result"]["not_rebuilt"]:
            ctx.ventana.statusBar().showMessage(
                f"No se rehicieron {len(r['result']['not_rebuilt'])} funciones: "
                + "; ".join(f["reason"] for f in r["result"]["not_rebuilt"][:3]), 8000)


# ---------------------------------------------------------------- barrido de parámetros (SC18)
_MEDIDAS_BARRIDO = ["volume", "mass", "area", "bounding_box"]      # lo que mide parameter_sweep por defecto
_COLUMNAS_BARRIDO = [("Valor", "value"), ("Volumen (mm³)", "volume"), ("Masa (g)", "mass_g"), ("Área (mm²)", "area"),
                     ("Caja (mm)", "bounding_box"), ("Interferencia", "interference"), ("Error", "error")]


def _celda_barrido(f, clave, crudo=False):
    """El texto de una celda de la tabla del barrido (y, con crudo, lo que va al portapapeles)."""
    v = f.get(clave)
    if clave == "error":
        return v or ""
    if clave == "interference":
        return "" if v is None else ("Sí" if v else "No")
    if v is None:
        return ""
    if clave == "bounding_box":
        x, y, z = v["size"]
        return f"{x:g}; {y:g}; {z:g}" if crudo else f"{_n(x)} × {_n(y)} × {_n(z)}"
    return f"{v:g}" if crudo else _n(v)


class _ResultadosBarrido(QWidget):
    """Tabla del barrido de parámetros: «Copiar» la pasa al portapapeles separada por tabuladores."""

    def __init__(self, comando, panel, r):
        super().__init__(panel)
        self.comando = comando
        self.setFixedWidth(min(760, max(panel.width() - 24, 420)))
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        cab, ico, titulo = armar_cabecera(self, panel.cancelar)
        ico.setPixmap(icono("parametros").pixmap(18, 18))
        titulo.setText(f"RESULTADOS DEL BARRIDO DE {r['parameter'].upper()}")
        v.addWidget(cab)
        filas = r["rows"]
        self.filas = filas
        self.tabla = t = QTableWidget(len(filas), len(_COLUMNAS_BARRIDO))
        t.setHorizontalHeaderLabels([c[0] for c in _COLUMNAS_BARRIDO])
        t.verticalHeader().hide()
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        t.setFixedHeight(min(40 + 30 * len(filas), 240))
        for i, f in enumerate(filas):
            for j, (_t, clave) in enumerate(_COLUMNAS_BARRIDO):
                t.setItem(i, j, QTableWidgetItem(_celda_barrido(f, clave)))
        v.addWidget(t)
        pie = QHBoxLayout()
        pie.setContentsMargins(10, 4, 10, 8)
        self.boton_copiar = QPushButton("Copiar", toolTip="Copia la tabla al portapapeles (separada por tabuladores)")
        self.boton_copiar.clicked.connect(self._copiar)
        pie.addWidget(self.boton_copiar)
        pie.addStretch(1)
        self.boton_cerrar = QPushButton("Cerrar", objectName="boton_primario")
        self.boton_cerrar.clicked.connect(self.close)
        pie.addWidget(self.boton_cerrar)
        v.addLayout(pie)
        self.adjustSize()
        self.move((self.parent().width() - self.width()) // 2, max(12, self.parent().height() - self.height() - 48))
        self.show()
        self.raise_()

    def _copiar(self):
        QApplication.clipboard().setText("\n".join(
            ["\t".join(c[0] for c in _COLUMNAS_BARRIDO)]
            + ["\t".join(_celda_barrido(f, clave, crudo=True) for _t, clave in _COLUMNAS_BARRIDO)
               for f in self.filas]))

    def closeEvent(self, e):
        self.comando.dialogo = None
        super().closeEvent(e)


class BarridoParametros(Comando):
    CLAVE, TITULO, ICONO = "barrido_parametros", "Barrido de parámetros", "parametros"
    AYUDA = ("Recalcula el diseño con cada valor de un parámetro en un rango y arma una tabla con volumen, masa, "
             "área, caja envolvente y, si se pide, interferencia. El diseño no cambia.")
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"
    dialogo = None

    def campos(self, ctx):
        opciones = {p.nombre: p.nombre for p in ctx.doc.parametros if p.tipo != TEXTO}
        return [Opciones("parametro", "Parámetro", opciones or {"": "(sin parámetros)"}),
                Expresion("desde", "Desde", "10 mm", ayuda="Primer valor, en la unidad del parámetro."),
                Expresion("hasta", "Hasta", "30 mm", ayuda="Último valor, en la unidad del parámetro."),
                Entero("pasos", "Pasos", 5, 2, 50, ayuda="Cantidad de valores entre Desde y Hasta, ambos incluidos."),
                Casilla("interferencia", "Buscar interferencia",
                        ayuda="Con cada valor busca choques entre los cuerpos sólidos (más lento)."),
                Personalizado("calcular", "Calcular", self._boton_calcular)]

    def verificar(self, ctx):
        return (None if any(p.tipo != TEXTO for p in ctx.doc.parametros)
                else "Este documento no tiene parámetros que se puedan barrer.")

    def _numero(self, v, ctx, texto):
        """La expresión tecleada como número en la unidad del parámetro (lo que entiende parameter_sweep)."""
        p = ctx.doc.parametros.obtener(v["parametro"])
        return unidad_de(p.tipo, p.unidad).desde_interno(ctx.evaluar(texto, p.tipo))

    def _boton_calcular(self, panel):
        b = QPushButton("Calcular")
        b.setIcon(icono("parametros"))
        b.clicked.connect(lambda: self.calcular(panel))
        return b

    def calcular(self, panel):
        from ...api.errores import ErrorAPI
        from ...api.herramientas_barrido import _barrido
        from ...api.sesion import Sesion
        ctx, v = panel.ctx, panel.valores
        if not v.get("parametro"):
            panel._mostrar("No hay parámetros que se puedan barrer.")
            return
        try:
            desde, hasta = self._numero(v, ctx, v["desde"]), self._numero(v, ctx, v["hasta"])
        except (ErrorComando, ErrorExpresion) as e:
            panel._mostrar(str(e))
            return
        dlg = QProgressDialog("Calculando el barrido…", "Cancelar", 0, int(v["pasos"]), panel)
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(0)

        def progreso(i, n):
            dlg.setValue(i)
            QApplication.processEvents()
        try:
            r = _barrido(Sesion(ctx.doc), v["parametro"], desde, hasta, int(v["pasos"]),
                         _MEDIDAS_BARRIDO + (["interference"] if v.get("interferencia") else []),
                         None, None, progreso=progreso, cancelado=dlg.wasCanceled)
        except ErrorAPI as e:              # cancelado o error del barrido: se informa en el panel
            dlg.close()
            if not dlg.wasCanceled():
                panel._mostrar(e.mensaje)
            return
        dlg.close()
        if self.dialogo is not None:
            d, self.dialogo = self.dialogo, None
            d.close()
            d.deleteLater()
        self.dialogo = _ResultadosBarrido(self, panel, r)

    def construir(self, v, ctx):
        return None

    def al_cerrar(self, ctx):
        if self.dialogo is not None:
            d, self.dialogo = self.dialogo, None
            d.deleteLater()


# ---------------------------------------------------------------- análisis guardados en el navegador
ANALISIS_POR_TIPO = {}             # tipo guardado en el documento → comando que lo crea y lo edita (`Editar` del navegador)


class _Analisis(Comando):
    TIPO_ANALISIS = ""
    SIN_OP = True
    editando = None                # nombre del análisis que se reabrió desde la carpeta Análisis

    def construir(self, v, ctx):
        return None

    def titulo_icono(self, valores):
        titulo, ico = super().titulo_icono(valores)
        return (f"Editar {titulo}", ico) if self.editando else (titulo, ico)

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []]}

    def desde_params(self, p, ctx):
        """Valores del panel para un análisis guardado: lo que falta queda con su valor por defecto."""
        return {"cuerpos": _hits_cuerpos(p.get("cuerpos"), ctx)}

    def mostrar(self, v, ctx):
        if ctx.ventana is None:
            return
        datos = analisis_vista.calcular(self.TIPO_ANALISIS, self.params(v, ctx), ctx.estado,
                                        ctx.ventana.propiedades_analisis(ctx.estado))
        analisis_vista.aplicar(ctx.ventana.visor, datos)

    def aplicar(self, v, ctx):
        if self.editando:
            ctx.doc.editar_analisis(self.editando, self.params(v, ctx))
        else:
            ctx.doc.agregar_analisis(self.TIPO_ANALISIS, self.params(v, ctx))

    def al_cerrar(self, ctx):
        if ctx.ventana is not None:
            ctx.ventana.aplicar_analisis()


def _hits_cuerpos(ids, ctx):
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in ids or []], ctx.estado)


def _cuerpos_campo(etiqueta="Cuerpos", filtros=("cuerpo",)):
    return Seleccion("cuerpos", etiqueta, set(filtros), minimo=0, maximo=None, ayuda="Sin selección: todos.", sin_resalte=True)


def _opacidad():
    return Deslizador("opacidad", "Opacidad", 100, 0, 100)


class Seccion(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "seccion", "Análisis de sección", "seccion", "seccion"
    AYUDA = "Corta la vista del modelo con un plano para ver su interior (no cambia el modelo)."
    INFO = {"titulo": "Información de análisis de sección", "ancho": 656, "centrado": True,
            "texto": "Cree varios análisis de sección y, a continuación, ajuste su visibilidad en el navegador para alternar "
                     "entre ellos.",
            "consejos": "La opción Color de sección se establece por defecto en Desde el componente, y muestra el color de la "
                        "vista en sección codificado por componente. Defínalo como Personalizado para cambiar toda la vista en "
                        "sección a un único color que usted especifique.",
            "articulo": "fusion-model/create-a-3d-section-view-5de88af0c95.md"}

    def campos(self, ctx):
        con_plano = lambda v: bool(v.get("plano"))  # noqa: E731
        return [Seleccion("plano", "Plano de corte", {"cara_plana", "plano"}),
                Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, minimo=0, maximo=None, ayuda="Sin selección: todos.", visible_si=con_plano, sin_resalte=True),
                Expresion("desfase", "Distancia", "0 mm", visible_si=con_plano),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO, visible_si=con_plano),
                Casilla("invertir", "Invertir", visible_si=con_plano),
                Opciones("color_modo", "Color de sección", {"componente": "Desde el componente", "personalizado": "Personalizado"},
                         visible_si=con_plano, avanzado=True),
                Personalizado("color", "Color propio", self._boton_color, list(COLOR_SECCION),
                              visible_si=lambda v: con_plano(v) and v.get("color_modo") != "componente", avanzado=True),
                Casilla("rayado", "Mostrar rayado", True, visible_si=con_plano, avanzado=True)]

    @staticmethod
    def _boton_color(panel):
        """Muestra el color elegido como muestra (sin números); un clic abre el selector de colores."""
        boton = QPushButton("Cambiar color…")

        def pintar():
            c = QColor.fromRgbF(*panel.valores["color"])
            boton.setStyleSheet(f"background: {c.name()}; color: {'#101010' if c.lightnessF() > 0.55 else '#f4f4f4'};"
                                " padding: 3px 8px;")

        def elegir():
            c = QColorDialog.getColor(QColor.fromRgbF(*panel.valores["color"]), boton, "Color de la sección",
                                      QColorDialog.DontUseNativeDialog)
            if c.isValid():
                panel._cambiar("color", [c.redF(), c.greenF(), c.blueF()])
                pintar()
        boton.clicked.connect(elegir)
        pintar()
        return boton

    def params(self, v, ctx):
        if not v.get("plano"):
            raise ErrorComando("Seleccioná el plano de corte.")
        return {"plano": ref1(v, "plano"), "desfase_mm": ctx.evaluar(v["desfase"]),
                "angulo": ctx.evaluar(v["angulo"], ANGULO), "invertir": bool(v["invertir"]),
                "cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []],
                "color_modo": v["color_modo"], "color": [float(x) for x in v.get("color") or COLOR_SECCION],
                "rayado": bool(v["rayado"])}

    def desde_params(self, p, ctx):
        return {**super().desde_params(p, ctx), "plano": hits([p["plano"]], ctx.estado), "desfase": f"{p.get('desfase_mm', 0.0)} mm",
                "angulo": f"{p.get('angulo', 0.0)} deg", "invertir": bool(p.get("invertir")), "color": list(p.get("color") or COLOR_SECCION),
                "color_modo": p.get("color_modo", "personalizado"), "rayado": bool(p.get("rayado"))}

    def mostrar(self, v, ctx):
        if v.get("plano"):
            super().mostrar(v, ctx)


class Cebra(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "cebra", "Análisis cebra", "cebra", "cebra"
    AYUDA = "Franjas reflejadas para ver la continuidad entre caras (sigue a la cámara)."

    def campos(self, ctx):
        return [_cuerpos_campo(), *campos_cebra()]

    def params(self, v, ctx):
        p = {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], **params_cebra(v, ctx)}
        if self.editando and "vista_fija" in p and "vista_fija" in ctx.doc.analisis[self.editando]["params"]:
            p["vista_fija"] = ctx.doc.analisis[self.editando]["params"]["vista_fija"]        # editar no mueve las rayas fijas
        return p

    def desde_params(self, p, ctx):
        return {**super().desde_params(p, ctx), "orientacion": p.get("orientacion", "horizontal"), "frecuencia": int(p.get("frecuencia", 8)),
                "opacidad": int(p.get("opacidad", 100)), "bloquear": "vista_fija" in p, "alta_calidad": bool(p.get("alta_calidad"))}


class MapaEntorno(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "mapa_entorno", "Análisis de mapas de entorno", "mapa_entorno", "mapa_entorno"
    AYUDA = "Refleja un entorno sobre las caras para evaluar su suavidad."

    def campos(self, ctx):
        return [_cuerpos_campo(),
                Opciones("entorno", "Entorno", {k: d[0] for k, d in an.ENTORNOS_ANALISIS.items()}, "luz_suave"),
                Deslizador("rotacion", "Rotar", 0.0, -180.0, 180.0, decimales=1, sufijo="deg"),
                Casilla("reflejo", "Aplicar simetría", True, ayuda="Apagada queda el cromo sin el reflejo del entorno.")]

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], "entorno": v["entorno"],
                "rotacion": float(v["rotacion"]), "reflejo": bool(v["reflejo"])}

    def desde_params(self, p, ctx):
        return {**super().desde_params(p, ctx), "entorno": p.get("entorno", "luz_suave"), "rotacion": float(p.get("rotacion", 0.0)),
                "reflejo": bool(p.get("reflejo", True))}


class AnguloDesmoldeo(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "angulo_desmoldeo", "Análisis de ángulo de desmoldeo", "angulo_desmoldeo", \
        "desmoldeo"
    AYUDA = "Pinta el cuerpo en degradé según el ángulo de cada zona respecto de la dirección de extracción."
    ANCHO_PANEL = "ancho"

    def campos(self, ctx):
        return [_cuerpos_campo("Cuerpo"), Seleccion("direccion", "Dirección", {"cara_plana", "plano", "eje", "arista_lineal"},
                                                    minimo=0, ayuda="Sin selección: eje Z."),
                Casilla("invertir", "Invertir dirección", visible_si=lambda v: bool(v.get("direccion"))),
                DosTopes("angulo", "Ángulo de desmoldeo", (-2.0, 2.0), -90.0, 90.0, sufijo="deg"),
                Casilla("zona", "Zona de tolerancia", True),
                DosTopes("tolerancia", "Tolerancia", (-0.5, 0.5), -90.0, 90.0, sufijo="deg", visible_si=lambda v: bool(v.get("zona"))),
                _opacidad(), Casilla("alta_calidad", "Calidad alta")]

    def params(self, v, ctx):
        p = {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], "direccion": ref1(v, "direccion"),
             "invertir": bool(v["invertir"]), "angulo_min": float(v["angulo"][0]), "angulo_max": float(v["angulo"][1]),
             "degradado": True, "opacidad": int(v["opacidad"]), "alta_calidad": bool(v["alta_calidad"])}
        if v["zona"]:
            p["tolerancia"] = [float(x) for x in v["tolerancia"]]
        return p

    def desde_params(self, p, ctx):
        v = {**super().desde_params(p, ctx), "invertir": bool(p.get("invertir")), "opacidad": int(p.get("opacidad", 100)),
             "angulo": [float(p.get("angulo_min", 0.0)), float(p.get("angulo_max", 3.0))], "alta_calidad": bool(p.get("alta_calidad")),
             "zona": "tolerancia" in p or not p.get("degradado"), "direccion": hits([p["direccion"]], ctx.estado) if p.get("direccion") else []}
        return v | ({"tolerancia": list(p["tolerancia"])} if "tolerancia" in p else {})


class MapaCurvatura(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "mapa_curvatura", "Análisis del mapa de curvatura", "mapa_curvatura", \
        "curvatura"
    AYUDA = "Colorea las caras según su curvatura (gaussiana, principal mínima o principal máxima)."
    INFO = {"titulo": "Información de análisis del mapa de curvatura", "ancho": 656, "centrado": True,
            "texto": "En los mapas de curvatura gaussiana, los colores cálidos indican una curvatura positiva, el verde indica una "
                     "superficie plana y los colores fríos indican una curvatura negativa. En los mapas de curvatura mínima "
                     "principal, las regiones verdes alcanzan el umbral del límite máximo y las regiones rojas lo superan. En los "
                     "mapas de curvatura máxima principal, las regiones verdes alcanzan el umbral del límite mínimo y las regiones "
                     "rojas lo superan.",
            "consejos": "En el navegador, los análisis se guardan en la carpeta Análisis, donde los podrá ver, ocultar o editar.",
            "articulo": "fusion-model/analyze-curvature-of-surfaces-41c34845ba2.md"}

    def campos(self, ctx):
        return [_cuerpos_campo(), *campos_mapa()]

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], **params_mapa(v, ctx)}

    def desde_params(self, p, ctx):
        v = {**super().desde_params(p, ctx), "tipo_curvatura": p.get("tipo_curvatura", "gaussiana"), "opacidad_mapa": int(p.get("opacidad", 100)),
             "alta_calidad_mapa": bool(p.get("alta_calidad")), "visualizar": "bandas" if p.get("bandas") else "suave",
             "escala": float(p.get("escala", 1.0))}
        return v | ({"limite": str(p["limite"])} if p.get("limite") else {})


class PeineCurvatura(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "curvatura_peine", "Análisis de curvatura en peine", "curvatura_peine", "peine"
    AYUDA = "Muestra un peine sobre las aristas: púas más largas = más curvatura."

    def campos(self, ctx):
        return [Seleccion("aristas", "Aristas", {"arista", "curva_boceto"}, maximo=None),
                Deslizador("densidad", "Densidad", 50, 2, 100), Deslizador("escala", "Escala", 10.0, 0.0, 100.0, decimales=3)]

    def params(self, v, ctx):
        if not v.get("aristas"):
            raise ErrorComando("Seleccioná aristas o curvas.")
        # la Escala 10 de Fusion es la escala 1 que guarda el análisis (los viejos y la API siguen midiendo igual)
        return {"aristas": [h["ref"] for h in v["aristas"]], "densidad": int(v["densidad"]), "escala": max(float(v["escala"]), 1e-3) / 10.0}

    def desde_params(self, p, ctx):
        return {"aristas": hits(p.get("aristas"), ctx.estado), "densidad": int(p.get("densidad", 30)),
                "escala": float(p.get("escala", 1.0)) * 10.0}

    def mostrar(self, v, ctx):
        if v.get("aristas"):
            super().mostrar(v, ctx)


class Isocurva(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "isocurva", "Análisis de la isocurva", "isocurva", "isocurva"
    AYUDA = "Dibuja las curvas U y V de las caras para ver su calidad."

    def campos(self, ctx):
        return [_cuerpos_campo("Cuerpos/Caras", ("cuerpo", "cara")), *campos_iso()]

    def params(self, v, ctx):
        elegidos = v.get("cuerpos") or []
        p = {"cuerpos": [h["ref"]["cuerpo"] for h in elegidos if h["ref"].get("tipo") == "cuerpo"], **params_iso(v, ctx)}
        caras = [h["ref"] for h in elegidos if h["ref"].get("tipo") == "cara"]
        return p | ({"caras": caras} if caras else {})

    def desde_params(self, p, ctx):
        return {"cuerpos": _hits_cuerpos(p.get("cuerpos"), ctx) + hits(p.get("caras"), ctx.estado), "tipo_iso": p.get("tipo_iso", "uv"),
                "densidad": int(p.get("densidad", 10)), "peines": bool(p.get("peines")), "densidad_peine": int(p.get("densidad_peine", 50)),
                "escala_peine": float(p.get("escala_peine", 10.0))}


class Accesibilidad(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "accesibilidad", "Análisis de accesibilidad", "accesibilidad", \
        "accesibilidad"
    AYUDA = "Verde: se alcanza desde la dirección elegida; rojo: queda tapado."

    def campos(self, ctx):
        return [_cuerpos_campo("Cuerpo"), Seleccion("direccion", "Dirección", {"cara_plana", "plano", "eje", "arista_lineal"},
                                                    minimo=0, ayuda="Sin selección: desde arriba (Z)."),
                _opacidad(),
                Botones("sentido", "Cambiar dirección", {"dir1": ("Dirección 1", "dir_un_lado"), "dir2": ("Dirección 2", "dir_dos_lados"),
                                                         "ambas": ("Ambas direcciones", "dir_simetrica")},
                        visible_si=lambda v: bool(v.get("direccion")))]

    def params(self, v, ctx):
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], "direccion": ref1(v, "direccion"),
                "sentido": v["sentido"], "opacidad": int(v["opacidad"])}

    def desde_params(self, p, ctx):
        return {**super().desde_params(p, ctx), "direccion": hits([p["direccion"]], ctx.estado) if p.get("direccion") else [],
                "sentido": p.get("sentido", "dir2" if p.get("invertir") else "dir1"), "opacidad": int(p.get("opacidad", 100))}


class RadioMinimo(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "radio_minimo", "Análisis de radio mínimo", "radio_minimo", "radio_minimo"
    AYUDA = "Marca en rojo las zonas donde no entra una fresa: degradé entre el Radio mínimo y el máximo."

    def campos(self, ctx):
        return [_cuerpos_campo("Cuerpo"), Expresion("radio_max", "Radio máximo de la herramienta", "25 mm"),
                Deslizador("radio_min", "Radio mínimo", 0.0, 0.0, formato.longitud(25.0), decimales=3, sufijo=formato.sufijo()),
                _opacidad(), Casilla("afilados", "Bordes afilados", ayuda="Incluye los rincones vivos: radio 0.")]

    def preparar_panel(self, panel):
        self.al_cambiar(panel, "radio_max")

    def al_cambiar(self, panel, clave):
        """El tope del Radio mínimo es el Radio máximo."""
        if clave != "radio_max":
            return
        try:
            tope = formato.longitud(panel.ctx.evaluar(panel.valores["radio_max"]))
        except (ValueError, TypeError):      # expresión a medio escribir: el panel ya lo marca en rojo
            return
        w = panel.widgets["radio_min"]
        w.numero.setMaximum(max(tope, 0.0))
        w.deslizador.setMaximum(int(max(tope, 0.0) * 1000))

    def params(self, v, ctx):
        radio = ctx.evaluar(v["radio_max"])
        if radio <= 0:
            raise ErrorComando("El radio máximo tiene que ser mayor que cero.")
        return {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or []], "radio": radio,
                "radio_minimo": min(float(v["radio_min"]) / formato.longitud(1.0), radio), "aristas_vivas": bool(v["afilados"]),
                "opacidad": int(v["opacidad"])}

    def desde_params(self, p, ctx):
        nuevo = "radio_minimo" in p                     # el análisis viejo tenía un solo radio y marcaba los rincones vivos
        return {**super().desde_params(p, ctx), "radio_max": f"{p.get('radio', 3.0)} mm", "opacidad": int(p.get("opacidad", 100)),
                "radio_min": formato.longitud(p.get("radio_minimo", 0.0)), "afilados": bool(p.get("aristas_vivas", not nuevo))}


class CentroMasa(_Analisis):
    CLAVE, TITULO, ICONO, TIPO_ANALISIS = "centro_masa", "Centro de masa", "centro_masa", "centro_masa"
    AYUDA = "Marca el centro de masa de los cuerpos o componentes elegidos y lo deja en la carpeta Análisis: se puede medir desde él."

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Selección", {"cuerpo", "componente"}, minimo=0, maximo=None,
                          ayuda="Seleccionar cuerpos o componentes. Sin selección: todos."),
                Info("resultado", "Centro de masa", self._resultado)]

    def params(self, v, ctx):
        p = {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("cuerpos") or [] if h["ref"].get("tipo") == "cuerpo"]}
        comp = [h["ref"]["componente"] for h in v.get("cuerpos") or [] if h["ref"].get("tipo") == "componente"]
        return p | ({"componentes": comp} if comp else {})

    def desde_params(self, p, ctx):
        return {"cuerpos": _hits_cuerpos(p.get("cuerpos"), ctx)
                + hits([{"tipo": "componente", "componente": c} for c in p.get("componentes") or []], ctx.estado)}

    def _calcular(self, v, ctx):
        return centro_de_masa(self.params(v, ctx), ctx.estado, ctx.doc.propiedades)

    def _resultado(self, v, ctx):
        c, masa = self._calcular(v, ctx)
        return "No hay cuerpos sólidos." if c is None else f"{_vec(c)} {formato.sufijo()}\nMasa total: {_n(formato.masa(masa))} {formato.unidad_masa()}"


registrar(ReconocerFunciones, BuscarSimilares, Medir, Interferencia, BarridoParametros, Seccion, Cebra, MapaEntorno,
          AnguloDesmoldeo, MapaCurvatura, PeineCurvatura, Isocurva, Accesibilidad, RadioMinimo, CentroMasa)
ANALISIS_POR_TIPO.update({c.TIPO_ANALISIS: c for c in (Seccion, Cebra, MapaEntorno, AnguloDesmoldeo, MapaCurvatura, PeineCurvatura, Isocurva,
                                                       Accesibilidad, RadioMinimo, CentroMasa)})
