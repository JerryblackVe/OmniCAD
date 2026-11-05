"""Eventos del boceto en el registro: herramienta, entidades, restricciones, cotas, solver y cierre."""
import json
import time

import pytest

from omnicad import registro_uso as ru
from omnicad.nucleo import geometria as g
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento

PLANO = g.Plano("XY")


def eventos(carpeta):
    return [json.loads(l) for p in sorted(carpeta.glob("sesion_*.jsonl")) for l in p.read_text(encoding="utf-8").splitlines()]


def de_tipo(carpeta, tipo):
    return [e["datos"] for e in eventos(carpeta) if e["tipo"] == tipo]


@pytest.fixture(scope="module")
def app_qt():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    ru.configurar(False)
    ru.aplicar(ru.FABRICA)
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    yield
    ru.configurar(False)
    ru.ultimo = None
    ru.aplicar(ru.FABRICA)


@pytest.fixture
def ventana(app_qt, tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtTest import QTest
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    v = VentanaPrincipal(prefs=Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat)))
    v.resize(1000, 700)
    v.show()
    QTest.qWait(1)
    ru.configurar(True)
    yield v
    ru.configurar(False)
    if v.modo_boceto.activo:
        v.modo_boceto.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app_qt.processEvents()


def _empezar(v):
    b = Boceto()
    v.set_documento(Documento())
    v.modo_boceto.iniciar(b, PLANO, {"op": None, "plano": "XY"})
    return v.modo_boceto.lienzo


def test_boceto_herramienta_se_registra(ventana):
    lz = _empezar(ventana)
    for h in ("linea", "circulo", "texto"):
        lz.set_herramienta(h)
    ru.activo.cola.join()
    assert [d["herramienta"] for d in de_tipo(ru.carpeta(), "boceto_herramienta")] == "seleccionar linea circulo texto".split()      # abrir el boceto ya activa Seleccionar


def test_boceto_entidad_al_crearyborrar(ventana):
    lz = _empezar(ventana)
    lz.aplicar_cambio(lambda: lz.b.agregar_linea((0, 0), (10, 0)))
    ru.activo.cola.join()
    creadas = [d for d in de_tipo(ru.carpeta(), "boceto_entidad") if d["accion"] == "creada"]
    assert creadas and creadas[-1]["tipo"] == "linea"
    cid = max(lz.b.curvas)
    lz.aplicar_cambio(lambda: lz.b.eliminar(cid))
    ru.activo.cola.join()
    borradas = [d for d in de_tipo(ru.carpeta(), "boceto_entidad") if d["accion"] == "borrada"]
    assert borradas and borradas[-1]["tipo"] == "linea"


def test_boceto_restriccion_y_cota_con_valor(ventana):
    lz = _empezar(ventana)
    p1 = lz.b.agregar_punto(0, 0)
    p2 = lz.b.agregar_punto(10, 5)
    lz.aplicar_cambio(lambda: lz.b.agregar_restriccion("coincidente", [p1, p2]))
    ru.activo.cola.join()
    rs = de_tipo(ru.carpeta(), "boceto_restriccion")
    assert rs and rs[-1]["tipo"] == "coincidente" and rs[-1]["accion"] == "agregada"
    p3 = lz.b.agregar_punto(0, 10)
    p4 = lz.b.agregar_punto(20, 10)
    lz.aplicar_cambio(lambda: lz.b.agregar_cota("distancia_h", [p3, p4], "20 mm"))
    ru.activo.cola.join()
    cs = de_tipo(ru.carpeta(), "boceto_cota")
    assert cs and cs[-1]["tipo"] == "distancia_h" and cs[-1]["valor"] == "20 mm"


def test_boceto_solver_a_lo_sumo_cada_medio_segundo(ventana):
    lz = _empezar(ventana)
    for i in range(5):
        lz.resolver()
        time.sleep(0.11)
    ru.activo.cola.join()
    sol = de_tipo(ru.carpeta(), "boceto_solver")
    assert sol and len(sol) <= 4                     # 5 cambios de ≥0,11 s: se fusiona al menos uno
    assert all(d["estado"] == "ok" for d in sol)
    assert "gdl" in sol[-1] and sol[-1]["gdl"] >= 0


def test_boceto_cerrado_aceptado_o_cancelado(ventana):
    _empezar(ventana)
    assert ventana.modo_boceto.terminar() is True
    ru.activo.cola.join()
    es = de_tipo(ru.carpeta(), "boceto_cerrado")
    assert es and es[-1]["resultado"] == "aceptado"
    _empezar(ventana)
    ventana.modo_boceto.cancelar()
    ru.activo.cola.join()
    assert de_tipo(ru.carpeta(), "boceto_cerrado")[-1]["resultado"] == "cancelado"


def test_registro_uso_sigue_sin_qt():
    import subprocess
    import sys
    codigo = ("import sys; from omnicad import registro_uso; from omnicad.registro_uso import ganchos, almacen, "
              "detector; assert not any(k.startswith('PySide') for k in sys.modules)")
    subprocess.run([sys.executable, "-c", codigo], check=True)
