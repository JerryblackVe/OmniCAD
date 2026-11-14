# -*- coding: utf-8 -*-
"""B-456: abrir un proyecto chico «aparte» (FL-3) solo sirve para no congelar la ventana. Si el proceso aparte cae, el
proyecto se abre igual, en la ventana; uno grande (que pide el ensayo aislado por seguridad, B-48) sigue sin abrirse."""
import pytest

from omnicad import api
from omnicad.io_archivos import proyecto
from omnicad.nucleo import aislado, geometria as geo


def _pieza_real(tmp_path, monkeypatch):
    """Caja con cilindro unido, empalme, agujero y simetría; guardada con otra versión (la caché no sirve)."""
    s = api.Sesion()
    for nombre, args in (("create_box", {"length": 60, "width": 40, "height": 20}),
                         ("create_cylinder", {"radius": 8, "height": 35, "x": 30, "y": 20}),
                         ("boolean_operation", {"target": "Cuerpo1", "tools": ["Cuerpo2"], "operation": "join"}),
                         ("fillet", {"edges": "|Z", "radius": 3}),
                         ("create_hole", {"face": ">Z", "diameter": 4, "depth": 10}),
                         ("mirror", {"bodies": "Cuerpo1", "plane": "YZ", "combine": True})):
        r = api.llamar(s, nombre, args)
        assert r["ok"], (nombre, r)
    ruta = tmp_path / "pieza.omnicad"
    with monkeypatch.context() as m:
        m.setattr(proyecto, "VERSION", "0.0.0-otra")
        assert api.llamar(s, "save_document", {"path": str(ruta)})["ok"]
    volumenes = {c.id: round(geo.volumen_exacto(c.forma), 3) for c in s.doc.estado_final.cuerpos.values()}
    return ruta, volumenes


def _hijo_caido(monkeypatch):
    def caido(*a, **k):
        raise aislado.TareaAislada("el proceso aparte se cayó")
    monkeypatch.setattr(aislado, "correr_json", caido)


def test_un_proyecto_chico_abre_en_la_ventana_si_el_proceso_aparte_cae(tmp_path, monkeypatch):
    ruta, esperado = _pieza_real(tmp_path, monkeypatch)
    _hijo_caido(monkeypatch)
    doc = proyecto.abrir(ruta, aparte=True)
    assert {c.id: round(geo.volumen_exacto(c.forma), 3) for c in doc.estado_final.cuerpos.values()} == esperado


def test_un_proyecto_grande_con_el_proceso_aparte_caido_sigue_sin_abrirse(tmp_path, monkeypatch):
    ruta, _ = _pieza_real(tmp_path, monkeypatch)
    _hijo_caido(monkeypatch)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)          # ahora este proyecto cuenta como grande
    with pytest.raises(proyecto.ErrorProyecto, match="ensayo de apertura falló"):
        proyecto.abrir(ruta, aparte=True)
