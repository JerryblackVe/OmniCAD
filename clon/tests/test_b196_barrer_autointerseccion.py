"""B-196: Barrer y Labio avisan si el resultado se cruza consigo mismo."""
import math
from unittest.mock import patch

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision as rev
from omnicad.nucleo import solidos_crear as sc


def _r(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r


def _preparar_barrido(cruzado=False):
    s = api.Sesion()
    _r(s, "create_sketch", plane="YZ", name="Perfil")
    _r(s, "draw_circle", radius=1, sketch="Perfil")
    _r(s, "create_sketch", plane="XY", name="Ruta")
    puntos = [(0, 0), (30, 0), (0, 20), (20, -10)] if cruzado else [(0, 0), (30, 0)]
    for a, b in zip(puntos[:-1], puntos[1:], strict=True):
        _r(s, "draw_line", sketch="Ruta", start_x=a[0], start_y=a[1], end_x=b[0], end_y=b[1])
    return s


def _barrer(s):
    return _r(s, "sweep", sketch="Perfil", path_sketch="Ruta", operation="new_body")


def _forma(s, r):
    return s.cuerpo(r["result"]["bodies_created"][0]["id"]).forma


def _exigir_aviso(s, r, que, causa):
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "aviso", r
    aviso = " ".join(r["avisos"]).lower()
    assert "autointerseccion" in aviso and que in aviso and causa in aviso, r


def test_barrido_cruzado_avisa_aunque_el_kernel_lo_de_valido():
    s = _preparar_barrido(True)
    r = _barrer(s)
    forma = _forma(s, r)
    assert geo.es_valida(forma)
    assert rev._autointersecciones_seguras(forma, 1, 5.0)[0] == 4
    assert math.isclose(geo.volumen(forma), math.pi * (30 + 2 * math.hypot(30, 20)), rel_tol=1e-6)
    _exigir_aviso(s, r, "barrido", "ruta")


def test_barrido_normal_sigue_ok_sin_aviso_y_con_el_mismo_volumen():
    s = _preparar_barrido()
    r = _barrer(s)
    forma = _forma(s, r)
    assert geo.es_valida(forma)
    assert math.isclose(geo.volumen(forma), math.pi * 30, rel_tol=1e-6)
    assert r["avisos"] == []
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "ok"


def test_barrido_de_cuerpo_tambien_revisa_el_resultado():
    """Inyecta una forma cruzada real: no depende de cómo una las copias Solid Sweep."""
    origen = _preparar_barrido(True)
    cruzada = _forma(origen, _barrer(origen))
    s = _preparar_barrido()
    _r(s, "create_box", length=2, width=2, height=2, name="Taco")
    with patch.object(sc, "barrer_cuerpo", return_value=cruzada):
        r = _r(s, "sweep", sweep_bodies="Taco", path_sketch="Ruta", orientation="parallel")
    _exigir_aviso(s, r, "barrido", "cuerpo")


def test_barrido_de_cuerpo_normal_no_avisa():
    s = _preparar_barrido()
    _r(s, "create_box", length=2, width=2, height=2, name="Taco")
    r = _r(s, "sweep", sweep_bodies="Taco", path_sketch="Ruta", orientation="parallel")
    forma = _forma(s, r)
    assert geo.es_valida(forma)
    assert math.isclose(geo.volumen(forma), 2 * 2 * (2 + 30), rel_tol=1e-6)
    assert r["avisos"] == []
    assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "ok"


def _preparar_labio(combinado=False):
    s = api.Sesion()
    _r(s, "create_box", length=40, width=20, height=20, anchor="corner", name="Base")
    if combinado:
        _r(s, "create_box", length=40, width=20, height=20, z=20, anchor="corner", name="Tapa")
    return s


def _labio(s, tipo):
    return _r(s, "create_lip_groove", body="Base", edges="|X and >Z and <Y", lip_type=tipo,
              groove_body="Tapa" if tipo == "lip_and_groove" else None,
              width=1, height=1.5, clearance=0.1, direction="Z")


def test_labio_y_ranura_revisan_el_resultado():
    """La geometría cruzada es real; se sustituye solo la salida del núcleo de Labio."""
    origen = _preparar_barrido(True)
    cruzada = _forma(origen, _barrer(origen))
    for tipo in ("lip", "groove", "lip_and_groove"):
        s = _preparar_labio(tipo == "lip_and_groove")
        funcion = "labio_y_ranura" if tipo == "lip_and_groove" else "labio_ranura"
        resultado = {"labio": cruzada, "ranura": cruzada} if tipo == "lip_and_groove" else cruzada
        with patch.object(sc, funcion, return_value=resultado):
            r = _labio(s, tipo)
        _exigir_aviso(s, r, "labio" if tipo == "lip" else "ranura", "ancho")
        aviso = " ".join(r["avisos"])
        assert aviso.count("quedó con 4 autointersecciones") == (2 if tipo == "lip_and_groove" else 1), r
        if tipo == "lip_and_groove":
            assert "El labio de «Base»" in aviso and "La ranura de «Tapa»" in aviso, r


def test_labio_y_ranura_normales_no_avisan():
    for tipo in ("lip", "groove", "lip_and_groove"):
        s = _preparar_labio(tipo == "lip_and_groove")
        r = _labio(s, tipo)
        forma = s.cuerpo("Base").forma
        esperado = 16000 - 40 * 1.1 * 1.6 if tipo == "groove" else 16000 + 40 * 1 * 1.5
        assert geo.es_valida(forma)
        assert math.isclose(geo.volumen(forma), esperado, rel_tol=1e-6)
        if tipo == "lip_and_groove":
            tapa = s.cuerpo("Tapa").forma
            assert geo.es_valida(tapa)
            assert math.isclose(geo.volumen(tapa), 16000 - 40 * 1.1 * 1.6, rel_tol=1e-6)
        assert r["avisos"] == []
        assert s.doc.resultado(r["result"]["feature"]["id"]).estado == "ok"


def test_barrido_con_revision_agotada_tambien_avisa():
    s = _preparar_barrido()
    with patch.object(rev, "_autointersecciones_seguras", return_value=(
            None, [{"mensaje": "No se revisaron las autointersecciones: plazo agotado."}], False)):
        r = _barrer(s)
    _exigir_aviso(s, r, "autointersecciones", "plazo agotado")
