"""B-450: Mover cara traslada los empalmes del borde sin escalón ni cambio de radio."""
import math

import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


def _llamar(sesion, nombre, **args):
    respuesta = api.llamar(sesion, nombre, args)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


@pytest.mark.parametrize("empalmes", [1, 2])
@pytest.mark.parametrize("distancia", [5, -5])
@pytest.mark.parametrize("con_direccion", [False, True])
def test_mover_cara_superior_conserva_los_empalmes(empalmes, distancia, con_direccion):
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=40, width=30, height=20)
    aristas = [">Z and |X and <Y", ">Z and |X and >Y"][:empalmes]
    _llamar(sesion, "fillet", edges=aristas, radius=5)
    movimiento = ({"direction": "Z", "distance": distancia} if con_direccion
                  else {"translate": [0, 0, distancia]})
    _llamar(sesion, "move_faces", faces="+Z", **movimiento)

    forma = sesion.cuerpo("Cuerpo1").forma
    perdida = empalmes * (1 - math.pi / 4) * 5**2 * 40
    assert geo.es_valida(forma)
    assert len(geo.solidos(forma)) == 1
    assert geo.volumen(forma) == pytest.approx(40 * 30 * (20 + distancia) - perdida, rel=1e-6)
    minimo, maximo = geo.caja_envolvente(forma)
    assert minimo == pytest.approx([-20, -15, 0], abs=1e-6)
    assert maximo == pytest.approx([20, 15, 20 + distancia], abs=1e-6)
    assert len(geo.caras(forma)) == 6 + empalmes  # no quedan caras adicionales formando un escalón
    curvas = [c for c in _llamar(sesion, "find_faces")["faces"] if c["type"] == "cylinder"]
    assert len(curvas) == empalmes
    assert [c["radius"] for c in curvas] == pytest.approx([5] * empalmes)


def test_mover_tapa_con_empalmes_superiores_y_verticales():
    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=40, width=30, height=20)
    _llamar(sesion, "fillet", edges=">Z or |Z", radius=5)
    volumen_inicial = geo.volumen(sesion.cuerpo("Cuerpo1").forma)

    _llamar(sesion, "move_faces", faces="+Z", translate=[0, 0, 5])

    forma = sesion.cuerpo("Cuerpo1").forma
    # Las cuatro esquinas redondeadas restan (4 - π)·r² a la sección de las paredes.
    esperado = volumen_inicial + 5 * (40 * 30 - (4 - math.pi) * 5**2)
    assert geo.es_valida(forma)
    assert len(geo.solidos(forma)) == 1
    assert geo.volumen(forma) == pytest.approx(esperado, rel=1e-6)
    assert geo.caja_envolvente(forma)[1] == pytest.approx([20, 15, 25], abs=1e-6)
    assert len(geo.caras(forma)) == 18


def test_si_la_via_de_empalmes_falla_cae_al_camino_de_siempre(monkeypatch):
    """Vía especial: su error no se muestra; mover la cara sigue andando por el camino normal (sobre un cuerpo ya modificado)."""
    from omnicad.nucleo import solidos_modificar as sm

    sesion = api.Sesion()
    _llamar(sesion, "create_box", length=40, width=30, height=20)
    _llamar(sesion, "fillet", edges=">Z", radius=3)
    _llamar(sesion, "move_faces", faces="+Z", translate=[0, 0, 2])          # cuerpo ya modificado por un paso anterior

    llamadas = []

    def falla(*args, **kw):
        llamadas.append(1)
        raise geo.ErrorGeometria("simulado")

    monkeypatch.setattr(sm, "_trasladar_caras", falla)
    antes = geo.volumen(sesion.cuerpo("Cuerpo1").forma)
    _llamar(sesion, "move_faces", faces="+Z", translate=[0, 0, 3])
    forma = sesion.cuerpo("Cuerpo1").forma
    assert llamadas, "la vía de empalmes no se usó: el test no prueba nada"
    assert geo.es_valida(forma) and len(geo.solidos(forma)) == 1
    assert geo.volumen(forma) > antes
