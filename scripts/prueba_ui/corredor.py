# -*- coding: utf-8 -*-
"""Corredor común: prueba un comando de punta a punta en la ventana real (elegir con el visor, valores, vista previa,
aceptar, reabrir para editar, deshacer) y los casos negativos (sin selección, expresión mala, Esc)."""
import arnes as A
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

def _vivo(p):
    try:
        return p.isVisible()
    except RuntimeError:                       # el panel ya se destruyó al cerrarse
        return False


TOL = 0.01          # 1 % para las medidas esperadas


def _medida(c):
    return c[1]


def _nuevos(antes, despues):
    return {k: v for k, v in despues.items() if k not in antes or antes[k] != v}


def caso(v, area, clave, sel, vals=None, esperado=None, deshacer=True, foto=None, rt=True, etiqueta=None, error=None):
    """sel: {campo: lambda -> [hits]}; vals: {campo: valor}; esperado: medida total de lo nuevo (área o volumen).
    `error`: texto que tiene que traer el aviso cuando el caso es uno que el programa debe rechazar."""
    vals = vals or {}
    nombre = etiqueta or clave
    antes, n0 = A.cuerpos_resumen(v), A.n_ops(v)
    A.MODALES.clear()
    p = A.abrir(v, clave)
    if p is None:
        A.reg(area, f"{nombre}: abrir", False, f"no abre: {A.MODALES[-1:]}")
        return None
    try:
        for campo, fn in sel.items():
            hs = fn()
            if not hs or any(h is None for h in hs):
                A.reg(area, f"{nombre}: elegir «{campo}» con el visor", False, "el visor no devolvió la entidad")
                p.cancelar()
                return None
            A.elegir(p, campo, *hs)
        for k, val in vals.items():
            p.set_valor(k, val)
        p._t_previa.stop()
        p._calcular_previa()
        A.esperar(120)
        st = A.estado_panel(p)
        if foto:
            A.foto(v, foto)
        if error is not None:
            rechazado = not st["previa_ok"]
            A.reg(area, f"{nombre}: se rechaza con un aviso claro", rechazado and error.lower() in (st["mensaje"] or "").lower(),
                  f"mensaje=«{st['mensaje']}» (esperaba «{error}»)" if rechazado else "la vista previa lo aceptó")
            p.cancelar()
            A.esperar(100)
            return {"previa_ok": False, "mensaje": st["mensaje"]}
        if not st["op"] or not st["previa_ok"]:
            A.reg(area, f"{nombre}: vista previa", False, f"mensaje=«{st['mensaje']}» op={st['op']} previa_ok={st['previa_ok']} params={getattr(p.ultima_op, 'p', None)}")
            p.cancelar()
            A.esperar(100)
            return {"previa_ok": False, "mensaje": st["mensaje"]}
        A.reg(area, f"{nombre}: vista previa", True, st["mensaje"] and f"aviso: {st['mensaje']}")
        p.aceptar()
        A.esperar(450)
        if A.n_ops(v) != n0 + 1:
            A.reg(area, f"{nombre}: aceptar agrega UN paso", False, f"pasos {n0} → {A.n_ops(v)}")
            return None
        despues = A.cuerpos_resumen(v)
        nv = _nuevos(antes, despues)
        total = round(sum(_medida(x) for k, x in nv.items() if k not in antes)
                      + sum(_medida(x) - _medida(antes[k]) for k, x in nv.items() if k in antes), 3)
        det = f"nuevos={ {k: x for k, x in nv.items() if k not in antes} } cambiados={ {k: x for k, x in nv.items() if k in antes} }"
        if esperado is not None:
            ok = abs(total - esperado) <= max(abs(esperado) * TOL, 0.05)
            A.reg(area, f"{nombre}: resultado = {esperado}", ok, f"obtenido {total}; {det}")
        else:
            A.reg(area, f"{nombre}: aceptar", True, det)
        resultado = {"total": total, "despues": despues, "det": det}
        if rt:
            op = v.doc.operaciones[-1]
            A.MODALES.clear()
            v.editar_operacion(op.id)
            A.esperar(250)
            p2 = v.panel
            if p2 is None or not p2.isVisible():
                A.reg(area, f"{nombre}: reabrir para editar", False, f"no abre el panel; modales={A.MODALES}")
            else:
                malos = []
                for k, val in vals.items():
                    got = p2.valores.get(k)
                    if str(got) != str(val):
                        malos.append(f"{k}: puse {val!r}, vuelve {got!r}")
                for campo in sel:
                    n = len(p2.valores.get(campo) or [])
                    if n != len(sel[campo]()) and n == 0:
                        malos.append(f"{campo}: la selección vuelve vacía")
                A.reg(area, f"{nombre}: al reabrir vuelven los valores", not malos, "; ".join(malos))
                p2._t_previa.stop()
                p2._calcular_previa()
                st2 = A.estado_panel(p2)
                A.reg(area, f"{nombre}: la vista previa al editar", st2["op"] and st2["previa_ok"], st2["mensaje"])
                p2.aceptar()
                A.esperar(450)
                igual = A.cuerpos_resumen(v) == despues and A.n_ops(v) == n0 + 1
                A.reg(area, f"{nombre}: aceptar sin cambiar no altera nada", igual,
                      "" if igual else f"antes {despues} ahora {A.cuerpos_resumen(v)} pasos {A.n_ops(v)}")
        if deshacer:
            k = 0
            while A.n_ops(v) > n0 and k < 4:
                A.deshacer(v)
                k += 1
            ok = A.n_ops(v) == n0 and A.cuerpos_resumen(v) == antes
            A.reg(area, f"{nombre}: deshacer vuelve al estado anterior ({k} paso/s)", ok,
                  "" if ok else f"pasos {A.n_ops(v)} (eran {n0}); {A.cuerpos_resumen(v)}")
        return resultado
    except Exception as e:  # noqa: BLE001
        A.reg(area, f"{nombre}: EXCEPCIÓN", False, f"{type(e).__name__}: {e}")
        if v.panel is not None and v.panel.isVisible():
            v.panel.cancelar()
        return None


def negativos(v, area, clave, sel_ok=None, expr=None, malos=("abc", "0", "-5"), vals=None, medir=True):
    """Sin selección, Enter, Esc y expresiones malas. `sel_ok`: {campo: lambda} válida para probar la expresión mala."""
    n0 = A.n_ops(v)
    A.MODALES.clear()
    p = A.abrir(v, clave)
    if p is None:
        A.reg(area, f"{clave}: negativos", False, f"no abre: {A.MODALES[-1:]}")
        return
    p._t_previa.stop()
    p._calcular_previa()
    msg = p.mensaje.text()
    p.aceptar()
    A.esperar(120)
    if A.n_ops(v) > n0:                          # los valores por defecto alcanzan: el comando crea sin elegir nada
        A.reg(area, f"{clave}: Aceptar sin elegir nada crea el paso con los valores por defecto", True, f"pasos {n0} → {A.n_ops(v)}")
        k = 0
        while A.n_ops(v) > n0 and k < 3:
            A.deshacer(v)
            k += 1
        return
    A.reg(area, f"{clave}: Aceptar sin elegir nada avisa y no crea el paso", bool(msg or p.mensaje.text()),
          f"mensaje=«{msg or p.mensaje.text()}» pasos={A.n_ops(v)}")
    QTest.keyClick(p, Qt.Key_Return)
    A.esperar(120)
    A.reg(area, f"{clave}: Enter sin elegir nada no crea paso ni cierra mal", A.n_ops(v) == n0, f"pasos={A.n_ops(v)} visible={_vivo(p)}")
    QTest.keyClick(p, Qt.Key_Escape)
    A.esperar(120)
    A.reg(area, f"{clave}: Esc cierra el panel", not _vivo(p), f"visible={_vivo(p)}")
    if sel_ok and expr:
        for malo in malos:
            p = A.abrir(v, clave)
            try:
                for campo, fn in sel_ok.items():
                    A.elegir(p, campo, *fn())
                for k, val in (vals or {}).items():
                    p.set_valor(k, val)
                p.set_valor(expr, malo)
                p._t_previa.stop()
                p._calcular_previa()
                st = A.estado_panel(p)
                creado = False
                if st["op"] and st["previa_ok"]:
                    p.aceptar()
                    A.esperar(300)
                    creado = A.n_ops(v) > n0
                    k = 0
                    while A.n_ops(v) > n0 and k < 3:
                        A.deshacer(v)
                        k += 1
                    detalle = f"{expr}={malo!r}: se aceptó y creó paso ({'sí' if creado else 'no'}); mensaje=«{st['mensaje']}»"
                else:
                    detalle = f"{expr}={malo!r}: rechazado con «{st['mensaje']}»"
                    p.cancelar()
                if malo == "abc":
                    A.reg(area, f"{clave}: {expr}=abc se rechaza con mensaje", not (st["op"] and st["previa_ok"]) and bool(st["mensaje"]), detalle)
                else:
                    A.reg(area, f"{clave}: {expr}={malo} (borde) → {'aceptado' if creado else 'rechazado'}", True, detalle)
            except Exception as e:  # noqa: BLE001
                A.reg(area, f"{clave}: {expr}={malo}", False, f"EXCEPCIÓN {type(e).__name__}: {e}")
                if v.panel is not None and v.panel.isVisible():
                    v.panel.cancelar()
