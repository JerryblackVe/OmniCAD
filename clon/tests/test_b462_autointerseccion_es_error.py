"""B-462: un Barrido o una Solevación que se cruzan consigo mismos fallan con un mensaje claro, como Fusion
(ASM_SELF_INTER), en vez de crear un cuerpo inválido. BRepCheck no los ve: `es_valida` da True con volumen negativo.
Los pasos son los de los repros de E11 (evidencias/reportes_pc/2026-11-14_e11_barrido y _solevacion)."""
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from omnicad import api
from omnicad.nucleo import aislado
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import revision as rev
from omnicad.timeline.documento import Documento
from omnicad.timeline import ops_solido
from omnicad.timeline.operaciones import ErrorOperacion

REPROS = json.loads((Path(__file__).parent / "datos" / "b462_autointersecciones.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("caso, que, con_cruces", [
    ("barrido_r15_en_arco_r10", "El barrido", False),
    ("solevacion_cerrada_4_circulos", "La solevación", False),
    ("solevacion_cerrada_3_cuadrados_girados", "La solevación", True),
    ("solevacion_linea_central_en_s", "La solevación", True),
])
def test_el_resultado_que_se_autointerseca_es_un_error_y_no_un_cuerpo(caso, que, con_cruces, monkeypatch):
    # B-490: con la máquina cargada el tope de 5 s se pasaba y daba aviso; el test mide la guarda, no el reloj
    monkeypatch.setattr(ops_solido, "PLAZO_CRUCES", 120.0)
    doc = Documento.desde_dict(REPROS[caso])
    paso = doc.resultados[-1]
    assert paso.estado == "error", (paso.estado, paso.mensaje)
    assert f"{que} se autointerseca" in paso.mensaje, paso.mensaje
    # P-158d: con cruces contados el mensaje trae «(N)»; el volumen negativo no cuenta cruces
    assert bool(re.search(r"se autointerseca \(\d+\)", paso.mensaje)) == con_cruces, paso.mensaje
    assert not doc.estado_final.cuerpos


def test_la_previa_tambien_rechaza_el_volumen_negativo_sin_analizar():
    """La vista previa no corre el análisis de autointersecciones (es para mirar rápido), pero el volumen negativo es
    barato y se rechaza igual; el sólido sano pasa."""
    previa = SimpleNamespace(revisar_autointersecciones=False)
    caja = geo.caja(10, 10, 10)
    with pytest.raises(ErrorOperacion, match="El barrido se autointerseca: causa"):
        ops_solido._exigir_sin_autointersecciones(previa, caja.Reversed(), "El barrido", "causa")
    ops_solido._exigir_sin_autointersecciones(previa, caja, "El barrido", "causa")


def test_en_el_proceso_aparte_una_forma_libre_chica_se_analiza_sin_abrir_otro(monkeypatch):
    """Ya dentro del proceso aparte (abrir o recalcular un documento grande), una forma libre chica no abre otro proceso
    para el análisis (costaba ~1,5 s por paso); una rosca modelada (muchos polos) sigue aislada (T-01)."""
    s = api.Sesion()
    for nombre, plano, entidad in (("A", "XY", {"type": "rectangle", "id": "R", "center": [0, 0], "width": 24, "height": 24}),
                                   ("B", "P2", {"type": "circle", "id": "C", "center": [0, 0], "radius": 7})):
        if plano == "P2":
            assert api.llamar(s, "create_construction_plane", {"plane": "XY", "offset": 30, "name": "P2"})["ok"]
        assert api.llamar(s, "sketch_from_spec", {"name": nombre, "plane": plano, "entities": [entidad]})["ok"]
    r = api.llamar(s, "loft", {"sketches": ["A", "B"]})
    forma = s.cuerpo(r["result"]["bodies_created"][0]["id"]).forma
    assert geo.es_forma_libre(forma)
    monkeypatch.setattr(aislado, "EN_HIJO", True)
    monkeypatch.setattr(aislado, "correr", lambda *a, **k: pytest.fail("abrió otro proceso"))
    assert rev._autointersecciones_seguras(forma, 1, 5.0)[0] == 0
