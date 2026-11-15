"""B-497 y B-476: el tamaño automático de la Rosca elige como Fusion entre todas las filas de sus tablas (Ø20 → M20,
Ø9,3 → M9×1,25, Ø100 → M100); una receta vieja (sin `version_tamano`) conserva el tamaño que elegía antes."""
import pytest

from omnicad import api
from omnicad.timeline.documento import Documento


def _rosca_automatica(diametro):
    s = api.Sesion()
    assert api.llamar(s, "create_cylinder", {"radius": diametro / 2, "height": 30})["ok"]
    r = api.llamar(s, "create_thread", {"faces": "%CYLINDER", "modeled": False})     # cosmética: solo importa el tamaño
    assert r["ok"], r
    return s


@pytest.mark.parametrize("diametro, designacion", [(20, "M20x2.5"), (9.3, "M9x1.25"), (100, "M100x6")])
def test_b497_el_tamano_automatico_es_el_de_fusion(diametro, designacion):
    s = _rosca_automatica(diametro)
    assert s.doc.operaciones[-1].roscas[0]["designacion"] == designacion


def test_b497_una_receta_vieja_conserva_su_tamano_automatico():
    datos = _rosca_automatica(9.3).doc.a_dict()
    del datos["operaciones"][-1]["params"]["version_tamano"]
    viejo = Documento.desde_dict(datos)
    assert viejo.operaciones[-1].p["version_tamano"] == 1 and viejo.operaciones[-1].p["version_rosca"] == 2
    viejo.estado_final                                      # recalcula
    assert viejo.operaciones[-1].roscas[0]["designacion"] == "M10x1.5"


def test_b520_el_nucleo_elige_el_mismo_tamano_que_la_app():
    """`rosca` sin designación (núcleo puro, agentes) elige como «Automático»: Ø9,3 → M9×1,25, no M10."""
    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import solidos_crear as sc
    cilindro = geo.cilindro(4.65, 10)
    assert geo.volumen(sc.rosca(cilindro)) == pytest.approx(geo.volumen(sc.rosca(cilindro, designacion="M9x1.25")),
                                                             rel=1e-9)
