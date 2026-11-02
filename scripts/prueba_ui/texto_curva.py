# -*- coding: utf-8 -*-
"""Texto en curva como lo usa una persona (B-132 a B-137, TXT-8, TXT-9): HOLA sobre un círculo sin partirlo, deslizarlo con el mouse
mirando los rellenos, elegirlo con un clic en cada letra, Extruir, Cancelar, Aceptar, reabrir y deshacer; elegir el boceto
en el navegador y el timeline; Arriba/Abajo, Espaciado en %, Voltear y Ajustar en el panel Carácter. Eventos simulados."""
import math
import sys

import numpy as np

import arnes as A
from omnicad import api
from omnicad.nucleo import fuentes
from omnicad.nucleo import geometria as geo
from omnicad.nucleo.perfiles import detectar_boceto, sin_huecos
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

AR = "TEXTO EN CURVA"
ESCALA = (2048 / 1466) ** 2                        # Arial: la altura es el alto de la A
H, O, L_, A_L, HUECO_O = (ESCALA * a for a in (150.34, 160.25, 87.83, 138.63, 206.79))
TOTAL = 10207.03 + ESCALA * 537.05                 # disco y letras: lo que tiene que estar pintado, sin los huecos
s = api.Sesion()


def L(nombre, **a):
    r = api.llamar(s, nombre, a)
    assert r["ok"], (nombre, a, r)
    return r["result"]


L("create_sketch", name="b", plane="XZ")
circulo = L("draw_circle", sketch="b", center_x=0, center_y=0, radius=57)["entities"][0]["id"]
texto = L("add_text", sketch="b", text="HOLA", font="Arial", height=30, path_entity=circulo, path_side="right",
          path_position=0.25)["entities"][0]["id"]
app, v = A.iniciar(s.doc, 1280, 720)
A.esperar(300)
op_id = s.paso("b").id


class Espia(QObject):
    """Anota toda ventana suelta que aparezca (B-136)."""
    def __init__(self):
        super().__init__()
        self.vistas = []

    def eventFilter(self, o, e):
        if e.type() == QEvent.Show and o.isWidgetType() and o.isWindow() and type(o).__name__ not in ("QMenu", "QTipLabel"):
            self.vistas.append(type(o).__name__)
        return False


def evento(w, tipo, q, boton=Qt.LeftButton, botones=Qt.LeftButton):
    QApplication.sendEvent(w, QMouseEvent(tipo, QPointF(q), QPointF(w.mapToGlobal(q)), boton, botones, Qt.NoModifier))


def clic_visor(px):
    q = QPoint(round(px[0]), round(px[1]))
    evento(v.visor, QEvent.MouseMove, q, Qt.NoButton, Qt.NoButton)
    A.esperar(60)
    evento(v.visor, QEvent.MouseButtonPress, q)
    evento(v.visor, QEvent.MouseButtonRelease, q, Qt.LeftButton, Qt.NoButton)
    A.esperar(120)


def en_pantalla(uv):
    br = v.doc.estado_final.bocetos[op_id]
    return v.visor.puntos_pantalla(np.array([br.plano.a_3d(*uv)], float))[0][0]


def perfil(area):
    br = v.doc.estado_final.bocetos[op_id]
    return min(br.perfiles, key=lambda p: abs(p.area - area))


def punto_adentro(p):
    tris = np.asarray(geo.teselar(p.cara)[0], float).reshape(-1, 3, 3)
    areas = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    centro = tris[int(np.argmax(areas))].mean(axis=0)
    br = v.doc.estado_final.bocetos[op_id]
    return float((centro - br.plano.origen) @ br.plano.u), float((centro - br.plano.origen) @ br.plano.v)


def relleno():
    """(centro en el plano del boceto, área) de lo que el visor tiene pintado como perfiles."""
    t = np.asarray(v.visor._perfiles, float).reshape(-1, 3, 3)
    a = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1) / 2
    centro = (t.mean(axis=1) * a[:, None]).sum(axis=0) / a.sum()
    pl = v.modo_boceto.plano
    return np.array([(centro - pl.origen) @ pl.u, (centro - pl.origen) @ pl.v]), float(a.sum())


def barra():
    return v.timeline.estado.toolTip()


def deslizar():
    """Arrastra el texto por la curva y mira que el relleno lo siga en cada tramo y que el disco siga pintado."""
    v.editar_operacion(op_id)
    A.esperar(500)
    modo = v.modo_boceto
    lz = modo.lienzo
    lz.visor.objetivo = lz.plano.a_3d(0, 0)
    lz.visor.distancia = 240 / 2 / math.sin(math.radians(lz.visor.fov) / 2)
    lz.visor.update()
    lz.update()
    A.esperar(300)
    t = lz.b.curvas[texto]
    pos0 = t.camino_pos
    desde = lz.a_px(*punto_adentro(perfil(H)))                        # sobre la H
    A.foto(v, "b137_antes")
    q = QPoint(round(desde[0] if isinstance(desde, tuple) else desde.x()), round(desde[1] if isinstance(desde, tuple) else desde.y()))
    evento(lz, QEvent.MouseMove, q, Qt.NoButton, Qt.NoButton)
    A.esperar(100)
    evento(lz, QEvent.MouseButtonPress, q)
    centro = lz.a_px(0, 0)
    cx, cy = (centro if isinstance(centro, tuple) else (centro.x(), centro.y()))
    r = math.hypot(q.x() - cx, q.y() - cy)
    a0 = math.atan2(q.y() - cy, q.x() - cx)
    bien = 0
    sombra = 0.0
    for paso in range(1, 13):
        ang = a0 + paso * 0.09
        evento(lz, QEvent.MouseMove, QPoint(round(cx + r * math.cos(ang)), round(cy + r * math.sin(ang))), Qt.NoButton, Qt.LeftButton)
        A.esperar(170)
        real = sin_huecos(detectar_boceto(lz.b, modo.plano, lz.geometria_real()), lz.b)
        esperado = np.average([p.centroide_uv for p in real], axis=0, weights=[p.area for p in real])
        centro_relleno, hecho = relleno()
        sombra = max(sombra, float(np.hypot(*(centro_relleno - esperado))))
        bien += bool(np.hypot(*(centro_relleno - esperado)) < 0.1 and abs(hecho - TOTAL) < 15)
        if paso == 6:
            A.foto(v, "b137_durante")
    A.reg(AR, "B-137: al deslizar, el relleno sigue a las letras y el disco queda pintado en cada tramo", bien >= 11,
          f"{bien}/12 tramos; el centro del relleno se corre {sombra:.3f} mm como mucho")
    evento(lz, QEvent.MouseButtonRelease, QPoint(round(cx + r * math.cos(a0 + 1.08)), round(cy + r * math.sin(a0 + 1.08))), Qt.LeftButton, Qt.NoButton)
    A.esperar(300)
    A.reg(AR, "el texto se movió sobre la curva", abs(lz.b.curvas[texto].camino_pos - pos0) > 0.02, f"{pos0:.3f} → {lz.b.curvas[texto].camino_pos:.3f}")
    A.foto(v, "b137_despues")
    QTest.keyClick(lz, Qt.Key_Z, Qt.ControlModifier)
    A.esperar(300)
    A.reg(AR, "Ctrl+Z vuelve el texto a su lugar", abs(lz.b.curvas[texto].camino_pos - pos0) < 1e-6)
    modo.terminar()
    A.esperar(500)


def elegir_letras():
    v.visor.vista("frente")
    v.visor.encuadrar()
    A.esperar(400)
    espia = Espia()
    app.installEventFilter(espia)
    panel = A.abrir(v, "extruir")
    app.removeEventFilter(espia)
    A.reg(AR, "B-136: abrir Extruir no muestra ninguna ventana suelta", espia.vistas == [], str(espia.vistas))
    A.reg(AR, "B-134: el disco conserva toda su área y el texto queda aparte",
          abs(perfil(10207).area - 10207.03) < 0.01 and len(v.doc.estado_final.bocetos[op_id].perfiles) == 7,
          f"{perfil(10207).area:.2f} mm², {len(v.doc.estado_final.bocetos[op_id].perfiles)} perfiles")
    letras = {"H": H, "O": O, "L": L_, "A": A_L}
    for nombre, area in letras.items():
        clic_visor(en_pantalla(punto_adentro(perfil(area))))
        n = len(panel.valores["perfiles"])
        tipos = {h["ref"]["tipo"] for h in panel.valores["perfiles"]}
        A.reg(AR, f"B-132: un clic en la {nombre} elige el texto entero", n == 4 and tipos == {"perfil"}, f"{n} perfiles, {tipos}")
        clic_visor(en_pantalla(punto_adentro(perfil(area))))
        A.reg(AR, f"otro clic en la {nombre} lo saca", panel.valores["perfiles"] == [])
    clic_visor(en_pantalla(punto_adentro(perfil(HUECO_O))))
    A.reg(AR, "B-132: un clic en el hueco de la O no elige nada", panel.valores["perfiles"] == [])
    clic_visor(en_pantalla(punto_adentro(perfil(L_))))
    A.esperar(500)
    A.foto(v, "extruir_letras")
    A.reg(AR, "con las letras elegidas Aceptar está activo", panel.boton_ok.isEnabled() and len(panel.valores["perfiles"]) == 4)
    return panel


def cancelar_y_aceptar(panel):
    pasos = A.n_ops(v)
    QTest.mouseClick(panel.boton_cancelar, Qt.LeftButton)
    A.esperar(150)
    A.reg(AR, "Cancelar no agrega pasos", A.n_ops(v) == pasos)
    A.reg(AR, "B-135: Cancelar deja la barra sin «Calculando»", not barra().startswith("Calculando"), barra())
    panel = elegir_letras()
    panel.widgets["distancia"].setText("10 mm")
    A.esperar(400)
    A.reg(AR, "B-135: terminada la previa, la barra no dice «Calculando»", not barra().startswith("Calculando"), barra())
    panel.aceptar()
    A.esperar(500)
    cuerpos = [geo.volumen(c.forma) for c in v.doc.estado_final.cuerpos.values()]
    A.reg(AR, "Aceptar da 4 letras separadas con los huecos vacíos",
          len(cuerpos) == 4 and abs(sum(cuerpos) - ESCALA * 5370.5) < 2, f"{len(cuerpos)} cuerpos, {sum(cuerpos):.1f} mm³")
    A.foto(v, "letras_extruidas")
    extrusion = v.doc.operaciones[-1]
    v.editar_operacion(extrusion.id)
    A.esperar(500)
    A.reg(AR, "reabrir muestra los 4 perfiles elegidos", v.panel is not None and len(v.panel.valores["perfiles"]) == 4)
    v.panel.cancelar()
    A.esperar(200)
    A.deshacer(v)
    A.esperar(400)
    A.reg(AR, "deshacer saca las letras", len(v.doc.estado_final.cuerpos) == 0)


def boceto_entero():
    panel = A.abrir(v, "extruir")
    def clic_boceto():                             # la previa cambia el árbol: se busca el renglón cada vez
        arbol = v.navegador.arbol
        item = next(i for i in arbol.findItems("b", Qt.MatchExactly | Qt.MatchRecursive))
        arbol.scrollToItem(item)
        A.esperar(80)
        QTest.mouseClick(arbol.viewport(), Qt.LeftButton, Qt.NoModifier, arbol.visualItemRect(item).center())
        A.esperar(300)

    clic_boceto()
    A.reg(AR, "TXT-8: elegir el boceto en el navegador toma disco y letras", len(panel.valores["perfiles"]) == 5, str(len(panel.valores["perfiles"])))
    A.foto(v, "txt8_navegador")
    A.esperar(700)                                 # dos clics seguidos serían un doble clic: renombrar
    clic_boceto()
    A.reg(AR, "otro clic lo saca", panel.valores["perfiles"] == [])
    tl = v.timeline
    for i in range(tl.lista.count()):
        it = tl.lista.item(i)
        if it.data(Qt.UserRole) == op_id:
            QTest.mouseClick(tl.lista.viewport(), Qt.LeftButton, Qt.NoModifier, tl.lista.visualItemRect(it).center())
    A.esperar(300)
    A.reg(AR, "TXT-8: elegirlo en el timeline también", len(panel.valores["perfiles"]) == 5, str(len(panel.valores["perfiles"])))
    panel.cancelar()
    A.esperar(200)


def panel_caracter():
    v.editar_operacion(op_id)
    A.esperar(500)
    modo = v.modo_boceto
    lz = modo.lienzo
    lz.editar_texto(texto, lz.a_px(*punto_adentro(perfil(H))))
    A.esperar(400)
    c = modo.caracter
    A.reg(AR, "TXT-9: el panel muestra el parámetro Text", c.parametro_texto.text() == "Text", c.parametro_texto.text())
    A.reg(AR, "TXT-9: Colocación dice Arriba y Abajo", [c.camino_colocacion.itemText(i) for i in range(2)] == ["Arriba", "Abajo"])
    A.reg(AR, "TXT-9: el espaciado va en %", c.interletraje.suffix() == " %")
    w = c.interletraje
    w.lineEdit().selectAll()
    QTest.keyClicks(w, "10")
    QTest.keyClick(w, Qt.Key_Tab)
    A.esperar(150)
    A.reg(AR, "TXT-9: teclear 10 % da el 10 % del ancho medio de Arial con altura 30", abs(lz.opciones["espaciado"] - 1.84992) < 1e-4, str(lz.opciones["espaciado"]))
    c.camino_colocacion.setCurrentIndex(1)
    A.esperar(150)
    c.camino_ajustar.setChecked(True)
    c.b_voltear_v.setChecked(True)
    A.esperar(200)
    A.foto(v, "txt9_panel")
    QTest.keyClick(lz, Qt.Key_Return, Qt.ControlModifier)
    A.esperar(300)
    t = lz.b.curvas[texto]
    A.reg(AR, "Aceptar guarda Abajo, Ajustar y Voltear", t.camino_colocacion == "abajo" and t.camino_ajustar and t.voltear_v,
          f"{t.camino_colocacion}, {t.camino_ajustar}, {t.voltear_v}")
    modo.cancelar()
    A.esperar(400)


def teclear_barra(lz, campo, escrito):
    w = lz.entrada.campos[campo]
    w.setFocus()
    w.selectAll()
    QTest.keyClicks(w, escrito)
    A.esperar(150)


def altura_y_lado():
    """Bar del texto en %, Text height al cambiar la altura y al reabrir, y el lado de un texto ya hecho."""
    A.deshacer(v)                                    # lo que dejó el panel Carácter no molesta: se parte de HOLA
    A.esperar(200)
    v.editar_operacion(op_id)
    A.esperar(500)
    modo, t0 = v.modo_boceto, s.paso("b").boceto.curvas[texto]
    lz = modo.lienzo
    lz.editar_texto(texto, lz.a_px(*punto_adentro(perfil(H))))
    A.esperar(400)
    c = modo.caracter
    A.reg(AR, "TXT-9: la barra dice Espaciado (%)", "Espaciado (%)" in [e.text() for e in lz.entrada.findChildren(QLabel)])
    A.reg(AR, "el texto viejo muestra su lado", c.camino_lado.currentData() == t0.camino_lado, c.camino_lado.currentText())
    teclear_barra(lz, 3, "20")
    A.reg(AR, "teclear 20 en la barra se ve 20 % en el panel", abs(c.interletraje.value() - 20) < 1e-6, str(c.interletraje.value()))
    lado = "izq" if t0.camino_lado == "der" else "der"
    c.camino_lado.setCurrentIndex(c.camino_lado.findData(lado))
    A.esperar(200)
    teclear_barra(lz, 1, "24")
    QTest.keyClick(lz, Qt.Key_Return, Qt.ControlModifier)
    A.esperar(300)
    modo.terminar()
    A.esperar(600)
    t = s.paso("b").boceto.curvas[texto]
    A.reg(AR, "TXT-9: cambiar el lado de un texto viejo en el panel", t.camino_lado == lado, t.camino_lado)
    A.reg(AR, "TXT-9: 24 en la barra pasa a Text height", v.doc.parametros.obtener(t.parametro_altura).expresion == "24 mm",
          v.doc.parametros.obtener(t.parametro_altura).expresion)
    cien = fuentes.espaciado_cien("Arial", 24)
    A.reg(AR, "TXT-9: el espaciado queda en 20 % del ancho medio con 24 mm", abs(t.espaciado - 0.2 * cien) < 1e-3, str(t.espaciado))
    r = api.llamar(api.Sesion(v.doc), "set_parameter", {"name": t.parametro_altura, "expression": "18 mm"})
    resuelto = v.doc.estado_final.bocetos[op_id].boceto.curvas[texto]
    A.reg(AR, "Text height cambia la altura", r["ok"] and abs(resuelto.altura - 18) < 1e-6)
    A.reg(AR, "TXT-9: con otra altura el % sigue igual", abs(resuelto.espaciado - 0.2 * cien * 18 / 24) < 1e-3, str(resuelto.espaciado))
    v.editar_operacion(op_id)
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    lz.editar_texto(texto, lz.a_px(0, 57))
    A.esperar(300)
    A.reg(AR, "reabrir muestra la altura del parámetro", lz.entrada.campos[1].text() == "18", lz.entrada.campos[1].text())
    QTest.keyClick(lz, Qt.Key_Escape)
    A.esperar(150)
    v.modo_boceto.cancelar()
    A.esperar(400)


def lado_de_un_texto_nuevo():
    v.editar_operacion(op_id)
    A.esperar(500)
    modo = v.modo_boceto
    lz = modo.lienzo
    lz.set_herramienta("texto")
    A.esperar(150)
    lz.clics.append((None, (0.0, 57.0)))
    lz._procesar_clics()
    A.esperar(300)
    A.reg(AR, "el panel muestra el lado natural de la curva", modo.caracter.camino_lado.currentData() == "der",
          str(modo.caracter.camino_lado.currentData()))
    QTest.keyClick(lz, Qt.Key_Escape)
    A.esperar(150)
    modo.cancelar()
    A.esperar(400)


def texto_nuevo_con_parametro():
    from omnicad.restricciones.boceto import Texto
    L2 = api.llamar(s, "create_sketch", {"plane": "XY", "name": "n"})
    assert L2["ok"]
    A.esperar(200)
    v.editar_operacion(s.paso("n").id)
    A.esperar(400)
    modo = v.modo_boceto
    modo.boceto.agregar_texto((0, 0), "NUEVO", altura=10)
    modo.terminar()
    A.esperar(500)
    t = next(c for c in s.paso("n").boceto.curvas.values() if isinstance(c, Texto))
    A.reg(AR, "TXT-9: un texto nuevo de la ventana crea su parámetro Text", t.parametro_texto == "Text_1", str(t.parametro_texto))
    A.reg(AR, "el parámetro tiene el contenido", v.doc.parametros.valores().get("Text_1") == "NUEVO")
    A.reg(AR, "TXT-9: y su Text height con la altura", v.doc.parametros.obtener("Text_height_1").expresion == "10 mm")
    n = len(v.doc.parametros.valores())
    A.deshacer(v)
    A.esperar(300)
    A.reg(AR, "deshacer quita boceto editado y parámetros de una vez", len(v.doc.parametros.valores()) == n - 2)


def texto_adentro_del_disco():
    """B-134 con la vista: letras apoyadas adentro del disco. Un clic en la letra elige el texto; en el hueco de la O, el disco."""
    global op_id
    L("create_sketch", name="d", plane="XZ")
    c = L("draw_circle", sketch="d", center_x=0, center_y=0, radius=57)["entities"][0]["id"]
    t = L("add_text", sketch="d", text="HOLA", font="Arial", height=12, path_entity=c, path_side="left",
          path_offset=5, path_position=0.25)["entities"][0]["id"]
    op_id = s.paso("d").id
    A.esperar(300)
    v.editar_operacion(op_id)
    A.esperar(500)
    A.foto(v, "b134_sombreado")
    pintado = np.asarray(v.visor._perfiles, float).reshape(-1, 3, 3)
    area = float((np.linalg.norm(np.cross(pintado[:, 1] - pintado[:, 0], pintado[:, 2] - pintado[:, 0]), axis=1) / 2).sum())
    br = v.doc.estado_final.bocetos[op_id]
    esperada = sum(p.area for p in sin_huecos(br.perfiles, br.boceto))   # el relleno es una malla: ~6 mm² menos; los huecos suman ~75
    A.reg(AR, "Los huecos de las letras no se pintan encima del disco", abs(area - esperada) < 20, f"{area:.1f} contra {esperada:.1f} mm²")
    v.modo_boceto.cancelar()
    A.esperar(400)
    v.visor.vista("frente")
    v.visor.encuadrar()
    A.esperar(400)
    panel = A.abrir(v, "extruir")
    chico = (12 / 30) ** 2
    clic_visor(en_pantalla(punto_adentro(perfil(L_ * chico))))
    firmas = [h["ref"]["firma"] for h in panel.valores["perfiles"]]        # adentro de la curva las letras se pisan entre ellas
    A.reg(AR, "B-134: sobre el disco, un clic en la L elige el texto y no el disco", len(firmas) >= 4 and all(f == [t] for f in firmas),
          str(len(firmas)))
    clic_visor(en_pantalla(punto_adentro(perfil(L_ * chico))))
    A.reg(AR, "otro clic lo saca", panel.valores["perfiles"] == [])
    clic_visor(en_pantalla(punto_adentro(perfil(HUECO_O * chico))))
    elegidos = panel.valores["perfiles"]
    A.reg(AR, "B-134: un clic en el hueco de la O elige el disco de abajo", len(elegidos) == 1 and elegidos[0]["ref"]["firma"] == [c],
          str([h["ref"]["firma"] for h in elegidos]))
    A.foto(v, "b134_disco_elegido")
    panel.widgets["distancia"].setText("10 mm")
    A.esperar(400)
    panel.aceptar()
    A.esperar(500)
    vol = sum(geo.volumen(k.forma) for k in v.doc.estado_final.cuerpos.values())
    A.reg(AR, "B-134: extruir el disco da el círculo entero", abs(vol - 102070.3) < 1, f"{vol:.1f} mm³")
    A.deshacer(v)
    A.esperar(400)


for nombre, f in (("deslizar", deslizar), ("letras", lambda: cancelar_y_aceptar(elegir_letras())), ("boceto", boceto_entero),
                  ("caracter", panel_caracter), ("altura", altura_y_lado), ("lado", lado_de_un_texto_nuevo),
                  ("nuevo", texto_nuevo_con_parametro), ("adentro", texto_adentro_del_disco)):
    A.correr(nombre, f)
A.reg(AR, "sin excepciones sueltas en slots de Qt", not A.ERRORES, "; ".join(A.ERRORES)[:300])
A.guardar_registro("texto_curva")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗", flush=True)
v.close()
sys.exit(0)
