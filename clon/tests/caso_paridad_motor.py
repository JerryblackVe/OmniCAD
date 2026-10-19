# -*- coding: utf-8 -*-
"""Una operación en un proceso con exactamente un kernel; invocado por pytest.

Los casos llaman a las funciones públicas de `nucleo/` (las mismas para los dos motores): así la prueba
verifica la conexión de cada función, no solo el kernel.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import numpy as np

import omnicad  # noqa: F401 — activa el bloqueo antes de cargar geometría
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import consultas
from omnicad.nucleo import engranajes
from omnicad.nucleo import intercambio
from omnicad.nucleo import perfiles
from omnicad.nucleo import referencias as refs
from omnicad.nucleo import revision
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import solidos_modificar as sm


def _rectangulo(u0=0.0, v0=0.0, ancho=10.0, alto=20.0):
    p = [(u0, v0), (u0 + ancho, v0), (u0 + ancho, v0 + alto), (u0, v0 + alto)]
    return [("linea", i + 1, p[i], p[(i + 1) % 4]) for i in range(4)]


def _perfil(geometria, plano="XY", cantidad=1):
    """La región más grande (con `cantidad` regiones esperadas: un marco con agujero da el marco y el hueco)."""
    regiones = perfiles.detectar(geometria, geo.Plano(plano))
    assert len(regiones) == cantidad, len(regiones)
    return max(regiones, key=lambda p: p.area).cara


def _sub(forma, tipo, punto):
    """La arista (por su punto medio) o la cara (por su centro) más cercana a `punto`."""
    clave = "medio" if tipo == "arista" else "centro"
    return min(refs.subformas(forma, tipo),
               key=lambda s: np.linalg.norm(np.asarray(refs.firma(s)[clave]) - punto))


def _caja():
    return geo.caja(10, 20, 30)


def _l():
    """Prisma en L: unión de dos cajas (las caras de atrás quedan coplanares)."""
    return geo.booleano(geo.caja(30, 10, 10), geo.caja(10, 10, 30), "unir")


CASOS = {
    "caja": _caja,
    "cilindro": lambda: geo.cilindro(10, 20),
    "esfera": lambda: geo.esfera(10),
    "toroide": lambda: geo.toroide(20, 5),
    "trasladar": lambda: geo.trasladar(_caja(), (5, 7, 11)),
    "rotar": lambda: geo.rotar(_caja(), (1, 2, 3), (1, 1, 0), 30),
    "unir": lambda: geo.booleano(_caja(), geo.caja(10, 20, 30, (5, 0, 0)), "unir"),
    "cortar": lambda: geo.booleano(_caja(), geo.caja(10, 20, 30, (5, 0, 0)), "cortar"),
    "intersecar": lambda: geo.booleano(_caja(), geo.caja(10, 20, 30, (5, 0, 0)), "intersecar"),
    "unir_l": _l,
    "cortar_cilindro": lambda: geo.booleano(geo.caja(30, 30, 10), geo.cilindro(5, 10, (15, 15, 0)), "cortar"),
    "agujero_pasante": lambda: geo.booleano(geo.caja(30, 30, 10), geo.cilindro(5, 20, (15, 15, -5)), "cortar"),
    "unir_cilindro": lambda: geo.booleano(geo.caja(30, 30, 10), geo.cilindro(5, 20, (15, 15, 0)), "unir"),
    "intersecar_cilindro": lambda: geo.booleano(geo.caja(30, 30, 10), geo.cilindro(20, 20, (0, 0, -5)), "intersecar"),
    "extruir_rectangulo": lambda: geo.extruir([_perfil(_rectangulo())], (0, 0, 1), 30),
    "extruir_simetrica": lambda: geo.extruir([_perfil(_rectangulo(5, 5))], (0, 0, 1), 30, simetrica=True),
    "extruir_xz": lambda: geo.extruir([_perfil(_rectangulo(), "XZ")], (0, -1, 0), 15),
    "extruir_sobre_cara": lambda: _sobre_cara(),
    "extruir_circulo": lambda: geo.extruir([_perfil([("circulo", 1, (0.0, 0.0), 10.0)])], (0, 0, 1), 30),
    "revolver_rectangulo": lambda: geo.revolver([_perfil(_rectangulo(10, 0, 10, 30), "XZ")], (0, 0, 0),
                                                (0, 0, 1), 360),
    "empalme": lambda: sm.empalme(_caja_fija(), [{"aristas": [_sub(_caja_fija(), "arista", (5, 0, 0))],
                                             "tipo": "constante", "radio": 3}]),
    "empalme_esquina": lambda: _empalme_esquina(),
    "chaflan": lambda: sm.chaflan(_caja_fija(), [{"aristas": [_sub(_caja_fija(), "arista", (5, 0, 0))],
                                                  "tipo": "distancia_igual", "distancia": 2}]),
    "vaciado": lambda: sm.vaciado(_caja_fija(), [_sub(_caja_fija(), "cara", (5, 10, 30))], espesor_interior=2),
    "desfasar_caras": lambda: sm.desfasar_caras(_caja_fija(), [_sub(_caja_fija(), "cara", (5, 10, 30))], 4),
    "desmoldeo": lambda: sm.desmoldeo(_caja_fija(), [_sub(_caja_fija(), "cara", (10, 10, 15))], (0, 0, 1), 5,
                                      geo.Plano("XY")),
    "quitar_caras": lambda: _quitar_chaflan(),
    "empalme_cilindro": lambda: _empalme_cilindro(),
    "cara_l": lambda: _sub(_l(), "cara", (5, 10, 5)),            # cara de abajo en L: sus 6 aristas, no las 18
    "perfil_rectangulo": lambda: _perfil(_rectangulo(2, 3, 10, 20)),
    "perfil_elipse_vertical": lambda: _perfil([("elipse", 1, (3.0, 4.0), 5.0, 10.0, 0.3)]),
    "perfil_con_curva_rota": lambda: _perfil(_rectangulo() + [("spline", 9, [(1.0, 1.0)] * 3, [0, 0, 0, 1, 1, 1], 2,
                                                                None)]),
    "chaflan_esquina": lambda: sm.chaflan(_caja_fija(), [{"aristas": [_sub(_caja_fija(), "arista", p) for p in
                                                                      ((5, 0, 30), (10, 10, 30), (10, 0, 15))],
                                                          "tipo": "distancia_igual", "distancia": 2}]),
    "vaciado_dos_caras": lambda: sm.vaciado(_caja_fija(), [_sub(_caja_fija(), "cara", p) for p in
                                                           ((5, 10, 30), (5, 0, 15))], espesor_interior=1.5),
    "empalme_dos": lambda: sm.empalme(_caja_fija(), [{"aristas": [_sub(_caja_fija(), "arista", p) for p in
                                                                  ((5, 0, 0), (5, 20, 30))],
                                                      "tipo": "constante", "radio": 2.5}]),
    "extruir_con_agujero": lambda: geo.extruir([_perfil(_rectangulo(0, 0, 40, 40) + [
        (t, i + 10, a, b) for t, i, a, b in _rectangulo(10, 10, 10, 10)], cantidad=2)], (0, 0, 1), 5),
    "extruir_dos": lambda: geo.extruir([p.cara for p in perfiles.detectar(
        _rectangulo() + [(t, i + 10, a, b) for t, i, a, b in _rectangulo(20, 0)], geo.Plano("XY"))], (0, 0, 1), 7),
    "revolver_arco": lambda: geo.revolver([_perfil([("linea", 1, (0.0, 0.0), (10.0, 0.0)),
                                                   ("arco", 2, (0.0, 0.0), 10.0, 0.0, np.pi / 2),
                                                   ("linea", 3, (0.0, 10.0), (0.0, 0.0))], "XZ")],
                                          (0, 0, 0), (0, 0, 1), 360),
    "vaciado_cilindro": lambda: _en_cilindro(lambda c: sm.vaciado(c, [_sub(c, "cara", (0, 0, 20))], espesor_interior=2)),
    "desfasar_cilindro": lambda: _en_cilindro(lambda c: sm.desfasar_caras(c, [_sub(c, "cara", (0, 0, 20))], 4)),
    "desfasar_lateral": lambda: _en_cilindro(lambda c: sm.desfasar_caras(c, [_sub(c, "cara", (0, 0, 10))], 2)),
    "desmoldeo_cilindro": lambda: _en_cilindro(lambda c: sm.desmoldeo(c, [_sub(c, "cara", (0, 0, 10))], (0, 0, 1), 5,
                                                                     geo.Plano("XY"))),
    "chaflan_cilindro": lambda: _en_cilindro(lambda c: sm.chaflan(c, [{"aristas": [_sub(c, "arista", (0, 0, 25))],
                                                                       "tipo": "distancia_igual", "distancia": 2}])),
    "revolver_negativo": lambda: geo.revolver([_perfil(_rectangulo(10, 0, 10, 30), "XZ")], (0, 0, 0), (0, 0, 1), -90),
    "cremallera": lambda: engranajes.cremallera(2.5, 63, ancho=20, alto=20),
    "simetria": lambda: sc.simetria(geo.trasladar(_l(), (5, 0, 0)), geo.Plano("YZ")),
    "patron_rectangular": lambda: _patron(sc.transformaciones_rectangulares((1, 0, 0), 3, 60, (0, 1, 0), 2, 25)),
    "patron_circular": lambda: _patron(sc.transformaciones_circulares((0, 0, 0), (0, 0, 1), 6)),
    "patron_puntos": lambda: _patron(sc.transformaciones_en_puntos([(40, 0, 0), (0, 40, 5)])),
    "multitransformacion": lambda: _patron(sc.componer_transformaciones([
        sc.transformaciones_rectangulares((0, 1, 0), 2, 30),
        [consultas.transformacion_identidad(), sc.transformacion_simetria(geo.Plano("YZ"))]])),
    "agujero_punta": lambda: sc.herramienta_agujero((5, 5, 10), (0, 0, -1), diametro=8, profundidad=20),
    "agujero_plano": lambda: sc.herramienta_agujero((5, 5, 10), (0, 0, -1), diametro=8, profundidad=20, punta="plana"),
    "agujero_abocardado": lambda: sc.herramienta_agujero((5, 5, 10), (0, 0, -1), tipo="abocardado", diametro=6,
                                                         profundidad=15, diam_abocardado=10, prof_abocardado=4),
    "agujero_avellanado": lambda: sc.herramienta_agujero((5, 5, 10), (0, 0, -1), tipo="avellanado", diametro=6,
                                                         profundidad=15, diam_avellanado=12),
    "agujero_en_caja": lambda: geo.booleano(geo.caja(30, 30, 10), sc.herramienta_agujero(
        (15, 15, 10), (0, 0, -1), tipo="abocardado", diametro=6, profundidad=6, diam_abocardado=10,
        prof_abocardado=3), "cortar"),
    "unir_dos_cuerpos": lambda: geo.booleano(geo.booleano(geo.caja(10, 10, 10), geo.caja(10, 10, 10, (20, 0, 0)),
                                                          "unir"), geo.caja(30, 4, 4, (0, 3, 3)), "unir"),
}

# Consultas que devuelven números (FK-008, FK-010): misma respuesta con los dos motores.
CONSULTAS = {
    "distancias": lambda: [consultas.distancia(geo.caja(10, 10, 10), geo.caja(10, 10, 10, d)) for d in
                           ((10, 0, 0), (12, 0, 0), (3, 3, 3))] + [
        consultas.distancia(geo.cilindro(10, 20), geo.cilindro(10, 20, (x, 0, 0))) for x in (20.002, 20, 15)],
    "se_tocan": lambda: [geo.se_tocan(geo.caja(10, 10, 10), geo.caja(10, 10, 10, d)) for d in
                         ((10, 0, 0), (12, 0, 0))] + [geo.se_tocan(geo.caja(10, 10, 10), geo.caja(2, 2, 2, (4, 4, 4)))],
    "dentro_solidos": lambda: [consultas.dentro_solidos([geo.caja(10, 10, 10)], p) for p in
                               ((5, 5, 5), (15, 5, 5), (5, 5, 10 - 1e-3), (5, 5, 10))] + [
        consultas.dentro_solidos([geo.cilindro(10, 20)], p) for p in ((0, 0, 10), (0, 0, 25), (9.99, 0, 10))],
    "centro_arco": lambda: [list(consultas.centro_lineal(a)) for a in refs.subformas(_perfil(
        [("linea", 1, (0.0, 0.0), (10.0, 0.0)), ("arco", 2, (0.0, 0.0), 10.0, 0.0, np.pi / 2),
         ("linea", 3, (0.0, 10.0), (0.0, 0.0))]), "arista") if refs.firma(a)["geom"] == "circulo"],
    "es_estanca": lambda: [revision.es_estanca(f) for f in (geo.caja(10, 10, 10), CASOS["unir_dos_cuerpos"](),
                                                             CASOS["agujero_pasante"](), _perfil(_rectangulo()))],
    "cadena_tangente": lambda: _tangentes("arista", (0, 0, 12.5), sm.aristas_cadena_tangente, "medio"),
    "caras_tangentes": lambda: _tangentes("cara", (15, 1.5, 28.5), sm.caras_tangentes, "centro"),
}


def _tangentes(tipo, punto, funcion, clave):
    """FK-004: caja 30³ con la arista de arriba adelante empalmada r = 5; la cadena desde una arista o cara."""
    c = geo.caja(30, 30, 30)
    c = sm.empalme(c, [{"aristas": [_sub(c, "arista", (15, 0, 30))], "tipo": "constante", "radio": 5}])
    return sorted((refs.firma(t)[clave] for t in funcion(c, _sub(c, tipo, punto))), key=lambda p: np.round(p, 6).tolist())

_FIJA = {}


def _caja_fija():
    """Una sola caja por proceso: las aristas elegidas pertenecen a la misma forma que se modifica."""
    if "caja" not in _FIJA:
        _FIJA["caja"] = _caja()
    return _FIJA["caja"]


def _empalme_esquina():
    c = _caja_fija()
    aristas = [_sub(c, "arista", p) for p in ((5, 0, 30), (10, 10, 30), (10, 0, 15))]
    return sm.empalme(c, [{"aristas": aristas, "tipo": "constante", "radio": 2}])


def _empalme_cilindro():
    c = geo.cilindro(10, 20)
    return sm.empalme(c, [{"aristas": [_sub(c, "arista", (0, 0, 25))], "tipo": "constante", "radio": 2}],
                      cadena_tangente=False)


def _patron(trsfs):
    """Una caja 10x6x8 en (15, 0, 0) copiada con cada transformación y unida («Combinar»)."""
    base = geo.caja(10, 6, 8, (15, 0, 0))
    return sc.unir_instancias([sc.aplicar(base, t) for t in trsfs])


def _en_cilindro(operacion):
    return operacion(geo.cilindro(10, 20))


def _quitar_chaflan():
    c = _caja_fija()
    ch = sm.chaflan(c, [{"aristas": [_sub(c, "arista", (5, 0, 0))], "tipo": "distancia_igual", "distancia": 2}])
    return sm.quitar_caras(ch, [_sub(ch, "cara", (5, 1, 1))])


def _sobre_cara():
    """Boceto en las caras +Y y +Z de la caja (`plano_de_cara`) y extrusión hacia afuera."""
    c = _caja_fija()
    salida = c
    for punto, u0 in (((5, 20, 15), -6), ((5, 10, 30), 1)):      # en la cara +Y el eje u apunta a −X
        plano = geo.plano_de_cara(_sub(c, "cara", punto))
        perfil = perfiles.detectar(_rectangulo(u0, 2, 3, 4), plano)[0].cara
        salida = geo.booleano(salida, geo.extruir([perfil], plano.normal, 5), "unir")
    return salida


def _ida_y_vuelta(forma, formato):
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / ("caso." + formato)
        if formato == "step":
            intercambio.escribir_step(forma, ruta)
            return intercambio.leer_step(ruta)
        intercambio.escribir_iges(forma, ruta)
        return intercambio.leer_iges(ruta)


def _aristas(c):
    """Aristas sin las degeneradas de OpenCascade (polos y ápices): OmniKernel no las crea (regla de FK-006)."""
    aristas = refs.subformas(c, "arista")
    if os.environ["OMNICAD_MOTOR"] == "opencascade":
        from OCP.BRep import BRep_Tool
        aristas = [a for a in aristas if not BRep_Tool.Degenerated_s(a)]
    return len(aristas)


def medir(caso):
    if caso in CONSULTAS:
        return {"valores": CONSULTAS[caso]()}
    inicio = time.perf_counter()
    nombre, _, formato = caso.partition("@")
    c = CASOS[nombre]()
    if formato:
        c = _ida_y_vuelta(c, formato)
    segundos = time.perf_counter() - inicio
    p = {"volumen": geo.volumen(c), "area": geo.area(c), "valida": geo.es_valida(c),
         "caras": len(geo.caras(c)), "aristas": _aristas(c)}
    firmas = [refs.firma_cara(s) for s in geo.caras(c)]
    v, i = geo.triangulos_indexados(c)
    t = np.asarray(v, float)[np.asarray(i)]
    p["area_malla"] = float(np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum() / 2)
    p["triangulos_por_cara"] = sum(len(tris) for _, tris in geo.teselar_por_cara(c)) == len(i)
    try:
        p["caja"] = [list(map(float, x)) for x in geo.caja_envolvente(c)]
    except geo.ErrorGeometria as e:          # OmniKernel: caja de una subforma suelta (MOTOR_SIN_SOPORTE)
        assert e.error_kind == "MOTOR_SIN_SOPORTE"
        p["caja"] = None
    assert len(geo.teselar(c)[0]) > 0
    if os.environ["OMNICAD_MOTOR"] == "omnikernel":
        assert not any(n == "OCP" or n.startswith("OCP.") for n in sys.modules)
    return {"propiedades": p, "firmas": firmas, "segundos": segundos}


if __name__ == "__main__":
    try:
        resultado = medir(sys.argv[1])
    except geo.ErrorGeometria as e:
        resultado = {"error_kind": getattr(e, "error_kind", "OPERATION_FAILED"), "mensaje": str(e)}
    print("RESULTADO_PARIDAD=" + json.dumps(resultado, ensure_ascii=False))
