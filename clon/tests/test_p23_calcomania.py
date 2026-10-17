"""P23d: cada control modifica la textura, la receta o su vista previa; Cancelar restaura."""
import numpy as np
import pytest
from PIL import Image

from omnicad import api
from omnicad.nucleo import calcomanias, geometria as geo
from omnicad.timeline.ops_insertar import OpLienzo
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos.insertar import Calcomania
from test_p23_navegador import ventana as ventana, v as v


@pytest.fixture
def imagen(tmp_path):
    ruta = tmp_path / "imagen.png"
    img = Image.new("RGBA", (80, 40), "white")
    img.paste("red", (0, 0, 20, 40))
    img.save(ruta)
    return ruta


def llamar(s, nombre, **args):
    r = api.llamar(s, nombre, args)
    assert r["ok"], r
    return r["result"]


@pytest.fixture
def decal(imagen):
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=30, height=20)
    llamar(s, "set_decal", image=str(imagen), face=">Z")
    return s, s.doc.operaciones[-1].id


def test_ajustar_cara_sin_deformar_y_conservar_solido(decal):
    s, ident = decal
    d = s.doc.estado_final.lienzos[ident]
    assert d["ancho"] == pytest.approx(36)
    assert d["alto"] == pytest.approx(18)
    c = next(iter(s.doc.estado_final.cuerpos.values()))
    assert geo.es_valida(c.forma) and geo.volumen(c.forma) == pytest.approx(24000)


@pytest.mark.parametrize("parametro,valor,clave", [("width", 12, "ancho"), ("height", 7, "alto"),
    ("x", 3, "dx"), ("y", -4, "dy"), ("angle", 45, "angulo"), ("opacity", 30, "opacidad"),
    ("flip_h", True, "voltear"), ("flip_v", True, "voltear_v")])
def test_opciones_decal_cambian_estado_y_uv(decal, parametro, valor, clave):
    s, ident = decal
    antes = s.doc.estado_final.lienzos[ident]["malla"]["uv"].copy()
    llamar(s, "set_decal", feature=ident, **{parametro: valor})
    d = s.doc.estado_final.lienzos[ident]
    assert d[clave] == pytest.approx(valor / 100 if parametro == "opacity" else valor)
    if parametro != "opacity":
        assert not np.allclose(antes, d["malla"]["uv"])
    if parametro == "height":
        assert d["ancho"] == pytest.approx(14)


def test_relacion_independiente_casilla_opacidad_imagen_y_cara(decal, imagen, tmp_path):
    s, ident = decal
    llamar(s, "set_decal", feature=ident, keep_aspect=False, width=12, height=19,
           opacity=20, use_opacity=False, face="<Z")
    d = s.doc.estado_final.lienzos[ident]
    assert (d["ancho"], d["alto"], d["opacidad"]) == (12, 19, 1)
    assert d["plano"].origen[2] == pytest.approx(0)
    otra = tmp_path / "otra.png"
    Image.new("RGB", (40, 80), "blue").save(otra)
    llamar(s, "set_decal", feature=ident, image=str(otra), keep_aspect=True)
    assert s.doc.estado_final.lienzos[ident]["alto"] == pytest.approx(24)


def test_cilindro_sigue_curvatura_y_anchura_mide_arco(imagen):
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=20, height=40)
    llamar(s, "set_decal", image=str(imagen), face="%CYLINDER", width=30)
    d = next(iter(s.doc.estado_final.lienzos.values()))
    pts = d["malla"]["vertices"]
    assert np.ptp(pts[:, 0]) > 39 and np.ptp(pts[:, 1]) > 39
    assert np.allclose(np.linalg.norm(pts[:, :2], axis=1), 20.02, atol=0.03)
    assert np.ptp(d["malla"]["coordenadas"][:, 0]) > 120
    assert np.max(np.ptp(d["malla"]["coordenadas"][:, 0].reshape(-1, 3), axis=1)) < 20 * np.pi
    assert d["alto"] == pytest.approx(15)


def test_encadenar_caras_incluye_solo_cadena_tangente(imagen):
    s = api.Sesion()
    llamar(s, "create_box", length=40, width=30, height=20)
    llamar(s, "fillet", edges="|Z", radius=3)
    llamar(s, "set_decal", image=str(imagen), face="+X", width=20, chain_faces=False)
    ident = s.doc.operaciones[-1].id
    assert s.doc.estado_final.lienzos[ident]["malla"]["caras"] == 1
    llamar(s, "set_decal", feature=ident, chain_faces=True)
    assert s.doc.estado_final.lienzos[ident]["malla"]["caras"] > 1


def test_textura_transformaciones_numericas():
    puntos = np.array([[0, 0], [10, 0]], float)
    assert np.allclose(calcomanias.textura(puntos, 20, 10), [[0.5, 0.5], [1, 0.5]])
    assert np.allclose(calcomanias.textura(puntos, 20, 10, dx=10), [[0, 0.5], [0.5, 0.5]])
    assert np.allclose(calcomanias.textura(puntos, 20, 10, angulo=90), [[0.5, 0.5], [0.5, -0.5]])
    assert np.allclose(calcomanias.textura(puntos, 20, 10, voltear_h=True), [[0.5, 0.5], [0, 0.5]])
    assert np.allclose(calcomanias.textura([[0, 5]], 20, 10, voltear_v=True), [[0.5, 0]])


def test_receta_vieja_abre_y_edicion_timeline_cancela_sin_cambios(v, imagen):
    s = api.Sesion(v.doc)
    cid = next(iter(v.doc.estado_final.cuerpos))
    llamar(s, "set_decal", image=str(imagen), face=">Z", body=cid, width=12)
    ident = v.doc.operaciones[-1].id
    # La receta anterior no tiene ninguno de estos campos: carga con sus valores compatibles.
    datos = v.doc.operaciones[-1].a_dict()
    for k in ("alto", "mantener_proporcion", "voltear_v", "encadenar", "usar_opacidad", "centrada"):
        datos["params"].pop(k, None)
    from omnicad.timeline.operaciones import operacion_desde_dict
    vieja = operacion_desde_dict(datos)
    assert isinstance(vieja, OpLienzo) and vieja.p["centrada"] is False
    antes = v.doc.a_dict()
    v.timeline.editar.emit(ident)
    p = v.panel
    assert isinstance(p.comando, Calcomania)
    assert p.ctx.evaluar(p.valores["ancho"]) == 12
    p.set_valor("dx", "5 mm")
    p.set_valor("alto", "9 mm")
    p.widgets["opacidad"].deslizador.setValue(25)
    p.widgets["opacidad"].casilla.setChecked(False)
    p._calcular_previa()
    assert p.valores["opacidad"] == 25 and p.valores["usar_opacidad"] is False
    assert p.ctx.evaluar(p.valores["ancho"]) == pytest.approx(18)
    p.cancelar()
    assert v.doc.a_dict() == antes


def test_panel_acepta_y_gizmo_escribe_cada_valor(v, imagen):
    cid = next(iter(v.doc.estado_final.cuerpos))
    s = api.Sesion(v.doc)
    referencia = llamar(s, "find_faces", body=cid, selector=">Z")["faces"][0]["id"]
    from omnicad.api.selectores import elegir
    cara = elegir(s, referencia, "cara")[0]
    from omnicad.nucleo import referencias
    ref = referencias.referencia(cid, cara[1].sub, v.doc.estado_final.cuerpos[cid].forma)
    p = v.ejecutar_comando(Calcomania(), valores={"archivo": str(imagen), "plano": [hit_desde_ref(ref, v.doc.estado_final)]})
    p._calcular_previa()
    assert p.ultima_op is not None
    g = p.manipuladores
    assert {m.clave for m in g.manips if hasattr(m, "clave")} >= {"dx", "dy", "angulo", "ancho", "voltear", "voltear_v"}
    g.escribir({"dx": 2, "dy": 3, "angulo": 30, "ancho": 16, "voltear": True, "voltear_v": True})
    assert p.valores["voltear"] is True and p.valores["voltear_v"] is True
    g.escribir({"voltear": False})
    assert p.valores["voltear"] is False
    botones = [m for m in g.manips if type(m).__name__ == "Volteo"]
    for boton in botones:
        previo = p.valores[boton.clave]
        boton.empezar(g, None, None)
        assert p.valores[boton.clave] is not previo
    p.aceptar()
    d = list(v.doc.estado_final.lienzos.values())[-1]
    assert (d["dx"], d["dy"], d["angulo"], d["ancho"]) == (2, 3, 30, 16)


def test_api_rechaza_opacidad_imagen_y_medidas_invalidas_sin_cambiar(decal, tmp_path):
    s, ident = decal
    antes = s.doc.a_dict()
    for args in ({"opacity": 101}, {"width": -1}, {"image": str(tmp_path / "no.png")}, {"width": "NaN"}):
        assert not api.llamar(s, "set_decal", {"feature": ident, **args})["ok"]
        assert s.doc.a_dict() == antes


def test_calcomania_antigua_reabre_con_medidas_compatibles(decal, tmp_path):
    from omnicad.io_archivos import proyecto
    s, ident = decal
    datos = s.doc.a_dict()
    params = datos["operaciones"][-1]["params"]
    for k in ("alto", "mantener_proporcion", "voltear_v", "encadenar", "usar_opacidad", "centrada"):
        params.pop(k, None)
    s.doc._cargar(datos)
    ruta = proyecto.guardar(s.doc, tmp_path / "antigua.omnicad")
    abierto = proyecto.abrir(ruta)
    d = abierto.estado_final.lienzos[ident]
    assert d["ancho"] / d["alto"] == pytest.approx(2)
    assert abierto.operaciones[-1].p["centrada"] is False


def test_visor_dibuja_opacidad_y_uv_decal(decal, ventana, monkeypatch):
    from unittest.mock import MagicMock
    import omnicad.ui.visor3d as visor3d
    s, ident = decal
    llamar(s, "set_decal", feature=ident, opacity=25, flip_v=True)
    gl = MagicMock()
    monkeypatch.setattr(visor3d, "GL", gl)
    monkeypatch.setattr(ventana.visor, "_textura", lambda _: 1)
    ventana.visor.config.lienzos = [(ident, s.doc.estado_final.lienzos[ident])]
    ventana.visor._dibujar_lienzos()
    gl.glColor4f.assert_called_with(1, 1, 1, 0.25)
    assert gl.glVertex3f.call_count == len(s.doc.estado_final.lienzos[ident]["malla"]["vertices"])
    assert gl.glTexCoord2f.call_count == gl.glVertex3f.call_count
    ventana.visor.config.lienzos = []
