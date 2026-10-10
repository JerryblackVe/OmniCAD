# -*- coding: utf-8 -*-
import math
import time

import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone

from omnicad.nucleo import analisis as an
from omnicad.nucleo import geometria as g


def _cara_con_normal(forma, normal):
    for c in g.caras(forma):
        info = an.medir(c)["a"]
        if np.allclose(info.get("normal", (9, 9, 9)), normal, atol=1e-9):
            return c
    raise AssertionError("no se encontró la cara")


def _aristas_circulares(forma):
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Circle
    return [e for e in an._aristas_unicas(forma) if BRepAdaptor_Curve(e).GetType() == GeomAbs_Circle]


# ---------------------------------------------------------------- medir
def test_medir_distancia_entre_cajas_separadas():
    a, b = g.caja(10, 10, 10), g.caja(10, 10, 10, (15, 0, 0))
    r = an.medir(a, b)
    assert r["distancia"] == pytest.approx(5.0)
    assert r["delta"][0] == pytest.approx(5.0)
    assert np.linalg.norm(r["delta"]) == pytest.approx(5.0)
    assert r["a"]["volumen"] == pytest.approx(1000) and r["a"]["tipo"] == "cuerpo"
    assert r["a"]["caja"][1] == pytest.approx((10, 10, 10))


def test_medir_angulo_y_entidades_sueltas():
    c = g.caja(10, 20, 30)
    fx, fz = _cara_con_normal(c, (1, 0, 0)), _cara_con_normal(c, (0, 0, 1))
    r = an.medir(fx, fz)
    assert r["angulo"] == pytest.approx(90.0)
    assert r["distancia"] == pytest.approx(0.0, abs=1e-9)
    assert an.medir(fz)["a"]["area"] == pytest.approx(200) and an.medir(fz)["a"]["perimetro"] == pytest.approx(60)
    # Caras paralelas: ángulo 0 y distancia = espesor.
    r2 = an.medir(_cara_con_normal(c, (0, 0, -1)), fz)
    assert r2["angulo"] == pytest.approx(0.0, abs=1e-9) and r2["distancia"] == pytest.approx(30)
    # Punto suelto contra cara.
    r3 = an.medir(np.array([5.0, 5.0, 40.0]), fz)
    assert r3["distancia"] == pytest.approx(10) and r3["a"]["tipo"] == "punto"
    from OCP.TopAbs import TopAbs_VERTEX
    from OCP.TopExp import TopExp_Explorer
    v = TopExp_Explorer(c, TopAbs_VERTEX).Current()
    assert an.medir(v)["a"]["tipo"] == "vertice" and len(an.medir(v)["a"]["posicion"]) == 3
    assert g.es_valida(c)


def test_medir_arco_cilindro_y_centro_a_centro():
    c1, c2 = g.cilindro(5, 10), g.cilindro(3, 10, base=(20, 0, 0))
    borde = _aristas_circulares(c1)[0]
    info = an.medir(borde)["a"]
    assert info["radio"] == pytest.approx(5) and info["diametro"] == pytest.approx(10)
    assert info["largo"] == pytest.approx(2 * math.pi * 5)
    lat1 = next(f for f in g.caras(c1) if an.medir(f)["a"].get("superficie") == "cilindro")
    lat2 = next(f for f in g.caras(c2) if an.medir(f)["a"].get("superficie") == "cilindro")
    assert an.medir(lat1)["a"]["perimetro"] == pytest.approx(4 * math.pi * 5)   # dos círculos, sin la costura
    r = an.medir(lat1, lat2)
    assert r["distancia"] == pytest.approx(12)                     # 20 − 5 − 3 entre superficies
    assert r["centro_a_centro"]["distancia"] == pytest.approx(20)
    assert r["centro_a_centro"]["minima"] == pytest.approx(12) and r["centro_a_centro"]["maxima"] == pytest.approx(28)
    r2 = an.medir(lat1, lat2, centro_a_centro=True)
    assert r2["distancia"] == pytest.approx(20) and abs(r2["delta"][0]) == pytest.approx(20)
    tapa = _cara_con_normal(c1, (0, 0, 1))
    assert an.medir(tapa)["a"]["centro"] == pytest.approx((0, 0, 10)) and an.medir(tapa)["a"]["radio"] == pytest.approx(5)
    with pytest.raises(g.ErrorGeometria):
        an.medir(g.caja(1, 1, 1), g.caja(1, 1, 1, (3, 0, 0)), centro_a_centro=True)


# ---------------------------------------------------------------- interferencias
def test_interferencias_volumen_exacto_y_coincidentes():
    cuerpos = {"A": g.caja(10, 10, 10), "B": g.caja(10, 10, 10, (5, 0, 0)), "C": g.caja(10, 10, 10, (50, 0, 0)),
               "D": g.caja(10, 10, 10, (0, 0, 10))}   # D apoya sobre A
    res = an.interferencias(cuerpos)
    assert [(r["a"], r["b"]) for r in res] == [("A", "B")]
    assert res[0]["volumen"] == pytest.approx(500)
    assert g.volumen(res[0]["forma"]) == pytest.approx(500) and g.es_valida(res[0]["forma"])
    con = an.interferencias(cuerpos, caras_coincidentes=True)
    coinc = {(r["a"], r["b"]): r for r in con if r["coincidente"]}
    assert coinc[("A", "D")]["area"] == pytest.approx(100) and coinc[("A", "D")]["volumen"] == 0.0
    assert coinc[("B", "D")]["area"] == pytest.approx(50)
    assert ("A", "C") not in coinc


def test_interferencias_ignora_contacto_con_error_de_redondeo():
    """El cilindro Ø28 de la lámpara apoyado en el Ø14 con 1,8e-5 rad de inclinación (la del extremo del
    barrido) daba 0,004 mm³ de «interferencia»: una cuña de 5e-5 mm de espesor es contacto, no choque."""
    a = 1.8e-5
    giro = np.identity(4)
    giro[[0, 0, 2, 2], [0, 2, 0, 2]] = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    giro[:3, 3] = np.array([0, 0, 405.0]) - giro[:3, :3] @ (0, 0, 405.0)      # alrededor del punto de apoyo
    arriba, abajo = g.transformar(g.cilindro(14, 27, base=(0, 0, 405)), giro), g.cilindro(7, 405)
    comun = g.volumen(g.booleano(arriba, abajo, "intersecar"))
    assert 1e-9 * g.volumen(abajo) < comun < 1e-2          # el filtro relativo solo no lo descartaba
    assert an.interferencias({"A": arriba, "B": abajo}) == []
    real = an.interferencias({"A": g.caja(30, 30, 10), "B": g.caja(10, 10, 10, (5, 5, 9.99))})   # solape de 0,01 mm
    assert len(real) == 1 and real[0]["volumen"] == pytest.approx(1.0) and g.es_valida(real[0]["forma"])


# ---------------------------------------------------------------- propiedades físicas
def test_propiedades_fisicas_caja_acero():
    p = an.propiedades_fisicas(g.caja(10, 20, 30), 7.85)
    m = 6000 * 7.85e-3
    assert p["volumen"] == pytest.approx(6000) and p["masa"] == pytest.approx(m)
    assert p["area"] == pytest.approx(2 * (200 + 300 + 600))
    assert p["centro_masa"] == pytest.approx((5, 10, 15))
    ic = np.array(p["inercia_centro"])
    assert ic[0, 0] == pytest.approx(m * (20 ** 2 + 30 ** 2) / 12)
    assert ic[1, 1] == pytest.approx(m * (10 ** 2 + 30 ** 2) / 12)
    assert ic[2, 2] == pytest.approx(m * (10 ** 2 + 20 ** 2) / 12)
    assert ic[0, 1] == pytest.approx(0, abs=1e-6)
    io = np.array(p["inercia_origen"])
    assert io[0, 0] == pytest.approx(ic[0, 0] + m * (10 ** 2 + 15 ** 2))
    assert io[0, 1] == pytest.approx(-m * 5 * 10)
    assert sorted(p["momentos_principales"]) == pytest.approx(sorted(np.diag(ic)))
    with pytest.raises(g.ErrorGeometria):
        an.propiedades_fisicas(g.caja(1, 1, 1), 0)


def test_centro_de_masa_combinado_y_materiales():
    a, b = g.caja(10, 10, 10), g.caja(10, 10, 10, (20, 0, 0))
    assert an.centro_de_masa([a, b]) == pytest.approx((15, 5, 5))
    assert an.centro_de_masa({"a": a, "b": b}, densidades=[1.0, 3.0]) == pytest.approx((20, 5, 5))
    nombres = {"Acero", "Acero inoxidable", "Aluminio 6061", "Latón", "Cobre", "ABS", "PLA", "PETG", "Nylon",
               "Policarbonato", "Madera (pino)", "Vidrio", "Titanio", "Hierro fundido", "Goma natural", "Goma EPDM",
               "Neopreno", "Silicona", "TPU", "Polipropileno", "Polietileno HDPE", "POM (acetal)", "Acrílico (PMMA)"}
    assert an.MATERIALES_BASE == nombres and nombres <= set(an.TABLA_MATERIALES)   # más los propios del usuario
    for mat in an.TABLA_MATERIALES.values():
        assert 0.3 < mat["densidad"] < 10 and all(0 <= c <= 1 for c in mat["color"])
    acero = an.TABLA_MATERIALES["Acero"]["densidad"]
    assert an.propiedades_fisicas(a, acero)["masa"] == pytest.approx(7.85)


# ---------------------------------------------------------------- mapas de color
def test_curvatura_media_esfera():
    v, n, val = an.valores_curvatura(g.esfera(10), tipo="media")
    assert v.shape == n.shape and len(val) == len(v) and len(v) % 3 == 0
    assert np.median(val) == pytest.approx(0.1, rel=1e-6)
    assert np.allclose(val, 0.1, atol=1e-6)
    _, _, k = an.valores_curvatura(g.esfera(10), tipo="gaussiana")
    assert np.allclose(k, 0.01, atol=1e-7)
    # Normales exactas hacia afuera: n = p/|p|.
    assert np.allclose(n, v / np.linalg.norm(v, axis=1, keepdims=True), atol=1e-4)
    # Agujero (cóncavo): curvatura media negativa en la pared del cilindro restado.
    pieza = g.booleano(g.caja(20, 20, 10, (-10, -10, 0)), g.cilindro(4, 10), "cortar")
    v2, n2, h = an.valores_curvatura(pieza, tipo="media")
    pared = np.abs(n2[:, 2]) < 0.1
    pared &= np.linalg.norm(v2[:, :2], axis=1) < 4.01
    assert pared.any() and np.allclose(h[pared], -1 / 8, atol=1e-6)
    _, _, col = an.colores_curvatura(g.esfera(10), tipo="gaussiana", rango=0.01)
    assert col.shape == v.shape and np.allclose(col, an._COLORES_RAMPA[-1], atol=1e-6)   # todo rojo
    _, _, col2 = an.colores_curvatura(g.caja(5, 5, 5), tipo="maxima", bandas=True)
    assert np.allclose(col2, an._COLORES_RAMPA[3], atol=1e-6)   # plano → verde
    with pytest.raises(g.ErrorGeometria):
        an.colores_curvatura(g.esfera(1), tipo="rara")


def test_desmoldeo_tronco_de_cono_5_grados():
    h, r1 = 20.0, 10.0
    r2 = r1 - h * math.tan(math.radians(5))
    cono = BRepPrimAPI_MakeCone(r1, r2, h).Shape()
    assert g.es_valida(cono)
    v, n, col = an.colores_desmoldeo(cono, (0, 0, 1), 0.0, 3.0)
    lateral = np.abs(n[:, 2]) < 0.5
    assert lateral.any() and np.allclose(col[lateral], an.VERDE)
    _, _, ang = an.angulos_desmoldeo(cono, (0, 0, 1))
    assert np.allclose(ang[lateral], 5.0, atol=0.05)   # normales interpoladas entre nodos exactos
    assert np.allclose(col[n[:, 2] < -0.99], an.ROJO)          # base: contrasalida
    _, _, col2 = an.colores_desmoldeo(cono, (0, 0, 1), 0.0, 10.0)
    assert np.allclose(col2[lateral], an.AMARILLO)              # 5° no llega a 10°: neutro
    _, _, col3 = an.colores_desmoldeo(g.caja(5, 5, 5), (0, 0, 1))
    assert (np.all(col3 == np.float32(an.ROJO), axis=1)).sum() > 0    # paredes a 0°: insuficiente


def test_accesibilidad_con_voladizo():
    # Soporte en C: base, columna y techo que tapa la base desde arriba para x > 10.
    pieza = g.unir_todos([g.caja(30, 10, 2), g.caja(10, 10, 12), g.caja(30, 10, 2, (0, 0, 12))])
    v, n, col = an.colores_accesibilidad(pieza, (0, 0, 1), deflexion=0.5)
    verde = np.all(np.isclose(col, an.VERDE), axis=1)
    techo = (np.abs(v[:, 2] - 14) < 1e-6) & (n[:, 2] > 0.99)
    interior = (v[:, 0] > 12) & (v[:, 0] < 29) & (v[:, 1] > 0.5) & (v[:, 1] < 9.5)   # lejos de los bordes
    tapado = (np.abs(v[:, 2] - 2) < 1e-6) & (n[:, 2] > 0.99) & interior
    abajo = (np.abs(v[:, 2]) < 1e-6) & (n[:, 2] < -0.99)
    assert verde[techo].all() and tapado.any() and not verde[tapado].any() and not verde[abajo].any()
    # Sin oclusión, la base tapada mira hacia arriba y cuenta como accesible.
    _, _, col2 = an.colores_accesibilidad(pieza, (0, 0, 1), oclusion=False, deflexion=0.5)
    assert np.allclose(col2[tapado], an.VERDE)
    # Ambas direcciones: la cara de abajo se ve desde −Z.
    _, _, col3 = an.colores_accesibilidad(pieza, (0, 0, 1), ambos_sentidos=True, deflexion=0.5)
    assert np.allclose(col3[abajo], an.VERDE)


def test_radio_minimo_agujero_y_rincon_vivo():
    pieza = g.booleano(g.caja(20, 20, 10, (-10, -10, 0)), g.cilindro(3, 10), "cortar")
    v, n, col = an.colores_radio_minimo(pieza, 5.0)
    pared = (np.linalg.norm(v[:, :2], axis=1) < 3.01) & (np.abs(n[:, 2]) < 0.1)
    rojo = np.all(np.isclose(col, an.ROJO), axis=1)
    assert pared.any() and rojo[pared].all() and not rojo[~pared].any()
    _, _, col2 = an.colores_radio_minimo(pieza, 2.0)
    assert np.allclose(col2, an.VERDE)
    # Caja: sin rincones interiores. L: el rincón interior (x=10, z=10) es una arista viva cóncava.
    _, _, col3 = an.colores_radio_minimo(g.caja(10, 10, 10), 1.0)
    assert np.allclose(col3, an.VERDE)
    ele = g.unir_todos([g.caja(30, 10, 10), g.caja(10, 10, 30)])
    v4, n4, col4 = an.colores_radio_minimo(ele, 1.0)
    rojo4 = np.all(np.isclose(col4, an.ROJO), axis=1)
    # Nodos sobre la arista del rincón, de las dos caras que la forman (no de las caras laterales y=0/10).
    rincon = (np.abs(v4[:, 0] - 10) < 1e-6) & (np.abs(v4[:, 2] - 10) < 1e-6) & (np.abs(n4[:, 1]) < 0.5)
    assert rincon.any() and rojo4[rincon].all() and not rojo4[~rincon].any()
    _, _, col5 = an.colores_radio_minimo(ele, 1.0, aristas_vivas=False)
    assert np.allclose(col5, an.VERDE)


def test_cebra_y_entorno_vectorizados():
    rng = np.random.default_rng(0)
    normales = rng.normal(size=(200_000, 3)).astype(np.float32)
    t0 = time.perf_counter()
    cebra = an.colores_cebra(normales, (0, -1, 0), frecuencia=8)
    entorno = an.colores_mapa_entorno(normales, (0, -1, 0))
    assert time.perf_counter() - t0 < 1.0
    assert cebra.shape == normales.shape and cebra.dtype == np.float32
    assert np.allclose(np.unique(cebra[:, 0]), [0.06, 0.97])
    assert entorno.shape == normales.shape and entorno.min() >= 0 and entorno.max() <= 1
    # Las franjas cambian al mover la cámara (no están bloqueadas).
    assert not np.array_equal(cebra, an.colores_cebra(normales, (1, -1, 0), frecuencia=8))
    # Reflejo hacia el cielo → azulado; hacia el piso → oscuro.
    vista = np.array([0.0, -1.0, 0.0])
    arriba = an.colores_mapa_entorno(np.array([[0.0, 0.5, 0.5]]), vista)[0]   # refleja hacia +Z
    abajo = an.colores_mapa_entorno(np.array([[0.0, 0.5, -0.5]]), vista)[0]   # refleja hacia −Z
    assert arriba[2] > arriba[0] and abajo.sum() < arriba.sum()


def test_peine_de_curvatura_circulo_y_recta():
    c = g.cilindro(10, 5)
    borde = _aristas_circulares(c)[0]
    r = an.peine_curvatura(borde, densidad=12, escala=1.0)
    assert r["puas"].shape == (12, 2, 3) and len(r["envolventes"]) == 1
    assert np.allclose(r["curvaturas"][0], 0.1, atol=1e-9)
    base, punta = r["puas"][:, 0], r["puas"][:, 1]
    largo = np.linalg.norm(punta - base, axis=1)
    assert np.allclose(largo, r["factor"] * 0.1, rtol=1e-5)          # largo = κ · factor
    assert largo.max() == pytest.approx(0.2 * np.linalg.norm(base.max(axis=0) - base.min(axis=0)), rel=1e-5)
    assert np.all(np.linalg.norm(punta[:, :2], axis=1) > 10)        # las púas salen hacia afuera
    recta = an.peine_curvatura(g.caja(10, 10, 10), densidad=5)
    assert recta["factor"] == 0.0 and np.allclose(recta["curvaturas"][0], 0)
    assert recta["puas"].shape == (12 * 5, 2, 3)


def test_isocurvas_caja_y_disco_recortado():
    iso = an.isocurvas(g.caja(10, 20, 30), n_u=3, n_v=3)
    assert len(iso["u"]) == 18 and len(iso["v"]) == 18
    total = sum(float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) for p in iso["u"] + iso["v"])
    assert total == pytest.approx(720, rel=1e-4)
    tapa = _cara_con_normal(g.cilindro(5, 2), (0, 0, 1))
    iso2 = an.isocurvas(tapa, n_u=1, n_v=1)
    for p in iso2["u"] + iso2["v"]:
        assert float(np.linalg.norm(p[-1] - p[0])) == pytest.approx(10, abs=1e-2)   # diámetro, no el cuadrado


def test_seccion_cilindro_y_medio_espacio():
    cil = g.cilindro(5, 10)
    plano = g.Plano("XY", 5)
    s = an.seccion(cil, plano)
    assert s["largo"] == pytest.approx(2 * math.pi * 5, rel=1e-6)
    assert s["area"] == pytest.approx(math.pi * 25, rel=1e-6)
    assert len(s["polilineas"]) >= 1 and s["triangulos"].shape[1:] == (3, 3)
    assert np.allclose(s["triangulos"][..., 2], 5, atol=1e-6)
    detras = an.cortar_medio_espacio(cil, plano)
    assert g.volumen(detras) == pytest.approx(math.pi * 25 * 5) and g.es_valida(detras)
    assert g.caja_envolvente(detras)[1][2] == pytest.approx(5)
    adelante = an.cortar_medio_espacio(cil, plano, invertir=True)
    assert g.caja_envolvente(adelante)[0][2] == pytest.approx(5)
    # Plano inclinado lejos del origen y sin corte.
    inclinado = g.Plano.desde_marco((0, 0, 5), (0.3, 0, 1), (1, 0, -0.3))
    assert an.seccion(cil, inclinado)["area"] > math.pi * 25
    vacia = an.seccion(cil, g.Plano("XY", 50))
    assert vacia["cara"] is None and vacia["area"] == 0.0 and vacia["polilineas"] == []
