"""Auditoría nocturna del boceto (2026-10-29): deshacer en cadena y validación de los patrones al editarlos."""
from omnicad import api


def llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def falla(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert not respuesta["ok"], respuesta
    return respuesta


def lineas(sesion):
    return sum(1 for e in llamar(sesion, "get_sketch", sketch="U")["entities"] if e["type"] == "line")


def test_deshacer_mas_de_50_pasos_en_cadena():
    """Antes el historial tenía tope 50: con 60 pasos los 10 primeros no se podían deshacer."""
    s = api.Sesion()
    llamar(s, "create_sketch", name="U")
    for i in range(60):
        llamar(s, "draw_line", sketch="U", start_x=i, start_y=0, end_x=i + 1, end_y=5)
    assert lineas(s) == 60
    for _ in range(60):
        llamar(s, "undo")
    assert lineas(s) == 0
    for _ in range(60):
        llamar(s, "redo")
    assert lineas(s) == 60


def _patron():
    s = api.Sesion()
    llamar(s, "create_sketch", name="PT")
    ids = [e["id"] for e in llamar(s, "draw_rectangle", sketch="PT", x1=0, y1=0, x2=5, y2=3)["entities"]]
    p = llamar(s, "sketch_rectangular_pattern", sketch="PT", entities=ids, count1=3, distance1=10)
    return s, ids, p["pattern"]


def test_editar_patron_rechaza_cantidad_cero_como_el_alta():
    s, _ids, pid = _patron()
    antes = len(llamar(s, "get_sketch", sketch="PT")["entities"])
    assert falla(s, "edit_sketch_pattern", sketch="PT", pattern=pid, count1=0)["error_kind"] == "INVALID_ARGUMENTS"
    assert len(llamar(s, "get_sketch", sketch="PT")["entities"]) == antes


def test_patron_rectangular_rechaza_distancia_cero_con_copias():
    s, ids, pid = _patron()
    assert falla(s, "sketch_rectangular_pattern", sketch="PT", entities=ids, count1=3, distance1=0)["error_kind"] \
        == "INVALID_ARGUMENTS"
    assert falla(s, "edit_sketch_pattern", sketch="PT", pattern=pid, distance1=0)["error_kind"] == "INVALID_ARGUMENTS"
    # con una sola fila la distancia 2 no se usa: 0 es válido
    llamar(s, "edit_sketch_pattern", sketch="PT", pattern=pid, distance1=12)


def test_patron_circular_editar_cantidad_cero_se_rechaza():
    s = api.Sesion()
    llamar(s, "create_sketch", name="PC")
    c = llamar(s, "draw_circle", sketch="PC", center_x=20, center_y=0, radius=2)["entities"][0]["id"]
    pid = llamar(s, "sketch_circular_pattern", sketch="PC", entities=[c], count=4, center_x=0, center_y=0)["pattern"]
    assert falla(s, "edit_sketch_pattern", sketch="PC", pattern=pid, count=0)["error_kind"] == "INVALID_ARGUMENTS"


# ---------------------------------------------------------------- Alinear: el «Angle» de Fusion
def test_alinear_angulo_gira_alrededor_de_la_normal_del_destino():
    import numpy as np
    import pytest

    from omnicad.nucleo import geometria as geo
    from omnicad.nucleo import solidos_modificar as sm
    o = {"tipo": "plano", "origen": (0, 0, 0), "normal": (0, 0, 1)}
    d = {"tipo": "plano", "origen": (20, 0, 0), "normal": (1, 0, 0)}
    _, m0 = sm.alinear(None, o, d)
    _, m90 = sm.alinear(None, o, d, angulo=90)
    _, m360 = sm.alinear(None, o, d, angulo=360)
    assert np.allclose(m360, m0)
    assert np.allclose(m90[:3, :3] @ (0, 0, 1), m0[:3, :3] @ (0, 0, 1))        # la normal enfrentada no cambia
    v0 = (m0 @ (0, 1, 0, 1))[:3] - (20, 0, 0)
    v1 = (m90 @ (0, 1, 0, 1))[:3] - (20, 0, 0)
    assert np.linalg.norm(v0) == pytest.approx(np.linalg.norm(v1))
    assert abs(v0 @ v1) < 1e-9 and np.cross(v0, v1)[0] > 0                      # 90° a derechas alrededor de +X
    with pytest.raises(geo.ErrorGeometria):
        sm.alinear(None, o, {"tipo": "punto", "punto": (0, 0, 0)}, angulo=90)


def test_align_bodies_angle_cambia_la_huella_del_cuerpo():
    import numpy as np

    from omnicad.nucleo import geometria as geo
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=10, height=5, name="B", anchor="corner")
    llamar(s, "align_bodies", bodies=["B"], source="XY", destination="XY", angle=90)
    caja = geo.caja_envolvente(next(iter(s.doc.estado_final.cuerpos.values())).forma)
    assert np.allclose(np.asarray(caja[1]) - np.asarray(caja[0]), (10, 20, 5), atol=1e-6)
    assert falla(s, "align_bodies", bodies=["B"], source="XY", destination="XY", angle=500)["error_kind"] \
        == "INVALID_ARGUMENTS"


def test_nucleo_del_boceto_rechaza_distancia_cero_con_copias():
    """La barra del lienzo y el diálogo llaman al boceto directo: la regla también vive ahí."""
    import pytest

    from omnicad.restricciones import Boceto, ErrorBoceto
    b = Boceto()
    c = b.agregar_circulo((0, 0), 2)
    with pytest.raises(ErrorBoceto):
        b.patron_rectangular([c], 3, 0.0)
    b.patron_rectangular([c], 3, 10.0)
    pid = b.patrones[0]["id"]
    with pytest.raises(ErrorBoceto):
        b.editar_patron(pid, distancia1=0.0)
    assert len(b.curvas) == 3                      # el rechazo no dejó el patrón a medias


def test_align_bodies_acepta_un_componente_como_objeto():
    """Fusion: Alinear trabaja con «Bodies» o «Components»; el componente mueve todos sus cuerpos."""
    import numpy as np

    from omnicad.nucleo import geometria as geo
    s = api.Sesion()
    a = llamar(s, "create_box", length=10, width=10, height=5, name="A", anchor="corner")["bodies_created"][0]["id"]
    b = llamar(s, "create_box", length=10, width=10, height=5, name="B", x=30, anchor="corner")["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[a, b], name="Par")
    def cajas():
        return [np.asarray(geo.caja_envolvente(c.forma)) for c in s.doc.estado_final.cuerpos.values()]
    antes = cajas()
    llamar(s, "align_bodies", bodies=["Par"], source="XY", destination="XZ")
    despues = cajas()
    assert len(despues) == 2 and all(not np.allclose(x, y) for x, y in zip(antes, despues, strict=True))   # los dos se movieron
