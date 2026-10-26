"""SOL-15: mover, copiar y escalar bocetos enteros (Move/Copy y Scale › objetos de boceto), en la API y en los diálogos."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _boceto():
    s = api.Sesion()
    llamar(s, "create_sketch", plane="XY", name="Contorno")
    llamar(s, "draw_rectangle", x1=0, y1=0, x2=10, y2=6, sketch="Contorno")
    return s


def _extruir(s):
    llamar(s, "extrude", sketch="Contorno", distance=4, operation="new_body")
    return [c for c in s.doc.estado_final.cuerpos.values()][-1].forma


def test_mover_y_escalar_conservan_los_ids_de_las_curvas_del_boceto():
    s = _boceto()
    antes = sorted(e["id"] for e in llamar(s, "get_sketch", sketch="Contorno")["entities"])
    llamar(s, "move_body", sketches=["Contorno"], rotate=[0, 0, 30], translate=[5, 5, 5], pivot="origin")
    llamar(s, "scale_body", sketches=["Contorno"], factor=3)
    assert sorted(e["id"] for e in llamar(s, "get_sketch", sketch="Contorno")["entities"]) == antes
    r = api.llamar(s, "move_body", {"sketches": ["Contorno", "op9"], "translate": [1, 0, 0]})
    assert not r["ok"]


def test_mover_un_boceto_mueve_lo_que_se_extruye_despues():
    s = _boceto()
    llamar(s, "move_body", sketches=["Contorno"], translate=[30, 5, 7])
    forma = _extruir(s)
    assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(10 * 6 * 4)
    caja = geo.caja_envolvente(forma)
    assert caja[0] == pytest.approx((30, 5, 7), abs=1e-6) and caja[1] == pytest.approx((40, 11, 11), abs=1e-6)


def test_girar_un_boceto_alrededor_de_un_eje_y_deshacer():
    s = _boceto()
    llamar(s, "move_body", sketches=["Contorno"], rotate=[0, 0, 90], pivot="origin")
    caja = geo.caja_envolvente(_extruir(s))
    assert caja[0] == pytest.approx((-6, 0, 0), abs=1e-6) and caja[1] == pytest.approx((0, 10, 4), abs=1e-6)
    llamar(s, "undo")
    llamar(s, "undo")
    assert geo.caja_envolvente(_extruir(s))[1] == pytest.approx((10, 6, 4), abs=1e-6)


def test_copiar_un_boceto_deja_el_original_y_un_boceto_nuevo():
    s = _boceto()
    llamar(s, "move_body", sketches=["Contorno"], translate=[0, 20, 0], copy=True)
    ids = list(s.doc.estado_final.bocetos)
    assert len(ids) == 2 and ids[1].endswith(".b1")
    assert geo.caja_envolvente(_extruir(s))[1] == pytest.approx((10, 6, 4), abs=1e-6)       # el original sigue en su lugar


def test_escalar_un_boceto_y_errores():
    s = _boceto()
    llamar(s, "scale_body", sketches=["Contorno"], factor=2)
    forma = _extruir(s)
    assert geo.volumen(forma) == pytest.approx(20 * 12 * 4)
    r = api.llamar(s, "scale_body", {"sketches": ["Contorno"], "scale_type": "non_uniform", "factor_x": 2})
    assert not r["ok"] and "uniforme" in r["mensaje"]
    r = api.llamar(s, "move_body", {"sketches": ["Contorno"], "position": [1, 2, 3]})
    assert not r["ok"] and "position" in r["mensaje"]
    r = api.llamar(s, "move_body", {})
    assert not r["ok"] and "sketches" in r["mensaje"]


def test_dialogos_de_mover_y_escalar_aceptan_bocetos():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from omnicad.ui.comando import ContextoComando, ErrorComando, hit_desde_ref
    from omnicad.ui.comandos.modificar import Escala, MoverCopiar
    QApplication.instance() or QApplication([])
    s = _boceto()
    doc = s.doc
    curva = llamar(s, "get_sketch", sketch="Contorno")["entities"][0]["id"]
    hit = hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": curva}, doc.estado_final)
    mover, ctx = MoverCopiar(), ContextoComando(doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in mover.campos(ctx)}
    v.update(objeto="bocetos", tipo="traslacion", dx="30 mm")
    with pytest.raises(ErrorComando, match="bocetos"):
        mover.construir(v, ctx)
    op = mover.construir(dict(v, bocetos=[hit]), ctx)
    assert op.p["bocetos"] == ["op1"] and op.p["cuerpos"] == []
    doc.agregar(op)
    assert doc.resultados[-1].estado in ("ok", "aviso")
    assert mover.desde_op(op, ContextoComando(doc, op=op))["objeto"] == "bocetos"
    escala = Escala()
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in escala.campos(ctx)}
    with pytest.raises(ErrorComando, match="boceto"):
        escala.construir(v, ctx)
    op2 = escala.construir(dict(v, bocetos=[hit], factor="2"), ctx)
    doc.agregar(op2)
    assert doc.resultados[-1].estado in ("ok", "aviso") and escala.desde_op(op2, ContextoComando(doc, op=op2))["bocetos"]


def test_mover_un_paso_que_no_es_boceto_da_un_error_claro():
    s = _boceto()
    _extruir(s)
    r = api.llamar(s, "move_body", {"sketches": ["Extrusión1"], "translate": [1, 0, 0]})
    assert not r["ok"] and "no es un boceto" in r["mensaje"]
