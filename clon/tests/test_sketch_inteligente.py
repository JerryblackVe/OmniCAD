"""Sketch inteligente: ayudas de dibujo (inferencias, alineaciones, capturas) y restricciones que dejan al confirmar."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from test_boceto_fase5_ui import _clic, _mover  # noqa: E402
from test_boceto_fase5_ui import lienzo as lienzo  # noqa: E402,F401


def test_geometria_oculta_no_atrae_el_cursor(lienzo):
    """Una construcción oculta no se ve: tampoco puede capturar el cursor (ni su punto medio ni sus extremos)."""
    lz = lienzo
    lz.b.agregar_linea((30, 30), (70, 30), True)          # construcción
    lz.resolver()
    lz.mostrar["construccion"] = False
    lz.set_herramienta("linea")
    _mover(lz, 50.1, 30.1)                            # sobre su punto medio
    assert lz.inf_actual is None
    _mover(lz, 30.1, 30.1)                            # sobre su extremo
    assert lz.cursor == pytest.approx((30.1, 30.1), abs=1e-6)


# ---------------------------------------------------------------- motor de inferencias (puro, sin Qt)
from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.restricciones.inferencia import Indice, inferencias, inferir  # noqa: E402


def _triangulo():
    b = Boceto()
    b.agregar_linea((-75, 0), (0, 0))
    b.agregar_linea((0, 0), (0, 75))
    b.agregar_linea((0, 75), (-75, 0))
    return b


def test_alineacion_horizontal_con_un_vertice_es_solo_guia():
    """Caso A: el vértice (0, 75) está a la misma altura que el cursor; hay guía pero ninguna restricción."""
    r = inferir(_triangulo(), (40, 75.1), 0.5)
    assert r.tipo == "alineado_h" and r.restriccion is None
    assert r.xy == pytest.approx((40, 75), abs=1e-9)
    assert r.guias == [((0.0, 75.0), (40, 75))]
    assert "punto" in r.etiqueta.lower()


def test_alineacion_vertical_con_un_vertice():
    """Caso B: misma X que el vértice (-75, 0)."""
    r = inferir(_triangulo(), (-75.2, 40), 0.5)
    assert r.tipo == "alineado_v" and r.restriccion is None
    assert r.xy == pytest.approx((-75, 40), abs=1e-9)


def test_cruce_de_dos_guias_de_puntos_distintos():
    """Caso C: la X de un punto y la Y de otro fijan una posición virtual."""
    b = Boceto()
    b.agregar_punto(30, 80)
    b.agregar_punto(90, 50)
    r = inferir(b, (30.2, 49.9), 0.5)
    assert r.tipo == "alineado_hv" and r.restriccion is None
    assert r.xy == pytest.approx((30, 50), abs=1e-9)
    assert len(r.guias) == 2


def test_alineacion_con_un_punto_medio_y_con_un_centro():
    """Caso D: se alinea con el medio de una línea y con el centro de un círculo."""
    b = Boceto()
    b.agregar_linea((10, 10), (50, 10))             # medio (30, 10)
    b.agregar_circulo((100, 60), 5)
    assert "medio" in inferir(b, (30.1, 40), 0.5).etiqueta
    assert "centro" in inferir(b, (150, 59.9), 0.5).etiqueta


def test_alineacion_se_combina_con_horizontal_de_la_base():
    """La línea sale de la base en horizontal y su extremo cae en la X de otro punto: restricción horizontal."""
    b = Boceto()
    b.agregar_punto(60, 80)
    r = inferir(b, (60.2, 20.3), 0.5, base=(10, 20))
    assert r.tipo == "horizontal" and r.restriccion == ("horizontal",)
    assert r.xy == pytest.approx((60, 20), abs=1e-9)
    assert len(r.guias) == 2


def test_interseccion_real_de_dos_lineas_pone_las_dos_coincidencias():
    b = Boceto()
    a = b.agregar_linea((0, 0), (40, 40))
    c = b.agregar_linea((0, 40), (40, 0))
    r = inferir(b, (20.2, 19.8), 0.5, tipos={"interseccion"})
    assert r.tipo == "interseccion" and r.xy == pytest.approx((20, 20), abs=1e-6)
    assert r.restriccion[0] == "coincidente" and r.restriccion[2][0] == "coincidente"
    assert {r.restriccion[1], r.restriccion[2][1]} == {a, c}


def test_interseccion_aparente_no_existe_si_los_tramos_no_se_cruzan():
    b = Boceto()
    b.agregar_linea((0, 0), (10, 10))
    b.agregar_linea((0, 40), (10, 30))              # sus prolongaciones se cruzan en (20, 20), pero no los tramos
    assert inferir(b, (20, 20), 0.5, tipos={"interseccion"}) is None


@pytest.mark.parametrize("escala", [0.01, 1.0, 100.0])
def test_tolerancia_en_pixeles_es_la_misma_con_cualquier_zoom(escala):
    """8 px de pantalla son 8/escala mm: la alineación aparece a 7 px y no a 9 px, sea cual sea el zoom."""
    b = Boceto()
    b.agregar_punto(0, 1000 * escala)
    tol = 8 / (1 / escala)                           # px_por_mm = 1/escala
    cerca = inferir(b, (500 * escala, 1000 * escala + 7 * escala), tol)
    lejos = inferir(b, (500 * escala, 1000 * escala + 9 * escala), tol)
    assert cerca is not None and cerca.tipo == "alineado_h"
    assert lejos is None


def test_alineacion_lejos_del_origen_y_con_geometria_inclinada():
    b = Boceto()
    b.agregar_linea((1e5, 1e5), (1e5 + 30, 1e5 + 40))       # inclinada y a 100 m del origen
    r = inferir(b, (1e5 + 500, 1e5 + 40.1), 0.5)
    assert r.tipo == "alineado_h" and r.xy == pytest.approx((1e5 + 500, 1e5 + 40), abs=1e-6)


def test_la_geometria_excluida_no_alinea():
    b = Boceto()
    cid = b.agregar_linea((0, 50), (20, 80))
    assert inferir(b, (60, 50.1), 0.5, excluir=(cid,)) is None


def test_tipos_apagados_no_aparecen():
    b = _triangulo()
    assert inferir(b, (40, 75.1), 0.5, tipos={"medio"}) is None
    assert inferir(b, (40, 75.1), 0.5, tipos=set()) is None


def test_historesis_mantiene_al_candidato_activo_un_poco_mas_lejos():
    b = Boceto()
    b.agregar_punto(0, 50)
    b.agregar_punto(0, 50.6)
    activo = inferir(b, (30, 50.3), 0.5)                     # los dos puntos alinean: gana el de 50
    assert activo.xy[1] == pytest.approx(50)
    # el cursor sube hasta quedar más cerca del otro: sin previa salta; con previa se queda
    assert inferir(b, (30, 50.45), 0.5).xy[1] == pytest.approx(50.6)
    assert inferir(b, (30, 50.45), 0.5, previa=activo).xy[1] == pytest.approx(50)
    # pero no se queda para siempre: más allá de 1,4 veces la tolerancia se suelta
    assert inferir(b, (30, 50.8), 0.5, previa=activo).xy[1] == pytest.approx(50.6)


def test_alternativa_recorre_las_ayudas_ambiguas_en_vueltas():
    b = Boceto()
    b.agregar_linea((0, 0), (20, 0))
    b.agregar_linea((10, -10), (10, 10))                     # se cruzan en (10, 0), que además es medio de la primera
    todas = inferencias(b, (10.1, 0.1), 0.5)
    assert len(todas) >= 2
    assert inferir(b, (10.1, 0.1), 0.5, alternativa=1) == todas[1]
    assert inferir(b, (10.1, 0.1), 0.5, alternativa=len(todas)) == todas[0]


def test_con_indice_da_lo_mismo_que_sin_indice():
    b = _triangulo()
    indice = Indice(b)
    for cur in [(40, 75.1), (-75.2, 40), (-37.5, 37.4), (12, 12)]:
        assert inferir(b, cur, 0.5, indice=indice) == inferir(b, cur, 0.5)


def test_las_ayudas_no_modifican_el_boceto_y_son_deterministas():
    b = _triangulo()
    antes = b.a_dict()
    a = inferencias(b, (-37.6, 37.4), 0.5, base=(5, 5))
    assert a == inferencias(b, (-37.6, 37.4), 0.5, base=(5, 5))
    assert b.a_dict() == antes


# ---------------------------------------------------------------- en el lienzo, con el ratón (como un usuario)
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from omnicad.restricciones import Boceto as _Boceto  # noqa: E402,F401


def _lienzo_con_triangulo(lz):
    lz.b.agregar_linea((-75, 0), (0, 0))
    lz.b.agregar_linea((0, 0), (0, 75))
    lz.b.agregar_linea((0, 75), (-75, 0))
    lz.resolver()
    lz.set_herramienta("linea")


def _restricciones(lz):
    return sorted((r.tipo, tuple(r.entidades)) for r in lz.b.restricciones.values())


def test_la_linea_se_alinea_con_un_vertice_y_no_deja_restricciones_falsas(lienzo):
    """Fusion: la guía horizontal desde el vértice (0, 75) ayuda a poner el extremo a su altura, sin restricción."""
    lz = lienzo
    _lienzo_con_triangulo(lz)
    antes = _restricciones(lz)
    _clic(lz, 40, 10)
    _mover(lz, 60.1, 75.2)
    assert lz.inf_actual.tipo == "alineado_h" and lz.inf_actual.restriccion is None
    _clic(lz, 60.1, 75.2)
    nueva = lz.b.curvas[lz._ultima_linea]
    assert lz.b.coords(nueva.p2) == pytest.approx((60.1, 75.0), abs=1e-6)
    assert _restricciones(lz) == antes                   # la guía es temporal: nada se guardó
    assert lz.resultado.ok


def test_vertical_desde_la_base_alineada_con_otro_punto_deja_solo_la_vertical(lienzo):
    lz = lienzo
    _lienzo_con_triangulo(lz)
    _clic(lz, 40, 10)
    _clic(lz, 40.2, 75.2)                                # misma Y que el vértice (0, 75) y vertical desde la base
    nueva = lz.b.curvas[lz._ultima_linea]
    assert lz.b.coords(nueva.p1) == pytest.approx((40, 10), abs=1e-6)
    assert lz.b.coords(nueva.p2) == pytest.approx((40, 75), abs=1e-6)
    tipos = [r.tipo for r in lz.b.restricciones.values() if nueva.id in r.entidades]
    assert tipos == ["vertical"]
    assert lz.resultado.ok


def test_extremo_en_la_interseccion_de_dos_lineas_queda_sobre_las_dos(lienzo):
    lz = lienzo
    a = lz.b.agregar_linea((10, 10), (50, 50))
    c = lz.b.agregar_linea((10, 50), (50, 10))
    lz.resolver()
    lz.set_herramienta("linea")
    _clic(lz, 80, 20)
    _clic(lz, 30.2, 29.8)
    nueva = lz.b.curvas[lz._ultima_linea]
    assert lz.b.coords(nueva.p2) == pytest.approx((30, 30), abs=1e-6)
    destinos = {r.entidades[1] for r in lz.b.restricciones.values()
                if r.tipo == "coincidente" and r.entidades[0] == nueva.p2}
    assert destinos == {a, c}
    assert lz.resultado.ok


def test_deshacer_y_rehacer_con_capturas_y_restricciones_automaticas(lienzo):
    lz = lienzo
    _lienzo_con_triangulo(lz)
    antes = lz.b.a_dict()
    _clic(lz, 40, 10)
    _clic(lz, 40.2, 75.2)
    despues = lz.b.a_dict()
    assert despues != antes
    lz.deshacer()
    assert lz.b.a_dict() == antes
    lz.rehacer()
    assert lz.b.a_dict() == despues


def test_guardar_y_reabrir_conserva_las_restricciones_confirmadas(lienzo):
    lz = lienzo
    _lienzo_con_triangulo(lz)
    _clic(lz, 40, 10)
    _clic(lz, 40.2, 75.2)
    reabierto = Boceto.desde_dict(lz.b.a_dict())
    assert sorted((r.tipo, tuple(r.entidades)) for r in reabierto.restricciones.values()) == _restricciones(lz)


def test_ctrl_apaga_las_ayudas_mientras_se_mantiene(lienzo):
    lz = lienzo
    _lienzo_con_triangulo(lz)
    _clic(lz, 40, 10)
    _mover(lz, 60.1, 75.2, Qt.ControlModifier)
    assert lz.inf_actual is None and lz.cursor == pytest.approx((60.1, 75.2), abs=1e-6)
    _mover(lz, 60.1, 75.2)
    assert lz.inf_actual is not None


def test_ajustes_apagan_las_inferencias_o_solo_las_restricciones(lienzo):
    lz = lienzo
    _lienzo_con_triangulo(lz)
    lz.ajustes_inf["inferencias"] = False
    _clic(lz, 40, 10)
    _mover(lz, 40.2, 75.2)
    assert lz.inf_actual is None
    lz.ajustes_inf["inferencias"] = True
    lz.ajustes_inf["restricciones_auto"] = False
    _mover(lz, 40.2, 75.2)
    assert lz.inf_actual is not None and lz.inf_actual.restriccion is None and lz.inferencia is None
    _clic(lz, 40.2, 75.2)
    nueva = lz.b.curvas[lz._ultima_linea]
    assert lz.b.coords(nueva.p2) == pytest.approx((40, 75), abs=1e-6)            # sigue capturando
    assert not [r for r in lz.b.restricciones.values() if nueva.id in r.entidades]   # pero no restringe


def test_espacio_alterna_entre_ayudas_y_flecha_arriba_bloquea_la_guia(lienzo):
    lz = lienzo
    a = lz.b.agregar_linea((0, 0), (20, 0))
    lz.b.agregar_linea((10, -10), (10, 10))
    lz.resolver()
    lz.set_herramienta("linea")
    _clic(lz, 60, 40)
    _mover(lz, 10.1, 0.1)
    assert len(lz.inf_lista) >= 2
    primera = lz.inf_actual
    QTest.keyClick(lz, Qt.Key_Space)
    assert lz.inf_actual is not primera and lz.inf_actual == lz.inf_lista[1]
    # bloquear una alineación y alejarse: el cursor sigue la guía
    lz._inf_alt = 0
    lz.b.agregar_punto(100, 80)
    lz.resolver()
    _mover(lz, 120, 80.2)
    assert lz.inf_actual.tipo == "alineado_h"
    QTest.keyClick(lz, Qt.Key_Up)
    _mover(lz, 140, 95)
    assert lz.cursor == pytest.approx((140, 80), abs=1e-6)
    QTest.keyClick(lz, Qt.Key_Up)                        # soltar
    _mover(lz, 140, 95)
    assert lz.cursor == pytest.approx((140, 95), abs=1e-6)
    assert a in lz.b.curvas


def test_sin_histeresis_visible_el_cursor_no_parpadea_entre_dos_puntos_casi_iguales(lienzo):
    lz = lienzo
    lz.b.agregar_punto(0, 50)
    lz.b.agregar_punto(0, 50.5)
    lz.resolver()
    lz.set_herramienta("linea")
    _clic(lz, 30, 10)
    vistos = []
    for y in (50.2, 50.24, 50.26, 50.3, 50.26, 50.24, 50.2):          # el ratón vuelve sobre sus pasos
        _mover(lz, 70, y)
        vistos.append(round(lz.cursor[1], 3))
    cambios = sum(1 for a, b in zip(vistos, vistos[1:], strict=False) if a != b)
    assert cambios <= 1, vistos


# ---------------------------------------------------------------- dirección: paralela, perpendicular, colineal
def test_paralela_a_una_linea_cercana_ajusta_el_cursor_al_rayo():
    b = Boceto()
    ref = b.agregar_linea((60, 40), (100, 70))                   # dirección 36,87°
    r = inferir(b, (83, 82.9), 2, base=(60, 65))                 # base→cursor casi paralela (37,5°, dentro de 3°)
    assert r.tipo == "paralela" and r.restriccion == ("paralela", ref)
    xy = r.xy
    assert (xy[1] - 65) * 40 - (xy[0] - 60) * 30 == pytest.approx(0, abs=1e-9)      # exactamente paralela


def test_perpendicular_por_direccion_y_colineal():
    b = Boceto()
    ref = b.agregar_linea((0, 0), (40, 0))
    r = inferir(b, (70.3, 40), 2, base=(70, 10), tipos={"paralela"})                 # vertical, perpendicular a ref
    assert r.tipo == "perpendicular_dir" and r.restriccion == ("perpendicular", ref)
    assert r.xy[0] == pytest.approx(70, abs=1e-9)
    c = inferir(b, (90, 0.8), 3, base=(40, 0), tipos={"paralela"})                   # sigue la propia línea
    assert c.tipo == "colineal" and c.restriccion == ("colineal", ref)
    assert c.xy[1] == pytest.approx(0, abs=1e-9)


def test_la_direccion_ignora_lineas_lejanas_y_fuera_de_angulo():
    b = Boceto()
    b.agregar_linea((1000, 1000), (1040, 1030))                  # paralela, pero a 1,6 m del cursor
    assert inferir(b, (83, 82.9), 2, base=(60, 65), tipos={"paralela"}) is None
    b2 = Boceto()
    b2.agregar_linea((60, 40), (100, 70))
    assert inferir(b2, (80, 90), 2, base=(60, 65), tipos={"paralela"}) is None           # 45°: ni paralela ni ⟂


def test_la_linea_confirmada_con_paralela_queda_paralela(lienzo):
    lz = lienzo
    ref = lz.b.agregar_linea((60, 40), (100, 70))
    lz.resolver()
    lz.set_herramienta("linea")
    _clic(lz, 60, 65)
    _clic(lz, 83, 82.9)
    nueva = lz.b.curvas[lz._ultima_linea]
    assert any(r.tipo == "paralela" and set(r.entidades) == {nueva.id, ref} for r in lz.b.restricciones.values())
    assert lz.resultado.ok


def test_rectangulo_no_usa_la_direccion_paralela(lienzo):
    lz = lienzo
    lz.b.agregar_linea((60, 40), (100, 70))
    lz.resolver()
    lz.set_herramienta("rectangulo")
    _clic(lz, 60, 65)
    _mover(lz, 83, 82.9)
    assert lz.inf_actual is None or lz.inf_actual.tipo != "paralela"


def test_espacio_y_flecha_arriba_son_del_boceto_cuando_hay_una_ayuda(lienzo):
    """Espacio es también un atajo de la ventana («Boceto sobre la cara»): con ayuda activa lo reclama el boceto."""
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication

    lz = lienzo
    _lienzo_con_triangulo(lz)
    _clic(lz, 40, 10)

    def reclama(k):
        e = QKeyEvent(QEvent.ShortcutOverride, k, Qt.NoModifier)
        e.ignore()
        QApplication.sendEvent(lz, e)
        return e.isAccepted()

    _mover(lz, 70, 20)                                    # sin ayuda: no lo reclama
    assert lz.inf_lista == [] and not reclama(Qt.Key_Space)
    _mover(lz, 60.1, 75.2)
    assert lz.inf_lista and reclama(Qt.Key_Space) and reclama(Qt.Key_Up)


# ---------------------------------------------------------------- conflictos y bocetos grandes
def test_una_restriccion_inferida_que_choca_se_descarta_sin_danar_el_boceto(lienzo):
    """Prueba 11: dos puntos fijos no pueden quedar horizontales si no lo son; la inferencia se rechaza sola."""
    from omnicad.restricciones.inferencia import Inferencia

    lz = lienzo
    p1, p2 = lz.b.agregar_punto(0, 0), lz.b.agregar_punto(10, 5)
    linea = lz.b.agregar_linea(p1, p2)
    lz.b.agregar_restriccion("fijo", [p1])
    lz.b.agregar_restriccion("fijo", [p2])
    lz.resolver()
    antes = lz.b.a_dict()
    horizontal = Inferencia("horizontal", (10, 5), None, ("horizontal",))
    lz._restringir_inferencias(linea, [(p2, horizontal)])         # no lanza ni cambia nada
    assert lz.b.a_dict() == antes
    assert lz.resultado.ok


def test_boceto_grande_la_alineacion_se_encuentra_y_el_indice_es_estable():
    """Prueba 9: con 2 000 líneas dispersas la guía correcta sigue apareciendo y el resultado no depende del índice."""
    import random
    r = random.Random(3)
    b = Boceto()
    for _ in range(2000):
        x, y = r.uniform(-900, 900), r.uniform(-900, 900)
        b.agregar_linea((x, y), (x + r.uniform(-20, 20), y + r.uniform(-20, 20)))
    b.agregar_punto(2000, 123.0)                                  # fuera de todo lo anterior
    indice = Indice(b)
    sel = inferir(b, (2500, 123.0), 0.5, indice=indice)
    assert sel.tipo == "alineado_h" and sel.xy == pytest.approx((2500, 123.0), abs=1e-9)
    assert sel == inferir(b, (2500, 123.0), 0.5)


def test_al_elegir_geometria_no_hay_ayudas_de_dibujo(lienzo):
    """Simetría, Empalme… piden qué tocar, no un punto: nada de guías ni etiquetas flotando sobre el panel."""
    lz = lienzo
    _lienzo_con_triangulo(lz)
    lz.set_herramienta("simetria")
    _mover(lz, 60.1, 75.2)
    assert lz.inf_actual is None and lz.inf_lista == []
    lz.set_herramienta("empalme")
    _mover(lz, 60.1, 75.2)
    assert lz.inf_actual is None
