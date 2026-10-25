"""SOL-26: Buscar componentes similares."""
from omnicad import api


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _escena():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=10, height=5, name="A")
    llamar(s, "create_box", length=20, width=10, height=5, name="B", x=50)
    llamar(s, "move_body", body="B", rotate=[0, 0, 90], pivot="center")      # girada: sigue siendo un duplicado
    llamar(s, "create_box", length=20.2, width=10, height=5, name="C", x=100)   # 1 % más larga
    llamar(s, "create_box", length=26, width=10, height=5, name="D", x=150)     # ~30 %: ya no se parece
    llamar(s, "create_cylinder", radius=4, height=30, name="E", x=200)
    for n in "ABCDE":
        llamar(s, "create_component", bodies=[n], name="Comp" + n)
    return s


def test_duplicado_y_muy_similar_aunque_este_girado():
    s = _escena()
    r = llamar(s, "find_similar_components", component="CompA")
    estados = {m["name"]: m["status"] for m in r["components"][0]["matches"]}
    assert estados == {"CompB": "duplicate", "CompC": "highly_similar"}
    assert r["compared"] == 5


def test_sin_componente_lista_los_que_tienen_coincidencias():
    s = _escena()
    r = llamar(s, "find_similar_components")
    nombres = {c["name"] for c in r["components"]}
    assert nombres == {"CompA", "CompB", "CompC"}      # D y E no tienen pareja


def test_errores():
    s = _escena()
    assert not api.llamar(s, "find_similar_components", {"component": "no existe"})["ok"]
