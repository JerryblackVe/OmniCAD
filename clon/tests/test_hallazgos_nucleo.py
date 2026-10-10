# -*- coding: utf-8 -*-
"""Hallazgos de las pruebas de uso (PROJECT_LOG «Hallazgos de pruebas de uso») que quedaban después de la ola 1:
resultados imposibles que pasaban como «ok», mensajes que culpaban a lo que no era y casos borde del núcleo."""
import json
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm
from omnicad.nucleo import superficies as sf


def _tapa(forma):
    return max(geo.caras(forma), key=lambda c: geo.centro_masa(c, True)[2])


def _abajo(forma):
    return min(geo.caras(forma), key=lambda c: geo.centro_masa(c, True)[2])


def _prisma(eje_cortes):
    """El auto de la Prueba 9: prisma de 456 × 176 × 155,8 (base en z = 38) con cuatro pasos de rueda de radio 48
    entre z = 40 y 76. Con `eje_cortes` = Y los cilindros cruzan la cara de abajo; con Z quedan a 2 mm de ella."""
    forma = geo.caja(456, 176, 155.8, (0, -88, 38))
    for x in (82.1, 367.1):
        for y0 in (-90, 54):
            forma = geo.booleano(forma, geo.cilindro(48, 36, (x, y0, 40), eje_cortes), "cortar")
    return forma


# ---------------------------------------------------------------- vaciado: resultados imposibles
def test_vaciado_que_da_un_solido_al_reves_falla():
    """El prisma con cortes a 2 mm de la cara quitada, vaciado 1 o 1,9 mm: el kernel daba IsDone y un sólido con
    volumen NEGATIVO (−445.548 y −200.982 mm³, el más grueso con menos material) y el paso quedaba en «ok»."""
    forma = _prisma((0, 0, 1))
    for espesor in (1, 1.9):
        with pytest.raises(geo.ErrorGeometria, match="El vaciado falló: el kernel no pudo hacerlo con") as e:
            sm.vaciado(forma, [_abajo(forma)], espesor_interior=espesor)
        assert "vaciar antes de cortar" in str(e.value)


@pytest.mark.parametrize("espesor", [12, 15, 20, 25, 30, 100])
def test_vaciado_mas_grueso_que_la_pieza_falla_y_lo_dice(espesor):
    """Caja de 40 × 40 × 10 sin la tapa: con 25 o 30 mm salía un «vaciado» MÁS ALTO que la caja (z hasta 25) y con
    más volumen (18.227 mm³ contra 16.000); con 20 o 100 el mensaje culpaba a «cortes que cruzan la cara»."""
    caja = geo.caja(40, 40, 10)
    with pytest.raises(geo.ErrorGeometria, match=rf"El vaciado falló: el espesor \({espesor} mm\) es demasiado "
                                                 r"grande para la pieza \(su medida más chica es 10 mm\)"):
        sm.vaciado(caja, [_tapa(caja)], espesor_interior=espesor)


def test_vaciado_en_ambos_sentidos_con_un_lado_imposible_falla():
    """«Ambos» con 25 mm unía la parte de adentro rota con la de afuera: 1.500 mm³ y «ok»."""
    caja = geo.caja(40, 40, 10)
    with pytest.raises(geo.ErrorGeometria, match="demasiado grande para la pieza"):
        sm.vaciado(caja, [_tapa(caja)], espesor_interior=25, espesor_exterior=25, direccion="ambos")


@pytest.mark.parametrize("espesor", [5, 6, 25])
def test_hueco_cerrado_mas_grueso_que_la_mitad_falla_y_lo_dice(espesor):
    """Sin caras quitadas (hueco cerrado) en una caja de 10 mm de alto: 25 mm devolvía la caja intacta («ok», sin
    hueco); 5 mm, «el resultado no es un sólido válido»; 6 mm, «La operación 'cortar' falló en el kernel»."""
    caja = geo.caja(40, 40, 10)
    with pytest.raises(geo.ErrorGeometria, match=rf"el espesor \({espesor} mm\) es demasiado grande para un hueco "
                                                 r"cerrado: tiene que ser menor que la mitad"):
        sm.vaciado(caja, [], espesor_interior=espesor)


@pytest.mark.parametrize("caras, direccion, espesor, volumen", [
    ("tapa", "interior", 5, 16000 - 30 * 30 * 5),
    ("tapa", "interior", 6, 16000 - 28 * 28 * 4),
    ("tapa", "interior", 9.9, 16000 - 20.2 * 20.2 * 0.1),
    ("tapa", "exterior", 5, 50 * 50 * 15 - 16000),
    ("tapa", "ambos", 2, 44 * 44 * 12 - 36 * 36 * 8),
    ("ninguna", "interior", 2, 16000 - 36 * 36 * 6),
    ("ninguna", "interior", 4.9, 16000 - 30.2 * 30.2 * 0.2),
    ("ninguna", "exterior", 5, 50 * 50 * 20 - 16000),
])
def test_vaciados_legitimos_siguen_andando(caras, direccion, espesor, volumen):
    caja = geo.caja(40, 40, 10)
    quitar = [_tapa(caja)] if caras == "tapa" else []
    r = sm.vaciado(caja, quitar, espesor_interior=espesor, espesor_exterior=espesor, direccion=direccion)
    assert geo.es_valida(r) and geo.volumen(r) == pytest.approx(volumen, rel=1e-6)


def test_vaciado_que_no_quita_la_cara_no_culpa_al_espesor():
    """Con los pasos de rueda cruzando la cara de abajo, 5 mm (chico para la pieza) sigue diciendo la causa real."""
    forma = _prisma((0, 1, 0))
    abajo = min((c for c in geo.caras(forma) if (p := geo.plano_de_cara(c)) is not None and p.normal[2] < -0.99),
                key=lambda c: geo.centro_masa(c, True)[2])
    with pytest.raises(geo.ErrorGeometria) as e:
        sm.vaciado(forma, [abajo], espesor_interior=5)
    assert "demasiado grande" not in str(e.value) and "vaciar antes de cortar" in str(e.value)


# ---------------------------------------------------------------- desfase de caras que atraviesa el cuerpo
@pytest.mark.parametrize("distancia", [-10, -15, -40])
def test_desfase_de_cara_que_atraviesa_el_cuerpo_lo_dice(distancia):
    """La tapa de una caja de 10 mm de alto desfasada −10 o más decía «Reemplazar cara: el kernel devolvió una forma
    vacía» (otro comando y sin la causa)."""
    caja = geo.caja(40, 40, 10)
    with pytest.raises(geo.ErrorGeometria) as e:
        sm.desfasar_caras(caja, [_tapa(caja)], distancia)
    texto = str(e.value)
    assert texto.startswith("Desfase de caras:") and "no queda material" in texto and "Reemplazar" not in texto


@pytest.mark.parametrize("distancia, alto", [(-5, 5), (-9.99, 0.01), (5, 15)])
def test_desfase_de_cara_legitimo_sigue_andando(distancia, alto):
    caja = geo.caja(40, 40, 10)
    r = sm.desfasar_caras(caja, [_tapa(caja)], distancia)
    assert geo.es_valida(r) and geo.volumen(r) == pytest.approx(1600 * alto, rel=1e-6)


def _curva(forma):
    return next(c for c in geo.caras(forma) if geo.plano_de_cara(c) is None)


def _cilindro_y_lateral():
    """Cilindro de radio 10 y alto 20, y su cara lateral."""
    cil = geo.cilindro(10, 20)
    return cil, _curva(cil)


def _lateral():
    return _cilindro_y_lateral()[1]


def _placa_agujereada():
    """Placa de 40 × 40 × 10 con un agujero pasante de radio 5 en el centro, y la cara del agujero."""
    placa = geo.booleano(geo.caja(40, 40, 10, (-20, -20, 0)), geo.cilindro(5, 10), "cortar")
    return placa, _curva(placa)


@pytest.mark.parametrize("caso, distancia", [("cilindro", -12), ("cilindro", -25), ("agujero", 14.9),
                                              ("agujero", 20)])
def test_desfase_de_cara_curva_que_se_da_vuelta_falla(caso, distancia):
    """Una cara curva desfasada más que su radio se daba vuelta por el eje y salía «ok»: el cilindro de radio 10
    achicado 25 mm quedaba de radio 15 (MÁS GRANDE); el agujero de radio 5 «llenado» 14,9 mm quedaba de radio 9,9."""
    forma, cara = _cilindro_y_lateral() if caso == "cilindro" else _placa_agujereada()
    with pytest.raises(geo.ErrorGeometria, match="la cara se da vuelta"):
        sm.desfasar_caras(forma, [cara], distancia)


@pytest.mark.parametrize("caso, distancia, volumen", [
    ("cilindro", -5, math.pi * 25 * 20), ("cilindro", 5, math.pi * 225 * 20),
    ("agujero", -2, 16000 - math.pi * 49 * 10), ("agujero", 2, 16000 - math.pi * 9 * 10),
    ("agujero", 4.99, 16000 - math.pi * 0.01 ** 2 * 10),
])
def test_desfase_de_cara_curva_legitimo_sigue_andando(caso, distancia, volumen):
    forma, cara = _cilindro_y_lateral() if caso == "cilindro" else _placa_agujereada()
    r = sm.desfasar_caras(forma, [cara], distancia)
    assert geo.es_valida(r) and geo.volumen(r) == pytest.approx(volumen, rel=1e-6)


# ---------------------------------------------------------------- engrosar y desfasar superficie
@pytest.mark.parametrize("espesor", [-10, -12, -25])
@pytest.mark.parametrize("tipo", ["agudo", "redondeado"])
def test_engrosar_mas_que_el_radio_de_curvatura_falla(espesor, tipo):
    """La cara lateral de un cilindro de radio 10 engrosada hacia adentro: con −10 salía «ok» con un sólido inválido,
    con −12 un tubo de radio 2 a 10 (dado vuelta por el eje: 6.032 mm³) y con −25 un volumen NEGATIVO (−7.854)."""
    with pytest.raises(geo.ErrorGeometria, match="engrosar|engrosado"):
        sf.engrosar_superficie(_lateral(), espesor, tipo=tipo)


@pytest.mark.parametrize("espesor, volumen", [
    (2, math.pi * (144 - 100) * 20),
    (-5, math.pi * (100 - 25) * 20),
    (-9.99, math.pi * (100 - 0.01 ** 2) * 20),
    (25, math.pi * (35 ** 2 - 100) * 20),
])
def test_engrosar_legitimo_sigue_andando(espesor, volumen):
    for tipo in ("agudo", "redondeado"):
        r = sf.engrosar_superficie(_lateral(), espesor, tipo=tipo)
        assert geo.es_valida(r) and geo.volumen(r) == pytest.approx(volumen, rel=1e-6)


def test_engrosar_simetrico_y_de_varias_caras_sigue_andando():
    r = sf.engrosar_superficie(_lateral(), 4, simetrica=True)
    assert geo.es_valida(r) and geo.volumen(r) == pytest.approx(math.pi * (144 - 64) * 20, rel=1e-6)
    caja = geo.caja(40, 40, 10)
    abiertas = geo.compuesto([c for c in geo.caras(caja) if geo.centro_masa(c, True)[2] < 9.99])   # caja sin tapa
    r = sf.engrosar_superficie(abiertas, -2)
    assert geo.es_valida(r) and geo.volumen(r) == pytest.approx(16000 - 36 * 36 * 8, rel=1e-6)


@pytest.mark.parametrize("distancia", [-10, -12])
def test_desfasar_superficie_mas_que_el_radio_falla(distancia):
    """−10 dejaba una «superficie» de área 0 sobre el eje y −12 un cilindro de radio 2 (a 8 mm, no a 12)."""
    with pytest.raises(geo.ErrorGeometria, match="radio de curvatura"):
        sf.desfasar_superficie(_lateral(), distancia)


@pytest.mark.parametrize("distancia, radio", [(-5, 5), (-9.99, 0.01), (5, 15)])
def test_desfasar_superficie_legitimo_sigue_andando(distancia, radio):
    r = sf.desfasar_superficie(_lateral(), distancia)
    assert geo.area(r) == pytest.approx(2 * math.pi * radio * 20, rel=1e-6)


@pytest.mark.parametrize("distancia, medidas", [(-2, (36, 36, 6)), (3, (46, 46, 16))])
def test_desfasar_superficie_de_un_cuerpo_solido(distancia, medidas):
    """Desfase de un cuerpo entero (la operación acepta cuerpos): hacia adentro las caras quedan DENTRO del sólido y
    tienen que medirse contra su superficie, no contra el sólido (ahí la distancia es 0)."""
    r = sf.desfasar_superficie(geo.caja(40, 40, 10), distancia)
    a, b, c = medidas
    assert geo.area(r) == pytest.approx(2 * (a * b + a * c + b * c), rel=1e-6)


@pytest.mark.parametrize("distancia", [-5, -6, -20])
def test_desfasar_un_cuerpo_mas_que_su_mitad_falla_sin_tirar_la_app(distancia):
    """Una caja de 10 mm de alto desfasada 6 mm hacia adentro: el kernel daba IsDone y una forma NULA, y
    `_tipado` le pedía el tipo: fallo de segmentación (se caía la app entera). Con 20 mm daba una forma «al revés»."""
    with pytest.raises(geo.ErrorGeometria, match="se cruza consigo misma"):
        sf.desfasar_superficie(geo.caja(40, 40, 10), distancia)


def test_sup_desfase_de_un_cuerpo_por_la_api_falla_limpio():
    s = api.Sesion()
    cid = api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 10})["result"]["bodies_created"][0]["id"]
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, "run_operation", {"type": "sup_desfase", "params": {
        "caras": [{"tipo": "cuerpo", "cuerpo": cid}], "distancia": "-6 mm"}})
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED" and "se cruza consigo misma" in r["mensaje"], r
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes
    r = api.llamar(s, "run_operation", {"type": "sup_desfase", "params": {
        "caras": [{"tipo": "cuerpo", "cuerpo": cid}], "distancia": "-2 mm"}})
    assert r["ok"], r
    nuevo = s.doc.estado_final.cuerpos[r["result"]["new_bodies"][0]].forma
    assert geo.area(nuevo) == pytest.approx(2 * (36 * 36 + 2 * 36 * 6), rel=1e-6)


def test_shell_por_la_api_con_resultado_imposible_no_cambia_el_documento():
    s = api.Sesion()
    cid = api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 10})["result"]["bodies_created"][0]["id"]
    antes = json.dumps(s.doc.a_dict(), sort_keys=True)
    r = api.llamar(s, "shell", {"body": cid, "faces": ">Z", "thickness": 25})
    assert not r["ok"] and r["error_kind"] == "OPERATION_FAILED", r
    assert "es demasiado grande para la pieza" in r["mensaje"]
    assert json.dumps(s.doc.a_dict(), sort_keys=True) == antes
