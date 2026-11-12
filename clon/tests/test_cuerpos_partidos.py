# -*- coding: utf-8 -*-
"""B-116: un corte o una intersección que parte un cuerpo deja un cuerpo por parte (Unir no). B-117: Extruir pasa solo a
Cortar cuando la extrusión se mete en un sólido visible."""
import json
import math
import time
import zipfile

import pytest
from PySide6.QtCore import QPointF, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from omnicad import api
from omnicad.api.herramientas_ensamble import _simular
from omnicad.io_archivos import proyecto
from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpExtrusion, propiedades_cuerpo
from omnicad.ui.comando import hit_desde_ref
from omnicad.ui.comandos import solido
from omnicad.ui.comandos.solido import Extruir
from omnicad.ui.manipuladores import CAPA_PREVIA
from omnicad.ui.preferencias import Preferencias
from omnicad.ui.ventana import VentanaPrincipal


def ok(r):
    assert r["ok"], r
    return r["result"]


def llamar(s, nombre, **args):
    return ok(api.llamar(s, nombre, args))


def rectangulo(s, x0, y0, x1, y1, nombre=None):
    """Boceto en XY con un rectángulo; devuelve el id de su paso."""
    llamar(s, "sketch_from_spec", name=nombre, entities=[{"type": "rectangle", "corner1": [x0, y0], "corner2": [x1, y1]}])
    return s.doc.operaciones[-1].id


def cuerpos(s):
    return s.doc.estado_final.cuerpos


@pytest.fixture
def placa():
    """Placa de 100 × 40 × 10 (x 0..100, y −20..20, z 0..10)."""
    s = api.Sesion()
    llamar(s, "extrude", sketch=rectangulo(s, 0, -20, 100, 20), distance=10)
    return s


def test_corte_de_lado_a_lado_deja_dos_cuerpos(placa):
    s = placa
    llamar(s, "extrude", sketch=rectangulo(s, 45, -30, 55, 30), distance=10, operation="cut", reverse=False)
    assert len(cuerpos(s)) == 2
    assert all(len(geo.solidos(c.forma)) == 1 for c in cuerpos(s).values())
    assert sum(geo.volumen(c.forma) for c in cuerpos(s).values()) == pytest.approx(90 * 40 * 10)


def volumenes(s):
    return sorted(round(geo.volumen(c.forma), 3) for c in cuerpos(s).values())


def cruz(s, x0=45, x1=55):
    """Corte de lado a lado de la placa, de x0 a x1."""
    return llamar(s, "extrude", sketch=rectangulo(s, x0, -30, x1, 30), distance=10, operation="cut", reverse=False)


def test_la_parte_mas_grande_conserva_id_y_nombre_y_las_otras_siguen_la_numeracion(placa):
    s = placa
    cid = next(iter(cuerpos(s)))
    s.doc.propiedades[cid] = {"apariencia": [1.0, 0.0, 0.0]}
    r = cruz(s, 20, 30)
    grande, chica = cuerpos(s)[cid], next(c for k, c in cuerpos(s).items() if k != cid)
    assert (grande.nombre, round(geo.volumen(grande.forma))) == ("Cuerpo1", 70 * 40 * 10)
    assert (chica.nombre, round(geo.volumen(chica.forma))) == ("Cuerpo2", 20 * 40 * 10)
    assert chica.id == f"{r['feature']['id']}.c1" and [c["id"] for c in r["bodies_created"]] == [chica.id]
    assert propiedades_cuerpo(s.doc.propiedades, chica)["apariencia"] == [1.0, 0.0, 0.0]


def test_partes_iguales_se_ordenan_por_centro_y_recalcular_da_lo_mismo(placa):
    s = placa
    cid = next(iter(cuerpos(s)))
    cruz(s)
    foto = {k: geo.caja_envolvente(c.forma) for k, c in cuerpos(s).items()}
    assert foto[cid][1][0] == pytest.approx(45)       # a igual volumen, la de X menor conserva el id
    s.doc.olvidar_memoria()
    s.doc.recalcular()
    assert {k: geo.caja_envolvente(c.forma) for k, c in cuerpos(s).items()} == foto


def test_deshacer_y_rehacer_un_corte_que_parte(placa):
    s = placa
    cruz(s)
    llamar(s, "undo")
    assert len(cuerpos(s)) == 1
    llamar(s, "redo")
    assert volumenes(s) == [18000, 18000]


def test_interseccion_que_deja_dos_partes(placa):
    s = placa
    llamar(s, "sketch_from_spec", entities=[{"type": "rectangle", "corner1": [10, -10], "corner2": [20, 10]},
                                            {"type": "rectangle", "corner1": [50, -10], "corner2": [70, 10]}])
    llamar(s, "extrude", sketch=s.doc.operaciones[-1].id, profile="all", distance=10, operation="intersect")
    assert volumenes(s) == [2000, 4000]


def test_combinar_cortar_parte_y_consume_la_herramienta(placa):
    s = placa
    placa_id = next(iter(cuerpos(s)))
    caja = llamar(s, "create_box", length=10, width=60, height=30, x=50, z=-10)["bodies_created"][0]["id"]
    r = llamar(s, "boolean_operation", target=placa_id, tools=[caja], operation="cut")
    assert volumenes(s) == [18000, 18000] and caja not in cuerpos(s)
    assert len(r["bodies_created"]) == 1


def test_combinar_cortar_conservando_la_herramienta(placa):
    s = placa
    placa_id = next(iter(cuerpos(s)))
    caja = llamar(s, "create_box", length=10, width=60, height=30, x=50, z=-10)["bodies_created"][0]["id"]
    llamar(s, "boolean_operation", target=placa_id, tools=[caja], operation="cut", keep_tools=True)
    assert len(cuerpos(s)) == 3


def test_combinar_intersecar_parte(placa):
    s = placa
    placa_id = next(iter(cuerpos(s)))
    llamar(s, "extrude", sketch=rectangulo(s, 40, -30, 60, 10), distance=10, operation="cut", reverse=False)
    caja = llamar(s, "create_box", length=120, width=20, height=30, x=50, y=-10, z=-10)["bodies_created"][0]["id"]
    llamar(s, "boolean_operation", target=placa_id, tools=[caja], operation="intersect")
    assert volumenes(s) == [8000, 8000]


def test_unir_no_parte_y_un_corte_que_no_suma_solidos_tampoco():
    s = api.Sesion()
    a = llamar(s, "create_box", length=10, width=10, height=10)["bodies_created"][0]["id"]
    b = llamar(s, "create_box", length=10, width=10, height=10, x=30)["bodies_created"][0]["id"]
    llamar(s, "boolean_operation", target=a, tools=[b], operation="join")
    assert len(cuerpos(s)) == 1 and len(geo.solidos(cuerpos(s)[a].forma)) == 2
    llamar(s, "create_box", length=4, width=4, height=20, operation="cut", z=-5)
    assert len(cuerpos(s)) == 1 and len(geo.solidos(cuerpos(s)[a].forma)) == 2


def test_extrusion_delgada_con_curva_abierta_parte_la_placa(placa):
    s = placa
    llamar(s, "sketch_from_spec", entities=[{"type": "line", "start": [50, -30], "end": [50, 30]}])
    sk = s.doc.operaciones[-1]
    llamar(s, "extrude", sketch=sk.id, open_curves=list(s.doc.estado_final.bocetos[sk.id].boceto.curvas), thin=True,
           wall_thickness=1, wall_location="center", distance=10, operation="cut", reverse=False)
    assert volumenes(s) == pytest.approx([19800, 19800])


def test_revolucion_que_corta_parte_el_cilindro():
    s = api.Sesion()
    llamar(s, "create_cylinder", radius=20, height=60, z=-30)
    llamar(s, "sketch_from_spec", plane="XZ", entities=[{"type": "rectangle", "corner1": [0, 10], "corner2": [30, 12]}])
    llamar(s, "revolve", sketch=s.doc.operaciones[-1].id, axis="z", operation="cut")
    assert len(cuerpos(s)) == 2 and sum(volumenes(s)) == pytest.approx(math.pi * 400 * 58, rel=1e-6)


def test_barrido_que_corta_parte_la_placa(placa):
    s = placa
    perfil = rectangulo(s, 45, -30, 55, 30)
    llamar(s, "sketch_from_spec", plane="XZ", entities=[{"type": "line", "start": [50, 0], "end": [50, 20]}])
    llamar(s, "sweep", sketch=perfil, path_sketch=s.doc.operaciones[-1].id, operation="cut")
    assert volumenes(s) == [18000, 18000]


def test_primitiva_que_corta_parte_la_placa(placa):
    s = placa
    llamar(s, "create_box", length=10, width=60, height=20, x=50, z=-5, operation="cut")
    assert volumenes(s) == [18000, 18000]


@pytest.mark.parametrize("calculo", ["identical", "optimized"])
def test_patron_de_un_corte_parte_en_cada_copia(placa, calculo):
    s = placa
    corte = cruz(s, 10, 12)["feature"]["id"]
    llamar(s, "rectangular_pattern", features=[corte], x_count=3, x_spacing=30, compute=calculo)
    assert volumenes(s) == [4000, 11200, 11200, 11200]


def test_patron_de_un_corte_con_objetivo_elegido_sigue_a_las_partes(placa):
    s = placa
    cid = next(iter(cuerpos(s)))
    corte = llamar(s, "extrude", sketch=rectangulo(s, 70, -30, 72, 30), distance=10, operation="cut", reverse=False,
                   target=[cid])["feature"]["id"]
    llamar(s, "rectangular_pattern", features=[corte], x_count=2, x_spacing=15)      # la copia cae en la parte chica
    assert volumenes(s) == [5200, 5200, 28000]


def _vieja(doc):
    """La receta como la guardaba un OmniCAD anterior a B-116."""
    return {k: v for k, v in doc.a_dict().items() if k != "sin_partir"}


def test_receta_vieja_abre_igual_y_un_paso_nuevo_si_parte(placa):
    s = placa
    cid = next(iter(cuerpos(s)))
    cruz(s)
    llamar(s, "move_body", body=cid, translate=[0, 0, 7])      # un solo cuerpo: se mueven los dos sólidos
    doc = Documento.desde_dict(_vieja(s.doc))
    c = doc.estado_final.cuerpos[cid]
    assert len(doc.estado_final.cuerpos) == 1 and len(geo.solidos(c.forma)) == 2
    assert geo.volumen(c.forma) == pytest.approx(36000) and geo.caja_envolvente(c.forma)[0][2] == pytest.approx(7)
    guardada = doc.a_dict()
    assert sorted(guardada["sin_partir"]) == sorted(o.id for o in doc.operaciones)
    assert len(Documento.desde_dict(guardada).estado_final.cuerpos) == 1      # guardar y reabrir no la cambia
    s2 = api.Sesion(doc)
    llamar(s2, "create_box", length=4, width=60, height=20, x=20, z=0, operation="cut")
    assert len(cuerpos(s2)) == 3


def test_el_estudio_de_movimiento_calcula_los_pasos_viejos_como_el_documento():
    s = api.Sesion()
    base = llamar(s, "create_box", length=40, width=40, height=10)["bodies_created"][0]["id"]
    bloque = llamar(s, "create_box", length=10, width=10, height=10, x=100, y=50)["bodies_created"][0]["id"]
    llamar(s, "create_component", bodies=[base], name="Base", grounded=True)
    llamar(s, "create_component", bodies=[bloque], name="Bloque")
    llamar(s, "create_joint", origin1="<Z", body1=bloque, origin2=">Z", body2=base, joint_type="revolute")
    llamar(s, "create_box", length=4, width=60, height=20, z=-5, target=[base], operation="cut")
    doc = Documento.desde_dict(_vieja(s.doc))
    union = next(o for o in doc.operaciones if o.TIPO == "union")
    estado, _avisos, fallo = _simular(doc, union, {"rotacion": "10"})
    assert fallo is None and list(estado.cuerpos) == list(doc.estado_final.cuerpos)


def test_auto_con_una_booleana_que_falla_queda_en_cuerpo_nuevo(placa, monkeypatch):
    s = placa
    def falla(*_a):
        raise geo.ErrorGeometria("El kernel no pudo.")
    monkeypatch.setattr(geo, "solapan", falla)
    r = llamar(s, "extrude", sketch=rectangulo(s, 40, -5, 50, 5), distance=5, operation="auto")
    assert r["operation"] == "new_body"


def test_archivo_omnicad_viejo_abre_igual(placa, tmp_path):
    s = placa
    cid = next(iter(cuerpos(s)))
    cruz(s)
    nuevo, viejo = tmp_path / "nuevo.omnicad", tmp_path / "viejo.omnicad"
    proyecto.guardar(s.doc, nuevo)
    with zipfile.ZipFile(nuevo) as a, zipfile.ZipFile(viejo, "w") as b:
        for n in a.namelist():
            datos = a.read(n)
            if n == "receta.json":
                receta = json.loads(datos)
                del receta["sin_partir"]
                datos = json.dumps(receta).encode("utf-8")
            b.writestr(n, datos)
    assert len(proyecto.abrir(nuevo).estado_final.cuerpos) == 2
    abierto = proyecto.abrir(viejo)
    assert list(abierto.estado_final.cuerpos) == [cid] and len(geo.solidos(abierto.estado_final.cuerpos[cid].forma)) == 2


def test_aplicar_una_receta_vieja_cambia_el_calculo_de_los_mismos_pasos(placa):
    s = placa
    cruz(s)
    assert len(cuerpos(s)) == 2
    llamar(s, "apply_recipe", recipe=_vieja(s.doc))
    assert len(cuerpos(s)) == 1
    llamar(s, "undo")
    assert len(cuerpos(s)) == 2


def test_agregar_una_receta_vieja_conserva_sus_pasos_sin_partir(placa):
    s, otra = placa, api.Sesion()
    llamar(otra, "create_box", length=200, width=10, height=10, x=50, y=100)
    cruz(otra)
    receta = _vieja(otra.doc)
    llamar(s, "apply_recipe", recipe=receta, mode="append")
    assert len(s.doc.a_dict()["sin_partir"]) == len(receta["operaciones"])


def test_la_parte_abierta_de_la_cache_sigue_viendose_como_su_original(placa):
    s = placa
    cid = next(iter(cuerpos(s)))
    s.doc.propiedades[cid] = {"apariencia": [1.0, 0.0, 0.0]}
    cruz(s, 20, 30)
    cache = {d["indice"]: (json.loads(json.dumps(d)), f) for d, f in s.doc.pasos_para_cache(0.0)}
    abierto = Documento.desde_dict(s.doc.a_dict(), cache)
    chica = next(c for k, c in abierto.estado_final.cuerpos.items() if k != cid)
    assert propiedades_cuerpo(abierto.propiedades, chica)["apariencia"] == [1.0, 0.0, 0.0]


@pytest.fixture
def ventana(tmp_path):
    """Panel de Extruir abierto sobre un perfil de 10 × 10 en la cara de abajo de una placa de z 0..10."""
    app = QApplication.instance() or QApplication([])
    s = api.Sesion()
    llamar(s, "extrude", sketch=rectangulo(s, 0, -20, 100, 20), distance=10)
    perfil = rectangulo(s, 40, -5, 50, 5)
    v = VentanaPrincipal(s.doc, prefs=Preferencias(QSettings(str(tmp_path / "p.ini"), QSettings.IniFormat)))
    v.show()
    p = v.ejecutar_comando(Extruir())
    br = s.doc.estado_final.bocetos[perfil]
    p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": perfil, **OpExtrusion.referencia_perfil(br.perfiles[0])},
                             p.ctx.estado))
    yield v, p
    if v.panel is not None:
        v.panel.cancelar()
    v.doc.modificado = False
    v.close()
    v.deleteLater()
    app.processEvents()


def previa(p):
    """Corre las previas pendientes, como hace el temporizador del panel."""
    for _ in range(4):
        if p._t_previa.isActive():
            p._t_previa.stop()
        p._calcular_previa()
        if not p._t_previa.isActive():
            break


def arrastrar(p, valor):
    """Agarra la flecha de la distancia (una vez) y la lleva a `valor`."""
    g = p.manipuladores
    if not g.arrastrando:
        flecha = next(m for m in g.manips if getattr(m, "clave", None) == "distancia")
        a, b = flecha.puntos(g)
        puntos, visibles = g.pantalla([(a + b) / 2])
        assert visibles[0] and g.empezar_arrastre(QPointF(*puntos[0]))
    g.escribir({"distancia": float(valor)})
    previa(p)


def test_distancia_tecleada_pasa_a_cortar_y_vuelve_al_salir(ventana):
    _, p = ventana
    p.set_valor("distancia", "10 mm")
    previa(p)
    assert p.valores["operacion"] == "cortar"      # los 10 mm escritos están adentro de la placa
    p.set_valor("distancia", "-5")
    previa(p)
    assert p.valores["operacion"] == "nuevo"       # z −5..0: solo apoya en la cara, no se mete
    p.set_valor("distancia", "5")
    previa(p)
    assert p.valores["operacion"] == "cortar"


def test_arrastrar_la_flecha_pasa_a_cortar_y_vuelve_sin_kernel_mientras_no_se_mete(ventana, monkeypatch):
    v, p = ventana
    p.set_valor("distancia", "-5")
    previa(p)
    arrastrar(p, -6)
    llamadas, original = [], v.doc.previsualizar
    monkeypatch.setattr(v.doc, "previsualizar", lambda *a, **k: llamadas.append(a) or original(*a, **k))
    arrastrar(p, -12)
    assert p.valores["operacion"] == "nuevo" and llamadas == []       # afuera de la caja: solo el prisma
    arrastrar(p, 5)
    assert p.valores["operacion"] == "cortar" and p.manipuladores.arrastrando
    assert p._previa_ok and CAPA_PREVIA in v.visor._capas       # la herramienta en rojo
    arrastrar(p, -5)
    assert p.valores["operacion"] == "nuevo"
    arrastrar(p, 7)
    p.manipuladores.soltar()
    previa(p)
    assert p.valores["operacion"] == "cortar"


def test_elegir_operacion_a_mano_queda_fija_hasta_cerrar(ventana):
    _, p = ventana
    previa(p)
    p.set_valor("operacion", "nuevo")
    p.set_valor("distancia", "6")
    previa(p)
    assert p.valores["operacion"] == "nuevo"
    p.set_valor("distancia", "-6")
    p.set_valor("operacion", "cortar")
    previa(p)
    assert p.valores["operacion"] == "cortar"      # tampoco vuelve solo


def test_aceptar_enseguida_de_teclear_ya_corta(ventana):
    v, p = ventana
    p.set_valor("distancia", "-5")
    previa(p)
    p.set_valor("distancia", "10")                 # sin esperar la previa: Enter pega con el temporizador en marcha
    p.aceptar()
    assert v.panel is None and v.doc.operaciones[-1].p["operacion"] == "cortar"
    assert geo.volumen(next(iter(v.doc.estado_final.cuerpos.values())).forma) == pytest.approx(100 * 40 * 10 - 1000)


def test_un_paso_reabierto_no_cambia_de_operacion(ventana):
    v, p = ventana
    p.set_valor("operacion", "nuevo")
    p.set_valor("distancia", "5")
    previa(p)
    p.aceptar()
    assert v.doc.operaciones[-1].p["operacion"] == "nuevo"
    v.editar_operacion(v.doc.operaciones[-1].id)
    p2 = v.panel
    p2.set_valor("distancia", "6")
    previa(p2)
    assert p2.valores["operacion"] == "nuevo"


def test_un_cuerpo_oculto_no_cuenta(ventana):
    v, p = ventana
    previa(p)
    p.cancelar()
    cid = next(iter(v.doc.estado_final.cuerpos))
    v.ocultos.add(cid)
    p = v.ejecutar_comando(Extruir(), valores=None)
    perfil = v.doc.operaciones[-1].id
    br = v.doc.estado_final.bocetos[perfil]
    p._elegida(hit_desde_ref({"tipo": "perfil", "boceto": perfil, **OpExtrusion.referencia_perfil(br.perfiles[0])},
                             p.ctx.estado))
    previa(p)
    assert p.valores["operacion"] == "nuevo"


def test_con_cuerpo_pesado_el_comun_va_al_proceso_aparte(ventana, monkeypatch):
    _, p = ventana
    c = p.comando
    p.set_valor("distancia", "-5")
    previa(p)
    monkeypatch.setattr(solido, "CARAS_PESADAS", 1)
    comunes = []
    monkeypatch.setattr(geo, "solapan", lambda *a: comunes.append(a))
    p.set_valor("distancia", "5")
    previa(p)
    assert comunes == []                           # un fallo dentro de la previa lo tragaría el panel
    assert c._hijo is not None and p.valores["operacion"] == "nuevo"
    fin = time.monotonic() + 60
    while c._hijo is not None and time.monotonic() < fin:
        QTest.qWait(50)
    assert c._hijo is None and p.valores["operacion"] == "cortar"


def test_el_proceso_aparte_se_cancela_al_cerrar_el_panel(ventana, monkeypatch):
    _, p = ventana
    c = p.comando
    p.set_valor("distancia", "-5")
    previa(p)
    monkeypatch.setattr(solido, "CARAS_PESADAS", 1)
    p.set_valor("distancia", "5")
    previa(p)
    assert c._hijo is not None
    p.cancelar()
    assert c._hijo is None             # el trabajador sigue vivo: test_previa_trabajador.py


def test_auto_en_la_api_corta_si_se_mete_y_si_no_crea_un_cuerpo(placa):
    s = placa
    r = llamar(s, "extrude", sketch=rectangulo(s, 40, -5, 50, 5), distance=5, operation="auto")
    assert r["operation"] == "cut" and s.doc.operaciones[-1].p["operacion"] == "cortar"
    assert volumenes(s) == [40000 - 500]
    r = llamar(s, "extrude", sketch=rectangulo(s, 70, -5, 80, 5), distance=-5, operation="auto")
    assert r["operation"] == "new_body" and len(cuerpos(s)) == 2       # z −5..0: solo apoya en la cara
    r = llamar(s, "extrude", sketch=rectangulo(s, 45, -30, 55, 30), distance=10)
    assert "operation" not in r and s.doc.operaciones[-1].p["operacion"] == "nuevo"


def test_auto_en_la_api_ignora_lo_oculto_y_respeta_target(placa):
    s = placa
    cid = next(iter(cuerpos(s)))
    sk = rectangulo(s, 40, -5, 50, 5)
    s.doc.set_propiedad(["__navegador__"], "ocultos", [cid])
    assert llamar(s, "extrude", sketch=sk, distance=5, operation="auto")["operation"] == "new_body"
    llamar(s, "undo")
    assert llamar(s, "extrude", sketch=sk, distance=5, operation="auto", target=[cid])["operation"] == "cut"


def test_solapan_no_cuenta_apoyarse():
    a = geo.caja(10, 10, 10)
    assert not geo.solapan(a, geo.caja(10, 10, 10, (0, 0, 10)))
    assert not geo.solapan(a, geo.caja(4, 4, 4, (20, 0, 0)))
    assert geo.solapan(a, geo.caja(4, 4, 4, (8, 8, 8)))
    assert geo.solapan(a, geo.caja(1, 1, 1, (5, 5, 5)))           # adentro del todo
