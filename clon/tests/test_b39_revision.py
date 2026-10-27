"""Regresiones de la revisión de B-39: geometría completa, material y mallas reutilizables."""
import math

import pytest
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Geom2d import Geom2d_Line
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Dir2d, gp_Pnt2d

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import intercambio


def _caja_con_pcurva_desplazada():
    forma = geo.caja(10, 10, 10)
    cara = geo.caras(forma)[0]
    arista = geo._aristas_unicas(cara)[0]
    BRep_Builder().UpdateEdge(arista, Geom2d_Line(gp_Pnt2d(1000, 1000), gp_Dir2d(1, 0)), cara, 1e-7)
    return forma


@pytest.mark.parametrize("tras_booleana", [False, True])
def test_b39_validar_no_omite_la_geometria(tras_booleana):
    forma = _caja_con_pcurva_desplazada()
    assert not BRepCheck_Analyzer(forma, GeomControls=True, theIsParallel=False).IsValid()
    assert BRepCheck_Analyzer(forma, GeomControls=False, theIsParallel=False).IsValid()
    valida = geo._es_valida_tras_booleana(forma, ()) if tras_booleana else geo.es_valida(forma)
    assert not valida


def _llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def test_b39_check_geometry_detecta_pcurva_desplazada():
    sesion = api.Sesion()
    _llamar(sesion, "run_operation", type="operacion_base", params={"cuerpos": [{
        "id": "x.c1", "nombre": "Desajustada", "tipo": "solido",
        "brep": intercambio.brep_a_texto(_caja_con_pcurva_desplazada()),
    }]})
    informe = _llamar(sesion, "check_geometry", body="Desajustada", self_intersection=False)
    assert not informe["all_valid"]
    assert not informe["bodies"][0]["valid"]
    assert informe["bodies"][0]["errors"] > 0


@pytest.mark.parametrize("radio, saliente", [(2.5, 0.005), (25, 0.075)])
def test_b39_casquete_pequeno_no_se_confunde_con_herramienta_enterrada(radio, saliente):
    base = geo.booleano(geo.caja(8 * radio, 8 * radio, 8 * radio),
                       geo.caja(4 * radio, 4 * radio, 4 * radio, (2 * radio,) * 3), "cortar")
    herramienta = geo.esfera(radio, (radio + saliente, 4 * radio, 4 * radio))
    volumen_antes = geo.volumen_exacto(base)
    resultado = geo.booleano(base, herramienta, "unir")
    casquete = math.pi * saliente**2 * (radio - saliente / 3)
    assert geo.volumen_exacto(resultado) - volumen_antes == pytest.approx(casquete, abs=2e-6)
    assert BRepCheck_Analyzer(resultado, GeomControls=True, theIsParallel=False).IsValid()
    assert geo._aristas_defectuosas(resultado) == (0, 0)


def test_b39_api_conserva_casquete_al_consumir_la_herramienta():
    sesion = api.Sesion()
    base = _llamar(sesion, "create_box", length=200, width=200, height=200,
                   anchor="corner", name="Carcasa")["bodies_created"][0]["id"]
    _llamar(sesion, "create_box", length=100, width=100, height=100, x=50, y=50, z=50,
            anchor="corner", operation="cut", target=base)
    volumen_antes = geo.volumen_exacto(sesion.cuerpo(base).forma)
    esfera = _llamar(sesion, "create_sphere", radius=25, x=25.075, y=100, z=100)["bodies_created"][0]["id"]
    _llamar(sesion, "boolean_operation", target=base, tools=[esfera], operation="join")
    casquete = math.pi * 0.075**2 * (25 - 0.075 / 3)
    assert len(sesion.doc.estado_final.cuerpos) == 1
    assert geo.volumen_exacto(sesion.cuerpo(base).forma) - volumen_antes == pytest.approx(casquete, abs=2e-6)
    informe = _llamar(sesion, "check_geometry", body=base, self_intersection=False)
    assert informe["all_valid"] and informe["all_closed"]
    assert informe["bodies"][0]["free_edges"] == informe["bodies"][0]["non_manifold_edges"] == 0


def test_b39_contencion_admite_herramienta_hueca():
    base = geo.caja(20, 20, 20)
    hueca = geo.booleano(geo.caja(10, 10, 10, (5, 5, 5)), geo.esfera(2, (10, 10, 10)), "cortar")
    resultado = geo.booleano(base, hueca, "unir")
    assert resultado is base
    assert geo.volumen_exacto(resultado) == pytest.approx(8000)
    assert geo.es_valida(resultado)


def test_b39_contencion_en_un_cuerpo_de_varios_solidos():
    base = geo.compuesto([geo.caja(10, 10, 10), geo.caja(10, 10, 10, (20, 0, 0))])
    herramienta = geo.compuesto([geo.caja(2, 2, 2, (2, 2, 2)), geo.caja(2, 2, 2, (22, 2, 2))])
    resultado = geo.booleano(base, herramienta, "unir")
    assert resultado is base
    assert geo.volumen_exacto(resultado) == pytest.approx(2000)
    assert len(geo.solidos(resultado)) == 2 and geo.es_valida(resultado)


def _caras_malladas(forma):
    return sum(BRep_Tool.Triangulation_s(cara, TopLoc_Location()) is not None for cara in geo.caras(forma))


def test_b39_unificar_conserva_mallas_existentes():
    cilindro = geo.cilindro(10, 20)
    BRepMesh_IncrementalMesh(cilindro, 0.05, False, 0.3, True)
    assert _caras_malladas(cilindro) == 3
    resultado = geo.unificar_caras(cilindro)
    assert _caras_malladas(resultado) == 3
    assert geo.volumen_exacto(resultado) == pytest.approx(math.pi * 100 * 20)
    assert geo.es_valida(resultado)


def test_b39_union_reutiliza_caras_intactas_y_sus_mallas():
    base = geo.booleano(geo.caja(60, 40, 10), geo.cilindro(3, 12, (15, 20, -1)), "cortar")
    BRepMesh_IncrementalMesh(base, 0.05, False, 0.3, True)
    caras_antes = geo.caras(base)
    volumen_antes = geo.volumen_exacto(base)
    herramienta = geo.caja(10, 10, 5, (40, 15, 10))
    resultado = geo.booleano(base, herramienta, "unir")
    assert _caras_malladas(resultado) == len(caras_antes) - 1  # solo cambia la cara de arriba, donde se agrega el saliente
    assert geo.volumen_exacto(resultado) == pytest.approx(volumen_antes + 500)
    assert geo.volumen_exacto(base) == pytest.approx(volumen_antes)
    assert BRepCheck_Analyzer(base, GeomControls=True, theIsParallel=False).IsValid()
    assert BRepCheck_Analyzer(resultado, GeomControls=True, theIsParallel=False).IsValid()
    assert geo._aristas_defectuosas(resultado) == (0, 0)


@pytest.mark.parametrize("x, volumen_esperado, cambia", [(150, 328, False), (1, 324, True)])
def test_b39_revision_reconoce_copias_de_caras_intactas(monkeypatch, x, volumen_esperado, cambia):
    base = geo.compuesto([geo.caja(2, 2, 2, (3 * i, 0, 0)) for i in range(40)])
    herramienta = geo.caja(2, 2, 2, (x, 0, 0))
    resultado, intactas = geo._booleana(base, herramienta, "unir", con_historial=True)
    revisadas = []
    original = geo.BRepCheck_Analyzer

    def analizar(forma, *args, **kwargs):
        revisadas.append(len(geo.caras(forma)))
        return original(forma, *args, **kwargs)

    monkeypatch.setattr(geo, "BRepCheck_Analyzer", analizar)
    assert geo._es_valida_tras_booleana(resultado, (base, herramienta), intactas)
    if cambia:
        assert 0 < sum(revisadas) < len(geo.caras(resultado))  # se revisa lo nuevo, sin omitir las caras cambiadas
    else:
        assert revisadas == [0]  # todas las caras pertenecían a las entradas, aunque sus copias tengan otra identidad
    assert geo.volumen_exacto(resultado) == pytest.approx(volumen_esperado)
    assert BRepCheck_Analyzer(resultado, GeomControls=True, theIsParallel=False).IsValid()
