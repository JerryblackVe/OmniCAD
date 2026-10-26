"""Asa de cantidad de los patrones (rectangular, circular y en trayectoria): se tira del disco y suma o quita copias."""
import numpy as np
import pytest
from test_manipuladores import _arrastrar, _doc_caja, _panel, app_qt  # noqa: F401  (fixture)

from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO


def _abrir(clave, valores):
    doc = _doc_caja()
    cuerpo = hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)
    ref = {"tipo": "eje", "id": "X" if clave == "patron_rectangular_3d" else "Z"}
    p, visor, _ = _panel(CATALOGO[clave](), doc, {"cuerpos": [cuerpo], **valores(hit_desde_ref(ref, doc.estado_final))})
    visor.vista("iso")
    p.manipuladores.actualizar()
    return p


def _asa(p, clave):
    return next(m for m in p.manipuladores.manips if isinstance(m, mp.AsaCantidad) and m.clave == clave)


def _arrastrar_n(p, m, copias):
    """Tira del disco `copias` pasos (de m.paso mm) a lo largo de la dirección del patrón."""
    gm = p.manipuladores
    asa, _pt, t = m._asa(gm)
    xy, ok = gm.pantalla([asa, asa + t * m.paso * copias])
    assert ok.all()
    _arrastrar(p.visor, *xy)


def test_rectangular_suma_y_quita_copias_y_no_baja_de_una(app_qt):  # noqa: F811
    p = _abrir("patron_rectangular_3d", lambda eje: {"dir1": [eje], "n1": 3, "d1": "10 mm", "distribucion": "espaciado"})
    gm = p.manipuladores
    m = _asa(p, "n1")
    assert gm.valor("n1") == 3 and "n1" in gm.cajas
    _arrastrar_n(p, m, 2)
    assert int(gm.valor("n1")) == 5 and p.widgets["n1"].value() == 5
    _arrastrar_n(p, _asa(p, "n1"), -9)
    assert p.widgets["n1"].value() == 1
    p._calcular_previa()
    assert p._previa_ok
    p.cancelar()


def test_rectangular_en_extension_reparte_la_distancia_entre_las_copias(app_qt):  # noqa: F811
    p = _abrir("patron_rectangular_3d", lambda eje: {"dir1": [eje], "n1": 3, "d1": "10 mm", "distribucion": "extension"})
    assert _asa(p, "n1").paso == pytest.approx(5)
    p.set_valor("n1", 5)
    assert _asa(p, "n1").paso == pytest.approx(2.5)
    p.cancelar()


def test_teclear_la_cantidad_mueve_el_asa(app_qt):  # noqa: F811
    p = _abrir("patron_rectangular_3d", lambda eje: {"dir1": [eje], "n1": 3, "d1": "10 mm", "distribucion": "espaciado"})
    gm = p.manipuladores
    antes = _asa(p, "n1")._asa(gm)[0].copy()
    p.set_valor("n1", 6)
    despues = _asa(p, "n1")._asa(gm)[0]
    assert np.linalg.norm(despues - antes) == pytest.approx(3 * 10, abs=0.05)
    p.cancelar()


def test_circular_cambia_la_cantidad_tirando_del_disco(app_qt):  # noqa: F811
    p = _abrir("patron_circular_3d", lambda eje: {"eje": [eje], "n": 4, "angulo": "40 deg", "distribucion": "espaciado"})
    m = _asa(p, "n")
    _arrastrar_n(p, m, 2)
    assert p.widgets["n"].value() == 6
    p._calcular_previa()
    assert p._previa_ok
    p.cancelar()
