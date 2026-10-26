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


def test_sin_plano_no_hay_flecha(app_qt, ventana):  # noqa: F811
    ventana.set_documento(_doc_caja())
    p = ventana.ejecutar_comando(CATALOGO["seccion"]())
    assert p.manipuladores.manips == []
    p.cancelar()
