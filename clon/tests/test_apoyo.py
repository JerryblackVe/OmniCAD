"""Apoyo (Rest) de PLÁSTICO [PLA-2]: núcleo, operación del timeline, herramienta create_rest y diálogo."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402
from omnicad.nucleo import geometria as geo  # noqa: E402
from omnicad.nucleo import perfiles  # noqa: E402
from omnicad.nucleo import referencias as refs  # noqa: E402
from omnicad.nucleo import solidos_crear as sc  # noqa: E402
from omnicad.nucleo import solidos_modificar as sm  # noqa: E402
from omnicad.ui.comando import ContextoComando  # noqa: E402

ALTO, PARED = 10.0, 2.0
TAPA = ALTO - PARED                      # de la tapa al fondo del cuerpo hueco
ARRIBA = (0.0, 0.0, 1.0)
CUADRO = (10, 6, 20, 16)                 # el perfil del ejemplo


@pytest.fixture(scope="module")
def caja_hueca():
    """Caja 40×20×10 vaciada 2 mm por arriba: fondo de 2 y paredes de 2; el área de adentro mide 36×16."""
    caja = geo.caja(40, 20, ALTO)
    tapa = max(refs.subformas(caja, "cara"), key=lambda c: refs.firma(c)["centro"][2])
    return sm.vaciado(caja, [tapa], espesor_interior=PARED)


def _perfil(cuadro):
    """Cara de la región rectangular (u0, v0, u1, v1) del plano XY (u = x, v = y)."""
    u0, v0, u1, v1 = cuadro
    curvas = [("linea", 1, (u0, v0), (u1, v0)), ("linea", 2, (u1, v0), (u1, v1)),
              ("linea", 3, (u1, v1), (u0, v1)), ("linea", 4, (u0, v1), (u0, v0))]
    return max(perfiles.detectar(curvas, geo.Plano("XY")), key=lambda p: p.area).cara


def _apoyo(caja, cuadro=CUADRO, **kwargs):
    kwargs.setdefault("grosor", PARED)
    kwargs.setdefault("lados", [(1, kwargs["grosor"])])
    return sc.apoyo([caja], [_perfil(cuadro)], direccion=ARRIBA, **kwargs)


def _tapa_sin_material(caja, herramienta):
    """Lo que el apoyo le saca a la tapa: el Trim no deja pared sobre la cara donde apoya."""
    return geo.volumen(geo.booleano(caja, herramienta, "intersecar"))


def _altura(forma):
    (_, _, z0), (_, _, z1) = geo.caja_envolvente(forma)
    return z0, z1


def test_sin_desfase_es_la_pared_bajo_el_perfil(caja_hueca):
    """Atraviesa de la tapa (z = 8) al fondo de la caja (z = 0): el Trim la corta en las caras extremas del
    cuerpo, así que mide 10×10 (el cuadro del perfil) por 10 de alto."""
    herramienta = _apoyo(caja_hueca)
    assert geo.es_valida(herramienta) and len(geo.solidos(herramienta)) == 1
    assert geo.volumen(herramienta) == pytest.approx(10 * 10 * ALTO, rel=1e-6)
    assert _altura(herramienta) == pytest.approx((0.0, ALTO), abs=1e-6)


def test_el_grosor_cambia_el_volumen_por_la_formula(caja_hueca):
    """Con 4 mm de grosor, dos lados de 2: la pared sigue la misma vertical del perfil (lado 1 para arriba, lado 2
    para abajo, recortada en z = 0); el volumen no cambia con esta simetría."""
    herramienta = _apoyo(caja_hueca, grosor=4, lados=[(1, 2), (-1, 2)])
    assert geo.es_valida(herramienta) and len(geo.solidos(herramienta)) == 1
    assert geo.volumen(herramienta) == pytest.approx(10 * 10 * ALTO, rel=1e-6)


def test_desmoldeo_angosta_hacia_el_fondo(caja_hueca):
    sin = _apoyo(caja_hueca)
    con = _apoyo(caja_hueca, angulo_desmoldeo=6)
    assert geo.es_valida(con)
    assert geo.solidos(geo.booleano(con, sin, "cortar")) == [], "el apoyo inclinado queda dentro del recto"
    assert geo.volumen(con) < geo.volumen(sin)


def test_invertir_apoya_contra_la_tapa(caja_hueca):
    """Flip: el abanico del desmoldeo se mira al revés (angosta hacia la tapa), igual que siguiendo al cuerpo de
    `direccion`: el apoyo queda donde estaba."""
    sin_desmoldeo = _apoyo(caja_hueca, invertir=True)
    con = _apoyo(caja_hueca, angulo_desmoldeo=6, invertir=True)
    assert geo.es_valida(con) and geo.es_valida(sin_desmoldeo)
    assert geo.volumen(sin_desmoldeo) == pytest.approx(geo.volumen(_apoyo(caja_hueca)), rel=1e-6)
    assert geo.volumen(con) > geo.volumen(sin_desmoldeo)
    assert geo.solidos(geo.booleano(_apoyo(caja_hueca), con, "cortar")) == [], \
        "el apoyo invertido queda dentro del recto"


def test_el_desfase_mueve_el_apoyo_arriba(caja_hueca):
    """Offset Position 2: el perfil sube 2 mm; el apoyo nace en z = 2 y el Trim lo corta en la tapa (z = 10)."""
    herramienta = _apoyo(caja_hueca, desfase=2)
    assert geo.es_valida(herramienta)
    assert _altura(herramienta) == pytest.approx((PARED, ALTO), abs=1e-6)
    assert geo.volumen(herramienta) == pytest.approx(10 * 10 * (ALTO - PARED), rel=1e-6)


def test_hasta_objeto_termina_en_el_fondo(caja_hueca):
    """To Object: la pared termina donde el cuerpo la contiene, la cara de arriba del fondo (z = 2): mide el
    cuadro por el fondo del hueco."""
    herramienta = _apoyo(caja_hueca, extension="objeto")
    assert geo.es_valida(herramienta) and len(geo.solidos(herramienta)) == 1
    assert _altura(herramienta) == pytest.approx((0.0, PARED), abs=1e-6)
    assert geo.volumen(herramienta) == pytest.approx(10 * 10 * PARED, rel=1e-6)


@pytest.mark.parametrize("grosor, lados", [(0, [(1, 0)]), (-2, [(1, 2)]), (2, [(1, -2), (-1, 4)]),
                                           (2, [(1, 0), (-1, 0)]), (2, [])])
def test_grosor_o_lados_imposibles_fallan(grosor, lados):
    with pytest.raises(geo.ErrorGeometria):
        sc.apoyo([geo.caja(10, 10, 10)], [_perfil((2, 2, 8, 8))], direccion=ARRIBA, grosor=grosor, lados=lados)


def test_solo_lado_2_falla():
    """El lado 2 es el material del lado opuesto al cuerpo: sin el lado 1 no hay apoyo."""
    with pytest.raises(geo.ErrorGeometria, match="lado 1"):
        sc.apoyo([geo.caja(10, 10, 10)], [_perfil((2, 2, 8, 8))], direccion=ARRIBA, grosor=2, lados=[(-1, 2)])


def test_grosor_distinto_de_la_suma_de_los_lados_falla():
    with pytest.raises(geo.ErrorGeometria, match="suma de los lados"):
        sc.apoyo([geo.caja(10, 10, 10)], [_perfil((2, 2, 8, 8))], direccion=ARRIBA, grosor=3, lados=[(1, 2)])


def test_perfil_vacio_falla():
    with pytest.raises(geo.ErrorGeometria):
        sc.apoyo([geo.caja(10, 10, 10)], [geo.cara_de_plano(geo.Plano("XY"))], direccion=ARRIBA, grosor=2,
                 lados=[(1, 2)])


def test_perfil_fuera_del_cuerpo_falla():
    with pytest.raises(geo.ErrorGeometria, match="tocar el cuerpo"):
        sc.apoyo([geo.caja(10, 10, 10)], [_perfil((12, 2, 18, 8))], direccion=ARRIBA, grosor=2, lados=[(1, 2)])


def test_desfase_fuera_del_cuerpo_falla():
    with pytest.raises(geo.ErrorGeometria):
        sc.apoyo([geo.caja(10, 10, 10)], [_perfil((2, 2, 8, 8))], direccion=ARRIBA, desfase=20, grosor=2,
                 lados=[(1, 2)])


def test_perfil_de_un_agujero_en_la_pared_falla():
    """El perfil queda sobre una caja MACIZA (z = 0, dentro del material): el apoyo se hunde en el cuerpo y no
    crea nada nuevo (el resultado ya está contenido en él), como en Fusion."""
    s = api.Sesion()
    r = api.llamar(s, "create_box", {"length": 40, "width": 20, "height": ALTO, "anchor": "corner"})
    maciza = r["result"]["bodies_created"][0]["id"]
    r = api.llamar(s, "create_sketch", {"plane": "XY"})
    plano = r["result"]["sketch"]["id"]
    for x1, y1, x2, y2 in [(10, 6, 20, 6), (20, 6, 20, 16), (20, 16, 10, 16), (10, 16, 10, 6)]:
        api.llamar(s, "draw_line", {"sketch": plano, "start_x": x1, "start_y": y1, "end_x": x2, "end_y": y2})
    r = api.llamar(s, "create_rest", {"sketch": plano, "body": maciza})
    assert r["ok"] and r["result"]["bodies_modified"] == [], r
    assert geo.volumen(s.cuerpo(maciza).forma) == pytest.approx(40 * 20 * ALTO, rel=1e-9)


def test_sin_cuerpo_falla():
    with pytest.raises(geo.ErrorGeometria, match="necesita un cuerpo"):
        sc.apoyo([], [_perfil(CUADRO)], direccion=ARRIBA, grosor=2, lados=[(1, 2)])


# ---------------------------------------------------------------- herramienta, operación, archivo y deshacer
def _sesion():
    s = api.Sesion()
    r = api.llamar(s, "create_box", {"length": 40, "width": 20, "height": ALTO, "anchor": "corner"})
    assert r["ok"], r
    cid = r["result"]["bodies_created"][0]["id"]
    r = api.llamar(s, "shell", {"body": cid, "faces": ">Z", "thickness": PARED})
    assert r["ok"], r
    r = api.llamar(s, "create_sketch", {"plane": "XY"})
    assert r["ok"], r
    boceto = r["result"]["sketch"]["id"]
    for x1, y1, x2, y2 in [(10, 6, 20, 6), (20, 6, 20, 16), (20, 16, 10, 16), (10, 16, 10, 6)]:
        r = api.llamar(s, "draw_line", {"sketch": boceto, "start_x": x1, "start_y": y1, "end_x": x2, "end_y": y2})
        assert r["ok"], r
    return s, cid, boceto


def _ok(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def test_create_rest():
    s, cid, boceto = _sesion()
    hueca = geo.volumen(s.cuerpo(cid).forma)
    r = _ok(s, "create_rest", sketch=boceto, body=cid)
    assert s.paso(r["feature"]["id"]).TIPO == "apoyo" and r["bodies_modified"]
    forma = s.cuerpo(cid).forma
    assert geo.es_valida(forma) and len(geo.solidos(forma)) == 1
    area = 10 * 8                                                # el apoyo atraviesa el hueco: 10×10 menos el 2 de fondo
    assert geo.volumen(forma) == pytest.approx(hueca + area * 10, rel=1e-6)


@pytest.mark.parametrize("grosor, lados", [(0, (0, 0)), (-1, (0, 0)), (3, (2, 0))])
def test_create_rest_grosor_imposible(grosor, lados):
    s, cid, boceto = _sesion()
    antes = [o.id for o in s.doc.operaciones]
    r = api.llamar(s, "create_rest", {"sketch": boceto, "body": cid, "thickness": grosor, "side1": lados[0],
                                      "side2": lados[1]})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS", r
    assert [o.id for o in s.doc.operaciones] == antes


def test_create_rest_lado_como_expresion_se_acepta():
    """side1 "2" (texto) con thickness 2: la cuenta la hace el núcleo al evaluar; no es un argumento inválido."""
    s, cid, boceto = _sesion()
    r = api.llamar(s, "create_rest", {"sketch": boceto, "body": cid, "thickness": 2, "side1": "2", "side2": 0})
    assert r["ok"], r


def test_create_rest_perfil_abierto(tmp_path):
    """Una curva suelta no da perfil cerrado: la herramienta dice qué falta y el documento no cambia."""
    s, cid, _ = _sesion()
    abierto = _ok(s, "create_sketch", plane="XY")["sketch"]["id"]
    _ok(s, "draw_line", sketch=abierto, start_x=0, start_y=0, end_x=10, end_y=0)
    _ok(s, "save_document", path=str(tmp_path / "apoyo.omnicad"))
    antes = len(s.doc.operaciones)
    r = api.llamar(s, "create_rest", {"sketch": abierto, "body": cid})
    assert not r["ok"] and "región cerrada" in r["mensaje"] and len(s.doc.operaciones) == antes


def test_create_rest_operacion_que_falla_no_cambia_el_documento():
    """El perfil del boceto queda fuera de la caja: el apoyo no toca el cuerpo y el documento no cambia."""
    maciza = api.Sesion()
    r = api.llamar(maciza, "create_box", {"length": 40, "width": 20, "height": ALTO, "anchor": "corner"})
    otro = r["result"]["bodies_created"][0]["id"]
    r = api.llamar(maciza, "create_sketch", {"plane": "XY"})
    plano = r["result"]["sketch"]["id"]
    for x1, y1, x2, y2 in [(50, 6, 55, 6), (55, 6, 55, 16), (55, 16, 50, 16), (50, 16, 50, 6)]:
        api.llamar(maciza, "draw_line", {"sketch": plano, "start_x": x1, "start_y": y1, "end_x": x2, "end_y": y2})
    pasos = [o.id for o in maciza.doc.operaciones]
    r = api.llamar(maciza, "create_rest", {"sketch": plano, "body": otro})
    assert not r["ok"] and "tocar el cuerpo" in r["mensaje"], r
    assert [o.id for o in maciza.doc.operaciones] == pasos
    assert geo.volumen(maciza.cuerpo(otro).forma) == pytest.approx(40 * 20 * ALTO, rel=1e-9)


def test_guardar_abrir_y_deshacer(tmp_path):
    s, cid, boceto = _sesion()
    volumen_hueco = geo.volumen(s.cuerpo(cid).forma)
    r = _ok(s, "create_rest", sketch=boceto, body=cid)
    volumen = geo.volumen(s.cuerpo(cid).forma)
    assert volumen > volumen_hueco
    _ok(s, "undo")
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(volumen_hueco, rel=1e-9)
    assert r["feature"]["id"] not in [o.id for o in s.doc.operaciones]
    _ok(s, "redo")
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(volumen, rel=1e-9)
    ruta = str(tmp_path / "apoyo.omnicad")
    _ok(s, "save_document", path=ruta)
    s2 = api.Sesion()
    _ok(s2, "open_document", path=ruta)
    assert geo.volumen(s2.cuerpo(cid).forma) == pytest.approx(volumen, rel=1e-9)


# ---------------------------------------------------------------- diálogo
def test_el_dialogo_construye_y_reabre():
    from omnicad.timeline.operaciones import OpExtrusion
    from omnicad.ui.comando import hit_desde_ref
    from omnicad.ui.comandos import comando_para
    from omnicad.ui.comandos.plastico import Apoyo
    s, cid, boceto = _sesion()
    perfil = s.doc.estado_final.bocetos[boceto].perfiles[0]
    hits = [hit_desde_ref({"tipo": "perfil", "boceto": boceto, **OpExtrusion.referencia_perfil(perfil)}, s.doc.estado_final)]
    cuerpo = [hit_desde_ref({"tipo": "cuerpo", "cuerpo": cid}, s.doc.estado_final)]
    cmd, ctx = Apoyo(), ContextoComando(s.doc)
    v = {c.clave: (list(c.defecto) if isinstance(c.defecto, list) else c.defecto) for c in cmd.campos(ctx)}
    op = cmd.construir(dict(v, perfiles=hits, cuerpo=cuerpo, grosor="2 mm", lado1="2 mm", angulo_desmoldeo="4 deg",
                            extension="objeto"), ctx)
    assert (op.TIPO, op.p["extension"], op.p["angulo_desmoldeo"]) == ("apoyo", "objeto", "4 deg")
    res = s.doc.agregar(op)
    assert res.estado in ("ok", "aviso"), res.mensaje
    assert comando_para(op) is Apoyo
    vuelta = cmd.desde_op(op, ContextoComando(s.doc, op=op))
    assert len(vuelta["perfiles"]) == len(hits) and len(vuelta["cuerpo"]) == len(cuerpo)
    assert cmd.construir(vuelta, ContextoComando(s.doc)).p == op.p
