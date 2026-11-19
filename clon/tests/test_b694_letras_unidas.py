"""B-694: las letras de un texto que se pisan (una cursiva, o espaciado negativo) se unen en un perfil, como en Fusion:
sin astillas donde se cruzan los contornos, los huecos siguen siendo huecos y Extruir da un sólido válido."""
import pytest

from omnicad import api
from omnicad.nucleo import fuentes, geometria as geo, perfiles as pf
from omnicad.restricciones.boceto import Boceto

pytestmark = pytest.mark.skipif(fuentes.buscar_fuente("DejaVu Sans") is None, reason="No hay DejaVu Sans instalada")


def _partes(espaciado):
    b = Boceto()
    tid = b.agregar_texto((0, 0), "OO", altura=10, fuente="DejaVu Sans", espaciado=espaciado)
    perfiles = pf.detectar_boceto(b, geo.Plano("XY"))
    return perfiles, pf.partes_de_texto(perfiles, [tid])


def test_letras_encimadas_dan_un_perfil_sin_astillas():
    (sueltas, (letras_sueltas, _)) = _partes(0.0)
    perfiles, (letras, huecos) = _partes(-4.0)             # la segunda «O» entra en el hueco de la primera
    assert len(letras_sueltas) == 2 and len(perfiles) == 3
    assert len(letras) == 1 and len(huecos) == 2           # antes: 7 piezas y los huecos contados como letras
    assert min(p.area for p in perfiles) > 1.0
    anillo = letras_sueltas[0].area
    assert anillo < letras[0].area < 2 * anillo           # la zona encimada cuenta una vez


def test_extruir_las_letras_encimadas_da_un_solido_valido():
    s = api.Sesion()
    assert api.llamar(s, "create_sketch", {})["ok"]
    assert api.llamar(s, "add_text", {"text": "OO", "height": 10, "font": "DejaVu Sans", "letter_spacing": -4})["ok"]
    r = api.llamar(s, "extrude", {"sketch": "Boceto1", "profile": "sketch", "distance": 3})
    assert r["ok"], r
    cuerpos = r["result"]["bodies_created"]
    letra = _partes(-4.0)[1][0][0]
    assert len(cuerpos) == 1 and cuerpos[0]["volume"] == pytest.approx(3 * letra.area, rel=1e-4)
    assert geo.es_valida(s.cuerpo(cuerpos[0]["id"]).forma)
