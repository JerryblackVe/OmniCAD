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


def _triada(gm):
    return next(m for m in gm.manips if isinstance(m, mp.Triada))


def _medio_del_eje(gm):
    """Medio del eje de la normal, donde se toma para arrastrar."""
    return dict(_triada(gm)._partes(gm)[0])[("eje", 2)].mean(axis=0)


@pytest.mark.parametrize("clave,campo", [("seccion", "desfase"), ("seccion_malla", "distancia")])
def test_eje_de_la_triada_da_la_distancia_en_los_dos_comandos(app_qt, ventana, clave, campo):  # noqa: F811
    p = _abrir(clave, ventana)
    gm = p.manipuladores
    t = _triada(gm)
    assert t.claves == (None, None, campo) and np.allclose(t.ejes[2], (0, 0, 1))
    medio = _medio_del_eje(gm)
    xy, ok = gm.pantalla([medio, medio + t.ejes[2] * 8])
    assert ok.all()
    _arrastrar(p.visor, *xy)
    assert gm.valor(campo) == pytest.approx(8, abs=0.5)
    medio = _medio_del_eje(gm)
    xy, ok = gm.pantalla([medio, medio - t.ejes[2] * 30])                                  # pasa por cero: negativos valen
    _arrastrar(p.visor, *xy)
    assert gm.valor(campo) < 0
    p.cancelar()


@pytest.mark.parametrize("clave", ["seccion", "seccion_malla"])
def test_arco_de_la_triada_gira_el_plano(app_qt, ventana, clave):  # noqa: F811
    p = _abrir(clave, ventana)
    gm = p.manipuladores
    t = _triada(gm)
    assert t.giros == ("angulo", None, None) and np.allclose(t.ejes[0], (1, 0, 0))        # gira sobre el eje u del plano XY
    arco = dict(t._partes(gm)[0])[("giro", 0)]
    asa = arco[len(arco) // 2]
    r = np.linalg.norm(asa - t.centro)
    objetivo = t.centro + (t.ejes[1] * np.cos(np.radians(85)) + t.ejes[2] * np.sin(np.radians(85))) * r
    xy, ok = gm.pantalla([asa, objetivo])
    assert ok.all()
    _arrastrar(p.visor, *xy)
    assert gm.valor("angulo") == pytest.approx(40, abs=2)
    p.set_valor("desfase" if clave == "seccion" else "distancia", "10 mm")             # la tríada sigue al plano desplazado
    assert _triada(gm).centro == pytest.approx([0, 0, 10])
    p.cancelar()


def test_corte_de_plano_de_malla_tiene_triada(app_qt):  # noqa: F811
    from test_api_malla import malla_de_caja
    from omnicad import api
    s = api.Sesion()
    malla_de_caja(s, z=-5)
    plano = hit_desde_ref({"tipo": "plano", "id": "XY"}, s.doc.estado_final)
    p, visor, _ = _panel(CATALOGO["cortar_plano"](), s.doc, {"plano": [plano]})
    visor.vista("iso")
    p.manipuladores.actualizar()
    gm = p.manipuladores
    assert [type(m).__name__ for m in gm.manips] == ["Triada"]
    t = _triada(gm)
    medio = _medio_del_eje(gm)
    xy, ok = gm.pantalla([medio, medio + t.ejes[2] * 3])
    _arrastrar(p.visor, *xy)
    assert gm.valor("desfase") == pytest.approx(3, abs=0.5)
    p.cancelar()


def test_sin_plano_no_hay_flecha(app_qt, ventana):  # noqa: F811
    ventana.set_documento(_doc_caja())
    p = ventana.ejecutar_comando(CATALOGO["seccion"]())
    assert p.manipuladores.manips == []
    p.cancelar()
