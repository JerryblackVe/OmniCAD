# -*- coding: utf-8 -*-
"""
Bocetos ↔ archivos 2D: INSERTAR › Insertar DXF / Insertar SVG (primitivas → entidades del boceto) y
«Guardar como DXF» de un boceto [GUID-BC1A5C26] (entidades del boceto → primitivas DXF).

Al insertar, los extremos que caen en el mismo lugar se convierten en el MISMO punto del boceto (si no,
los contornos no cerrarían en perfiles) y las curvas Bézier del SVG pasan a splines de puntos de control.
"""
import math

import numpy as np

from ..restricciones.boceto import ArcoElipse, Boceto, puntos_primitiva


def _transformacion(escala, desplazamiento, angulo_grados, voltear=(False, False), centro=(0.0, 0.0)):
    """Punto → punto: voltea alrededor de `centro`, escala desde el origen, gira y mueve."""
    c, s = math.cos(math.radians(angulo_grados)), math.sin(math.radians(angulo_grados))
    dx, dy = desplazamiento
    fx, fy = (-1.0 if voltear[0] else 1.0), (-1.0 if voltear[1] else 1.0)
    cx, cy = centro

    def f(p):
        x, y = cx + fx * (float(p[0]) - cx), cy + fy * (float(p[1]) - cy)
        x, y = x * escala, y * escala
        return (c * x - s * y + dx, s * x + c * y + dy)
    return f


def _cerca(a, b, tol=1e-8):
    return math.dist(a, b) <= tol


def caja_primitivas(primitivas):
    """((xmin, ymin), (xmax, ymax)) de las primitivas de `dxf.leer_dxf` / `svg.leer_svg` (las curvas se
    muestrean); None si no hay ninguna con puntos."""
    pts, beziers = [], []
    for prim in primitivas:
        tipo = prim[0]
        if tipo == "linea":
            pts += [prim[1], prim[2]]
        elif tipo in ("polilinea", "curva"):
            pts += list(prim[1])
        elif tipo == "circulo":
            (cx, cy), r = prim[1], prim[2]
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
        elif tipo == "arco":
            (cx, cy), r, a0, a1 = prim[1], prim[2], prim[3], prim[4]
            barrido = (a1 - a0) % (2 * math.pi) or 2 * math.pi
            pts += [(cx + r * math.cos(a0 + barrido * k / 24), cy + r * math.sin(a0 + barrido * k / 24))
                    for k in range(25)]
        elif tipo == "bezier":
            beziers.append(prim[1])
        elif tipo in ("elipse", "arco_elipse"):
            from ..restricciones.objetos import limites_primitiva
            c = limites_primitiva((tipo, None, *prim[1:]))
            pts.extend(((c[0], c[1]), (c[2], c[3])))
        elif tipo == "texto":
            pts.append(tuple(prim[1]))
    if beziers:                            # todas juntas: (k, 4, 2) por la matriz de Bernstein (17, 4)
        t = np.linspace(0.0, 1.0, 17)[:, None]
        base = np.hstack([(1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3])
        muestras = np.einsum("tk,bkd->btd", base, np.asarray(beziers, float)).reshape(-1, 2)
        pts.extend(map(tuple, muestras))
    if not pts:
        return None
    a = np.asarray(pts, float)
    return (float(a[:, 0].min()), float(a[:, 1].min())), (float(a[:, 0].max()), float(a[:, 1].max()))


def boceto_desde_primitivas(primitivas, *, escala=1.0, desplazamiento=(0.0, 0.0), angulo=0.0, tolerancia=1e-6,
                            voltear_h=False, voltear_v=False, ancho=None, destino=None):
    """Boceto con las primitivas de `dxf.leer_dxf` / `svg.leer_svg`, volteadas (alrededor del centro de su
    caja), escaladas, giradas y movidas, en ese orden. `ancho` (mm) fija el ancho final del dibujo y pisa a
    `escala`. Con `destino` (un Boceto) se agregan ahí en vez de crear uno nuevo."""
    caja = caja_primitivas(primitivas)
    if ancho is not None:
        if caja is None or caja[1][0] - caja[0][0] <= 1e-12:
            raise ValueError("No se puede ajustar el ancho: el dibujo no tiene ancho.")
        if not ancho > 0:
            raise ValueError("El ancho tiene que ser positivo.")
        escala = float(ancho) / (caja[1][0] - caja[0][0])
    if not escala > 0:
        raise ValueError("La escala tiene que ser positiva.")
    centro = ((caja[0][0] + caja[1][0]) / 2, (caja[0][1] + caja[1][1]) / 2) if caja else (0.0, 0.0)
    b = destino if destino is not None else Boceto()
    antes = len(b.curvas)
    espejo = bool(voltear_h) != bool(voltear_v)             # un espejo invierte el sentido de los arcos
    f = _transformacion(escala, desplazamiento, angulo, (voltear_h, voltear_v), centro)
    puntos = {}
    por_grupo = {}
    sentidos = {}

    def pid(p):
        x, y = f(p)
        clave = (round(x / tolerancia), round(y / tolerancia))
        if clave not in puntos:
            puntos[clave] = b.agregar_punto(x, y)
        return puntos[clave]

    def linea(a, c):
        ia, ic = pid(a), pid(c)
        if ia != ic:
            b.agregar_linea(ia, ic)

    for numero, prim in enumerate(primitivas):
        anteriores = b._siguiente if getattr(primitivas, "como_objeto", False) else None
        tipo = prim[0]
        if tipo == "linea":
            linea(prim[1], prim[2])
        elif tipo == "polilinea":
            pts = list(prim[1])
            for a, c in zip(pts, pts[1:], strict=False):
                linea(a, c)
            if prim[2] and len(pts) > 2:
                linea(pts[-1], pts[0])
        elif tipo == "curva":                                   # spline de ajuste por los puntos (imagen vectorizada)
            ids = [pid(q) for q in prim[1]]
            if len(set(ids)) >= (3 if prim[2] else 2):
                b.agregar_spline(ids, modo="ajuste", grado=3, cerrada=bool(prim[2]))
        elif tipo == "circulo":
            (cx, cy), r = prim[1], prim[2]
            if r * escala > tolerancia:
                b.agregar_circulo(pid((cx, cy)), r * escala)
        elif tipo == "arco":
            (cx, cy), r, a0, a1 = prim[1], prim[2], prim[3], prim[4]
            ini = (cx + r * math.cos(a0), cy + r * math.sin(a0))
            fin = (cx + r * math.cos(a1), cy + r * math.sin(a1))
            if espejo:
                ini, fin = fin, ini
            if r * escala > tolerancia and pid(ini) != pid(fin):
                b.agregar_arco_centro(pid((cx, cy)), pid(ini), pid(fin))
        elif tipo == "bezier":
            p = prim[1]
            if _cerca(p[0], p[1]) and _cerca(p[2], p[3]):
                linea(p[0], p[3])                              # Bézier degenerada = recta
            else:
                ids = [pid(p[0])] + [b.agregar_punto(*f(q)) for q in p[1:3]] + [pid(p[3])]
                b.agregar_spline(ids, modo="control", grado=3)
        elif tipo in ("elipse", "arco_elipse"):
            (cx, cy), a, menor, giro = prim[1:5]
            c, s = math.cos(giro), math.sin(giro)
            centro, mayor = pid((cx, cy)), pid((cx + a * c, cy + a * s))
            if tipo == "elipse":
                b.agregar_elipse(centro, mayor, menor * escala, ejes=False)
            else:
                ini, fin = [pid((cx + a * math.cos(t) * c - menor * math.sin(t) * s,
                                 cy + a * math.cos(t) * s + menor * math.sin(t) * c)) for t in prim[5:7]]
                if espejo:
                    ini, fin = fin, ini
                b._agregar_curva(ArcoElipse(b._nuevo_id(), centro, mayor, menor * escala, ini, fin))
        elif tipo == "texto":
            (x, y), altura, texto = prim[1], prim[2], prim[3]
            if str(texto).strip():
                b.agregar_texto(f((x, y)), texto, altura=altura * escala, angulo=angulo)
        if anteriores is not None:
            capa = tuple(primitivas.grupos[numero]) if primitivas.grupos else ()
            nuevos = [i for i in range(anteriores, b._siguiente) if i in b.curvas]
            if getattr(primitivas, "formas", None):
                forma = primitivas.formas[numero]
                por_grupo.setdefault((capa, forma["numero"]), []).extend(nuevos)
                sentidos.update({str(i): forma.get("sentido", 1) * (-1 if espejo and tipo in ("arco", "arco_elipse") else 1)
                                 for i in nuevos})
            else:
                # Un TEXT ya nace como objeto editable; el DXF lo agrupa sin apropiarse dos veces de su curva.
                elementos = [next((oid for oid, o in b.objetos.items() if o.get("texto_automatico") == i), i)
                             if b.curvas[i].tipo == "texto" else i for i in nuevos]
                por_grupo.setdefault(capa, []).extend(elementos)
    if len(b.curvas) == antes:
        raise ValueError("El archivo no tiene geometría para el boceto.")
    if por_grupo:
        from ..restricciones import objetos
        if getattr(primitivas, "formas", None):
            formas = {f["numero"]: f for f in primitivas.formas}
            grupos = {}
            for (capa, numero), ids in por_grupo.items():
                if ids:
                    forma = formas[numero]
                    oid = objetos.crear(b, ids, forma["nombre"])
                    b.objetos[oid]["regla_relleno"] = forma["regla"]
                    b.objetos[oid]["relleno_svg"] = forma["relleno"]
                    b.objetos[oid]["sentidos_svg"] = {str(i): sentidos[str(i)] for i in ids}
                    grupos.setdefault(capa, []).append(oid)
            por_grupo = grupos
        # Primero las hojas, después sus padres: los ids de las curvas no se reemplazan.
        for capa in sorted(list(por_grupo), key=len, reverse=True):
            for n in range(len(capa) - 1, -1, -1):
                por_grupo.setdefault(capa[:n], [])
        for capa in sorted(por_grupo, key=len, reverse=True):
            ids = por_grupo[capa]
            if ids:
                oid = objetos.crear(b, ids, capa[-1] if capa else primitivas.nombre)
                b.objetos[oid]["tipo_origen"] = getattr(primitivas, "tipo_origen", "Vector")
                if capa:
                    por_grupo[capa[:-1]].append(oid)
    return b


def agregar_geometria(b, prims, tolerancia=1e-6):
    """Agrega al boceto `b` primitivas con el formato de `Boceto.geometria()` (las que salen de OpenCascade:
    'linea', 'circulo', 'arco', 'elipse', 'arco_elipse', 'spline'). Los extremos que coinciden pasan a ser el
    mismo punto. Devuelve los ids de las curvas nuevas."""
    from ..restricciones.boceto import puntos_primitiva
    puntos, nuevas = {}, []

    def pid(q):
        clave = (round(q[0] / tolerancia), round(q[1] / tolerancia))
        if clave not in puntos:
            puntos[clave] = b.agregar_punto(float(q[0]), float(q[1]))
        return puntos[clave]

    for prim in prims:
        tipo = prim[0]
        if tipo == "linea":
            a, c = pid(prim[2]), pid(prim[3])
            if a != c:
                nuevas.append(b.agregar_linea(a, c))
        elif tipo == "circulo":
            nuevas.append(b.agregar_circulo(pid(prim[2]), prim[3]))
        elif tipo == "arco":
            (cx, cy), r, a0, a1 = prim[2], prim[3], prim[4], prim[5]
            ini, fin = pid((cx + r * math.cos(a0), cy + r * math.sin(a0))), pid((cx + r * math.cos(a1), cy + r * math.sin(a1)))
            if ini != fin:
                nuevas.append(b.agregar_arco_centro(pid((cx, cy)), ini, fin))
        elif tipo == "elipse":
            (cx, cy), a, r_menor, ang = prim[2], prim[3], prim[4], prim[5]
            nuevas.append(b.agregar_elipse(pid((cx, cy)), (cx + a * math.cos(ang), cy + a * math.sin(ang)), r_menor,
                                           ejes=False))
        elif tipo == "spline":
            polos, nudos, grado, pesos = prim[2], prim[3], prim[4], prim[5]
            ids = [pid(polos[0])] + [b.agregar_punto(*map(float, q)) for q in polos[1:-1]]
            ultimo = pid(polos[-1])
            ids.append(ultimo if ultimo != ids[0] else b.agregar_punto(*map(float, polos[-1])))
            nuevas.append(b.agregar_spline(ids, modo="control", grado=grado, pesos=list(pesos) if pesos else None,
                                           nudos=list(nudos)))
        elif tipo == "arco_elipse":
            c, a, bb, ang, _t0, _t1 = prim[2:8]
            q = puntos_primitiva(prim, 4)
            centro = pid(c)
            mayor = pid((c[0] + a * math.cos(ang), c[1] + a * math.sin(ang)))
            nuevas.append(b._agregar_curva(ArcoElipse(b._nuevo_id(), centro, mayor, bb, pid(q[0]), pid(q[-1]))))
    return nuevas


def primitivas_dxf_de_boceto(boceto, incluir_construccion=False):
    """Entidades del boceto como primitivas del escritor DXF (líneas, círculos, arcos; lo demás, polilínea).
    La construcción va a la capa «CONSTRUCCION» si se incluye."""
    salida = []
    for prim in boceto.geometria(incluir_construccion=incluir_construccion):
        c = boceto.curvas.get(prim[1])
        capa = "CONSTRUCCION" if c is not None and getattr(c, "construccion", False) else "0"
        if prim[0] == "linea":
            dxf = ("linea", prim[2], prim[3])
        elif prim[0] == "circulo":
            dxf = ("circulo", prim[2], prim[3])
        elif prim[0] == "arco":
            dxf = ("arco", prim[2], prim[3], prim[4], prim[5])
        else:
            pts = puntos_primitiva(prim)
            cerrada = len(pts) > 2 and np.allclose(pts[0], pts[-1])
            dxf = ("polilinea", [tuple(p) for p in (pts[:-1] if cerrada else pts)], cerrada)
        salida.append((capa, dxf))
    return salida
