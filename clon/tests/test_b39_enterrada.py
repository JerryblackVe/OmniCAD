# -*- coding: utf-8 -*-
"""B-39: unir una herramienta 100 % enterrada en la pared de una carcasa no suma volumen y no deja aristas libres.

El caso original (cilindro r2,5 en la carcasa del motor, arista libre en (27, 0, 129,5)) no se pudo reproducir
con ningún modelo guardado ni con este montaje; el test fija el comportamiento correcto para que una regresión se vea.
Además, el atajo de «herramienta enterrada» devuelve el cuerpo original SIN pasar por la fusión del kernel: los tests
de atajo espían `_booleana` y exigen que no haya ninguna llamada a «unir»."""
import pytest

from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision as rv


@pytest.mark.parametrize("x0, largo", [(27.0, 2.0), (27.0, 2.5), (27.2, 2.3)])
def test_b39_herramienta_enterrada_en_la_pared_no_suma_ni_deja_aristas_libres(x0, largo):
    pared = geo.booleano(geo.cilindro(30, 140, (0, 0, 0)), geo.cilindro(27, 140, (0, 0, 0)), "cortar")
    herramienta = geo.cilindro(2.5, largo, (x0, 0, 129.5), eje=(1, 0, 0))      # apoyada tangente a la cara interior
    unida = geo.booleano(pared, herramienta, "unir")
    informe = rv.revisar(unida, autointersecciones=False)
    assert geo.volumen(unida) == pytest.approx(geo.volumen(pared), abs=1e-6)
    assert geo.es_valida(unida) and rv.es_estanca(unida) and len(geo.solidos(unida)) == 1
    assert informe["aristas_libres"] == 0 and informe["aristas_no_manifold"] == 0


# ---------------------------------------------------------------- atajo: herramienta enterrada sin fusión del kernel
def _espiar_booleana(monkeypatch):
    """Reemplaza `geo._booleana` por un espía que anota la operación de cada pasada del kernel."""
    original, llamadas = geo._booleana, []

    def espia(objetivo, herramienta, operacion, **kw):
        llamadas.append(operacion)
        return original(objetivo, herramienta, operacion, **kw)

    monkeypatch.setattr(geo, "_booleana", espia)
    return llamadas


def _pared():
    return geo.booleano(geo.cilindro(30, 140), geo.cilindro(27, 140), "cortar")


def _carcasa():
    ext = geo.caja(60, 50, 40, (-30, -25, 0))
    hueco = geo.caja(54, 44, 34, (-27, -22, 3))
    return geo.booleano(ext, hueco, "cortar")


def test_b39_herramienta_enterrada_en_la_pared_no_fusiona_en_el_kernel(monkeypatch):
    """El atajo (B-39) comprueba que no queda material fuera del cuerpo; nunca fusiona la herramienta enterrada."""
    pared = _pared()
    herramienta = geo.cilindro(2.5, 1.8, (0, 0, 70), eje=(1, 0, 0))          # al medio del espesor de la pared
    herramienta = geo.trasladar(herramienta, (27.4, 0, 0))
    llamadas = _espiar_booleana(monkeypatch)
    unida = geo.booleano(pared, herramienta, "unir")
    assert llamadas == ["cortar"], llamadas
    assert unida is pared                                                      # el cuerpo original, sin reconstruir
    assert geo.volumen(unida) == geo.volumen(pared) and len(geo.caras(unida)) == len(geo.caras(pared))
    assert geo.es_valida(unida) and rv.es_estanca(unida)
    assert rv.revisar(unida, autointersecciones=False)["aristas_libres"] == 0


def test_b39_herramienta_enterrada_en_la_carcasa_hueca_no_fusiona_en_el_kernel(monkeypatch):
    carcasa = _carcasa()
    cilindro = geo.cilindro(2.5, 2, (20, 15, 0.5))                            # enterrado en el piso (0–3 mm)
    llamadas = _espiar_booleana(monkeypatch)
    unida = geo.booleano(carcasa, cilindro, "unir")
    assert llamadas == ["cortar"], llamadas
    assert unida is carcasa
    assert geo.volumen(unida) == geo.volumen(carcasa) and len(geo.caras(unida)) == len(geo.caras(carcasa))
    assert geo.es_valida(unida) and rv.es_estanca(unida)


def test_b39_herramienta_que_roza_la_cara_desde_adentro_usa_el_atajo(monkeypatch):
    """Tangente a la cara interior: los vértices caen en ON y no queda material fuera del cuerpo."""
    carcasa = _carcasa()
    cilindro = geo.cilindro(2.5, 2.6, (27.0, 10, 20), eje=(1, 0, 0))          # toca la cara x=27 desde el material
    llamadas = _espiar_booleana(monkeypatch)
    unida = geo.booleano(carcasa, cilindro, "unir")
    assert llamadas == ["cortar"], llamadas
    assert unida is carcasa
    assert geo.volumen(unida) == geo.volumen(carcasa) and len(geo.caras(unida)) == len(geo.caras(carcasa))
    assert geo.es_valida(unida) and rv.es_estanca(unida)


def test_b39_cuando_el_objetivo_queda_enterrado_en_la_herramienta_tambien_acorta(monkeypatch):
    """Unir es simétrico: si el objetivo entero está dentro de la herramienta, devuelve la herramienta sin fusión."""
    llamadas = _espiar_booleana(monkeypatch)
    chica, grande = geo.caja(2, 2, 2, (4, 4, 4)), geo.caja(10, 10, 10)
    unida = geo.booleano(chica, grande, "unir")
    assert llamadas == ["cortar"], llamadas
    assert unida is grande
    assert geo.volumen_exacto(unida) == pytest.approx(1000)


def test_b39_cuerpos_que_no_estan_enterrados_siguen_por_el_kernel(monkeypatch):
    """El atajo no se cuela en una unión normal: eso sí pasa por la fusión."""
    llamadas = _espiar_booleana(monkeypatch)
    a, b = geo.caja(10, 10, 10), geo.caja(10, 10, 10, (5, 0, 0))
    unida = geo.booleano(a, b, "unir")
    assert "unir" in llamadas
    assert geo.volumen_exacto(unida) == pytest.approx(1500)


# ---------------------------------------------------------------- B-39 (fuzzer): el kernel devolvía resultados imposibles
# Los tres montajes salieron de `scripts/fuzz_b39.py` (semilla b39) y fallaban SIN avisar: la unión devolvía solo la
# herramienta, un cuerpo que «no tocaba» la pared o una forma vacía. `geo.booleano` ahora verifica el resultado y reintenta.
def _unir_creible(base, herramienta):
    unida = geo.booleano(base, herramienta, "unir")
    vb, vh, vu = (geo.volumen_exacto(f) for f in (base, herramienta, unida))
    assert max(vb, vh) - 1e-3 <= vu <= vb + vh + 1e-3
    assert geo.es_valida(unida)
    return unida, vb, vh, vu


def test_b39_esfera_centrada_a_un_micrometro_de_la_cara_interior_no_borra_la_pared():
    esfera = geo.esfera(5.774899598519848, (-25.0485835630025, 10.078120632701422, 40.294906809049834))
    unida, vb, vh, vu = _unir_creible(_pared(), esfera)
    assert vu > vb and len(geo.solidos(unida)) == 1          # antes: 806,7 mm³ (solo la esfera)


def test_b39_toro_que_cruza_la_pared_se_une_con_su_parte_de_afuera():
    toro = geo.toroide(2.4651789735093654, 1.3714429023683579)       # eje Z; girado al eje X como lo arma el fuzzer
    toro = geo.trasladar(geo.rotar(toro, (0, 0, 0), (0, 1, 0), 90), (-26.99695215674611, -0.46752031652268067, 112.5936192487904))
    unida, vb, vh, vu = _unir_creible(_pared(), toro)
    assert 35 < vu - vb < 50                                   # ~46 % del toro (91,5 mm³) queda del lado del hueco
    assert len(geo.solidos(unida)) == 1                        # antes: 2 sólidos, el toro «afuera» de la pared


def test_b39_union_con_solape_de_un_micrometro_no_queda_vacia():
    placa = geo.booleano(geo.caja(80, 60, 8, (-40, -30, 0)), geo.cilindro(10, 8), "cortar")
    r = 2.07862826
    perno = geo.cilindro(r, 5.4607566954, (0, 0, -2.7303783477))      # eje Z; girado al eje Y como lo arma el fuzzer
    perno = geo.trasladar(geo.rotar(perno, (0, 0, 0), (1, 0, 0), -90), (10, 0, 1e-6 - r))
    unida, vb, vh, vu = _unir_creible(placa, perno)
    assert vu == pytest.approx(vb + vh, abs=1e-3)              # antes: forma vacía, la placa desaparecía


def test_b39_booleano_reintenta_si_el_primer_resultado_es_imposible(monkeypatch):
    base, esfera = _pared(), geo.esfera(3, (28, 0, 70))
    original, llamadas = geo._booleana, []

    def primero_malo(objetivo, herramienta, operacion, *, con_historial=False, **kw):
        llamadas.append(kw)
        if not kw:
            return (herramienta, ()) if con_historial else herramienta
        return original(objetivo, herramienta, operacion, con_historial=con_historial, **kw)

    monkeypatch.setattr(geo, "_booleana", primero_malo)
    unida = geo.booleano(base, esfera, "unir")
    assert len(llamadas) >= 2 and geo.volumen_exacto(unida) > geo.volumen_exacto(base)


def test_b39_booleano_prefiere_el_error_claro_a_la_geometria_equivocada(monkeypatch):
    monkeypatch.setattr(geo, "_booleana", lambda objetivo, herramienta, operacion, **kw:
                        (herramienta, ()) if kw.get("con_historial") else herramienta)
    with pytest.raises(geo.ErrorGeometria, match="imposible"):
        geo.booleano(_pared(), geo.esfera(3, (28, 0, 70)), "unir")


def test_b39_unir_con_un_cuerpo_vacio_o_cortar_todo_sigue_siendo_legitimo():
    caja = geo.caja(10, 10, 10)
    assert geo.esta_vacia(geo.booleano(caja, geo.caja(2, 2, 2, (50, 50, 50)), "intersecar"))     # sin nada en común
    assert geo.esta_vacia(geo.booleano(geo.caja(2, 2, 2, (1, 1, 1)), caja, "cortar"))            # la herramienta cubre todo


def test_b39_union_general_descarta_un_resultado_que_pierde_material():
    a, b, c = geo.caja(10, 10, 10), geo.caja(10, 10, 10, (5, 0, 0)), geo.caja(10, 10, 10, (10, 0, 0))
    correcta = geo.unir_todos([a, b, c])
    assert geo.volumen_exacto(correcta) == pytest.approx(2000)
    assert geo._union_general_creible([a, b, c], correcta)
    assert not geo._union_general_creible([a, b, c], geo.caja(5, 5, 5))     # menos que la caja más grande
    assert not geo._union_general_creible([a, b, c], geo.compuesto([]))      # vacía


# ---------------------------------------------------------------- ruta completa por la API: crear, unir, guardar, reabrir
def test_b39_ruta_completa_carcasa_con_cilindro_enterrado(tmp_path, monkeypatch):
    from omnicad import api

    s = api.Sesion()

    def llamar(ses, nombre, **campos):
        r = api.llamar(ses, nombre, campos)
        assert r["ok"], (nombre, r)
        return r["result"]

    def volumen_limpio(ses, contexto):
        chk = llamar(ses, "check_geometry")
        assert chk["all_valid"] and chk["all_closed"], contexto
        for b in chk["bodies"]:
            assert b["free_edges"] == 0 and b["non_manifold_edges"] == 0, (contexto, b)
        return chk["bodies"][0]["volume"]

    carcasa = llamar(s, "create_box", length=60, width=50, height=40, x=0, y=0, z=0,
                     name="Carcasa")["bodies_created"][0]["id"]
    llamar(s, "create_box", length=54, width=44, height=34, x=0, y=0, z=3, operation="cut", target=carcasa)
    v_antes = volumen_limpio(s, "carcasa sin unir")
    cilindro = llamar(s, "create_cylinder", height=2, radius=2.5, x=20, y=15, z=0.5,
                      name="Tapon")["bodies_created"][0]["id"]

    original, pasadas = geo._booleana, []

    def espia(objetivo, herramienta, operacion, **kw):
        pasadas.append(operacion)
        return original(objetivo, herramienta, operacion, **kw)

    monkeypatch.setattr(geo, "_booleana", espia)
    r = api.llamar(s, "boolean_operation", {"target": carcasa, "tools": [cilindro], "operation": "join"})
    assert r["ok"], r
    assert "unir" not in pasadas, pasadas                    # el atajo confirmó una resta exterior vacía, sin fusión
    v_despues = volumen_limpio(s, "carcasa con el cilindro enterrado unido")
    assert v_despues == pytest.approx(v_antes, rel=1e-9)     # la unión no suma volumen

    ruta = str(tmp_path / "b39_carcasa.omnicad")
    llamar(s, "save_document", path=ruta)
    s2 = api.Sesion()
    r = api.llamar(s2, "open_document", {"path": ruta})
    assert r["ok"], r
    v_reabierta = volumen_limpio(s2, "tras reabrir")
    assert "unir" not in pasadas                            # el recálculo al reabrir tampoco fusiona
    assert v_reabierta == pytest.approx(v_antes, rel=1e-9)
