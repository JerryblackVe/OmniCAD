# -*- coding: utf-8 -*-
"""B-842: Cara de desfase sobre cadenas abiertas de paredes de una extrusión."""
import math
import time

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_modificar as sm


def _ok(sesion, herramienta, args):
    respuesta = api.llamar(sesion, herramienta, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _cuerpo_mixto():
    """Spline, arco y dos paredes planas tangentes; una cara mínima corta la cadena antes de cerrarla."""
    sesion = api.Sesion()
    entidades = [
        {"type": "spline", "points": [[10, 0], [10, 10], [-10, 10], [-10, 0]],
         "spline_type": "control_points", "degree": 3},
        {"type": "line", "start": [-10, 0], "end": [-10, -10]},
        {"type": "arc", "center": [0, -10], "start": [-10, -10], "sweep": 180},
        {"type": "line", "start": [10, -10], "end": [10, -0.15]},
        {"type": "line", "start": [10, -0.15], "end": [10.1, 0]},
        {"type": "line", "start": [10.1, 0], "end": [10, 0]},
    ]
    _ok(sesion, "sketch_from_spec", {"plane": "XY", "name": "Perfil", "entities": entidades})
    _ok(sesion, "extrude", {"sketch": "Perfil", "profile": 0, "distance": 3})
    return sesion


def _cadena(sesion):
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    curva = max((c for c in geo.caras(forma) if sm._plano_de_cara(c) is None), key=geo.area)
    return forma, sm.caras_en_cadena(forma, [curva], coplanares=False)


def _cara_curva(sesion):
    caras = _ok(sesion, "find_faces", {"body": "Cuerpo1"})["faces"]
    return max((c for c in caras if c["type"] != "plane"), key=lambda c: c["area"])["id"]


def test_cadena_abierta_mixta_negativa_por_contorno():
    sesion = _cuerpo_mixto()
    forma, caras = _cadena(sesion)
    assert len(caras) == 4                   # spline, cilindro y dos planos; la cara mínima queda afuera
    resultado = sm._desfase_por_contorno(forma, caras, -0.3)
    assert resultado is not None and geo.es_valida(resultado) and len(geo.solidos(resultado)) == 1
    cambio = geo.volumen_exacto(resultado) - geo.volumen_exacto(forma)
    assert cambio == pytest.approx(-0.3 * sum(geo.area(c) for c in caras), rel=0.1)


def test_cadena_abierta_positiva_sobre_un_cuerpo_ya_desfasado():
    sesion = _cuerpo_mixto()
    _ok(sesion, "offset_faces", {"faces": _cara_curva(sesion), "distance": -0.3, "tangent": True})
    forma, caras = _cadena(sesion)
    antes = geo.volumen_exacto(forma)
    _ok(sesion, "offset_faces", {"faces": _cara_curva(sesion), "distance": 0.5, "tangent": True})
    resultado = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(resultado) and len(geo.solidos(resultado)) == 1
    cambio = geo.volumen_exacto(resultado) - antes
    assert cambio == pytest.approx(0.5 * sum(geo.area(c) for c in caras), rel=0.15)


@pytest.mark.parametrize("distancia, cambio", [(0.5, 102.5), (-0.5, -97.5)])
def test_cadena_abierta_de_caras_planas(distancia, cambio):
    caja = geo.caja(10, 10, 10)
    este = max(geo.caras(caja), key=lambda c: geo.centro_masa(c, True)[0])
    norte = max(geo.caras(caja), key=lambda c: geo.centro_masa(c, True)[1])
    resultado = sm._desfase_por_contorno(caja, [este, norte], distancia)
    assert resultado is not None and geo.es_valida(resultado)
    assert geo.volumen_exacto(resultado) - 1000 == pytest.approx(cambio)


def test_si_la_banda_falla_cae_al_camino_normal_sobre_un_cuerpo_ya_desfasado(monkeypatch):
    caja = geo.caja(10, 10, 10)
    este = max(geo.caras(caja), key=lambda c: geo.centro_masa(c, True)[0])
    norte = max(geo.caras(caja), key=lambda c: geo.centro_masa(c, True)[1])
    modificada = sm.desfasar_caras(caja, [este, norte], 0.5)
    este = max(geo.caras(modificada), key=lambda c: geo.centro_masa(c, True)[0])
    norte = max(geo.caras(modificada), key=lambda c: geo.centro_masa(c, True)[1])
    esperado = sm.desfasar_caras(modificada, [este, norte], 0.5)
    monkeypatch.setattr(sm, "_bandas_de_cadena_abierta", lambda *a: None)
    resultado = sm.desfasar_caras(modificada, [este, norte], 0.5)
    assert geo.es_valida(resultado)
    assert geo.volumen_exacto(resultado) == pytest.approx(geo.volumen_exacto(esperado))


def test_previa_de_cadena_abierta_en_proceso_aparte(monkeypatch):
    """La previa aislada entrega un sólido y no deja el diálogo calculando."""
    from omnicad.nucleo import aislado, referencias as refs
    from omnicad.timeline.ops_modificar import OpDesfaseCara

    sesion = _cuerpo_mixto()
    doc = sesion.doc
    cid = next(iter(doc.estado_final.cuerpos))
    forma, caras = _cadena(sesion)
    op = OpDesfaseCara(doc.nuevo_id(), caras=[refs.referencia(cid, caras[0], forma)], distancia="0.5")
    monkeypatch.setattr(doc, "_prevuelo_corresponde", lambda *a: True)     # fuerza el proceso aparte
    llamadas, real = [], doc.calcular_aparte
    def medir(tarea, datos, esperar=None):
        llamadas.append(tarea)
        return real(tarea, datos, esperar)
    monkeypatch.setattr(doc, "calcular_aparte", medir)
    try:
        estado, _avisos = doc.previsualizar(op)
    finally:
        aislado.cerrar_trabajador()
    resultado = estado.cuerpos[cid].forma
    assert llamadas == ["prevuelo_cambio"]
    assert len(doc.operaciones) == 2 and geo.es_valida(resultado)          # la previa no agrega el paso
    cambio = geo.volumen_exacto(resultado) - geo.volumen_exacto(forma)
    assert cambio == pytest.approx(0.5 * sum(geo.area(c) for c in caras), rel=0.15)


def test_agujero_desfasado_hasta_o_mas_que_su_radio_se_tapa_como_fusion():
    """B-856: en un anillo R50/r30, +30 o más tapa el agujero como Fusion; +20 deja un agujero de radio 10."""
    sesion = api.Sesion()
    _ok(sesion, "create_cylinder", {"radius": 50, "height": 30})
    _ok(sesion, "create_cylinder", {"radius": 30, "height": 30, "operation": "cut", "target": "Cuerpo1"})
    agujero = next(c for c in _ok(sesion, "find_faces", {"body": "Cuerpo1"})["faces"] if c.get("radius") == 30.0)["id"]
    for distancia in ("30", "31", "40"):
        _ok(sesion, "offset_faces", {"faces": agujero, "distance": distancia})
        volumen = _ok(sesion, "get_physical_properties", {"bodies": ["Cuerpo1"]})["bodies"][0]["volume"]
        assert volumen == pytest.approx(3.141592653589793 * 50**2 * 30, rel=1e-4)
        _ok(sesion, "undo", {})
    _ok(sesion, "offset_faces", {"faces": agujero, "distance": "20"})
    volumen = _ok(sesion, "get_physical_properties", {"bodies": ["Cuerpo1"]})["bodies"][0]["volume"]
    assert volumen == pytest.approx(3.141592653589793 * (50**2 - 10**2) * 30, rel=1e-4)


def test_anillo_de_boceto_engorda_en_radio_y_no_en_altura():
    """B-844 (video del anillo): el contorno exterior sale a otra altura y al revés; daba un cilindro flaco en el centro."""
    sesion = api.Sesion()
    _ok(sesion, "sketch_from_spec", {"plane": "XY", "name": "Anillo", "entities": [
        {"type": "circle", "center": [0, 0], "radius": 50.721}, {"type": "circle", "center": [0, 0], "radius": 30.9243}]})
    _ok(sesion, "extrude", {"sketch": "Anillo", "profile": 1, "distance": 34.9})      # el perfil 1 es el anillo
    exterior = next(c for c in _ok(sesion, "find_faces", {"body": "Cuerpo1"})["faces"] if c.get("radius") == 50.721)["id"]
    for distancia, radio in (("5", 55.721), ("27.5", 78.221), ("-8.22", 42.501)):
        _ok(sesion, "offset_faces", {"faces": exterior, "distance": distancia})
        cuerpo = _ok(sesion, "get_physical_properties", {})["bodies"][0]
        assert cuerpo["bounding_box"]["size"][2] == pytest.approx(34.9, abs=1e-3), cuerpo
        assert cuerpo["volume"] == pytest.approx(3.141592653589793 * (radio**2 - 30.9243**2) * 34.9, rel=1e-3)
        _ok(sesion, "undo", {})


def _logo_de_11_bsplines():
    """El logo del video de Gerardo (B-842): 11 caras B-spline tangentes en cadena ABIERTA — la recta de cierre quiebra
    ~85° respecto de cada extremo y la cadena tangente queda en las 11 paredes curvas, sin cerrarse."""
    n, radio = 11, 20.0

    def punto(a):
        a = math.radians(a)
        r = radio * (1 + 0.12 * math.cos(2 * a) + 0.05 * math.sin(3 * a))
        return [r * math.cos(a), r * math.sin(a)]

    def tangente(a):
        p0, p1 = punto(a - 0.01), punto(a + 0.01)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        m = math.hypot(dx, dy)
        return [dx / m, dy / m]

    angulos = [i * 350.0 / n for i in range(n + 1)]
    entidades = []
    for i in range(n):
        p0, p3 = punto(angulos[i]), punto(angulos[i + 1])
        paso = math.dist(p0, p3) / 3.0
        t0, t1 = tangente(angulos[i]), tangente(angulos[i + 1])
        entidades.append({"type": "spline", "points": [p0,
                                                      [p0[0] + paso * t0[0], p0[1] + paso * t0[1]],
                                                      [p3[0] - paso * t1[0], p3[1] - paso * t1[1]],
                                                      p3],
                          "spline_type": "control_points", "degree": 3})
    entidades.append({"type": "line", "start": punto(angulos[n]), "end": punto(angulos[0])})
    sesion = api.Sesion()
    _ok(sesion, "sketch_from_spec", {"plane": "XY", "name": "Logo", "entities": entidades})
    _ok(sesion, "extrude", {"sketch": "Logo", "profile": 0, "distance": 3})
    return sesion


def test_b842_el_logo_desfasa_los_4_valores_del_video_igual_y_rapido():
    """B-842 (regresión de velocidad): los 4 valores del video (2,629 / 1,926 / 0,5 / −0,3 mm) desfasan la cadena
    abierta del logo con el volumen de siempre y por el atajo: los topes generosos solo saltan si se degrada (p. ej.
    sin la conversión NURBS del prisma, el −0,3 tarda 7,4 s y falla). B-857: las paredes desfasadas ya no son arcos
    sueltos sino UNA B-spline por curva; el volumen se mide con la integración adaptativa porque el Gauss fijo de
    `volumen_exacto` erra ~1e-4 en caras B-spline de muchos tramos (el propio prisma de arcos medía 187,06 contra
    188,42)."""
    forma, caras = _cadena(_logo_de_11_bsplines())
    assert len(caras) == 11 and all(sm._plano_de_cara(c) is None for c in caras)
    volumenes = ((2.629, 4836.548481), (1.926, 4545.761292), (0.5, 3983.459859), (-0.3, 3684.160712))
    t0 = time.perf_counter()
    for distancia, esperado in volumenes:
        t = time.perf_counter()
        resultado = sm._desfase_por_contorno(forma, caras, distancia)
        assert resultado is not None and geo.es_valida(resultado) and len(geo.solidos(resultado)) == 1
        assert geo.volumen_exacto(resultado, 1e-9) == pytest.approx(esperado, rel=1e-6)
        assert time.perf_counter() - t < 5.0       # generoso: 0,5–0,9 s en máquina quieta, hasta 2,4 s con carga
    assert time.perf_counter() - t0 < 12.0


@pytest.mark.parametrize("distancia, esperado", [(2.629, 4836.548481), (1.926, 4545.761292),
                                                 (0.5, 3983.459859), (-0.3, 3684.160712)])
def test_b857_el_logo_conserva_el_volumen_sin_quedar_trizado(distancia, esperado):
    """B-857: el Desfase de cadena abierta ya no deja el cuerpo trizado (antes las 11 caras B-spline del logo se
    volvían 143–180 por la cadena de arcos de la aproximación; un Desfase siguiente no reconocía la cadena y el
    kernel fallaba a los ~6–12 s). El contorno unido reproduce el de los arcos a 1e-7: el volumen es el mismo."""
    forma, caras = _cadena(_logo_de_11_bsplines())
    resultado = sm._desfase_por_contorno(forma, caras, distancia)
    assert resultado is not None and geo.es_valida(resultado)
    assert geo.volumen_exacto(resultado, 1e-9) == pytest.approx(esperado, rel=1e-6)
    assert len(geo.caras(resultado)) < 100, f"{len(geo.caras(resultado))} caras"


def test_b857_el_segundo_desfase_sobre_el_logo_ya_desfasado_no_cae_al_kernel():
    """B-857 (la otra cara del bug): un Desfase siguiente sobre el cuerpo ya desfasado reconoce la cadena y anda
    por el atajo; antes quedaban 175 caras tangentes, `_desfase_por_contorno` volvía None y el kernel fallaba a los
    ~6 s con «No se pudo desfasar estas caras 0,5 mm». En el cuerpo ya NURBS no se reconvierte el prisma: el volumen
    queda a menos de 1e−4 relativo del camino con conversión y el segundo Desfase tarda menos de 3 s."""
    forma, caras = _cadena(_logo_de_11_bsplines())
    r1 = sm._desfase_por_contorno(forma, caras, -0.3)
    assert r1 is not None and geo.es_valida(r1) and len(geo.caras(r1)) < 100
    curva = max((c for c in geo.caras(r1) if sm._plano_de_cara(c) is None), key=geo.area)
    cadena = sm.caras_en_cadena(r1, [curva], coplanares=False)
    assert 2 <= len(cadena) < 20                    # las 11 paredes, no 175 arcos
    t0 = time.perf_counter()
    r2 = sm.desfasar_caras(r1, cadena, 0.5)
    assert geo.es_valida(r2) and len(geo.solidos(r2)) == 1 and len(geo.caras(r2)) < 100
    assert geo.volumen_exacto(r2, 1e-9) > geo.volumen_exacto(r1, 1e-9)     # +0,5 hacia afuera engorda
    assert geo.volumen_exacto(r2, 1e-9) == pytest.approx(3869.861995, rel=1e-4)
    assert time.perf_counter() - t0 < 3.0           # antes fallaba a los ~12 s; medido 1,65 s
