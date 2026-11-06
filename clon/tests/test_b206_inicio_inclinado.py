"""B-206: conicidad desde el objeto inclinado, conservando su plano neutro."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _ok(sesion, herramienta, **argumentos):
    respuesta = api.llamar(sesion, herramienta, argumentos)
    assert respuesta["ok"], respuesta.get("mensaje", respuesta)
    return respuesta["result"]


@pytest.mark.parametrize("angulo,distancia", [(5, 10), (-5, 10), (5, -10)])
def test_b206_rectangulo_conserva_el_plano_neutro_y_el_volumen(angulo, distancia):
    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    _ok(sesion, "draw_rectangle", sketch="Perfil", x1=-10, y1=-5, x2=10, y2=5)
    _ok(sesion, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="Inicio")
    resultado = _ok(sesion, "extrude", sketch="Perfil", start="object", start_object="Inicio",
                    distance=distancia, taper_angle=angulo)
    forma = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    # Integración de las secciones s = z - y·tan(30°). Cada lateral forma el ángulo pedido con Z.
    t, k, h = math.tan(math.radians(angulo)), math.tan(math.radians(30)), abs(distancia)
    q = t / math.sqrt(1 - (k * t) ** 2)
    r = t / (1 - (k * t) ** 2)
    esperado = 200 * h + (20 * r + 10 * q) * h ** 2 + 4 * q * r * h ** 3 / 3
    assert geo.volumen_exacto(forma) == pytest.approx(esperado, rel=1e-8)
    planos = [geo.plano_de_cara(c) for c in geo.caras(forma)]
    tapas = [p for p in planos if abs(abs(float(p.normal[2])) - math.cos(math.radians(30))) < 1e-7]
    assert len(tapas) == 2
    assert sorted(float(p.origen[2] - k * p.origen[1]) for p in tapas) == pytest.approx(
        sorted([0, distancia]), abs=1e-6)


@pytest.mark.parametrize("angulo,distancia", [(5, 10), (-5, 10), (5, -10)])
def test_b206_circulo_inclinado_con_conicidad_es_un_solido_valido(angulo, distancia):
    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    _ok(sesion, "draw_circle", sketch="Perfil", radius=5)
    _ok(sesion, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="Inicio")
    resultado = _ok(sesion, "extrude", sketch="Perfil", start="object", start_object="Inicio",
                    distance=distancia, taper_angle=angulo)
    forma = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    assert len(geo.solidos(forma)) == 1
    assert (geo.volumen_exacto(forma) - 250 * math.pi) * angulo > 0
    plano = geo.Plano.desde_marco((0, 0, 0), (0, -0.5, math.cos(math.radians(30))), (1, 0, 0))
    base = [c for c in geo.caras(forma) if (p := geo.plano_de_cara(c)) is not None
            and abs(float(p.normal @ plano.normal)) > 1 - 1e-8
            and abs(float(p.origen @ plano.normal)) < 1e-7]
    assert len(base) == 1
    assert geo.area(base[0]) == pytest.approx(25 * math.pi / math.cos(math.radians(30)), rel=1e-7)


@pytest.mark.parametrize("angulo,distancia", [(5, 10), (-5, 10), (5, -10)])
def test_b206_superficie_curva_comparte_el_lateral_y_los_planos_limite(angulo, distancia):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS

    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    _ok(sesion, "draw_circle", sketch="Perfil", radius=5)
    _ok(sesion, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="Inicio")
    resultado = _ok(sesion, "create_surface_extrude", profiles={"sketch": "Perfil", "profile": 0},
                    start="object", start_object="Inicio", distance=distancia, taper_angle=angulo)
    superficie = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(superficie)
    assert not geo.solidos(superficie)
    # Las aristas de borde están en el inicio o en su plano trasladado; las costuras unen ambos.
    pendiente = math.tan(math.radians(30))
    bordes = []
    for arista in geo._explorar(superficie, TopAbs_EDGE):
        curva = BRepAdaptor_Curve(TopoDS.Edge(arista))
        niveles = []
        for i in range(9):
            u = curva.FirstParameter() + (curva.LastParameter() - curva.FirstParameter()) * i / 8
            p = curva.Value(u)
            niveles.append(p.Z() - pendiente * p.Y())
        if max(niveles) - min(niveles) < 1e-5:
            bordes.append(sum(niveles) / len(niveles))
        else:
            assert min(niveles) == pytest.approx(min(0, distancia), abs=1e-5)
            assert max(niveles) == pytest.approx(max(0, distancia), abs=1e-5)
    assert min(bordes) == pytest.approx(min(0, distancia), abs=1e-5)
    assert max(bordes) == pytest.approx(max(0, distancia), abs=1e-5)
    resultado = _ok(sesion, "extrude", sketch="Perfil", start="object", start_object="Inicio",
                    distance=distancia, taper_angle=angulo)
    solido = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    lateral = [c for c in geo.caras(solido) if geo.plano_de_cara(c) is None]
    assert geo.area(superficie) == pytest.approx(sum(geo.area(c) for c in lateral), rel=1e-6)


@pytest.mark.parametrize("angulo", [5, -5])
@pytest.mark.parametrize("perfil", ["anillo", "elipse", "ranura", "delgada"])
def test_b206_perfiles_curvos_con_huecos_y_tramos_rectos(perfil, angulo):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_WIRE

    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    opciones = {}
    if perfil == "elipse":
        _ok(sesion, "draw_ellipse", sketch="Perfil", major_radius=7, minor_radius=4)
        area = 28 * math.pi
    elif perfil == "ranura":
        _ok(sesion, "draw_slot", sketch="Perfil", points=[[-5, 0], [5, 0]], width=6)
        area = 60 + 9 * math.pi
    else:
        _ok(sesion, "draw_circle", sketch="Perfil", radius=5)
        if perfil == "anillo":
            _ok(sesion, "draw_circle", sketch="Perfil", radius=2)
            area = 21 * math.pi
        else:
            opciones = {"thin": True, "wall_thickness": 1, "wall_location": "center"}
            area = 10 * math.pi
    _ok(sesion, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="Inicio")
    resultado = _ok(sesion, "extrude", sketch="Perfil", profile="largest", start="object", start_object="Inicio",
                    distance=2, taper_angle=angulo, **opciones)
    forma = sesion.cuerpo(resultado["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    assert len(geo.solidos(forma)) == 1
    assert (geo.volumen_exacto(forma) - 2 * area) * angulo > 0
    base = [c for c in geo.caras(forma) if (p := geo.plano_de_cara(c)) is not None
            and abs(p.origen[2] - math.tan(math.radians(30)) * p.origen[1]) < 1e-6]
    assert len(base) == 1
    # La elipse de boceto proyectada queda como B-spline racional: integrar con tolerancia explícita.
    propiedades = GProp_GProps()
    BRepGProp.SurfaceProperties_s(base[0], propiedades, 1e-10)
    assert propiedades.Mass() == pytest.approx(area / math.cos(math.radians(30)), rel=1e-7)
    assert len(list(geo._explorar(base[0], TopAbs_WIRE))) == (2 if perfil in ("anillo", "delgada") else 1)


def test_b206_previa_recalculo_guardado_y_deshacer(tmp_path):
    import copy

    from omnicad.io_archivos.proyecto import guardar, abrir
    from omnicad.timeline.operaciones import OpExtrusion

    sesion = api.Sesion()
    _ok(sesion, "create_sketch", plane="XY", name="Perfil")
    _ok(sesion, "draw_circle", sketch="Perfil", radius=5)
    _ok(sesion, "create_construction_plane", type="angle", plane="XY", references=["X"], angle=30, name="Inicio")
    bid = sesion.paso("Perfil").id
    referencia = OpExtrusion.referencia_perfil(sesion.doc.estado_final.bocetos[bid].perfiles[0])
    op = OpExtrusion(sesion.doc.nuevo_id(), boceto=bid, perfiles=[referencia], inicio="objeto",
                     inicio_objeto={"tipo": "plano", "id": sesion.paso("Inicio").id},
                     desfase_inicio="3 mm", distancia="10 mm", conicidad="5 deg")
    receta = copy.deepcopy(op.p)
    previa, _ = sesion.doc.previsualizar(op, en_vivo=True)
    assert sesion.doc.agregar(op).estado == "ok"
    cid = f"{op.id}.c1"
    volumen = geo.volumen_exacto(sesion.doc.estado_final.cuerpos[cid].forma)
    assert geo.volumen_exacto(previa.cuerpos[cid].forma) == pytest.approx(volumen, rel=1e-9)
    assert op.p == receta
    archivo = tmp_path / "inicio_inclinado.omnicad"
    guardar(sesion.doc, archivo)
    reabierto = abrir(archivo)
    assert geo.volumen_exacto(reabierto.estado_final.cuerpos[cid].forma) == pytest.approx(volumen, rel=1e-9)
    assert sesion.doc.puede_deshacer()
    sesion.doc.deshacer()
    assert not sesion.doc.estado_final.cuerpos
    assert sesion.doc.puede_rehacer()
    sesion.doc.rehacer()
    assert geo.volumen_exacto(sesion.doc.estado_final.cuerpos[cid].forma) == pytest.approx(volumen, rel=1e-9)
