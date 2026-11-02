# -*- coding: utf-8 -*-
"""Fase C · asas de arrastre (manipuladores) de los comandos de Superficie y Sólido, con eventos de mouse simulados
al visor (no mueve el cursor real). Por cada asa: arrastrar, ver que el valor del panel cambie lo esperado y que la vista
previa siga andando; arrastrar hacia el otro lado y ver el tope."""
import json
import math
import sys
import types
from collections import Counter

import arnes as A
import escena
import numpy as np
from omnicad import api
from omnicad.ui import manipuladores as mp
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
AR = "ASAS"
caja, cil, tubo = ids["caja"], ids["cil"], ids["tubo"]


def mover_sim(w, pos):
    p = QPointF(pos)
    QApplication.sendEvent(w, QMouseEvent(QEvent.MouseMove, p, w.mapToGlobal(p), Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def arrastrar(panel, g, desde, hasta, pasos=6):
    """Press en `desde`, mueve en `pasos` tramos y suelta en `hasta` (puntos 3D del mundo)."""
    xy, ok = g.pantalla([desde, hasta])
    if not ok.all():
        return False
    a, b = (QPointF(*q) for q in xy)
    vis = panel.visor
    mover_sim(vis, a)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, a, vis.mapToGlobal(a), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for i in range(1, pasos + 1):
        q = a + (b - a) * (i / pasos)
        QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseMove, q, vis.mapToGlobal(q), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
        A.esperar(15)
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, b, vis.mapToGlobal(b), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(120)
    panel._t_previa.stop()
    panel._calcular_previa()
    return True


# ---------------------------------------------------------------- auditoría visual (H-60): cada asa en 4 vistas
AUDITORIA, VECES = [], Counter()
LARGO_NOMINAL = {"Flecha": mp.LARGO_FLECHA, "Triada": mp.LARGO_TRIADA * 0.8}      # px que mide un eje de frente a la cámara


def camara(vis, atras):
    """Cámara que mira hacia -atras (R: derecha, arriba, atrás)."""
    atras = mp.unitario(atras)
    ref = np.array([0.0, 0.0, 1.0]) if abs(atras[2]) < 0.95 else np.array([0.0, 1.0, 0.0])
    der = mp.unitario(np.cross(ref, atras))
    vis.R = np.array([der, np.cross(atras, der), atras])
    vis.encuadrar()


def direcciones(g):
    """(eje principal de las flechas, eje del primer arco o None) de los manipuladores del comando."""
    d0, d1 = None, None
    for m in g.manips:
        if isinstance(m, mp.Flecha) and not isinstance(m, (mp.AsaRadial, mp.FlechaCalcomania)) and d0 is None:
            d0 = np.asarray(m.direccion, float)
        elif isinstance(m, mp.Triada) and d0 is None:
            d0 = m.ejes[2] if m.claves[2] is not None else m.ejes[0]
        elif isinstance(m, mp.Angulo) and d1 is None:
            d1 = np.asarray(m.eje, float)
    return d0, d1


def huella_script(g):
    """Puntos de pantalla sobre las líneas de todas las asas (se calcula aquí para medir también el código viejo)."""
    pts = []
    for m in g.manips:
        for pr in m.dibujar(g, None):
            if pr[0] == "lineas" and len(pr[1]) > 1:
                d = np.asarray(pr[1], float).reshape(-1, 3)
                d = d[:len(d) - len(d) % 2]
                a, b = d[0::2], d[1::2]
                pts += [a + (b - a) * t for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
    if not pts:
        return np.zeros((0, 2))
    s_, ok = g.pantalla(np.concatenate(pts))
    return s_[ok]


def medir_vista(g):
    """{largo_min: razón del largo visible de la flecha más corta, cajas_sobre_asa, cajas_solapadas}."""
    razones = []
    for m in g.manips:
        if isinstance(m, mp.Flecha) and not isinstance(m, (mp.AsaRadial, mp.FlechaCalcomania)):
            a, b = m.puntos(g)
            sp, ok = g.pantalla([a, b])
            razones.append(float(np.linalg.norm(sp[1] - sp[0])) / LARGO_NOMINAL["Flecha"])
        elif isinstance(m, mp.Triada):
            partes, _k = m._partes(g)
            for sub, poli in partes:
                if sub[0] == "eje":
                    sp, ok = g.pantalla(poli)
                    razones.append(float(np.linalg.norm(sp[-1] - sp[0])) / LARGO_NOMINAL["Triada"])
    huella = huella_script(g)
    rects = [c.geometry() for c in g.cajas.values() if c.isVisible()]
    sobre = 0
    for r in rects:
        x, y = huella[:, 0], huella[:, 1]
        if len(huella) and np.count_nonzero((x >= r.left() - 3) & (x <= r.right() + 3) & (y >= r.top() - 3) & (y <= r.bottom() + 3)):
            sobre += 1
    solapadas = sum(rects[i].intersects(rects[j]) for i in range(len(rects)) for j in range(i + 1, len(rects)))
    return {"largo_min": round(min(razones), 2) if razones else None, "cajas": len(rects), "cajas_sobre_asa": sobre,
            "cajas_solapadas": solapadas}


def auditar_vistas(p, g, clave):
    """4 vistas por comando: de frente al eje, de costado, isométrica y alineada al arco. Mide el largo visible de las flechas
    y si una caja de valor tapa un asa u otra caja; deja una hoja con las 4 capturas recortadas en torno a las asas."""
    VECES[clave] += 1
    nombre = clave if VECES[clave] == 1 else f"{clave}_{VECES[clave]}"
    vis = p.visor
    d0, d1 = direcciones(g)
    d0 = np.array([0.0, 0.0, 1.0]) if d0 is None else d0
    lateral = mp.perpendiculares(d0)
    vistas = {"frente al eje": lambda: camara(vis, d0), "de costado": lambda: camara(vis, lateral[0]),
              "iso": lambda: (vis.vista("iso"), vis.encuadrar()),
              "alineada al arco": lambda: camara(vis, d1 if d1 is not None else lateral[1])}
    hoja, fila = [], {"comando": nombre, "vistas": {}}
    for titulo, poner in vistas.items():
        poner()
        g.redibujar()
        A.esperar(60)
        medida = medir_vista(g)
        fila["vistas"][titulo] = medida
        img = vis.grab().toImage()
        h = huella_script(g)
        if len(h):
            cx, cy = (h.min(axis=0) + h.max(axis=0)) / 2
        else:
            cx, cy = img.width() / 2, img.height() / 2
        ancho, alto = 420, 330
        x0 = int(max(0, min(img.width() - ancho, cx - ancho / 2)))
        y0 = int(max(0, min(img.height() - alto, cy - alto / 2)))
        corte = img.copy(x0, y0, min(ancho, img.width()), min(alto, img.height()))
        pint = QPainter(corte)
        pint.fillRect(0, 0, corte.width(), 18, QColor(0, 0, 0, 170))
        pint.setPen(QColor(255, 255, 255))
        pint.drawText(4, 13, f"{nombre} · {titulo} · largo {medida['largo_min']} · cajas {medida['cajas']}/{medida['cajas_sobre_asa']}/{medida['cajas_solapadas']}")
        pint.end()
        hoja.append(corte)
    sal = QImage(sum(i.width() for i in hoja), max(i.height() for i in hoja), QImage.Format_RGB32)
    sal.fill(QColor(40, 40, 40))
    pint = QPainter(sal)
    x = 0
    for i in hoja:
        pint.drawImage(x, 0, i)
        x += i.width()
    pint.end()
    sal.save(str(A.CAPTURAS / f"asas_{nombre}.png"))
    AUDITORIA.append(fila)
    vis.vista("iso")
    vis.encuadrar()
    g.redibujar()


def probar_triada_seccion(p, g, nombre):
    """Tríada de Análisis de sección: eje de la normal → Distancia, arco → Ángulo, Esc en la caja y ventanas chicas."""
    vis = p.visor
    camara(vis, np.array([1.0, -1.0, 0.7]))
    g.redibujar()
    for sub, clave, texto in ((("eje", 2), "desfase", "eje → Distancia"), (("giro", 0), "angulo", "arco → Ángulo")):
        t = next(x for x in g.manips if isinstance(x, mp.Triada))
        poli = dict(t._partes(g)[0])[sub]
        sp, _ok = g.pantalla(poli)
        medio = sp[len(sp) // 2]
        tang = sp[min(len(sp) - 1, len(sp) // 2 + 1)] - sp[max(0, len(sp) // 2 - 1)]
        tang = tang / np.linalg.norm(tang)
        antes = g.valor(clave)
        ok = arrastrar(p, g, *[x for x in _a_mundo(vis, medio, tang)])
        A.reg(nombre, f"tríada: arrastrar {texto}", ok and abs(g.valor(clave) - antes) > 0.5, f"{antes:g} → {g.valor(clave):g}")
    # un valor tecleado en la caja al lado y Esc
    sub_antes = g.valor("desfase")
    g._arrastre = {"m": next(x for x in g.manips if isinstance(x, mp.Triada)), "sub": ("eje", 2), "estado": {}}
    g.sincronizar_cajas()
    caja = g.cajas.get("desfase")
    A.reg(nombre, "tríada: la caja de valor aparece junto al eje", caja is not None and not caja.isHidden(), "")
    if caja is not None:
        caja.setFocus()
        caja.selectAll()
        QTest.keyClicks(caja, "7 mm")
        QTest.keyClick(caja, Qt.Key_Return)
        A.reg(nombre, "tríada: teclear 7 mm y Enter cambia Distancia", abs(g.valor("desfase") - 7) < 1e-6, f"{sub_antes:g} → {g.valor('desfase'):g}")
    g._arrastre = None
    g.sincronizar_cajas()
    for ancho, alto in ((1024, 640), (800, 520)):
        v.resize(ancho, alto)
        A.esperar(200)
        vis.encuadrar()
        g._arrastre = {"m": next(x for x in g.manips if isinstance(x, mp.Triada)), "sub": ("eje", 2), "estado": {}}
        g.redibujar()
        medida = medir_vista(g)
        g._arrastre = None
        g.redibujar()
        A.reg(nombre, f"tríada en ventana {ancho}x{alto}: caja sin tapar el asa", medida["cajas_sobre_asa"] == 0 and medida["cajas_solapadas"] == 0, str(medida))
    v.resize(1900, 1000)
    A.esperar(200)


def _a_mundo(vis, medio, tang):
    """(punto3d en el plano de la cámara bajo el píxel `medio`, ese punto corrido 40 px en `tang`)."""
    o, r = vis.rayo(QPointF(*medio))
    o2, r2 = vis.rayo(QPointF(*(medio + tang * 40)))
    p0 = np.asarray(o, float) + np.asarray(r, float) * vis.distancia
    p1 = np.asarray(o2, float) + np.asarray(r2, float) * vis.distancia
    return p0, p1


def fijar_trazo(p, vals, nombre):
    """Caja, cilindro, esfera y toroide siguen al mouse, sin botón, para dar el tamaño hasta el primer clic (como Fusion). Una
    persona lo prueba moviendo el mouse, lo fija con un clic y escribe los valores que quiere antes de tomar las asas. True
    si había un trazo en curso."""
    g = p.manipuladores
    if g is None or g.trazo is None:
        return False
    m = next((x for x in g.manips if isinstance(x, mp.AsaRadial)), None)
    if m is None:
        return False
    antes = g.valor(m.clave)
    xy, ok = g.pantalla([m.origen + m.direccion * 8.0])             # 8 mm del centro, hacia el asa
    if not ok.all():
        return False
    vis, q = p.visor, QPointF(*xy[0])
    mover_sim(vis, q)
    A.esperar(60)
    A.reg(nombre, f"mover el mouse sin botón dibuja «{m.clave}»", abs(g.valor(m.clave) - antes) > 1e-6 and g.trazo is not None,
          f"{antes:g} → {g.valor(m.clave):g}")
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, q, vis.mapToGlobal(q), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, q, vis.mapToGlobal(q), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
    A.esperar(60)
    fijado = g.valor(m.clave)
    mover_sim(vis, QPointF(q.x() + 40, q.y() + 25))
    A.esperar(60)
    A.reg(nombre, "un clic fija el trazo: el mouse ya no cambia el tamaño", g.trazo is None and abs(g.valor(m.clave) - fijado) < 1e-9,
          f"{fijado:g} → {g.valor(m.clave):g}")
    for k, x in vals.items():                                        # y se vuelven a escribir los valores de la prueba
        p.set_valor(k, x)
    p._t_previa.stop()
    p._calcular_previa()
    A.esperar(150)
    return True


def probar(clave, sel, vals, foto=None):
    nombre = f"{AR} · {clave}"
    A.MODALES.clear()
    p = A.abrir(v, clave)
    if p is None:
        A.reg(nombre, "abrir", False, f"{A.MODALES[-1:]}")
        return
    try:
        for campo, fn in sel.items():
            A.elegir(p, campo, *fn())
        for k, x in vals.items():
            p.set_valor(k, x)
        p._t_previa.stop()
        p._calcular_previa()
        A.esperar(150)
        g = p.manipuladores
        if g is None or not g.manips:
            A.reg(nombre, "tiene asas en la vista", False, "el comando no muestra ninguna asa")
            p.cancelar()
            return
        tipos = [(type(m).__name__, getattr(m, "clave", None)) for m in g.manips]
        A.reg(nombre, "asas en la vista", True, str(tipos))
        if fijar_trazo(p, vals, nombre):
            g = p.manipuladores
        if foto:
            A.foto(v, foto)
        auditar_vistas(p, g, clave)
        for m in list(g.manips):
            tn, cl = type(m).__name__, getattr(m, "clave", None)
            try:
                if isinstance(m, mp.Angulo) and not isinstance(m, mp.GiroCalcomania):
                    m = next(x for x in g.manips if isinstance(x, mp.Angulo) and x.clave == cl)       # las asas se rehacen en cada cambio
                    antes = g.valor(cl)
                    centro = np.asarray(m.centro, float)
                    d = m.asa(g) - centro
                    eje = np.asarray(m.eje, float)
                    a30 = math.radians(30)
                    objetivo = centro + d * math.cos(a30) + np.cross(eje, d) * math.sin(a30)
                    ok = arrastrar(p, g, m.asa(g), objetivo)
                    despues = g.valor(cl)
                    A.reg(nombre, f"arrastrar asa de ángulo «{cl}» 30°", ok and abs(despues - antes) > 5,
                          f"{antes:g}° → {despues:g}°; previa_ok={p._previa_ok}; «{p.mensaje.text()}»")
                elif isinstance(m, mp.Flecha) and not isinstance(m, (mp.FlechaCalcomania,)):
                    texto_antes = p.valores.get(cl)
                    antes = g.valor(cl)
                    a, b = m.puntos(g)
                    medio = (a + b) / 2
                    mm = 3.0
                    ok = arrastrar(p, g, medio, medio + m.direccion * mm)
                    despues = g.valor(cl)
                    esperado = mm / (m.factor or 1.0)
                    A.reg(nombre, f"arrastrar flecha «{cl}» {mm:g} mm", ok and abs((despues - antes) - esperado) < max(0.35, abs(esperado) * 0.1),
                          f"{antes:g} → {despues:g} (esperado +{esperado:g}); previa_ok={p._previa_ok}; «{p.mensaje.text()}»")
                    # hacia el otro lado, pasando por cero: tope
                    a, b = m.puntos(g)
                    medio = (a + b) / 2
                    ok = arrastrar(p, g, medio, medio - m.direccion * (abs(despues) + 6) * (m.factor or 1.0))
                    final = g.valor(cl)
                    A.reg(nombre, f"flecha «{cl}» arrastrada más allá del cero", ok,
                          f"{despues:g} → {final:g} (mínimo {m.minimo}); previa_ok={p._previa_ok}; «{p.mensaje.text()}»")
                    # el tope puede dejar un valor sin sentido (cero); se escribe de nuevo el de antes y la previa se recupera
                    p.set_valor(cl, texto_antes)
                    p._t_previa.stop()
                    p._calcular_previa()
                    A.esperar(150)
                    A.reg(nombre, f"flecha «{cl}»: al escribir de nuevo {texto_antes!r} la previa se recupera", p._previa_ok,
                          f"{final:g} → {g.valor(cl):g}; previa_ok={p._previa_ok}; «{p.mensaje.text()}»")
                elif isinstance(m, mp.AsaCantidad):
                    antes = int(g.valor(cl))
                    m = next(x for x in g.manips if isinstance(x, mp.AsaCantidad) and x.clave == cl)      # las asas se rehacen en cada cambio
                    asa, _pt, t = m._asa(g)
                    ok = arrastrar(p, g, asa, asa + t * m.paso * 2)
                    despues = int(g.valor(cl))
                    A.reg(nombre, f"asa de cantidad «{cl}» +2 copias", ok and despues == antes + 2,
                          f"{antes} → {despues}; previa_ok={p._previa_ok}; «{p.mensaje.text()}»")
                    m = next(x for x in g.manips if isinstance(x, mp.AsaCantidad) and x.clave == cl)
                    asa, _pt, t = m._asa(g)
                    ok = arrastrar(p, g, asa, asa - t * m.paso * (despues + 5))
                    A.reg(nombre, f"asa de cantidad «{cl}» no baja de una copia", ok and int(g.valor(cl)) == 1, str(g.valor(cl)))
                elif isinstance(m, mp.AsaRuta):
                    antes = g.valor(cl)
                    i = int(np.searchsorted(m.ts, 0.9))
                    ok = arrastrar(p, g, m.asa(g), m.puntos_ruta[i])
                    despues = g.valor(cl)
                    A.reg(nombre, f"asa de ruta «{cl}» llevada al 90 % del largo", ok and abs(despues / m.factor - 0.9) < 0.05,
                          f"{antes:g} → {despues:g}; previa_ok={p._previa_ok}; «{p.mensaje.text()}»")
                    ok = arrastrar(p, g, m.asa(g), m.puntos_ruta[-1])
                    A.reg(nombre, f"asa de ruta «{cl}» al final de lo que admite", ok and g.valor(cl) / m.factor > min(1.1, m.ts[-1] - 0.05),
                          f"{g.valor(cl):g}; previa_ok={p._previa_ok}")
                elif isinstance(m, mp.AsaLista):
                    m = next(x for x in g.manips if isinstance(x, mp.AsaLista) and x.clave == cl)       # las asas se rehacen en cada cambio
                    antes = str(p.valores.get(cl))
                    sig = next((t for t, n in m.opciones if n > m.actual), None)
                    objetivo = m.origen + m.direccion * next(n for t, n in m.opciones if t == sig) * m.factor if sig else m._asa()
                    ok = arrastrar(p, g, m._asa(), objetivo)
                    A.reg(nombre, f"asa de lista «{cl}» salta a la opción siguiente", ok and sig is not None and str(p.valores.get(cl)) == sig,
                          f"{antes} → {p.valores.get(cl)} (esperado {sig}); previa_ok={p._previa_ok}; «{p.mensaje.text()}»")
                elif isinstance(m, mp.Triada) and clave == "seccion":
                    probar_triada_seccion(p, g, nombre)
                elif isinstance(m, mp.Posicion):
                    A.reg(nombre, f"asa de posición ({tn}) presente", True, "no se arrastra en esta prueba")
                else:
                    A.reg(nombre, f"asa {tn} «{cl}»", True, "tipo sin prueba automática")
            except Exception as e:  # noqa: BLE001
                A.reg(nombre, f"asa {tn} «{cl}»: EXCEPCIÓN", False, f"{type(e).__name__}: {e}")
        # la vista previa tras los arrastres
        A.reg(nombre, "la vista previa sigue andando tras arrastrar", p._previa_ok, p.mensaje.text())
        # lo arrastrado se acepta y queda en el paso
        n0 = A.n_ops(v)
        valores = {k: p.valores.get(k) for k in vals}
        if p._previa_ok and p.ultima_op is not None:
            p.aceptar()
            A.esperar(300)
            ok = A.n_ops(v) == n0 + 1
            A.reg(nombre, "aceptar tras arrastrar crea el paso", ok, f"valores finales {valores}")
            while A.n_ops(v) > n0:
                A.deshacer(v)
        else:
            p.cancelar()
    except Exception as e:  # noqa: BLE001
        A.reg(nombre, "EXCEPCIÓN", False, f"{type(e).__name__}: {e}")
        if v.panel is not None and v.panel.isVisible():
            v.panel.cancelar()
    A.esperar(100)


per = lambda nombre, i=0: (lambda: [A.hit_perfil(v, s, nombre, i)])  # noqa: E731
cur = lambda nombre, i=0: (lambda: [A.hit_curva(v, s, nombre, i)])  # noqa: E731
cara = lambda cid, **k: (lambda: [A.hit_cara(v, cid, **k)])  # noqa: E731
arista = lambda cid, **k: (lambda: [A.hit_arista(v, cid, **k)])  # noqa: E731
cuerpo = lambda cid: (lambda: [A.hit_cuerpo(v, cid)])  # noqa: E731
eje = lambda i: (lambda: [A.hit_eje(v, i)])  # noqa: E731
pl = lambda: [A.hit_plano(v, "XY")]  # noqa: E731
top = cara(caja, normal=(0, 0, 1))

# Construir
def vertice_de(cid):
    def f():
        from omnicad.nucleo import referencias as refs
        from OCP.BRep import BRep_Tool
        for vt in refs.subformas(v.doc.estado_final.cuerpos[cid].forma, "vertice"):
            q = BRep_Tool.Pnt_s(vt)
            h = A._clic_en(v, (q.X(), q.Y(), q.Z()), {"vertice"})
            if h is not None:
                return [h]
        return [None]
    return f


probar("pestana", {"curvas": cur("Lin")}, {"tipo": "contorno", "distancia": "10 mm", "direccion": "dos_lados", "distancia2": "6 mm"})
probar("seccion", {"plano": pl}, {"desfase": "5 mm"})
probar("barrido", {"perfiles": per("Circ"), "ruta": cur("Ruta")}, {"distancia": "0.8"})
probar("sup_barrido", {"perfil": cur("Circ"), "ruta": cur("Ruta")}, {})
probar("plano_ruta", {"r0": cur("Ruta")}, {"posicion": "0.5"}, "asas_plano_ruta")
probar("punto_ruta", {"r0": cur("Ruta")}, {"posicion": "0.5"})
probar("plano_tangente", {"r0": cara(cil)}, {"angulo": "20 deg"})
probar("plano_perpendicular", {"r0": top, "r1": vertice_de(caja)}, {"desfase": "2 mm"})

# Superficie
probar("sup_extruir", {"curvas": cur("Circ")}, {"distancia": "15 mm"}, "asas_sup_extruir")
probar("sup_revolucion", {"curvas": cur("RevL"), "eje": eje("Z")}, {"angulo": "90 deg"})
probar("sup_desfase", {"caras": cara(tubo)}, {"distancia": "3 mm"})
probar("extender_sup", {"aristas": arista(tubo, lineal=False)}, {"distancia": "5 mm"})
probar("reglada", {"aristas": arista(tubo, lineal=False)}, {"tipo": "tangente", "distancia": "5 mm"})
probar("engrosar", {"caras": cuerpo(tubo)}, {"espesor": "2 mm"})
probar("sup_empalme", {"aristas": lambda: [A.hit_arista(v, ids["quilt"], lineal=True, cerca=(110, -10, 5))]}, {"medida": "1 mm"})
# Sólido · crear
probar("extruir", {"perfiles": per("Rect")}, {"distancia": "15 mm"}, "asas_extruir")
probar("extruir", {"perfiles": per("Rect")}, {"distancia": "15 mm", "direccion": "simetrica"})
probar("extruir", {"perfiles": per("Rect")}, {"distancia": "15 mm", "conicidad": "5 deg"})
probar("revolucion", {"perfiles": per("Rect"), "eje": eje("X")}, {"extension": "angulo", "angulo": "90 deg"})
probar("fijacion", {"posiciones": arista(cil, lineal=False)}, {"familia": "tornillo"})
probar("agujero", {"colocacion": top}, {"diametro": "6 mm", "profundidad": "8 mm"}, "asas_agujero")
probar("caja", {"centro": pl}, {"ancho": "10 mm", "largo": "20 mm", "alto": "5 mm"}, "asas_caja")
probar("cilindro", {"centro": pl}, {"diametro": "10 mm", "alto": "20 mm"})
probar("esfera", {"centro": pl}, {"diametro": "10 mm"})
probar("toroide", {"centro": pl}, {"diametro": "20 mm", "diametro_tubo": "4 mm"})
# Sólido · modificar
probar("empalme_3d", {"aristas": arista(caja)}, {"radio": "2 mm"})
probar("chaflan_3d", {"aristas": arista(caja)}, {"distancia": "2 mm"})
probar("pulsar_tirar", {"objetos": top}, {"distancia": "3 mm"})
probar("vaciado", {"caras": top}, {"espesor_interior": "2 mm"})
probar("desmoldeo", {"plano": top, "caras": cara(caja, normal=(1, 0, 0))}, {"angulo": "5 deg"})
probar("escala_3d", {"entidades": cuerpo(caja)}, {"factor": "2"})
probar("mover_copiar", {"cuerpos": cuerpo(caja)}, {"tipo": "libre", "dx": "10 mm", "dy": "5 mm", "dz": "0 mm"}, "asas_mover")
probar("patron_rectangular_3d", {"cuerpos": cuerpo(caja), "dir1": eje("X")}, {"n1": 3, "d1": "12 mm", "distribucion": "espaciado"})
probar("patron_circular_3d", {"cuerpos": cuerpo(caja), "eje": eje("Z")}, {"n": 4, "angulo_paso": "40 deg", "modo": "espaciado"})
probar("patron_ruta", {"cuerpos": cuerpo(caja), "ruta": cur("Ruta")}, {"rn": 3, "rd": "8 mm", "distribucion": "espaciado"})


def probar_gizmo_lienzo(clave="lienzo"):
    """Gizmo del Lienzo / Calcomanía (mover, flechas, giro, escala, volteos) arrastrado con mouse simulado."""
    import tempfile
    from pathlib import Path

    from PIL import Image
    nombre = f"{AR} · gizmo {clave}"
    es_svg = clave == "insertar_svg"
    ruta = Path(tempfile.mkdtemp()) / ("dibujo.svg" if es_svg else "imagen.png")
    if es_svg:
        ruta.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"><rect width="40" height="20"/></svg>')
    else:
        Image.new("RGB", (80, 40), "red").save(ruta)
    h, vv = ("voltear_h", "voltear_v") if es_svg else ("voltear", "voltear_v")
    A.MODALES.clear()
    p = A.abrir(v, clave)
    if p is None:
        A.reg(nombre, "abrir", False, f"{A.MODALES[-1:]}")
        return
    try:
        A.elegir(p, "plano", *(cara(caja, normal=(0, 0, 1))() if clave == "calcomania" else pl()))
        p.set_valor("archivo", str(ruta))
        p._t_previa.stop()
        p._calcular_previa()
        A.esperar(150)
        g = p.manipuladores
        asa = lambda cl: next(m for m in g.manips if getattr(m, "clave", None) == cl)  # noqa: E731
        libre = next(m for m in g.manips if isinstance(m, mp.PosicionCalcomania))
        A.reg(nombre, "siete asas en la vista", len(g.manips) == 7, str([type(m).__name__ for m in g.manips]))
        # flechas X e Y
        for cl in ("dx", "dy"):
            m = asa(cl)
            a, b = m.puntos(g)
            medio = (a + b) / 2
            ok = arrastrar(p, g, medio, medio + (m.u if cl == "dx" else m.v) * 5)
            A.reg(nombre, f"flecha {cl} 5 mm", ok and abs(g.valor(cl) - 5) < 0.3, f"{g.valor(cl):g}; «{p.mensaje.text()}»")
        # cuadrado central: lleva a (-4, 3) pasando por cero
        ok = arrastrar(p, g, libre.punto, libre.punto - libre.u * 9 - libre.v * 2)
        A.reg(nombre, "cuadrado central pasa por cero", ok and abs(g.valor("dx") + 4) < 0.3 and abs(g.valor("dy") - 3) < 0.3,
              f"dx={g.valor('dx'):g} dy={g.valor('dy'):g}")
        # giro 40°
        m = asa("angulo")
        o, d = m._origen_arco(g), m.asa(g) - m._origen_arco(g)
        a40 = math.radians(40)
        ok = arrastrar(p, g, m.asa(g), o + d * math.cos(a40) + np.cross(m.eje, d) * math.sin(a40))
        A.reg(nombre, "giro 40°", ok and abs(g.valor("angulo") - 40) < 1.0, f"{g.valor('angulo'):g}°")
        # escala x1.5
        m = asa("ancho")
        antes = g.valor("escala")
        ok = arrastrar(p, g, m.puntos(g)[1], m.origen + (m.puntos(g)[1] - m.origen) * 1.5)
        A.reg(nombre, "escala x1,5 por el codo", ok and abs(g.valor("escala") / antes - 1.5) < 0.05,
              f"{antes:g} → {g.valor('escala'):g}")
        # volteos: clic
        for cl in (h, vv):
            xy = g.pantalla([asa(cl)._geom(g)[0]])[0][0]
            vis = p.visor
            q = QPointF(*xy)
            QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonPress, q, vis.mapToGlobal(q), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
            QApplication.sendEvent(vis, QMouseEvent(QEvent.MouseButtonRelease, q, vis.mapToGlobal(q), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
            A.esperar(60)
            A.reg(nombre, f"clic en {cl}", p.valores.get(cl) is True, str(p.valores.get(cl)))
        p._calcular_previa()
        A.reg(nombre, "la vista previa sigue andando", p._previa_ok, p.mensaje.text())
        # lo tecleado mueve el gizmo
        antes = libre.punto.copy()
        p.set_valor("dx", "10 mm")
        mueve = not np.allclose(next(m for m in g.manips if isinstance(m, mp.PosicionCalcomania)).punto, antes)
        A.reg(nombre, "teclear en el panel mueve el gizmo", mueve, "")
        n0 = A.n_ops(v)
        p.aceptar()
        A.esperar(300)
        A.reg(nombre, "aceptar crea el paso", A.n_ops(v) == n0 + 1, "")
        while A.n_ops(v) > n0:
            A.deshacer(v)
    except Exception as e:  # noqa: BLE001
        A.reg(nombre, "EXCEPCIÓN", False, f"{type(e).__name__}: {e}")
        if v.panel is not None and v.panel.isVisible():
            v.panel.cancelar()
    A.esperar(100)


probar_gizmo_lienzo("lienzo")
probar_gizmo_lienzo("calcomania")
probar_gizmo_lienzo("insertar_svg")


def asas_del_boceto():
    """Asas del editor de boceto (patrones, Escala, Empalme, Chaflán) arrastradas con mouse simulado sobre el lienzo."""
    AB = f"{AR} · boceto"
    v.editar_operacion(s.paso("Rect").id)
    A.esperar(500)
    lz = v.modo_boceto.lienzo
    v.visor.encuadrar()
    A.esperar(300)

    def sim(tipo, xy, botones):
        q = lz.a_px(*xy)
        boton = Qt.LeftButton if tipo != QEvent.MouseMove else Qt.NoButton
        QApplication.sendEvent(lz, QMouseEvent(tipo, q, lz.mapToGlobal(q), boton, botones, Qt.NoModifier))

    def tirar(i, destino):
        a = lz._asas.asas[i].posicion(lz._asas.valores())
        sim(QEvent.MouseButtonPress, a, Qt.LeftButton)
        for k in range(1, 7):
            sim(QEvent.MouseMove, (a[0] + (destino[0] - a[0]) * k / 6, a[1] + (destino[1] - a[1]) * k / 6), Qt.LeftButton)
            A.esperar(15)
        sim(QEvent.MouseButtonRelease, destino, Qt.NoButton)
        A.esperar(60)

    def caja(i):
        return lz.entrada.campos[i].text()

    ids = list(lz.b.curvas)
    # los patrones del boceto (rectangular y circular) tienen su panel y su pieza: scripts/prueba_ui/patrones_boceto.py
    # escala
    lz.seleccion = ids
    lz.set_herramienta("escala")                      # con la geometría elegida pasa solo al punto base (panel ESCALA)
    lz.transformar.clic(lz.a_px(0.0, 0.0))
    A.esperar(100)
    factor = v.modo_boceto.transformar.campos["factor"]
    factor.setText("1")
    q = lz._asas.asas[0].posicion(lz._asas.valores())
    tirar(0, (q[0] * 2, q[1] * 2))
    A.reg(AB, "escala: asa del factor x2", abs(float(factor.text()) - 2.0) < 0.2, f"factor={factor.text()}")
    lz.cancelar()
    # empalme y chaflán en la esquina (20, 0) del rectángulo
    inf = next(c for c in lz.b.curvas.values() if all(abs(lz.b.coords(p)[1]) < 1e-6 for p in (c.p1, c.p2)))
    der = next(c for c in lz.b.curvas.values() if all(abs(lz.b.coords(p)[0] - 20) < 1e-6 for p in (c.p1, c.p2)))
    for h, esperado in (("empalme", 1), ("chaflan", 1), ("chaflan_dos_dist", 2), ("chaflan_dist_angulo", 2)):
        lz.set_herramienta(h)
        lz.agregar_pick(inf.id, (15.0, 0.0))
        lz.agregar_pick(der.id, (20.0, 5.0))
        A.esperar(100)
        A.reg(AB, f"{h}: {esperado} asa(s) en la vista", lz._asas is not None and len(lz._asas.asas) == esperado, "")
        lz.entrada.campos[0].setText("3")
        if esperado == 2:
            lz.entrada.campos[1].setText("3" if h == "chaflan_dos_dist" else "45")
        a = lz._asas.asas[0].posicion(lz._asas.valores())
        tirar(0, (a[0] - 3.0, a[1] + 3.0))
        A.reg(AB, f"{h}: tirar del asa cambia el valor", float(caja(0)) != 3.0 and float(caja(0)) > 0, f"valor={caja(0)}")
        lz._cerrar_entrada()
    # texto: giro del marco
    lz.set_herramienta("texto")
    lz.clics.append((None, (0.0, -40.0)))
    lz.clics.append((None, (40.0, -30.0)))
    lz._procesar_clics()
    A.esperar(100)
    A.reg(AB, "texto: asa de giro del marco", lz._asas is not None and len(lz._asas.asas) == 1, "")
    a = lz._asas.asas[0].posicion(lz._asas.valores())
    tirar(0, (a[0] - 25.0, a[1] + 25.0))
    A.reg(AB, "texto: tirar del asa gira el marco", abs(float(caja(2)) - 59.0) < 3.0, f"∠={caja(2)}")
    lz._cerrar_entrada()
    lz.clics = []
    v.modo_boceto.cancelar()
    A.esperar(300)


try:
    asas_del_boceto()
except Exception as e:  # noqa: BLE001
    A.reg(f"{AR} · boceto", "EXCEPCIÓN", False, f"{type(e).__name__}: {e}")

def asas_de_animacion():
    """Animación › Transformar componentes: la tríada del lienzo se tira con mouse simulado, la escena se mueve en vivo y el
    diálogo (real, sin bloquear la ventana) escribe la acción al aceptar."""
    from omnicad.ui import animacion as an
    from PySide6.QtCore import QTimer
    AN = f"{AR} · animación"
    w = an.VentanaAnimacion(v.doc)
    A.mostrar(w)
    A.esperar(600)
    cid = list(w.lienzo.objetos)[0]
    w.seleccionar([cid])
    visto = {}

    def con_el_dialogo_abierto():
        d = w._dialogo
        visto["abierto"] = d is not None and d.isVisible() and not d.isModal()
        g = d.asas
        tri = next(m for m in g.manips if isinstance(m, mp.Triada))
        (_, poli), = [(sub, pol) for sub, pol in tri._partes(g)[0] if sub == ("eje", 2)]
        medio = poli.mean(axis=0)
        arrastrar(types.SimpleNamespace(visor=w.lienzo, _t_previa=types.SimpleNamespace(stop=lambda: None), _calcular_previa=lambda: None),
                  g, medio, medio + [0, 0, 8])
        visto["dZ"] = d.campos["dZ"].value()
        visto["z"] = float(w.lienzo.transformaciones[cid][2, 3])
        d.accept()
    QTimer.singleShot(200, con_el_dialogo_abierto)
    a = w.comando("transformar")
    A.reg(AN, "el diálogo de Transformar se abre sin bloquear la ventana", visto.get("abierto") is True, str(visto))
    A.reg(AN, "tirar de la flecha Z escribe la distancia", abs(visto.get("dZ", 0) - 8) < 0.6, f"dZ={visto.get('dZ')}")
    A.reg(AN, "la escena se movió en vivo mientras se tiraba", abs(visto.get("z", 0) - visto.get("dZ", 99)) < 0.1, f"z={visto.get('z')}")
    A.reg(AN, "aceptar guarda la acción con esa distancia", a is not None and abs(a["traslacion"][2] - visto.get("dZ", 99)) < 0.1, str(a and a["traslacion"]))
    A.reg(AN, "la cinta y la línea de tiempo quedan habilitadas", w.cinta.isEnabled() and w.linea.isEnabled() and w._dialogo is None, "")
    w.close()
    A.esperar(200)


def asas_de_pestana_arista():
    """Pestaña de arista: flecha de la altura y arco del ángulo sobre una placa de chapa creada por la API."""
    for nombre, args in (("create_sketch", {"name": "Placa", "plane": "XY"}),
                         ("draw_rectangle", {"sketch": "Placa", "x1": 200, "y1": 200, "x2": 260, "y2": 240})):
        assert api.llamar(s, nombre, args)["ok"]
    r = api.llamar(s, "create_base_flange", {"sketch": "Placa"})
    assert r["ok"], r
    cid = r["result"]["bodies_created"][0]["id"]
    probar("pestana", {"aristas": lambda: [A.hit_arista(v, cid, lineal=True, cerca=(230, 240, 1))]},
           {"tipo": "arista", "altura": "15 mm"})


try:
    asas_de_pestana_arista()
except Exception as e:  # noqa: BLE001
    A.reg(f"{AR} · pestaña de arista", "EXCEPCIÓN", False, f"{type(e).__name__}: {e}")

try:
    asas_de_animacion()
except Exception as e:  # noqa: BLE001
    A.reg(f"{AR} · animación", "EXCEPCIÓN", False, f"{type(e).__name__}: {e}")

(A.SALIDA / "auditoria_asas.json").write_text(json.dumps(AUDITORIA, ensure_ascii=False, indent=1), encoding="utf-8")
A.guardar_registro("u3_asas")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)
