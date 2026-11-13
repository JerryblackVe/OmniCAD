"""B-376: un Vaciado con un espesor que no cabe da un error claro, no un cuerpo con la pared cruzada sobre sí misma."""
import json
from pathlib import Path

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision

CASO = Path(__file__).parent / "corpus_caza" / "b376_vaciado_espesor_enorme.json"


def _armar_hasta_el_ultimo_paso():
    sesion = api.Sesion()
    pasos = json.loads(CASO.read_text(encoding="utf-8"))["pasos"]
    for paso in pasos[:-1]:
        assert api.llamar(sesion, paso["tool"], paso["args"])["ok"], paso
    return sesion, pasos[-1]


def test_espesor_mayor_que_la_pared_se_rechaza_con_un_mensaje():
    sesion, ultimo = _armar_hasta_el_ultimo_paso()
    antes = geo.volumen(next(iter(sesion.doc.estado_final.cuerpos.values())).forma)
    r = api.llamar(sesion, ultimo["tool"], ultimo["args"])
    assert not r["ok"] and "el espesor no cabe" in r["mensaje"], r
    cuerpos = list(sesion.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1 and geo.volumen(cuerpos[0].forma) == antes          # el documento quedó como estaba
    assert revision._autointersecciones_seguras(cuerpos[0].forma, 1, 5.0)[0] == 0


def test_un_vaciado_normal_sigue_andando_y_sin_cruces():
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_box", {"length": 40, "width": 30, "height": 20})["ok"]
    assert api.llamar(sesion, "shell", {"body": "Cuerpo1", "thickness": 2, "faces": "<Z"})["ok"]
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma) and revision._autointersecciones_seguras(forma, 1, 5.0)[0] == 0
    assert 24000 - 40 * 30 * 20 < geo.volumen(forma) < 24000
