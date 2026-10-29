# -*- coding: utf-8 -*-
"""Arnés para manejar la ventana REAL de OmniCAD (prueba omnicad-test, vía «usuario»). No toca el código del programa.

Abre VentanaPrincipal con un documento armado por la API, y deja ejecutar comandos como los ejecuta una persona:
v.ejecutar_comando(...) → PanelComando → elegir con el visor → cambiar valores → aceptar / cancelar / editar / deshacer.
Corre con QT_QPA_PLATFORM=windows (fuentes reales). No usar el ratón mientras corre."""
import faulthandler
import json
import os
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows")
os.environ.setdefault("OMNICAD_SIN_ANIMACION", "1")      # las pruebas esperan cada vista al instante
# Los chats del Asistente que guardan las piezas van a una carpeta temporal, nunca al historial del usuario.
os.environ.setdefault("OMNICAD_ASISTENTE_DIR", tempfile.mkdtemp(prefix="omnicad_ui_chats_"))
faulthandler.enable()          # un cierre brusco del programa deja el rastro nativo en el log
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "clon"))
# Carpeta de evidencia (fuera de git): OMNICAD_PRUEBA_SALIDA o evidencias/ui_<hoy>.
SALIDA = Path(os.environ.get("OMNICAD_PRUEBA_SALIDA") or RAIZ / "evidencias" / f"ui_{date.today().isoformat()}")
CAPTURAS = SALIDA / "capturas"
CAPTURAS.mkdir(parents=True, exist_ok=True)

import numpy as np  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtGui import QSurfaceFormat  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMenu, QMessageBox  # noqa: E402

from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo import referencias as refs  # noqa: E402

REGISTRO = []
MODALES = []
MENUS = []              # menús emergentes que se «abrieron» (QMenu.exec bloquearía): el último es MENUS[-1]
ERRORES = []            # excepciones que se escaparon dentro de un slot de Qt (la persona vería la app fallar)


def _gancho_excepciones(tipo, valor, tb):
    ERRORES.append("".join(traceback.format_exception(tipo, valor, tb))[-900:])
    sys.__excepthook__(tipo, valor, tb)


sys.excepthook = _gancho_excepciones


def reg(area, que, ok, detalle=""):
    REGISTRO.append({"area": area, "que": que, "ok": bool(ok), "detalle": str(detalle)})
    print(f"[{'OK ' if ok else 'XX '}] {area} · {que}" + (f" — {detalle}" if detalle else ""), flush=True)


def guardar_registro(nombre):
    (SALIDA / f"{nombre}.json").write_text(json.dumps(REGISTRO, ensure_ascii=False, indent=1), encoding="utf-8")


def _modal(tipo):
    def f(*a, **k):
        MODALES.append((tipo, " | ".join(str(x) for x in a[1:3])))
        return QMessageBox.Ok
    return staticmethod(f)


def parchar_modales():
    """Un diálogo modal cuelga el script: se anota y se devuelve enseguida."""
    for nombre in ("information", "warning", "critical", "question"):
        setattr(QMessageBox, nombre, _modal(nombre))
    QDialog.exec = lambda self: (MODALES.append(("exec", type(self).__name__)), 0)[1]
    # QMenu.exec bloquea: los módulos de la app (que se importan DESPUÉS) reciben una subclase que deja el menú a mano.
    import PySide6.QtWidgets as _qw

    class MenuPrueba(QMenu):
        def exec(self, *a, **k):
            MENUS.append(self)
            return None

    _qw.QMenu = MenuPrueba
    for nombre in ("getOpenFileName", "getSaveFileName", "getExistingDirectory", "getOpenFileNames"):
        setattr(QFileDialog, nombre, staticmethod(lambda *a, **k: ("", "")))


def iniciar(doc, ancho=1900, alto=1000):
    fmt = QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)
    app = QApplication.instance() or QApplication([])
    parchar_modales()
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    prefs = Preferencias(QSettings(str(Path(tempfile.mkdtemp(prefix="omnicad_ui_")) / "prefs.ini"), QSettings.IniFormat))
    v = VentanaPrincipal(doc, prefs=prefs)
    v.resize(ancho, alto)
    v.show()
    QTest.qWait(700)
    v.visor.encuadrar()
    QTest.qWait(250)
    return app, v


def esperar(ms=350):
    QTest.qWait(ms)


def foto(v, nombre):
    ruta = CAPTURAS / f"{nombre}.png"
    v.grab().save(str(ruta))
    return ruta


# ------------------------------------------------------------------ elegir como lo haría el clic
def _clic_en(v, punto3d, filtros):
    q = v.visor.proyectar(np.array(punto3d, float))
    if q is None:
        return None
    return v.visor.elegir_entidad(q, filtros)


def hit_cara(v, cid, normal=None, cerca=None):
    """Cara del cuerpo elegida con el visor (el clic en su centro). `normal`: la que mira hacia allá."""
    forma = v.doc.estado_final.cuerpos[cid].forma
    mejor = None
    for c in refs.subformas(forma, "cara"):
        f = refs.firma_cara(c)
        if normal is not None and not ("normal" in f and np.dot(f["normal"], normal) > 0.99):
            continue
        if cerca is not None and np.linalg.norm(np.array(f["centro"]) - np.array(cerca)) > 1e-6 and normal is None:
            continue
        hit = _clic_en(v, f["centro"], {"cara"})
        if hit and hit["ref"].get("cuerpo") == cid:
            if mejor is None or f["area"] > mejor[0]:
                mejor = (f["area"], hit)
    return mejor[1] if mejor else None


def hit_arista(v, cid, lineal=True, orden=0, paralela=None, cerca=None):
    """Arista del cuerpo elegida con el visor. `cerca`: la que tiene su punto medio a menos de 0.5 mm de ese punto."""
    forma = v.doc.estado_final.cuerpos[cid].forma
    cands = []
    for a in sorted(refs.subformas(forma, "arista"), key=lambda a: -refs.firma_arista(a)["largo"]):
        f = refs.firma_arista(a)
        if lineal and f["geom"] != "linea":
            continue
        if cerca is not None and np.linalg.norm(np.array(f["medio"]) - np.array(cerca)) > 0.5:
            continue
        if paralela is not None:
            d = np.array(f["direccion"]) if "direccion" in f else None
            if d is None or abs(np.dot(d, paralela)) < 0.99:
                continue
        hit = _clic_en(v, f["medio"], {"arista"})
        if hit and hit["ref"].get("cuerpo") == cid:
            cands.append(hit)
    return cands[orden] if len(cands) > orden else None


def hit_cuerpo(v, cid):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref({"tipo": "cuerpo", "cuerpo": cid}, v.doc.estado_final)


def hit_plano(v, ident):
    """Plano de origen («XY») o de construcción por su NOMBRE («PM»): el id del paso se busca solo."""
    from omnicad.ui.comando import hit_desde_ref
    if ident not in geo.Plano.DEFINICIONES:
        op = next((o for o in v.doc.operaciones if o.nombre == ident), None)
        ident = op.id if op else ident
    return hit_desde_ref({"tipo": "plano", "id": ident}, v.doc.estado_final)


def hit_eje(v, ident):
    from omnicad.ui.comando import hit_desde_ref
    return hit_desde_ref({"tipo": "eje", "id": ident}, v.doc.estado_final)


def hit_curva(v, sesion, boceto, indice=0):
    """Curva de un boceto elegida con el visor (el clic en su punto medio)."""
    op = sesion.paso(boceto)
    br = v.doc.estado_final.bocetos[op.id]
    curvas = list(br.boceto.curvas)
    cid = curvas[indice]
    from omnicad.ui.comando import hit_desde_ref
    h = hit_desde_ref({"tipo": "curva_boceto", "boceto": op.id, "curva": cid}, v.doc.estado_final)
    if h.get("forma") is not None:
        pts = geo.polilinea_arista(h["forma"])
        medio = pts[len(pts) // 2]
        clic = _clic_en(v, medio, {"curva_boceto"})
        if clic and clic["ref"].get("curva") == cid and clic["ref"].get("boceto") == op.id:
            return clic
    return h


def hit_perfil(v, sesion, boceto, indice=0):
    """Perfil de un boceto elegido con el visor (el clic en su centroide)."""
    from omnicad.timeline.operaciones import OpExtrusion
    from omnicad.api.herramientas_boceto import boceto_activo, seleccionar_perfiles
    op = sesion.paso(boceto)
    sop, br = boceto_activo(sesion, op.id)
    p = seleccionar_perfiles(br, sop, indice)[0]
    ref = OpExtrusion.referencia_perfil(p)
    u, w = ref["centroide"]
    punto = br.plano.a_3d(u, w)
    hit = _clic_en(v, punto, {"perfil"})
    if hit is None:
        from omnicad.ui.comando import hit_desde_ref
        hit = hit_desde_ref({"tipo": "perfil", "boceto": op.id, **ref}, v.doc.estado_final)
    return hit


# ------------------------------------------------------------------ un comando de punta a punta
def abrir(v, clave):
    from omnicad.ui.comandos import CATALOGO
    panel = v.ejecutar_comando(CATALOGO[clave]())
    esperar(150)
    return panel


def elegir(panel, campo, *hits):
    """Como la persona: activa el campo y hace clic en cada entidad."""
    c = next(c for c in panel.campos if c.clave == campo)
    panel._activar(c)
    for h in hits:
        if h is None:
            raise RuntimeError(f"no hay entidad para elegir en «{campo}»")
        panel._elegida(h)


def estado_panel(panel):
    return {"mensaje": panel.mensaje.text() if panel.mensaje.isVisible() else "", "op": panel.ultima_op is not None,
            "previa_ok": panel._previa_ok}


def etiquetas(panel):
    return [(c.clave, type(c).__name__, c.etiqueta, panel._visible(c)) for c in panel.campos]


def n_ops(v):
    return len(v.doc.operaciones)


def deshacer(v):
    v.acciones["deshacer"].trigger()
    esperar(250)


def _medida(c):
    """Volumen del sólido, área de la superficie o cantidad de caras de la malla (no es una forma OCC)."""
    if c.tipo == "solido":
        return round(geo.volumen(c.forma), 3)
    return len(c.forma.caras) if c.tipo == "malla" else round(geo.area(c.forma), 3)


def cuerpos_resumen(v):
    return {c.id: (c.tipo, _medida(c)) for c in v.doc.estado_final.cuerpos.values()}


def correr(nombre, funcion):
    """Ejecuta una prueba y anota la excepción si la hay (una falla no corta las demás)."""
    try:
        funcion()
    except Exception as e:  # noqa: BLE001
        reg(nombre, "EXCEPCIÓN", False, f"{type(e).__name__}: {e} | {traceback.format_exc().splitlines()[-3:]}")


def clic_derecho(widget, pos):
    """Clic derecho como lo ve la app: el botón y, aparte, el evento de menú contextual (QTest no lo genera solo)."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QContextMenuEvent
    QTest.mouseClick(widget, Qt.RightButton, Qt.NoModifier, pos)
    QApplication.sendEvent(widget, QContextMenuEvent(QContextMenuEvent.Mouse, pos, widget.mapToGlobal(pos)))
    QTest.qWait(80)
