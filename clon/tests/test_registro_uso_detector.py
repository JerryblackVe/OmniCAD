"""Cada regla del detector con una sesión armada a mano, y una sesión limpia sin hallazgos."""
from omnicad.registro_uso import detector


def ev(t, tipo, **datos):
    return {"t": t, "ts": f"2026-10-26T12:00:{t:06.3f}Z", "tipo": tipo, "datos": datos, "seq": int(t * 1000) + 1}


def test_sesion_limpia_no_dispara_nada():
    eventos = [
        ev(0, "sesion_inicio", version="0.1.4"),
        ev(1, "comando_abierto", comando="cilindro"),
        ev(1.5, "comando_editado", comando="cilindro", cambios=1, valores={"alto": 35}),
        ev(3.2, "comando_aceptado", comando="cilindro", duracion_s=2.2, cambios=1),
        ev(3.3, "op_ejecutada", paso="op1", tipo_op="primitiva", duracion_ms=500, exito=True),
        ev(3.4, "recalculo", duracion_ms=650, lentos=[]),
        ev(4, "archivo_abrir", formato="omnicad", tamano=1200, duracion_ms=1500, exito=True),
        ev(5, "clic", objetivo=77, x=10, y=10),
        ev(5.2, "clic", objetivo=77, x=10, y=10),
        ev(5.4, "clic", objetivo=77, x=10, y=10),
        ev(5, "visor_cuadros", fps_promedio=58, fps_p95=56, fps_minimo=48, cuadros=240),
        ev(0, "memoria", rss=100_000_000, objetos_occ=10),
        ev(301, "memoria", rss=105_000_000, objetos_occ=11),
        ev(320, "comando_cancelado", comando="empalme", duracion_s=1, cambios=0),
        ev(330, "deshacer"),
    ]
    assert detector.analizar(eventos) == []


def test_cada_regla_dispara_una_vez():
    eventos = [
        ev(1, "op_ejecutada", paso="op1", tipo_op="extrusion", duracion_ms=2500, exito=True),
        ev(2.5, "deshacer"),
        ev(3, "bloqueo_ui", duracion_ms=400, comando="extruir"),
        ev(4, "visor_cuadros", fps_promedio=20, fps_p95=12, fps_minimo=8, cuadros=60),
        ev(5, "comando_resultado", comando="empalme", exito=False),
        ev(5.5, "comando_resultado", comando="empalme", exito=False),
        ev(10, "dialogo_inactivo", comando="agujero", duracion_s=25),
        ev(11, "clic", objetivo=5, x=1, y=1),
        ev(11.2, "clic", objetivo=5, x=1, y=1),
        ev(11.4, "clic", objetivo=5, x=1, y=1),
        ev(11.6, "clic", objetivo=5, x=1, y=1),
        ev(11.8, "clic", objetivo=5, x=1, y=1),
        ev(0, "memoria", rss=100_000_000, objetos_occ=10),
        ev(300, "memoria", rss=140_000_000, objetos_occ=10),
        ev(301, "error", origen="qt_slot", excepcion="RuntimeError", comando="empalme"),
        ev(302, "error", origen="operacion", categoria="error", paso="op7"),
        ev(350, "archivo_abrir", formato="omnicad", tamano=99, duracion_ms=11000, exito=True),
    ]
    for t in (20, 21, 22):
        eventos.append(ev(t, "comando_cancelado", comando="empalme", duracion_s=1, cambios=0))
    reglas = {h["regla"] for h in detector.analizar(eventos)}
    assert {"operacion_lenta", "apertura_lenta", "bloqueo_ui", "visor_lento", "falla_repetida",
            "deshacer_inmediato", "duda_larga", "clics_repetidos", "memoria", "error",
            "cancelaciones"} <= reglas
    assert all(h["severidad"] in ("alta", "media", "baja") for h in detector.analizar(eventos))
    assert all("|" in h["sugerencia"] and h["ts"] for h in detector.analizar(eventos))


def test_umbrales_configurables():
    eventos = [ev(1, "op_ejecutada", paso="op1", tipo_op="extrusion", duracion_ms=2500, exito=True)]
    assert detector.analizar(eventos)
    assert detector.analizar(eventos, {"operacion_lenta_s": 10}) == []


def test_resumen_tiempos_operaciones_y_errores():
    eventos = [
        ev(0, "comando_abierto", comando="cilindro"),
        ev(1, "comando_editado", comando="cilindro", cambios=1, valores={"alto": 35}),
        ev(2, "comando_aceptado", comando="cilindro", duracion_s=2.0, cambios=1),
        ev(2.1, "op_ejecutada", paso="op1", tipo_op="primitiva", duracion_ms=2500, exito=True,
           despues={"cuerpos": 1, "volumen": 6000}),
        ev(3, "error", origen="api", excepcion="ValueError", comando="cilindro"),
        ev(4, "seleccion", categoria="cara", cantidad=1, duracion_ms=12),
        ev(5, "recalculo", duracion_ms=700, lentos=[]),
    ]
    r = detector.resumir(eventos)
    assert r["comandos"]["cilindro"] == {"abiertos": 1, "aceptados": 1, "cancelados": 0,
                                         "cambios": 1, "tiempo_s": 2.0}
    assert r["operaciones_lentas"][0]["paso"] == "op1"
    assert r["errores"] == 1 and r["recalculos"]["total_ms"] == 700
    assert r["picking_ms_promedio"] == 12
    assert r["hallazgos_por_severidad"]["media"] == 1    # operación lenta
    assert r["hallazgos_por_severidad"]["alta"] == 1     # error
