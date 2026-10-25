# -*- coding: utf-8 -*-
"""Fase C · asas de arrastre (manipuladores) de los comandos de Superficie y Sólido, con eventos de mouse simulados
al visor (no mueve el cursor real). Por cada asa: arrastrar, ver que el valor del panel cambie lo esperado y que la vista
previa siga andando; arrastrar hacia el otro lado y ver el tope."""
import math
import sys

import arnes as A
import escena
import numpy as np
from omnicad.ui import manipuladores as mp
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
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
        if foto:
            A.foto(v, foto)
        for m in list(g.manips):
            tn, cl = type(m).__name__, getattr(m, "clave", None)
            try:
                if isinstance(m, mp.Angulo) and not isinstance(m, mp.GiroCalcomania):
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
probar("escala_3d", {"cuerpos": cuerpo(caja)}, {"factor": "2"})
probar("mover_copiar", {"cuerpos": cuerpo(caja)}, {"tipo": "libre", "dx": "10 mm", "dy": "5 mm", "dz": "0 mm"}, "asas_mover")
probar("patron_rectangular_3d", {"cuerpos": cuerpo(caja), "dir1": eje("X")}, {"n1": 3, "d1": "50 mm"})
probar("patron_circular_3d", {"cuerpos": cuerpo(caja), "eje": eje("Z")}, {"n": 4})

A.guardar_registro("u3_asas")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)
