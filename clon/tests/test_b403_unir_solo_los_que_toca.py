"""B-403 / FL-4: Unir con «Objetos» vacío opera solo contra los cuerpos que toca; un cuerpo lejano cuesta una caja
envolvente, no una booleana ni un volumen. Con 11 cuerpos el texto tarda lo mismo que con 1 y da el mismo resultado."""
from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(s, nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], r
    return r["result"]


def escena(n):
    s = api.Sesion()
    for i in range(n):
        b = llamar(s, "create_sketch", plane="XY")["sketch"]["id"]
        llamar(s, "create_polygon", sides=60, center_x=i * 400, center_y=0, radius=60)     # lejos unos de otros
        llamar(s, "extrude", sketch=b, profile=0, distance=20)
    t = llamar(s, "create_sketch", plane="XY", name="Texto")["sketch"]["id"]
    llamar(s, "add_text", text="EMILIA", x=-40, y=-10, height=30)
    return s, t


def unir_texto(n, monkeypatch):
    s, t = escena(n)
    llamadas = []
    original = geo.booleano
    monkeypatch.setattr(geo, "booleano", lambda *a, **k: (llamadas.append(1), original(*a, **k))[1])
    llamar(s, "extrude", sketch=t, profile="text", distance="0.563 mm", operation="join")
    monkeypatch.undo()
    return s, len(llamadas)


def test_un_cuerpo_que_no_toca_no_se_une_ni_cambia_el_resultado(monkeypatch):
    s1, b1 = unir_texto(1, monkeypatch)
    s11, b11 = unir_texto(11, monkeypatch)
    assert b1 == b11 == 1                                     # una sola booleana, contra el que toca
    c1, c11 = s1.doc.estado_final.cuerpos, s11.doc.estado_final.cuerpos
    assert len(c1) == 1 and len(c11) == 11
    assert geo.volumen_exacto(next(iter(c11.values())).forma) == geo.volumen_exacto(next(iter(c1.values())).forma)
    lejanos = list(c11.values())[1:]
    assert all(geo.volumen_exacto(c.forma) > 0 for c in lejanos)      # los otros 10 siguen enteros
