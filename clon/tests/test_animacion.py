# -*- coding: utf-8 -*-
"""Espacio ANIMACIÓN: rotaciones e interpolación, acciones de un guion gráfico (transformar, explosión, mostrar/ocultar,
vista, anotación, restaurar), invertir, persistencia y Publicar video (GIF y secuencia PNG). La ventana corre offscreen,
sin OpenGL: los cuadros del video salen del render de CPU (lo gráfico con OpenGL se ve en
evidencias/capturas/animacion.png)."""
import json
import math
import os

import numpy as np
import pytest

from omnicad.ui import animacion as an


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _centro(fr, cid, centros):
    M = fr["matrices"][cid]
    return M[:3, :3] @ centros[cid] + M[:3, 3]


# ---------------------------------------------------------------- rotaciones e interpolación
def test_rotaciones():
    R = an.matriz_rotacion([0, 0, 90])
    assert R @ np.array([1.0, 0, 0]) == pytest.approx([0, 1, 0], abs=1e-12)
    rng = np.random.default_rng(3)
    for _ in range(5):
        rv = rng.uniform(-170, 170, 3) / 2
        assert an.vector_rotacion(an.matriz_rotacion(rv)) == pytest.approx(rv, abs=1e-7)
    assert an.euler_a_giro(90, 0, 0) == pytest.approx([90, 0, 0])
    # dos ejes: primero X, después Z
    Rx, Rz = an.matriz_rotacion([30, 0, 0]), an.matriz_rotacion([0, 0, 45])
    assert an.matriz_rotacion(an.euler_a_giro(30, 0, 45)) == pytest.approx(Rz @ Rx, abs=1e-9)
    assert an.vector_rotacion(an.matriz_rotacion([180, 0, 0])) == pytest.approx([180, 0, 0], abs=1e-6)


def test_suavizado_y_slerp():
    assert [an.suavizado(f) for f in (0, 0.5, 1, 2)] == pytest.approx([0, 0.5, 1, 1])
    R = an.slerp(np.identity(3), an.matriz_rotacion([0, 0, 90]), 0.5)
    assert an.vector_rotacion(R) == pytest.approx([0, 0, 45], abs=1e-9)
    A = np.identity(4)
    B = an.matriz_movimiento((10, 0, 0), (0, 0, 20), (0, 0, 90))
    m = an.interpolar_matriz(A, B, 0.5, (10, 0, 0))
    assert m[:3, :3] @ np.array([10, 0, 0.0]) + m[:3, 3] == pytest.approx([10, 0, 10])   # el centro, en línea recta


# ---------------------------------------------------------------- acciones
CENTROS = {"a": np.array([0.0, 0.0, 0.0]), "b": np.array([100.0, 0.0, 0.0])}


def test_transformar_mueve_y_gira_alrededor_del_centro():
    g = an.Guion()
    g.agregar({"tipo": "transformar", "cuerpos": ["a"], "traslacion": [10, 0, 0], "giro": [0, 0, 0], "inicio": 1,
               "duracion": 2})
    g.agregar({"tipo": "transformar", "cuerpos": ["b"], "traslacion": [0, 0, 0], "giro": [0, 0, 90], "inicio": 0,
               "duracion": 1})
    assert g.duracion == pytest.approx(3.0)
    assert _centro(an.evaluar(g, 0.5, CENTROS), "a", CENTROS) == pytest.approx([0, 0, 0])   # aún no empezó
    assert _centro(an.evaluar(g, 2.0, CENTROS), "a", CENTROS) == pytest.approx([5, 0, 0])   # a la mitad
    fin = an.evaluar(g, 3.0, CENTROS)
    assert _centro(fin, "a", CENTROS) == pytest.approx([10, 0, 0])
    Mb = fin["matrices"]["b"]
    assert _centro(fin, "b", CENTROS) == pytest.approx([100, 0, 0])       # gira sobre su propio centro
    assert Mb[:3, :3] @ np.array([110.0, 0, 0]) + Mb[:3, 3] == pytest.approx([100, 10, 0])


def test_explosion_un_paso_y_secuencial():
    despl, orden = an.calcular_explosion(CENTROS, [["a"], ["b"]], 30.0)
    assert despl["a"] == pytest.approx([-30, 0, 0]) and despl["b"] == pytest.approx([30, 0, 0])
    assert orden == [["a"], ["b"]]
    g = an.Guion()
    g.agregar({"tipo": "explosion", "desplazamientos": despl, "orden": orden, "secuencial": True, "inicio": 0,
               "duracion": 2})
    mitad = an.evaluar(g, 1.0, CENTROS)
    assert _centro(mitad, "a", CENTROS) == pytest.approx([-30, 0, 0])        # la primera pieza ya terminó
    assert _centro(mitad, "b", CENTROS) == pytest.approx([100, 0, 0])        # la segunda todavía no arrancó
    g.acciones[0]["secuencial"] = False
    assert _centro(an.evaluar(g, 1.0, CENTROS), "b", CENTROS) == pytest.approx([115, 0, 0])
    # una sola pieza (en el centro): sube por +Z
    solo, _o = an.calcular_explosion({"c": np.zeros(3)}, [["c"]], 12.0)
    assert solo["c"] == pytest.approx([0, 0, 12])


def test_grupos_de_explosion_por_componente():
    class C:
        def __init__(self, comp):
            self.componente = comp

    class E:
        cuerpos = {"x": C(""), "y": C("k1"), "z": C("k1"), "w": C("k2")}
        componentes = {"k1": {"padre": ""}, "k2": {"padre": "k1"}}
    uno = an.grupos_explosion(E(), None, "uno")
    assert sorted(sorted(g) for g in uno) == [["w", "y", "z"], ["x"]]       # k2 cuelga de k1: van juntos
    assert sorted(an.grupos_explosion(E(), None, "todos")) == [["w"], ["x"], ["y"], ["z"]]


def test_mostrar_ocultar_con_y_sin_transicion():
    g = an.Guion()
    g.agregar({"tipo": "visibilidad", "cuerpos": ["a"], "visible": False, "inicio": 1, "duracion": 2})
    g.agregar({"tipo": "visibilidad", "cuerpos": ["b"], "visible": False, "inicio": 1, "duracion": 0})
    assert an.evaluar(g, 0.5, CENTROS)["opacidad"] == {"a": 1.0, "b": 1.0}
    op = an.evaluar(g, 2.0, CENTROS)["opacidad"]
    assert op["a"] == pytest.approx(0.5) and op["b"] == 0.0
    assert an.evaluar(g, 3.0, CENTROS)["opacidad"]["a"] == 0.0


def test_vista_interpola_la_camara():
    c0 = {"R": np.identity(3).tolist(), "objetivo": [0, 0, 0], "distancia": 100.0, "fov": 40.0}
    R1 = an.matriz_rotacion([0, 0, 90]).T
    c1 = {"R": R1.tolist(), "objetivo": [10, 0, 0], "distancia": 400.0, "fov": 40.0}
    g = an.Guion(inicial={"camara": c0})
    g.agregar({"tipo": "vista", "camara": c1, "inicio": 1, "duracion": 1})
    assert an.evaluar(g, 0.0, {})["camara"]["distancia"] == pytest.approx(100.0)
    mitad = an.evaluar(g, 1.5, {})["camara"]
    assert mitad["distancia"] == pytest.approx(200.0)                    # geométrica: √(100·400)
    assert mitad["objetivo"] == pytest.approx([5, 0, 0])
    R = np.asarray(mitad["R"])
    assert R @ R.T == pytest.approx(np.identity(3), abs=1e-9)
    assert np.allclose(an.evaluar(g, 5.0, {})["camara"]["R"], R1)


def test_anotacion_sigue_al_cuerpo():
    g = an.Guion()
    g.agregar({"tipo": "transformar", "cuerpos": ["a"], "traslacion": [0, 0, 50], "inicio": 0, "duracion": 2})
    g.agregar({"tipo": "anotacion", "texto": "Tapa", "punto": [1, 2, 3], "cuerpo": "a", "inicio": 0.5, "duracion": 1})
    g.agregar({"tipo": "anotacion", "texto": "Fija", "punto": [7, 7, 7], "cuerpo": "", "inicio": 0, "duracion": 0})
    assert [n["texto"] for n in an.evaluar(g, 0.2, CENTROS)["notas"]] == ["Fija"]
    notas = {n["texto"]: n for n in an.evaluar(g, 1.0, CENTROS)["notas"]}
    assert notas["Tapa"]["punto"] == pytest.approx([1, 2, 28]) and notas["Fija"]["punto"] == pytest.approx([7, 7, 7])
    assert [n["texto"] for n in an.evaluar(g, 1.8, CENTROS)["notas"]] == ["Fija"]   # «Fija» dura hasta el final
    assert an.evaluar(g, 2.1, CENTROS)["notas"] == []


def test_restaurar_vuelve_a_la_posicion_del_diseno():
    g = an.Guion()
    g.agregar({"tipo": "transformar", "cuerpos": ["a"], "traslacion": [20, 0, 0], "giro": [0, 0, 60], "inicio": 0,
               "duracion": 1})
    g.agregar({"tipo": "restaurar", "cuerpos": ["a"], "inicio": 1, "duracion": 1})
    assert an.evaluar(g, 2.0, CENTROS)["matrices"]["a"] == pytest.approx(np.identity(4), abs=1e-9)
    assert _centro(an.evaluar(g, 1.5, CENTROS), "a", CENTROS) == pytest.approx([10, 0, 0])


def test_invertir_reproduce_al_reves():
    g = an.Guion("G")
    despl, orden = an.calcular_explosion(CENTROS, [["a"], ["b"]], 25.0)
    g.agregar({"tipo": "explosion", "desplazamientos": despl, "orden": orden, "secuencial": True, "inicio": 0,
               "duracion": 2})
    g.agregar({"tipo": "transformar", "cuerpos": ["b"], "traslacion": [0, 5, 0], "giro": [0, 30, 0], "inicio": 2,
               "duracion": 1})
    g.agregar({"tipo": "visibilidad", "cuerpos": ["a"], "visible": False, "inicio": 3, "duracion": 0.5})
    inv = an.invertir(g, CENTROS)
    D = g.duracion
    assert inv.duracion == pytest.approx(D)
    for t in (0.0, 0.4, 1.3, 2.2, 2.9, 3.5):
        a, b = an.evaluar(g, D - t, CENTROS), an.evaluar(inv, t, CENTROS)
        for c in CENTROS:
            assert b["matrices"][c] == pytest.approx(a["matrices"][c], abs=1e-6)
            assert b["opacidad"][c] == pytest.approx(a["opacidad"][c], abs=1e-6)


def test_guion_a_dict_ida_y_vuelta():
    g = an.Guion("Armado", inicial={"matrices": {"a": an.matriz_movimiento((0, 0, 0), (1, 2, 3), (0, 0, 10))},
                                    "opacidad": {"b": 0.0}})
    g.agregar({"tipo": "transformar", "cuerpos": ["a", "b"], "traslacion": [0, 0, 9], "inicio": 0.5, "duracion": 1.5})
    g.agregar({"tipo": "anotacion", "texto": "Hola", "punto": [0, 0, 0], "inicio": 1, "duracion": 0})
    datos = json.loads(json.dumps(g.a_dict()))
    h = an.Guion.desde_dict(datos)
    assert h.nombre == "Armado" and [a["id"] for a in h.acciones] == [a["id"] for a in g.acciones]
    for t in (0, 1, 2):
        x, y = an.evaluar(g, t, CENTROS), an.evaluar(h, t, CENTROS)
        assert all(np.allclose(x["matrices"][c], y["matrices"][c]) for c in CENTROS)
        assert x["opacidad"] == y["opacidad"]
    with pytest.raises(an.ErrorGeometria):
        g.agregar({"tipo": "bailar"})


def test_tiempos_y_notas_en_la_imagen():
    ts = an.tiempos(2.0, 15)
    assert len(ts) == 31 and ts[0] == 0.0 and ts[-1] == pytest.approx(2.0)
    assert an.tiempos(0.0, 10) == [0.0]
    cam = {"R": np.identity(3).tolist(), "objetivo": [0, 0, 0], "distancia": 100.0, "fov": 40.0}
    (x, y, texto), = an.proyectar_notas([{"punto": [0, 0, 0], "texto": "C"}], cam, 200, 100)
    assert (x, y, texto) == (pytest.approx(100), pytest.approx(50), "C")
    img = np.full((100, 200, 3), 128, np.uint8)
    salida = an.dibujar_notas(img, [(x, y, "Centro")])
    assert salida.shape == img.shape and (salida != 128).any()


# ---------------------------------------------------------------- ventana
@pytest.fixture()
def ventana(qapp):
    from omnicad.ejemplo import crear_documento_ejemplo
    v = an.VentanaAnimacion(crear_documento_ejemplo())
    v.lienzo.resize(320, 240)
    v.lienzo.encuadrar()
    yield v
    v.close()


def test_ventana_aplica_el_cuadro_al_lienzo(ventana):
    v = ventana
    cid = list(v.lienzo.objetos)[0]
    v.seleccionar([cid])
    a = v.agregar_accion({"tipo": "transformar", "cuerpos": [cid], "traslacion": [0, 0, 40], "inicio": 0,
                          "duracion": 1})
    assert a["id"] and v.guion.duracion == pytest.approx(1.0)
    v.ir_a(1.0)
    assert v.lienzo.transformaciones[cid][:3, 3] == pytest.approx([0, 0, 40])
    v.ir_a(0.0)
    assert np.allclose(v.lienzo.transformaciones[cid], np.identity(4))
    ex = v.agregar_accion({"tipo": "explosion", "nivel": "todos", "distancia": 30.0, "inicio": 1, "duracion": 1,
                           "cuerpos": []})
    assert set(ex["desplazamientos"]) == set(v.lienzo.objetos)
    assert max(np.linalg.norm(d) for d in ex["desplazamientos"].values()) == pytest.approx(30.0)
    v.cambiar_tiempos(ex["id"], 2.0, 0.5)
    assert v.guion.duracion == pytest.approx(2.5)
    v.eliminar_accion(ex["id"])
    assert len(v.guion.acciones) == 1


def test_ventana_guiones_y_persistencia(ventana):
    v = ventana
    cid = list(v.lienzo.objetos)[0]
    v.agregar_accion({"tipo": "transformar", "cuerpos": [cid], "traslacion": [5, 0, 0], "inicio": 0, "duracion": 1})
    v.crear_anotacion("Pieza", v.centros[cid], cid, inicio=0, duracion=0)
    g2 = v.nuevo_guion("continuar")
    assert v.actual == 1 and g2.inicial["matrices"][cid][:3, 3] == pytest.approx([5, 0, 0])
    v.copiar_guion(0)
    assert [g.nombre for g in v.guiones][:2] == ["Guion gráfico1", "Guion gráfico1 (copia)"]
    datos = json.loads(json.dumps(v.a_dict()))
    assert datos["version"] == 1 and len(datos["guiones"]) == 3
    v.desde_dict({"guiones": [], "actual": 5})
    assert len(v.guiones) == 1 and v.guion.acciones == []
    v.desde_dict(datos)
    assert len(v.guiones) == 3 and v.actual == datos["actual"]
    assert v.guiones[0].acciones[1]["tipo"] == "anotacion"
    v.invertir_guion(0)
    assert v.guiones[0].inicial["matrices"][cid][:3, 3] == pytest.approx([5, 0, 0])


def test_publicar_gif_y_secuencia_png(ventana, tmp_path):
    from PIL import Image
    v = ventana
    cid = list(v.lienzo.objetos)[0]
    v.agregar_accion({"tipo": "transformar", "cuerpos": [cid], "traslacion": [0, 0, 30], "giro": [0, 0, 45],
                      "inicio": 0, "duracion": 1})
    ruta = tmp_path / "anim.gif"
    archivos = v.publicar(str(ruta), "gif", 48, 36, 4, "actual", "cpu", "lienzo")
    assert archivos == [str(ruta)]
    gif = Image.open(ruta)
    assert gif.n_frames == len(an.tiempos(1.0, 4)) == 5 and gif.size == (48, 36)
    gif.seek(0)
    primero = np.asarray(gif.convert("RGB"))
    gif.seek(4)
    ultimo = np.asarray(gif.convert("RGB"))
    assert np.abs(primero.astype(int) - ultimo.astype(int)).sum() > 0      # algo se movió
    carpeta = tmp_path / "cuadros"
    pngs = v.publicar(str(carpeta), "png", 32, 24, 2, "documento", "cpu", "render")
    assert len(pngs) == 3 and all(os.path.exists(p) for p in pngs)
    assert Image.open(pngs[0]).size == (32, 24)
    assert math.isclose(v.t, 0.0)


def test_comandos_de_la_cinta_con_dialogo(ventana, monkeypatch):
    from PySide6.QtWidgets import QDialog
    monkeypatch.setattr(an.DialogoAccion, "exec", lambda self: QDialog.Accepted)
    v = ventana
    assert v.comando("transformar") is None                      # sin selección no hace nada
    cid = list(v.lienzo.objetos)[0]
    v.seleccionar([cid])
    v.ir_a(0.5)
    a = v.comando("transformar")
    assert a["tipo"] == "transformar" and a["cuerpos"] == [cid] and a["inicio"] == pytest.approx(0.5)
    oc = v.comando("visibilidad")
    assert oc["visible"] is False and oc["duracion"] == 0.0     # por defecto oculta, instantáneo
    ex = v.comando("explosion", nivel="todos")
    assert ex["nivel"] == "todos" and ex["distancia"] > 0
    vista = v.comando("vista")
    assert vista["camara"]["distancia"] > 0 and v.guion.inicial["camara"] is not None
    assert len(v.guion.acciones) == 4 and v.linea.pistas.barras()
    for tipo in an.TIPOS:                                        # los diálogos de editar se arman con cada tipo
        d = an.DialogoAccion(v, tipo, {"inicio": 1.0, "duracion": 2.0, "traslacion": (1, 2, 3), "giro": (0, 0, 30)},
                             1, nuevo=False)
        valores = d.valores()
        assert valores["inicio"] == pytest.approx(1.0)
    pub = an.DialogoPublicar(v, (300, 200), "x.gif")
    pub.formato.setCurrentIndex(1)
    assert pub.valores()["formato"] == "png" and not pub.valores()["ruta"].endswith(".gif")
