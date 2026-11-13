"""CI-H77: la punta de un giro trae una arista degenerada (largo 0) que `%CIRCLE` no debe elegir: no se puede
empalmar («Las aristas elegidas no pertenecen al cuerpo») y, según la numeración del OCC de cada plataforma, caía
justo en `%CIRCLE[1]` del test de la silueta (falló en Windows Server, no en Linux ni en la PC)."""
from omnicad import api


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _bala():
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XZ", name="Perfil")
    puntos = [(0, 0), (35, 0), (35, 100), (25, 150), (0, 180)]
    for a, b in zip(puntos, puntos[1:] + puntos[:1], strict=True):
        _llamar(s, "draw_line", start_x=a[0], start_y=a[1], end_x=b[0], end_y=b[1])
    _llamar(s, "revolve", sketch="Perfil", profile=0, axis="Z")
    return s


def test_el_selector_circle_no_elige_la_arista_degenerada_de_la_punta():
    s = _bala()
    todas = _llamar(s, "find_edges")["edges"]
    circulos = _llamar(s, "find_edges", selector="%CIRCLE")["edges"]
    assert any(not e["length"] for e in todas)                        # la punta del cono (largo 0) sigue en la lista…
    assert [round(e["radius"]) for e in circulos] == [35, 35, 25]     # …pero %CIRCLE solo trae los círculos reales
    assert all(e["length"] > 0 for e in circulos)


def test_todo_circulo_que_ofrece_find_edges_se_puede_empalmar():
    for i in range(3):
        s = _bala()
        arista = _llamar(s, "find_edges", selector="%CIRCLE")["edges"][i]["id"]
        _llamar(s, "fillet", edges=[arista], radius=20)
