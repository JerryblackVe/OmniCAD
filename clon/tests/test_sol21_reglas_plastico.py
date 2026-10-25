"""SOL-21: reglas de plástico (biblioteca, asignación a componentes, parámetros)."""
import pytest

from omnicad import api
from omnicad.nucleo import plastico


@pytest.fixture(autouse=True)
def biblioteca_temporal(tmp_path, monkeypatch):
    monkeypatch.setenv(plastico.VAR_REGLAS, str(tmp_path / "reglas.json"))
    previas = dict(plastico.REGLAS_USUARIO)
    plastico.REGLAS_USUARIO.clear()
    yield
    plastico.REGLAS_USUARIO.clear()
    plastico.REGLAS_USUARIO.update(previas)


def llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r["ok"], r
    return r["result"]


def _pieza():
    s = api.Sesion()
    llamar(s, "create_box", length=20, width=20, height=10, name="Tapa")
    llamar(s, "create_component", bodies=["Tapa"], name="Carcasa")
    return s


def test_lista_de_fabrica_y_crear_borrar():
    s = api.Sesion()
    r = llamar(s, "list_plastic_rules")
    assert r["default"] == "ABS 2 mm" and any(x["nombre"] == "ABS 2 mm" for x in r["rules"])
    nueva = llamar(s, "create_plastic_rule", name="PP 3 mm", thickness=3, draft_angle=2)["rule"]
    assert nueva["espesor"] == 3 and nueva["radio_nominal"] == 1.5
    repetida = api.llamar(s, "create_plastic_rule", {"name": "pp 3 mm", "thickness": 3})
    assert not repetida["ok"]
    assert llamar(s, "delete_plastic_rule", name="PP 3 mm")["deleted"] == "PP 3 mm"
    assert not api.llamar(s, "delete_plastic_rule", {"name": "ABS 2 mm"})["ok"]


def test_asignar_pasa_el_material_y_crea_parametros():
    s = _pieza()
    llamar(s, "create_plastic_rule", name="ABS 2.5", thickness=2.5, material="ABS")
    r = llamar(s, "assign_plastic_rule", component="Carcasa", rule="ABS 2.5", create_parameters=True)
    assert r["rule"]["espesor"] == 2.5
    nombres = {p["name"]: p for p in llamar(s, "get_parameters")["parameters"]}
    assert {"PlasticThickness", "PlasticDraftAngle", "PlasticNominalRadius"} <= set(nombres)
    assert "2.5" in str(nombres["PlasticThickness"].get("expression", nombres["PlasticThickness"]))
    asignada = next(x for x in llamar(s, "list_plastic_rules")["rules"] if x["nombre"] == "ABS 2.5")
    assert asignada["assigned_to"]
    # una regla distinta reemplaza a la anterior y actualiza los parámetros
    llamar(s, "assign_plastic_rule", component="Carcasa", rule="ABS 2 mm", create_parameters=True)
    p = {p["name"]: p for p in llamar(s, "get_parameters")["parameters"]}
    assert "2 " in str(p["PlasticThickness"]) + " " or "2mm" in str(p["PlasticThickness"]).replace(" ", "")


def test_errores_claros():
    s = _pieza()
    assert not api.llamar(s, "assign_plastic_rule", {"component": "Nada"})["ok"]
    assert not api.llamar(s, "assign_plastic_rule", {"component": "Carcasa", "rule": "no existe"})["ok"]


def test_comandos_de_ventana():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.plastico import AdministrarReglasPlastico, AsignarReglaPlastico
    adm, ctx = AdministrarReglasPlastico(), ContextoComando(Documento())
    v = {c.clave: c.defecto for c in adm.campos(ctx)}
    with pytest.raises(ErrorComando):
        adm.aplicar(dict(v, nombre=""), ctx)                      # sin nombre
    with pytest.raises(ErrorComando):
        adm.aplicar(dict(v, nombre="ABS 2 mm"), ctx)              # pisa una de fábrica
    adm.aplicar(dict(v, nombre="PP 3", espesor="3 mm", angulo="2 deg"), ctx)
    assert plastico.regla("PP 3")["espesor"] == 3 and plastico.regla("PP 3")["angulo_desmoldeo"] == pytest.approx(2)
    adm.aplicar(dict(v, accion="borrar", nombre="PP 3"), ctx)
    assert "PP 3" not in plastico.REGLAS_USUARIO
    asignar = AsignarReglaPlastico()
    with pytest.raises(ErrorComando):
        asignar.construir({"componente": "", "regla": "ABS 2 mm"}, ctx)   # no hay componentes
