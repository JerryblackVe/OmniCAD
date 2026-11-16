# -*- coding: utf-8 -*-
"""B-570: una pieza guardada con un agujero M10 modelado y un Chaflán después (pieza12 de E11) no se podía recalcular:
en el proceso aparte, el chequeo de autointersecciones del Chaflán analizaba la rosca ahí mismo, sin tope (atajo de
B-462 para formas libres «de pocos polos»), y BOPAlgo no terminaba nunca. La hélice de una rosca es reglada (2 polos en
una dirección): va siempre al análisis con tope."""
import json
from pathlib import Path

from omnicad.nucleo import aislado, revision
from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento

RECETA = json.loads((Path(__file__).parent / "datos" / "b570_pieza12_receta.json").read_text(encoding="utf-8"))


def test_b570_la_pieza_guardada_con_rosca_se_rearma_en_el_hijo_sin_analisis_sin_tope(monkeypatch):
    monkeypatch.setattr(aislado, "EN_HIJO", True)                       # como la rearma el trabajador
    sin_tope, original = [], revision._autointersecciones

    def analizar(forma, limite):
        if geo.es_forma_libre(forma):
            sin_tope.append(len(geo.caras(forma)))
            return 0, [], True                                          # no se corre: colgaría el test
        return original(forma, limite)
    monkeypatch.setattr(revision, "_autointersecciones", analizar)
    con_tope = []
    monkeypatch.setattr(aislado, "correr", lambda tarea, *a, **k: con_tope.append(tarea) or (_ for _ in ()).throw(
        aislado.TiempoAgotado("pasó de 5 s y se cortó")))                  # el análisis con tope, sin esperarlo
    doc = Documento.desde_dict(RECETA)
    assert sin_tope == [] and "autointersecciones" in con_tope
    assert len(doc.estado_final.cuerpos) == 1 and all(r.estado == "ok" for r in doc.resultados)


def test_b570_una_cara_reglada_no_cuenta_como_pocos_polos():
    doc = Documento.desde_dict(RECETA)
    (cuerpo,) = doc.estado_final.cuerpos.values()
    assert geo.es_forma_libre(cuerpo.forma) and not revision._pocos_polos(cuerpo.forma)
