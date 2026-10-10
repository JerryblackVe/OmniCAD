# -*- coding: utf-8 -*-
import json
import math
import warnings

import numpy as np
import pytest

from omnicad.nucleo import geometria as g
from omnicad.nucleo import malla as ml

V_CUBO = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0],
                   [0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]], float)
F_CUBO = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4],
                   [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])


def cubo(desplazamiento=(0, 0, 0), lado=10.0):
    return ml.Malla(V_CUBO * lado / 10 + np.asarray(desplazamiento, float), F_CUBO)


@pytest.fixture(scope="module")
def esfera():
    return ml.desde_brep(g.esfera(10))


def mismos_triangulos(a, b):
    return a.caras.shape == b.caras.shape and np.array_equal(a.triangulos(), b.triangulos())


# ---------------------------------------------------------------- modelo
def test_cubo_12_triangulos():
    m = cubo()
    assert m.volumen() == pytest.approx(1000.0)
    assert m.area() == pytest.approx(600.0)
    assert m.caja() == ((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    assert m.es_cerrada()
    n = m.normales_caras()
    centros = m.triangulos().mean(1) - 5.0
    assert np.all(np.einsum("ij,ij->i", n, centros) > 0)      # normales hacia afuera
    assert np.allclose(np.linalg.norm(n, axis=1), 1.0)


def test_copia_y_dict_ida_y_vuelta():
    m = ml.generar_grupos(cubo())
    c = m.copia()
    c.vertices[0, 0] = 99
    assert m.vertices[0, 0] == 0                               # la copia es independiente
    texto = json.dumps(m.a_dict())
    r = ml.Malla.desde_dict(json.loads(texto))
    assert np.array_equal(r.vertices, m.vertices) and np.array_equal(r.caras, m.caras)
    assert np.array_equal(r.grupos, m.grupos)
    with pytest.raises(g.ErrorGeometria):
        ml.Malla.desde_dict({"formato": "otro"})


def test_validaciones_del_modelo():
    with pytest.raises(g.ErrorGeometria):
        ml.Malla(V_CUBO, [[0, 1, 99]])
    with pytest.raises(g.ErrorGeometria):
        ml.Malla(V_CUBO, F_CUBO, grupos=[0, 1])
    abierta = ml.Malla(V_CUBO, F_CUBO[:-1])
    assert not abierta.es_cerrada()
    a = ml.analizar(abierta)
    assert a["aristas_borde"] == 3 and not a["cerrada"] and a["caras"] == 11


# ---------------------------------------------------------------- E/S
def test_stl_binario_y_ascii_sin_perdida(tmp_path, esfera):
    m32 = ml.Malla(esfera.vertices.astype(np.float32).astype(float), esfera.caras)
    ml.escribir_stl(m32, tmp_path / "b.stl")
    assert mismos_triangulos(ml.leer_stl(tmp_path / "b.stl"), m32)          # binario = float32
    ml.escribir_stl(esfera, tmp_path / "a.stl", binario=False)
    r = ml.leer_stl(tmp_path / "a.stl")
    assert mismos_triangulos(r, esfera) and len(r.vertices) == len(esfera.vertices)
    assert r.volumen() == pytest.approx(esfera.volumen(), rel=1e-12)


def test_stl_unidades(tmp_path):
    ml.escribir_stl(cubo(), tmp_path / "c.stl", unidades="cm")             # 10 mm → 1 cm en el archivo
    assert ml.leer_stl(tmp_path / "c.stl").volumen() == pytest.approx(1.0)
    assert ml.leer_stl(tmp_path / "c.stl", unidades="cm").volumen() == pytest.approx(1000.0)
    assert ml.leer_stl(tmp_path / "c.stl", unidades="pulgadas").volumen() == pytest.approx(25.4 ** 3)
    with pytest.raises(g.ErrorGeometria):
        ml.leer_stl(tmp_path / "c.stl", unidades="leguas")


def test_obj_conserva_grupos(tmp_path, esfera):
    m = ml.desde_brep(g.cilindro(5, 10))
    ml.escribir_obj(m, tmp_path / "m.obj")
    r = ml.leer_obj(tmp_path / "m.obj")
    assert mismos_triangulos(r, m) and np.array_equal(r.grupos, m.grupos)
    (tmp_path / "q.obj").write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\ng tapa\nf 1/1 2/2 3/3 4/4\n")
    q = ml.leer_obj(tmp_path / "q.obj", unidades="m")                      # cuadrilátero → 2 triángulos
    assert len(q.caras) == 2 and q.area() == pytest.approx(1e6)


def test_3mf_sin_perdida_y_unidad_del_archivo(tmp_path, esfera):
    ml.escribir_3mf(esfera, tmp_path / "e.3mf")
    assert mismos_triangulos(ml.leer_3mf(tmp_path / "e.3mf"), esfera)
    ml.escribir_3mf(cubo(), tmp_path / "c.3mf", unidades="cm")
    assert ml.leer_3mf(tmp_path / "c.3mf").volumen() == pytest.approx(1000.0)   # lee unit="centimeter"
    assert ml.leer(tmp_path / "c.3mf", unidades="mm").volumen() == pytest.approx(1.0)


def test_ply_binario_y_ascii(tmp_path, esfera):
    for binario in (True, False):
        ruta = tmp_path / f"e{binario}.ply"
        ml.escribir_ply(esfera, ruta, binario=binario)
        r = ml.leer_ply(ruta)
        assert np.array_equal(r.vertices, esfera.vertices) and np.array_equal(r.caras, esfera.caras)
    cab = ("ply\nformat binary_big_endian 1.0\nelement vertex 4\nproperty float x\nproperty float y\n"
           "property float z\nproperty uchar red\nelement face 1\nproperty list uchar int vertex_indices\nend_header\n")
    cuerpo = np.zeros(4, np.dtype([("p", ">f4", 3), ("r", "u1")]))
    cuerpo["p"] = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]
    cara = np.array([4], "u1").tobytes() + np.array([0, 1, 2, 3], ">i4").tobytes()
    (tmp_path / "q.ply").write_bytes(cab.encode() + cuerpo.tobytes() + cara)
    q = ml.leer_ply(tmp_path / "q.ply")                                    # big endian + cuadrilátero
    assert len(q.caras) == 2 and q.area() == pytest.approx(1.0)


def test_leer_archivo_invalido(tmp_path):
    (tmp_path / "x.stl").write_bytes(b"cualquier cosa")
    with pytest.raises(g.ErrorGeometria):
        ml.leer_stl(tmp_path / "x.stl")
    with pytest.raises(g.ErrorGeometria):
        ml.leer(tmp_path / "x.fbx")


# ---------------------------------------------------------------- desde B-rep
def test_desde_brep_refinamientos(esfera):
    assert esfera.es_cerrada()
    assert esfera.volumen() == pytest.approx(4 / 3 * math.pi * 1000, rel=0.01)
    bajo = ml.desde_brep(g.esfera(10), refinamiento="bajo")
    alto = ml.desde_brep(g.esfera(10), refinamiento="alto")
    assert len(bajo.caras) < len(esfera.caras) < len(alto.caras)
    fina = ml.desde_brep(g.esfera(10), refinamiento="personalizado", desviacion=0.5, angulo=40)
    assert len(fina.caras) < len(bajo.caras)
    caja = ml.desde_brep(g.caja(10, 20, 30))
    assert caja.volumen() == pytest.approx(6000.0) and len(np.unique(caja.grupos)) == 6
    with pytest.raises(g.ErrorGeometria):
        ml.desde_brep(g.esfera(10), refinamiento="personalizado")


# ---------------------------------------------------------------- reparar
def test_reparar_une_vertices_duplicados():
    sopa = ml.Malla(V_CUBO[F_CUBO].reshape(-1, 3) + np.random.default_rng(1).normal(0, 1e-7, (36, 3)),
                    np.arange(36).reshape(-1, 3))
    assert len(sopa.vertices) == 36 and not sopa.es_cerrada()
    r = ml.reparar(sopa, tipo="unir_vertices", tolerancia=1e-4)
    assert len(r.vertices) == 8 and r.es_cerrada()
    assert r.volumen() == pytest.approx(1000.0, abs=1e-3)


def test_reparar_cierra_agujeros_y_orienta():
    caras = F_CUBO[:-2].copy()                    # falta una tapa entera (2 triángulos) …
    caras[3] = caras[3][[0, 2, 1]]                # … y hay una cara dada vuelta
    caras = caras[:, [0, 2, 1]]                   # y todo apunta hacia adentro
    rota = ml.Malla(V_CUBO, caras)
    a = ml.analizar(rota)
    assert not a["cerrada"] and not a["orientada"]
    r = ml.reparar(rota, tipo="cerrar_agujeros")
    assert r.es_cerrada() and r.volumen() == pytest.approx(1000.0)
    assert ml.analizar(r)["orientada"] and len(np.unique(r.grupos)) == 2  # el parche es un grupo nuevo


def test_reparar_coser_y_quitar():
    base = cubo()
    v = np.vstack([base.vertices, [[50, 50, 50], [50.001, 50, 50], [50, 50.001, 50]]])
    c = np.vstack([base.caras, base.caras[:2], [[8, 9, 10]]])        # caras dobles + cáscara diminuta
    r = ml.reparar(ml.Malla(v, c), tipo="coser_y_quitar")
    assert len(r.caras) == 12 and r.es_cerrada() and r.volumen() == pytest.approx(1000.0)
    rec = ml.reparar(ml.Malla(v, c), tipo="reconstruir", densidad=4)
    assert rec.es_cerrada() and len(rec.caras) > 12 and rec.volumen() == pytest.approx(1000.0)


def test_reparar_conserva_huecos_internos():
    hueco = ml.vaciar(cubo(), 2)
    r = ml.reparar(hueco, tipo="cerrar_agujeros")
    assert r.volumen() == pytest.approx(1000 - 6 ** 3)                     # la cáscara interior sigue invertida


# ---------------------------------------------------------------- grupos
def test_generar_y_combinar_grupos():
    m = ml.generar_grupos(cubo())
    assert len(np.unique(m.grupos)) == 6
    cil = ml.desde_brep(g.cilindro(5, 10))
    assert len(np.unique(ml.generar_grupos(ml.Malla(cil.vertices, cil.caras)).grupos)) == 3
    assert len(np.unique(ml.generar_grupos(ml.Malla(cil.vertices, cil.caras), angulo=89).grupos)) == 3
    g_abajo, g_costado = m.grupos[0], m.grupos[4]
    j = ml.combinar_grupos(m, [g_abajo, g_costado])
    assert len(np.unique(j.grupos)) == 5
    g_arriba = m.grupos[2]
    with pytest.raises(g.ErrorGeometria):
        ml.combinar_grupos(m, [g_abajo, g_arriba])                         # opuestas: no se tocan


def test_generar_grupos_tamano_minimo():
    m = ml.desde_brep(g.caja(100, 100, 1))                                 # 4 costados finitos (0,4 % c/u)
    m = ml.Malla(m.vertices, m.caras)
    assert len(np.unique(ml.generar_grupos(m).grupos)) == 6
    assert len(np.unique(ml.generar_grupos(m, tamano_minimo=0.01).grupos)) == 2


# ---------------------------------------------------------------- reducir y remallar
def test_reducir_a_la_mitad_mantiene_volumen(esfera):
    r = ml.reducir(esfera, proporcion=0.5)
    assert len(r.caras) <= len(esfera.caras) // 2 + 1
    assert r.volumen() == pytest.approx(esfera.volumen(), rel=0.05)
    assert r.es_cerrada()
    r2 = ml.reducir(esfera, objetivo_caras=500)
    assert len(r2.caras) <= 501 and r2.es_cerrada()
    assert r2.volumen() == pytest.approx(esfera.volumen(), rel=0.05)


def test_reducir_por_tolerancia_y_planos():
    fino = ml.remallar(cubo(), longitud=1.0)
    r = ml.reducir(fino, tolerancia=1e-6)                                  # caras planas: se puede reducir mucho
    assert len(r.caras) < len(fino.caras) / 5
    assert r.volumen() == pytest.approx(1000.0, rel=1e-6) and r.es_cerrada()
    with pytest.raises(g.ErrorGeometria):
        ml.reducir(fino)


def test_remallar_cubo():
    r = ml.remallar(cubo(), longitud=2.0)
    assert r.es_cerrada() and r.volumen() == pytest.approx(1000.0)
    t = ml._Topo(r.caras, len(r.vertices))
    largos = np.linalg.norm(r.vertices[t.aristas[:, 0]] - r.vertices[t.aristas[:, 1]], axis=1)
    assert 0.6 * 2 < largos.mean() < 1.4 * 2
    assert r.caja() == ((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))               # aristas vivas y esquinas intactas


def test_remallar_esfera_densidad(esfera):
    r = ml.remallar(esfera, densidad=0.25, iteraciones=3)
    assert len(r.caras) < len(esfera.caras) / 2 and r.es_cerrada()
    assert r.volumen() == pytest.approx(esfera.volumen(), rel=0.02)


# ---------------------------------------------------------------- cortar y vaciar
def test_cortar_plano_medio():
    r = ml.cortar_plano(cubo(), (0, 0, 5), (0, 0, 1))
    assert r.volumen() == pytest.approx(500.0) and r.es_cerrada()
    assert r.caja() == ((0.0, 0.0, 5.0), (10.0, 10.0, 10.0))
    otro = ml.cortar_plano(cubo(), (0, 0, 5), (0, 0, 1), invertir=True)
    assert otro.caja()[1][2] == pytest.approx(5.0)
    arriba, abajo = ml.cortar_plano(cubo(), (5, 5, 5), (1, 1, 1), tipo="partir")
    assert arriba.volumen() == pytest.approx(500.0) and abajo.volumen() == pytest.approx(500.0)
    assert arriba.es_cerrada() and abajo.es_cerrada()
    caras = ml.cortar_plano(cubo(), (0, 0, 5), (0, 0, 1), tipo="partir_caras")
    assert caras.volumen() == pytest.approx(1000.0) and len(caras.caras) > 12 and caras.es_cerrada()
    abierta = ml.cortar_plano(cubo(), (0, 0, 5), (0, 0, 1), rellenar=False)
    assert not abierta.es_cerrada()
    with pytest.raises(g.ErrorGeometria):
        ml.cortar_plano(cubo(), (0, 0, 50), (0, 0, 1), tipo="partir")


def test_cortar_esfera_y_cuerpo_hueco(esfera):
    r = ml.cortar_plano(esfera, (0, 0, 0), (0.3, -0.2, 1))
    assert r.volumen() == pytest.approx(esfera.volumen() / 2, rel=1e-3) and r.es_cerrada()
    hueco = ml.vaciar(cubo(), 1)                                           # tapa con agujero (anillo)
    mitad = ml.cortar_plano(hueco, (0, 0, 5), (0, 0, 1))
    assert mitad.es_cerrada() and mitad.volumen() == pytest.approx(488.0 / 2)


def test_vaciar():
    r = ml.vaciar(cubo(), 1.0)
    assert r.volumen() == pytest.approx(1000 - 8 ** 3) and r.es_cerrada()
    assert ml.analizar(r)["cascaras"] == 2
    with pytest.warns(RuntimeWarning):
        ml.vaciar(cubo(), 6.0)
    with pytest.raises(g.ErrorGeometria):
        ml.vaciar(ml.Malla(V_CUBO, F_CUBO[:-1]), 1.0)


# ---------------------------------------------------------------- combinar
@pytest.mark.parametrize("motor", ["manifold", "brep"])
def test_combinar_booleanas(motor):
    if motor == "manifold" and ml._manifold is None:
        pytest.skip("manifold3d no está instalado")
    a, b = cubo(), cubo((5, 5, 5))
    esperado = {"unir": 1875.0, "cortar": 875.0, "intersecar": 125.0}
    for op, vol in esperado.items():
        r = ml.combinar([a, b], operacion=op, motor=motor)
        assert r.volumen() == pytest.approx(vol) and r.es_cerrada()
    with pytest.raises(g.ErrorGeometria):
        ml.combinar([a, ml.Malla(V_CUBO, F_CUBO[:-1])], motor=motor)


def test_combinar_fusionar_y_grupos():
    a, b = ml.generar_grupos(cubo()), ml.generar_grupos(cubo((5, 5, 5)))
    f = ml.combinar([a, b], operacion="fusionar")
    assert len(f.caras) == 24 and f.volumen() == pytest.approx(2000.0)
    assert len(np.unique(f.grupos)) == 12
    if ml._manifold is not None:
        u = ml.combinar([a, b], operacion="unir")
        assert len(np.unique(u.grupos)) == 12                               # 6 + 6 caras planas conservadas


# ---------------------------------------------------------------- suavizar, normales, separar, escalar, alinear
def test_suavizar_taubin_no_encoge(esfera):
    rng = np.random.default_rng(0)
    ruidosa = ml.Malla(esfera.vertices * (1 + rng.normal(0, 0.01, (len(esfera.vertices), 1))), esfera.caras)
    r = ml.suavizar(ruidosa, intensidad=0.8, iteraciones=10)
    radio = np.linalg.norm(r.vertices, axis=1)
    assert radio.std() < 0.5 * np.linalg.norm(ruidosa.vertices, axis=1).std()
    assert r.volumen() == pytest.approx(esfera.volumen(), rel=0.03)
    assert np.array_equal(ml.suavizar(ruidosa, intensidad=0).vertices, ruidosa.vertices)


def test_invertir_normales():
    assert ml.invertir_normales(cubo()).volumen() == pytest.approx(-1000.0)
    r = ml.invertir_normales(cubo(), caras=[0])
    assert not r.es_cerrada() and not ml.analizar(r)["orientada"]
    m = ml.generar_grupos(cubo())
    assert not ml.invertir_normales(m, grupos=[m.grupos[0]]).es_cerrada()


def test_separar_dos_cubos():
    dos = ml.combinar([cubo(), cubo((20, 0, 0))], operacion="fusionar")
    partes = ml.separar(dos)
    assert len(partes) == 2
    assert [p.volumen() for p in partes] == pytest.approx([1000.0, 1000.0])
    assert all(p.es_cerrada() and len(p.vertices) == 8 for p in partes)
    m = ml.generar_grupos(cubo())
    assert len(ml.separar(m, tipo="grupos")) == 6
    sel = ml.separar(m, tipo="grupos", grupos=[m.grupos[0]])
    assert [len(p.caras) for p in sel] == [2, 10]


def test_escalar():
    r = ml.escalar(cubo(), 2, 1, 1, punto=(10, 0, 0))
    assert r.volumen() == pytest.approx(2000.0) and r.caja()[0] == (-10.0, 0.0, 0.0)
    espejo = ml.escalar(cubo(), -1, 1, 1)
    assert espejo.volumen() == pytest.approx(1000.0) and espejo.es_cerrada()
    assert ml.escalar(cubo(), 0.5).volumen() == pytest.approx(125.0)
    with pytest.raises(g.ErrorGeometria):
        ml.escalar(cubo(), 0)


def test_alinear_a_plano():
    m = cubo((3, 4, 20))
    r = ml.alinear_a_plano(m, [4, 5], g.Plano("XY"))                       # cara del frente (normal -Y) al suelo
    assert r.volumen() == pytest.approx(1000.0)
    n = r.normales_caras()[[4, 5]]
    assert np.allclose(n, [0, 0, -1])
    assert r.caja()[0][2] == pytest.approx(0.0) and r.caja()[1][2] == pytest.approx(10.0)
    f = ml.alinear_a_plano(m, [4, 5], g.Plano("XY"), invertir=True)
    assert np.allclose(f.normales_caras()[[4, 5]], [0, 0, 1]) and f.caja()[1][2] == pytest.approx(0.0)


def test_borrar_y_rellenar():
    m = ml.remallar(cubo(), longitud=2.5)
    arriba = np.flatnonzero(m.triangulos().mean(1)[:, 2] > 9.99)
    minimo = ml.borrar_y_rellenar(m, arriba, tipo="minimo")
    assert minimo.es_cerrada() and minimo.volumen() == pytest.approx(1000.0)
    uniforme = ml.borrar_y_rellenar(m, arriba, tipo="uniforme")
    assert uniforme.es_cerrada() and uniforme.volumen() == pytest.approx(1000.0)
    assert len(uniforme.caras) > len(minimo.caras)
    with pytest.raises(g.ErrorGeometria):
        ml.borrar_y_rellenar(m, np.arange(len(m.caras)))


# ---------------------------------------------------------------- a sólido
def test_a_brep_cubo_facetado_y_prismatico():
    s = ml.a_brep(cubo())
    assert g.es_valida(s) and g.volumen(s) == pytest.approx(1000.0) and len(g.caras(s)) == 12
    assert len(g.solidos(s)) == 1
    p = ml.a_brep(ml.desde_brep(g.caja(10, 10, 10)), metodo="prismatico")
    assert g.es_valida(p) and g.volumen(p) == pytest.approx(1000.0) and len(g.caras(p)) == 6


def test_a_brep_hueco_abierto_y_limite():
    s = ml.a_brep(ml.vaciar(cubo(), 1.0))
    assert g.es_valida(s) and g.volumen(s) == pytest.approx(488.0)
    sup = ml.a_brep(ml.Malla(V_CUBO, F_CUBO[:-2]))
    assert g.es_valida(sup) and not g.solidos(sup) and g.area(sup) == pytest.approx(500.0)
    dos = ml.a_brep(ml.combinar([cubo(), cubo((20, 0, 0))], operacion="fusionar"))
    assert len(g.solidos(dos)) == 2 and g.volumen(dos) == pytest.approx(2000.0)
    with pytest.raises(g.ErrorGeometria, match="máximo"):
        ml.a_brep(cubo(), max_triangulos=10)


def test_3mf_transformadas_y_componentes(tmp_path):
    import zipfile
    modelo = (f'<?xml version="1.0"?><model unit="centimeter" xmlns="{ml._NS_3MF}"><resources>'
              '<object id="1" type="model"><mesh><vertices>'
              + "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in (V_CUBO / 10).tolist())
              + '</vertices><triangles>'
              + "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in F_CUBO.tolist())
              + '</triangles></mesh></object>'
              '<object id="2" type="model"><components><component objectid="1" transform="1 0 0 0 1 0 0 0 1 5 0 0"/>'
              '</components></object></resources>'
              '<build><item objectid="1"/><item objectid="2" transform="-1 0 0 0 1 0 0 0 1 0 10 0"/></build></model>')
    with zipfile.ZipFile(tmp_path / "t.3mf", "w") as z:
        z.writestr("3D/3dmodel.model", modelo)
    m = ml.leer_3mf(tmp_path / "t.3mf")                                    # 2 cubos de 10 mm, uno espejado
    partes = ml.separar(m)
    assert len(partes) == 2 and all(p.es_cerrada() for p in partes)
    assert [p.volumen() for p in partes] == pytest.approx([1000.0, 1000.0])
    assert partes[1].caja() == ((-60.0, 100.0, 0.0), (-50.0, 110.0, 10.0))


def test_obj_indices_negativos(tmp_path):
    (tmp_path / "n.obj").write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\n")
    m = ml.leer_obj(tmp_path / "n.obj")
    assert m.caras.tolist() == [[0, 1, 2]] and m.area() == pytest.approx(0.5)


def test_remallar_malla_abierta():
    abierta = ml.Malla(V_CUBO, F_CUBO[:-2])                                # sin la tapa x=0
    fija = ml.remallar(abierta, longitud=2.0)
    borde = lambda m: sorted(map(tuple, m.vertices[np.unique(ml._Topo(m.caras, len(m.vertices)).libres())]))
    assert borde(fija) == borde(abierta)                                   # borde intacto (mismos 4 vértices)
    libre = ml.remallar(abierta, longitud=2.0, preservar_bordes=False)
    assert len(borde(libre)) > 4 and libre.area() == pytest.approx(500.0)


# ---------------------------------------------------------------- avisos de volumen y memoria (pruebas de uso)
def tubo(R=10.0, r=8.0, alto=30.0, n=32):
    """Tubo de pared fina (2 mm) teselado como un STL de CAD: 256 triángulos, los de las paredes de 30 × 2 mm."""
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    anillo = lambda radio, z: np.c_[radio * np.cos(a), radio * np.sin(a), np.full(n, z)]  # noqa: E731
    eb, et, ib, it = 0, n, 2 * n, 3 * n
    caras = []
    for i in range(n):
        j = (i + 1) % n
        caras += [[eb + i, eb + j, et + j], [eb + i, et + j, et + i], [ib + i, it + j, ib + j], [ib + i, it + i, it + j],
                  [et + i, et + j, it + j], [et + i, it + j, it + i], [eb + i, ib + j, eb + j], [eb + i, ib + i, ib + j]]
    return ml.Malla(np.vstack([anillo(R, 0), anillo(R, alto), anillo(r, 0), anillo(r, alto)]), caras)


def test_remallar_pared_fina_conserva_el_volumen():
    """Prueba de uso: remallar una pared de 2 mm cambiaba el volumen −5,4 % sin avisar. La causa era proyectar sobre
    el triángulo de CENTRO más cercano: en las astillas (30 × 2 mm) caía sobre la otra pared, a 2 mm."""
    tb = tubo()
    assert tb.es_cerrada() and tb.volumen() == pytest.approx(3371.16, abs=0.01)
    pared = np.flatnonzero(np.abs(tb.normales_caras()[:, 2]) < 0.1)
    puntos = np.einsum("j,ijk->ik", [0.8, 0.1, 0.1], tb.triangulos()[pared])       # 128 puntos sobre las paredes
    assert ml._Referencia(tb.vertices, tb.caras, largo=2.0).mas_cercano(puntos)[0].max() < 1e-9
    with warnings.catch_warnings():
        warnings.simplefilter("error", ml.AvisoMalla)
        r = ml.remallar(tb, longitud=2.0)
    assert r.es_cerrada() and len(r.caras) < 2500
    assert r.volumen() == pytest.approx(tb.volumen(), rel=0.005) and r.area() == pytest.approx(tb.area(), rel=0.004)


def test_remallar_avisa_si_el_volumen_cambia_mas_del_1_por_ciento(esfera):
    """Con densidad baja las aristas del tubo miden más de 11 mm contra una pared de 2 mm: el volumen cambia varios por
    ciento. El número exacto depende del orden en que se procesan aristas de igual largo (por eso el orden es estable
    y redondeado: antes daba +10,9 % en Windows y −0,9 % en un procesador con AVX-512)."""
    with pytest.warns(ml.AvisoMalla, match=r"Remallar cambió el volumen un [+-]\d+,\d % \(aristas de 12 mm\): la "
                                            r"densidad es baja .*paredes finas.*subí la densidad"):
        r = ml.remallar(tubo(), densidad=0.9)
    assert r.es_cerrada() and abs(r.volumen() / tubo().volumen() - 1) > 0.03
    with pytest.warns(ml.AvisoMalla, match=r"bajá la longitud"):
        ml.remallar(tubo(), longitud=12.0)
    with warnings.catch_warnings():                                        # −0,9 % y 0 %: sin aviso
        warnings.simplefilter("error", ml.AvisoMalla)
        ml.remallar(esfera, densidad=0.25, iteraciones=3)
        ml.remallar(cubo(), longitud=2.0)
        ml.remallar(ml.Malla(V_CUBO, F_CUBO[:-2]), longitud=2.0)          # abierta: no tiene volumen


def test_suavizar_pondera_por_largo_de_arista(esfera):
    """Prueba de uso: Suavizar 5 iteraciones subía el volumen +0,65 % de una botella reducida. Con pesos iguales, un
    vértice unido por una arista larga (Reducir deja caras de 64 mm) viajaba hasta 9 mm; en el tubo, las aristas de
    30 mm acortaban el cuerpo de 0..30 a 2,45..27,55. Con pesos 1/largo el desplazamiento queda a la escala de las
    aristas cortas. Lo que sigue cambiando el volumen es redondear las aristas vivas: si pasa del 1 %, avisa."""
    tb = tubo()
    with pytest.warns(ml.AvisoMalla, match=r"Suavizar cambió el volumen un -2\d,\d %: redondea las aristas vivas"):
        r = ml.suavizar(tb, intensidad=0.5, iteraciones=5)
    (_, _, z0), (_, _, z1) = r.caja()
    assert z0 == pytest.approx(0.0, abs=0.1) and z1 == pytest.approx(30.0, abs=0.1)
    assert np.linalg.norm(r.vertices - tb.vertices, axis=1).max() < 0.5
    with warnings.catch_warnings():
        warnings.simplefilter("error", ml.AvisoMalla)
        lisa = ml.suavizar(esfera, intensidad=0.5, iteraciones=5)
    assert lisa.volumen() == pytest.approx(esfera.volumen(), rel=0.01)


def test_timeline_avisa_y_no_recalcula_reducir_ni_remallar_si_la_entrada_no_cambio(monkeypatch):
    """Prueba de uso: reducir 74.252 triángulos tarda ~9 s y remallar ~7 s, y se rehacían en cada recálculo
    (deshacer, editar un paso anterior, vista previa y Aceptar). Ahora se recuerdan por contenido."""
    from omnicad.timeline import ops_malla
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.ops_malla import OpInsertarMalla, OpReducirMalla, OpRemallar, OpVaciadoMalla
    ops_malla._MEMORIA.clear()
    llamadas = {"remallar": 0, "reducir": 0}
    for nombre in llamadas:
        original = getattr(ml, nombre)

        def contar(*a, _nombre=nombre, _original=original, **k):
            llamadas[_nombre] += 1
            return _original(*a, **k)
        monkeypatch.setattr(ml, nombre, contar)
    doc = Documento()
    doc.agregar(OpInsertarMalla(doc.nuevo_id(), "tubo", archivo="tubo", datos=tubo().a_dict()))
    res = doc.agregar(OpRemallar(doc.nuevo_id(), cuerpos=["op1.c1"], densidad="0.9"))
    assert res.estado == "aviso" and "cambió el volumen un" in res.mensaje
    vol_remallado = doc.estado_final.cuerpos["op1.c1"].forma.volumen()
    assert llamadas["remallar"] == 1
    doc.recalcular(0)
    assert llamadas["remallar"] == 1                                       # misma entrada: no se rehace …
    assert doc.resultados[1].estado == "aviso" and "volumen" in doc.resultados[1].mensaje     # … y sigue avisando
    assert doc.estado_final.cuerpos["op1.c1"].forma.volumen() == pytest.approx(vol_remallado, rel=1e-9)
    doc.reemplazar("op2", OpRemallar("op2", cuerpos=["op1.c1"], densidad="5"))
    assert llamadas["remallar"] == 2 and doc.resultados[1].estado == "ok"  # otra densidad: se calcula
    doc.agregar(OpReducirMalla(doc.nuevo_id(), cuerpos=["op1.c1"], proporcion="0.5"))
    doc.recalcular(0)
    assert llamadas == {"remallar": 2, "reducir": 1}
    doc.reemplazar("op3", OpReducirMalla("op3", cuerpos=["op1.c1"], proporcion="0.4"))
    assert llamadas == {"remallar": 2, "reducir": 2}
    res = doc.agregar(OpVaciadoMalla(doc.nuevo_id(), cuerpos=["op1.c1"], espesor="20 mm"))
    assert res.estado == "aviso" and res.mensaje.count("Vaciar: con 20") == 1                # un solo aviso
