"""SOL-24: reconocer funciones (agujeros, empalmes y chaflanes) en un cuerpo sin historial."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import reconocer_funciones as rf


def _tipos(r):
    return sorted(f["type"] for f in r["features"])


def _bloque():
    return geo.caja(40, 40, 20, (-20, -20, 0))


def test_agujero_pasante_y_ciego():
    pasante = geo.booleano(_bloque(), geo.cilindro(4, 30, (0, 0, -5)), "cortar")
    r = rf.reconocer_funciones(pasante)
    (h,) = r["features"]
    assert h["type"] == "hole" and h["through"] and h["diameter"] == pytest.approx(8) and h["depth"] == pytest.approx(20)
    ciego = geo.booleano(_bloque(), geo.cilindro(3, 10, (0, 0, 10)), "cortar")
    (h,) = rf.reconocer_funciones(ciego)["features"]
    assert h["type"] == "hole" and not h["through"] and h["depth"] == pytest.approx(10)


def test_avellanado_une_dos_agujeros_coaxiales():
    pieza = geo.booleano(geo.booleano(_bloque(), geo.cilindro(3, 30, (0, 0, -5)), "cortar"),
                         geo.cilindro(6, 6, (0, 0, 14)), "cortar")
    r = rf.reconocer_funciones(pieza)
    assert _tipos(r) == ["hole", "hole"]
    assert all("counterbore_with" in f for f in r["features"])


def test_empalme_y_chaflan_y_cuerpo_liso():
    assert rf.reconocer_funciones(_bloque())["features"] == []                    # una caja lisa no tiene funciones
    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 40, "width": 40, "height": 20, "name": "Caja"})
    api.llamar(s, "fillet", {"edges": "|Z", "radius": 4})
    r = api.llamar(s, "find_features", {})["result"]
    assert r["summary"] == {"hole": 0, "fillet": 4, "chamfer": 0}
    assert all(f["radius"] == pytest.approx(4) and f["convex"] for f in r["features"] if f["type"] == "fillet")
    t = api.Sesion()
    api.llamar(t, "create_box", {"length": 40, "width": 40, "height": 20, "name": "Caja"})
    api.llamar(t, "chamfer", {"edges": ">Z", "distance": 2})
    r = api.llamar(t, "find_features", {})["result"]
    assert r["summary"]["chamfer"] == 4 and r["summary"]["fillet"] == 0
    assert r["features"][0]["angle"] == pytest.approx(45, abs=1) and r["features"][0]["width"] == pytest.approx(2.828, rel=1e-2)


def test_un_cilindro_macizo_no_es_un_agujero():
    assert rf.reconocer_funciones(geo.cilindro(10, 10))["features"] == []


def test_herramienta_pide_un_solido_y_valida_tipos():
    s = api.Sesion()
    assert not api.llamar(s, "find_features", {})["ok"]
    api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})
    assert not api.llamar(s, "find_features", {"types": ["extrude"]})["ok"]
    solo = api.llamar(s, "find_features", {"types": ["hole"]})["result"]
    assert solo["features"] == []


def test_dialogo_lista_lo_encontrado():
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpPrimitiva
    from omnicad.ui.comando import ContextoComando, hit_desde_ref
    from omnicad.ui.comandos.inspeccionar import ReconocerFunciones
    QApplication.instance() or QApplication([])
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="40", largo="40", alto="20"))
    cmd, ctx = ReconocerFunciones(), ContextoComando(doc)
    v = {c.clave: c.defecto for c in cmd.campos(ctx)}
    assert "Elegí" in cmd._resultado(v, ctx)
    v["cuerpo"] = [hit_desde_ref({"tipo": "cuerpo", "cuerpo": "op1.c1"}, doc.estado_final)]
    assert "No se encontró" in cmd._resultado(v, ctx)
    v.update(agujeros=False, empalmes=False, chaflanes=False)
    assert "Marcá" in cmd._resultado(v, ctx)
