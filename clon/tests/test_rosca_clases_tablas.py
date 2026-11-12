# -*- coding: utf-8 -*-
"""CAP-14: clase de tolerancia en los tipos de rosca que no son la métrica M ni la unificada (ACME, BSP y tuberías,
trapezoidal, autorroscantes, AFBMA…). Los valores salen de las tablas de Fusion (`tablas_rosca.CLASES`, que genera
`scripts/generar_tablas_rosca.py`); cada clase da los diámetros mayor, de flancos y menor de cada tamaño."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import tablas_rosca, tolerancias as tol

IN = 25.4
TUBO = "ISO G13.157x1.337"          # G 1/4 de la tabla de tuberías ISO: clases A (interior y exterior) y B (exterior)


def _datos(designacion):
    return sc.datos_rosca(designacion)


def _limites(designacion, clase, interna=None):
    d = _datos(designacion)
    return tol.limites_rosca(d["familia"], d["diametro"], d["paso"], clase, interna)


def test_acme_trae_las_clases_2g_3g_y_4g_de_fusion_con_sus_diametros():
    # 1/2-10 ACME, ASME B1.5 (XML de Fusion, en pulgadas): exterior 2G Ø flancos 0.4375, 3G 0.4426, 4G 0.4449;
    # interior 2G 0.4569, 3G 0.4532, 4G 0.4523
    for clase, ext, inte in (("2G", 0.4375, 0.4569), ("3G", 0.4426, 0.4532), ("4G", 0.4449, 0.4523)):
        assert _limites("1/2-10 ACME", clase, False)["diametro_flancos"] == pytest.approx([ext * IN] * 2, abs=1e-4)
        assert _limites("1/2-10 ACME", clase, True)["diametro_flancos"] == pytest.approx([inte * IN] * 2, abs=1e-4)
    interior = _limites("1/2-10 ACME", "3G", True)
    assert interior["interna"] is True and interior["diametro_menor"] == pytest.approx([0.4025 * IN] * 2, abs=1e-4)
    assert interior["diametro_mayor"][1] is None and interior["norma"] == "ASME B1.5"
    assert tol.CLASES_POR_FAMILIA["acme"] == {"2G": None, "3G": None, "4G": None}      # valen para los dos lados


def test_tuberia_iso_clase_a_vale_para_los_dos_lados_y_b_solo_para_el_eje():
    assert _limites(TUBO, "A", False)["diametro_flancos"] == pytest.approx([12.2385, 12.2385])
    assert _limites(TUBO, "B", False)["diametro_flancos"] == pytest.approx([12.176, 12.176])
    assert _limites(TUBO, "A", True)["diametro_flancos"] == pytest.approx([12.3635, 12.3635])
    assert _limites(TUBO, "A", True)["diametro_menor"] == pytest.approx([11.6675, 11.6675])
    assert _limites(TUBO, "A", None)["interna"] is False                # sin decirlo, la rosca exterior
    d = _datos(TUBO)
    with pytest.raises(geo.ErrorGeometria, match="no es de rosca interior"):
        tol.resolver_clase(d["familia"], d["diametro"], d["paso"], "B", True)
    assert tol.resolver_clase(d["familia"], d["diametro"], d["paso"], "B", False) == ("B", None)


def test_la_clase_corre_los_flancos_como_el_diametro_de_la_tabla():
    d = _datos(TUBO)
    base = (d["diametro_flancos"], d["diametro_menor"])                  # el perfil básico es el hilo interior A
    a = tol.desfases_rosca(d["familia"], d["diametro"], d["paso"], "A", False, *base)["flancos"]
    b = tol.desfases_rosca(d["familia"], d["diametro"], d["paso"], "B", False, *base)["flancos"]
    assert a == pytest.approx((12.3635 - 12.2385) / 2) and b == pytest.approx((12.3635 - 12.176) / 2)
    interior = tol.desfases_rosca(d["familia"], d["diametro"], d["paso"], "A", True, *base)
    assert interior["flancos"] == pytest.approx(0.0, abs=1e-9) and interior["menor"] == pytest.approx(0.0, abs=1e-9)


def test_auto_es_la_clase_de_fusion_de_cada_lado_y_los_solo_exterior_no_tienen_en_el_agujero():
    d = _datos(TUBO)
    assert tol.resolver_clase(d["familia"], d["diametro"], d["paso"], "auto", False) == ("A", None)
    assert tol.resolver_clase(d["familia"], d["diametro"], d["paso"], "auto", True) == ("A", None)
    assert tablas_rosca.CLASE_FUSION["afbma"] == ("3B", "3A")
    assert tablas_rosca.CLASE_FUSION["metrica_formado"] == (None, "6g")
    f = next(n for n, x in sc.TABLA_ROSCAS.items() if x["familia"] == "metrica_formado")
    d = _datos(f)
    assert tol.resolver_clase(d["familia"], d["diametro"], d["paso"], "auto", True) == ("", None)
    assert tol.resolver_clase(d["familia"], d["diametro"], d["paso"], "auto", False)[0] == "6g"


def test_clase_que_ese_tamano_no_tiene_da_un_error_claro():
    d = _datos("1/2-10 ACME")
    with pytest.raises(geo.ErrorGeometria, match="desconocida"):
        tol.limites_rosca("acme", d["diametro"], d["paso"], "7e")
    with pytest.raises(geo.ErrorGeometria, match="No hay datos de la clase 2G para este tamaño"):
        tol.limites_rosca("acme", 1.0, 0.1, "2G")                         # un tamaño que no existe


def test_toda_designacion_con_clases_existe_en_la_tabla_de_roscas():
    for familia, tabla in tablas_rosca.CLASES.items():
        faltan = [n for n in tabla if n not in sc.TABLA_ROSCAS]
        assert not faltan, (familia, faltan[:3])
        assert set(tablas_rosca.CLASES_FAMILIA[familia]) == {c for por_clase in tabla.values() for c in por_clase}


def test_trapezoidal_trae_7e_y_7h():
    assert tol.CLASES_POR_FAMILIA["trapezoidal"] == {"7e": False, "7H": True}
    lim = tol.limites_rosca("trapezoidal", 20, 4, "7e")
    assert lim["interna"] is False and lim["diametro_flancos"][0] == pytest.approx(17.7725)


@pytest.fixture
def s():
    return api.Sesion()


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _volumen_del_eje(clase):
    sesion = api.Sesion()
    llamar(sesion, "create_cylinder", radius=6.35, height=12)
    llamar(sesion, "create_thread", faces="%CYLINDER", thread="1/2-10 ACME", thread_class=clase, length=8)
    return geo.volumen(next(iter(sesion.doc.estado_final.cuerpos.values())).forma)


def test_create_thread_acme_con_clase_cambia_el_filete_en_la_direccion_correcta():
    # el exterior de la 4G tiene el Ø de flancos más grande que el de la 2G: se saca menos material
    v2g, v3g, v4g = (_volumen_del_eje(c) for c in ("2G", "3G", "4G"))
    assert v2g < v3g < v4g and v4g - v2g > 1.0


def test_thread_info_lista_las_clases_del_tamano_y_create_thread_rechaza_las_que_no_son(s):
    info = llamar(s, "thread_info", thread="1/2-10 ACME")
    assert info["classes"] == ["2G", "3G", "4G"]
    limites = llamar(s, "thread_info", thread="1/2-10 ACME", thread_class="3G")["limits"]
    assert limites[0]["class"] == "3G"
    llamar(s, "create_cylinder", radius=6.35, height=12)
    r = api.llamar(s, "create_thread", {"faces": "%CYLINDER", "thread": "1/2-10 ACME", "thread_class": "6g"})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"


def test_agujero_roscado_con_clase_de_tuberia_usa_la_clase_interior(s):
    llamar(s, "create_cylinder", radius=12, height=15)
    r = llamar(s, "create_hole", face=">Z", depth=12, hole_tap="modeled", thread="ISO G13.157x1.337", thread_class="A")
    assert r["bodies_modified"][0]["volume"] < math.pi * 144 * 15 - 1000                # sacó el agujero de la rosca
    mala = api.llamar(s, "create_hole", {"face": ">Z", "depth": 12, "hole_tap": "modeled", "thread": "ISO G13.157x1.337",
                                         "thread_class": "B"})
    assert not mala["ok"] and mala["error_kind"] == "INVALID_ARGUMENTS"
