"""Sección Proyectar/Incluir del boceto: B-119 (Proyectar un cuerpo da su silueta cerrada) y lo que arregló la revisión."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as g
from omnicad.nucleo.perfiles import detectar, silueta_forma


def _areas(prims, plano):
    return sorted(round(p.area, 1) for p in detectar([(p[0], i + 1, *p[2:]) for i, p in enumerate(prims)], plano))


def test_cilindro_acostado_da_un_rectangulo_y_un_perfil():
    prims, puntos = silueta_forma(g.cilindro(14, 47), g.Plano("XZ"))
    assert [p[0] for p in prims] == ["linea"] * 4 and puntos == []
    assert _areas(prims, g.Plano("XZ")) == [pytest.approx(28 * 47)]


def test_esfera_toro_y_agujero():
    assert [p[0] for p in silueta_forma(g.esfera(10), g.Plano("XZ"))[0]] == ["circulo"]
    toro = silueta_forma(g.toroide(20, 5), g.Plano("XZ"))[0]                   # de costado: un estadio
    assert _areas(toro, g.Plano("XZ")) == [pytest.approx(40 * 10 + 3.14159 * 25, abs=0.5)]
    placa = g.cortar_varias(g.caja(40, 40, 10), [g.cilindro(5, 10, (20, 20, 0))])
    prims = silueta_forma(placa, g.Plano("XY"))[0]                             # el agujero pasante queda
    assert sorted(p[0] for p in prims) == ["circulo"] + ["linea"] * 4


def test_las_aristas_de_adentro_no_entran():
    """Caja con un cilindro arriba, vista de frente: solo el contorno (Fusion no dibuja la arista donde se juntan)."""
    pieza = g.unir_todos([g.caja(40, 10, 10), g.cilindro(5, 30, (20, 5, 0))])
    prims = silueta_forma(pieza, g.Plano("XZ"))[0]
    assert len(prims) == 8 and _areas(prims, g.Plano("XZ")) == [pytest.approx(400 + 10 * 20)]


def test_forma_libre_tambien_cierra():
    """Un solevado B-spline (forma libre) va por el HLR en un proceso aparte: también da un solo perfil."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.BRepOffsetAPI import BRepOffsetAPI_ThruSections
    from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Elips, gp_Pnt
    solevado = BRepOffsetAPI_ThruSections(True, False)
    for curva in (gp_Circ(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 10), gp_Elips(gp_Ax2(gp_Pnt(0, 0, 20), gp_Dir(0, 0, 1)), 8, 4),
                  gp_Circ(gp_Ax2(gp_Pnt(0, 0, 40), gp_Dir(0, 0, 1)), 6)):
        solevado.AddWire(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(curva).Edge()).Wire())
    solevado.Build()
    assert g.es_forma_libre(solevado.Shape())
    assert _areas(silueta_forma(solevado.Shape(), g.Plano("XZ"))[0], g.Plano("XZ")) == [pytest.approx(640, rel=1e-3)]


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(s, nombre, **args):
    return ok(api.llamar(s, nombre, args))


def test_proyectar_cuerpo_curvo_asociativo_guardar_y_deshacer(tmp_path):
    """El caso del video de Gerardo: cuerpo de revolución, boceto en un plano por el eje, Proyectar › Cuerpos con vínculo."""
    s = api.Sesion()
    llamar(s, "create_parameter", name="r", expression="14 mm")
    llamar(s, "create_cylinder", radius="r", height=47)
    llamar(s, "create_sketch", plane="XZ")
    r = llamar(s, "project_to_sketch", bodies=["Cuerpo1"])
    info = llamar(s, "get_sketch")
    assert len(r["entities"]) == 4 and info["projections"][0]["mode"] == "silhouette"
    assert [p["area"] for p in info["profiles"]] == [pytest.approx(28 * 47)]
    llamar(s, "extrude", sketch="Boceto1", profile=0, distance=5)          # el perfil sirve para extruir
    llamar(s, "set_parameter", name="r", expression="20 mm")                  # el cuerpo cambia: la silueta lo sigue
    info = llamar(s, "get_sketch", sketch="Boceto1")
    assert not info["projections"][0]["lost"] and [p["area"] for p in info["profiles"]] == [pytest.approx(40 * 47)]
    ruta = str(tmp_path / "silueta.omnicad")
    llamar(s, "save_document", path=ruta)
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    info = llamar(otra, "get_sketch", sketch="Boceto1")
    assert info["projections"][0]["mode"] == "silhouette" and [p["area"] for p in info["profiles"]] == [
        pytest.approx(40 * 47)]
    for _ in range(3):                                                        # parámetro, extrusión y proyección
        llamar(s, "undo")
    assert "projections" not in llamar(s, "get_sketch", sketch="Boceto1")


def test_perfil_giratorio_de_un_cilindro_llega_al_eje_y_cierra_con_el_eje():
    """Spun Profile: las tapas giran en discos que llegan al eje. Antes quedaba solo la línea del costado (sin
    frentes) y el perfil no cerraba ni con el eje proyectado."""
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=10, height=30)
    llamar(s, "create_sketch", plane="XZ")
    llamar(s, "project_spun_profile", bodies=["Cuerpo1"], axis="Z", project_axis=True)
    info = llamar(s, "get_sketch")
    assert [p["area"] for p in info["profiles"]] == [pytest.approx(300)]
    llamar(s, "create_sketch", plane="XZ")
    llamar(s, "project_spun_profile", faces="%CYLINDER", axis="Z")              # la cara curva sola no toca el eje
    assert [e["length"] for e in llamar(s, "get_sketch")["entities"]] == [pytest.approx(30)]


def test_incluir_geometria_3d_deja_las_aristas_donde_estan_y_las_sigue():
    """Include 3D Geometry: antes se llevaba al plano (igual que Proyectar). Ahora la arista de arriba de la caja queda
    a z=10 sobre un boceto en XY, sigue al modelo y el vértice queda como punto 3D."""
    s = api.Sesion()
    llamar(s, "create_parameter", name="h", expression="10 mm")
    llamar(s, "create_box", length=20, width=10, height="h")
    llamar(s, "create_sketch", plane="XY")
    r = llamar(s, "include_3d_geometry", edges=[llamar(s, "find_edges", selector=">Z and |X")["edges"][0]["id"]],
               vertices=[[-10, -5, 0]])
    assert len(r["entities"]) == 1 and len(r["points"]) == 1
    alto = lambda: {round(p["z"], 6) for p in llamar(s, "get_sketch")["points_3d"] if p["z"] > 1}  # noqa: E731
    assert alto() == {10}
    llamar(s, "set_parameter", name="h", expression="15 mm")
    assert alto() == {15}
    assert not api.llamar(s, "include_3d_geometry", {})["ok"]


def test_si_unir_las_regiones_falla_igual_queda_el_borde(monkeypatch):
    """Respaldo de `silueta_forma`: con miles de tramos (roscas) UnifySameDomain puede fallar; el borde sale de las
    aristas que son de una sola región (sin las de adentro)."""
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

    llamadas = []

    def falla(self):
        llamadas.append(1)
        raise RuntimeError("tramo nulo")
    monkeypatch.setattr(ShapeUpgrade_UnifySameDomain, "Build", falla)
    pieza = g.unir_todos([g.caja(40, 10, 10), g.cilindro(5, 30, (20, 5, 0))])
    assert _areas(silueta_forma(pieza, g.Plano("XZ"))[0], g.Plano("XZ")) == [pytest.approx(600)] and llamadas


# ---------------------------------------------------------------- H-77, H-78 y H-79
def _bala(s):
    """Bala de revolución (la del video de Gerardo, simplificada) por el mismo camino que la persona: boceto y Revolución."""
    llamar(s, "create_sketch", plane="XZ", name="Perfil")
    puntos = [(0, 0), (35, 0), (35, 100), (25, 150), (0, 180)]
    for a, b in zip(puntos, puntos[1:] + puntos[:1], strict=True):
        llamar(s, "draw_line", start_x=a[0], start_y=a[1], end_x=b[0], end_y=b[1])
    llamar(s, "revolve", sketch="Perfil", profile=0, axis="Z")


def test_h77_la_silueta_que_cambia_de_tramos_se_rehace_y_conserva_lo_que_encuentra():
    s = api.Sesion()
    _bala(s)
    llamar(s, "create_sketch", plane="XZ", name="Costado")
    llamar(s, "project_to_sketch", bodies=["Cuerpo1"], sketch="Costado")
    lado = next(e["id"] for e in llamar(s, "get_sketch", sketch="Costado")["entities"]
                if e["type"] == "line" and e["start"][0] == pytest.approx(35) and e["end"][0] == pytest.approx(35))
    guia = llamar(s, "draw_line", sketch="Costado", start_x=60, start_y=0, end_x=62, end_y=50)["entities"][0]["id"]
    llamar(s, "add_constraint", sketch="Costado", type="parallel", entities=[guia, lado])
    antes = llamar(s, "get_sketch", sketch="Costado")
    llamar(s, "fillet", edges=[llamar(s, "find_edges", selector="%CIRCLE")["edges"][1]["id"]], radius=20)
    llamar(s, "move_feature", feature="op4", index=2)                 # el empalme pasa antes del boceto
    info = llamar(s, "get_sketch", sketch="Costado")
    assert not info["projections"][0]["lost"] and len(info["entities"]) != len(antes["entities"])
    assert any(e["type"] in ("arc", "spline") for e in info["entities"])            # el redondeo del empalme
    assert len(info["profiles"]) == 1 and info["profiles"][0]["area"] < antes["profiles"][0]["area"]
    paralela = [c for c in info["constraints"] if c["type"] == "parallel"]
    assert len(paralela) == 1 and guia in paralela[0]["entities"]               # pasó al tramo nuevo del costado
    # los tramos nuevos se pueden restringir con el id que muestra get_sketch (la edición guarda la silueta nueva)
    curva = next(e["id"] for e in info["entities"] if e["type"] in ("arc", "spline"))
    llamar(s, "add_constraint", sketch="Costado", type="tangent", entities=[guia, curva])
    assert any(c["type"] == "tangent" for c in llamar(s, "get_sketch", sketch="Costado")["constraints"])
    llamar(s, "undo")
    llamar(s, "extrude", sketch="Costado", profile="largest", distance=5)
    for _ in range(2):
        llamar(s, "undo")
    assert llamar(s, "get_sketch", sketch="Costado")["profiles"][0]["area"] == pytest.approx(antes["profiles"][0]["area"])


def test_h78_forma_libre_da_curvas_suaves_a_menos_de_005_mm(monkeypatch):
    """Una esfera NURBS (forma libre): la silueta sale en curvas (no tramos rectos) pegadas al círculo real, por el HLR
    exacto aparte; y si ese no termina, la sombra de la malla ajustada tampoco se aleja."""
    import math

    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert

    from omnicad.nucleo import perfiles
    from omnicad.restricciones.boceto import puntos_primitiva
    esfera = BRepBuilderAPI_NurbsConvert(g.esfera(10), True).Shape()
    assert g.es_forma_libre(esfera)
    lejos = lambda prims: max(abs(math.hypot(*q) - 10) for p in prims for q in puntos_primitiva(p, 400))  # noqa: E731
    prims = silueta_forma(esfera, g.Plano("XZ"))[0]
    assert {p[0] for p in prims} <= {"spline", "arco", "circulo"} and lejos(prims) < 0.05
    monkeypatch.setattr(perfiles, "PLAZO_SILUETA", 0.0)                      # el exacto «no termina»
    prims = silueta_forma(esfera, g.Plano("YZ"))[0]
    assert lejos(prims) < 0.05 and _areas(prims, g.Plano("YZ")) == [pytest.approx(math.pi * 100, rel=1e-3)]


def test_h80_rosca_vista_desde_su_eje_tarda_menos_de_un_segundo():
    """H-80: una rosca M8 modelada (forma libre). Antes: el HLR exacto no terminaba en 30 s desde su eje (22 s de
    costado) y el contorno de su malla, vuelta sobre vuelta, tardaba ~10 s en partir la cara: 13,7 s la primera vez.
    Ahora la sombra de la malla unida en 2D: ~0,2 s. Un perfil, a menos de 0,05 mm del círculo de cresta (r = 4)."""
    import math
    import time

    from omnicad.nucleo import perfiles
    from omnicad.restricciones.boceto import puntos_primitiva
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=4, height=12)
    llamar(s, "create_thread", faces=[llamar(s, "find_faces", selector="%CYLINDER")["faces"][0]["id"]], thread="M8",
           modeled=True)
    rosca = s.cuerpo("Cuerpo1").forma
    assert g.es_forma_libre(rosca) and perfiles._polos(rosca) > perfiles.POLOS_EXACTO      # va por la malla
    perfiles._CACHE_SILUETA.clear()
    for nombre in ("XY", "XZ"):
        inicio = time.perf_counter()
        prims = silueta_forma(rosca, g.Plano(nombre))[0]
        assert time.perf_counter() - inicio < 1.0, nombre
        assert len(_areas(prims, g.Plano(nombre))) == 1, nombre
    radios = [math.hypot(*q) for p in silueta_forma(rosca, g.Plano("XY"))[0] for q in puntos_primitiva(p, 200)]
    assert max(radios) < 3.98 and min(radios) > 3.88       # B-250: Ø mayor de la clase 6g (7,854), no el nominal


def test_h78_la_misma_forma_no_repite_el_hlr(monkeypatch):
    from omnicad.nucleo import perfiles
    llamadas = []
    original = perfiles._hlr_exacto
    monkeypatch.setattr(perfiles, "_hlr_exacto", lambda f, p: llamadas.append(1) or original(f, p))
    monkeypatch.setattr(perfiles, "_CACHE_SILUETA", {})
    cilindro = g.cilindro(3, 9)
    assert silueta_forma(cilindro, g.Plano("XZ")) == silueta_forma(cilindro, g.Plano("XZ"))
    assert len(llamadas) == 1
    silueta_forma(g.cilindro(3, 9), g.Plano("XZ"))         # la misma forma construida de nuevo (Recalcular todo)
    assert len(llamadas) == 1
    silueta_forma(g.cilindro(3, 9), g.Plano("YZ"))                           # otro plano: se calcula
    silueta_forma(g.cilindro(3, 10), g.Plano("XZ"))                          # otra forma: se calcula
    assert len(llamadas) == 3


def test_h79_el_vertice_incluido_sigue_al_cuerpo(tmp_path):
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=10, height=10)
    llamar(s, "create_sketch", plane="XY")
    pid = llamar(s, "include_3d_geometry", vertices=[[10, 5, 10]])["points"][0]
    llamar(s, "move_body", body="Cuerpo1", translate=[0, 0, 7])
    llamar(s, "move_feature", feature="op3", index=1)                 # el movimiento pasa antes del boceto
    punto = next(p for p in llamar(s, "get_sketch")["points_3d"] if p["id"] == pid)
    assert (punto["x"], punto["y"], punto["z"]) == pytest.approx((10, 5, 17))
    ruta = str(tmp_path / "vertice.omnicad")
    llamar(s, "save_document", path=ruta)
    otra = api.Sesion()
    llamar(otra, "open_document", path=ruta)
    punto = next(p for p in llamar(otra, "get_sketch", sketch="Boceto1")["points_3d"] if p["id"] == pid)
    assert punto["z"] == pytest.approx(17) and punto["source"]["tool"] == "include_3d"
    # movido a mano deja de seguir al vértice (si no, el recálculo lo devolvía), como una curva incluida
    llamar(otra, "transform_sketch_3d", sketch="Boceto1", entities=[pid], translation=[0, 0, 5])
    llamar(otra, "recompute_all")
    punto = next(p for p in llamar(otra, "get_sketch", sketch="Boceto1")["points_3d"] if p["id"] == pid)
    assert punto["z"] == pytest.approx(22) and "source" not in punto
