"""B-118: lo que corta, une o interseca sin objetos elegidos alcanza a los cuerpos visibles al crear el paso, como Fusion
(evidencias/fusion_2026-11-01/p5.py: cubos de 8 cm³, el visible queda en 6 y el oculto sigue en 8)."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva, operacion_desde_dict


def ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def volumenes(s):
    return [round(geo.volumen(c.forma), 3) for c in s.doc.estado_final.cuerpos.values()]


@pytest.fixture
def s():
    """Dos cubos de 20 mm: el segundo, oculto."""
    sesion = api.Sesion()
    ok(sesion, "create_box", length=20, width=20, height=20, x=10, y=10)
    ok(sesion, "create_box", length=20, width=20, height=20, x=40, y=10)
    sesion.doc.set_propiedad(["__navegador__"], "ocultos", ["op2.c1"])
    return sesion


def cortar(s):
    return ok(s, "create_box", length=30, width=10, height=40, x=25, y=10, z=-10, operation="cut")


def test_corte_sin_objetivo_deja_intacto_el_cuerpo_oculto(s):
    cortar(s)
    assert volumenes(s) == [6000, 8000]


def test_extrusion_que_corta_con_todo_tampoco_lo_toca(s):
    ok(s, "create_sketch", plane="XY", name="B")
    ok(s, "draw_rectangle", sketch="B", x1=10, y1=5, x2=40, y2=15)
    ok(s, "extrude", sketch="B", profile=0, operation="cut", extent="all")
    assert volumenes(s) == [6000, 8000]


def test_mostrar_el_cuerpo_despues_no_cambia_el_corte_y_editarlo_tampoco(s):
    paso = cortar(s)["feature"]["id"]
    s.doc.set_propiedad(["__navegador__"], "ocultos", [])
    ok(s, "recompute_all")
    assert volumenes(s) == [6000, 8000]
    nueva = s.doc.operacion(paso).copia()
    nueva.p["ancho"] = "12 mm"
    s.doc.reemplazar(paso, nueva)
    assert s.doc.operacion(paso).ocultos == ["op2.c1"] and volumenes(s)[1] == 8000


def test_ocultar_despues_de_crear_el_paso_no_cambia_lo_que_corto():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, x=10, y=10)
    ok(s, "create_box", length=20, width=20, height=20, x=40, y=10)
    cortar(s)
    assert volumenes(s) == [6000, 6000]
    assert "ocultos" not in s.doc.a_dict()["operaciones"][-1]        # sin nada oculto, la receta no cambia
    s.doc.set_propiedad(["__navegador__"], "ocultos", ["op2.c1"])
    ok(s, "recompute_all")
    assert volumenes(s) == [6000, 6000]


def test_guardar_abrir_y_deshacer_conservan_lo_oculto_del_paso(s):
    cortar(s)
    datos = s.doc.a_dict()
    assert datos["operaciones"][-1]["ocultos"] == ["op2.c1"]
    otro = Documento.desde_dict(datos)
    assert [round(geo.volumen(c.forma), 3) for c in otro.estado_final.cuerpos.values()] == [6000, 8000]
    ok(s, "undo")
    ok(s, "redo")
    assert volumenes(s) == [6000, 8000]


def test_una_receta_vieja_sin_la_clave_corta_lo_que_cortaba(s):
    cortar(s)
    datos = s.doc.a_dict()
    del datos["operaciones"][-1]["ocultos"]
    otro = Documento.desde_dict(datos)
    assert [round(geo.volumen(c.forma), 3) for c in otro.estado_final.cuerpos.values()] == [6000, 6000]


def test_la_vista_previa_tampoco_toca_lo_oculto(s):
    cortar(s)
    op = s.doc.operaciones[-1]
    ok(s, "undo")
    s.doc.set_propiedad(["__navegador__"], "ocultos", ["op2.c1"])
    op.ocultos = []
    estado, _ = s.doc.previsualizar(op)
    assert [round(geo.volumen(c.forma), 3) for c in estado.cuerpos.values()] == [6000, 8000]


def test_tambien_unir_e_intersecar(s):
    ok(s, "create_box", length=30, width=10, height=10, x=25, y=10, z=5, operation="intersect", name="I")
    assert volumenes(s) == [1000, 8000]
    t = api.Sesion()
    ok(t, "create_box", length=20, width=20, height=20, x=10, y=10)
    ok(t, "create_box", length=20, width=20, height=20, x=40, y=10)
    t.doc.set_propiedad(["__navegador__"], "ocultos", ["op2.c1"])
    ok(t, "create_box", length=30, width=10, height=10, x=25, y=10, z=5, operation="join")
    assert volumenes(t) == [10000, 8000]                  # el oculto, que también toca, no se absorbe


def test_un_componente_oculto_tampoco_se_corta():
    s = api.Sesion()
    ok(s, "create_box", length=20, width=20, height=20, x=10, y=10)
    ok(s, "create_box", length=20, width=20, height=20, x=40, y=10)
    componente = ok(s, "create_component", bodies=["op2.c1"], name="C")["feature"]["id"]
    s.doc.set_propiedad(["__navegador__"], "ocultos", [s.doc.estado_final.cuerpos["op2.c1"].componente])
    assert s.doc.estado_final.cuerpos["op2.c1"].componente and componente
    cortar(s)
    assert volumenes(s) == [6000, 8000]


def test_el_patron_de_un_corte_no_alcanza_lo_que_estaba_oculto(s):
    cortar(s)
    ok(s, "rectangular_pattern", features=["op3"], x_count=2, x_spacing=-5, y_count=1)
    assert volumenes(s)[1] == 8000


def test_paso_con_ocultos_mal_formados_se_lee_sin_ellos():
    d = OpPrimitiva("op1", forma="caja").a_dict()
    for malo in (5, "x", {"a": 1}):
        assert operacion_desde_dict({**d, "ocultos": malo}).ocultos == []
    assert operacion_desde_dict({**d, "ocultos": ["a", 3]}).ocultos == ["a"]
