"""B-250: la cresta exterior con clase queda al centro de tolerancia, como en Fusion."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.timeline.documento import Documento
from tests.test_rosca_diametros_tabla import d_max, d_min


def _llamar(sesion, nombre, **argumentos):
    resultado = api.llamar(sesion, nombre, argumentos)
    assert resultado["ok"], resultado
    return resultado["result"]


def _forma(sesion):
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma)
    return forma


def _exterior(designacion, clase, holgura=0):
    datos = sc.datos_rosca(designacion)
    sesion = api.Sesion()
    _llamar(sesion, "create_cylinder", radius=datos["diametro"] / 2, height=4 * datos["paso"])
    _llamar(sesion, "create_thread", faces="%CYLINDER", thread=designacion, thread_class=clase,
            modeled=True, print_clearance=holgura)
    return sesion


def test_m20_6g_da_el_diametro_mayor_medido_en_fusion():
    assert d_max(_forma(_exterior("M20", "6g"))) == pytest.approx(19.79, abs=0.005)


def test_m3_6g_da_el_diametro_mayor_medido_en_fusion():
    assert d_max(_forma(_exterior("M3", "6g"))) == pytest.approx(2.927, abs=0.005)


def test_unc_2a_da_el_diametro_mayor_medido_en_fusion():
    assert d_max(_forma(_exterior("3/4-10 UNC", "2A"))) == pytest.approx(18.839, abs=0.005)


def test_las_otras_familias_metricas_sin_tabla_usan_el_mismo_centro():
    for designacion in ("ANSI M20x2.5", "GB M20x2.5"):
        assert d_max(_forma(_exterior(designacion, "6g"))) == pytest.approx(19.79, abs=0.005)


def test_afbma_3a_con_tabla_conserva_sus_diametros_y_volumen():
    forma = _forma(_exterior("AFBMA N 04", "3A"))
    assert d_max(forma) == pytest.approx(19.7688, abs=0.001)
    assert geo.volumen(forma) == pytest.approx(928.335496, abs=0.001)


def test_el_perfil_basico_conserva_su_diametro_y_volumen():
    forma = _forma(_exterior("M20", ""))
    assert d_max(forma) == pytest.approx(20, abs=0.001)
    assert geo.volumen(forma) == pytest.approx(2689.708645, abs=0.001)


def test_la_rosca_interior_conserva_su_diametro_y_volumen():
    sesion = api.Sesion()
    _llamar(sesion, "create_cylinder", radius=10, height=6)
    _llamar(sesion, "create_hole", face=">Z", diameter=8.5, through_all=True)
    caras = _llamar(sesion, "find_faces", selector="%CYLINDER")["faces"]
    cara = min(caras, key=lambda c: c["radius"])["id"]
    _llamar(sesion, "create_thread", faces=cara, thread="M10", thread_class="6H", modeled=True)
    forma = _forma(sesion)
    assert d_min(forma) == pytest.approx(8.5, abs=0.001)
    assert geo.volumen(forma) == pytest.approx(1485.669163, abs=0.001)


def test_la_holgura_radial_se_aplica_al_centro_de_la_clase():
    assert d_max(_forma(_exterior("M20", "6g", 0.1))) == pytest.approx(19.5905, abs=0.001)


def test_la_receta_vieja_conserva_el_diametro_nominal():
    receta = _exterior("M20", "6g").doc.a_dict()
    del receta["operaciones"][-1]["params"]["version_rosca"]
    documento = Documento.desde_dict(receta)
    forma = next(iter(documento.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma)
    assert d_max(forma) == pytest.approx(20, abs=0.001)
