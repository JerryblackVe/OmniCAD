"""SOL-15: mover o copiar caras, y escalar componentes."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _caja(s):
    llamar(s, "create_box", length=20, width=20, height=10, name="Cubo")       # x, y de −10 a 10; z de 0 a 10


def test_mover_una_cara_estira_el_cuerpo():
    s = api.Sesion()
    _caja(s)
    llamar(s, "move_faces", faces=">Z", translate=[0, 0, 5])
    forma = s.cuerpo("Cubo").forma
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(20 * 20 * 15)
    llamar(s, "undo")
    assert geo.volumen(s.cuerpo("Cubo").forma) == pytest.approx(4000)


def test_mover_con_direccion_y_distancia_negativa():
    s = api.Sesion()
    _caja(s)
    llamar(s, "move_faces", faces=">X", type="translate", direction="X", distance=-4)
    assert geo.volumen(s.cuerpo("Cubo").forma) == pytest.approx(16 * 20 * 10)


def test_girar_una_cara_alrededor_de_un_eje_la_inclina():
    s = api.Sesion()
    _caja(s)
    llamar(s, "move_faces", faces=">Z", type="rotate", axis="Y", angle=10)
    forma = s.cuerpo("Cubo").forma
    assert geo.es_valida(forma)
    assert geo.volumen(forma) != pytest.approx(4000, rel=1e-3)        # la tapa quedó inclinada


def test_copiar_la_cara_deja_el_cuerpo_y_crea_una_superficie():
    s = api.Sesion()
    _caja(s)
    r = llamar(s, "move_faces", faces=">Z", translate=[0, 0, 7], copy=True)
    assert geo.volumen(s.cuerpo("Cubo").forma) == pytest.approx(4000)
    nuevo = r["bodies_created"][0]["id"]
    assert s.cuerpo(nuevo).tipo == "superficie"
    assert geo.area(s.cuerpo(nuevo).forma) == pytest.approx(400)
    assert geo.caja_envolvente(s.cuerpo(nuevo).forma)[0][2] == pytest.approx(17)


def test_argumentos_invalidos():
    s = api.Sesion()
    _caja(s)
    for args in ({"faces": ">Z"}, {"faces": ">Z", "translate": [1, 2]}, {"faces": ">Z", "type": "rotate"},
                 {"faces": ">Z", "translate": [0, 0, 1], "direction": "Z"}):
        r = api.llamar(s, "move_faces", args)
        assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", args
    llamar(s, "create_cylinder", radius=3, height=10, x=40, name="Cil")
    r = api.llamar(s, "move_faces", {"faces": "nearest:[40,0,5]", "translate": [0, 0, 1], "body": "Cil"})
    assert not r["ok"]                                                  # cara cilíndrica: todavía no


def test_escalar_un_componente_escala_todos_sus_cuerpos():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="A")
    llamar(s, "create_box", length=10, width=10, height=10, name="B", x=30)
    llamar(s, "create_component", bodies=["A", "B"], name="Par")
    llamar(s, "scale_body", bodies="Par", factor=2)
    assert geo.volumen(s.cuerpo("A").forma) == pytest.approx(8000)
    assert geo.volumen(s.cuerpo("B").forma) == pytest.approx(8000)
