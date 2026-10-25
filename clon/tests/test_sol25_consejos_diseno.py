"""SOL-25: consejos de diseño (Design Advice): espesor, contrasalida, desmoldeo y filos."""
import pytest

from omnicad import api
from omnicad.nucleo import consejos_diseno as cd
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import plastico

REGLA = plastico.regla("ABS 2 mm")                      # espesor 1 a 3 mm, mínimo de desmoldeo 0,5°, filo 0,5 mm
Z = (0, 0, 1)


def _tipos(r):
    return {t: n for t, n in r["summary"].items() if n}


def test_caja_maciza_pared_gruesa_y_sin_desmoldeo():
    r = cd.consejos_de_diseno(geo.caja(20, 20, 10), Z, REGLA)
    assert r["faces"] == 6
    assert r["summary"]["too_thick"] == 6 and r["summary"]["draft"] == 4        # 4 laterales sin desmoldeo
    assert r["summary"]["undercut"] == 0 and r["summary"]["knife_edge"] == 0
    assert r["thickness"]["min"] == pytest.approx(10) and r["thickness"]["max"] == pytest.approx(20)
    assert all(a["advice"] for a in r["alerts"])


def test_caja_con_desmoldeo_no_alerta_desmoldeo():
    from omnicad.nucleo import solidos_modificar as sm
    caja = geo.caja(20, 20, 10)
    laterales = [c for c in geo.caras(caja) if abs(geo.plano_de_cara(c).normal[2]) < 1e-6]
    drafteada = sm.desmoldeo(caja, laterales, Z, 2, geo.Plano("XY"))
    assert cd.consejos_de_diseno(drafteada, Z, REGLA)["summary"]["draft"] == 0


def test_agujero_horizontal_es_contrasalida_y_vertical_no():
    bloque = geo.caja(30, 30, 30, (-15, -15, -15))
    horizontal = geo.booleano(bloque, geo.cilindro(4, 40, (-20, 0, 0), (1, 0, 0)), "cortar")
    vertical = geo.booleano(bloque, geo.cilindro(4, 40, (0, 0, -20), (0, 0, 1)), "cortar")
    assert cd.consejos_de_diseno(horizontal, Z, REGLA)["summary"]["undercut"] > 0
    assert cd.consejos_de_diseno(vertical, Z, REGLA)["summary"]["undercut"] == 0


def test_pared_fina_y_filo():
    fina = geo.booleano(geo.caja(20, 20, 10), geo.caja(19.2, 19.2, 10, (0.4, 0.4, 0.4)), "cortar")      # pared de 0,4 mm
    r = cd.consejos_de_diseno(fina, Z, REGLA)
    assert r["summary"]["too_thin"] > 0
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeWedge
    cuña = BRepPrimAPI_MakeWedge(40.0, 2.0, 20.0, 0.0).Shape()                  # base angulos de unos 5,7°
    assert cd.consejos_de_diseno(cuña, Z, REGLA)["summary"]["knife_edge"] > 0


def test_herramienta_design_advice():
    s = api.Sesion()
    r = api.llamar(s, "design_advice", {})
    assert not r["ok"]                                                         # sin cuerpos
    api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 10, "name": "Caja"})
    r = api.llamar(s, "design_advice", {"body": "Caja"})["result"]
    assert r["rule"] == "ABS 2 mm" and r["summary"]["draft"] == 4 and r["faces"] == 6
    assert all("/F" in a["face"] for a in r["alerts"])
    sin_grueso = api.llamar(s, "design_advice", {"body": "Caja", "ignore": ["thickness", "draft"]})["result"]
    assert sin_grueso["summary"]["too_thick"] == 0 and sin_grueso["summary"]["draft"] == 0
    otra = api.llamar(s, "design_advice", {"body": "Caja", "rule": "no existe"})
    assert not otra["ok"]
