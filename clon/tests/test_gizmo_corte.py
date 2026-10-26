"""Gizmo de los planos de corte: Análisis de sección y Boceto de sección de malla."""
import numpy as np
import pytest
from test_manipuladores import _arrastrar, _doc_caja, _panel, app_qt  # noqa: F401  (fixture)

from omnicad.ui import manipuladores as mp
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import CATALOGO
from test_p23_navegador import ventana as ventana  # noqa: F401  (fixture)


def _abrir(clave, ventana, **valores):
    """Los análisis se muestran en la ventana (sin ella el panel no se puede cerrar); los comandos de malla no
    abren sin una malla, así que van con el panel suelto."""
    doc = _doc_caja()
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)
    if clave == "seccion":
        ventana.set_documento(doc)
        p = ventana.ejecutar_comando(CATALOGO[clave](), valores={"plano": [plano], **valores})
        p.visor.vista("iso")
    else:
        p, visor, _ = _panel(CATALOGO[clave](), doc, {"plano": [plano], **valores})
        visor.vista("iso")
    p.manipuladores.actualizar()
    return p


@pytest.mark.parametrize("clave,campo", [("seccion", "desfase"), ("seccion_malla", "distancia")])
def test_flecha_de_distancia_en_los_dos_comandos(app_qt, ventana, clave, campo):  # noqa: F811
    p = _abrir(clave, ventana)
    gm = p.manipuladores
    f = next(m for m in gm.manips if isinstance(m, mp.Flecha))
    assert f.clave == campo and np.allclose(f.direccion, (0, 0, 1))
    a, b = f.puntos(gm)
    xy, ok = gm.pantalla([(a + b) / 2, (a + b) / 2 + f.direccion * 8])
    assert ok.all()
    _arrastrar(p.visor, *xy)
    assert gm.valor(campo) == pytest.approx(8, abs=0.5)
    xy, ok = gm.pantalla([f.puntos(gm)[0], f.puntos(gm)[0] - f.direccion * 30])           # pasa por cero: negativos valen
    _arrastrar(p.visor, *xy)
    assert gm.valor(campo) < 0
    p.cancelar()


@pytest.mark.parametrize("clave", ["seccion", "seccion_malla"])
def test_arco_del_angulo_gira_el_plano(app_qt, ventana, clave):  # noqa: F811
    p = _abrir(clave, ventana)
    gm = p.manipuladores
    arco = next(m for m in gm.manips if isinstance(m, mp.Angulo))
    assert arco.clave == "angulo" and np.allclose(arco.eje, (1, 0, 0))                # gira sobre el eje u del plano XY
    objetivo = arco.centro + (arco.u * np.cos(np.radians(40)) + arco.v * np.sin(np.radians(40))) * arco._r(gm)
    xy, ok = gm.pantalla([arco.asa(gm), objetivo])
    assert ok.all()
    _arrastrar(p.visor, *xy)
    assert gm.valor("angulo") == pytest.approx(40, abs=2)
    p.set_valor("desfase" if clave == "seccion" else "distancia", "10 mm")             # el arco sigue al plano desplazado
    nuevo = next(m for m in gm.manips if isinstance(m, mp.Angulo))
    assert nuevo.centro == pytest.approx([0, 0, 10])
    p.cancelar()


def test_corte_de_plano_de_malla_tiene_flecha_y_arco(app_qt):  # noqa: F811
    from test_api_malla import malla_de_caja
    from omnicad import api
    s = api.Sesion()
    malla_de_caja(s, z=-5)
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, s.doc.estado_final)
    p, visor, _ = _panel(CATALOGO["cortar_plano"](), s.doc, {"plano": [plano]})
    visor.vista("iso")
    p.manipuladores.actualizar()
    gm = p.manipuladores
    assert sorted(type(m).__name__ for m in gm.manips) == ["Angulo", "Flecha"]
    f = next(m for m in gm.manips if isinstance(m, mp.Flecha))
    a, b = f.puntos(gm)
    xy, ok = gm.pantalla([(a + b) / 2, (a + b) / 2 + f.direccion * 3])
    _arrastrar(p.visor, *xy)
    assert gm.valor("desfase") == pytest.approx(3, abs=0.5)
    p.cancelar()


def test_sin_plano_no_hay_flecha(app_qt, ventana):  # noqa: F811
    ventana.set_documento(_doc_caja())
    p = ventana.ejecutar_comando(CATALOGO["seccion"]())
    assert p.manipuladores.manips == []
    p.cancelar()
