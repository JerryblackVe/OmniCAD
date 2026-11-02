# -*- coding: utf-8 -*-
"""Capa D de la caza: eventos simulados al azar sobre cada comando del CATALOGO, con la ventana real minimizada.

Clics en el visor, elegir, teclear, Enter, Esc, Tab y arrastrar, siempre por eventos al widget: el cursor real no se
mueve y la PC se puede seguir usando. Falla si se escapa una excepción de un slot de Qt o si el panel queda trabado."""
import json
import os
import random
import re
import sys
import tempfile
from pathlib import Path

os.environ["OMNICAD_PRUEBA_VENTANA"] = "minimizada"
os.environ.setdefault("OMNICAD_PRUEBA_SALIDA", tempfile.mkdtemp(prefix="caza_ventana_"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prueba_ui"))

import arnes as A  # noqa: E402
import escena  # noqa: E402
import jueces as j  # noqa: E402
from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLineEdit  # noqa: E402
from omnicad.ui.comando import Seleccion  # noqa: E402
from teclado import teclear  # noqa: E402

TEXTOS = ("15", "15 mm", "2,5", "0", "-5", "1e9", "abc", "", "1/0", "45 deg", "ancho*2")
PREVIA_MS = 200             # lo que espera una persona a ver la vista previa de lo que tecleó
ANGULOS_ENORMES = ("1e9 deg", "1e9", "-1e9 deg")
ESTADO = {}


def _vivo(p):
    try:
        return p.isVisible()
    except RuntimeError:          # el panel ya se destruyó al cerrarse
        return False


def _evento(w, tipo, q, boton, botones):
    QApplication.sendEvent(w, QMouseEvent(tipo, q, w.mapToGlobal(q), boton, botones, Qt.NoModifier))


def _punto(rng, w):
    return QPointF(rng.uniform(10, max(w.width() - 10, 11)), rng.uniform(10, max(w.height() - 10, 11)))


def clic_visor(p, rng, _ev):
    q = _punto(rng, A_V().visor)
    _evento(A_V().visor, QEvent.MouseButtonPress, q, Qt.LeftButton, Qt.LeftButton)
    _evento(A_V().visor, QEvent.MouseButtonRelease, q, Qt.LeftButton, Qt.NoButton)


def arrastrar(p, rng, _ev):
    vis = A_V().visor
    a, b = _punto(rng, vis), _punto(rng, vis)
    _evento(vis, QEvent.MouseMove, a, Qt.NoButton, Qt.NoButton)
    _evento(vis, QEvent.MouseButtonPress, a, Qt.LeftButton, Qt.LeftButton)
    for i in range(1, 5):
        _evento(vis, QEvent.MouseMove, a + (b - a) * (i / 4), Qt.NoButton, Qt.LeftButton)
    _evento(vis, QEvent.MouseButtonRelease, b, Qt.LeftButton, Qt.NoButton)


def elegir_en(p, c, rng, ev):
    """Elige en el campo algo de lo que pide: el visor no deja elegir otra cosa."""
    v, ids, s = A_V(), ESTADO["ids"], ESTADO["sesion"]
    hits = [lambda: A.hit_cara(v, ids["caja"]), lambda: A.hit_arista(v, ids["caja"]), lambda: A.hit_cuerpo(v, ids["caja"]),
            lambda: A.hit_plano(v, "XY"), lambda: A.hit_perfil(v, s, "Rect"), lambda: A.hit_eje(v, "X"),
            lambda: A.hit_curva(v, s, "Lin")]
    rng.shuffle(hits)
    for hit in hits:
        h = hit()
        if h and h["ref"].get("tipo") in c.filtros:
            ev.append(f"elegir {c.clave}")
            A.elegir(p, c.clave, h)
            return


def _selecciones(p):
    return [c for c in p.campos if isinstance(c, Seleccion) and p._visible(c)]


def elegir(p, rng, ev):
    if _selecciones(p):
        elegir_en(p, rng.choice(_selecciones(p)), rng, ev)


def llenar_selecciones(p, rng, ev):
    """Como una persona, primero elige lo que pide el comando: recién ahí hay vista previa y asas que probar."""
    for c in _selecciones(p):
        try:
            elegir_en(p, c, rng, ev)
        except Exception as e:  # noqa: BLE001 — un fallo del cazador al armar el evento no es del programa
            ev.append(f"sin_efecto:{type(e).__name__}")


def escribir(p, rng, ev):
    claves = [k for k, w in p.widgets.items() if isinstance(w, QLineEdit) and w.isVisible()]
    if claves:
        clave = rng.choice(claves)
        angulo = next((c for c in p.campos if c.clave == clave and str(getattr(c, "tipo", "")).lower() == "angulo"), None)
        texto = rng.choice(ANGULOS_ENORMES) if angulo and rng.random() < 0.4 else rng.choice(TEXTOS)
        ev.append(f"teclear {clave}={texto!r}")
        teclear(p, clave, texto)
        A.esperar(PREVIA_MS)


def tecla(p, rng, ev):
    t = rng.choice((Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Return, Qt.Key_Escape))
    ev.append(f"tecla {t.name}")
    QTest.keyClick(p, t)


def opcion(p, rng, ev):
    c = next((c for c in rng.sample(p.campos, len(p.campos)) if type(c).__name__ == "Opciones" and p._visible(c)), None)
    w = p.widgets.get(c.clave) if c else None
    if w is not None and hasattr(w, "count") and w.count():
        i = rng.randrange(w.count())
        ev.append(f"opción {c.clave}={i}")
        w.setCurrentIndex(i)


ACCIONES = (elegir, elegir, escribir, escribir, tecla, opcion, clic_visor, arrastrar)


def A_V():
    if "v" not in ESTADO:
        s, ids = escena.construir()
        _app, v = A.iniciar(s.doc, 1280, 800)
        ESTADO.update(v=v, ids=ids, sesion=s, base=A.n_ops(v))
    return ESTADO["v"]


def caso(ped):
    v, rng, eventos = A_V(), random.Random(ped["semilla"]), []
    A.ERRORES.clear()
    A.MODALES.clear()
    p = A.abrir(v, ped["clave"])
    if p is not None and hasattr(p, "campos"):
        llenar_selecciones(p, rng, eventos)
        for _ in range(rng.randint(3, 9)):
            if not _vivo(p):
                break
            accion = rng.choice(ACCIONES)
            eventos.append(accion.__name__)
            try:
                accion(p, rng, eventos)
            except Exception as e:  # noqa: BLE001 — un fallo del cazador al armar el evento no es del programa
                eventos.append(f"sin_efecto:{type(e).__name__}")
            A.esperar(20)
    falla = None
    if p is not None and _vivo(p):
        QTest.keyClick(p, Qt.Key_Escape)
        A.esperar(30)
        if _vivo(p):
            p.cancelar()
            A.esperar(30)
        if _vivo(p):
            falla = {"juez": "slot", "op": ped["clave"], "kind": "panel_trabado", "detalle": "Esc y Cancelar no lo cierran"}
    while A.n_ops(v) > ESTADO["base"] and v.acciones["deshacer"].isEnabled():
        v.acciones["deshacer"].trigger()
        A.esperar(30)
    falla = falla or j.juez_memoria(ped["clave"])
    if A.ERRORES:
        ultimo = A.ERRORES[0]
        donde = re.findall(r'File "[^"]*omnicad[\\/]([^"]+)", line (\d+)', ultimo)
        lugar = f"{Path(donde[-1][0]).name}:{donde[-1][1]}" if donde else ""
        tipo = ultimo.strip().splitlines()[-1].split(":")[0]
        falla = {"juez": "slot", "op": "", "kind": f"{tipo}@{lugar}", "detalle": f"{ped['clave']}: {ultimo[-300:]}"}
    return {"fallo": falla, "eventos": eventos}


def catalogo(_ped):
    from omnicad.ui.comandos import CATALOGO
    return {"claves": sorted(CATALOGO)}


def principal():
    salida = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
    os.dup2(2, 1)
    j.vigilar_memoria()
    atender = {"caso": caso, "catalogo": catalogo}
    for linea in sys.stdin:
        ped = json.loads(linea)
        salida.write(json.dumps(atender[ped["tipo"]](ped), ensure_ascii=False, default=str) + "\n")


if __name__ == "__main__":
    principal()
