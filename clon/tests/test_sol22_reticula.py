"""SOL-22: retícula volumétrica (barras cross/x_cell como sólido; gyroid y Schwarz como malla)."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import reticula


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _cubo(lado=20):
    s = api.Sesion()
    llamar(s, "create_box", length=lado, width=lado, height=lado, name="Cubo")
    return s


def _cuerpo(s):
    (c,) = s.doc.estado_final.cuerpos.values()
    return c


@pytest.mark.parametrize("forma", ["cross", "x_cell"])
def test_barras_dan_la_solidez_pedida(forma):
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape=forma, cell_size=10, solidity=20)
    c = _cuerpo(s)
    assert c.tipo == "solido" and geo.es_valida(c.forma)
    assert geo.volumen(c.forma) / 8000 == pytest.approx(0.20, abs=0.03)


@pytest.mark.parametrize("forma", ["gyroid", "schwarz_p", "schwarz_d"])
def test_superficies_minimas_quedan_como_malla(forma):
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape=forma, cell_size=10, solidity=30, resolution=10)
    c = _cuerpo(s)
    assert c.tipo == "malla" and len(c.forma.caras) > 100
    assert c.forma.volumen() / 8000 == pytest.approx(0.30, abs=0.08)               # el borde escalonado y la grilla restan precisión


def test_no_uniforme_y_cuerpo_curvo():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=12, height=20, name="Cil")
    llamar(s, "create_volumetric_lattice", cell_shape="gyroid", cell_size=8, cell_size_y=10, cell_size_z=12, solidity=40)
    c = _cuerpo(s)
    assert c.tipo == "malla"
    volumen_cilindro = 3.14159265 * 144 * 20
    assert 0.25 < c.forma.volumen() / volumen_cilindro < 0.55


def test_deshacer_devuelve_el_cuerpo():
    s = _cubo()
    llamar(s, "create_volumetric_lattice", cell_shape="gyroid", cell_size=10, solidity=30)
    llamar(s, "undo")
    assert _cuerpo(s).tipo == "solido" and geo.volumen(_cuerpo(s).forma) == pytest.approx(8000)


def test_errores():
    s = _cubo()
    for args in ({"solidity": 0}, {"solidity": 100}, {"cell_size": 0}, {"resolution": 2}, {"cell_size": 0.2, "cell_shape": "cross"},
                 {"cell_shape": "no existe"}):
        assert not api.llamar(s, "create_volumetric_lattice", args)["ok"], args
    assert not api.llamar(api.Sesion(), "create_volumetric_lattice", {})["ok"]


def test_espesor_para_es_monotono():
    assert reticula.espesor_para("gyroid", 0.2) < reticula.espesor_para("gyroid", 0.5) < reticula.espesor_para("gyroid", 0.8)


def test_dialogo_de_la_reticula():
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref
    from omnicad.ui.comandos.modificar import ReticulaVolumetrica
    QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="20", largo="20", alto="20"))
    cmd, ctx = ReticulaVolumetrica(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    with pytest.raises(ErrorComando):
        cmd.construir(v, ctx)                                                      # sin cuerpo
    v.update(cuerpo=[hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)], forma_celda="cross",
             tamano="10 mm", solidez="25")
    op = cmd.construir(v, ctx)
    doc.agregar(op)
    assert doc.resultados[-1].estado == "ok", doc.resultados[-1].mensaje
    assert cmd.desde_op(op, ContextoComando(doc, op=op))["forma_celda"] == "cross"
    v["tamano"] = "mucho"
    with pytest.raises(Exception):
        cmd.construir(v, ctx)
