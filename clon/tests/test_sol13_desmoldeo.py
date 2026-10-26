"""SOL-13: desmoldeo con modo de ángulo relativo/absoluto y línea de partición."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _inclinacion_de_la_cara_x(s, cuerpo="Bloque"):
    """Ángulo (grados) de la cara lateral que mira a +X respecto de la vertical: positivo = se angosta hacia arriba."""
    forma = s.cuerpo(cuerpo).forma
    for c in geo.caras(forma):
        p = geo.plano_de_cara(c)
        if p is not None and p.normal[0] > 0.5:
            return math.degrees(math.asin(p.normal[2]))
    raise AssertionError("no hay cara +X plana")


def _bloque():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10, name="Bloque")
    return s


def test_modo_relativo_suma_y_absoluto_mide_desde_la_direccion():
    s = _bloque()
    llamar(s, "draft", faces=">X", angle=5, neutral="XY")
    assert _inclinacion_de_la_cara_x(s) == pytest.approx(5)
    llamar(s, "draft", faces=">X", angle=5, neutral="XY", angle_mode="relative")      # relativo: 5 + 5
    assert _inclinacion_de_la_cara_x(s) == pytest.approx(10)
    llamar(s, "draft", faces=">X", angle=5, neutral="XY", angle_mode="absolute")     # absoluto: vuelve a 5
    assert _inclinacion_de_la_cara_x(s) == pytest.approx(5)
    r = api.llamar(s, "draft", {"faces": ">X", "angle": 85, "neutral": "XY", "angle_mode": "relative"})        # 5 + 85 = 90: no se puede
    assert not r["ok"]


def test_linea_de_particion_con_plano_equivale_al_plano_fijo():
    volumenes = []
    for tipo in ("parting_line", "fixed_plane"):
        s = _bloque()
        plano = llamar(s, "create_construction_plane", plane="XY", offset=5)["plane"]["id"]
        extra = dict(type="parting_line", pull_direction="XY", parting_tool=plano) if tipo == "parting_line"             else dict(neutral=plano)
        llamar(s, "draft", faces="#Z", angle=4, sides="symmetric", **extra)
        forma = s.cuerpo("Bloque").forma
        assert geo.es_valida(forma)
        volumenes.append(geo.volumen(forma))
    assert volumenes[0] == pytest.approx(volumenes[1]) and volumenes[0] < 4000


def test_linea_de_particion_con_curva_plana():
    volumenes = []
    for tipo in ("parting_line", "fixed_plane"):
        s = api.Sesion()
        llamar(s, "create_cylinder", radius=10, height=20, z=-10, name="Cil")          # z de -10 a 10; la curva queda en z=0
        sk = llamar(s, "create_sketch", plane="XY")
        circulo = llamar(s, "draw_circle", radius=10)
        curva = circulo["entities"][0]["id"]
        extra = dict(type="parting_line", pull_direction="XY", parting_tool={"sketch": sk["sketch"]["id"], "curve": curva})             if tipo == "parting_line" else dict(neutral="XY")
        llamar(s, "draft", faces="%CYLINDER", angle=3, angle_mode="absolute", sides="symmetric", **extra)
        volumenes.append(geo.volumen(s.cuerpo("Cil").forma))
    assert volumenes[0] == pytest.approx(volumenes[1]) and volumenes[0] < math.pi * 100 * 20


def test_linea_de_particion_pide_sus_datos():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=20, name="Cil")
    for args in ({"pull_direction": "XY"}, {"parting_tool": "XY"}):
        r = api.llamar(s, "draft", {"faces": "%CYLINDER", "angle": 3, "type": "parting_line", **args})
        assert not r["ok"]


def test_mover_linea_de_particion_gira_la_cara_entera_alrededor_de_su_borde():
    """above: bisagra en el borde más atrás de la extracción (z = 0) = plano fijo en z = 0; below: z = 10; both: la línea."""
    def volumen(**extra):
        s = _bloque()
        plano = llamar(s, "create_construction_plane", plane="XY", offset=5)["plane"]["id"]
        if "neutral" in extra and extra["neutral"] == "arriba":
            extra["neutral"] = llamar(s, "create_construction_plane", plane="XY", offset=10)["plane"]["id"]
        if extra.get("type") == "parting_line":
            extra.update(pull_direction="XY", parting_tool=plano)
        llamar(s, "draft", faces=">X", angle=5, **extra)
        forma = s.cuerpo("Bloque").forma
        assert geo.es_valida(forma)
        return geo.volumen(forma)
    mover = dict(type="parting_line", parting_line_type="move")
    assert volumen(**mover, move_direction="above") == pytest.approx(volumen(neutral="XY"), rel=1e-9)
    assert volumen(**mover, move_direction="below") == pytest.approx(volumen(neutral="arriba"), rel=1e-9)
    assert volumen(**mover, move_direction="both") == pytest.approx(volumen(type="parting_line"), rel=1e-9)
    assert volumen(**mover, move_direction="above") != pytest.approx(volumen(**mover, move_direction="below"), rel=1e-6)
    r = api.llamar(_bloque(), "draft", {"faces": ">X", "angle": 5, "parting_line_type": "move"})
    assert not r["ok"] and "parting_line" in r["mensaje"]
    s = _bloque()
    plano = llamar(s, "create_construction_plane", plane="XY", offset=5)["plane"]["id"]
    llamar(s, "draft", faces=">X", angle=5, type="parting_line", pull_direction="XY", parting_tool=plano,
           parting_line_type="move", fixed_edges="nearest:[10,0,10]")                  # bisagra en la arista de arriba
    assert geo.es_valida(s.cuerpo("Bloque").forma)
