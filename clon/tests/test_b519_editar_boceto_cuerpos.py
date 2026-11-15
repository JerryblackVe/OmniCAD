"""B-519: editar el boceto de la pieza de Gerardo (contorno con empalmes R7/R6 y rectángulo interior) rompía los
cuerpos. Sin un empalme el contorno queda abierto: la extrusión del anillo se «re-vinculaba» al hueco (comparte 4 de
sus 12 curvas) y dejaba un bloque que no sigue al perfil. Como Fusion, el paso queda marcado con error, lo demás
sigue sano y Deshacer vuelve todo."""
from omnicad import api
from omnicad.nucleo import geometria as geo


def _llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


def _volumenes(s):
    return {k: round(geo.volumen(c.forma), 1) for k, c in s.doc.estado_final.cuerpos.items()}


def _pieza():
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY", name="Boceto1")
    _llamar(s, "draw_rectangle", x1=0, y1=0, x2=100, y2=60)
    puntos = {(p["x"], p["y"]): p["id"] for p in _llamar(s, "get_sketch")["points"]}
    for (x, y), r in (((100, 60), 7), ((0, 60), 7), ((100, 0), 6), ((0, 0), 6)):
        _llamar(s, "sketch_fillet", sketch="Boceto1", vertex=puntos[(x, y)], radius=r)
    _llamar(s, "draw_rectangle", x1=10, y1=10, x2=90, y2=50)
    perfiles = _llamar(s, "get_sketch")["profiles"]
    anillo = [i for i, p in enumerate(perfiles) if p["area"] < 3000]
    interior = [i for i, p in enumerate(perfiles) if p["area"] >= 3000]
    _llamar(s, "extrude", sketch="Boceto1", profile=anillo, distance="20 mm")                                  # op2
    _llamar(s, "extrude", sketch="Boceto1", profile=interior, distance="3 mm", operation="new_body")           # op3
    # El marco ya modificado por un paso posterior: un reborde de 5 mm unido arriba.
    _llamar(s, "extrude", sketch="Boceto1", profile=anillo, distance="5 mm", start="offset", start_offset="20 mm",
            operation="join")                                                                                  # op4
    return s


def test_b519_quitar_un_empalme_marca_el_marco_y_deshacer_vuelve_todo():
    s = _pieza()
    antes, estados_antes = _volumenes(s), [r.estado for r in s.doc.resultados]
    assert antes["op3.c1"] == 9600.0 and len(antes) == 2
    # Como la ventana: se edita el boceto y se recalcula sin la transacción de la API.
    nueva = s.doc.operacion("op1").copia()
    b = nueva.boceto
    arco = max((c for c in b.curvas.values() if c.tipo == "arco" and abs(b.radio(c.id) - 7) < 1e-9),
               key=lambda c: b.coords(c.centro)[0])
    b.eliminar(arco.id)
    s.doc.reemplazar("op1", nueva)
    estados = {o.id: r.estado for o, r in zip(s.doc.operaciones, s.doc.resultados, strict=True)}
    assert estados["op2"] == "error" and estados["op4"] == "error", estados    # marcados, sin bloque equivocado
    assert _volumenes(s) == {"op3.c1": 9600.0}                                  # lo demás sigue sano
    s.doc.deshacer()
    assert _volumenes(s) == antes
    assert [r.estado for r in s.doc.resultados] == estados_antes


def _marco(cadena):
    """La caja de Gerardo: pared delgada de 1 mm sobre las 4 líneas del rectángulo (curvas abiertas, sin perfil)."""
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XY", name="Boceto1")
    _llamar(s, "draw_rectangle", x1=0, y1=0, x2=100, y2=60)
    sk = _llamar(s, "get_sketch")
    lineas = [e["id"] for e in sk["entities"] if e["type"] == "line"]
    _llamar(s, "extrude", sketch="Boceto1", open_curves=lineas, thin=True, wall_thickness="1 mm", distance="30 mm",
            tangent_chain=cadena)
    return s, {(p["x"], p["y"]): p["id"] for p in sk["points"]}


def test_b519_redondear_el_boceto_despues_deja_la_pared_entera():
    """Captura 2 de Gerardo: después de redondear las esquinas del boceto (R7/R6) la pared quedaba en 4 placas sueltas.
    Con «Cadena tangente» (marcada por defecto, como Fusion) los arcos nuevos entran en la pared al recalcular."""
    s, puntos = _marco(cadena=True)
    for (x, y), r in (((100, 60), 7), ((0, 60), 7), ((100, 0), 6), ((0, 0), 6)):
        _llamar(s, "sketch_fillet", sketch="Boceto1", vertex=puntos[(x, y)], radius=r)
    cuerpos = s.doc.estado_final.cuerpos
    assert len(cuerpos) == 1, list(cuerpos)
    forma = next(iter(cuerpos.values())).forma
    assert geo.es_valida(forma)
    assert 30 * 300 * 0.95 < geo.volumen(forma) < 30 * 320 * 1.0        # ~ largo del contorno redondeado × 30 × 1 mm
    # Sin la cadena, como antes: las 4 líneas solas, 4 placas.
    s, puntos = _marco(cadena=False)
    for (x, y), r in (((100, 60), 7), ((0, 60), 7), ((100, 0), 6), ((0, 0), 6)):
        _llamar(s, "sketch_fillet", sketch="Boceto1", vertex=puntos[(x, y)], radius=r)
    assert len(s.doc.estado_final.cuerpos) == 4


def test_b519_timeline_de_gerardo_redondear_el_boceto_sigue_al_perfil_sin_aviso():
    """El timeline real (autoguardado de Gerardo): Extrusión1 de anillo + interior, Extrusión2 corta el interior (el
    cuerpo ya modificado) y después se redondean las esquinas del boceto. El anillo nuevo conserva sus 8 curvas y suma
    4 arcos; el interior comparte 4 con la misma diferencia: antes el desempate podía elegir el interior y el paso
    quedaba con aviso. Ahora gana el que conserva más curvas, sin aviso (Fusion conserva el perfil)."""
    s = api.Sesion()
    _llamar(s, "create_sketch", plane="XZ", name="Boceto1")
    _llamar(s, "draw_rectangle", x1=0, y1=0, x2=52.8, y2=35.1)
    puntos = {(round(p["x"], 1), round(p["y"], 1)): p["id"] for p in _llamar(s, "get_sketch")["points"]}
    _llamar(s, "draw_rectangle", x1=9.3, y1=9.5, x2=42.3, y2=26.4)
    _llamar(s, "extrude", sketch="Boceto1", profile="all", distance="50 mm")                                  # op2
    interior = min(range(2), key=lambda i: abs(_llamar(s, "get_sketch")["profiles"][i]["area"] - 33 * 16.9))
    _llamar(s, "extrude", sketch="Boceto1", profile=interior, extent="all", operation="cut")                 # op3
    for xy, r in (((52.8, 35.1), 7), ((0.0, 35.1), 7), ((52.8, 0.0), 6), ((0.0, 0.0), 6)):
        _llamar(s, "sketch_fillet", sketch="Boceto1", vertex=puntos[xy], radius=r)
    pasos = {p["id"]: p["status"] for p in _llamar(s, "get_timeline")["steps"]}
    assert pasos == {"op1": "ok", "op2": "ok", "op3": "ok"}, pasos
    anillo = max(p["area"] for p in _llamar(s, "get_sketch")["profiles"])        # el anillo con los arcos
    (forma,) = [c.forma for c in s.doc.estado_final.cuerpos.values()]
    assert geo.es_valida(forma) and abs(geo.volumen(forma) - anillo * 50) < 1e-3 * anillo * 50


def test_b519_la_casilla_cadena_tangente_se_guarda_en_el_paso():
    """La casilla «Cadena tangente» de Extruir delgada escribe `cadena` en el paso y al editarlo vuelve igual."""
    from omnicad.restricciones import Boceto
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpBoceto
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import Extruir
    doc = Documento()
    b = Boceto()
    lineas = b.agregar_rectangulo((0, 0), (20, 10))
    doc.agregar(OpBoceto(doc.nuevo_id(), "Boceto1", boceto=b))
    ctx, cmd = ContextoComando(doc), Extruir()
    v = {c.clave: getattr(c, "defecto", None) for c in cmd.campos(ctx)}
    assert v["cadena"] is True                                         # marcada por defecto, como Fusion
    v.update(tipo="delgada", espesor="1 mm", distancia="10 mm",
             perfiles=[{"ref": {"tipo": "curva_boceto", "boceto": "op1", "curva": c}} for c in lineas[:2]])
    for marcada in (False, True):
        op = cmd.construir({**v, "cadena": marcada}, ctx)
        assert op.p["cadena"] is marcada
        assert cmd.desde_op(op, ctx)["cadena"] is marcada
