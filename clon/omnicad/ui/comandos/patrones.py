# -*- coding: utf-8 -*-
"""Patrones de SÓLIDO › CREAR que se agregan a los de `crear.py`: Patrón en puntos y Multitransformación (patrón +
simetría + patrón en un solo paso, como el MultiTransform de FreeCAD; ninguna de las dos es una herramienta de Fusion).
Los dos repiten cuerpos u operaciones.

La Multitransformación es una LISTA de transformaciones (agregar, quitar, subir, bajar) y un editor de la que está
seleccionada. Cada elemento de la lista guarda su receta completa: lo que el editor no muestra (la simetría de la
dirección 2, las copias suprimidas, las coordenadas de la API…) viaja intacto al aceptar sin tocarlo."""
import copy

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QMenu, QPushButton, QToolButton, QVBoxLayout, QWidget

from ...timeline.ops_solido import OpMultitransformar
from ..comando import Casilla, Comando, ErrorComando, Info, Opciones, Personalizado, Seleccion, ref1
from . import registrar
from .crear import (_de_cuerpos, _h1, _Patron, campos_objeto, campos_patron, objeto_params, objeto_valores,
                    params_patron, valores_patron)

MAX_TRANSFORMACIONES = 12                         # recursos: cada una multiplica las instancias (tope total: 10.000)
TIPOS_TRANSFORMACION = {"rectangular": "Patrón rectangular", "circular": "Patrón circular",
                        "ruta": "Patrón en trayectoria", "puntos": "Patrón en puntos", "simetria": "Simetría"}
FALTA = {"rectangular": "la dirección 1", "circular": "el eje", "ruta": "la ruta", "puntos": "los puntos",
         "simetria": "el plano de simetría"}


class PatronPuntos(_Patron):
    CLAVE, TITULO, ICONO, FORMA = "patron_puntos", "Patrón en puntos", "patron_puntos", "puntos"
    AYUDA = "Copias de cuerpos u operaciones en cada punto elegido (puntos de boceto, vértices o puntos de construcción)."
    VARIANTE = ("forma_patron", "puntos")


def _completa(item):
    """¿La transformación tiene lo imprescindible para calcularse?"""
    tipo = item.get("tipo")
    if tipo == "rectangular":
        return bool(item.get("dir1"))
    if tipo == "circular":
        return bool(item.get("eje"))
    if tipo == "ruta":
        return bool(item.get("ruta"))
    if tipo == "puntos":
        return bool(item.get("puntos") or item.get("coordenadas"))
    return tipo == "simetria" and bool(item.get("plano"))


def _etiqueta(i, item):
    tipo = item.get("tipo")
    detalle = {"rectangular": f" {item.get('n1', 3)}×{item.get('n2', 1)}", "circular": f" ×{item.get('n', 6)}",
               "ruta": f" ×{item.get('n1', 3)}",
               "puntos": f" ({len(item.get('puntos') or []) + len(item.get('coordenadas') or [])})"}.get(tipo, "")
    falta = "" if _completa(item) else f"   ⚠ falta {FALTA.get(tipo, 'completarla')}"
    return f"{i + 1}. {TIPOS_TRANSFORMACION.get(tipo, str(tipo))}{detalle}{falta}"


def _item_nuevo(tipo):
    return {"tipo": tipo}


def _valores_item(item, estado):
    """Valores del editor (campos «t_…») para una transformación guardada."""
    tipo = item.get("tipo") if item.get("tipo") in TIPOS_TRANSFORMACION else "rectangular"
    if tipo == "simetria":
        return {"t_tipo": tipo, "t_plano": _h1(item.get("plano"), estado)}
    return {**valores_patron(dict(item, tipo=tipo), estado, "t_"), "t_tipo": tipo}


class Multitransformar(Comando):
    CLAVE, TITULO, ICONO = "multitransformar", "Multitransformación", "multitransformar"
    AYUDA = ("Patrones y simetrías encadenados en un solo paso: cada transformación se aplica a todas las copias de "
             "las anteriores (patrón de 3 + simetría = 6).")
    CLASE_OP = OpMultitransformar
    ANCHO_PANEL = "ancho"          # lista de transformaciones + el editor de la elegida

    # ------------------------------------------------------------ campos
    def campos(self, ctx):
        tipo = lambda v: v.get("t_tipo", "rectangular")                         # noqa: E731
        return (campos_objeto()
                + [Personalizado("lista", "Transformaciones", self._crear_lista, ancho_completo=True),
                   Info("etapa", "", self._info_etapa),
                   Opciones("t_tipo", "Tipo de transformación", TIPOS_TRANSFORMACION, "rectangular")]
                + campos_patron("t_", forma=tipo)
                + [Seleccion("t_plano", "Plano de simetría", {"plano", "cara_plana"},
                             visible_si=lambda v: tipo(v) == "simetria"),
                   Casilla("combinar", "Unir al original", visible_si=_de_cuerpos),
                   Casilla("ligeras", "Copias ligeras (comparten la geometría)", avanzado=True,
                           visible_si=lambda v: _de_cuerpos(v) and not v.get("combinar"),
                           ayuda="Las copias rígidas comparten la geometría del original (las simetrías, no).")])

    def _crear_lista(self, panel):
        w = QWidget()
        col = QVBoxLayout(w)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)
        w.lista = QListWidget(objectName="lista_transformaciones")
        w.lista.setMaximumHeight(112)
        w.lista.currentRowChanged.connect(lambda i: self._ir_a(panel, i))
        col.addWidget(w.lista)
        fila = QHBoxLayout()
        fila.setSpacing(4)
        w.agregar = QToolButton(text="＋ Agregar", objectName="agregar_transformacion")
        w.agregar.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(w.agregar)
        for clave, texto in TIPOS_TRANSFORMACION.items():
            menu.addAction(texto, lambda k=clave: self._agregar(panel, k))
        w.agregar.setMenu(menu)
        w.quitar = QPushButton("Quitar", objectName="quitar_transformacion")
        w.subir = QPushButton("▲", objectName="subir_transformacion")
        w.bajar = QPushButton("▼", objectName="bajar_transformacion")
        w.quitar.clicked.connect(lambda: self._quitar(panel))
        w.subir.clicked.connect(lambda: self._mover(panel, -1))
        w.bajar.clicked.connect(lambda: self._mover(panel, 1))
        for b in (w.agregar, w.quitar, w.subir, w.bajar):
            fila.addWidget(b)
        fila.addStretch(1)
        col.addLayout(fila)
        return w

    def preparar_panel(self, panel):
        if "_lista" not in panel.valores:                         # un comando nuevo: una transformación para empezar
            panel.valores["_lista"], panel.valores["_sel"] = [_item_nuevo("rectangular")], 0
        self._refrescar(panel)

    # ------------------------------------------------------------ la lista y el editor
    def _sel(self, v):
        lista = v.get("_lista") or []
        return min(max(int(v.get("_sel", 0)), 0), max(len(lista) - 1, 0))

    def _item_desde_editor(self, v, base, estricto):
        """La receta de la transformación que muestra el editor, sobre lo que ya tenía guardado (`base`): las claves que
        el editor no muestra se conservan mientras no cambie el tipo."""
        tipo = v.get("t_tipo", "rectangular")
        if tipo == "simetria":
            d = {"plano": ref1(v, "t_plano")}
            if estricto and not d["plano"]:
                raise ErrorComando("Seleccioná el plano de simetría.")
        else:
            d = params_patron(v, tipo, "t_", estricto=estricto)
            d.pop("forma_patron")
        d["tipo"] = tipo
        return {**(base if base.get("tipo") == tipo else {}), **d}

    def _lista_actual(self, v):
        """Las transformaciones tal como quedarían: la lista guardada con la elegida tomada del editor. Falla con un
        mensaje que dice cuál está incompleta (nada se calcula ni se acepta a medias)."""
        lista = [dict(t) for t in v.get("_lista") or []]
        if not lista:
            raise ErrorComando("Elegí al menos una transformación.")
        if len(lista) > MAX_TRANSFORMACIONES:
            raise ErrorComando(f"Una multitransformación admite hasta {MAX_TRANSFORMACIONES} transformaciones.")
        sel = self._sel(v)
        try:
            lista[sel] = self._item_desde_editor(v, lista[sel], estricto=True)
        except ErrorComando as e:
            raise ErrorComando(f"Transformación {sel + 1} ({TIPOS_TRANSFORMACION[v.get('t_tipo', 'rectangular')]}): "
                               f"{e}") from None
        for i, t in enumerate(lista):
            if not _completa(t):
                raise ErrorComando(f"Falta completar la transformación {i + 1} ({TIPOS_TRANSFORMACION.get(t.get('tipo'), '?')}): "
                                   f"elegí {FALTA.get(t.get('tipo'), 'lo que falta')}. Mientras tanto no hay vista previa ni "
                                   "se puede aceptar.")
        return lista

    def _guardar(self, panel):
        """Pasa lo que muestra el editor a la lista (sin exigir que esté completo: se puede saltar a otra transformación)."""
        v = panel.valores
        lista = v["_lista"]
        sel = self._sel(v)
        try:
            lista[sel] = self._item_desde_editor(v, lista[sel], estricto=False)
        except ErrorComando:
            pass                                    # un texto a medio escribir: queda lo que había

    def _cargar(self, panel):
        """Muestra en el editor la transformación elegida."""
        v = panel.valores
        panel.set_valores(_valores_item(v["_lista"][self._sel(v)], panel.ctx.estado))
        siguiente = next((c for c in panel.campos if isinstance(c, Seleccion) and panel._visible(c)
                          and not panel.valores.get(c.clave)), None)
        panel._activar(siguiente)
        self._refrescar(panel)

    def _ir_a(self, panel, i):
        v = panel.valores
        if v.get("_refrescando") or i < 0 or i == self._sel(v):
            return
        self._guardar(panel)
        v["_sel"] = i
        self._cargar(panel)

    def _agregar(self, panel, tipo):
        v = panel.valores
        if len(v["_lista"]) >= MAX_TRANSFORMACIONES:
            return
        self._guardar(panel)
        v["_lista"].append(_item_nuevo(tipo))
        v["_sel"] = len(v["_lista"]) - 1
        self._cargar(panel)

    def _quitar(self, panel):
        v = panel.valores
        if len(v["_lista"]) <= 1:
            return
        del v["_lista"][self._sel(v)]
        v["_sel"] = min(self._sel(v), len(v["_lista"]) - 1)
        self._cargar(panel)

    def _mover(self, panel, delta):
        v = panel.valores
        i, j = self._sel(v), self._sel(v) + delta
        if not 0 <= j < len(v["_lista"]):
            return
        self._guardar(panel)
        v["_lista"][i], v["_lista"][j] = v["_lista"][j], v["_lista"][i]
        v["_sel"] = j
        self._refrescar(panel)
        panel._programar()

    def _refrescar(self, panel):
        """Los rótulos de la lista (con la elegida tal como está en el editor) y qué botones sirven."""
        w = panel.widgets.get("lista")
        v = panel.valores
        if w is None or "_lista" not in v:
            return
        sel, lista = self._sel(v), v["_lista"]
        try:
            actual = self._item_desde_editor(v, lista[sel], estricto=False)
        except ErrorComando:
            actual = lista[sel]
        v["_refrescando"] = True
        try:
            w.lista.clear()
            for i, t in enumerate(lista):
                w.lista.addItem(_etiqueta(i, actual if i == sel else t))
            w.lista.setCurrentRow(sel)
        finally:
            v["_refrescando"] = False
        w.quitar.setEnabled(len(lista) > 1)
        w.subir.setEnabled(sel > 0)
        w.bajar.setEnabled(sel < len(lista) - 1)
        w.agregar.setEnabled(len(lista) < MAX_TRANSFORMACIONES)

    def al_cambiar(self, panel, clave):
        if clave.startswith("t_"):
            self._refrescar(panel)

    def _info_etapa(self, v, ctx):
        lista = v.get("_lista") or []
        if not lista:
            return ""
        sel = self._sel(v)
        texto = (f"Editando la transformación {sel + 1} de {len(lista)} "
                 f"({TIPOS_TRANSFORMACION.get(v.get('t_tipo', 'rectangular'), '')}). Se aplica a las copias de las anteriores.")
        if sel < len(lista) - 1:
            try:
                from . import asas_patron
                n = len(asas_patron.instancias_hasta_etapa(ctx, self.construir(v, ctx), sel)) + 1
                texto += f" Hasta esta etapa quedan {n} instancias (en azul en la vista)."
            except Exception:  # noqa: BLE001 — una etapa incompleta ya la explica el mensaje del panel
                pass
        return texto

    def manipuladores(self, ctx, v):
        from . import asas_patron
        return asas_patron.manipuladores_etapa(ctx, v)

    def previa_vista(self, ctx, v, op):
        from . import asas_patron
        return asas_patron.previa_etapa(ctx, v, op, self._sel(v)) or None

    # ------------------------------------------------------------ operación
    def construir(self, v, ctx):
        objeto = objeto_params(v, ctx)
        return self.crear_op(OpMultitransformar, v, ctx, transformaciones=self._lista_actual(v),
                             combinar=bool(v.get("combinar")) and _de_cuerpos(v),
                             ligeras=bool(v.get("ligeras")) and _de_cuerpos(v) and not v.get("combinar"), **objeto)

    def desde_op(self, op, ctx):
        v = dict(objeto_valores(op, ctx), combinar=op.p.get("combinar", False), ligeras=op.p.get("ligeras", False))
        lista = copy.deepcopy(list(op.p.get("transformaciones") or []))
        v["_lista"], v["_sel"] = lista, 0
        if lista:
            v.update(_valores_item(lista[0], ctx.estado))
        return v


registrar(PatronPuntos, Multitransformar)
