# -*- coding: utf-8 -*-
"""B-842: Cara de desfase sobre cadenas abiertas de paredes de una extrusión."""
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


def test_agujero_no_se_achica_mas_que_su_radio():
    """Anillo R50/r30: la cara del agujero con +30 o más pasaba el eje y el kernel rellenaba todo sin error."""
    sesion = api.Sesion()
    _ok(sesion, "create_cylinder", {"radius": 50, "height": 30})
    _ok(sesion, "create_cylinder", {"radius": 30, "height": 30, "operation": "cut", "target": "Cuerpo1"})
    agujero = next(c for c in _ok(sesion, "find_faces", {"body": "Cuerpo1"})["faces"] if c.get("radius") == 30.0)["id"]
    for distancia in ("30", "31", "40"):
        respuesta = api.llamar(sesion, "offset_faces", {"faces": agujero, "distance": distancia})
        assert not respuesta["ok"] and "eje" in respuesta["mensaje"], respuesta
    _ok(sesion, "offset_faces", {"faces": agujero, "distance": "20"})
    volumen = _ok(sesion, "get_physical_properties", {"bodies": ["Cuerpo1"]})["bodies"][0]["volume"]
    assert volumen == pytest.approx(3.141592653589793 * (50**2 - 10**2) * 30, rel=1e-4)
