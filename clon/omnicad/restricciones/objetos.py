# -*- coding: utf-8 -*-
"""Objetos rígidos del boceto: identidad y jerarquía sobre las curvas originales.

Las curvas siguen siendo la única geometría y conservan sus ids de perfil. Las matrices se
aplican al consultar primitivas, nunca a los puntos del solver. No hay Qt ni geometría visual aquí.
"""
import copy
import math
import weakref
from functools import lru_cache

import numpy as np

_INDICES = weakref.WeakKeyDictionary()
_MATRICES = weakref.WeakKeyDictionary()
_AISLADO = weakref.WeakKeyDictionary()
IDENTIDAD = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def _error(texto):
    from .boceto import ErrorBoceto
    return ErrorBoceto(texto)


def invalidar(b):
    _INDICES.pop(b, None)
    _MATRICES.pop(b, None)
    _AISLADO.pop(b, None)


def matriz(valor):
    """Matriz afín invertible 3×3, finita; rechaza proyecciones y escalas degeneradas."""
    try:
        m = np.asarray(valor, float)
        valido = (m.shape == (3, 3) and np.isfinite(m).all() and abs(m).max() <= 1e12
                  and np.allclose(m[2], (0, 0, 1), atol=1e-12, rtol=0)
                  and abs(np.linalg.det(m[:2, :2])) > 0)
    except (TypeError, ValueError, OverflowError):
        valido = False
    if not valido:
        raise _error("La transformación debe ser afín, finita y tener escala distinta de cero.")
    return m


def afin(dx=0.0, dy=0.0, angulo=0.0, sx=1.0, sy=1.0, pivote=(0.0, 0.0)):
    """Escala en X/Y, gira y traslada alrededor de un pivote, en mm y grados."""
    valores = (dx, dy, angulo, sx, sy, *pivote)
    if not all(math.isfinite(float(v)) for v in valores) or min(abs(sx), abs(sy)) < 1e-6:
        raise _error("Usá valores finitos y escalas de al menos 0,000001.")
    a = math.radians(angulo)
    c, s = math.cos(a), math.sin(a)
    m = np.array([[c * sx, -s * sy, dx], [s * sx, c * sy, dy], [0, 0, 1.0]])
    p = np.asarray(pivote, float)
    m[:2, 2] += p - m[:2, :2] @ p
    return matriz(m)


def indice(b):
    """{curva: (objeto raíz, objeto hoja, matriz acumulada)}; una visita por jerarquía."""
    if b in _INDICES:
        return _INDICES[b]
    resultado, padres, visitados, claves = {}, {}, set(), {}
    for oid, o in b.objetos.items():
        for i in o["entidades"]:
            if i in padres:
                raise _error("Un elemento no puede pertenecer a dos objetos.")
            if i not in b.curvas and i not in b.objetos:
                raise _error(f"El objeto {oid} contiene un elemento inexistente: {i}.")
            padres[i] = oid

    def visitar(oid, raiz, m, camino):
        if oid in camino or len(camino) >= 40:
            raise _error("La jerarquía de objetos tiene un ciclo o supera 40 niveles.")
        o = b.objetos[oid]
        visitados.add(oid)
        m = m @ np.asarray(o["matriz"], float)  # validada al crear, transformar o cargar el objeto
        clave = tuple(map(tuple, m))
        for i in o["entidades"]:
            if i in b.objetos:
                visitar(i, raiz, m, camino | {oid})
            else:
                resultado[i] = (raiz, oid, m)
                claves[i] = clave

    for oid in b.objetos:
        if oid not in padres:
            visitar(oid, oid, np.eye(3), set())
    if visitados != set(b.objetos):
        raise _error("La jerarquía de objetos contiene un ciclo sin raíz.")
    _INDICES[b] = resultado
    _MATRICES[b] = claves
    return resultado


def clave_matriz(b, cid):
    indice(b)
    return _MATRICES[b][cid]


def aplicar_a_primitivas(b, cid, prims):
    if cid not in indice(b):
        return prims
    m, salida = clave_matriz(b, cid), []
    for p in prims:
        try:
            hash(p)
        except TypeError:
            p = inmutable(p)
        salida.append(primitiva_cacheada(p, m))
    return salida


def curvas(b, ids):
    """Curvas de objetos o curvas sueltas, sin repetir; conserva el orden de origen."""
    salida, vistos = [], set()

    def visitar(i):
        if i in b.objetos:
            for hijo in b.objetos[i]["entidades"]:
                visitar(hijo)
        elif i in b.curvas:
            if i not in vistos:
                vistos.add(i)
                salida.append(i)
        else:
            raise _error(f"No existe el objeto o la curva {i}.")
    for i in ids:
        visitar(i)
    return salida


def raices(b):
    hijos = {i for o in b.objetos.values() for i in o["entidades"]}
    return [i for i in b.objetos if i not in hijos]


def curvas_visibles(b):
    """Curvas que se dibujan; mientras haya un aislamiento, la geometría suelta tampoco se ve."""
    salida = set() if aislamiento_activo(b) else {i for i in b.curvas if i not in indice(b)}
    def visitar(i):
        if i in b.objetos:
            if b.objetos[i]["visible"]:
                for h in b.objetos[i]["entidades"]:
                    visitar(h)
        else:
            salida.add(i)
    for i in raices(b):
        visitar(i)
    return salida


# ------------------------------------------------------------ organización del boceto
# Tres propiedades independientes por objeto: "visible" (se dibuja), "bloqueado" (no se transforma) y "perfiles"
# (sus curvas forman perfiles CAD; falta = True, así los proyectos viejos no cambian). Ocultar no excluye de los
# perfiles ni bloquear cambia la participación. Las categorías no se guardan: salen de los datos de cada objeto.
CATEGORIAS = {"geometrias": "Geometrías", "textos": "Textos", "vectores": "SVG / DXF", "grupos": "Grupos personalizados"}
NOMBRES_CURVA = {"linea": "Línea", "circulo": "Círculo", "arco": "Arco", "elipse": "Elipse",
                 "arco_elipse": "Arco elíptico", "spline": "Spline", "conica": "Cónica", "texto": "Texto"}


def categoria(b, oid):
    """geometrias, textos, vectores o grupos: de dónde salió el objeto, no dónde está."""
    o = b.objetos[oid]
    if o.get("tipo_origen"):
        return "vectores"
    if (o.get("texto_automatico") is not None or o.get("clase") == "texto"
            or any(i in b.curvas and b.curvas[i].tipo == "texto" for i in o["entidades"])):
        return "textos"
    if any(i in b.objetos for i in o["entidades"]):
        return "grupos"
    return "geometrias"


def padres(b):
    return {i: k for k, o in b.objetos.items() for i in o["entidades"]}


def unidades(b):
    """{categoría: [ids]} de lo que el usuario maneja como una pieza: los objetos raíz y los que están dentro de un
    grupo personalizado (conservan su categoría). Lo interno de un SVG o de un texto no se lista."""
    arriba = padres(b)
    salida = {c: [] for c in CATEGORIAS}
    for oid in b.objetos:
        padre = arriba.get(oid)
        if padre is None or categoria(b, padre) == "grupos":
            salida[categoria(b, oid)].append(oid)
    return salida


def nombre_curva(b, cid):
    c = b.curvas[cid]
    return f"{NOMBRES_CURVA.get(c.tipo, 'Curva')} {cid}"


def geometria_suelta(b):
    """Curvas que no pertenecen a ningún objeto: siguen bajo el solver y se listan como geometría."""
    internas = indice(b)
    return [i for i in b.curvas if i not in internas]


def curvas_sin_perfil(b):
    """Curvas de objetos (o de sus padres) con "perfiles" apagado: no forman perfiles CAD aunque se vean."""
    salida = set()

    def visitar(i, fuera):
        if i in b.objetos:
            fuera = fuera or b.objetos[i].get("perfiles", True) is False
            for h in b.objetos[i]["entidades"]:
                visitar(h, fuera)
        elif fuera:
            salida.add(i)
    if any(o.get("perfiles", True) is False for o in b.objetos.values()):
        for i in raices(b):
            visitar(i, False)
    return salida


def aislamiento_activo(b):
    """Se consulta por curva al dibujar: queda en caché hasta el próximo `invalidar`."""
    if b not in _AISLADO:
        # También si lo aislado se borró: lo que ocultó sigue esperando «Restaurar aislamiento».
        _AISLADO[b] = any(o.get("aislado") or o.get("oculto_por_aislar") for o in b.objetos.values())
    return _AISLADO[b]


def aislar(b, ids):
    """Deja a la vista solo `ids` (y lo que los contiene): oculta el resto y la geometría suelta. Se guarda en los
    objetos, así que `restaurar_aislamiento` vuelve exactamente a la visibilidad anterior, también tras reabrir."""
    ids = list(dict.fromkeys(ids))
    if not ids or any(i not in b.objetos for i in ids):
        raise _error("Elegí objetos existentes para aislar.")
    restaurar_aislamiento(b)
    arriba = padres(b)
    camino = set()
    for i in ids:
        while i is not None:
            camino.add(i)
            i = arriba.get(i)
    for oid, o in b.objetos.items():
        if oid in camino or arriba.get(oid) not in camino | {None}:
            continue
        if o["visible"]:
            o["visible"], o["oculto_por_aislar"] = False, True
    for i in ids:
        b.objetos[i]["aislado"] = True
    invalidar(b)


def restaurar_aislamiento(b):
    """Termina el aislamiento: muestra lo que ocultó y nada más (lo que ya estaba oculto sigue oculto)."""
    for o in b.objetos.values():
        if o.pop("oculto_por_aislar", False):
            o["visible"] = True
        o.pop("aislado", None)
    invalidar(b)


def mover_a_grupo(b, ids, grupo=None):
    """Cambia la pertenencia sin mover nada en pantalla: la matriz local se recalcula contra el grupo nuevo.
    grupo None saca los objetos a la raíz. Un objeto interno de un SVG o de un texto no se saca de su recurso."""
    ids = list(dict.fromkeys(ids))
    if not ids or any(i not in b.objetos for i in ids):
        raise _error("Elegí objetos existentes para cambiar de grupo.")
    if grupo is not None and (grupo not in b.objetos or categoria(b, grupo) != "grupos"):
        raise _error("El destino tiene que ser un grupo personalizado.")
    arriba = padres(b)
    for i in ids:
        padre = arriba.get(i)
        if padre is not None and categoria(b, padre) != "grupos":
            raise _error("Ese objeto es parte de un SVG, un DXF o un texto: no se saca de su recurso.")
        if b.objetos[i]["bloqueado"]:
            raise _error("Desbloqueá el objeto antes de cambiarlo de grupo.")
        q = grupo
        while q is not None:
            if q == i:
                raise _error("Un grupo no puede quedar dentro de sí mismo.")
            q = arriba.get(q)
    mundo = {i: acumulada(b, i) for i in ids}
    destino = np.eye(3) if grupo is None else acumulada(b, grupo)
    for i in ids:
        padre = arriba.get(i)
        if padre is not None:
            b.objetos[padre]["entidades"].remove(i)
        if grupo is not None:
            b.objetos[grupo]["entidades"].append(i)
        local = np.linalg.inv(destino) @ mundo[i]
        o = b.objetos[i]
        if o.get("pasos"):
            # La historia paramétrica era relativa al padre anterior: queda la posición como valor fijo.
            o.pop("pasos")
            o.pop("base_parametrica", None)
        o["matriz"] = local.tolist()
    b._quitar_huerfanas()                      # el grupo que quedó vacío desaparece (también de su grupo padre)
    indice(b)


def eliminar(b, ids, contenido=True):
    """Borra objetos. Con `contenido` se van sus curvas (deshacer las recupera); sin él solo se quita el contenedor de
    un grupo personalizado y sus objetos quedan donde estaban."""
    ids = list(dict.fromkeys(ids))
    if not ids or any(i not in b.objetos for i in ids):
        raise _error("Elegí objetos existentes para eliminar.")
    if any(b.objetos[i]["bloqueado"] for i in ids):
        raise _error("Desbloqueá el objeto antes de eliminarlo.")
    if not contenido:
        if any(categoria(b, i) != "grupos" for i in ids):
            raise _error("Solo un grupo personalizado se puede quitar conservando su contenido.")
        for i in ids:
            desagrupar(b, i)
        return
    pendientes, vistos = list(ids), set()              # un hijo bloqueado dentro de un grupo también frena el borrado
    while pendientes:
        i = pendientes.pop()
        if i in vistos or i not in b.objetos:
            continue
        vistos.add(i)
        if b.objetos[i]["bloqueado"]:
            raise _error("Hay un objeto bloqueado dentro de la selección: desbloquealo antes de eliminarla.")
        pendientes.extend(b.objetos[i]["entidades"])
    for cid in curvas(b, ids):
        if cid in b.curvas:
            b.eliminar(cid)
    for i in ids:
        b.objetos.pop(i, None)                 # un grupo vacío ya lo quitó `_quitar_huerfanas`
    invalidar(b)


def normalizar_seleccion(b, ids):
    """Las herramientas tradicionales admiten el objeto entero, nunca una parte de sus controles ocultos."""
    seleccion = set(ids)
    ind = indice(b)
    reemplazos = {}
    for i in ids:
        if i not in ind:
            continue
        raiz = ind[i][0]
        o = b.objetos[raiz]
        if o.get("texto_automatico") == i and np.array_equal(o["matriz"], IDENTIDAD):
            continue
        if raiz not in seleccion and not set(curvas(b, [raiz])) <= seleccion:
            raise _error("Elegí el objeto vectorial completo; sus curvas no se transforman por separado.")
        reemplazos[i] = raiz
    return list(dict.fromkeys(reemplazos.get(i, i) for i in ids))


def crear(b, entidades, nombre="Objeto vectorial"):
    """Agrupa sin unir contornos ni cambiar ids; una agrupación puede contener otras."""
    ids = list(dict.fromkeys(entidades))
    if not ids:
        raise _error("Elegí al menos un elemento para crear el objeto.")
    ocupados = {i for o in b.objetos.values() for i in o["entidades"]}
    if ocupados.intersection(ids):
        raise _error("Elegí los objetos completos; esos elementos ya pertenecen a un objeto.")
    cids = set(curvas(b, ids))
    puntos = set(b.puntos_de(cids))
    dentro = cids | puntos
    for vinculo in (*b.restricciones.values(), *b.cotas.values()):
        refs = set(vinculo.entidades)
        if refs & dentro and not refs <= dentro:
            raise _error("Hay restricciones con geometría exterior: quitá ese vínculo antes de agrupar.")
        if refs & dentro and getattr(vinculo, "datos", {}).get("origen"):
            raise _error("Hay geometría anclada al origen: quitá el anclaje antes de convertirla en objeto.")
    oid = b._nuevo_id()
    b.objetos[oid] = {"id": oid, "nombre": str(nombre), "entidades": ids, "matriz": [list(f) for f in IDENTIDAD],
                      "pivote": None, "visible": True, "bloqueado": False, "proporciones": True}
    invalidar(b)
    return oid


def validar(b):
    """Valida los datos serializados sin reparar ni eliminar geometría silenciosamente."""
    for oid, o in b.objetos.items():
        if (not isinstance(oid, int) or isinstance(oid, bool) or oid < 1 or oid != o["id"]
                or oid in b.curvas or oid in b.puntos or oid in b.restricciones or oid in b.cotas or not o["entidades"]):
            raise _error("Identificador de objeto repetido u objeto vacío en el proyecto.")
        matriz(o["matriz"])
        p = o.get("pivote")
        if p is not None and (len(p) != 2 or not all(math.isfinite(float(v)) for v in p)):
            raise _error("El pivote del objeto debe ser un punto finito en milímetros.")
        if not all(isinstance(o.get(k, True), bool) for k in ("visible", "bloqueado", "perfiles")):
            raise _error("Visible, bloqueado y en perfiles tienen que ser verdadero o falso.")
        if o.get("regla_relleno", "nonzero") not in ("nonzero", "evenodd"):
            raise _error("La regla de relleno del SVG debe ser nonzero o evenodd.")
        for paso in o.get("pasos", []):
            if "matriz" in paso:
                matriz(paso["matriz"])
            else:
                datos = paso["parametros"]
                if set(datos) - {"dx", "dy", "angulo", "sx", "sy", "pivote"}:
                    raise _error("Hay un parámetro de transformación desconocido en el objeto.")
        if o.get("pasos"):
            matriz(o["base_parametrica"])
    invalidar(b)
    indice(b)


def _conica(prim):
    """Círculo/elipse/arco → B-spline racional cuadrática EXACTA, sin discretizar."""
    tipo, cid, centro, r = prim[:4]
    if tipo in ("circulo", "arco"):
        a, bb, giro = r, r, 0.0
        t0, t1 = prim[4:6] if tipo == "arco" else (0.0, 2 * math.pi)
    else:
        a, bb, giro = prim[3:6]
        t0, t1 = prim[6:8] if tipo == "arco_elipse" else (0.0, 2 * math.pi)
    while t1 <= t0 + 1e-12:
        t1 += 2 * math.pi
    n = max(1, int(math.ceil((t1 - t0) / (math.pi / 2))))
    polos, pesos = [], []
    c, s = math.cos(giro), math.sin(giro)

    def punto(t, w=1.0):
        x, y = a * math.cos(t) / w, bb * math.sin(t) / w
        return (centro[0] + c * x - s * y, centro[1] + s * x + c * y)
    for k in range(n):
        ini, fin = t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n
        w = math.cos((fin - ini) / 2)
        if not polos:
            polos.append(punto(ini))
            pesos.append(1.0)
        polos.extend((punto((ini + fin) / 2, w), punto(fin)))
        pesos.extend((w, 1.0))
    nudos = (0.0,) * 3 + tuple(v for k in range(1, n) for v in (k / n, k / n)) + (1.0,) * 3
    return ("spline", cid, tuple(polos), nudos, 2, tuple(pesos))


def transformar_primitiva(prim, m):
    """Transformación afín exacta: líneas, curvas de control y cónicas racionales."""
    tipo, cid = prim[:2]
    if np.array_equal(m, IDENTIDAD):
        return prim

    def punto(q):
        return tuple(m[:2, :2] @ q + m[:2, 2])
    if tipo == "linea":
        return (tipo, cid, punto(prim[2]), punto(prim[3]))
    if tipo == "spline":
        pts = np.asarray(prim[2]) @ m[:2, :2].T + m[:2, 2]
        return (tipo, cid, tuple(map(tuple, pts)), *prim[3:])
    centro = punto(prim[2])
    circular = tipo in ("circulo", "arco")
    a, bb, giro = (prim[3], prim[3], 0.0) if circular else prim[3:6]
    c, s = math.cos(giro), math.sin(giro)
    base = m[:2, :2] @ np.array([[c * a, -s * bb], [s * a, c * bb]])
    u, radios, vt = np.linalg.svd(base)
    if np.linalg.det(u) < 0:
        u[:, 1] *= -1
        vt[1] *= -1
    ang = math.atan2(u[1, 0], u[0, 0])
    arco = tipo in ("arco", "arco_elipse")
    if arco:
        ts = prim[4:6] if circular else prim[6:8]
        extremos = [math.atan2(*(vt @ [math.cos(t), math.sin(t)])[::-1]) for t in ts]
        if np.linalg.det(vt) < 0:
            extremos.reverse()
    if abs(radios[0] - radios[1]) < 1e-12 * max(radios[0], 1):
        return (("arco", cid, centro, float(radios[0]), *(t + ang for t in extremos)) if arco
                else ("circulo", cid, centro, float(radios[0])))
    return (("arco_elipse" if arco else "elipse", cid, centro, *map(float, radios), ang)
            + (tuple(extremos) if arco else ()))


def inmutable(valor):
    return tuple(inmutable(v) for v in valor) if isinstance(valor, (list, tuple, np.ndarray)) else valor


@lru_cache(maxsize=16384)
def primitiva_cacheada(prim, m):
    return transformar_primitiva(prim, np.asarray(m))


def primitivas(b, oid):
    return [p for i in curvas(b, [oid]) for p in b.primitivas(i)]


@lru_cache(maxsize=4096)
def _polinomios(prim):
    from scipy.interpolate import BSpline, PPoly
    p = _conica(prim) if prim[0] != "spline" else prim
    polos, nudos, grado, pesos = p[2:]
    w = np.ones(len(polos)) if pesos is None else np.asarray(pesos)
    denominador = PPoly.from_spline(BSpline(nudos, w, grado))
    numeradores = tuple(PPoly.from_spline(BSpline(nudos, np.asarray(polos)[:, eje] * w, grado)) for eje in (0, 1))
    return p, denominador, numeradores


@lru_cache(maxsize=4096)
def limites_primitiva(prim):
    """Extremos analíticos (incluye raíces de derivadas racionales); precisión de doble flotante."""
    from .boceto import evaluar_primitiva
    if prim[0] == "linea":
        pts = np.asarray(prim[2:4], float)
    elif prim[0] in ("circulo", "elipse"):
        cx, cy = prim[2]
        if prim[0] == "circulo":
            dx = dy = prim[3]
        else:
            a, b, giro = prim[3:6]
            c, s = math.cos(giro), math.sin(giro)
            dx, dy = math.hypot(a * c, b * s), math.hypot(a * s, b * c)
        return (cx - dx, cy - dy, cx + dx, cy + dy)
    elif (prim[0] == "spline" and prim[4] == 3 and len(prim[2]) == 4 and
          prim[3] == (0., 0., 0., 0., 1., 1., 1., 1.) and
          (prim[5] is None or all(w == 1 for w in prim[5]))):
        # SVG y texto: Bézier cúbica polinómica; no necesita construir cuatro PPoly racionales.
        p0, p1, p2, p3 = np.asarray(prim[2], float)
        a, b, c = -p0 + 3 * p1 - 3 * p2 + p3, 3 * p0 - 6 * p1 + 3 * p2, 3 * (p1 - p0)
        ts = [0., 1.]
        for eje in (0, 1):
            ts.extend(float(t.real) for t in np.roots((3 * a[eje], 2 * b[eje], c[eje]))
                      if abs(t.imag) < 1e-9 and 0 < t.real < 1)
        t = np.asarray(ts)[:, None]
        pts = ((a * t + b) * t + c) * t + p0
    else:
        p, denominador, numeradores = _polinomios(prim)
        ts = set(p[3])
        for eje in (0, 1):
            numerador = numeradores[eje]
            for k, (ta, tb) in enumerate(zip(denominador.x, denominador.x[1:], strict=False)):
                if tb <= ta:
                    continue
                a, d = np.poly1d(numerador.c[:, k]), np.poly1d(denominador.c[:, k])
                for z in np.roots(np.polysub(np.polymul(np.polyder(a), d), np.polymul(a, np.polyder(d)))):
                    if abs(z.imag) < 1e-9 and 0 < z.real < tb - ta:
                        ts.add(float(ta + z.real))
        pts = np.array([evaluar_primitiva(p, t)[0] for t in sorted(ts)])
    return (*pts.min(axis=0), *pts.max(axis=0))


def vueltas_primitiva(prim, q):
    """Número de cruces orientados con el semirrayo +X, por raíces de las curvas exactas."""
    if prim[0] == "linea":
        a, z = prim[2:4]
        cruz = (z[0] - a[0]) * (q[1] - a[1]) - (q[0] - a[0]) * (z[1] - a[1])
        return 1 if a[1] <= q[1] < z[1] and cruz > 0 else -1 if z[1] <= q[1] < a[1] and cruz < 0 else 0
    _p, den, nums = _polinomios(prim)
    total = 0
    for k, (ta, tb) in enumerate(zip(den.x, den.x[1:], strict=False)):
        if tb <= ta:
            continue
        px, py, w = nums[0].c[:, k], nums[1].c[:, k], den.c[:, k]
        pol = np.polysub(py, q[1] * w)
        for raiz in np.roots(pol):
            t = float(raiz.real)
            if abs(raiz.imag) > 1e-9 or t < -1e-10 or t > tb - ta + 1e-10:
                continue
            if np.polyval(px, t) / np.polyval(w, t) <= q[0]:
                continue
            dy = np.polyval(np.polyder(pol), t) / np.polyval(w, t)
            if abs(dy) < 1e-12:
                continue  # tangencia al semirrayo: no cambia el número de vueltas
            if t <= 1e-10 and dy < 0 or t >= tb - ta - 1e-10 and dy > 0:
                continue
            total += 1 if dy > 0 else -1
    return total


def caja(b, ids):
    cajas = [limites_primitiva(p) for i in ids for p in primitivas(b, i)]
    if not cajas:
        raise _error("El objeto no tiene geometría utilizable.")
    v = np.asarray(cajas)
    return (float(v[:, 0].min()), float(v[:, 1].min()), float(v[:, 2].max()), float(v[:, 3].max()))


def pivote(b, oid):
    o = b.objetos[oid]
    if o["pivote"] is None:
        x0, y0, x1, y1 = caja(b, [oid])
        return ((x0 + x1) / 2, (y0 + y1) / 2)
    # El pivote se guarda en el sistema local del objeto, independiente de su geometría.
    m = acumulada(b, oid)
    return tuple(m[:2, :2] @ o["pivote"] + m[:2, 2])


def acumulada(b, oid):
    padres = {i: k for k, o in b.objetos.items() for i in o["entidades"] if i in b.objetos}
    m, camino = matriz(b.objetos[oid]["matriz"]), {oid}
    while oid in padres:
        oid = padres[oid]
        if oid in camino:
            raise _error("La jerarquía de objetos tiene un ciclo.")
        camino.add(oid)
        m = matriz(b.objetos[oid]["matriz"]) @ m
    return m


def poner_pivote(b, oid, punto):
    q = np.asarray((*punto, 1.0), float)
    if q.shape != (3,) or not np.isfinite(q).all():
        raise _error("El pivote debe ser un punto finito en milímetros.")
    b.objetos[oid]["pivote"] = (np.linalg.inv(acumulada(b, oid)) @ q)[:2].tolist()


def transformar(b, ids, m, parametros=None, *, pasos=None):
    """Una matriz por objeto; la geometría original y las firmas de los perfiles no cambian."""
    from .boceto import MEDIDA_MAXIMA
    ids = list(dict.fromkeys(ids))
    m = matriz(m)
    if not ids or any(i not in b.objetos for i in ids):
        raise _error("Elegí objetos existentes para transformar.")
    if any(b.objetos[i]["bloqueado"] for i in ids):
        raise _error("Hay un objeto bloqueado: desbloquealo antes de transformarlo.")
    conjuntos = [set(curvas(b, [i])) for i in ids]
    if any(a & z for k, a in enumerate(conjuntos) for z in conjuntos[k + 1:]):
        raise _error("No se puede transformar a la vez un grupo y uno de sus elementos.")
    anteriores = {i: b.objetos[i]["matriz"] for i in ids}
    try:
        for i in ids:
            local = matriz(b.objetos[i]["matriz"])
            padre = acumulada(b, i) @ np.linalg.inv(local)
            b.objetos[i]["matriz"] = (np.linalg.inv(padre) @ m @ padre @ local).tolist()
        invalidar(b)
        if any(abs(v) > MEDIDA_MAXIMA for v in caja(b, ids)):
            raise _error("El objeto transformado supera 1 km desde el origen del boceto.")
    except Exception:
        for i, anterior in anteriores.items():
            b.objetos[i]["matriz"] = anterior
        invalidar(b)
        raise
    for i in ids:
        o = b.objetos[i]
        if parametros is not None or pasos is not None or o.get("pasos"):
            if "base_parametrica" not in o:
                o["base_parametrica"], o["pasos"] = anteriores[i], []
            delta = matriz(o["matriz"]) @ np.linalg.inv(matriz(anteriores[i]))
            o["pasos"].extend(copy.deepcopy(pasos) if pasos is not None else
                              [{"parametros": copy.deepcopy(parametros)}] if parametros is not None else
                              [{"matriz": delta.tolist()}])


def restablecer(b, ids):
    """Restablece la transformación del recurso a su posición importada; conserva curvas y sus ids CAD."""
    if not ids or any(i not in raices(b) for i in ids):
        raise _error("Elegí objetos raíz completos para restablecer su transformación.")
    if any(b.objetos[i]["bloqueado"] for i in ids):
        raise _error("Desbloqueá el objeto antes de restablecer su transformación.")
    for i in ids:
        o = b.objetos[i]
        o["matriz"] = [list(f) for f in IDENTIDAD]
        o["pivote"] = None
        o.pop("base_parametrica", None)
        o.pop("pasos", None)
    invalidar(b)


def expresiones(b):
    return [v for o in b.objetos.values() for p in o.get("pasos", [])
            for k, v in p.get("parametros", {}).items() if k != "pivote" and isinstance(v, str)]


def evaluar(b, valor):
    """Resuelve fórmulas únicamente en la copia del recálculo (igual que las cotas)."""
    for o in b.objetos.values():
        if not o.get("pasos"):
            continue
        m = matriz(o["base_parametrica"])
        for paso in o["pasos"]:
            if "parametros" in paso:
                p = paso["parametros"]
                delta = afin(**{k: v if k == "pivote" else valor(v, k) for k, v in p.items()})
            else:
                delta = matriz(paso["matriz"])
            m = delta @ m
        o["matriz"] = m.tolist()
    invalidar(b)
    if any(o.get("pasos") for o in b.objetos.values()):
        from .boceto import MEDIDA_MAXIMA
        if any(abs(v) > MEDIDA_MAXIMA for v in caja(b, raices(b))):
            raise _error("La transformación paramétrica supera 1 km desde el origen del boceto.")


def desagrupar(b, oid):
    """Quita solo un nivel; conserva ids, curvas, transformaciones y grupos interiores.

    Una hoja (un elemento del SVG) NO se separa: sus curvas tienen que quedar juntas para que el contorno
    cerrado y la regla de relleno se conserven; desagruparla deja el objeto como estaba.
    """
    o = b.objetos[oid]
    if o["bloqueado"]:
        raise _error("Desbloqueá el objeto antes de desagruparlo.")
    if not any(i in b.objetos for i in o["entidades"]):
        return [oid]
    hijos = list(o["entidades"])
    for i in hijos:
        hijo = b.objetos[i]
        anterior = hijo["matriz"]
        hijo["matriz"] = (matriz(o["matriz"]) @ matriz(anterior)).tolist()
        if o.get("pasos") or hijo.get("pasos"):
            hijo["base_parametrica"] = hijo.get("base_parametrica", anterior)
            hijo["pasos"] = (hijo.get("pasos", []) + [{"matriz": o.get("base_parametrica", o["matriz"])}]
                              + copy.deepcopy(o.get("pasos", [])))
    for padre in b.objetos.values():
        if oid in padre["entidades"]:
            j = padre["entidades"].index(oid)
            padre["entidades"][j:j + 1] = hijos
    del b.objetos[oid]
    invalidar(b)
    return hijos


def duplicar(b, ids, dx=10.0, dy=0.0):
    """Duplica objetos y su jerarquía con nuevos ids; las curvas se copian una sola vez."""
    salida = []
    for oid in ids:
        if oid not in raices(b):
            raise _error("Para duplicar, elegí un objeto raíz completo.")
        cids = curvas(b, [oid])
        _puntos, mapa = b._copiar(cids, lambda q: q)

        def copiar(i, mapa=mapa):
            if i not in b.objetos:
                return mapa[i]
            o = copy.deepcopy(b.objetos[i])
            if o.get("texto_automatico") in mapa:
                o["texto_automatico"] = mapa[o["texto_automatico"]]
            if "sentidos_svg" in o:
                o["sentidos_svg"] = {str(mapa[int(k)]): v for k, v in o["sentidos_svg"].items() if int(k) in mapa}
            nuevo = b._nuevo_id()
            o["id"], o["entidades"] = nuevo, [copiar(h) for h in o["entidades"]]
            b.objetos[nuevo] = o
            return nuevo
        nuevo = copiar(oid)
        b.objetos[nuevo]["nombre"] += " (copia)"
        b.objetos[nuevo]["bloqueado"] = False
        salida.append(nuevo)
    invalidar(b)
    transformar(b, salida, afin(dx, dy))
    return salida


def alinear(b, ids, modo, referencia="seleccion", objeto_referencia=None, separacion=None):
    """Alinea cajas o reparte huecos exactos; agrupar nunca hace booleanas."""
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise _error("Elegí los objetos para alinear.")
    cajas = {i: caja(b, [i]) for i in ids}
    ref = ((0.0,) * 4 if referencia == "origen" else caja(b, [objeto_referencia])
           if referencia == "objeto" else caja(b, ids))
    ejes = {"izquierda": (0, 0), "derecha": (0, 2), "abajo": (1, 1), "arriba": (1, 3),
            "centro_h": (0, None), "centro_v": (1, None)}
    if modo == "origen":
        transformar(b, ids, afin(-(ref[0] + ref[2]) / 2, -(ref[1] + ref[3]) / 2))
        return
    if modo in ("distribuir_h", "distribuir_v"):
        if len(ids) < 3 and separacion is None:
            raise _error("Para distribuir sin separación, elegí al menos tres objetos.")
        eje = int(modo == "distribuir_v")
        orden = sorted(ids, key=lambda i: (cajas[i][eje], i))
        largos = {i: cajas[i][eje + 2] - cajas[i][eje] for i in ids}
        hueco = ((ref[eje + 2] - ref[eje] - sum(largos.values())) / (len(ids) - 1)
                 if separacion is None else float(separacion))
        pos = cajas[orden[0]][eje]
        deltas = []
        for i in orden:
            deltas.append((i, eje, pos - cajas[i][eje]))
            pos += largos[i] + hueco
    elif modo in ejes:
        eje, k = ejes[modo]
        valor = lambda q: q[k] if k is not None else (q[eje] + q[eje + 2]) / 2  # noqa: E731
        deltas = [(i, eje, valor(ref) - valor(cajas[i])) for i in ids if i != objeto_referencia]
    else:
        raise _error("La alineación solicitada no existe.")
    if any(b.objetos[i]["bloqueado"] for i, _e, _d in deltas):
        raise _error("Hay un objeto bloqueado en la selección.")
    for i, eje, d in deltas:
        transformar(b, [i], afin(d if eje == 0 else 0.0, d if eje else 0.0))


def simplificar(b, oid, tolerancia=0.01):
    """Elimina redundancia lineal con cota conservadora acumulada; nunca ajusta Bézier ni cierra huecos."""
    from .boceto import Restriccion, puntos_primitiva
    if not math.isfinite(tolerancia) or not 0 < tolerancia <= 1:
        raise _error("La tolerancia de simplificación debe estar entre 0 y 1 mm.")
    if b.objetos[oid]["bloqueado"]:
        raise _error("Desbloqueá el objeto antes de simplificarlo.")
    ids = set(curvas(b, [oid]))
    antes = primitivas(b, oid)
    escala = max(float(np.linalg.norm(indice(b)[i][2][:2, :2], 2)) for i in ids)
    # Como mucho N fusiones, cada una a menos de tol/N; conserva una cota de error global.
    epsilon = min(tolerancia / (max(len(ids), 1) * escala), 1e-9)
    guardia = min(b.restricciones, default=0) - 1
    b.restricciones[guardia] = Restriccion(guardia, "fijo", [i for i in b.curvas if i not in ids])
    try:
        informe = b.limpiar(epsilon, duplicados=True, huecos=False, colineales=True)
    finally:
        b.restricciones.pop(guardia, None)
    despues = primitivas(b, oid)
    lineas = [(np.asarray(p[2]), np.asarray(p[3])) for p in despues if p[0] == "linea"]
    desvio = 0.0
    for p in antes:
        if p[0] != "linea" or not lineas:
            continue
        for q in puntos_primitiva(p):
            dmin = math.inf
            for a, z in lineas:
                d = z - a
                t = np.clip(np.dot(np.asarray(q) - a, d) / max(float(d @ d), 1e-30), 0, 1)
                dmin = min(dmin, float(np.linalg.norm(np.asarray(q) - a - t * d)))
            desvio = max(desvio, dmin)
    if desvio > tolerancia:
        raise _error("La simplificación superó la tolerancia: conservá el objeto original.")
    return {"before": len(antes), "after": len(despues), "removed": informe["duplicadas"] + informe["colineales"],
            "measured_deviation_mm": desvio, "deviation_bound_mm": len(ids) * epsilon * escala,
            "tolerance_mm": tolerancia}
