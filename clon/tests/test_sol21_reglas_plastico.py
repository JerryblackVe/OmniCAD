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


def test_la_delgada_toma_el_espesor_de_la_regla_asignada():
    """H-87: con una regla de plástico asignada, Extruir delgada arranca con su espesor (Fusion: la regla da
    Thickness y la usan Extrude, Rib, Web…). Sin regla sigue en 1 mm; lo escrito a mano manda."""
    s = _pieza()                                   # la caja de 20×20×10 queda en el componente Carcasa
    llamar(s, "assign_plastic_rule", component="Carcasa", rule="ABS 2 mm")
    llamar(s, "create_sketch", plane="XY", name="B")
    llamar(s, "draw_rectangle", x1=30, y1=0, x2=50, y2=10)
    cuerpo = llamar(s, "extrude", sketch="B", distance=10, thin=True)["bodies_created"][0]
    assert cuerpo["volume"] == pytest.approx(1360)          # pared de 2 mm (con 1 mm da 640)
    escrito = llamar(s, "extrude", sketch="B", distance=10, thin=True, wall_thickness=1)["bodies_created"][0]
    assert escrito["volume"] == pytest.approx(640)
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.solido import Extruir
    campos = {c.clave: c.defecto for c in Extruir().campos(ContextoComando(s.doc))}
    assert campos["espesor"] == "2 mm"                       # el panel arranca con el de la regla
    sin_regla = {c.clave: c.defecto for c in Extruir().campos(ContextoComando(Documento()))}
    assert sin_regla["espesor"] == "1 mm"


def test_el_espesor_de_la_regla_no_se_toma_de_otro_componente():
    """La regla es la del componente del cuerpo que se toca; sin cuerpos (cuerpo nuevo) manda la única del diseño."""
    from omnicad.nucleo import geometria as geo
    from omnicad.timeline.operaciones import EstadoModelo, espesor_plastico
    e = EstadoModelo()
    con_regla = e.nuevo_cuerpo("op1", geo.caja(10, 10, 10))
    suelto = e.nuevo_cuerpo("op1", geo.caja(10, 10, 10))
    e.componentes["op1"] = {"nombre": "Carcasa", "regla_plastico": {"espesor": 3.0}}
    e.cuerpos[con_regla].componente = "op1"
    assert espesor_plastico(e, [suelto]) == "1 mm"     # su componente no tiene regla: no toma la de al lado
    assert espesor_plastico(e, [con_regla]) == "3 mm"
    assert espesor_plastico(e) == "3 mm"               # sin cuerpos: la única regla asignada


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
