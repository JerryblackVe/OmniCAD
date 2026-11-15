# -*- coding: utf-8 -*-
"""H-119: conjuntos de contactos (ENSAMBLAR › Activar conjuntos / Nuevo conjunto / Activar todos / Desactivar todos).
Con el análisis prendido, accionar una unión no puede meter un componente dentro de otro."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api


def _llamar(s, nombre, **args):
    return api.llamar(s, nombre, args)


def _montaje():
    """Base fija, pared fija sobre ella (x 55..65) y un pistón que desliza sobre X (hoy en x -5..5)."""
    s = api.Sesion()
    base = _llamar(s, "create_box", length=100, width=100, height=10)["result"]["bodies_created"][0]["id"]
    pist = _llamar(s, "create_box", length=10, width=10, height=10, x=300)["result"]["bodies_created"][0]["id"]
    pared = _llamar(s, "create_box", length=10, width=10, height=10, x=60, y=0, z=10)["result"]["bodies_created"][0]["id"]
    for cuerpo, nombre, fijo in ((base, "Base", True), (pist, "Piston", False), (pared, "Pared", True)):
        assert _llamar(s, "create_component", bodies=[cuerpo], name=nombre, grounded=fijo)["ok"]
    assert _llamar(s, "create_joint", origin1="<Z", body1=pist, origin2=">Z", body2=base, joint_type="slider",
                   slide_axis="X", slide=0, name="J2")["ok"]
    return s, pist


def _x_max(s, pist):
    from omnicad.nucleo import geometria as geo
    return geo.caja_envolvente(s.doc.estado_final.cuerpos[pist].forma)[1][0]


def test_sin_contactos_el_piston_atraviesa_la_pared():
    s, pist = _montaje()
    assert _llamar(s, "drive_joint", joint="J2", slide="60")["ok"]
    assert _x_max(s, pist) == pytest.approx(65)             # x 55..65: justo donde está la pared


def test_con_un_conjunto_activado_el_movimiento_se_rechaza_y_todo_queda_igual():
    s, pist = _montaje()
    r = _llamar(s, "create_contact_set", components=["Piston", "Pared"])
    assert r["ok"] and r["result"]["sets"][0]["name"] == "Conjunto de contactos1"
    assert _llamar(s, "set_contact_mode", mode="sets")["result"]["mode"] == "sets"
    assert _llamar(s, "drive_joint", joint="J2", slide="50")["ok"]            # llega justo hasta tocar: no es superposición
    r = _llamar(s, "drive_joint", joint="J2", slide="60")
    assert r["ok"] is False and r["error_kind"] == "CONTACT_BLOCKED"
    assert _x_max(s, pist) == pytest.approx(55)                                 # se quedó donde estaba
    assert _llamar(s, "set_contact_mode", mode="none")["result"]["mode"] == "none"
    assert _llamar(s, "drive_joint", joint="J2", slide="60")["ok"]            # Desactivar todos: pasa de nuevo


def test_activar_todos_vigila_aunque_no_haya_conjuntos_y_los_conjuntos_solos_no_vigilan_sin_el_par():
    s, pist = _montaje()
    assert _llamar(s, "set_contact_mode", mode="sets")["ok"]
    assert _llamar(s, "drive_joint", joint="J2", slide="60")["ok"]            # modo sets sin conjuntos: nada vigilado
    assert _llamar(s, "drive_joint", joint="J2", slide="0")["ok"]
    assert _llamar(s, "set_contact_mode", mode="all")["ok"]
    r = _llamar(s, "drive_joint", joint="J2", slide="60")
    assert r["ok"] is False and r["error_kind"] == "CONTACT_BLOCKED"


def test_conjuntos_validaciones_y_deshacer():
    s, _ = _montaje()
    assert _llamar(s, "create_contact_set", components=["Piston"])["ok"] is False                 # hacen falta 2
    assert _llamar(s, "create_contact_set", components=["Piston", "Piston"])["ok"] is False
    assert _llamar(s, "create_contact_set", components=["Piston", "Nada"])["ok"] is False
    assert _llamar(s, "create_contact_set", components=["Piston", "Pared"], name="A")["ok"]
    assert _llamar(s, "create_contact_set", components=["Pared", "Base"], name="a")["ok"] is False  # nombre repetido
    s.doc.deshacer()
    assert _llamar(s, "get_contact_sets")["result"]["sets"] == []
    s.doc.rehacer()
    assert [c["name"] for c in _llamar(s, "get_contact_sets")["result"]["sets"]] == ["A"]
    assert _llamar(s, "delete_contact_set", contact_set="A")["result"]["sets"] == []
    assert _llamar(s, "delete_contact_set", contact_set="A")["ok"] is False


def test_se_guardan_con_el_proyecto():
    from omnicad.timeline.documento import Documento
    s, _ = _montaje()
    _llamar(s, "create_contact_set", components=["Piston", "Pared"])
    _llamar(s, "set_contact_mode", mode="all")
    d = Documento.desde_dict(s.doc.a_dict())
    assert d.espacios["contactos"]["modo"] == "todos" and len(d.espacios["contactos"]["conjuntos"]) == 1


def test_accionar_uniones_de_la_ventana_rechaza_el_choque_y_no_toca_el_documento():
    """El camino de la ventana (AccionarUniones.aplicar) deshace con doc.deshacer(): no puede dejar pasos de más ni de menos."""
    from omnicad.ui.comando import ContextoComando, ErrorComando
    from omnicad.ui.comandos.ensamblar import AccionarUniones
    s, pist = _montaje()
    _llamar(s, "set_contact_mode", mode="all")
    op = next(o for o in s.doc.operaciones if getattr(o, "nombre", "") == "J2")
    antes_ops, antes_p = len(s.doc.operaciones), dict(s.doc.operacion(op.id).p)
    with pytest.raises(ErrorComando, match="chocaría"):
        AccionarUniones().aplicar({"union": op.id, "giro": "0 deg", "desliz": "60 mm"}, ContextoComando(s.doc))
    assert len(s.doc.operaciones) == antes_ops and s.doc.operacion(op.id).p == antes_p
    assert _x_max(s, pist) == pytest.approx(5)                       # el pistón sigue donde estaba
    AccionarUniones().aplicar({"union": op.id, "giro": "0 deg", "desliz": "50 mm"}, ContextoComando(s.doc))   # tocar no es chocar
    assert _x_max(s, pist) == pytest.approx(55)


@pytest.fixture(scope="module")
def ventana(tmp_path_factory):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from omnicad.ui.preferencias import Preferencias
    from omnicad.ui.ventana import VentanaPrincipal
    QApplication.instance() or QApplication([])
    ruta = tmp_path_factory.mktemp("h119") / "preferencias.ini"
    w = VentanaPrincipal(prefs=Preferencias(QSettings(str(ruta), QSettings.IniFormat)))
    yield w
    w.doc.modificado = False   # si no, close() abre «¿Guardar los cambios?» y el test se cuelga
    w.close()


def test_la_cinta_tiene_los_cuatro_comandos_activos_y_los_botones_cambian_el_modo(ventana):
    from omnicad.timeline.contactos import datos
    for clave in ("contactos_activar", "contactos_nuevo", "contactos_todos", "contactos_desactivar"):
        assert ventana.acciones[clave].isEnabled(), clave
    ventana.acciones["contactos_todos"].trigger()
    assert datos(ventana.doc)["modo"] == "todos"
    ventana.acciones["contactos_activar"].trigger()
    assert datos(ventana.doc)["modo"] == "conjuntos"
    ventana.acciones["contactos_desactivar"].trigger()
    assert datos(ventana.doc)["modo"] == "ninguno"
