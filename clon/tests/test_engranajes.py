# -*- coding: utf-8 -*-
"""CREAR › Engranaje y Eje: núcleo (`nucleo/engranajes.py`) y pasos del timeline (`timeline/ops_engranaje.py`).
Medidas de ISO 21771 / ISO 53, par sin interferencia y con contacto, helicoidal, cremallera, rueda de cadena ISO 606 y
eje escalonado con su volumen exacto."""
import math

import numpy as np
import pytest
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from scipy.integrate import quad

from omnicad.nucleo import engranajes as en
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import referencias as refs
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva, operacion_desde_dict
from omnicad.timeline.ops_engranaje import OpEje, OpEngranaje, agregar_ensamblaje
from omnicad.timeline.ops_ensamblar import OpUnion

M, Z = 2.0, 20


def _inv(a):
    return math.tan(a) - a


def _area_exacta(m, z, alfa=20.0, x=0.0, c=0.25):
    """Área del perfil transversal integrada en polares: el disco de fondo más z dientes de ancho angular 2θ(ρ)."""
    g = en.medidas_engranaje(m, z, alfa, 0, x, c)
    rb, ra, rf, tb = g["diametro_base"] / 2, g["diametro_exterior"] / 2, g["diametro_fondo"] / 2, g["semiangulo_base"]

    def theta(rho):
        return tb if rho <= rb else tb - _inv(math.acos(rb / rho))
    puntos = [rb] if rf < rb < ra else None
    dientes, _ = quad(lambda rho: 2 * theta(rho) * rho, rf, ra, points=puntos, epsabs=1e-12, epsrel=1e-12)
    return math.pi * rf ** 2 + z * dientes


def _zona(forma, centro, lado=16.0, alto=30.0):
    """La parte de la forma dentro de una caja alrededor de `centro` (para medir el engrane rápido)."""
    caja = geo.caja(lado, lado, alto, (centro[0] - lado / 2, centro[1] - lado / 2, -1.0))
    return geo.booleano(forma, caja, "intersecar")


def _interseccion(a, b):
    inter = geo.booleano(a, b, "intersecar")
    return 0.0 if geo.esta_vacia(inter) else abs(geo.volumen(inter))


# ---------------------------------------------------------------- medidas
def test_medidas_de_un_z20_m2():
    g = en.medidas_engranaje(M, Z)
    assert g["diametro_primitivo"] == pytest.approx(40.0)
    assert g["diametro_exterior"] == pytest.approx(44.0)
    assert g["diametro_fondo"] == pytest.approx(35.0)
    assert g["diametro_base"] == pytest.approx(40.0 * math.cos(math.radians(20)))
    assert g["paso"] == pytest.approx(2 * math.pi) and g["espesor_primitivo"] == pytest.approx(math.pi)
    h = en.medidas_engranaje(2, 20, helice=20)               # helicoidal: módulo y primitivo transversales
    assert h["modulo_transversal"] == pytest.approx(2 / math.cos(math.radians(20)))
    assert h["diametro_primitivo"] == pytest.approx(40 / math.cos(math.radians(20)))
    assert h["diametro_exterior"] == pytest.approx(h["diametro_primitivo"] + 4)


def test_socavado_y_dientes_minimos():
    assert en.dientes_minimos_teorico(20) == pytest.approx(2 / math.sin(math.radians(20)) ** 2)   # 17,1
    assert en.dientes_minimos(20) == 18 and en.dientes_minimos(14.5) == 32
    s = en.socavado(12, 20)
    assert s["socavado"] and s["desplazamiento_minimo"] == pytest.approx(1 - 12 * math.sin(math.radians(20)) ** 2 / 2)
    assert not en.socavado(12, 20, desplazamiento=0.35)["socavado"]
    assert not en.socavado(18, 20)["socavado"]


def test_distancia_entre_centros():
    assert en.distancia_entre_centros(2, 20, 40) == pytest.approx(60.0)
    assert en.distancia_entre_centros(2, 20, 40, desplazamiento1=0.3, desplazamiento2=-0.3) == pytest.approx(60.0)
    assert en.distancia_entre_centros(2, 20, 40, helice=15) == pytest.approx(60 / math.cos(math.radians(15)))
    # con x1 + x2 > 0 se separan: inv αw = inv α + 2·tan α·(x1+x2)/(z1+z2)
    a = en.distancia_entre_centros(2, 20, 40, desplazamiento1=0.5)
    alfa = math.radians(20)
    objetivo = _inv(alfa) + 2 * math.tan(alfa) * 0.5 / 60
    aw = math.acos(60 * math.cos(alfa) / a)
    assert a > 60 and _inv(aw) == pytest.approx(objetivo, abs=1e-12)
    d = en.datos_par(2, 20, 40)
    assert d["relacion"] == pytest.approx(2.0) and 1.6 < d["recubrimiento"] < 1.7
    assert not d["interferencia1"] and not d["interferencia2"]
    assert en.datos_par(2, 10, 60)["interferencia1"]          # z1 = 10 sin desplazar: la cabeza del 2 entra


# ---------------------------------------------------------------- engranaje recto y helicoidal
def test_engranaje_recto_volumen_exacto_y_valido():
    f = en.engranaje(M, Z, ancho=10)
    assert geo.es_valida(f)
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(f)
    assert (x1, z0, z1) == pytest.approx((22.0, 0.0, 10.0), abs=1e-5) and x0 == pytest.approx(-22, abs=0.5)
    v = geo.volumen(f)
    assert math.pi * 17.5 ** 2 * 10 < v < math.pi * 22 ** 2 * 10            # entre el disco de fondo y el exterior
    assert v == pytest.approx(_area_exacta(M, Z) * 10, rel=1e-5)            # y el perfil de evolvente exacto
    con_agujero = en.engranaje(M, Z, ancho=10, agujero=8)
    assert geo.es_valida(con_agujero) and geo.volumen(con_agujero) == pytest.approx(v - math.pi * 16 * 10, rel=1e-6)


def test_helicoidal_valido_y_mismo_perfil_en_cada_seccion():
    f = en.engranaje(M, Z, ancho=10, helice=20)
    assert geo.es_valida(f)
    area = geo.area(en.perfil_engranaje(M, Z, helice=20))
    assert geo.volumen(f) == pytest.approx(area * 10, rel=1e-3)               # Cavalieri: el perfil solo gira
    g = en.medidas_engranaje(M, Z, helice=20)
    ra = g["diametro_exterior"] / 2
    (_x0, _y0, z0), (_x1, _y1, z1) = geo.caja_envolvente(f)
    assert (z0, z1) == pytest.approx((0, 10), abs=1e-5)
    assert max(abs(c) for c in geo.caja_envolvente(f)[1][:2]) <= ra + 1e-3
    # hélice a derechas: arriba los dientes giraron ancho·tan β / r en sentido antihorario (visto desde +Z)
    cabezas = [refs.punto_de_vertice(v) for v in refs.subformas(f, "vertice")]
    cabezas = [math.degrees(math.atan2(p[1], p[0])) % 18 for p in cabezas
               if abs(p[2] - 10) < 1e-6 and abs(math.hypot(p[0], p[1]) - ra) < 1e-3]
    giro = g["torsion_por_mm"] * 10
    assert giro == pytest.approx(math.degrees(10 * math.tan(math.radians(20)) / (g["diametro_primitivo"] / 2)))
    assert (min(cabezas) + max(cabezas)) / 2 == pytest.approx(giro % 18, abs=1e-3)


def test_errores_claros():
    with pytest.raises(geo.ErrorGeometria, match="entre 3 y"):
        en.engranaje(M, 2)
    with pytest.raises(geo.ErrorGeometria, match="entero"):
        en.medidas_engranaje(M, 20.5)
    with pytest.raises(geo.ErrorGeometria, match="en punta"):
        en.perfil_engranaje(M, 8, desplazamiento=1.5)
    with pytest.raises(geo.ErrorGeometria, match="no entra"):
        en.engranaje(M, Z, agujero=34)
    with pytest.raises(geo.ErrorGeometria, match="ángulo de presión"):
        en.medidas_engranaje(M, Z, angulo_presion=60)


# ---------------------------------------------------------------- par
def test_par_engrana_sin_interferencia_y_con_contacto():
    par = en.par_engranajes(M, 20, 40, ancho=4)
    f1, f2 = par["engranaje1"], par["engranaje2"]
    assert par["distancia_centros"] == pytest.approx(M * (20 + 40) / 2)
    assert geo.es_valida(f1) and geo.es_valida(f2)
    (x0, y0, _), (x1, y1, _) = geo.caja_envolvente(f2)
    assert ((x0 + x1) / 2, (y0 + y1) / 2) == pytest.approx((60.0, 0.0), abs=0.6)
    assert _interseccion(f1, f2) == pytest.approx(0.0, abs=1e-6)
    z1, z2 = _zona(f1, (20, 0)), _zona(f2, (20, 0))
    assert BRepExtrema_DistShapeShape(z1, z2).Value() < 0.05


def test_par_con_juego_direccion_y_desplazamiento():
    par = en.par_engranajes(M, 18, 30, ancho=3, juego=0.1, direccion=30)
    d = math.radians(30)
    assert par["centro2"][:2] == pytest.approx((48 * math.cos(d), 48 * math.sin(d)))
    contacto = (18 * math.cos(d), 18 * math.sin(d))
    z1, z2 = _zona(par["engranaje1"], contacto), _zona(par["engranaje2"], contacto)
    # juego de 0,1 mm repartido a los dos flancos: 0,05 en el primitivo = 0,05·cos 20° en la normal
    assert BRepExtrema_DistShapeShape(z1, z2).Value() == pytest.approx(0.05 * math.cos(math.radians(20)), rel=0.02)
    corrido = en.par_engranajes(1.5, 12, 30, ancho=3, desplazamiento1=0.4, desplazamiento2=-0.1, giro=5)
    assert corrido["distancia_centros"] > 1.5 * 42 / 2
    assert corrido["giro2"] == pytest.approx(180 + 6 - 5 * 12 / 30)        # el primero girado 5°: el segundo, −2°
    assert _interseccion(corrido["engranaje1"], corrido["engranaje2"]) == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------- cremallera y rueda de cadena
def test_cremallera_paso_pi_por_modulo():
    n, alto, b = 6, 10.0, 5.0
    f = en.cremallera(M, n, ancho=b, alto=alto)
    assert geo.es_valida(f)
    p = math.pi * M
    (x0, y0, _), (x1, y1, _) = geo.caja_envolvente(f)
    assert (x0, x1, y0, y1) == pytest.approx((0, n * p, -alto, M), abs=1e-6)
    cabezas = sorted(refs.firma_cara(c)["centro"][0] for c in refs.subformas(f, "cara")
                     if refs.firma_cara(c)["geom"] == "plano" and np.allclose(refs.firma_cara(c)["normal"], (0, 1, 0))
                     and abs(refs.firma_cara(c)["centro"][1] - M) < 1e-6)
    assert len(cabezas) == n and np.allclose(np.diff(cabezas), p)
    hf, t = 1.25 * M, math.tan(math.radians(20))
    area = n * p * (alto - hf) + n * (p / 2 + (hf - M) * t) * (M + hf)       # base + dientes trapeciales
    assert geo.volumen(f) == pytest.approx(area * b, rel=1e-9)


def test_rueda_de_cadena_iso_606():
    p, d1, z = en.CADENAS["08B"][0], en.CADENAS["08B"][1], 20
    d = en.datos_rueda_cadena(p, d1, z)
    assert d["diametro_primitivo"] == pytest.approx(p / math.sin(math.pi / z))
    assert d["diametro_fondo"] == pytest.approx(d["diametro_primitivo"] - d1)
    assert d["diametro_exterior_min"] < d["diametro_exterior_max"]
    f = en.rueda_cadena(p, d1, z, ancho=7.2, agujero=12)
    assert geo.es_valida(f)
    radios = [np.hypot(*refs.punto_de_vertice(v)[:2]) for v in refs.subformas(f, "vertice")]
    ra = max(radios)
    assert d["diametro_exterior_min"] / 2 - 0.5 < ra <= d["diametro_exterior_max"] / 2
    # el fondo del hueco: el arco de asiento (radio medio entre ri mín y máx) centrado en el rodillo
    ri = (d["radio_asiento_min"] + d["radio_asiento_max"]) / 2
    fondo = d["diametro_primitivo"] / 2 - ri
    seccion = geo.booleano(f, geo.caja(fondo + 0.02, 0.002, 1, (0, -0.001, 3)), "intersecar")
    assert geo.caja_envolvente(seccion)[1][0] == pytest.approx(fondo, abs=1e-5)     # el rayo +X cae en un hueco
    v = geo.volumen(f)
    assert math.pi * (fondo ** 2 - 36) * 7.2 < v < math.pi * (ra ** 2 - 36) * 7.2
    assert en.ancho_diente_cadena(7.75, 12.7) == pytest.approx(0.93 * 7.75)


# ---------------------------------------------------------------- eje escalonado
TRAMOS = [{"diametro": 20, "largo": 30, "inicio": "chaflan", "medida_inicio": 1},
          {"diametro": 30, "largo": 20, "fin": "chaflan", "medida_fin": 2},
          {"diametro": 16, "largo": 25, "inicio": "chaflan", "medida_inicio": 0.5, "fin": "chaflan", "medida_fin": 1}]


def test_eje_volumen_exacto_cilindros_menos_chaflanes():
    e = en.eje_escalonado(TRAMOS)
    assert geo.es_valida(e)
    assert sum(geo.caja_envolvente(e), ()) == pytest.approx((-15, -15, 0, 15, 15, 75), abs=1e-6)
    cilindros = math.pi * (10 ** 2 * 30 + 15 ** 2 * 20 + 8 ** 2 * 25)
    # chaflán de 45° en una esquina convexa de radio R: π·s²·(R − s/3); en una cóncava (el Ø16 contra el Ø30) suma
    # π·s²·(r + s/3)
    chaflanes = math.pi * (1 * (10 - 1 / 3) + 4 * (15 - 2 / 3) + 1 * (8 - 1 / 3))
    concavo = math.pi * 0.25 * (8 + 0.5 / 3)
    assert geo.volumen(e) == pytest.approx(cilindros - chaflanes + concavo, rel=1e-9)


def test_eje_con_empalmes_coincide_con_pappus():
    tramos = [{"diametro": 12, "largo": 10, "inicio": "empalme", "medida_inicio": 1},
              {"diametro": 24, "largo": 15, "inicio": "empalme", "medida_inicio": 2},
              {"diametro": 24, "largo": 5, "fin": "empalme", "medida_fin": 3},      # mismo diámetro: sin escalón
              {"diametro": 10, "largo": 20, "inicio": "empalme", "medida_inicio": 1.5}]
    e = en.eje_escalonado(tramos)
    assert geo.es_valida(e)
    assert geo.volumen(e) == pytest.approx(en.volumen_eje(tramos), rel=1e-7)


def test_eje_errores():
    with pytest.raises(geo.ErrorGeometria, match="no entra"):
        en.eje_escalonado([{"diametro": 10, "largo": 4, "inicio": "chaflan", "medida_inicio": 3,
                            "fin": "chaflan", "medida_fin": 3}])
    with pytest.raises(geo.ErrorGeometria, match="no hay escalón"):
        en.eje_escalonado([{"diametro": 10, "largo": 4, "fin": "chaflan", "medida_fin": 1}, {"diametro": 10, "largo": 4}])
    with pytest.raises(geo.ErrorGeometria, match="al menos un tramo"):
        en.eje_escalonado([])
    with pytest.raises(geo.ErrorGeometria, match="remate"):
        en.eje_escalonado([{"diametro": 10, "largo": 4, "inicio": "bisel"}])


# ---------------------------------------------------------------- pasos del timeline
def _cuerpos(doc, op):
    return [c for c in doc.estado_final.cuerpos.values() if c.op_id == op.id]


def test_op_engranaje_en_plano_xz_con_parametros_y_receta():
    doc = Documento()
    doc.parametros.agregar("z", "24", "escalar")
    op = OpEngranaje(doc.nuevo_id(), dientes="z", plano={"tipo": "plano", "id": "XZ"}, x="10 mm", y="5 mm",
                     ancho="6 mm")
    r = doc.agregar(op)
    assert r.estado == "ok", r.mensaje
    (c,) = _cuerpos(doc, op)
    assert c.nombre == "Engranaje z24" and geo.es_valida(c.forma)
    (x0, y0, z0), (x1, y1, z1) = geo.caja_envolvente(c.forma)
    assert (y0, y1) == pytest.approx((-6, 0), abs=1e-5)                      # la normal de XZ es −Y
    assert x1 == pytest.approx(10 + 26, abs=1e-5) and (z0 + z1) / 2 == pytest.approx(5, abs=0.6)
    doc.parametros.modificar("z", "30")
    doc.recalcular()
    (c,) = _cuerpos(doc, op)
    assert geo.caja_envolvente(c.forma)[1][0] == pytest.approx(10 + 32, abs=1e-5)
    copia = operacion_desde_dict(op.a_dict())
    assert copia.p == op.p and isinstance(copia, OpEngranaje)


def test_op_engranaje_cremallera_rueda_y_avisos():
    doc = Documento()
    ops = [OpEngranaje(doc.nuevo_id(), tipo="cremallera", dientes="5"),
           OpEngranaje(doc.nuevo_id(), tipo="rueda_cadena", dientes="16", cadena="06B", ancho="5.3 mm"),
           OpEngranaje(doc.nuevo_id(), tipo="rueda_cadena", dientes="12", cadena="personalizada", paso="8 mm",
                       rodillo="5 mm", ancho="2.8 mm"),
           OpEngranaje(doc.nuevo_id(), dientes="12", y="80 mm")]
    for op in ops:
        r = doc.agregar(op)
        assert r.estado in ("ok", "aviso"), r.mensaje
        assert all(geo.es_valida(c.forma) for c in _cuerpos(doc, op))
    assert "socavado" in doc.resultado(ops[-1].id).mensaje
    mal = OpEngranaje(doc.nuevo_id(), dientes="20.5")
    assert doc.agregar(mal).estado == "error" and "entero" in doc.resultado(mal.id).mensaje


def test_par_ensamblado_gira_sin_interferir_y_deshace_en_un_paso():
    doc = Documento()
    op = OpEngranaje(doc.nuevo_id(), par=True, ancho="4 mm")
    assert doc.agregar(op).estado == "ok"
    pila = len(doc._deshacer)
    pasos = agregar_ensamblaje(doc, op.id, un_paso=True)
    assert len(doc.operaciones) == 6 and len(doc._deshacer) == pila
    assert all(r.estado == "ok" for r in doc.resultados), [r.mensaje for r in doc.resultados]
    assert doc.operacion(pasos["vinculo"]).p["factor"] == "(20) / (40)"
    u1 = doc.operacion(pasos["uniones"][0])
    doc.reemplazar(u1.id, OpUnion(u1.id, u1.nombre, u1.suprimida, **dict(u1.p, giro="7 deg")))
    assert doc.estado_final.uniones[pasos["uniones"][1]]["valores"]["giro"] == pytest.approx(-3.5)
    c1, c2 = (doc.estado_final.cuerpos[f"{op.id}.c{k}"] for k in (1, 2))
    assert _interseccion(c1.forma, c2.forma) == pytest.approx(0.0, abs=1e-6)
    doc.deshacer()                     # el giro
    doc.deshacer()                     # el engranaje y su ensamblaje juntos
    assert doc.operaciones == []


def test_op_eje_nuevo_y_cortando_un_agujero_escalonado():
    doc = Documento()
    tramos = [{k: f"{v} mm" if isinstance(v, (int, float)) else v for k, v in t.items()} for t in TRAMOS]
    eje = OpEje(doc.nuevo_id(), tramos=tramos)
    assert doc.agregar(eje).estado == "ok"
    (c,) = _cuerpos(doc, eje)
    assert c.nombre == "Eje Ø30" and geo.volumen(c.forma) == pytest.approx(en.volumen_eje(TRAMOS), rel=1e-9)
    assert "30 mm" in eje.expresiones()
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40 mm", largo="40 mm", alto="20 mm", x="-20 mm",
                            y="-20 mm"))
    hueco = OpEje(doc.nuevo_id(), tramos=[{"diametro": "10 mm", "largo": "8 mm"}, {"diametro": "6 mm", "largo": "20 mm"}],
                  operacion="cortar")
    assert doc.agregar(hueco).estado == "ok"
    caja = doc.estado_final.cuerpos["op1.c1"].forma
    assert geo.es_valida(caja)
    assert geo.volumen(caja) == pytest.approx(40 * 40 * 20 - math.pi * (25 * 8 + 9 * 12), rel=1e-9)
    mal = OpEje(doc.nuevo_id(), tramos=["20 mm"])
    assert doc.agregar(mal).estado == "error" and "tramos[0]" in doc.resultado(mal.id).mensaje
