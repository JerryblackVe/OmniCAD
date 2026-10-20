"""B-75: calcomanía centrada en la cara cilíndrica real y visible en el render CPU."""
import io
import math

import numpy as np
import pytest
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepTools import BRepTools
from PIL import Image

from omnicad import api
from omnicad.api.selectores import elegir
from omnicad.nucleo import geometria as geo


def llamar(sesion, nombre, **argumentos):
    resultado = api.llamar(sesion, nombre, argumentos)
    assert resultado["ok"], resultado
    return resultado["result"]


@pytest.fixture
def imagen(tmp_path):
    ruta = tmp_path / "calcomania.png"
    Image.new("RGBA", (400, 40), (255, 0, 0, 255)).save(ruta)
    return ruta


def cilindro(recorte):
    sesion = api.Sesion()
    llamar(sesion, "create_cylinder", diameter=40, height=60)
    if recorte:
        x = -10 if recorte == "estrecha" else 10
        z, alto = (10, 40) if recorte == "ventana" else (-10, 80)
        llamar(sesion, "create_box", length=40, width=60, height=alto, x=x, y=-30, z=z,
               anchor="corner", operation="cut")
    cara = elegir(sesion, "%CYLINDER", "cara")[0][1].sub
    cuerpo = next(iter(sesion.doc.estado_final.cuerpos.values()))
    assert geo.es_valida(cuerpo.forma)
    assert 0 < geo.volumen(cuerpo.forma) <= math.pi * 20**2 * 60 + 1e-6
    return sesion, cara


@pytest.mark.parametrize("recorte", ["amplia", "estrecha", "ventana", False],
                         ids=["240_grados", "120_grados", "ventana", "entera"])
def test_centro_y_ancho_se_ajustan_al_rango_real(imagen, recorte):
    sesion, cara = cilindro(recorte)
    u0, u1, v0, v1 = BRepTools.UVBounds_s(cara)
    superficie = BRepAdaptor_Surface(cara)
    llamar(sesion, "set_decal", image=str(imagen), face="%CYLINDER")
    datos = next(iter(sesion.doc.estado_final.lienzos.values()))
    centro = np.array(superficie.Value((u0 + u1) / 2, (v0 + v1) / 2).Coord())
    origen = np.array(superficie.Cylinder().Location().Coord())
    a, b = datos["plano"].origen - origen, centro - origen
    diferencia = math.atan2(a[1], a[0]) - math.atan2(b[1], b[0])
    assert abs(math.degrees(math.atan2(math.sin(diferencia), math.cos(diferencia)))) <= 2
    arco = (u1 - u0) * 20
    assert datos["ancho"] <= arco
    assert datos["ancho"] == pytest.approx(min(arco, (v1 - v0) * 10) * 0.9, abs=0.05)
    assert datos["malla"]["tamano"][0] == pytest.approx(arco, abs=0.05)
    coordenadas = datos["malla"]["coordenadas"][:, 0]
    if recorte and recorte != "ventana":
        assert coordenadas.min() >= -arco / 2 - 0.05
        assert coordenadas.max() <= arco / 2 + 0.05
    else:
        assert datos["plano"].origen == pytest.approx([-20, 0, 30], abs=1e-6)


def test_render_cpu_muestra_color_de_calcomania(imagen):
    sesion, _cara = cilindro("amplia")
    antes = llamar(sesion, "get_viewport_image", view="left", width=160, height=160)["image"].png
    llamar(sesion, "set_decal", image=str(imagen), face="%CYLINDER")
    despues = llamar(sesion, "get_viewport_image", view="left", width=160, height=160)["image"].png

    def rojos(png):
        pixeles = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
        return (pixeles[:, :, 0] > 230) & (pixeles[:, :, 1] < 20) & (pixeles[:, :, 2] < 20)

    assert not rojos(antes).any()
    assert np.count_nonzero(rojos(despues)) > 100
    oculto = llamar(sesion, "get_viewport_image", view="right", width=160, height=160)["image"].png
    assert not rojos(oculto).any()
    otro = llamar(sesion, "create_box", length=10, width=10, height=10, y=40)["bodies_created"][0]["id"]
    filtrado = llamar(sesion, "get_viewport_image", view="left", width=160, height=160,
                      bodies=[otro], fit=False)["image"].png
    assert not rojos(filtrado).any()


def test_render_cpu_respeta_uv_alfa_y_opacidad(tmp_path):
    ruta = tmp_path / "cuadrantes.png"
    imagen = Image.new("RGBA", (40, 40), (0, 255, 0, 0))
    imagen.paste((255, 0, 0, 255), (0, 0, 20, 20))
    imagen.paste((0, 0, 255, 255), (0, 20, 20, 40))
    imagen.paste((255, 255, 0, 255), (20, 20, 40, 40))
    imagen.save(ruta)
    sesion = api.Sesion()
    llamar(sesion, "create_box", length=40, width=40, height=10)

    def render():
        png = llamar(sesion, "get_viewport_image", view="top", width=160, height=160)["image"].png
        return np.asarray(Image.open(io.BytesIO(png)).convert("RGB"), float)

    fondo = render()
    llamar(sesion, "set_decal", image=str(ruta), face=">Z", width=30)
    completo = render()
    assert completo[60, 60] == pytest.approx([255, 0, 0], abs=1)
    assert completo[100, 60] == pytest.approx([0, 0, 255], abs=1)
    assert completo[100, 100] == pytest.approx([255, 255, 0], abs=1)
    assert completo[60, 100] == pytest.approx(fondo[60, 100], abs=1)
    ident = sesion.doc.operaciones[-1].id
    llamar(sesion, "set_decal", feature=ident, opacity=50)
    medio = render()
    assert medio[60, 60] == pytest.approx((completo[60, 60] + fondo[60, 60]) / 2, abs=1)


def test_render_cpu_no_pinta_sobre_la_ventana(imagen):
    sesion, _cara = cilindro("ventana")
    llamar(sesion, "set_decal", image=str(imagen), face="%CYLINDER", width=150, height=60, keep_aspect=False)
    png = llamar(sesion, "get_viewport_image", view="right", width=160, height=160)["image"].png
    pixeles = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
    rojos = (pixeles[:, :, 0] > 230) & (pixeles[:, :, 1] < 20) & (pixeles[:, :, 2] < 20)
    assert rojos.any()
    assert not rojos[80, 80]
