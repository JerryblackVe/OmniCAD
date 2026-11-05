"""Grampa de fijación (Snap Fit) de PLÁSTICO [PLA-1]: núcleo, operación del timeline, herramienta
create_snap_fit y diálogo. Los tres tipos: gancho y ranurado paralelos, perpendiculares, y gancho y contorno."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo import solidos_crear as sc  # noqa: E402

# Cuerpos del ejemplo: el gancho es la losa 40×20×5 con la cara de arriba en z = 0; la pared de la ranura es
# una caja al alcance del gancho. El marco de cada punto: (punto, normal, brazo).
ARRIBA, DERECHA = (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)


def _gancho():
    return geo.caja(40, 20, 5, origen=(0, -10, -5))       # x∈[0,40], y∈[−10,10], z∈[−5,0]


def _pared_paralela():
    return geo.caja(4, 20, 20, origen=(3.5, -10, 0))     # x∈[3.5,7.5], apoyada en z = 0; el gancho entra 0.5


def _pared_perpendicular():
    return geo.caja(4, 4, 20, origen=(0.5, 2.5, 1))       # y∈[2.5,6.5], z∈[1,21]


def _pared_contorno():
    return geo.caja(20, 20, 10, origen=(-8, -10, 8.5))    # z∈[8.5,18.5]; el contorno entra 0.5


def _grampa(pared=_pared_paralela, marcos=None, **kwargs):
    kwargs.setdefault("largo", 8)
    kwargs.setdefault("ancho", 4)
    kwargs.setdefault("espesor", 2)
    kwargs.setdefault("alto_gancho", 1)
    kwargs.setdefault("holgura", 0.1)
    if marcos is None:
        marcos = [((2.0, 0.0, 0.0), ARRIBA, DERECHA)]
    return sc.grampa(_gancho(), pared() if pared else None, marcos, **kwargs)


# ------------------------------------------------------------------ núcleo: volumen por la cuenta
def test_paralelo_volumen_y_union():
    """Brazo 2×4×8 (64) + gancho 1×4×1 (4) unidos a la losa; la pared pierde el bolsillo del gancho más la
    holgura: 0.6 × 4.2 × 1.2 = 3.024."""
    r = _grampa()
    assert geo.es_valida(r["gancho"]) and len(geo.solidos(r["gancho"])) == 1
    assert geo.volumen(r["gancho"]) == pytest.approx(4000 + 64 + 4, rel=1e-6)
    assert geo.es_valida(r["ranura"])
    assert geo.volumen(r["ranura"]) == pytest.approx(1600 - 0.6 * 4.2 * 1.2, rel=1e-6)


def test_paralelo_sin_interferencia():
    r = _grampa()
    corte = geo.booleano(r["gancho"], r["ranura"], "intersecar")
    assert geo.volumen(corte) == pytest.approx(0.0, abs=1e-9)


def test_perpendicular_volumenes():
    """El gancho sale en +y (el brazo sigue en +z): su volumen es 2×1×1 = 2 y la pared pierde 2.2 × 0.6 × 1.2 = 1.584."""
    r = _grampa(_pared_perpendicular, tipo="perpendicular")
    assert geo.volumen(r["gancho"]) == pytest.approx(4000 + 64 + 2, rel=1e-6)
    assert geo.volumen(r["ranura"]) == pytest.approx(320 - 2.2 * 0.6 * 1.2, rel=1e-6)
    assert geo.volumen(geo.booleano(r["gancho"], r["ranura"], "intersecar")) == pytest.approx(0.0, abs=1e-9)


def test_contorno_volumenes():
    """El contorno abraza la punta del brazo (4×6×1 = 24 de más) y corta un hueco de 4.2 × 6.2 × 0.6 = 15.624."""
    r = _grampa(_pared_contorno, tipo="contorno")
    assert geo.volumen(r["gancho"]) == pytest.approx(4000 + 64 + 24, rel=1e-6)
    assert geo.volumen(r["ranura"]) == pytest.approx(4000 - 4.2 * 6.2 * 0.6, rel=1e-6)
    assert geo.volumen(geo.booleano(r["gancho"], r["ranura"], "intersecar")) == pytest.approx(0.0, abs=1e-9)


def test_dos_puntos():
    """Sin cuerpo de ranura solo crece el gancho: dos grampas iguales suman."""
    r = _grampa(None, marcos=[((2.0, 0.0, 0.0), ARRIBA, DERECHA), ((20.0, 0.0, 0.0), ARRIBA, DERECHA)])
    assert r["ranura"] is None
    assert geo.volumen(r["gancho"]) == pytest.approx(4000 + 2 * (64 + 4), rel=1e-6)


def test_angulo_gira_el_brazo():
    """Giro Uniforme 90°: el brazo apunta a +y en vez de +x (se comprueba con la caja envolvente sobre una losa
    chica, sin pared)."""
    marcos = [((0.0, 0.0, 0.0), ARRIBA, DERECHA)]
    kw = dict(largo=8, ancho=4, espesor=2, alto_gancho=3, holgura=0.1)
    losa = geo.caja(4, 4, 5, origen=(-2, -2, -5))
    r = sc.grampa(losa, None, marcos, angulo=90, **kw)
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(r["gancho"])
    assert (x1, y1) == pytest.approx((2.0, 4.0), abs=1e-6)


def test_extension_distancia_y_siguiente_coinciden():
    """Punto a 3 mm sobre la cara: la base de 3 mm llega a la losa igual con "distancia" que con "siguiente"."""
    marcos = [((2.0, 0.0, 3.0), ARRIBA, DERECHA)]
    kw = dict(largo=8, ancho=4, espesor=2, alto_gancho=1, holgura=0.1)
    con_distancia = sc.grampa(_gancho(), None, marcos, extension="distancia", distancia=3, **kw)
    siguiente = sc.grampa(_gancho(), None, marcos, extension="siguiente", **kw)
    assert geo.volumen(con_distancia["gancho"]) == pytest.approx(4000 + 24 + 64 + 4, rel=1e-6)
    assert geo.volumen(siguiente["gancho"]) == pytest.approx(geo.volumen(con_distancia["gancho"]), rel=1e-6)


# ------------------------------------------------------------------ núcleo: errores
@pytest.mark.parametrize("kwargs", [dict(tipo="diagonal"), dict(extension="largo"), dict(largo=0), dict(ancho=-1),
                                    dict(espesor=0), dict(alto_gancho=0), dict(holgura=-0.1)])
def test_medidas_o_modos_imposibles_fallan(kwargs):
    with pytest.raises(geo.ErrorGeometria):
        _grampa(**kwargs)


def test_distancia_sin_valor_falla():
    with pytest.raises(geo.ErrorGeometria, match="distancia"):
        _grampa(None, extension="distancia")


def test_gancho_sin_cuerpo_falla():
    """El punto está lejos de la losa y la base no lo alcanza: el gancho tiene que tocar su cuerpo."""
    with pytest.raises(geo.ErrorGeometria, match="tocar el cuerpo del gancho"):
        _grampa(None, marcos=[((100.0, 0.0, 0.0), ARRIBA, DERECHA)])


def test_ranura_lejana_falla():
    """La pared queda fuera del alcance del gancho: la grampa no une nada."""
    with pytest.raises(geo.ErrorGeometria, match="no llega"):
        _grampa(lambda: geo.caja(4, 20, 20, origen=(20, -10, -10)))


# ------------------------------------------------------------------ herramienta create_snap_fit
def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _sesion():
    """Gancho = caja 40×20×5 (z∈[0,5]); pared = caja 4×20×20 (x∈[3.5,7.5], z∈[5,25]); boceto en la tapa con un
    punto en (2,10)."""
    s = api.Sesion()
    g = _ok(s, "create_box", length=40, width=20, height=5, anchor="corner")["bodies_created"][0]["id"]
    p = _ok(s, "create_box", length=4, width=20, height=20, x=3.5, y=0, z=5, anchor="corner")["bodies_created"][0]["id"]
    b = _ok(s, "create_sketch", plane=">Z", body=g)["sketch"]["id"]
    _ok(s, "draw_point", sketch=b, x=2, y=10)
    punto = next(iter(s.paso(b).boceto.puntos))
    return s, g, p, b, punto


def _snap_fit(s, g, p, b, punto, **extra):
    args = dict(positions=[{"sketch": b, "point": punto}], hook_body=g, groove_body=p, length=8, width=4,
                thickness=2, hook_height=1, clearance=0.1)
    args.update(extra)
    return _ok(s, "create_snap_fit", **args)


def test_create_snap_fit():
    s, g, p, b, punto = _sesion()
    r = _snap_fit(s, g, p, b, punto)
    assert s.paso(r["feature"]["id"]).TIPO == "grampa"
    assert geo.volumen(s.cuerpo(g).forma) == pytest.approx(4000 + 64 + 4, rel=1e-6)
    assert geo.volumen(s.cuerpo(p).forma) == pytest.approx(1600 - 0.6 * 4.2 * 1.2, rel=1e-6)
    assert {c["id"] for c in r["bodies_modified"]} == {g, p}


@pytest.mark.parametrize("extra", [dict(snap_type="diagonal"), dict(positions=[]),
                                   dict(extent="distance"), dict(length=-1), dict(hook_body="No existe")])
def test_create_snap_fit_errores_no_cambian_el_documento(extra):
    s, g, p, b, punto = _sesion()
    pasos = len(s.doc.operaciones)
    args = dict(positions=[{"sketch": b, "point": punto}], hook_body=g, groove_body=p)
    args.update(extra)
    r = api.llamar(s, "create_snap_fit", args)
    assert not r["ok"], r
    assert len(s.doc.operaciones) == pasos


def test_create_snap_fit_medida_vacia_da_error_claro():
    """Una medida vacía no puede reventar con un TypeError («Error inesperado»): el error tiene que ser claro."""
    s, g, p, b, punto = _sesion()
    pasos = len(s.doc.operaciones)
    r = api.llamar(s, "create_snap_fit", dict(positions=[{"sketch": b, "point": punto}], hook_body=g,
                                              groove_body=p, length="", width=4, thickness=2, hook_height=1))
    assert not r["ok"], r
    assert "vacía" in r["mensaje"], r
    assert len(s.doc.operaciones) == pasos


def test_create_snap_fit_mismo_cuerpo_falla():
    """El gancho y la ranura no pueden ser el mismo cuerpo: la ranura se cortaría sobre el cuerpo original y el
    gancho se perdería en silencio."""
    s, g, p, b, punto = _sesion()
    pasos = len(s.doc.operaciones)
    antes = geo.volumen(s.cuerpo(g).forma)
    r = api.llamar(s, "create_snap_fit", dict(positions=[{"sketch": b, "point": punto}], hook_body=g,
                                              groove_body=g, length=8, width=4, thickness=2, hook_height=1))
    assert not r["ok"] and "distintos" in r["mensaje"], r
    assert len(s.doc.operaciones) == pasos
    assert geo.volumen(s.cuerpo(g).forma) == pytest.approx(antes, rel=1e-9)


def test_guardar_abrir_y_deshacer(tmp_path):
    s, g, p, b, punto = _sesion()
    r = _snap_fit(s, g, p, b, punto)
    vg, vp = geo.volumen(s.cuerpo(g).forma), geo.volumen(s.cuerpo(p).forma)
    assert vg > 4000 and vp < 1600
    _ok(s, "save_document", path=str(tmp_path / "grampa.omnicad"))
    _ok(s, "undo")
    assert geo.volumen(s.cuerpo(g).forma) == pytest.approx(4000, rel=1e-9)
    assert geo.volumen(s.cuerpo(p).forma) == pytest.approx(1600, rel=1e-9)
    assert r["feature"]["id"] not in [o.id for o in s.doc.operaciones]
    _ok(s, "redo")
    assert geo.volumen(s.cuerpo(g).forma) == pytest.approx(vg, rel=1e-9)
    s2 = api.Sesion()
    _ok(s2, "open_document", path=str(tmp_path / "grampa.omnicad"))
    assert geo.volumen(s2.cuerpo(g).forma) == pytest.approx(vg, rel=1e-9)


# ------------------------------------------------------------------ diálogo
def test_el_dialogo_construye_y_reabre():
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos import comando_para
    from omnicad.ui.comandos.plastico import Grampa
    s, g, p, b, punto = _sesion()
    _snap_fit(s, g, p, b, punto)
    op = [o for o in s.doc.operaciones if o.TIPO == "grampa"][0]
    cmd, ctx = Grampa(), ContextoComando(s.doc)
    vuelta = cmd.desde_op(op, ContextoComando(s.doc, op=op))
    assert len(vuelta["posiciones"]) == 1 and len(vuelta["cuerpo_gancho"]) == 1 and len(vuelta["cuerpo_ranura"]) == 1
    assert comando_para(op) is Grampa
    nueva = cmd.construir(vuelta, ContextoComando(s.doc))
    assert nueva.p == op.p
    # construir desde valores del diálogo (sin operación previa):
    hits = [hit_desde_ref({"tipo": "punto_boceto", "boceto": b, "punto": punto}, s.doc.estado_final)]
    cuerpo = lambda cid: [hit_desde_ref({"tipo": "cuerpo", "cuerpo": cid}, s.doc.estado_final)]
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    op2 = cmd.construir(dict(v, posiciones=hits, cuerpo_gancho=cuerpo(g), cuerpo_ranura=[],
                             tipo="perpendicular", largo="6 mm", angulo="10 deg", extension="distancia",
                             distancia="3 mm"), ctx)
    assert (op2.TIPO, op2.p["tipo"], op2.p["angulo"], op2.p["extension"], op2.p["distancia"]) == \
        ("grampa", "perpendicular", "10 deg", "distancia", "3 mm")
    res = s.doc.agregar(op2)
    assert res.estado in ("ok", "aviso"), res.mensaje
