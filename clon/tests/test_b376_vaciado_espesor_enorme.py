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


def test_b524_vaciar_de_nuevo_un_cuerpo_hueco_no_agranda_el_volumen():
    """B-524: quitar la cara interior de una pared de 2 mm con 14 mm de espesor daba «ok» y MÁS volumen (ShapeFix
    «reparaba» el resultado inválido del kernel después del control). Ahora es un error y el cuerpo queda igual."""
    sesion = api.Sesion()
    assert api.llamar(sesion, "create_box", {"length": 80, "width": 30, "height": 40})["ok"]
    assert api.llamar(sesion, "shell", {"body": "Cuerpo1", "faces": "<Z"})["ok"]
    antes = geo.volumen(next(iter(sesion.doc.estado_final.cuerpos.values())).forma)
    r = api.llamar(sesion, "shell", {"body": "op1.c1", "faces": ["Cuerpo1/F7"], "thickness": 14.0})
    assert not r["ok"] and "Pared" in r["mensaje"], r
    assert geo.volumen(next(iter(sesion.doc.estado_final.cuerpos.values())).forma) == antes


def test_b536_barrido_empalmado_la_cadena_toma_todo_y_sin_cadena_se_vacia():
    """B-536: tras empalmar todo un barrido, la cadena tangente de una tapa llega a todas las caras (como en Fusion);
    el error dice qué desmarcar, y sin cadena el vaciado de 1 mm anda."""
    sesion = api.Sesion()
    for nombre, args in (("create_sketch", {"plane": "XY", "name": "perfil"}), ("draw_circle", {"radius": 5}),
                         ("create_sketch", {"plane": "XZ", "name": "ruta"}),
                         ("draw_spline", {"points": [[0, 0], [30, 10], [60, 0], [90, 10]]}),
                         ("sweep", {"sketch": "perfil", "path_sketch": "ruta"}),
                         ("fillet", {"body": "Cuerpo1", "edges": "all", "radius": 1})):
        assert api.llamar(sesion, nombre, args)["ok"], nombre
    caras = api.llamar(sesion, "find_faces", {})["result"]["faces"]
    tapa = [f["id"] for f in caras if f["type"] == "plane"][0]
    antes = geo.volumen(next(iter(sesion.doc.estado_final.cuerpos.values())).forma)
    r = api.llamar(sesion, "shell", {"body": "Cuerpo1", "faces": [tapa], "thickness": 1})
    assert not r["ok"] and "desmarcá Cadena tangente" in r["mensaje"], r
    r = api.llamar(sesion, "shell", {"body": "Cuerpo1", "faces": [tapa], "thickness": 1, "tangent_chain": False})
    assert r["ok"], r
    forma = next(iter(sesion.doc.estado_final.cuerpos.values())).forma
    assert geo.es_valida(forma) and 0 < geo.volumen(forma) < antes
