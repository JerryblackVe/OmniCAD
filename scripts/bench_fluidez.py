"""Banco FL-0: eventos a widgets reales, sin mover el cursor del usuario.

Uso (desde clon/, Python del venv):
  QT_QPA_PLATFORM=xcb OMNICAD_PRUEBA_VENTANA=minimizada xvfb-run -a \
    python ../scripts/turno.py --plazo 1500 -- \
    python ../scripts/bench_fluidez.py a b --rep 3 --json ../evidencias/fluidez.json

En Linux hace falta QT_QPA_PLATFORM=xcb + xvfb-run -a (o un DISPLAY real).
Offscreen no ofrece el visor OpenGL y NO sirve para este banco.
Las cifras principales son el máximo entre acciones; --rep toma su mediana.
El JSON conserva cada corrida y submedida, incluidos errores y cuelgues.
"""
import argparse
from contextlib import contextmanager
from datetime import date
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import traceback

RAIZ = Path(__file__).resolve().parents[1]
METRICAS = ("bloqueo_max_ms", "primera_previa_ms", "aceptar_ms")
TOPE_SEGUNDOS = int(os.environ.get("OMNICAD_TOPE_BANCO", 300))
TITULOS = dict(zip("abcdefghijklmnopqr", (
    "Texto de 8 perfiles · Unir · 11 cuerpos", "Rosca modelada M20 × 60",
    "Empalme R2 · 200 caras", "Desfase de cara", "Barrido / bobina / solevación",
    "Combinar dos cuerpos", "Eliminar un paso · 20 pasos", "Abrir proyecto pesado (sustituto)",
    "Preferencias · deslizador y combo", "Arrastrar punto · 200 entidades", "Órbita · 300 000 triángulos",
    "Abrir motor_impreso (pieza real)", "Abrir motor_cohete (pieza real)", "Abrir gatoRL (pieza real)",
    "Abrir ABANICO EMILIA (pieza real)", "Abrir STEP ABANICO CORAZONES (6,8 MB)", "Abrir STEP Prusa Core One (95 MB)",
    "Insertar STEP ABANICO CORAZONES (6,8 MB)",
), strict=True))
# Piezas de Gerardo (fuera del repo): se copian a una carpeta temporal y, si falta el archivo, el escenario se omite con aviso.
PIEZAS_REALES = {
    "l": ("evidencias/motor_impreso/motor_impreso.omnicad", "~/OmniCAD/evidencias/motor_impreso/motor_impreso.omnicad"),
    "m": ("~/piezas/motor_cohete.omnicad",), "n": ("~/piezas/gatoRL.omnicad",),
    "o": ("~/piezas/ABANICO EMILIA.omnicad",),
    "p": ("~/piezas/ABANICO CORAZONES.step",),
    "q": ("evidencias/archivos_prueba/prusa_core_one.step", "~/OmniCAD/evidencias/archivos_prueba/prusa_core_one.step"),
    "r": ("~/piezas/ABANICO CORAZONES.step",),
}
STEPS = "pqr"           # B-335/B-337: abrir o insertar un STEP; el bloqueo se mide con un latido del bucle de eventos


def _latido():
    """Un temporizador de 10 ms: si el bucle se queda sin atender más de 100 ms, anota el hueco (lo que se vería congelado)."""
    ultimo = [time.perf_counter()]

    def tic():
        ahora = time.perf_counter()
        ms = (ahora - ultimo[0]) * 1000.0
        if ms > sonda.UMBRAL_MS or ms > 100:
            sonda.BLOQUEOS.append(("latido", round(ms), time.time()))
        ultimo[0] = ahora
    reloj = QTimer(interval=10)
    reloj.timeout.connect(tic)
    reloj.start()
    return reloj


def _cargar_ui():
    # El proceso coordinador y pytest no importan Qt: cada hijo configura su GL.
    sys.path.insert(0, str(RAIZ / "scripts" / "prueba_ui"))
    sys.path.insert(0, str(RAIZ / "clon"))
    global A, sonda, api, np, Qt, QEvent, QPoint, QPointF, QTimer, QMouseEvent, QTest, QApplication
    global QLineEdit, QScrollArea, QFileDialog, QDialog, QToolButton
    import arnes as A
    import sonda
    from omnicad import api
    import numpy as np
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QLineEdit, QScrollArea, QToolButton
    sonda.UMBRAL_MS = 0
    sonda.BLOQUEOS.clear()


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    if not respuesta["ok"]:
        raise RuntimeError(f"{nombre}({argumentos}): {respuesta}")
    return respuesta["result"]


def _cuerpo(sesion, herramienta="create_box", **argumentos):
    return _llamar(sesion, herramienta, **argumentos)["bodies_created"][0]["id"]


def _esperar(condicion, motivo, segundos=90):
    fin = time.perf_counter() + segundos
    while not condicion():
        if A.ERRORES:
            raise RuntimeError(A.ERRORES[-1])
        if time.perf_counter() >= fin:
            raise RuntimeError(f"Sin respuesta en {segundos} s: {motivo}")
        QTest.qWait(1)
        # QTest.qWait no suelta el GIL y frena los hilos de la app (FL-3b: mallar 23 cuerpos, 1,7 s → 24 s); la app real
        # espera en exec(), que sí lo suelta. Lo que tarda en volver es la ventana esperando el GIL: cuenta como bloqueo.
        antes = time.perf_counter()
        time.sleep(0.002)
        if (ms := (time.perf_counter() - antes) * 1000 - 2) > 50:
            sonda.BLOQUEOS.append(("GIL", round(ms), time.time()))


def _responde():
    marca = []
    QTimer.singleShot(0, lambda: marca.append(True))
    _esperar(lambda: bool(marca), "el bucle de eventos no responde")


@contextmanager
def _ventana(sesion):
    app, ventana = A.iniciar(sesion.doc, ancho=1500, alto=950)
    try:
        if not ventana.visor.isValid():
            raise RuntimeError("No hay contexto OpenGL válido: usar QT_QPA_PLATFORM=xcb + xvfb-run -a")
        sonda.BLOQUEOS.clear()  # La construcción API y el arranque no son la acción medida.
        yield ventana
    finally:
        if ventana.panel is not None:
            ventana.panel.cancelar()
        ventana.doc.modificado = False
        ventana.close()
        ventana.deleteLater()
        app.processEvents()


def _visible(widget):
    padre = widget.parentWidget()
    while padre is not None:
        if isinstance(padre, QScrollArea):
            padre.ensureWidgetVisible(widget)
        padre = padre.parentWidget()


def _teclear(widget, texto, enter=False):
    _visible(widget)
    QTest.mouseClick(widget, Qt.LeftButton)
    QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
    for caracter in texto:
        QTest.keyClicks(widget, caracter)
    QTest.keyClick(widget, Qt.Key_Return if enter else Qt.Key_Tab)


def _campo(panel, clave):
    widget = panel.widgets[clave]
    return widget if isinstance(widget, QLineEdit) else next(
        c for c in widget.findChildren(QLineEdit) if c.isVisible())


def _combo(widget, valor):
    indice = widget.findData(valor)
    if indice < 0:
        raise RuntimeError(f"No existe la opción {valor!r}")
    _visible(widget)
    if hasattr(widget, "boton"):
        QTest.mouseClick(widget.boton(valor), Qt.LeftButton)
        assert widget.currentData() == valor
        return
    widget.setFocus()
    QTest.keyClick(widget, Qt.Key_Home)
    for _ in range(indice):
        QTest.keyClick(widget, Qt.Key_Down)
    QTest.keyClick(widget, Qt.Key_Tab)
    assert widget.currentData() == valor, f"No se seleccionó {valor!r}: {widget.currentData()!r}"


def _casilla(widget, valor):
    if widget.isChecked() != valor:
        _visible(widget)
        # Clic sobre el cuadrito: sin texto, el centro del QCheckBox no cuenta. (Espacio no sirve: lo toma el atajo global.)
        QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, QPoint(8, 7))
    assert widget.isChecked() == valor, f"La casilla {widget.text()} no cambió a {valor}"


def _previa(panel, accion):
    # La señal nueva evita confundir _previa_ok=True de la entrada anterior.
    vistas = []
    inicio = time.perf_counter()

    def recibir(estado):
        if estado is not None and panel._previa_ok:
            vistas.append((time.perf_counter() - inicio) * 1000)

    panel.previa.connect(recibir)
    try:
        accion()
        _esperar(lambda: bool(vistas) and not panel._t_previa.isActive()
                 and panel._hijo_previa is None, f"previa: {panel.mensaje.text()}")
        if not panel._previa_ok:
            raise RuntimeError(f"Previa fallida: {panel.mensaje.text()}")
        return round(vistas[0], 2)
    finally:
        panel.previa.disconnect(recibir)


def _aceptar(v, panel):
    antes = len(v.doc.operaciones)
    _visible(panel.boton_ok)
    inicio = time.perf_counter()
    QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
    _esperar(lambda: len(v.doc.operaciones) == antes + 1 and v.panel is None, "Aceptar no agregó el paso")
    _responde()
    if A.MODALES:
        raise RuntimeError(f"Aceptar mostró un error: {A.MODALES}")
    return round((time.perf_counter() - inicio) * 1000, 2)


def _medir_panel(v, panel, clave, texto):
    previa = _previa(panel, lambda: _teclear(_campo(panel, clave), texto))
    return {"primera_previa_ms": previa, "aceptar_ms": _aceptar(v, panel)}


def _mouse(widget, tipo, punto, boton, botones, modificadores=None):
    p = QPointF(punto)
    QApplication.sendEvent(widget, QMouseEvent(tipo, p, widget.mapToGlobal(p), boton, botones,
                                              Qt.NoModifier if modificadores is None else modificadores))


def _arrastrar(widget, desde, hasta, pasos, boton=None, modificadores=None):
    boton = Qt.LeftButton if boton is None else boton
    _mouse(widget, QEvent.MouseButtonPress, desde, boton, boton, modificadores)
    tiempos = []
    for i in range(1, pasos + 1):
        p = desde + (hasta - desde) * (i / pasos)
        inicio = time.perf_counter()
        _mouse(widget, QEvent.MouseMove, p, Qt.NoButton, boton, modificadores)
        widget.repaint()  # Incluye pintar el cuadro, no solo encolar update().
        _responde()
        tiempos.append(round((time.perf_counter() - inicio) * 1000, 2))
    _mouse(widget, QEvent.MouseButtonRelease, hasta, boton, Qt.NoButton, modificadores)
    _responde()
    return tiempos


def _asa(panel, clave, desplazamiento):
    gestor = panel.manipuladores
    asa = next((m for m in gestor.manips if getattr(m, "clave", None) == clave), None)
    if asa is None:
        raise RuntimeError(f"No está el asa {clave}; longitud completa={panel.valores.get('largo_completo')}; "
                           f"asas={[getattr(m, 'clave', None) for m in gestor.manips]}")
    a, b = asa.puntos(gestor)
    desde = a if clave == "tam_iso_metrica" else (a + b) / 2
    xy, visibles = gestor.pantalla([desde, desde + asa.direccion * desplazamiento])
    if not visibles.all():
        raise RuntimeError(f"Asa {clave} fuera del visor")
    antes = panel.valores[clave]
    _arrastrar(panel.visor, QPointF(*xy[0]), QPointF(*xy[1]), 6)
    if panel.valores[clave] == antes:
        raise RuntimeError(f"Los eventos no arrastraron el asa {clave}")


def _boceto(s, nombre, entidades, plano="XY"):
    _llamar(s, "sketch_from_spec", name=nombre, plane=plano, entities=entidades)


def _texto(r):
    s = api.Sesion()
    for i in range(11):
        _cuerpo(s, length=100 if i == 0 else 12, width=24, height=5, x=i * 120)
    _llamar(s, "create_construction_plane", plane="XY", offset=5, name="Apoyo")
    _boceto(s, "Texto", [{"type": "text", "text": "FLUIDEZS", "font": "DejaVu Sans",
                            "height": 8, "x": -40, "y": 0}], "Apoyo")
    from omnicad.api.herramientas_boceto import boceto_activo, seleccionar_perfiles
    op, br = boceto_activo(s, "Texto")
    perfiles = seleccionar_perfiles(br, op, "text")
    assert len(perfiles) == 8, f"El texto produjo {len(perfiles)} perfiles, no 8"
    r["detalle"].update(cuerpos=11, perfiles=len(perfiles))
    with _ventana(s) as v:
        p = A.abrir(v, "extruir")
        A.elegir(p, "perfiles", *(A.hit_perfil(v, s, "Texto", i) for i in range(8)))
        _combo(p.widgets["operacion"], "unir")
        sonda.BLOQUEOS.clear()
        previas = {}
        for texto in ("0,5", "1", "2"):
            previas[texto] = _previa(p, lambda texto=texto: _teclear(_campo(p, "distancia"), texto))
        r["detalle"]["previas_ms"] = previas
        r["primera_previa_ms"] = max(previas.values())
        r["aceptar_ms"] = _aceptar(v, p)


def _rosca(r):
    s = api.Sesion()
    cid = _cuerpo(s, "create_cylinder", radius=10, height=60)
    with _ventana(s) as v:
        p = A.abrir(v, "rosca")
        A.elegir(p, "caras", A.hit_cara(v, cid))
        if p.seccion is not None:
            QTest.mouseClick(p.seccion.boton, Qt.LeftButton)
        _casilla(p.widgets["modelada"], True)
        _casilla(p.widgets["largo_completo"], False)
        _combo(p.widgets["tam_iso_metrica"], "M20")
        _teclear(_campo(p, "longitud"), "60")
        _esperar(lambda: not p._t_previa.isActive() and p._hijo_previa is None, "rosca inicial")
        if not p._previa_ok:
            raise RuntimeError(p.mensaje.text())
        sonda.BLOQUEOS.clear()
        previas = r["detalle"]["previas_ms"] = {}
        previas["arrastrar_tamano"] = _previa(p, lambda: _asa(p, "tam_iso_metrica", 1))
        caja = p.manipuladores.cajas["tam_iso_metrica"]
        previas["teclear_radio_10"] = _previa(p, lambda: _teclear(caja, "10", enter=True))
        _casilla(p.widgets["largo_completo"], False)
        _responde()
        previas["arrastrar_longitud"] = _previa(p, lambda: _asa(p, "longitud", -10))
        previas["teclear_longitud_60"] = _previa(p, lambda: _teclear(_campo(p, "longitud"), "60"))
        r["detalle"]["previas_ms"] = previas
        r["primera_previa_ms"] = max(previas.values())
        r["aceptar_ms"] = _aceptar(v, p)


def _empalme(r):
    s = api.Sesion()
    # Estrella de 198 lados: un polígono regular casi liso (178°) no se puede empalmar («no pertenecen al cuerpo»).
    radios = [150 if i % 2 == 0 else 140 for i in range(198)]
    puntos = [(r_ * np.cos(2 * np.pi * i / 198), r_ * np.sin(2 * np.pi * i / 198)) for i, r_ in enumerate(radios)]
    _boceto(s, "Poligono", [{"type": "line", "start": a, "end": b}
                             for a, b in zip(puntos, puntos[1:] + puntos[:1], strict=True)])
    cid = _cuerpo(s, "extrude", sketch="Poligono", distance=30)
    from omnicad.nucleo import geometria as geo
    r["detalle"]["caras"] = len(geo.caras(s.cuerpo(cid).forma))
    assert r["detalle"]["caras"] == 200
    with _ventana(s) as v:
        p = A.abrir(v, "empalme_3d")
        from omnicad.nucleo import referencias as refs
        from omnicad.ui.comando import hit_desde_ref
        forma = s.cuerpo(cid).forma
        aristas = [a for a in refs.subformas(forma, "arista")
                   if abs(refs.direccion_curva(a)[2]) > 0.99]
        # La selección prepara la escena: el pick del arnés confunde las aristas tan juntas.
        hit = hit_desde_ref(refs.referencia(cid, aristas[0], forma), v.doc.estado_final)
        A.elegir(p, "aristas", hit)
        sonda.BLOQUEOS.clear()
        r.update(_medir_panel(v, p, "radio", "2"))


def _desfase(r):
    s = api.Sesion()
    cid = _cuerpo(s, length=40, width=30, height=20)
    with _ventana(s) as v:
        p = A.abrir(v, "desfase_cara")
        A.elegir(p, "caras", A.hit_cara(v, cid, normal=(0, 0, 1)))
        sonda.BLOQUEOS.clear()
        r.update(_medir_panel(v, p, "distancia", "3"))


def _crear(r):
    s = api.Sesion()
    _boceto(s, "Perfil", [{"type": "circle", "center": [0, 0], "radius": 3}])
    _boceto(s, "Ruta", [{"type": "line", "start": [0, 0], "end": [0, 40]}], "YZ")
    _llamar(s, "create_construction_plane", plane="XY", offset=40, name="Arriba")
    _boceto(s, "Seccion", [{"type": "circle", "center": [0, 0], "radius": 7}], "Arriba")
    medidas = r["detalle"]["submedidas"] = {}
    errores = []
    with _ventana(s) as v:
        for clave in ("barrido", "bobina", "solevacion"):
            try:
                p = A.abrir(v, clave)
                if clave == "barrido":
                    A.elegir(p, "perfiles", A.hit_perfil(v, s, "Perfil"))
                    A.elegir(p, "ruta", A.hit_curva(v, s, "Ruta"))
                    campo, valor = "torsion", "30"
                elif clave == "bobina":
                    A.elegir(p, "plano", A.hit_plano(v, "XY"))
                    for campo, valor in (("diametro", "20"), ("revoluciones", "3"), ("tamano", "2")):
                        _teclear(_campo(p, campo), valor)
                    campo, valor = "altura", "30"
                else:
                    A.elegir(p, "secciones", A.hit_perfil(v, s, "Perfil"), A.hit_perfil(v, s, "Seccion"))
                    tabla = p.widgets["secciones"].tabla
                    QTest.mouseClick(tabla.viewport(), Qt.LeftButton, pos=tabla.visualItemRect(tabla.item(0, 0)).center())
                    _combo(tabla.cellWidget(0, 1), "direccion")
                    campo, valor = "angulo_inicio", "10"
                _combo(p.widgets["operacion"], "nuevo")
                medidas[clave] = _medir_panel(v, p, campo, valor)
            except Exception as exc:
                medidas[clave] = {"error": f"{type(exc).__name__}: {exc}"}
                errores.append(f"{clave}: {exc}")
                if v.panel is not None:
                    v.panel.cancelar()
    for metrica in METRICAS[1:]:
        valores = [m[metrica] for m in medidas.values() if metrica in m]
        r[metrica] = max(valores) if valores else None
    if errores:
        r["error"] = "; ".join(errores)


def _combinar(r):
    s = api.Sesion()
    a = _cuerpo(s, length=40, width=30, height=20)
    b = _cuerpo(s, "create_cylinder", radius=12, height=30, x=15)
    with _ventana(s) as v:
        p = A.abrir(v, "combinar")
        A.elegir(p, "objetivo", A.hit_cuerpo(v, a))
        A.elegir(p, "herramientas", A.hit_cuerpo(v, b))
        # El combo dispara la previa, no se llama al kernel desde el banco.
        _combo(p.widgets["operacion"], "cortar")
        _esperar(lambda: not p._t_previa.isActive() and p._hijo_previa is None, "combinar inicial")
        sonda.BLOQUEOS.clear()
        r["primera_previa_ms"] = _previa(p, lambda: _combo(p.widgets["operacion"], "unir"))
        r["aceptar_ms"] = _aceptar(v, p)


def _item(v, ident):
    lista = v.timeline.lista
    item = next(lista.item(i) for i in range(lista.count()) if lista.item(i).data(Qt.UserRole) == ident)
    lista.scrollToItem(item)
    _responde()
    return lista.viewport(), lista.visualItemRect(item).center()


def _eliminar(r):
    s = api.Sesion()
    for i in range(20):
        _cuerpo(s, length=10, width=10, height=10, x=i * 14)
    r["detalle"]["pasos_iniciales"] = len(s.doc.operaciones)
    ident = s.doc.operaciones[10].id
    with _ventana(s) as v:
        widget, punto = _item(v, ident)
        QTest.mouseClick(widget, Qt.LeftButton, pos=punto)
        sonda.BLOQUEOS.clear()
        inicio = time.perf_counter()
        QTest.keyClick(widget, Qt.Key_Delete)
        _esperar(lambda: len(v.doc.operaciones) == 19, "Supr no eliminó el paso")
        _responde()
        r["detalle"]["eliminar_ms"] = round((time.perf_counter() - inicio) * 1000, 2)


def _aceptar_deshacer(v, cid, r):
    """FL-3b: Mover/copiar un cuerpo, Aceptar, Deshacer y Rehacer, cada uno con su tiempo (incluye el cálculo aparte)."""
    p = A.abrir(v, "mover_copiar")
    A.elegir(p, "cuerpos", A.hit_cuerpo(v, cid))
    _teclear(_campo(p, "dz"), "5")
    _esperar(lambda: not p._t_previa.isActive() and p._hijo_previa is None, "previa de Mover")
    sonda.BLOQUEOS.clear()
    medidas = r["detalle"]["submedidas"] = {"aceptar_ms": _aceptar(v, p)}
    pasos = len(v.doc.operaciones)
    for nombre, accion, quedan in (("deshacer_ms", "deshacer", pasos - 1), ("rehacer_ms", "rehacer", pasos)):
        # la acción del menú y no Ctrl+Z: con la ventana minimizada el atajo no siempre llega; la sonda no mide trigger()
        inicio = time.perf_counter()
        v.acciones[accion].trigger()
        if (ms := (time.perf_counter() - inicio) * 1000) > sonda.UMBRAL_MS:
            sonda.BLOQUEOS.append((f"{accion}.trigger", round(ms), time.time()))
        _esperar(lambda q=quedan: len(v.doc.operaciones) == q and not v.doc._esperando_hijo, f"{nombre} no terminó")
        _responde()
        medidas[nombre] = round((time.perf_counter() - inicio) * 1000, 2)
    r["aceptar_ms"] = medidas["aceptar_ms"]


def _aceptar_20(r):
    s = api.Sesion()
    for i in range(20):
        cid = _cuerpo(s, length=10, width=10, height=10, x=i * 14)
    with _ventana(s) as v:
        _aceptar_deshacer(v, cid, r)


def _aceptar_motor(r):
    def despues(v):
        _aceptar_deshacer(v, next(iter(v.doc.estado_final.cuerpos)), r)
    _pieza_real("l", despues)(r)


def _abrir(r):
    s = api.Sesion()
    base = _cuerpo(s, length=300, width=180, height=8)
    for i in range(72):
        x, y = -130 + (i % 12) * 23, -65 + (i // 12) * 25
        cid = _cuerpo(s, "create_cylinder", radius=6, height=16, x=x, y=y, z=7)
        if i == 0:
            _llamar(s, "create_thread", body=cid, faces="%CYLINDER", modeled=True,
                    thread="M12x1.75", thread_class="")
        else:
            _llamar(s, "fillet", body=cid, edges=">Z", radius=1)
        _llamar(s, "boolean_operation", target=base, tools=[cid])
    r["detalle"].update(sustituto=True, motivo="motor_impreso no está en esta máquina",
                        combinar=72, pasos=len(s.doc.operaciones), roscas=1, empalmes=71)
    with tempfile.TemporaryDirectory(prefix="fluidez_", dir=RAIZ / "evidencias") as carpeta:
        ruta = Path(carpeta) / "sustituto_motor_impreso.omnicad"
        _llamar(s, "save_document", path=str(ruta))
        r["detalle"]["bytes_proyecto"] = ruta.stat().st_size
        vacia = api.Sesion()
        with _ventana(vacia) as v:
            QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(ruta), ""))
            sonda.BLOQUEOS.clear()
            inicio = time.perf_counter()
            QTest.keyClick(v, Qt.Key_O, Qt.ControlModifier)
            _esperar(lambda: len(v.doc.operaciones) == len(s.doc.operaciones), "Abrir no cargó el sustituto")
            _responde()
            r["detalle"]["abrir_ms"] = round((time.perf_counter() - inicio) * 1000, 2)


def _preferencias(r):
    s = api.Sesion()
    _cuerpo(s, length=30, width=20, height=10)
    with _ventana(s) as v:
        # El arnés evita exec() bloqueante; aquí lo muestra para poder enviar eventos.
        QDialog.exec = lambda dlg: (A.mostrar(dlg), 0)[1]
        sonda.BLOQUEOS.clear()
        inicio = time.perf_counter()
        boton = next(b for b in v.findChildren(QToolButton) if b.defaultAction() is v.acciones["preferencias"])
        QTest.mouseClick(boton, Qt.LeftButton)
        _responde()
        from omnicad.ui.preferencias import DialogoPreferencias
        dlg = v.findChild(DialogoPreferencias)
        if dlg is None or not dlg.isVisible():
            raise RuntimeError("Preferencias no se abrió")
        r["detalle"]["abrir_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
        item = dlg._items["apariencia"]
        dlg.arbol.scrollToItem(item)
        QTest.mouseClick(dlg.arbol.viewport(), Qt.LeftButton, pos=dlg.arbol.visualItemRect(item).center())
        _responde()
        deslizador = dlg.controles["interfaz/tamano_pct"]
        antes = deslizador.value()
        tiempos = _arrastrar(deslizador, QPointF(deslizador.width() / 3, deslizador.height() / 2),
                             QPointF(deslizador.width() * 2 / 3, deslizador.height() / 2), 10)
        if deslizador.value() == antes:
            QTest.keyClick(deslizador, Qt.Key_Right)
        combo = dlg.controles["interfaz/perfil"]
        _combo(combo, "lectura_comoda")
        assert combo.currentData() == "lectura_comoda" and deslizador.value() != antes
        r["detalle"]["eventos_deslizador_ms"] = tiempos
        QTest.mouseClick(dlg.b_cancelar, Qt.LeftButton)


def _punto(r):
    s = api.Sesion()
    _boceto(s, "Doscientas", [{"type": "line", "start": [i % 20 * 6, i // 20 * 6],
                              "end": [i % 20 * 6 + 4, i // 20 * 6 + 2]} for i in range(200)])
    with _ventana(s) as v:
        widget, punto = _item(v, s.paso("Doscientas").id)
        QTest.mouseClick(widget, Qt.LeftButton, pos=punto)
        QTest.mouseDClick(widget, Qt.LeftButton, pos=punto)
        _esperar(lambda: v.modo_boceto.activo, "el boceto no se abrió")
        lienzo = v.modo_boceto.lienzo
        v.visor.encuadrar()
        _responde()
        curva = list(lienzo.b.curvas.values())[105]
        pid = curva.p1
        antes = lienzo.b.coords(pid)
        desde = lienzo.a_px(*antes)
        hasta = desde + QPointF(35, -20)
        sonda.BLOQUEOS.clear()
        tiempos = _arrastrar(lienzo, desde, hasta, 30)
        assert np.linalg.norm(np.array(lienzo.b.coords(pid)) - antes) > 0.1, "El punto no se movió"
        r["detalle"].update(entidades=len(lienzo.b.curvas), movimientos=30, eventos_ms=tiempos,
                            evento_max_ms=max(tiempos), cuadros_s=round(1000 / statistics.mean(tiempos), 2))
        v.modo_boceto.cancelar()


def _orbita(r):
    s = api.Sesion()
    with tempfile.TemporaryDirectory(prefix="fluidez_", dir=RAIZ / "evidencias") as carpeta:
        ruta = Path(carpeta) / "malla.obj"
        nx, ny = 500, 300
        with ruta.open("w", encoding="utf-8") as archivo:
            for j in range(ny + 1):
                for i in range(nx + 1):
                    archivo.write(f"v {i / 5} {j / 5} {2 * np.sin(i / 20) * np.cos(j / 20)}\n")
            for j in range(ny):
                for i in range(nx):
                    a = j * (nx + 1) + i + 1
                    b = a + nx + 1
                    archivo.write(f"f {a} {a + 1} {b}\nf {a + 1} {b + 1} {b}\n")
        _llamar(s, "open_document", path=str(ruta))
        with _ventana(s) as v:
            malla = next(iter(v.doc.estado_final.cuerpos.values())).forma
            assert len(malla.caras) == 300000
            antes = v.visor.R.copy()
            centro = QPointF(v.visor.rect().center())
            sonda.BLOQUEOS.clear()
            tiempos = _arrastrar(v.visor, centro, centro + QPointF(180, 60), 40,
                                 Qt.MiddleButton, Qt.ShiftModifier)
            assert not np.allclose(antes, v.visor.R), "Los eventos no cambiaron la órbita"
            r["detalle"].update(triangulos=len(malla.caras), movimientos=40, eventos_ms=tiempos,
                                evento_max_ms=max(tiempos), cuadros_s=round(1000 / statistics.mean(tiempos), 2))


def _pieza_real(letra, despues=None):
    def correr(r):
        ruta = next((c for c in (RAIZ / Path(x).expanduser() if not x.startswith("~") else Path(x).expanduser()
                                 for x in PIEZAS_REALES[letra]) if c.is_file()), None)
        if ruta is None:
            r["omitido"] = "falta el archivo: " + " | ".join(PIEZAS_REALES[letra])
            print(f"AVISO fluidez {letra}: {r['omitido']}", file=sys.stderr, flush=True)
            return
        with tempfile.TemporaryDirectory(prefix="fluidez_real_", dir=RAIZ / "evidencias") as carpeta:
            copia = Path(carpeta) / ruta.name
            copia.write_bytes(ruta.read_bytes())
            r["detalle"].update(archivo=str(ruta), bytes_proyecto=copia.stat().st_size)
            with _ventana(api.Sesion()) as v:
                QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(copia), ""))
                sonda.BLOQUEOS.clear()
                latido = _latido() if letra in STEPS else None
                if os.environ.get("OMNICAD_TRAZA"):       # pila del hilo principal cada segundo: dónde se traba
                    import faulthandler
                    faulthandler.dump_traceback_later(1, repeat=True, file=open(os.environ["OMNICAD_TRAZA"], "w"))
                inicio = time.perf_counter()
                if letra == "r":                          # Insertar STEP: el documento ya existe, se suma un paso
                    v.importar_step()
                else:
                    QTest.keyClick(v, Qt.Key_O, Qt.ControlModifier)
                _esperar(lambda: len(v.doc.operaciones) > 0, "Abrir no cargó la pieza", segundos=1100)
                _responde()
                if latido is not None:
                    latido.stop()
                r["detalle"]["abrir_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
                r["detalle"]["pasos"] = len(v.doc.operaciones)
                if despues is not None:
                    despues(v)
    return correr


def _escenario(letra, funcion):
    _cargar_ui()
    r = {"escenario": letra, "titulo": TITULOS[letra], **dict.fromkeys(METRICAS), "detalle": {}}
    try:
        funcion(r)
        if A.ERRORES or A.MODALES:
            raise RuntimeError(f"Excepciones Qt: {A.ERRORES}; diálogos: {A.MODALES}")
    except Exception as exc:
        r["error"] = f"{type(exc).__name__}: {exc}"
        r["detalle"]["traza"] = traceback.format_exc()
    r["bloqueo_max_ms"] = max((b[1] for b in sonda.BLOQUEOS), default=0)
    r["detalle"]["peores_bloqueos"] = sorted(sonda.BLOQUEOS, key=lambda b: -b[1])[:10]
    # repaint() directo del banco no pasa por la sonda: incluir el ciclo de cada cuadro.
    if "evento_max_ms" in r["detalle"]:
        r["bloqueo_max_ms"] = max(r["bloqueo_max_ms"], r["detalle"]["evento_max_ms"])
    return r


def escenario_a():
    """Extruye ocho letras, tres distancias y Aceptar."""
    return _escenario("a", _texto)


def escenario_b():
    """Cambia tamaño y longitud de una rosca con asas y teclado."""
    return _escenario("b", _rosca)


def escenario_c():
    """Redondea una arista de un sólido de doscientas caras."""
    return _escenario("c", _empalme)


def escenario_d():
    """Desplaza una cara y acepta el paso."""
    return _escenario("d", _desfase)


def escenario_e():
    """Mide barrido, bobina y solevación por separado."""
    return _escenario("e", _crear)


def escenario_f():
    """Une dos sólidos desde el panel Combinar."""
    return _escenario("f", _combinar)


def escenario_g():
    """Elimina con Supr un paso intermedio del timeline."""
    return _escenario("g", _eliminar)


def escenario_h():
    """Guarda y abre un sustituto pesado con setenta y dos uniones."""
    return _escenario("h", _abrir)


def escenario_i():
    """Abre Preferencias y mueve un deslizador y un combo."""
    return _escenario("i", _preferencias)


def escenario_j():
    """Arrastra un punto de un boceto de doscientas líneas."""
    return _escenario("j", _punto)


def escenario_k():
    """Orbita una malla de trescientos mil triángulos."""
    return _escenario("k", _orbita)


ESCENARIOS = dict(zip("abcdefghijk", (escenario_a, escenario_b, escenario_c, escenario_d, escenario_e,
                                     escenario_f, escenario_g, escenario_h, escenario_i, escenario_j,
                                     escenario_k), strict=True))
for _letra in PIEZAS_REALES:
    ESCENARIOS[_letra] = (lambda letra: lambda: _escenario(letra, _pieza_real(letra)))(_letra)
# FL-3b (s, t): letras aparte de las que suma B-337 (p a r)
TITULOS.update(s="Aceptar, deshacer y rehacer · 20 pasos", t="Aceptar, deshacer y rehacer en motor_impreso (pieza real)")
ESCENARIOS["s"] = lambda: _escenario("s", _aceptar_20)
ESCENARIOS["t"] = lambda: _escenario("t", _aceptar_motor)


def correr_aislado(letra):
    """Una corrida en proceso propio; mata su grupo si excede trescientos segundos."""
    comando = [sys.executable, str(Path(__file__).resolve()), "--hijo", letra]
    with tempfile.TemporaryDirectory(prefix="fluidez_proceso_", dir=RAIZ / "evidencias") as carpeta:
        entorno = dict(os.environ, OMNICAD_CODIGO=str(RAIZ / "clon"), OMNICAD_FLUIDEZ="aviso",
                       OMNICAD_ASISTENTE_DIR=carpeta, OMNICAD_PREAJUSTES=str(Path(carpeta) / "preajustes.json"))
        with subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                              env=entorno, start_new_session=os.name != "nt") as proceso:
            try:
                salida, errores = proceso.communicate(timeout=TOPE_SEGUNDOS)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(proceso.pid)], capture_output=True)
                else:
                    os.killpg(proceso.pid, signal.SIGKILL)
                salida, errores = proceso.communicate()
                return {"escenario": letra, "titulo": TITULOS[letra], **dict.fromkeys(METRICAS),
                        "colgado": True, "error": "El proceso excedió 300 s", "detalle": {"salida": salida[-4000:], "stderr": errores[-4000:]}}
        for linea in reversed(salida.splitlines()):
            if linea.startswith("FLUIDEZ_JSON="):
                resultado = json.loads(linea.removeprefix("FLUIDEZ_JSON="))
                if proceso.returncode:
                    resultado["error"] = f"Salida {proceso.returncode}: {errores[-4000:]}"
                return resultado
        return {"escenario": letra, "titulo": TITULOS[letra], **dict.fromkeys(METRICAS),
                "error": f"Proceso sin resultado (salida {proceso.returncode})", "detalle": {"salida": salida[-4000:], "stderr": errores[-4000:]}}


def resumir(corridas):
    """Medianas por métrica; ninguna corrida fallida se oculta tras la mediana."""
    r = {"escenario": corridas[0]["escenario"], "titulo": corridas[0]["titulo"], "detalle": {"corridas": corridas}}
    for metrica in METRICAS:
        valores = [c[metrica] for c in corridas if c.get(metrica) is not None]
        r[metrica] = round(statistics.median(valores), 2) if valores else None
    errores = [c["error"] for c in corridas if "error" in c]
    if errores:
        r["error"] = " | ".join(dict.fromkeys(errores))
    if any(c.get("colgado") for c in corridas):
        r["colgado"] = True
    if all("omitido" in c for c in corridas):
        r["omitido"] = corridas[0]["omitido"]
    return r


def main():
    """CLI del banco, serial por escenario y repetición."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("letras", nargs="*", help="escenarios a–o, s y t (l–o y t: piezas reales); por defecto todos")
    parser.add_argument("--json", type=Path, help="archivo de resultados y corridas originales")
    parser.add_argument("--rep", type=int, default=3, help="repeticiones por escenario (mediana; predeterminado: 3)")
    parser.add_argument("--hijo", choices=ESCENARIOS, help=argparse.SUPPRESS)
    opciones = parser.parse_args()
    if opciones.hijo:
        print("FLUIDEZ_JSON=" + json.dumps(ESCENARIOS[opciones.hijo](), ensure_ascii=False), flush=True)
        return 0
    letras = opciones.letras or list(ESCENARIOS)
    if opciones.rep < 1 or any(letra not in ESCENARIOS for letra in letras):
        parser.error("usar letras a–o, s o t y --rep mayor que cero")
    if sys.platform != "win32" and (os.environ.get("QT_QPA_PLATFORM") != "xcb" or not os.environ.get("DISPLAY")):
        parser.error("El visor exige QT_QPA_PLATFORM=xcb + xvfb-run -a (o DISPLAY real); offscreen no sirve")
    (RAIZ / "evidencias").mkdir(exist_ok=True)
    resultados = []
    print("Escenario | Bloqueo máx. ms | Primera previa ms | Aceptar ms | Estado", flush=True)
    for letra in letras:
        corridas = []
        for repeticion in range(opciones.rep):
            print(f"Midiendo {letra}, corrida {repeticion + 1}/{opciones.rep}…", flush=True)
            corridas.append(correr_aislado(letra))
        r = resumir(corridas)
        resultados.append(r)
        cifras = " | ".join("—" if r[m] is None else f"{r[m]:.2f}" for m in METRICAS)
        print(f"{letra}) {r['titulo']} | {cifras} | {r.get('error', 'OMITIDO: ' + r['omitido'] if 'omitido' in r else 'OK')}", flush=True)
        if opciones.json:
            opciones.json.write_text(json.dumps({"fecha": date.today().isoformat(), "nucleos": os.cpu_count(),
                                                 "repeticiones": opciones.rep, "resultados": resultados},
                                                ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any("error" in r for r in resultados))


if __name__ == "__main__":
    sys.exit(main())
