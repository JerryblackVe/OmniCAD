"""Cobertura de cotas del boceto: tipos y combinaciones que no tenían una prueba que resuelva con la cota y mida el
resultado. La matriz de `test_restricciones_matriz.py` cubre distancia (punto–punto, largo de línea, punto–línea),
distancia_h/v entre dos puntos, radio y diámetro de un círculo y ángulo sin cuadrante; acá van las que faltaban:
distancia_h/v sobre una línea, el sentido que guarda la lineal, el ángulo con cuadrante, la distancia entre dos
paralelas y el desfase negativo (que sí se admite, al revés que las cotas de largo)."""
import pytest

from omnicad.restricciones import Boceto, resolver


def test_distancia_h_y_v_sobre_una_linea_resuelven_la_medida():
    for tipo, eje in (("distancia_h", 0), ("distancia_v", 1)):
        b = Boceto()
        linea = b.agregar_linea((0, 0), (6, 8))
        cota = b.agregar_cota(tipo, [linea], "10")
        assert resolver(b, {cota: 10}).ok, tipo
        p1, p2 = b.coords(b.curvas[linea].p1), b.coords(b.curvas[linea].p2)
        assert abs(p2[eje] - p1[eje]) == pytest.approx(10, abs=1e-6), tipo
        assert b.medir(b.cotas[cota]) == pytest.approx(10, abs=1e-6), tipo


def test_distancia_h_conserva_el_sentido_de_la_linea():
    b = Boceto()
    linea = b.agregar_linea((10, 0), (0, 0))          # dibujada al revés: x decrece
    cota = b.agregar_cota("distancia_h", [linea], "6")
    assert b.cotas[cota].datos["signo"] == -1
    assert resolver(b, {cota: 6}).ok
    x1 = b.coords(b.curvas[linea].p1)[0]
    x2 = b.coords(b.curvas[linea].p2)[0]
    assert x2 - x1 == pytest.approx(-6, abs=1e-6)     # no se da vuelta para cumplir la cota
    assert b.medir(b.cotas[cota]) == pytest.approx(6, abs=1e-6)


def test_angulo_con_cuadrante_resuelve_ese_cuadrante():
    b = Boceto()
    l1 = b.agregar_linea((0, 0), (10, 0))
    l2 = b.agregar_linea((0, 0), (-6, 6))             # 45° en el cuadrante 1, 135° en el 0
    cota = b.agregar_cota("angulo", [l1, l2], "120", {"cuadrante": 1})
    assert resolver(b, {cota: 120}).ok
    assert b.medir(b.cotas[cota]) == pytest.approx(120, abs=1e-6)
    assert b.medir_cota("angulo", [l1, l2]) == pytest.approx(60, abs=1e-6)     # el otro cuadrante


def test_distancia_entre_paralelas_con_la_restriccion_paralela():
    b = Boceto()
    l1 = b.agregar_linea((0, 0), (20, 0))
    l2 = b.agregar_linea((3, 9), (30, 9))
    b.agregar_restriccion("paralela", [l1, l2])
    cota = b.agregar_cota("distancia", [l1, l2], "14")
    assert resolver(b, {cota: 14}).ok
    assert b.medir(b.cotas[cota]) == pytest.approx(14, abs=1e-6)
    (ax, ay), (bx, by) = b.coords(b.curvas[l1].p1), b.coords(b.curvas[l1].p2)
    (cx, cy), (dx, dy) = b.coords(b.curvas[l2].p1), b.coords(b.curvas[l2].p2)
    cruz = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx)
    assert cruz == pytest.approx(0, abs=1e-6)         # siguen paralelas


def test_desfase_negativo_pasa_la_copia_al_otro_lado():
    b = Boceto()
    madre = b.agregar_linea((0, 0), (20, 0))
    (copia,), _ = b.desfasar(madre, 3, cadena=False)
    cota, = b.cotas.values()
    assert b.medir(cota) == pytest.approx(3, abs=1e-6)
    assert resolver(b, {cota.id: -4}).ok
    assert b.medir(b.cotas[cota.id]) == pytest.approx(-4, abs=1e-6)
    assert b.coords(b.curvas[copia].p1)[1] == pytest.approx(-4, abs=1e-6)      # la copia quedó del otro lado
