# -*- coding: utf-8 -*-
"""Escribir en los campos como una persona: clic, borrar, teclear (coma decimal, unidades, expresiones, vacío y basura),
pegar, Enter y Esc. Mira qué valor entiende el panel, si el campo se pone rojo y qué dice."""
import sys

import arnes as A
import escena
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from teclado import pegar, teclear

s, ids = escena.construir()
app, v = A.iniciar(s.doc)
AR = "TECLEAR"
caja, tubo = ids["caja"], ids["tubo"]

# (entrada, esperado en mm / grados / factor; None = tiene que rechazarse)
LONG = [("15", 15), ("15 mm", 15), ("15.5 mm", 15.5), ("15,5 mm", 15.5), ("15,5", 15.5), ("  15 mm  ", 15), ("15mm", 15),
        ("1e3 mm", 1000), ("2*3 mm", 6), ("0.5 cm", 5), ("10 in", 254), ("1/2 mm", 0.5), ("1 m", 1000), ("-5 mm", -5),
        ("abc", None), ("", None), ("-", None), ("15 mm mm", None), ("15 xx", None), ("(", None), ("1/0", None), ("15 deg", None)]
ANG = [("45", 45), ("45 deg", 45), ("45°", 45), ("1,5 deg", 1.5), ("1.5 deg", 1.5), ("-30 deg", -30), ("1e1 deg", 10),
       ("abc", None), ("", None), ("45 mm", None), ("45 deg deg", None)]
ESC = [("2", 2), ("2,5", 2.5), ("2.5", 2.5), ("1/2", 0.5), ("abc", None), ("", None), ("2 mm", None)]
TABLAS = {"LONGITUD": LONG, "ANGULO": ANG, "ESCALAR": ESC}

per = lambda n, i=0: (lambda: [A.hit_perfil(v, s, n, i)])  # noqa: E731
cur = lambda n, i=0: (lambda: [A.hit_curva(v, s, n, i)])  # noqa: E731
cara = lambda cid, **k: (lambda: [A.hit_cara(v, cid, **k)])  # noqa: E731
arista = lambda cid, **k: (lambda: [A.hit_arista(v, cid, **k)])  # noqa: E731
cuerpo = lambda cid: (lambda: [A.hit_cuerpo(v, cid)])  # noqa: E731
eje = lambda i: (lambda: [A.hit_eje(v, i)])  # noqa: E731
pl = lambda: [A.hit_plano(v, "XY")]  # noqa: E731

COMANDOS = [
    ("extruir", {"perfiles": per("Rect")}, ["distancia", "conicidad"]),
    ("revolucion", {"perfiles": per("Rect"), "eje": eje("X")}, ["angulo"]),
    ("sup_extruir", {"curvas": cur("Circ")}, ["distancia", "conicidad"]),
    ("agujero", {"colocacion": cara(caja, normal=(0, 0, 1))}, ["diametro", "profundidad"]),
    ("caja", {"centro": pl}, ["ancho", "largo", "alto"]),
    ("empalme_3d", {"aristas": arista(caja)}, ["radio"]),
    ("chaflan_3d", {"aristas": arista(caja)}, ["distancia"]),
    ("vaciado", {"caras": cara(caja, normal=(0, 0, 1))}, ["espesor_interior"]),
    ("escala_3d", {"cuerpos": cuerpo(caja)}, ["factor"]),
    ("sup_desfase", {"caras": cara(tubo)}, ["distancia"]),
    ("mover_copiar", {"cuerpos": cuerpo(caja)}, ["dx", "rx"]),
]

resumen = {}                   # entrada → casos que no se comportaron como se esperaba
for clave, sel, campos in COMANDOS:
    A.MODALES.clear()
    p = A.abrir(v, clave)
    if p is None:
        A.reg(AR, f"{clave}: abrir", False, f"{A.MODALES[-1:]}")
        continue
    try:
        for campo, fn in sel.items():
            A.elegir(p, campo, *fn())
        if clave == "mover_copiar":
            p.set_valor("tipo", "libre")
        for cm in campos:
            c = next(c for c in p.campos if c.clave == cm)
            if not p._visible(c):
                A.reg(AR, f"{clave}.{cm}", False, "el campo no está visible")
                continue
            tipo = {"angulo": "ANGULO", "escalar": "ESCALAR"}.get(str(getattr(c, "tipo", "")).lower(), "LONGITUD")
            for entrada, esperado in TABLAS[tipo]:
                w = teclear(p, cm, entrada)
                valor, msg = None, ""
                try:
                    valor = float(p.ctx.evaluar(w.text().strip(), c.tipo))
                except Exception as e:  # noqa: BLE001
                    msg = str(e)
                rojo = bool(w.styleSheet())
                guardado = p.valores.get(cm)
                ok_texto = guardado == entrada.strip()
                if esperado is None:
                    bien = valor is None and rojo and ok_texto
                else:
                    bien = valor is not None and abs(valor - esperado) < 1e-6 * max(1, abs(esperado)) and not rojo and ok_texto
                A.reg(f"{AR} · {clave}.{cm}", f"teclear «{entrada}»", bien,
                      f"entendió={valor}; esperado={esperado}; rojo={rojo}; mensaje={msg!r}; guardado={guardado!r}")
                if not bien:
                    resumen.setdefault(entrada, []).append((f"{clave}.{cm}", valor, rojo, msg))
            pegado = "12 mm" if tipo == "LONGITUD" else "12 deg" if tipo == "ANGULO" else "3"
            pegar(p, cm, pegado)
            A.reg(f"{AR} · {clave}.{cm}", "pegar con Ctrl+V", p.valores.get(cm) == pegado, f"guardado={p.valores.get(cm)!r}")
        # Enter dentro de un campo acepta; Esc cancela
        cm = campos[0]
        teclear(p, cm, "5 mm" if clave != "escala_3d" else "2")
        n0 = A.n_ops(v)
        p._t_previa.stop()
        p._calcular_previa()
        previa = bool(p._previa_ok and p.ultima_op is not None)
        QTest.keyClick(p.widgets[cm], Qt.Key_Return)
        A.esperar(250)
        creo = A.n_ops(v) > n0
        A.reg(f"{AR} · {clave}", "Enter dentro del campo acepta (si la vista previa es válida)", creo == previa,
              f"previa_ok={previa}; paso creado={creo}")
        while A.n_ops(v) > n0:
            A.deshacer(v)
        if not creo:
            QTest.keyClick(p.widgets[cm], Qt.Key_Escape)
            A.esperar(150)
            try:
                vivo = p.isVisible()
            except RuntimeError:
                vivo = False
            A.reg(f"{AR} · {clave}", "Esc dentro del campo cancela", not vivo, f"visible={vivo}")
    except Exception as e:  # noqa: BLE001
        A.reg(f"{AR} · {clave}", "EXCEPCIÓN", False, f"{type(e).__name__}: {e}")
    finally:
        try:
            if v.panel is not None and v.panel.isVisible():
                v.panel.cancelar()
        except RuntimeError:
            pass
    A.esperar(100)

print("\n=== ENTRADAS QUE NO SE COMPORTARON COMO SE ESPERABA ===")
for entrada, casos in resumen.items():
    print(f"«{entrada}»: {len(casos)} campos; p. ej. {casos[0]}")
A.guardar_registro("teclear")
fallas = [r for r in A.REGISTRO if not r["ok"]]
print(f"\n=== {len(A.REGISTRO)} comprobaciones, {len(fallas)} con ✗ ===")
v.close()
sys.exit(0)
