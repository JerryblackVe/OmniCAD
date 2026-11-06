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


def test_nervio_y_red_toman_desmoldeo_y_radio_de_la_regla():
    """H-100: con una regla de plástico asignada, Nervio y Red arrancan con su ángulo de desmoldeo y su radio
    nominal (Fusion: la regla da Draft Angle y Nominal Radius y los usan Rib, Web…). Sin regla siguen en 0."""
    from omnicad.nucleo import geometria as geo
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Nervio, Red

    s = api.Sesion()
    cid = llamar(s, "create_box", length=40, width=20, height=20, anchor="corner", name="Cuerpo")["bodies_created"][0]["id"]
    llamar(s, "create_box", length=36, width=20, height=18, x=2, z=2, anchor="corner", operation="cut", target=cid)
    llamar(s, "create_component", bodies=["Cuerpo"], name="Carcasa")
    llamar(s, "create_plastic_rule", name="PP 5x1.5", thickness=2.5, draft_angle=5, nominal_radius=1.5)
    llamar(s, "assign_plastic_rule", component="Carcasa", rule="PP 5x1.5")

    llamar(s, "create_construction_plane", plane="XZ", offset=-10, name="Plano")
    b = llamar(s, "create_sketch", plane="Plano")["sketch"]["id"]
    llamar(s, "draw_line", sketch=b, start_x=10, start_y=8, end_x=30, end_y=8)

    # Nervio sin draft_angle -> toma el de la regla (5 deg): misma geometría que ponerlo a mano.
    llamar(s, "create_rib", sketch=b, thickness=2, target="Cuerpo")
    vol_regla = geo.volumen(s.cuerpo(cid).forma)
    llamar(s, "undo")
    llamar(s, "create_rib", sketch=b, thickness=2, target="Cuerpo", draft_angle=5)
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(vol_regla, rel=1e-6)
    llamar(s, "undo")
    llamar(s, "create_rib", sketch=b, thickness=2, target="Cuerpo", draft_angle=0)
    assert geo.volumen(s.cuerpo(cid).forma) != pytest.approx(vol_regla, rel=1e-6)
    llamar(s, "undo")

    # Red sin fillet_radius -> toma el radio nominal de la regla (1.5 mm): igual que ponerlo a mano.
    llamar(s, "create_construction_plane", plane="XY", offset=12, name="P2")
    b2 = llamar(s, "create_sketch", plane="P2")["sketch"]["id"]
    llamar(s, "draw_line", sketch=b2, start_x=10, start_y=10, end_x=30, end_y=10)
    llamar(s, "create_web", sketch=b2, thickness=2, target="Cuerpo")
    vol_web_regla = geo.volumen(s.cuerpo(cid).forma)
    llamar(s, "undo")
    llamar(s, "create_web", sketch=b2, thickness=2, target="Cuerpo", fillet_radius=1.5)
    assert geo.volumen(s.cuerpo(cid).forma) == pytest.approx(vol_web_regla, rel=1e-6)

    # Sin regla (documento nuevo) el panel arranca en 0.
    nv = {c.clave: c.defecto for c in Nervio().campos(ContextoComando(Documento()))}
    assert nv["angulo_desmoldeo"] == "0 deg"
    rd = {c.clave: c.defecto for c in Red().campos(ContextoComando(Documento()))}
    assert rd["radio_empalme"] == "0 mm"

    # Con regla asignada, el panel arranca con los valores de la regla.
    cn = {c.clave: c.defecto for c in Nervio().campos(ContextoComando(s.doc))}
    assert cn["angulo_desmoldeo"] == "5 deg"
    cr = {c.clave: c.defecto for c in Red().campos(ContextoComando(s.doc))}
    assert cr["radio_empalme"] == "1.5 mm"
    s = _pieza()
    assert not api.llamar(s, "assign_plastic_rule", {"component": "Nada"})["ok"]
    assert not api.llamar(s, "assign_plastic_rule", {"component": "Carcasa", "rule": "no existe"})["ok"]


def test_nervio_red_vaciado_y_engrosar_toman_el_espesor_de_la_regla():
    """H-102: con una regla de plástico asignada, Nervio, Red, Vaciado y Engrosar toman su espesor (Fusion: la regla
    da Thickness, «used by modeling tools such as Extrude, Rib, Web, … Thicken, Shell»). Sin regla cada uno sigue con
    el suyo (2 mm Nervio, Red y Engrosar; 1 mm Vaciado) y lo escrito a mano manda."""
    from omnicad.nucleo import geometria as geo
    from omnicad.timeline.documento import Documento
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Nervio, Red
    from omnicad.ui.comandos.modificar import Vaciado
    from omnicad.ui.comandos.superficie import Engrosar

    s = api.Sesion()
    cid = llamar(s, "create_box", length=40, width=20, height=20, anchor="corner", name="Cuerpo")["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=["Cuerpo"], name="Carcasa")
    llamar(s, "create_plastic_rule", name="PP 3", thickness=3, draft_angle=0, nominal_radius=0)
    llamar(s, "assign_plastic_rule", component="Carcasa", rule="PP 3")

    def volumen():
        return geo.volumen(s.cuerpo(cid).forma)

    # Vaciado sin espesor -> los 3 mm de la regla (el valor fijo de antes era 1 mm).
    llamar(s, "shell", body="Cuerpo", faces=[], thickness="")
    con_regla = volumen()
    llamar(s, "undo")
    llamar(s, "shell", body="Cuerpo", faces=[], thickness=3)
    assert volumen() == pytest.approx(con_regla, rel=1e-6)
    llamar(s, "undo")
    llamar(s, "shell", body="Cuerpo", faces=[], thickness=1)
    assert volumen() != pytest.approx(con_regla, rel=1e-6)
    llamar(s, "undo")

    # Engrosar sin espesor -> los 3 mm de la regla (el valor fijo de antes era 2 mm).
    creado = llamar(s, "thicken", faces=">Z", body="Cuerpo", thickness="")["bodies_created"][0]["volume"]
    llamar(s, "undo")
    assert creado == pytest.approx(40 * 20 * 3)                       # 2400 mm³ con 3 mm
    a_mano = llamar(s, "thicken", faces=">Z", body="Cuerpo", thickness=3)["bodies_created"][0]["volume"]
    assert a_mano == pytest.approx(creado, rel=1e-6)
    llamar(s, "undo")
    fijo = llamar(s, "thicken", faces=">Z", body="Cuerpo", thickness=2)["bodies_created"][0]["volume"]
    assert fijo != pytest.approx(creado, rel=1e-6)
    llamar(s, "undo")

    # Cuerpo hueco de paredes de 2 mm para el nervio y la red.
    llamar(s, "create_box", length=36, width=20, height=18, x=2, z=2, anchor="corner", operation="cut", target=cid)

    # Nervio sin grosor -> los 3 mm de la regla (el valor fijo de antes era 2 mm).
    llamar(s, "create_construction_plane", plane="XZ", offset=-10, name="Plano")
    b = llamar(s, "create_sketch", plane="Plano")["sketch"]["id"]
    llamar(s, "draw_line", sketch=b, start_x=10, start_y=8, end_x=30, end_y=8)
    llamar(s, "create_rib", sketch=b, target="Cuerpo")
    con_regla = volumen()
    llamar(s, "undo")
    llamar(s, "create_rib", sketch=b, target="Cuerpo", thickness=3)
    assert volumen() == pytest.approx(con_regla, rel=1e-6)
    llamar(s, "undo")
    llamar(s, "create_rib", sketch=b, target="Cuerpo", thickness=2)
    assert volumen() != pytest.approx(con_regla, rel=1e-6)
    llamar(s, "undo")

    # Red sin grosor -> los 3 mm de la regla.
    llamar(s, "create_construction_plane", plane="XY", offset=12, name="P2")
    b2 = llamar(s, "create_sketch", plane="P2")["sketch"]["id"]
    llamar(s, "draw_line", sketch=b2, start_x=10, start_y=10, end_x=30, end_y=10)
    llamar(s, "create_web", sketch=b2, target="Cuerpo")
    con_regla = volumen()
    llamar(s, "undo")
    llamar(s, "create_web", sketch=b2, target="Cuerpo", thickness=3)
    assert volumen() == pytest.approx(con_regla, rel=1e-6)
    llamar(s, "undo")

    # Los paneles arrancan con el espesor de la regla y, sin regla, con el de siempre.
    con = {c.clave: c.defecto for c in Nervio().campos(ContextoComando(s.doc))}
    assert con["espesor"] == "3 mm"
    assert {c.clave: c.defecto for c in Red().campos(ContextoComando(s.doc))}["espesor"] == "3 mm"
    vac = {c.clave: c.defecto for c in Vaciado().campos(ContextoComando(s.doc))}
    assert vac["espesor_interior"] == vac["espesor_exterior"] == "3 mm"
    assert {c.clave: c.defecto for c in Engrosar().campos(ContextoComando(s.doc))}["espesor"] == "3 mm"
    sin = Documento()
    assert {c.clave: c.defecto for c in Nervio().campos(ContextoComando(sin))}["espesor"] == "2 mm"
    assert {c.clave: c.defecto for c in Red().campos(ContextoComando(sin))}["espesor"] == "2 mm"
    vac = {c.clave: c.defecto for c in Vaciado().campos(ContextoComando(sin))}
    assert vac["espesor_interior"] == vac["espesor_exterior"] == "1 mm"
    assert {c.clave: c.defecto for c in Engrosar().campos(ContextoComando(sin))}["espesor"] == "2 mm"


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
