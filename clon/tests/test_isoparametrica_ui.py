"""Curva isoparamétrica en la ventana (BOC-36): la herramienta del boceto saca las curvas de la cara elegida con la
dirección, el tipo y el vínculo de la paleta, y las deja como curvas 3D (con su origen si hay vínculo)."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402
from omnicad.ui import editor_boceto  # noqa: E402


@pytest.fixture
def lienzo():
    app = QApplication.instance() or QApplication([])
    lz = editor_boceto.Lienzo(Boceto(), TablaParametros().evaluar, plano=geo.Plano("XY"))
    lz.resize(600, 400)
    yield lz
    lz.close()
    lz.deleteLater()
    app.processEvents()


@pytest.fixture
def cara():
    """(forma OCC de la cara lateral de un cilindro de radio 10 y alto 40, su referencia como la da el visor)."""
    s = api.Sesion()
    api.llamar(s, "create_cylinder", {"radius": 10, "height": 40})
    f = api.llamar(s, "find_faces", {"selector": "%CYLINDER"})["result"]["faces"][0]["id"]
    from omnicad.api import selectores as sl
    c, e = sl.elegir(s, f, "cara")[0]
    return e.sub, sl.referencia(c, e)


def _curvas(lz):
    return list(lz.b.geo3d.get("curvas", {}).values())


def test_una_curva_por_el_punto_del_clic_con_vinculo(lienzo, cara):
    forma, ref = cara
    lienzo.set_herramienta("isoparametrica")
    assert lienzo._usar_entidad({"forma": forma, "ref": ref, "punto": [10, 0, 15], "tipo": "cara"}) is True
    (c,) = _curvas(lienzo)
    assert c["tipo"] == "circulo" and c["radio"] == pytest.approx(10)
    assert c["origen"]["tool"] == "isoparametric_curve" and c["origen"]["point"] == [10, 0, 15] and c["origen"]["index"] == 0
    lienzo.deshacer()                                                   # UN paso de deshacer
    assert not _curvas(lienzo)


def test_distribuidas_por_cantidad_ambas_direcciones_y_sin_vinculo(lienzo, cara):
    forma, ref = cara
    lienzo.opciones.update(iso_direccion="both", iso_tipo="cantidad", iso_cantidad=3, vinculo_proyeccion=False)
    lienzo.set_herramienta("isoparametrica")
    lienzo._usar_entidad({"forma": forma, "ref": ref, "punto": [10, 0, 15], "tipo": "cara"})
    tipos = sorted(c["tipo"] for c in _curvas(lienzo))
    assert tipos == ["circulo"] * 3 + ["linea"] * 3 and all("origen" not in c for c in _curvas(lienzo))
    lienzo.opciones.update(iso_direccion="u", iso_tipo="unica", vinculo_proyeccion=True)


def test_por_distancia_y_los_errores_se_dicen_sin_tocar_el_boceto(lienzo, cara):
    forma, ref = cara
    mensajes = []
    lienzo.mensaje.connect(mensajes.append)
    lienzo.opciones.update(iso_tipo="distancia", iso_distancia=10.0)
    lienzo.set_herramienta("isoparametrica")
    lienzo._usar_entidad({"forma": forma, "ref": ref, "punto": [10, 0, 20], "tipo": "cara"})
    assert sorted(round(c["radio"], 6) for c in _curvas(lienzo)) == [10, 10, 10]
    n = len(_curvas(lienzo))
    assert not lienzo._usar_entidad({"forma": forma, "ref": ref, "punto": [10, 0, 99], "tipo": "cara"})
    assert not lienzo._usar_entidad({"forma": forma, "ref": ref, "punto": None, "tipo": "cara"})
    lienzo.opciones.update(iso_distancia=0.01)
    assert not lienzo._usar_entidad({"forma": forma, "ref": ref, "punto": [10, 0, 20], "tipo": "cara"})
    assert len(_curvas(lienzo)) == n and any("tope" in m for m in mensajes) and any("no cae" in m for m in mensajes)
    lienzo.opciones.update(iso_tipo="unica", iso_distancia=10.0)


def test_la_herramienta_pide_caras_y_esta_en_el_menu_de_la_cinta(lienzo):
    from omnicad.ui.cinta_boceto import GRUPOS_BOCETO
    from omnicad.ui.modo_boceto import ACCIONES_BOCETO, ENTEROS_HERRAMIENTA, NUMEROS_HERRAMIENTA, OPCIONES_HERRAMIENTA
    assert any(a[0] == "sk_isoparametrica" for a in ACCIONES_BOCETO) and "sk_isoparametrica" in repr(GRUPOS_BOCETO)
    assert "isoparametrica" in OPCIONES_HERRAMIENTA and "isoparametrica" in NUMEROS_HERRAMIENTA and "isoparametrica" in ENTEROS_HERRAMIENTA
    lienzo.set_herramienta("isoparametrica")
    assert lienzo.herramienta == "isoparametrica"


# ---------------------------------------------------------------- la vista previa antes del clic (BOC-75)
class VisorFalso(QWidget):
    """Lo mínimo del visor que usa la vista previa: dice qué hay bajo el cursor y guarda las capas que le piden."""

    def __init__(self, info):
        super().__init__()
        self.info, self.capas, self.pedidos = info, {}, []

    def elegir_entidad(self, pos, filtros=None, a_traves=False):
        self.pedidos.append(filtros)
        return self.info

    def set_capa(self, nombre, primitivas):
        self.capas[nombre] = primitivas


@pytest.fixture
def con_visor(lienzo, cara):
    forma, ref = cara
    visor = VisorFalso({"forma": forma, "ref": ref, "punto": np.array([10.0, 0.0, 15.0]), "tipo": "cara"})
    lienzo.visor = visor
    lienzo.set_herramienta("isoparametrica")
    yield lienzo, visor
    lienzo.visor = None                                                  # el lienzo de la prueba es 2D: no pinta con un visor falso


def _segmentos_previa(visor):
    return np.asarray(visor.capas["iso_previa"][0][1], float)


def test_la_vista_previa_dibuja_la_curva_antes_del_clic_y_no_toca_el_boceto(con_visor):
    lz, visor = con_visor
    lz.programar_previa_iso(QPointF(40, 40))
    assert lz._t_iso.isActive() and "iso_previa" not in visor.capas       # espera a que el cursor se quede quieto
    lz._previa_iso()
    pts = _segmentos_previa(visor).reshape(-1, 3)
    assert visor.pedidos == [{"cara"}] and np.hypot(pts[:, 0], pts[:, 1]) == pytest.approx(10) and pts[:, 2] == pytest.approx(15)
    assert not _curvas(lz)


def test_la_vista_previa_sigue_a_las_opciones_de_la_paleta(con_visor):
    lz, visor = con_visor
    lz.opciones.update(iso_tipo="cantidad", iso_cantidad=3)
    lz.programar_previa_iso(QPointF(40, 40))
    lz._previa_iso()
    alturas = sorted({round(z, 4) for z in _segmentos_previa(visor).reshape(-1, 3)[:, 2]})
    assert alturas == pytest.approx([40 / 6, 20, 40 * 5 / 6], abs=1e-3)
    lz.opciones.update(iso_tipo="unica")


def test_la_vista_previa_se_borra_al_hacer_clic_al_salir_del_modelo_y_al_cambiar_de_herramienta(con_visor):
    lz, visor = con_visor
    lz.programar_previa_iso(QPointF(40, 40))
    lz._previa_iso()
    assert visor.capas["iso_previa"]
    assert lz._usar_entidad(visor.info) and visor.capas["iso_previa"] is None and len(_curvas(lz)) == 1       # el clic la reemplaza
    lz._previa_iso()
    assert visor.capas["iso_previa"]
    lz.leaveEvent(QEvent(QEvent.Leave))                                   # el cursor sale de la vista
    assert visor.capas["iso_previa"] is None
    lz._previa_iso()
    lz.set_herramienta("seleccionar")
    assert visor.capas["iso_previa"] is None and not lz._t_iso.isActive()
    visor.capas.clear()
    lz._previa_iso()                                                      # ya no es la herramienta: no dibuja nada
    assert "iso_previa" not in visor.capas


def test_sin_cara_bajo_el_cursor_no_hay_vista_previa_y_un_valor_malo_se_avisa_una_sola_vez(con_visor, cara):
    lz, visor = con_visor
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    lz.programar_previa_iso(QPointF(40, 40))
    lz._previa_iso()
    assert visor.capas["iso_previa"]
    visor.info = None                                                     # el cursor se fue a un lugar sin cara
    lz._previa_iso()
    assert visor.capas["iso_previa"] is None and not mensajes
    visor.info = {"forma": None, "punto": None, "tipo": "cara"}
    lz._previa_iso()
    assert visor.capas["iso_previa"] is None and not mensajes
    forma, ref = cara
    visor.info = {"forma": forma, "ref": ref, "punto": np.array([10.0, 0.0, 15.0]), "tipo": "cara"}
    lz.opciones.update(iso_tipo="distancia", iso_distancia=0.01)         # saldrían más curvas que el tope
    lz._previa_iso()
    lz._previa_iso()
    assert visor.capas["iso_previa"] is None and len(mensajes) == 1 and "tope" in mensajes[0]
    lz.opciones.update(iso_tipo="unica", iso_distancia=10.0)


def test_un_arco_que_no_se_puede_armar_no_deja_excepcion_en_la_vista_previa(con_visor, monkeypatch):
    from omnicad.restricciones import ErrorBoceto, boceto3d as b3
    lz, visor = con_visor
    lz.programar_previa_iso(QPointF(40, 40))
    lz._previa_iso()
    assert visor.capas["iso_previa"]
    def malo(*a, **k):
        raise ErrorBoceto("Los tres puntos del arco están alineados")
    monkeypatch.setattr(b3, "agregar_desde_mundo", malo)
    lz._previa_iso()                                                      # antes: excepción dentro del timer
    assert visor.capas["iso_previa"] is None
