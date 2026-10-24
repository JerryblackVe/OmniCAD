"""BOC-4 y BOC-5: AutoConstrain completo (tipos inferidos, opciones, proponer sin aplicar, Finish)."""
import math
from time import perf_counter

import pytest

from omnicad import api
from test_p23_navegador import v as v, ventana as ventana  # noqa: F401  (fixtures de la ventana en vivo)
from omnicad.restricciones import Boceto, auto_restringir, grados_de_libertad, resolver, sugerir_auto_restricciones


def _valores(b):
    return {k.id: float(k.expresion) for k in b.cotas.values()}


def _tipos(b):
    return [r.tipo for r in b.restricciones.values() if r.tipo != "fijo"]       # sin el dato del origen


def _cotas(b):
    return [k.tipo for k in b.cotas.values()]


def _sin_mover(b):
    """Auto-restringir solo agrega: resolver con todo lo agregado deja la geometría donde estaba."""
    antes = {p: b.coords(p) for p in b.puntos}
    valores = _valores(b)
    r = resolver(b, valores)
    assert r.ok, r.descripcion()
    for p, xy in antes.items():
        assert b.coords(p) == pytest.approx(xy, abs=2e-3)
    assert grados_de_libertad(b, valores) == 0


# ---------------------------------------------------------------- BOC-4: tipos inferidos
def test_boc4_circulos_concentricos_dan_concentrica():
    b = Boceto()
    b.agregar_circulo((3, 4), 5)
    b.agregar_circulo((3, 4), 10)
    agregado = auto_restringir(b)
    assert _tipos(b) == ["concentrica"]
    assert "coincidente" not in _tipos(b)
    assert sorted(_cotas(b)) == ["diametro", "diametro", "distancia_h", "distancia_v"]
    assert agregado[0].descripcion.startswith("concentrica")
    _sin_mover(b)


def test_boc4_l_girada_da_perpendicular_en_vez_de_cotas():
    b = Boceto()
    o = b.agregar_punto(1, 2)
    a = math.radians(30)
    p = b.agregar_punto(1 + 10 * math.cos(a), 2 + 10 * math.sin(a))
    q = b.agregar_punto(1 - 6 * math.sin(a), 2 + 6 * math.cos(a))
    b.agregar_linea(o, p)
    b.agregar_linea(o, q)
    auto_restringir(b)
    assert "perpendicular" in _tipos(b)
    assert "angulo" not in _cotas(b)
    assert _cotas(b).count("distancia") == 2
    _sin_mover(b)


def test_boc4_circulo_apoyado_en_una_linea_da_tangente():
    b = Boceto()
    b.agregar_linea((-10, 0), (10, 0))
    b.agregar_circulo((2, 3), 3)
    auto_restringir(b)
    assert "tangente" in _tipos(b)
    _sin_mover(b)


def test_boc4_circulos_tangentes_exterior_e_interior():
    b = Boceto()
    b.agregar_circulo((0, 0), 3)
    b.agregar_circulo((8, 0), 5)       # exterior: 3 + 5
    b.agregar_circulo((0, 6), 9)       # interior con el primero: |9 - 3|
    auto_restringir(b)
    assert _tipos(b).count("tangente") == 2
    _sin_mover(b)


def test_boc4_arco_encadenado_a_una_linea_es_tangente():
    b = Boceto()
    p0 = b.agregar_punto(0, 0)
    p1 = b.agregar_punto(10, 0)
    b.agregar_linea(p0, p1)
    centro = b.agregar_punto(10, 5)
    fin = b.agregar_punto(15, 5)
    arco = b.agregar_arco_centro(centro, p1, fin)
    auto_restringir(b)
    r = next(r for r in b.restricciones.values() if r.tipo == "tangente")
    assert arco in r.entidades
    _sin_mover(b)


def test_boc4_linea_y_elipse_tangentes():
    b = Boceto()
    b.agregar_linea((-20, 0), (20, 0))
    b.agregar_elipse((3, 4), (3 + 6, 4), 4, ejes=False)     # semieje menor 4 apoyado en y = 0
    auto_restringir(b)
    assert "tangente" in _tipos(b)
    _sin_mover(b)


def test_boc4_lineas_paralelas_y_colineales():
    b = Boceto()
    a = math.radians(25)
    c, s = math.cos(a), math.sin(a)
    b.agregar_linea((0, 0), (10 * c, 10 * s))
    b.agregar_linea((0, 8), (10 * c, 8 + 10 * s))                       # paralela a la primera
    b.agregar_linea((20 * c, 20 * s), (30 * c, 30 * s))                 # sobre la recta de la primera
    auto_restringir(b)
    assert "colineal" in _tipos(b) and "paralela" in _tipos(b)
    _sin_mover(b)


def test_boc4_punto_medio():
    b = Boceto()
    b.agregar_linea((0, 0), (10, 4))
    b.agregar_punto(5, 2)
    auto_restringir(b)
    assert "punto_medio" in _tipos(b)
    _sin_mover(b)


def test_boc4_punto_medio_de_un_arco():
    b = Boceto()
    centro = b.agregar_punto(0, 0)
    inicio = b.agregar_punto(10, 0)
    fin = b.agregar_punto(0, 10)
    arco = b.agregar_arco_centro(centro, inicio, fin)
    b.agregar_punto(10 * math.cos(math.pi / 4), 10 * math.sin(math.pi / 4))
    auto_restringir(b)
    r = next(r for r in b.restricciones.values() if r.tipo == "punto_medio")
    assert r.entidades[1] == arco
    _sin_mover(b)


def test_boc4_simetria_respecto_de_un_eje():
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10), eje=True)
    p = b.agregar_punto(3, 2)
    q = b.agregar_punto(-3, 2)
    b.agregar_circulo((5, -4), 1.5)
    b.agregar_circulo((-5, -4), 1.5)
    auto_restringir(b)
    simetricas = [r for r in b.restricciones.values() if r.tipo == "simetrica"]
    assert {tuple(r.entidades) for r in simetricas if len(r.entidades) == 3 and r.entidades[2] == eje
            and r.entidades[0] in (p, q)} == {(p, q, eje)}
    assert len(simetricas) == 2          # los puntos y los dos círculos
    _sin_mover(b)


def test_boc4_cuadrado_girado_y_boceto_mixto_queda_restringido():
    b = Boceto()
    a = math.radians(20)
    c, s = math.cos(a), math.sin(a)
    esquinas = [b.agregar_punto(12 + 10 * (x * c - y * s), 7 + 10 * (x * s + y * c))
                for x, y in ((0, 0), (1, 0), (1, 1), (0, 1))]
    for i in range(4):
        b.agregar_linea(esquinas[i], esquinas[(i + 1) % 4])
    b.agregar_circulo((12 + 5 * (c - s), 7 + 5 * (s + c)), 3)
    auto_restringir(b)
    tipos = _tipos(b)
    assert tipos.count("paralela") == 2 and "perpendicular" in tipos
    assert "angulo" not in _cotas(b)
    _sin_mover(b)


def test_boc4_no_agrega_nada_que_no_baje_los_gdl():
    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    b.agregar_linea((0, 5), (10, 5))
    auto_restringir(b)
    # horizontal x2 + (paralela/colineal no aplican: ya son horizontales) → ninguna restricción redundante
    assert "paralela" not in _tipos(b)
    assert resolver(b, _valores(b)).ok


# ---------------------------------------------------------------- opciones
def test_boc4_tolerancia_de_angulo_configurable():
    def dibujo():
        b = Boceto()
        o = b.agregar_punto(0, 0)
        p = b.agregar_punto(10, 0)
        a = math.radians(91.5)
        q = b.agregar_punto(10 * math.cos(a), 10 * math.sin(a))
        b.agregar_linea(o, p)
        b.agregar_linea(o, q)
        return b

    ajustado, flojo = dibujo(), dibujo()
    auto_restringir(ajustado, tol_angulo=1.0)
    auto_restringir(flojo, tol_angulo=2.0)
    assert "perpendicular" not in _tipos(ajustado) and "vertical" not in _tipos(ajustado)
    assert "vertical" in _tipos(flojo)


def test_boc4_tolerancia_de_distancia_configurable():
    def dibujo():
        b = Boceto()
        b.agregar_linea((-10, 0), (10, 0))
        b.agregar_circulo((2, 3.01), 3)         # a 0,01 mm de ser tangente
        return b

    estricto, flojo = dibujo(), dibujo()
    auto_restringir(estricto, tol_distancia=1e-3)
    auto_restringir(flojo, tol_distancia=0.05)
    assert "tangente" not in _tipos(estricto)
    assert "tangente" in _tipos(flojo)


def test_boc4_tipos_limita_lo_que_se_infiere():
    b = Boceto()
    b.agregar_linea((-10, 0), (10, 0))
    b.agregar_circulo((2, 3), 3)
    agregado = auto_restringir(b, tipos=("tangente",))
    assert _tipos(b) == ["tangente"] and not b.cotas
    assert len(agregado) == 1


def test_boc4_tipo_desconocido_es_error():
    from omnicad.restricciones import ErrorBoceto
    with pytest.raises(ErrorBoceto, match="triangulo"):
        auto_restringir(Boceto(), tipos=("triangulo",))


def test_boc4_limite_es_un_prefijo_del_resultado_completo():
    def dibujo():
        b = Boceto()
        b.agregar_rectangulo((3, 4), (23, 14))
        b.agregar_circulo((13, 9), 2)
        return b

    completo = auto_restringir(dibujo())
    parcial = auto_restringir(dibujo(), limite=3)
    assert len(completo) > 3 and parcial == completo[:3]


def test_boc4_excluir_una_sugerencia_la_quita_del_resultado():
    def dibujo():
        b = Boceto()
        b.agregar_linea((-10, 0), (10, 0))
        b.agregar_circulo((2, 3), 3)
        return b

    resultado = sugerir_auto_restricciones(dibujo())[0]
    tangente = next(s for s in resultado.sugerencias if s.tipo == "tangente")
    nuevo = sugerir_auto_restricciones(dibujo(), excluir=[tangente.clave])[0]
    assert all(s.clave != tangente.clave for s in nuevo.sugerencias)
    assert len(nuevo.sugerencias) >= len(resultado.sugerencias) - 1


def test_boc5_datum_ordena_las_cotas_de_posicion():
    b = Boceto()
    b.agregar_linea((5, 5), (25, 5))
    b.agregar_linea((25, 5), (25, 15))
    datum = b.agregar_punto(40, 40)
    auto_restringir(b, datum=datum)
    posicion = [k for k in b.cotas.values() if k.tipo in ("distancia_h", "distancia_v")]
    assert sum(datum in k.entidades for k in posicion) >= 4         # la ubica respecto del origen y ubica a los demás
    assert grados_de_libertad(b, _valores(b)) == 0


def test_boc5_datum_inexistente_es_error():
    from omnicad.restricciones import ErrorBoceto
    b = Boceto()
    b.agregar_linea((0, 0), (1, 1))
    with pytest.raises(ErrorBoceto, match="datum"):
        auto_restringir(b, datum=999)


# ---------------------------------------------------------------- proponer sin aplicar
def _dibujo_mixto():
    b = Boceto()
    b.agregar_rectangulo((3, 4), (23, 14))
    b.agregar_circulo((13, 9), 2)
    b.agregar_linea((0, -5), (30, -5))
    return b


def test_boc5_sugerir_no_modifica_el_boceto_y_da_varios_resultados():
    b = _dibujo_mixto()
    antes = b.a_dict()
    resultados = sugerir_auto_restricciones(b, resultados=3)
    assert b.a_dict() == antes
    assert len(resultados) == 3
    assert len({r.nombre for r in resultados}) == 3
    completo, solo_restricciones = resultados[0], resultados[1]
    assert completo.gdl == 0 and completo.totalmente_restringido
    assert any(s.clase == "cota" for s in completo.sugerencias)
    assert all(s.clase == "restriccion" for s in solo_restricciones.sugerencias)
    assert not solo_restricciones.totalmente_restringido
    ultimo = completo.sugerencias[-1]
    assert ultimo.gdl == completo.gdl
    assert [s.gdl for s in completo.sugerencias] == sorted((s.gdl for s in completo.sugerencias), reverse=True)


def test_boc5_aplicar_una_sugerencia_equivale_a_auto_restringir():
    b = _dibujo_mixto()
    resultado = sugerir_auto_restricciones(b)[0]
    assert resultado.sugerencias == auto_restringir(_dibujo_mixto())


def test_boc5_generar_mas_agrega_alternativas_nuevas():
    b = _dibujo_mixto()
    tres = sugerir_auto_restricciones(b, resultados=3)
    cinco = sugerir_auto_restricciones(b, resultados=5)
    assert [r.nombre for r in cinco[:3]] == [r.nombre for r in tres]
    assert len({r.nombre for r in cinco}) == 5


# ---------------------------------------------------------------- rendimiento
def test_boc4_rendimiento_boceto_de_250_entidades():
    b = Boceto()
    for i in range(50):
        x, y = 40 * (i % 10), 40 * (i // 10)
        b.agregar_rectangulo((x, y), (x + 20, y + 10))           # 4 líneas
        b.agregar_circulo((x + 10, y + 5), 3)
    assert len(b.curvas) == 250
    inicio = perf_counter()
    auto_restringir(b)
    segundos = perf_counter() - inicio
    print(f"BOC-4 250 entidades: {segundos:.2f} s", flush=True)
    assert segundos < 10
    assert grados_de_libertad(b, _valores(b)) == 0


def test_boc4_rendimiento_440_lineas_inclinadas_aisladas():
    b = Boceto()
    c, s = math.cos(math.radians(33)), math.sin(math.radians(33))
    for i in range(440):
        x, y = 30 * (i % 20), 30 * (i // 20)
        b.agregar_linea((x, y), (x + 10 * c, y + 10 * s))
    inicio = perf_counter()
    auto_restringir(b)
    segundos = perf_counter() - inicio
    print(f"BOC-4 440 inclinadas: {segundos:.2f} s; {len(b.restricciones)} restr.", flush=True)
    assert segundos < 30
    assert "paralela" in _tipos(b)
    assert grados_de_libertad(b, _valores(b)) == 0


# ---------------------------------------------------------------- API
def llamar(sesion, nombre, **argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.fixture
def sesion():
    s = api.Sesion()
    llamar(s, "create_sketch", name="Base")
    llamar(s, "draw_line", start_x=-10, start_y=0, end_x=10, end_y=0)
    llamar(s, "draw_circle", center_x=2, center_y=3, radius=3)
    return s


def test_boc5_api_suggest_no_cambia_el_documento(sesion):
    antes = sesion.doc.a_dict()
    historial = len(sesion.doc._deshacer)
    r = llamar(sesion, "suggest_auto_constraints", results=3)
    assert sesion.doc.a_dict() == antes and len(sesion.doc._deshacer) == historial
    assert len(r["results"]) == 3
    primero = r["results"][0]
    assert primero["fully_constrained"] is True and primero["dof"] == 0
    assert {"kind", "type", "entities", "description", "dof"} <= set(primero["items"][0])
    assert any(i["type"] == "tangent" for i in primero["items"])
    assert primero["constraints"] + primero["dimensions"] == len(primero["items"])


def test_boc5_api_auto_constrain_con_opciones(sesion):
    r = llamar(sesion, "auto_constrain", types=["tangent"])
    assert [i["type"] for i in r["items"]] == ["tangent"] and r["dof"] > 0
    info = llamar(sesion, "get_sketch")
    assert [c["type"] for c in info["constraints"]] == ["tangent"]


def test_boc5_api_auto_constrain_max_items_y_exclude(sesion):
    sugerido = llamar(sesion, "suggest_auto_constraints")["results"][0]["items"]
    tangente = next(i for i in sugerido if i["type"] == "tangent")
    r = llamar(sesion, "auto_constrain", exclude=[{"type": "tangent", "entities": tangente["entities"]}], max_items=2)
    assert len(r["items"]) == 2 and all(i["type"] != "tangent" for i in r["items"])
    assert r["added"] == [i["description"] for i in r["items"]]


def test_boc5_api_datum(sesion):
    puntos = llamar(sesion, "get_sketch")["points"]
    datum = puntos[0]["id"]
    r = llamar(sesion, "auto_constrain", datum=datum)
    assert r["dof"] == 0
    dimensiones = llamar(sesion, "get_sketch")["dimensions"]
    assert any(datum in d["entities"] for d in dimensiones) or any(
        c["type"] == "fix" for c in llamar(sesion, "get_sketch")["constraints"])


@pytest.mark.parametrize("herramienta,argumentos", [
    ("auto_constrain", {"tolerance_angle": -1}), ("auto_constrain", {"tolerance_distance": 0}),
    ("auto_constrain", {"types": ["triangle"]}), ("auto_constrain", {"max_items": -1}),
    ("auto_constrain", {"datum": 999}), ("suggest_auto_constraints", {"tolerance_angle": 91}),
    ("suggest_auto_constraints", {"types": ["triangle"]}), ("suggest_auto_constraints", {"datum": 999}),
    ("suggest_auto_constraints", {"results": 0}), ("suggest_auto_constraints", {"results": 13})])
def test_boc5_api_opciones_invalidas_son_error_atomico(sesion, herramienta, argumentos):
    antes = sesion.doc.a_dict()
    r = api.llamar(sesion, herramienta, argumentos)
    assert r["ok"] is False and r["error_kind"] in ("INVALID_ARGUMENTS", "INVALID_GEOMETRY"), r
    assert sesion.doc.a_dict() == antes


def test_boc5_api_finish_with_auto_constrain_necesita_ventana(sesion):
    r = api.llamar(sesion, "sketch_view", {"sketch": "Base", "action": "finish_with_auto_constrain"})
    assert r["ok"] is False and r["error_kind"] == "APP_NOT_RUNNING"


# ---------------------------------------------------------------- BOC-5: interfaz (diálogo y Terminar con AutoConstrain)
@pytest.fixture(scope="module")
def app_qt():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _tangente_en_linea():
    b = Boceto()
    b.agregar_linea((-10, 0), (10, 0))
    b.agregar_circulo((2, 3), 3)
    return b


def test_boc5_dialogo_resultados_cantidad_quitar_y_reiniciar(app_qt):
    from omnicad.ui.dialogo_autorestringir import DialogoAutoRestringir

    d = DialogoAutoRestringir(_tangente_en_linea(), {})
    assert len(d.resultados) == 3 and d.lista.count() == 3
    completo = d.resultado()
    assert completo.totalmente_restringido and d.cantidad.maximum() == len(completo.sugerencias)
    assert "totalmente restringido" in d.lista.item(0).text() and d.aceptar.isEnabled()
    d.cantidad.setValue(1)                                   # deslizador: solo la primera sugerencia
    assert d.detalle.count() == 1 and d.opciones()["limite"] == 1
    assert "quedan" in d.estado.text()
    d.cantidad.setValue(d.cantidad.maximum())
    fila = [s.tipo for s in completo.sugerencias].index("tangente")
    d.detalle.setCurrentRow(fila)
    d._quitar()
    assert all(s.tipo != "tangente" for s in d.resultado().sugerencias) and len(d.excluidas) == 1
    d._reiniciar()
    assert not d.excluidas and any(s.tipo == "tangente" for s in d.resultado().sugerencias)
    d._generar_mas()
    assert d.pedidos == 5 and len(d.resultados) == 5
    d.tol_distancia.setValue(0.05)
    d._calcular()
    assert d.opciones()["tol_distancia"] == 0.05


def test_boc5_dialogo_boceto_ya_restringido_no_ofrece_nada(app_qt):
    from omnicad.ui.dialogo_autorestringir import DialogoAutoRestringir

    b = Boceto()
    p = b.agregar_punto(0, 0)
    b.agregar_restriccion("fijo", [p])
    d = DialogoAutoRestringir(b, {})
    assert not d.aceptar.isEnabled() and "No hay nada" in d.estado.text()


def test_boc5_lienzo_aplica_el_resultado_elegido_del_dialogo(app_qt, monkeypatch):
    from PySide6.QtWidgets import QDialog

    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.dialogo_autorestringir import DialogoAutoRestringir
    from omnicad.ui.editor_boceto import Lienzo

    lz = Lienzo(_tangente_en_linea(), TablaParametros().evaluar)
    monkeypatch.setattr(DialogoAutoRestringir, "exec", lambda self: QDialog.Accepted)
    agregado = lz.auto_restringir_dialogo()
    assert agregado and lz.resultado.gdl == 0 and "tangente" in _tipos(lz.b)

    lz = Lienzo(_tangente_en_linea(), TablaParametros().evaluar)
    monkeypatch.setattr(DialogoAutoRestringir, "exec", lambda self: QDialog.Rejected)
    assert lz.auto_restringir_dialogo() == [] and not lz.b.restricciones


def test_boc5_lienzo_vacio_no_abre_el_dialogo(app_qt):
    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.editor_boceto import Lienzo

    lz = Lienzo(Boceto(), TablaParametros().evaluar)
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    assert lz.auto_restringir_dialogo() == [] and "vacío" in mensajes[0]



def _boceto_en_ventana(v, b):
    from omnicad.timeline.operaciones import OpBoceto
    ident = v.doc.nuevo_id()
    v.doc.agregar(OpBoceto(ident, "Boceto de prueba", plano="XY", boceto=b))
    return ident


def test_boc5_terminar_con_autoconstrain_en_la_ventana(v, tmp_path):
    from omnicad.ui.puente import PuenteAgentes

    ident = _boceto_en_ventana(v, _tangente_en_linea())
    puente = PuenteAgentes(v, archivo=tmp_path / "puente.json")
    assert puente.ejecutar("sketch_view", {"sketch": ident, "action": "edit"})["ok"]
    r = puente.ejecutar("sketch_view", {"sketch": ident, "action": "finish_with_auto_constrain"})
    assert r["ok"] and any(a.startswith("tangente") for a in r["result"]["added"]), r
    assert not v.modo_boceto.activo
    assert v.doc.estado_final.bocetos[ident].solver.totalmente_restringido


def test_boc5_terminar_con_autoconstrain_pasado_el_tope_termina_igual(v, tmp_path):
    from omnicad.restricciones import TOPE_TERMINAR_AUTO
    from omnicad.ui.puente import PuenteAgentes

    b = Boceto()
    for i in range(TOPE_TERMINAR_AUTO + 1):
        b.agregar_punto(i, 0)
    ident = _boceto_en_ventana(v, b)
    puente = PuenteAgentes(v, archivo=tmp_path / "puente.json")
    assert puente.ejecutar("sketch_view", {"sketch": ident, "action": "edit"})["ok"]
    r = puente.ejecutar("sketch_view", {"sketch": ident, "action": "finish_with_auto_constrain"})
    assert r["ok"] and r["result"]["added"] == []
    assert not v.modo_boceto.activo and not v.doc.operaciones[-1].boceto.restricciones


# ---------------------------------------------------------------- red de seguridad y casos límite
def test_boc4_arcos_simetricos_respetan_el_sentido():
    b = Boceto()
    eje = b.agregar_linea((0, -10), (0, 10), eje=True)
    for signo in (1, -1):         # el reflejo invierte el sentido: el arco de la izquierda sale de la derecha al revés
        centro = b.agregar_punto(6 * signo, 0)
        a, c = (b.agregar_punto(6 * signo + 3 * signo, 0), b.agregar_punto(6 * signo, 3)) if signo == 1 else (
            b.agregar_punto(6 * signo, 3), b.agregar_punto(6 * signo + 3 * signo, 0))
        b.agregar_arco_centro(centro, a, c)
    auto_restringir(b, tipos=("simetrica",))
    simetricas = [r for r in b.restricciones.values() if r.tipo == "simetrica" and r.entidades[2] == eje]
    assert simetricas and all(len(r.entidades) == 3 for r in simetricas)
    antes = {k: b.coords(k) for k in b.puntos}
    assert resolver(b, _valores(b)).ok
    assert all(b.coords(k) == pytest.approx(xy, abs=2e-3) for k, xy in antes.items())


def test_boc4_restriccion_que_la_geometria_no_cumple_no_suma_rango():
    import math as m

    from omnicad.restricciones.solver import _GradosAuto

    b = Boceto()
    b.agregar_linea((0, 0), (10, 0))
    b.agregar_linea((0, 5), (10 * m.cos(m.radians(30)), 5 + 10 * m.sin(m.radians(30))))     # 30° de la primera
    calcular = _GradosAuto(b, {})
    inicial = calcular()
    falsa = b.agregar_restriccion("paralela", list(b.curvas))
    assert calcular(falsa, (1e-3, m.sin(m.radians(1)))) == inicial          # no cumple: ni se cuenta
    b.eliminar(falsa)
    real = b.agregar_restriccion("horizontal", [next(iter(b.curvas))])
    assert calcular(real, (1e-3, m.sin(m.radians(1)))) == inicial - 1       # el rango no quedó contaminado


def test_boc5_sugerir_sin_nada_que_variar_no_agota_la_paciencia():
    b = Boceto()
    for i in range(60):
        b.agregar_restriccion("fijo", [b.agregar_punto(i, 0)])
    inicio = perf_counter()
    resultados = sugerir_auto_restricciones(b, resultados=5)
    assert len(resultados) == 1 and resultados[0].sugerencias == [] and perf_counter() - inicio < 10


# ---------------------------------------------------------------- BOC-5: vista previa en violeta sobre el lienzo
def _pixeles_violeta(lz):
    from omnicad.ui.editor_boceto import VIOLETA
    lz.resize(640, 420)
    lz.encuadrar()
    imagen = lz.grab().toImage()
    objetivo = VIOLETA.rgb()
    return sum(imagen.pixel(x, y) == objetivo for x in range(imagen.width()) for y in range(imagen.height()))


def test_boc5_el_dialogo_emite_la_vista_previa_del_resultado_y_la_cantidad(app_qt):
    from omnicad.ui.dialogo_autorestringir import DialogoAutoRestringir

    emitidas = []
    d = DialogoAutoRestringir(_tangente_en_linea(), {})
    d.previa.connect(lambda lista: emitidas.append(list(lista)))
    d.cantidad.setValue(2)
    assert emitidas[-1] == d.resultado().sugerencias[:2]
    d.cantidad.setValue(0)
    assert emitidas[-1] == []


def test_boc5_el_lienzo_pinta_la_previa_en_violeta_y_la_borra(app_qt, monkeypatch):
    from PySide6.QtWidgets import QDialog

    from omnicad.timeline.parametros import TablaParametros
    from omnicad.ui.dialogo_autorestringir import DialogoAutoRestringir
    from omnicad.ui.editor_boceto import Lienzo

    lz = Lienzo(_tangente_en_linea(), TablaParametros().evaluar)
    assert _pixeles_violeta(lz) == 0
    sugerencias = sugerir_auto_restricciones(lz.b)[0].sugerencias
    lz.set_previa_auto(sugerencias)
    assert _pixeles_violeta(lz) > 50                       # restricciones (íconos) y cotas (texto) en violeta
    lz.set_previa_auto([])
    assert _pixeles_violeta(lz) == 0

    visto = []

    def exec_falso(self):                                  # el diálogo abierto deja la previa pintada en el lienzo
        visto.append(len(lz.previa_auto))
        return QDialog.Rejected
    monkeypatch.setattr(DialogoAutoRestringir, "exec", exec_falso)
    lz.auto_restringir_dialogo()
    assert visto[0] > 0 and lz.previa_auto == [] and _pixeles_violeta(lz) == 0     # al cerrar se borra


def test_boc5_sin_sugerencias_la_previa_se_vacia(app_qt):
    from omnicad.ui.dialogo_autorestringir import DialogoAutoRestringir

    emitidas = []
    d = DialogoAutoRestringir(_tangente_en_linea(), {})
    d.previa.connect(lambda lista: emitidas.append(list(lista)))
    d.tol_distancia.setValue(0.0001)
    d.resultados = []                              # un recálculo sin resultados
    d.lista.clear()
    d._elegir(-1)
    assert emitidas[-1] == []
