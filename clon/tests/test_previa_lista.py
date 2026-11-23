# -*- coding: utf-8 -*-
"""B-840: el evento «previa_lista» del registro de uso y la vía rápida de `_toca` (puntos del perfil)."""
from types import SimpleNamespace

import pytest
from OCP.TopAbs import TopAbs_ShapeEnum

from omnicad import registro_uso
from omnicad.nucleo import geometria as geo
from omnicad.timeline import operaciones as ops
from omnicad.timeline.calculo_aislado import leer_previa_visual, previa_visual
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.ui.comando import PanelComando


class _Registro:
    def __init__(self):
        self.eventos = []

    def emitir(self, tipo, datos=None, **_):
        self.eventos.append((tipo, datos))


@pytest.fixture
def registro(monkeypatch):
    r = _Registro()
    monkeypatch.setattr(registro_uso, "activo", r)
    return r


def _panel(t_pedido=100.0):
    return SimpleNamespace(comando=SimpleNamespace(CLAVE="extruir"), _t_pedido=t_pedido)


def test_previa_lista_aparte_reparte_el_tiempo_entre_etapas(registro, monkeypatch):
    monkeypatch.setattr("omnicad.ui.comando.time.time", lambda: 101.0)
    etapas = {"t_ini": 100.02, "t_fin": 100.9, "recalculo_ms": 15.0, "kernel_ms": 600.0, "malla_ms": 250.0}
    PanelComando._registrar_previa_lista(_panel(), etapas, t_recibida=100.97)
    (tipo, d), = registro.eventos
    assert tipo == "previa_lista" and d["comando"] == "extruir" and d["aparte"] is True
    assert d["total_ms"] == pytest.approx(1000, abs=1) and d["espera_ms"] == pytest.approx(20, abs=1)
    assert d["vuelta_ms"] == pytest.approx(70, abs=1) and d["ventana_ms"] == pytest.approx(30, abs=1)
    assert (d["recalculo_ms"], d["kernel_ms"], d["malla_ms"]) == (15.0, 600.0, 250.0)


def test_previa_lista_en_la_ventana_solo_trae_el_kernel(registro):
    PanelComando._registrar_previa_lista(_panel(), None, kernel_ms=12.345)
    assert registro.eventos == [("previa_lista", {"comando": "extruir", "aparte": False, "kernel_ms": 12.3})]


def test_previa_lista_sin_registro_no_hace_nada(monkeypatch):
    monkeypatch.setattr(registro_uso, "activo", None)
    PanelComando._registrar_previa_lista(_panel(), None, kernel_ms=1.0)       # no levanta


def test_previa_visual_trae_las_etapas_al_padre():
    doc = Documento()
    doc.agregar(OpPrimitiva("op1", forma="caja", ancho="20", largo="20", alto="10"))
    op = OpPrimitiva("op90", forma="caja", ancho="5", largo="5", alto="5", z="12").a_dict()
    salida = previa_visual(doc.a_dict(), op, None, 0.05, 0.5)
    estado = leer_previa_visual(salida, doc.estado_final)[0]
    e = estado._etapas
    assert 0 < e["t_ini"] <= e["t_fin"] and e["kernel_ms"] > 0 and e["malla_ms"] >= 0 and e["recalculo_ms"] >= 0


# --- vía rápida de `_toca`: un punto del perfil sobre el cuerpo lo da por tocado, sin `se_tocan` ---

@pytest.fixture
def cuerpo_ya_modificado():
    """Una placa a la que un paso anterior (una booleana) ya le sacó un agujero: no es la caja del principio."""
    placa = geo.caja(100, 100, 10)
    agujero = geo.trasladar(geo.caja(20, 20, 30), (40, 40, -10))
    return SimpleNamespace(forma=geo.booleano(placa, agujero, "cortar")), geo.trasladar(geo.caja(30, 30, 5), (0, 0, 10))


def test_toca_por_un_punto_del_perfil_sobre_un_cuerpo_ya_modificado(cuerpo_ya_modificado, monkeypatch):
    c, herramienta = cuerpo_ya_modificado
    original = geo.se_tocan

    def solo_vertices(a, b, *r, **k):             # `punto_toca` mide un vértice; el cuerpo entero no se mide
        if a.ShapeType() != TopAbs_ShapeEnum.TopAbs_VERTEX:
            pytest.fail("la vía rápida no debía medir el cuerpo entero")
        return original(a, b, *r, **k)
    monkeypatch.setattr(geo, "se_tocan", solo_vertices)
    assert ops._toca(c, herramienta, None, [(10.0, 10.0, 10.0)])         # el punto está sobre la cara de arriba


def test_toca_sin_punto_o_con_punto_lejos_mide_como_siempre(cuerpo_ya_modificado):
    c, herramienta = cuerpo_ya_modificado
    esperado = geo.se_tocan(c.forma, herramienta)
    assert esperado is True
    assert ops._toca(c, herramienta) is esperado
    assert ops._toca(c, herramienta, None, [(10.0, 10.0, 11.5)]) is esperado      # un punto en el aire no decide nada


def test_toca_si_la_via_rapida_falla_cae_al_camino_normal(cuerpo_ya_modificado, monkeypatch):
    c, herramienta = cuerpo_ya_modificado

    def roto(*a, **k):
        raise RuntimeError("falló el punto")
    monkeypatch.setattr(geo, "punto_toca", roto)
    assert ops._toca(c, herramienta, None, [(10.0, 10.0, 10.0)]) is True
    lejos = SimpleNamespace(forma=c.forma)
    assert ops._toca(lejos, geo.trasladar(geo.caja(5, 5, 5), (500, 500, 500)), None, [(10.0, 10.0, 10.0)]) is False
