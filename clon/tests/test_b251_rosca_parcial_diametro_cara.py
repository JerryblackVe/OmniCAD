"""B-251: una rosca parcial ajusta el diámetro de toda la cara, como lo medido en Fusion el 2026-11-08."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from tests.test_rosca_diametros_tabla import d_max, d_min


def _llamar(sesion, herramienta, **argumentos):
    resultado = api.llamar(sesion, herramienta, argumentos)
    assert resultado["ok"], resultado


def _crear_rosca(radio=10, designacion="AFBMA N 04", clase="3A", interna=False, **opciones):
    sesion = api.Sesion()
    if interna:
        _llamar(sesion, "create_box", length=40, width=40, height=30)
    _llamar(sesion, "create_cylinder", radius=radio, height=30, operation="cut" if interna else "new_body")
    _llamar(sesion, "create_thread", faces="%CYLINDER", thread=designacion, thread_class=clase, **opciones)
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma) and len(geo.solidos(forma)) == 1
    return forma


def _comprobar_fuera_del_tramo(forma, diametro, interna=False):
    """Las dos puntas siguen lisas, con el diámetro ajustado: el filete no se extendió."""
    area = math.pi * (diametro / 2) ** 2
    for z in (1, 27):
        losa = geo.booleano(forma, geo.caja(40, 40, 2, origen=(-20, -20, z)), "intersecar")
        assert (d_min(losa) if interna else d_max(losa)) == pytest.approx(diametro, abs=1e-3)
        assert geo.volumen(losa) == pytest.approx(2 * (1600 - area if interna else area), abs=1e-3)


def test_afbma_parcial_tornea_toda_la_cara_y_da_el_volumen_medido_en_fusion():
    for invertir in (False, True):
        forma = _crear_rosca(length=10, offset=5, reverse=invertir)
        assert geo.volumen(forma) == pytest.approx(9062.6, abs=1)
        _comprobar_fuera_del_tramo(forma, 19.7688)


def test_la_rosca_completa_conserva_los_valores_anteriores():
    forma = _crear_rosca()
    # Las medidas de main antes de B-251 (2026-11-12). Solo la integración adaptativa: la de `geo.volumen` (sin ella) no es
    # exacta en esta hélice y cambia con la plataforma (B-379: 8950,29 en Linux y 8714,02 en Windows, con el mismo OCP).
    # Relativa: el kernel arma una hélice apenas distinta en cada plataforma (adaptativa: 8774,16 en Linux, 8771,73 en
    # Windows, 0,03 %); 0,1 % sigue atrapando un cambio real de la rosca.
    assert geo.volumen_exacto(forma, 1e-6) == pytest.approx(8774.158769, rel=1e-3)
    assert d_max(forma) == pytest.approx(19.769, abs=1e-3)


def test_la_rosca_parcial_rellena_toda_la_cara_exterior():
    forma = _crear_rosca(designacion="M30", clase="6g", length=10, offset=5)
    _comprobar_fuera_del_tramo(forma, 29.7345)
    assert geo.volumen_exacto(forma, 1e-6) < math.pi * (29.7345 / 2) ** 2 * 30


def test_la_rosca_parcial_ajusta_todo_el_agujero_al_tornear_o_rellenar():
    for radio in (3, 7):
        forma = _crear_rosca(radio, "M10", "6H", interna=True, length=10, offset=5)
        _comprobar_fuera_del_tramo(forma, 8.5262, interna=True)
        assert geo.volumen_exacto(forma, 1e-6) < (1600 - math.pi * (8.5262 / 2) ** 2) * 30


def test_las_roscas_parciales_cosmeticas_conservan_el_diametro_y_el_volumen():
    for radio, designacion, clase, interna in ((10, "AFBMA N 04", "3A", False), (10, "M30", "6g", False),
                                              (3, "M10", "6H", True), (7, "M10", "6H", True)):
        forma = _crear_rosca(radio, designacion, clase, interna, length=10, offset=5, modeled=False)
        _comprobar_fuera_del_tramo(forma, 2 * radio, interna)
        area = math.pi * radio ** 2
        assert geo.volumen(forma) == pytest.approx(30 * (1600 - area if interna else area), abs=1e-3)
