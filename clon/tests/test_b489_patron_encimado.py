"""B-489: un patrón de boceto con las copias encimadas (count1=1000, distance1=5 en «Extensión» sobre un 60×40) colgaba la
app (7,9 GB) o la cerraba con un fallo nativo al detectar los perfiles. Ahora falla con un mensaje claro ANTES de
partir, y el boceto queda como estaba."""
import time

from omnicad import api


def _sesion():
    s = api.Sesion()
    api.llamar(s, "create_sketch", {"plane": "XY", "name": "B"})
    return s


def _ids(r):
    assert r["ok"], r
    return [e["id"] for e in r["result"]["entities"]]


def test_b489_patron_de_mil_copias_encimadas_falla_claro_y_rapido():
    s = _sesion()
    rect = _ids(api.llamar(s, "draw_rectangle", {"x1": 0, "y1": 0, "x2": 60, "y2": 40}))
    t = time.perf_counter()
    r = api.llamar(s, "sketch_rectangular_pattern", {"entities": rect, "count1": 1000, "distance1": 5})
    assert time.perf_counter() - t < 20
    assert not r["ok"] and "Demasiadas curvas encimadas (4000)." in r["mensaje"], r
    assert len(api.llamar(s, "get_sketch", {})["result"]["entities"]) == 4    # el boceto quedó como estaba
    # Un patrón chico encimado sigue andando (19 perfiles).
    r = api.llamar(s, "sketch_rectangular_pattern", {"entities": rect, "count1": 10, "distance1": 5})
    assert r["ok"] and r["result"]["profiles"] == 19, r


def test_b489_rayos_por_un_punto_no_tiran_la_app():
    """300 rayos por el mismo punto: antes más de 22 GB (200: fallo nativo)."""
    s = _sesion()
    linea = _ids(api.llamar(s, "draw_line", {"start_x": -50, "start_y": 0, "end_x": 50, "end_y": 0}))
    r = api.llamar(s, "sketch_circular_pattern", {"entities": linea, "count": 300, "total_angle": 180})
    assert not r["ok"] and "curvas encimadas" in r["mensaje"], r
