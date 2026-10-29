"""SUP-25: asas de Revolución de superficie y de Reglada; B-112: un factor no lleva unidad."""
import math
import os

import numpy as np
import pytest

from omnicad.nucleo import geometria as geo, referencias as refs, superficies as sf
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpBoceto, OpPrimitiva
from omnicad.timeline.parametros import ErrorExpresion, con_unidad


@pytest.fixture(scope="module")
def app_qt():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def caja_100():
    return geo.caja(100, 60, 20)


def arista_de_arriba(forma):
    """La arista recta de la cara de arriba (z = 20) que está en x = 100."""
    def esta(e):
        (x0, _y0, z0), (x1, _y1, z1) = geo.caja_envolvente(e)
        return min(x0, x1) == pytest.approx(100) and max(x0, x1) == pytest.approx(100) and z0 == pytest.approx(20) and z1 == pytest.approx(20)
    return next(e for e in refs.subformas(forma, "arista") if esta(e))


@pytest.mark.parametrize("tipo,angulo", [("normal", 0), ("tangente", 0), ("normal", 30), ("tangente", -45)])
def test_la_direccion_de_la_asa_es_la_misma_con_que_sale_la_reglada(tipo, angulo):
    forma = caja_100()
    e = arista_de_arriba(forma)
    d = sf.direccion_reglada(e, forma, tipo, angulo)
    assert np.linalg.norm(d) == pytest.approx(1.0)
    resultado = sf.reglada([e], 7.0, angulo, tipo=tipo, referencia=forma)
    desplazada = geo.trasladar(e, d * 7.0)
    (a0, a1), (b0, b1) = geo.caja_envolvente(e), geo.caja_envolvente(desplazada)
    esperada = (np.minimum(a0, b0), np.maximum(a1, b1))
    assert np.allclose(geo.caja_envolvente(resultado), esperada, atol=1e-6)


def test_la_direccion_de_la_asa_distingue_los_tipos_y_el_que_no_es_ninguno():
    forma = caja_100()
    e = arista_de_arriba(forma)            # una arista de la caja toca dos caras: sale por la primera que halla el kernel
    n, t = sf.direccion_reglada(e, forma, "normal"), sf.direccion_reglada(e, forma, "tangente")
    assert sorted(np.abs(np.round(n)).tolist()) == [0, 0, 1] and sorted(np.abs(np.round(t)).tolist()) == [0, 0, 1]
    assert abs(float(n @ t)) < 1e-9 and n.tolist() != t.tolist()      # la normal y el plano de la cara son perpendiculares
    assert sf.direccion_reglada(e, forma, "direccion") is None


def _doc_arista():
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="100", largo="60", alto="20"))
    return doc


def _panel(clave, doc, valores):
    from omnicad.ui.comando import ContextoComando, PanelComando
    from omnicad.ui.comandos import CATALOGO
    from omnicad.ui.visor3d import Visor3D
    visor = Visor3D()
    visor.resize(800, 600)
    visor.set_modelo(doc.estado_final)
    visor.vista("iso")
    visor.encuadrar()
    return PanelComando(CATALOGO[clave](), ContextoComando(doc, None), visor, valores), visor


def test_la_reglada_normal_y_tangente_muestran_flecha_y_arco(app_qt):
    from omnicad.ui import manipuladores as mp
    from omnicad.ui.comando import hit_desde_ref
    doc = _doc_arista()
    cid = next(iter(doc.estado_final.cuerpos))
    forma = doc.estado_final.cuerpos[cid].forma
    hit = hit_desde_ref(refs.referencia(cid, arista_de_arriba(forma), forma), doc.estado_final)
    for tipo in ("normal", "tangente"):
        panel, _visor = _panel("reglada", doc, {"aristas": [hit], "tipo": tipo, "distancia": "5 mm", "angulo": "0 deg"})
        manips = panel.manipuladores.manips
        assert sorted(type(m).__name__ for m in manips) == ["Angulo", "Flecha"]
        flecha = next(m for m in manips if isinstance(m, mp.Flecha))
        esperada = sf.direccion_reglada(arista_de_arriba(forma), forma, tipo)
        assert flecha.clave == "distancia" and flecha.direccion == pytest.approx(esperada)
        panel.cancelar()
    panel, _visor = _panel("reglada", doc, {"aristas": [hit], "tipo": "normal", "distancia": "5 mm", "angulo": "90 deg"})
    flecha = next(m for m in panel.manipuladores.manips if isinstance(m, mp.Flecha))
    assert flecha.direccion == pytest.approx(sf.direccion_reglada(arista_de_arriba(forma), forma, "normal", 90))
    panel.cancelar()


def test_la_revolucion_de_superficie_muestra_el_arco_de_angulo(app_qt):
    from omnicad.ui.comando import hit_desde_ref
    doc = Documento()
    b = Boceto()
    b.agregar_linea((10, 0), (10, 20))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", plano="XZ", boceto=b))
    cid = next(iter(doc.estado_final.bocetos["op1"].boceto.curvas))
    curva = hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": cid}, doc.estado_final)
    eje = hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)
    panel, _visor = _panel("sup_revolucion", doc, {"curvas": [curva], "eje": [eje], "angulo": "90 deg"})
    manips = panel.manipuladores.manips
    assert [type(m).__name__ for m in manips] == ["Angulo"] and manips[0].clave == "angulo"
    asa = manips[0].asa(panel.manipuladores)
    assert math.hypot(asa[0], asa[1]) == pytest.approx(10.0, abs=1e-6)       # a la distancia del perfil al eje
    assert math.degrees(math.atan2(asa[1], asa[0])) == pytest.approx(90.0, abs=1e-6)
    panel.cancelar()
    panel, _visor = _panel("sup_revolucion", doc, {"curvas": [], "eje": [eje], "angulo": "90 deg"})
    assert not panel.manipuladores.manips          # sin perfil elegido todavía no hay asa
    panel.cancelar()


def test_un_factor_no_lleva_unidad_pero_una_longitud_si(app_qt):
    from omnicad.ui.comando import ContextoComando
    ctx = ContextoComando(Documento(), None)
    assert ctx.evaluar("2", "escalar") == 2.0 and ctx.evaluar("1.5*2", "escalar") == 3.0
    for malo in ("2 mm", "30°", "2 deg", "1.5*2 cm"):
        with pytest.raises(ErrorExpresion, match="no lleva unidad"):
            ctx.evaluar(malo, "escalar")
    assert ctx.evaluar("2 mm") == 2.0 and ctx.evaluar("30 deg", "angulo") == 30.0
    assert con_unidad("2 mm") and not con_unidad("2") and not con_unidad("ancho / 2")
    assert ctx.parametros.evaluar("2 mm", "escalar") == 2.0      # un archivo viejo con unidad sigue abriendo
