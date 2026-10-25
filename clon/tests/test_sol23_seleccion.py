"""SOL-23: conjuntos de selección, seleccionar por límite y por semilla y límite."""

from omnicad import api


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _dos_cajas():
    s = api.Sesion()
    llamar(s, "create_box", length=10, width=10, height=10, name="Chica")                  # centro en (0, 0, 5)
    llamar(s, "create_box", length=10, width=10, height=10, name="Lejos", x=100)
    return s


def test_por_limite_cuerpos_dentro_fuera_e_intersecados():
    s = _dos_cajas()
    base = dict(shape="box", center=[0, 0, 5], x_size=40, y_size=40, z_size=40)
    assert llamar(s, "select_by_boundary", **base)["bodies"] == ["op1.c1"]
    assert llamar(s, "select_by_boundary", selection="outside", **base)["bodies"] == ["op2.c1"]
    corta = dict(shape="box", center=[0, 0, 5], x_size=10, y_size=4, z_size=4)           # cruza la caja chica
    assert llamar(s, "select_by_boundary", **corta)["bodies"] == []
    assert llamar(s, "select_by_boundary", intersected=True, **corta)["bodies"] == ["op1.c1"]
    esfera = llamar(s, "select_by_boundary", shape="sphere", center="Lejos", radius=30)
    assert esfera["bodies"] == ["op2.c1"]
    cil = llamar(s, "select_by_boundary", shape="cylinder", center="Chica", radius=30, length=30)
    assert cil["bodies"] == ["op1.c1"]


def test_por_limite_caras_y_aristas():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10, name="Bloque")               # x e y de -10 a 10, z de 0 a 10
    mitad = dict(shape="box", center=[0, 0, 10], x_size=40, y_size=40, z_size=4, kind="face")   # solo la tapa (z=10)
    assert len(llamar(s, "select_by_boundary", **mitad)["faces"]) == 1                    # solo la tapa cabe en z de 8 a 12
    caras = llamar(s, "select_by_boundary", **dict(mitad, z_size=40))["faces"]
    assert len(caras) == 6
    aristas = llamar(s, "select_by_boundary", shape="box", center=[0, 0, 10], x_size=40, y_size=40, z_size=4,
                     kind="edge")["edges"]
    assert len(aristas) == 4                                                             # las 4 aristas de la tapa


def test_semilla_y_limite_en_un_cilindro():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=20, name="Cil")
    # semilla: la cara lateral; límite: la tapa de arriba -> lateral + tapa de abajo
    lateral = llamar(s, "find_faces", selector="%CYLINDER")["faces"][0]["id"]
    sup = llamar(s, "find_faces", selector=">Z")["faces"][0]["id"]
    r = llamar(s, "select_by_seed_and_boundary", seed=lateral, boundary_faces=[sup])
    assert r["count"] == 2 and lateral in r["faces"] and sup not in r["faces"]
    aristas = llamar(s, "find_edges", selector=">Z")["edges"]
    ids = [a["id"] for a in aristas]
    r2 = llamar(s, "select_by_seed_and_boundary", seed=lateral, boundary_edges=ids)
    assert r2["count"] == 2 and sup not in r2["faces"]
    assert not api.llamar(s, "select_by_seed_and_boundary", {"seed": lateral})["ok"]
    assert not api.llamar(s, "select_by_seed_and_boundary", {"seed": sup, "boundary_faces": [sup]})["ok"]


def test_conjuntos_de_seleccion_crear_sumar_seleccionar_borrar():
    s = _dos_cajas()
    c = llamar(s, "manage_selection_sets", action="create", name="Tapas", faces=">Z", body="Chica")
    assert c["sets"][0]["faces"] == 1
    llamar(s, "manage_selection_sets", action="update", name="Tapas", bodies=["Lejos"])
    sel = llamar(s, "manage_selection_sets", action="select", name="Tapas")
    assert len(sel["faces"]) == 1 and sel["bodies"] == ["op2.c1"] and sel["missing"] == 0
    assert not api.llamar(s, "manage_selection_sets", {"action": "create", "name": "Tapas", "bodies": ["Chica"]})["ok"]
    llamar(s, "manage_selection_sets", action="rename", name="Tapas", new_name="Cubiertas")
    assert [x["name"] for x in llamar(s, "manage_selection_sets", action="list")["sets"]] == ["Cubiertas"]
    # sobrevive a guardar y reabrir la receta
    receta = s.doc.a_dict()
    assert "Cubiertas" in receta["espacios"]["conjuntos_seleccion"]
    llamar(s, "manage_selection_sets", action="delete", name="Cubiertas")
    assert llamar(s, "manage_selection_sets", action="list")["count"] == 0
    assert not api.llamar(s, "manage_selection_sets", {"action": "select", "name": "Cubiertas"})["ok"]
