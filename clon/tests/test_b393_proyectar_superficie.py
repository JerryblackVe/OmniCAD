"""B-393: proyectar una superficie no encadena dos veces el círculo que la genera."""
import json
import math
from pathlib import Path

import pytest
from OCP.BRep import BRep_Tool

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision
from omnicad.nucleo.perfiles import aristas_boceto
from omnicad.nucleo.referencias import subformas
from omnicad.nucleo.solidos_crear import _cadenas
from omnicad.nucleo.solidos_modificar import aristas_cadena_tangente


def test_b393_proyectar_superficie_conserva_el_cuerpo():
    sesion = api.Sesion()
    ruta = Path(__file__).parent / "corpus_caza" / "b393_proyectar_a_boceto.json"
    pasos = json.loads(ruta.read_text(encoding="utf-8"))["pasos"]
    for paso in pasos[:-1]:
        resultado = api.llamar(sesion, paso["tool"], paso["args"])
        assert resultado["ok"], resultado
    antes = sesion.cuerpo("op2.c1").forma
    cruces = revision._autointersecciones_seguras(antes, 1, 5.0)[0]
    assert cruces == 0
    area = geo.area(antes)
    assert area == pytest.approx(2 * math.pi * 20 * 10)

    paso = pasos[-1]
    resultado = api.llamar(sesion, paso["tool"], paso["args"])
    assert resultado["ok"] and resultado["result"]["entities"], resultado
    despues = sesion.cuerpo("op2.c1").forma
    assert revision._autointersecciones_seguras(despues, 1, 5.0)[0] == cruces
    assert geo.es_valida(despues)
    assert len(geo.caras(despues)) == len(geo.caras(antes)) == 1
    assert geo.area(despues) == pytest.approx(area)
    assert geo.caja_envolvente(despues) == geo.caja_envolvente(antes)


@pytest.mark.parametrize("cerrada", [True, False], ids=["desde_circulo", "desde_recta"])
def test_b393_costura_de_circulo_no_es_extremo_para_encadenar(cerrada):
    geometria = [("circulo", 1, (0, 0), 20), ("linea", 2, (20, 0), (20, 10))]
    forma = geo.compuesto(_cadenas([a for _, a in aristas_boceto(geometria, geo.Plano("XY"))]))
    arista = next(a for a in subformas(forma, "arista") if BRep_Tool.IsClosed_s(a) == cerrada)
    cadena = aristas_cadena_tangente(forma, arista)
    assert len(cadena) == 1 and cadena[0].IsSame(arista)
