"""BOC-31: inferencias persistentes en línea de punto medio, rectángulo 3p y círculo."""
import math

import pytest

from test_boceto_fase5_ui import _clic, _mover, _objetivo
from test_boceto_fase5_ui import lienzo as lienzo

from omnicad.restricciones import Boceto, ErrorBoceto


@pytest.mark.parametrize("fin,tipo,extremos", [
    ((40, 20.1), "horizontal", ((-20, 20), (40, 20))),
    ((10.1, 50), "vertical", ((10, -10), (10, 50))),
])
def test_boc31_linea_medio_horizontal_vertical(lienzo, fin, tipo, extremos):
    lz = lienzo
    lz.set_herramienta("linea_medio")
    _clic(lz, 10, 20)
    _clic(lz, *fin)
    (linea,) = lz.b.curvas.values()
    assert any(r.tipo == tipo and r.entidades == [linea.id] for r in lz.b.restricciones.values())
    a, b = lz.b._extremos_linea(linea.id)
    assert a == pytest.approx(extremos[0], abs=1e-8)
    assert b == pytest.approx(extremos[1], abs=1e-8)
    assert tuple((x + y) / 2 for x, y in zip(a, b, strict=True)) == pytest.approx((10, 20), abs=1e-8)
    assert lz.resultado.ok


def test_boc31_linea_medio_tangente(lienzo):
    lz = lienzo
    objetivo = _objetivo(lz, circulo=True)
    lz.set_herramienta("linea_medio")
    _clic(lz, 40, 20)
    contacto = (25, 20 + math.sqrt(75))
    _clic(lz, contacto[0] + 0.2, contacto[1] + 0.1)
    linea = lz.b.curvas[max(lz.b.curvas)]
    assert any(r.tipo == "tangente" and r.entidades == [linea.id, objetivo]
               for r in lz.b.restricciones.values())
    a, b = lz.b._extremos_linea(linea.id)
    assert b == pytest.approx(contacto, abs=1e-8)
    assert a == pytest.approx((55, 20 - math.sqrt(75)), abs=1e-8)
    assert abs(sum((b[i] - (20, 20)[i]) * (b[i] - a[i]) for i in range(2))) < 1e-6
    assert lz.resultado.ok


@pytest.mark.parametrize("herramienta", ["linea_medio", "rectangulo_3p"])
def test_boc31_lado_perpendicular_con_extremo_sobre_la_linea(lienzo, herramienta):
    lz = lienzo
    objetivo = _objetivo(lz)
    lz.set_herramienta(herramienta)
    _clic(lz, 23, 45)
    _clic(lz, 23.2, 20.2)
    if herramienta == "rectangulo_3p":
        _clic(lz, 45, 25)
    linea = next(c for c in lz.b.curvas.values() if c.id != objetivo)
    assert any(r.tipo == "perpendicular" and r.entidades == [linea.id, objetivo]
               for r in lz.b.restricciones.values())
    assert any(r.tipo == "coincidente" and r.entidades == [linea.p2, objetivo]
               for r in lz.b.restricciones.values())
    assert lz.b.coords(linea.p2) == pytest.approx((23, 20), abs=1e-8)
    assert lz.b.coords(linea.p1) == pytest.approx((23, 70) if herramienta == "linea_medio" else (23, 45), abs=1e-8)
    assert lz.resultado.ok


def test_boc31_rectangulo_3p_tangente(lienzo):
    lz = lienzo
    objetivo = _objetivo(lz, circulo=True)
    lz.set_herramienta("rectangulo_3p")
    _clic(lz, 40, 20)
    contacto = (25, 20 + math.sqrt(75))
    _clic(lz, contacto[0] + 0.2, contacto[1] + 0.1)
    _clic(lz, 40, 50)
    linea = next(c for c in lz.b.curvas.values() if c.id != objetivo)
    assert any(r.tipo == "tangente" and r.entidades == [linea.id, objetivo]
               for r in lz.b.restricciones.values())
    assert lz.b.coords(linea.p1) == pytest.approx((40, 20), abs=1e-8)
    assert lz.b.coords(linea.p2) == pytest.approx(contacto, abs=1e-8)
    assert lz.resultado.ok


def test_boc31_rectangulo_3p_conserva_inferencia_del_segundo_clic(lienzo):
    lz = lienzo
    lz.set_herramienta("rectangulo_3p")
    _clic(lz, 10, 20)
    _clic(lz, 40, 20.1)
    _mover(lz, 40.1, 50)
    assert lz.inf_actual.tipo == "vertical"
    _clic(lz, 40.1, 50)
    lados = list(lz.b.curvas.values())
    assert len(lados) == 4
    assert any(r.tipo == "horizontal" and r.entidades == [lados[0].id]
               for r in lz.b.restricciones.values())
    esquinas = [(10, 20), (40, 20), (40, 50), (10, 50)]
    for i, lado in enumerate(lados):
        a, b = lz.b._extremos_linea(lado.id)
        assert a == pytest.approx(esquinas[i], abs=1e-8)
        assert b == pytest.approx(esquinas[(i + 1) % 4], abs=1e-8)
    assert lz.resultado.ok


def test_boc31_circulo_tangente_al_pie_perpendicular(lienzo):
    lz = lienzo
    objetivo = _objetivo(lz)
    lz.set_herramienta("circulo")
    _clic(lz, 23, 45)
    _mover(lz, 23.2, 20.2)
    assert lz.inf_actual.tipo == "perpendicular"
    _clic(lz, 23.2, 20.2)
    circulo = lz.b.curvas[max(lz.b.curvas)]
    assert any(r.tipo == "tangente" and r.entidades == [circulo.id, objetivo]
               for r in lz.b.restricciones.values())
    assert not any(r.tipo == "coincidente" for r in lz.b.restricciones.values())
    assert len(lz.b.puntos) == 3
    centro = lz.b.coords(circulo.centro)
    assert centro == pytest.approx((23, 45), abs=1e-8)
    assert lz.b.radio(circulo.id) == pytest.approx(abs(centro[1] - 20), abs=1e-8)
    assert lz.b.radio(circulo.id) == pytest.approx(25, abs=1e-8)
    assert lz.resultado.ok


@pytest.mark.parametrize("herramienta,clave,texto", [
    ("linea_medio", "largo", "60"),
    ("rectangulo_3p", "ancho", "30"),
    ("circulo", "diametro", "50"),
])
def test_boc31_inferencia_conserva_las_cotas_escritas(lienzo, herramienta, clave, texto):
    lz = lienzo
    objetivo = _objetivo(lz) if herramienta == "circulo" else None
    lz.set_herramienta(herramienta)
    _clic(lz, *((23, 45) if objetivo is not None else (10, 20)))
    lz._bloquear(clave, texto, float(texto))
    _clic(lz, *((23.2, 20.2) if objetivo is not None else (40, 20.1)))
    if herramienta == "rectangulo_3p":
        _clic(lz, 40, 50)
    (cota,) = lz.b.cotas.values()
    assert cota.expresion == texto
    assert lz.b.medir(cota) == pytest.approx(float(texto), abs=1e-8)
    tipo = "tangente" if objetivo is not None else "horizontal"
    assert any(r.tipo == tipo for r in lz.b.restricciones.values())
    assert lz.resultado.ok and len(lz.historial) == 1


@pytest.mark.parametrize("herramienta", ["linea_medio", "rectangulo_3p"])
def test_boc31_hv_solo_si_la_inferencia_sigue_habilitada(lienzo, herramienta):
    lz = lienzo
    lz.set_herramienta(herramienta)
    _clic(lz, 10, 20)
    _mover(lz, 40, 20.1)
    assert lz.inf_actual.tipo == "horizontal"
    lz.inferencia = None
    lz._registrar_clic(None, lz.cursor)
    if herramienta == "rectangulo_3p":
        _clic(lz, 40, 50)
    assert not any(r.tipo in ("horizontal", "vertical") for r in lz.b.restricciones.values())
    assert lz.resultado.ok


@pytest.mark.parametrize("rechazo", ["validacion", "solver"])
@pytest.mark.parametrize("herramienta", ["linea_medio", "rectangulo_3p", "circulo"])
def test_boc31_inferencia_rechazada_conserva_geometria_y_un_deshacer(lienzo, monkeypatch, rechazo, herramienta):
    lz = lienzo
    objetivo = _objetivo(lz) if herramienta == "circulo" else None
    lz.set_herramienta(herramienta)
    antes = lz.b.a_dict()
    agregar = lz.b.agregar_restriccion
    intentos = []
    inferida = "tangente" if objetivo is not None else "horizontal"

    def rechazar(tipo, entidades, datos=None):
        if tipo == inferida:
            intentos.append(tipo)
            if rechazo == "validacion":
                raise ErrorBoceto("Conflicto simulado de inferencia")
            agregar("fijo", entidades[:1])
            if objetivo is not None:
                return agregar("coincidente", [lz.b.curvas[entidades[0]].centro, lz.b.curvas[objetivo].p1])
            return agregar("vertical", entidades)
        return agregar(tipo, entidades, datos)

    monkeypatch.setattr(lz.b, "agregar_restriccion", rechazar)
    _clic(lz, *((23, 45) if objetivo is not None else (10, 20)))
    _clic(lz, *((23.2, 20.2) if objetivo is not None else (40, 20.1)))
    if herramienta == "rectangulo_3p":
        _clic(lz, 40, 50)
    assert intentos == [inferida]
    assert len(lz.historial) == 1
    assert not any(r.tipo == inferida for r in lz.b.restricciones.values())
    nuevas = [c for c in lz.b.curvas.values() if c.id != objetivo]
    assert len(nuevas) == (4 if herramienta == "rectangulo_3p" else 1)
    if herramienta == "circulo":
        assert lz.b.radio(nuevas[0].id) == pytest.approx(25, abs=1e-8)
        assert lz.b.coords(nuevas[0].centro) == pytest.approx((23, 45), abs=1e-8)
    else:
        a, b = lz.b._extremos_linea(nuevas[0].id)
        assert a == pytest.approx((-20, 20) if herramienta == "linea_medio" else (10, 20), abs=1e-8)
        assert b == pytest.approx((40, 20), abs=1e-8)
    assert lz.resultado.ok
    lz.deshacer()
    assert lz.b.a_dict() == antes


def test_boc31_rectangulo_esquina_no_agrega_inferencias_hv(lienzo):
    lz = lienzo
    lz.set_herramienta("rectangulo")
    _clic(lz, 10, 20)
    _clic(lz, 40, 20.1)
    assert not lz.b.curvas and not lz.historial  # el ajuste deja alto cero, como antes de BOC-31
    _clic(lz, 10, 20)
    _clic(lz, 40, 30)
    esperado = Boceto()
    esperado.agregar_rectangulo((10, 20), (40, 30))
    assert lz.b.a_dict() == esperado.a_dict()
    assert lz.resultado.ok
