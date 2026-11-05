# -*- coding: utf-8 -*-
"""SUP-29 · Encadenado (Chain Selection) en los comandos de SUPERFICIE de Fusion.

Al elegir una arista (o una cara) se toma la cadena tangente entera; la casilla la apaga y queda solo lo elegido.
Las recetas guardadas antes del encadenado, que no tienen la clave, calculan igual que antes.
"""
import inspect
import math
import os

import pytest
from OCP.BRepAdaptor import BRepAdaptor_Curve

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt                                  # noqa: E402
from PySide6.QtTest import QTest                                     # noqa: E402
from PySide6.QtWidgets import QApplication                           # noqa: E402

from omnicad import api                                              # noqa: E402
from omnicad.api import herramientas_superficie as hs                # noqa: E402
from omnicad.api import selectores as sl                             # noqa: E402
from omnicad.api.sesion import Sesion                                # noqa: E402
from omnicad.nucleo import geometria as geo                          # noqa: E402
from omnicad.restricciones import Boceto                             # noqa: E402
from omnicad.timeline import ops_superficie as ops                   # noqa: E402
from omnicad.timeline.documento import Documento                     # noqa: E402
from omnicad.timeline.operaciones import OpBoceto, operacion_desde_dict  # noqa: E402
from omnicad.ui.comando import ContextoComando, PanelComando, hit_desde_ref  # noqa: E402
from omnicad.ui.comandos import CATALOGO                             # noqa: E402
from omnicad.ui.visor3d import Visor3D                               # noqa: E402

# Las 7 operaciones de superficie que Fusion encadena (docs/brechas_superficie.md § SUP-29) y su campo de selección.
CLASES = ((ops.OpSupExtruir, "curvas"), (ops.OpSupRevolucion, "curvas"), (ops.OpParche, "contorno"),
          (ops.OpReglada, "aristas"), (ops.OpSupDesfase, "caras"), (ops.OpExtenderSup, "aristas"),
          (ops.OpDescoser, "caras"))
CLAVES_PANEL = ("sup_extruir", "sup_revolucion", "parche", "reglada", "sup_desfase", "extender_sup", "descoser")
HERRAMIENTAS = ("create_surface_extrude", "create_surface_revolve", "create_patch", "create_ruled_surface",
                "offset_surface", "extend_surface", "unstitch_surfaces")
ARCO = (25.0, 5.0, 0.0)            # punto medio de la arista del semicírculo, en el borde inferior de la U
LARGO_U = 200.0 + 50.0 * math.pi    # dos rectas de 10×10 + semicírculo de r=5 y 10 de largo


@pytest.fixture(scope="module", autouse=True)
def app_qt():
    return QApplication.instance() or QApplication([])


def _medio(arista):
    c = BRepAdaptor_Curve(arista)
    p = c.Value((c.FirstParameter() + c.LastParameter()) / 2)
    return (p.X(), p.Y(), p.Z())


def _agregar(doc, op):
    r = doc.agregar(op)
    assert r.estado in ("ok", "aviso"), r.mensaje
    return list(doc.estado_final.cuerpos.values())[-1]


def _doc_u():
    """Boceto en «U»: recta + semicírculo r=5 + recta, unidos tangentes, extruido 10 mm como superficie.
    Deja 3 caras en cadena tangente y un borde inferior libre de 3 aristas en cadena. Todo queda apartado de los
    ejes X e Y, que se usan como eje de revolución sin pinzar la superficie."""
    doc = Documento()
    boceto = Boceto()
    ids = [boceto.agregar_linea((10, 0), (20, 0)),
           boceto.agregar_arco_centro((20, 5), (20, 0), (20, 10)),
           boceto.agregar_linea((20, 10), (30, 10))]
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=boceto)
    assert doc.agregar(sk).estado == "ok"
    curvas = [{"tipo": "curva_boceto", "boceto": sk.id, "curva": i} for i in ids]
    _agregar(doc, ops.OpSupExtruir(doc.nuevo_id(), curvas=curvas, distancia="10 mm"))
    return doc


def _arista_u(doc, punto=ARCO):
    """Referencia a la arista del cuerpo en «U» cuyo punto medio está en `punto`."""
    cuerpo = list(doc.estado_final.cuerpos.values())[-1]
    elem = next(e for e in sl.listar(cuerpo.forma, "arista") if math.dist(_medio(e.sub), punto) < 1e-6)
    return sl.referencia(cuerpo, elem)


def _doc_circulo():
    """Una circunferencia r=5 partida en 3 arcos: contorno CERRADO cuya cadena tangente es exactamente él."""
    doc = Documento()
    boceto = Boceto()
    pts = [(5 * math.cos(math.radians(a)), 5 * math.sin(math.radians(a))) for a in (0, 120, 240)]
    ids = [boceto.agregar_arco_centro((0, 0), pts[i], pts[(i + 1) % 3]) for i in range(3)]
    sk = OpBoceto(doc.nuevo_id(), plano="XY", boceto=boceto)
    assert doc.agregar(sk).estado == "ok"
    return doc, [{"tipo": "curva_boceto", "boceto": sk.id, "curva": i} for i in ids]


def _llamar(sesion, nombre, **args):
    r = api.llamar(sesion, nombre, args)
    assert r.get("ok"), r
    return r["result"]


def _caja_empalmada():
    """Caja 40×20×10 con la arista +X+Z empalmada r=3: tapa, empalme y cara +X son una cadena de 3 caras tangentes."""
    s = Sesion()
    _llamar(s, "create_box", length=40, width=20, height=10)
    _llamar(s, "fillet", edges="|Y and >X and >Z", radius=3)
    return s


def _cara(s, selector):
    return _llamar(s, "find_faces", selector=selector)["faces"][0]["id"]


# ------------------------------------------------------------------ aristas: Extruir, Revolución, Reglada, Extender
@pytest.mark.parametrize("cadena, caras", [(True, 3), (False, 1)], ids=["encadenado", "solo_la_elegida"])
def test_extruir_revolucion_y_reglada_toman_toda_la_cadena_de_aristas(cadena, caras):
    casos = ((ops.OpSupExtruir, "curvas", {"distancia": "4 mm"}),
             (ops.OpSupRevolucion, "curvas", {"eje": {"tipo": "eje", "id": "Z"}, "angulo": "90 deg"}),
             (ops.OpReglada, "aristas", {"distancia": "5 mm"}))
    for clase, clave, extra in casos:
        doc = _doc_u()
        cuerpo = _agregar(doc, clase(doc.nuevo_id(), cadena=cadena, **{clave: [_arista_u(doc)]}, **extra))
        assert geo.es_valida(cuerpo.forma), clase.TIPO
        assert len(geo.caras(cuerpo.forma)) == caras, f"{clase.TIPO} con cadena={cadena}"


def test_extender_alarga_los_tres_bordes_de_la_cadena_y_no_solo_el_elegido():
    """Cada borde estirado 2 mm suma su largo: las dos rectas 10×2 cada una y el arco 5π×2 (el área sale exacta)."""
    for cadena, suma in ((True, 40 + 10 * math.pi), (False, 10 * math.pi)):
        doc = _doc_u()
        cuerpo = _agregar(doc, ops.OpExtenderSup(doc.nuevo_id(), aristas=[_arista_u(doc)], distancia="2 mm",
                                                 cadena=cadena))
        assert geo.area(cuerpo.forma) == pytest.approx(LARGO_U + suma, rel=1e-6)


# ------------------------------------------------------------------ contorno cerrado: Parche
def test_parche_con_encadenado_tapa_el_contorno_y_sin_ella_un_solo_arco_no_lo_cierra():
    for cadena, area in ((True, math.pi * 25), (False, None)):
        doc, curvas = _doc_circulo()
        r = doc.agregar(ops.OpParche(doc.nuevo_id(), contorno=curvas[:1], continuidad="G0", cadena=cadena))
        if area is None:
            assert r.estado == "error" and "cerrado" in r.mensaje, r     # solo entró el arco elegido
        else:
            assert r.estado in ("ok", "aviso"), r.mensaje
            assert geo.area(list(doc.estado_final.cuerpos.values())[-1].forma) == pytest.approx(area, rel=1e-6)


# ------------------------------------------------------------------ caras: Desfase y Descoser
@pytest.mark.parametrize("cadena, caras", [(True, 3), (False, 1)], ids=["encadenado", "solo_la_elegida"])
def test_desfase_de_superficie_encadena_las_caras_tangentes(cadena, caras):
    s = _caja_empalmada()
    r = _llamar(s, "offset_surface", faces=_cara(s, ">Z"), distance=2, chain=cadena)
    forma = s.cuerpo(r["bodies_created"][0]["id"]).forma
    assert geo.es_valida(forma)
    assert len(geo.caras(forma)) == caras


def test_desfase_de_un_cuerpo_entero_no_cambia_con_el_encadenado():
    """Lo elegido que no es una cara (un cuerpo) pasa igual: la caja entera se desfasea con la casilla en cualquier estado."""
    areas = []
    for cadena in (True, False):
        s = _caja_empalmada()
        r = _llamar(s, "offset_surface", faces="Cuerpo1", distance=2, chain=cadena)
        forma = s.cuerpo(r["bodies_created"][0]["id"]).forma
        assert geo.es_valida(forma)
        areas.append(geo.area(forma))
    assert areas[0] == pytest.approx(areas[1], rel=1e-9)


@pytest.mark.parametrize("cadena, cuerpos", [(True, 4), (False, 2)], ids=["encadenado", "solo_la_elegida"])
def test_descoser_separa_toda_la_cadena_de_caras(cadena, cuerpos):
    """Fusion: Unstitch también con un sólido; la cadena suelta la tapa, el empalme y la cara +X."""
    s = _caja_empalmada()
    _llamar(s, "unstitch_surfaces", faces=_cara(s, ">Z"), chain=cadena)
    assert len(s.doc.estado_final.cuerpos) == cuerpos
    assert all(c.tipo == "superficie" for c in s.doc.estado_final.cuerpos.values())


# ------------------------------------------------------------------ recetas viejas y valores por defecto
def test_el_paso_no_encadena_por_defecto_para_no_mover_las_recetas_viejas():
    for clase, _ in CLASES:
        assert clase.PARAMS["cadena"] is False, clase.TIPO
    doc = _doc_u()
    op = ops.OpSupExtruir(doc.nuevo_id(), curvas=[_arista_u(doc)], distancia="4 mm")
    _agregar(doc, op)
    receta = op.a_dict()
    del receta["params"]["cadena"]                      # una .omnicad guardada antes de SUP-29
    doc2 = _doc_u()
    cuerpo = _agregar(doc2, operacion_desde_dict(dict(receta, id=doc2.nuevo_id())))
    assert len(geo.caras(cuerpo.forma)) == 1            # calcula como antes: solo la arista elegida


@pytest.mark.parametrize("clave", CLAVES_PANEL)
def test_la_casilla_del_panel_viene_encendida_como_en_fusion(clave):
    campos = {c.clave: c for c in CATALOGO[clave]().campos(ContextoComando(_doc_u()))}
    assert campos["cadena"].defecto is True and not campos["cadena"].avanzado, clave


@pytest.mark.parametrize("nombre", HERRAMIENTAS)
def test_cada_herramienta_de_la_api_tiene_chain_encendido_por_defecto(nombre):
    assert inspect.signature(getattr(hs, nombre)).parameters["chain"].default is True, nombre
    h = next(x for x in api.catalogo("solido") if x["nombre"] == nombre)
    assert h["esquema"]["properties"]["chain"]["description"], nombre


def test_chain_de_la_api_llega_al_paso():
    s = Sesion()
    _llamar(s, "create_sketch", name="Perfil", plane="XY")
    _llamar(s, "draw_line", sketch="Perfil", start_x=10, start_y=0, end_x=30, end_y=0)
    curva = next(iter(s.doc.estado_final.bocetos[s.paso("Perfil").id].boceto.curvas))
    for chain in (False, True):
        _llamar(s, "create_surface_extrude", profiles={"sketch": "Perfil", "curve": curva}, distance=5, chain=chain)
        assert s.doc.operaciones[-1].p["cadena"] is chain


# ------------------------------------------------------------------ la casilla en la ventana
def test_tildar_y_destildar_la_casilla_cambia_lo_que_se_resalta_en_la_previa(app_qt):
    """Extruir superficie con una arista de la cadena: destildar el encadenado deja 1 cara y volver a tildar, 3."""
    doc = _doc_u()
    visor = Visor3D()
    visor.set_modelo(doc.estado_final)
    panel = PanelComando(CATALOGO["sup_extruir"](), ContextoComando(doc), visor,
                         {"curvas": [hit_desde_ref(_arista_u(doc), doc.estado_final)]})
    panel.show()
    emitidos = []
    panel.previa.connect(emitidos.append)
    casilla = panel.widgets["cadena"]
    caras_vistas = []
    for esperado in (False, True):
        # clic real sobre el cuadradito: el medio del widget cae fuera de él (patrón de tests/test_patrones_solidos_ui.py)
        QTest.mouseClick(casilla, Qt.MouseButton.LeftButton, pos=QPoint(6, max(casilla.height() // 2, 6)))
        assert casilla.isChecked() is panel.valores["cadena"] is esperado
        panel._calcular_previa()
        nuevo = set(emitidos[-1].cuerpos) - set(doc.estado_final.cuerpos)
        caras_vistas.append(len(geo.caras(emitidos[-1].cuerpos[nuevo.pop()].forma)))
    assert caras_vistas == [1, 3]
