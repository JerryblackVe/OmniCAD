# -*- coding: utf-8 -*-
"""
Herramientas del grupo "boceto": planos de construcción, bocetos 2D, restricciones, cotas y perfiles.

Cómo se orientan las coordenadas 2D (x, y) del boceto, en mm, según el plano (lo decide `geo.Plano`):
  - XY: x → eje X, y → eje Y; la normal (sentido positivo de una extrusión) es +Z.
  - XZ: x → eje X, y → eje Z; la normal es −Y (una extrusión positiva avanza hacia −Y).
  - YZ: x → eje Y, y → eje Z; la normal es +X.
  - Plano de construcción: el mismo marco que el plano de origen del que se desfasó.

Cada `draw_*` edita el `OpBoceto` con `doc.reemplazar` (sobre una copia, nunca en el lugar): es UN paso de
deshacer. Los ids de entidades, restricciones y cotas del boceto son enteros estables (no cambian al
editar ni al recalcular).
"""
import difflib
import math
from typing import Literal

from ..nucleo import geometria as geo
from ..restricciones import Boceto, ErrorBoceto
from ..restricciones.boceto import validar_valor_cota
from ..timeline.operaciones import OpBoceto, OpPlano
from ..timeline.parametros import ANGULO, LONGITUD, evaluar
from . import selectores as sl
from .errores import ErrorAPI, error
from .registro import Expr, herramienta

PLANOS_ORIGEN = ("XY", "XZ", "YZ")
_ENTIDADES = {"linea": "line", "circulo": "circle", "arco": "arc", "elipse": "ellipse", "arco_elipse": "elliptical_arc",
              "spline": "spline", "conica": "conic", "texto": "text"}
RESTRICCIONES = {"coincident": "coincidente", "horizontal": "horizontal", "vertical": "vertical",
                 "parallel": "paralela", "perpendicular": "perpendicular", "equal": "igual", "tangent": "tangente",
                 "concentric": "concentrica", "midpoint": "punto_medio", "fix": "fijo", "collinear": "colineal",
                 "symmetry": "simetrica", "curvature": "curvatura"}
COTAS = {"distance": "distancia", "horizontal": "distancia_h", "vertical": "distancia_v", "radius": "radio",
         "diameter": "diametro", "angle": "angulo", "offset": "desfase"}
_RESTRICCION_A_INGLES = {v: k for k, v in RESTRICCIONES.items()} | {"poligono": "polygon", "desfase": "offset",
                                                                     "patron": "pattern"}
_COTA_A_INGLES = {v: k for k, v in COTAS.items()}


def _r(x):
    return round(float(x), 4) + 0.0


def texto_expr(valor):
    """Número (mm o grados) o expresión de texto → texto de expresión del timeline."""
    return valor.strip() if isinstance(valor, str) else repr(float(valor))


# ---------------------------------------------------------------- búsqueda de planos y bocetos
def nombre_nuevo(doc, base, clase, filtro=None):
    """Nombre libre «<base><n>» (n = cantidad de pasos de esa clase + 1, o los que cumplan `filtro`)."""
    n = sum(1 for o in doc.operaciones if isinstance(o, clase) and (filtro is None or filtro(o))) + 1
    usados = {o.nombre.casefold() for o in doc.operaciones}
    while f"{base}{n}".casefold() in usados:
        n += 1
    return f"{base}{n}"


def referencia_plano(sesion, plane):
    """'XY' | 'XZ' | 'YZ' o el id/nombre de un plano de construcción → valor de `OpBoceto.p['plano']`."""
    ref = str(plane).strip()
    if ref.upper() in PLANOS_ORIGEN:
        return ref.upper()
    planos = [o for o in sesion.doc.operaciones[:sesion.doc.marcador] if isinstance(o, OpPlano)]
    hallados = [o for o in planos if o.id == ref] or [o for o in planos if o.nombre.casefold() == ref.casefold()]
    if len(hallados) == 1:
        return hallados[0].id
    if hallados:
        raise error("AMBIGUOUS_REFERENCE", f"Hay {len(hallados)} planos llamados «{ref}»: "
                    + ", ".join(o.id for o in hallados) + ".")
    opciones = list(PLANOS_ORIGEN) + [o.id for o in planos] + [o.nombre for o in planos]
    parecidos = difflib.get_close_matches(ref, opciones, n=3, cutoff=0.5)
    raise error("PLANE_NOT_FOUND", f"No existe el plano '{ref}'.",
                *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []))


def plano_o_cara(sesion, plane, body=None):
    """Dónde va un boceto nuevo: (plano, marco, id de cara, referencia de cara). Un plano de origen o de construcción da
    (referencia, None, None, None); una cara plana (selector como '>Z' o id 'Cuerpo1/F6', evaluado sobre `body` o el
    único cuerpo) da ('cara', marco de la cara, id efímero, referencia persistente con la que el boceto sigue a la
    cara en cada recálculo). Lo comparten create_sketch y sketch_from_spec."""
    try:
        return referencia_plano(sesion, plane), None, None, None
    except ErrorAPI as e:
        if e.error_kind != "PLANE_NOT_FOUND" or not (sl.es_id(plane) or sl.parece_selector(plane)):
            raise
    cuerpo, elem = sl.elegir_uno(sesion, plane, "cara", body)
    return "cara", sl.plano_de_cara(elem).marco(), sl.emitir_id(sesion, cuerpo, elem), sl.referencia(cuerpo, elem)


def op_boceto(sesion, ref=None):
    """`OpBoceto` por id o nombre; sin `ref`, el último boceto activo del timeline."""
    doc = sesion.doc
    if ref is None or not str(ref).strip():
        activos = [o for o in doc.operaciones[:doc.marcador] if isinstance(o, OpBoceto)]
        if not activos:
            raise error("SKETCH_NOT_FOUND", "El documento todavía no tiene ningún boceto.")
        return activos[-1]
    ref = str(ref).strip()
    bocetos = [o for o in doc.operaciones if isinstance(o, OpBoceto)]
    for o in bocetos:
        if o.id == ref:
            return o
    hallados = [o for o in bocetos if o.nombre.casefold() == ref.casefold()]
    if len(hallados) == 1:
        return hallados[0]
    if hallados:
        raise error("AMBIGUOUS_REFERENCE", f"Hay {len(hallados)} bocetos llamados «{ref}»: "
                    + ", ".join(o.id for o in hallados) + ".")
    otro = next((o for o in doc.operaciones if o.id == ref), None)
    if otro is not None:
        raise error("SKETCH_NOT_FOUND", f"El paso '{ref}' ({otro.nombre}) es de tipo {otro.TIPO}, no un boceto.")
    opciones = [o.id for o in bocetos] + [o.nombre for o in bocetos]
    parecidos = difflib.get_close_matches(ref, opciones, n=3, cutoff=0.5)
    raise error("SKETCH_NOT_FOUND", f"No existe el boceto '{ref}'.",
                *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []))


def boceto_resuelto(sesion, op):
    """`BocetoResuelto` del final del timeline (con perfiles y solver) o None si el paso no está activo."""
    return sesion.doc.estado_final.bocetos.get(op.id)


def boceto_activo(sesion, ref=None):
    """(op, resuelto) o error SKETCH_NOT_FOUND si el boceto está suprimido, con error o después del marcador."""
    op = op_boceto(sesion, ref)
    br = boceto_resuelto(sesion, op)
    if br is None:
        estado = next((r.estado for o, r in zip(sesion.doc.operaciones, sesion.doc.resultados, strict=False)
                       if o.id == op.id), "")
        raise error("SKETCH_NOT_FOUND", f"El boceto «{op.nombre}» ({op.id}) no está disponible ahora (estado: "
                    f"{estado or 'desconocido'}): puede estar suprimido, con error o después del marcador.")
    return op, br


def seleccionar_perfiles(br, op, profile):
    """Índice, lista de índices, 'all' o 'largest' → lista de perfiles del boceto. Errores PROFILE_*."""
    perfiles = br.perfiles
    if not perfiles:
        if any(not c.construccion for c in br.boceto.curvas.values()):
            raise error("PROFILE_NOT_CLOSED", f"El boceto «{op.nombre}» ({op.id}) tiene curvas pero ninguna región "
                        "cerrada.")
        raise error("PROFILE_NOT_FOUND", f"El boceto «{op.nombre}» ({op.id}) no tiene perfiles: está vacío o solo "
                    "tiene geometría de construcción.")
    if isinstance(profile, str):
        clave = profile.strip().casefold()
        if clave == "all":
            return list(perfiles)
        if clave == "largest":
            return [max(perfiles, key=lambda p: p.area)]
        if clave.lstrip("-").isdigit():
            profile = int(clave)
        else:
            raise error("PROFILE_NOT_FOUND", f"Selección de perfil desconocida: '{profile}'.",
                        "Usá un índice, una lista de índices, 'all' o 'largest'.")
    indices = profile if isinstance(profile, list) else [profile]
    if not indices:
        raise error("PROFILE_NOT_FOUND", "La lista de perfiles está vacía.")
    elegidos = []
    for i in indices:
        if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(perfiles):
            raise error("PROFILE_NOT_FOUND", f"El boceto «{op.nombre}» ({op.id}) no tiene el perfil {i!r}: tiene "
                        f"{len(perfiles)} (índices 0 a {len(perfiles) - 1}).")
        if perfiles[i] not in elegidos:
            elegidos.append(perfiles[i])
    return elegidos


# ---------------------------------------------------------------- estado del solver
def estado_solver(br):
    """('fully_constrained' | 'under_constrained' | 'over_constrained' | 'unknown', grados de libertad | None)."""
    if br is None:
        return "unknown", None
    if not br.solver.ok:
        return "over_constrained", br.solver.gdl
    return ("fully_constrained" if br.solver.gdl == 0 else "under_constrained"), br.solver.gdl


def _exigir_sin_conflicto(sesion, op, previo_ok, que):
    br = boceto_resuelto(sesion, op)
    if br is not None and previo_ok and not br.solver.ok:
        raise error("SKETCH_OVERCONSTRAINED", f"{que} deja el boceto «{op.nombre}» en conflicto: "
                    f"{br.solver.descripcion()}")


# ---------------------------------------------------------------- números finitos
def _finito(v):
    """True si `v` es un número (no bool) finito: NaN, ±inf y enteros que no entran en un float dan False."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    try:
        return math.isfinite(v)
    except OverflowError:
        return False


def _exigir_finitos(argumentos):
    """INVALID_ARGUMENTS si un número de los argumentos (o de una lista anidada) es NaN o infinito: con una
    coordenada así, el cálculo de perfiles de OpenCascade no termina nunca. Se llama con `locals()`."""
    def revisar(nombre, v):
        if isinstance(v, (list, tuple)):
            for i, x in enumerate(v):
                revisar(f"{nombre}[{i}]", x)
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and not _finito(v):
            raise error("INVALID_ARGUMENTS", f"'{nombre}' tiene que ser un número finito (llegó {v!r}).")
    for nombre, v in argumentos.items():
        revisar(nombre, v)


# ---------------------------------------------------------------- constructores sobre un Boceto
def _xy(v, que):
    try:
        x, y = v
        x, y = float(x), float(y)
    except (TypeError, ValueError, OverflowError):
        x = y = math.nan
    if not (math.isfinite(x) and math.isfinite(y)):
        raise error("INVALID_GEOMETRY", f"{que} tiene que ser [x, y] con números finitos (mm).")
    return x, y


def _linea(b, x1, y1, x2, y2, construccion=False):
    if math.hypot(x2 - x1, y2 - y1) < 1e-9:
        raise ErrorBoceto("Una línea necesita dos puntos distintos.")
    lid = b.agregar_linea((x1, y1), (x2, y2), construccion)
    ln = b.curvas[lid]
    return {"": lid, "start": ln.p1, "end": ln.p2}


def _rectangulo(b, x1, y1, x2, y2, construccion=False):
    x1, x2, y1, y2 = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
    lineas = b.agregar_rectangulo((x1, y1), (x2, y2), construccion)
    alias = {lado: lineas[i] for i, lado in enumerate(("bottom", "right", "top", "left"))}
    alias.update({f"c{i + 1}": b.curvas[lineas[i]].p1 for i in range(4)})
    return alias


def _circulo(b, cx, cy, radio, construccion=False):
    cid = b.agregar_circulo((cx, cy), radio, construccion)
    return {"": cid, "center": b.curvas[cid].centro}


def _arco(b, cx, cy, sx, sy, barrido, construccion=False):
    r = math.hypot(sx - cx, sy - cy)
    if r < 1e-9:
        raise ErrorBoceto("El punto inicial del arco no puede coincidir con el centro.")
    if abs(barrido) < 1e-9 or abs(barrido) > 360 - 1e-6:
        raise ErrorBoceto("El ángulo de barrido del arco tiene que estar entre 0 y 360 grados (sin incluirlos).")
    a = math.atan2(sy - cy, sx - cx) + math.radians(barrido)
    fin = (cx + r * math.cos(a), cy + r * math.sin(a))
    if barrido > 0:
        aid = b.agregar_arco_centro((cx, cy), (sx, sy), fin, construccion)
        arco = b.curvas[aid]
        return {"": aid, "center": arco.centro, "start": arco.inicio, "end": arco.fin}
    aid = b.agregar_arco_centro((cx, cy), fin, (sx, sy), construccion)   # el boceto solo guarda arcos antihorarios
    arco = b.curvas[aid]
    return {"": aid, "center": arco.centro, "start": arco.fin, "end": arco.inicio}


def _arco_3_puntos(b, p1, p2, p3, construccion=False):
    aid = b.agregar_arco_3_puntos(p1, p2, p3, construccion)
    arco = b.curvas[aid]
    horario = math.dist(b.coords(arco.inicio), p1) > 1e-6 * max(1.0, math.dist(p1, p3))
    return {"": aid, "center": arco.centro, "start": arco.fin if horario else arco.inicio,
            "end": arco.inicio if horario else arco.fin}


def _poligono(b, lados, radio, cx, cy, giro, circunscrito, construccion=False):
    if lados < 3:
        raise ErrorBoceto("Un polígono necesita al menos 3 lados.")
    if lados > 64:      # el mismo tope que la interfaz (ui/editor_boceto.py, _evaluar_campo)
        raise ErrorBoceto(f"Un polígono admite como máximo 64 lados, como la interfaz (recibió {lados}).")
    if radio <= 1e-9:
        raise ErrorBoceto("El radio del polígono tiene que ser positivo.")
    rv = radio / math.cos(math.pi / lados) if circunscrito else radio
    a0 = math.radians(giro)
    esquinas = [(cx + rv * math.cos(a0 + 2 * math.pi * k / lados), cy + rv * math.sin(a0 + 2 * math.pi * k / lados))
                for k in range(lados)]
    cid = b.agregar_circulo((cx, cy), radio, True)         # círculo de construcción guía, como en la interfaz
    verts = [b.agregar_punto(*q) for q in esquinas]
    ls = [b.agregar_linea(verts[k], verts[(k + 1) % lados], construccion) for k in range(lados)]
    for k in range(1, lados):
        b.agregar_restriccion("igual", [ls[0], ls[k]])
    for v, ln in zip(verts, ls, strict=True):
        b.agregar_restriccion("tangente" if circunscrito else "coincidente", [ln if circunscrito else v, cid])
    alias = {"": cid, "circle": cid, "center": b.curvas[cid].centro}
    alias.update({f"side{k + 1}": ls[k] for k in range(lados)})
    alias.update({f"v{k + 1}": verts[k] for k in range(lados)})
    return alias


def _spline(b, puntos, tipo, grado, cerrada, construccion=False):
    pts = [_xy(p, "Cada punto de la spline") for p in puntos]
    control = tipo == "control_points"
    if control and (grado not in (3, 5) or len(pts) < grado + 1):
        raise ErrorBoceto(f"Una spline de puntos de control de grado {grado} necesita grado 3 o 5 y al menos "
                          f"{grado + 1} puntos.")
    # como Fusion, la spline de ajuste es siempre cúbica: su grado se ignora (con 0 o −1 rompía la interpolación)
    sid = b.agregar_spline(pts, "control" if control else "ajuste", grado if control else 3, cerrada,
                           construccion=construccion)
    ids = b.curvas[sid].pts
    alias = {"": sid, "start": ids[0], "end": ids[-1]}
    alias.update({f"p{i + 1}": p for i, p in enumerate(ids)})
    return alias


# ---------------------------------------------------------------- informes
def _claves(b):
    return {"puntos": set(b.puntos), "curvas": set(b.curvas), "restricciones": set(b.restricciones),
            "cotas": set(b.cotas)}


def _tipo_curva(c):
    return _ENTIDADES.get(c.tipo, c.tipo)


def _paso(op):
    return {"id": op.id, "name": op.nombre, "type": op.TIPO}


def _informe_edicion(sesion, op, b, antes):
    br = boceto_resuelto(sesion, op)
    estado, gdl = estado_solver(br)
    nuevas = [c for cid, c in b.curvas.items() if cid not in antes["curvas"]]
    return {"sketch": _paso(op),
            "entities": [{"id": c.id, "type": _tipo_curva(c)} for c in nuevas],
            "points": [p for p in b.puntos if p not in antes["puntos"]],
            "constraints": [{"id": r.id, "type": _RESTRICCION_A_INGLES.get(r.tipo, r.tipo)}
                            for rid, r in b.restricciones.items() if rid not in antes["restricciones"]],
            "profiles": None if br is None else len(br.perfiles), "dof": gdl, "status": estado}


def _dibujar(sesion, ref, constructor):
    """Edita el boceto con `constructor(boceto)` sobre una copia y la reemplaza en el timeline (un paso)."""
    op = op_boceto(sesion, ref)
    nueva = op.copia()
    b = nueva.boceto
    antes = _claves(b)
    try:
        constructor(b)
    except ErrorBoceto as e:
        raise error("INVALID_GEOMETRY", str(e)) from e
    sesion.doc.reemplazar(op.id, nueva)
    return _informe_edicion(sesion, nueva, b, antes)


def _info_plano(plano):
    return {"origin": [_r(c) for c in plano.origen], "u_axis": [_r(c) for c in plano.u],
            "v_axis": [_r(c) for c in plano.v], "normal": [_r(c) for c in plano.normal]}


def _caja_uv(plano, cara):
    caja = geo.caja_envolvente(cara)
    if not caja:
        return None
    (x0, y0, z0), (x1, y1, z1) = caja
    uv = [plano.a_uv((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    return {"min": [_r(min(p[0] for p in uv)), _r(min(p[1] for p in uv))],
            "max": [_r(max(p[0] for p in uv)), _r(max(p[1] for p in uv))]}


def info_perfiles(br):
    return [{"index": i, "area": _r(p.area), "centroid": [_r(p.centroide_uv[0]), _r(p.centroide_uv[1])],
             "bounding_box": _caja_uv(br.plano, p.cara), "curves": sorted(p.firma)}
            for i, p in enumerate(br.perfiles)]


def _info_curva(b, c):
    xy = lambda pid: [_r(v) for v in b.coords(pid)]  # noqa: E731
    d = {"id": c.id, "type": _tipo_curva(c), "construction": c.construccion, "points": c.puntos()}
    if c.eje:
        d["centerline"] = True
    if c.tipo == "linea":
        d.update(start=xy(c.p1), end=xy(c.p2), length=_r(math.dist(b.coords(c.p1), b.coords(c.p2))))
    elif c.tipo == "circulo":
        d.update(center=xy(c.centro), radius=_r(c.radio))
    elif c.tipo == "arco":
        (cx, cy), (sx, sy), (ex, ey) = b.coords(c.centro), b.coords(c.inicio), b.coords(c.fin)
        d.update(center=xy(c.centro), radius=_r(b.radio(c.id)), start=xy(c.inicio), end=xy(c.fin),
                 start_angle=_r(math.degrees(math.atan2(sy - cy, sx - cx))),
                 end_angle=_r(math.degrees(math.atan2(ey - cy, ex - cx))))
    elif c.tipo == "spline":
        d.update(spline_type="control_points" if c.modo == "control" else "fit_points", degree=c.grado,
                 closed=c.cerrada, vertices=[xy(p) for p in c.pts])
    elif c.tipo in ("elipse", "arco_elipse"):
        d.update(center=xy(c.centro), minor_radius=_r(c.radio_menor))
    elif c.tipo == "texto":
        d.update(text=c.texto)
    return d


def _valor_cota(sesion, k):
    try:
        valores = sesion.doc.parametros.valores()
        return _r(evaluar(k.expresion, ANGULO if k.tipo == "angulo" else LONGITUD, valores))
    except Exception:  # noqa: BLE001 — informe: un valor ilegible no debe tumbar get_sketch
        return None


def info_boceto(sesion, op):
    """Informe completo de un boceto (lo que devuelve get_sketch)."""
    br = boceto_resuelto(sesion, op)
    b = br.boceto if br is not None else op.boceto
    estado, gdl = estado_solver(br)
    fijos = b.puntos_fijos()
    resultado = next((r for o, r in zip(sesion.doc.operaciones, sesion.doc.resultados, strict=False) if o.id == op.id),
                     None)
    info = {"id": op.id, "name": op.nombre, "plane": op.p.get("plano"), "available": br is not None,
            "plane_frame": _info_plano(br.plano) if br is not None else None,
            "status": estado, "dof": gdl,
            "message": br.solver.descripcion() if br is not None else (resultado.mensaje if resultado else ""),
            "entities": [_info_curva(b, c) for c in b.curvas.values()],
            "points": [{"id": p.id, "x": _r(p.x), "y": _r(p.y), "fixed": p.id in fijos} for p in b.puntos.values()],
            "constraints": [{"id": r.id, "type": _RESTRICCION_A_INGLES.get(r.tipo, r.tipo), "entities": r.entidades}
                            for r in b.restricciones.values()],
            "dimensions": [{"id": k.id, "type": _COTA_A_INGLES.get(k.tipo, k.tipo), "entities": k.entidades,
                            "expression": k.expresion, "value": _valor_cota(sesion, k)} for k in b.cotas.values()],
            "profiles": info_perfiles(br) if br is not None else []}
    return info


# ================================================================ herramientas
@herramienta("create_construction_plane", "boceto",
             "Crea un plano de construcción desfasado de un plano de origen (XY, XZ, YZ) o de otro plano de construcción. "
             "Sirve para dibujar bocetos fuera del origen. Va en el grupo «boceto» porque su uso típico es "
             "create_sketch(plane=<este plano>). El desfase es sobre la normal del plano base.", modifica=True)
def create_construction_plane(sesion, plane: str = "XY", offset: Expr = "10 mm", name: str | None = None):
    """
    plane: plano base: "XY", "XZ", "YZ" o el id/nombre de otro plano de construcción.
    offset: desfase en mm sobre la normal del plano base (número o expresión con parámetros, p. ej. "alto / 2").
    name: nombre del plano; vacío = "Plano1", "Plano2"…
    """
    base = referencia_plano(sesion, plane)
    doc = sesion.doc
    nombre = name.strip() if name and name.strip() else nombre_nuevo(doc, "Plano", OpPlano)
    op = OpPlano(doc.nuevo_id(), nombre, tipo="desfase", base=base, distancia=texto_expr(offset))
    doc.agregar(op)
    plano = doc.estado_final.planos[op.id]
    return {"plane": _paso(op), "base": base, "offset": op.p["distancia"], **_info_plano(plano)}


@herramienta("create_sketch", "boceto",
             "Crea un boceto vacío sobre un plano o sobre una cara plana. Coordenadas del boceto (mm): en XY x→X e y→Y "
             "(normal +Z); en XZ x→X e y→Z (normal −Y: una extrusión positiva avanza hacia −Y); en YZ x→Y e y→Z "
             "(normal +X). Un plano de construcción usa el marco de su plano base. SOBRE UNA CARA (plane = selector como "
             "'>Z' o id de find_faces como 'Cuerpo1/F6'; tiene que ser UNA cara plana): el boceto queda sobre la cara con "
             "la normal exterior como normal (extruir con join crece hacia afuera; con cut entra al material solo, como Fusion). Ejes: en "
             "caras horizontales x→+X; en las demás y→+Z (hacia arriba) y x = y × normal; el origen es la proyección del "
             "origen del mundo sobre el plano de la cara, no una esquina (plane_frame lo da y find_faces trae center_uv, "
             "el centro de cada cara en estos ejes). El boceto queda asociado a la cara, como en Fusion: si un parámetro "
             "la mueve o la gira, el boceto la sigue; si la cara desaparece, el paso da error. Con varios cuerpos, body dice en cuál se evalúa "
             "el selector de la cara.",
             modifica=True)
def create_sketch(sesion, plane: str = "XY", name: str | None = None, body: str | None = None):
    """
    plane: "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana: selector (">Z") o id ("Cuerpo1/F6").
    name: nombre del boceto; vacío = "Boceto1", "Boceto2"…
    body: id o nombre del cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo. No se usa con un plano ni con un id de cara.
    """
    doc = sesion.doc
    ref, marco, cara, ref_cara = plano_o_cara(sesion, plane, body)
    nombre = name.strip() if name and name.strip() else nombre_nuevo(doc, "Boceto", OpBoceto)
    op = OpBoceto(doc.nuevo_id(), nombre, plano=ref, marco=marco, cara=ref_cara)
    doc.agregar(op)
    br = boceto_resuelto(sesion, op)
    info = {"sketch": _paso(op), "plane": ref, "plane_frame": _info_plano(br.plano) if br is not None else None,
            "profiles": 0}
    if cara:
        info["face"] = cara
    return info


@herramienta("draw_line", "boceto", "Dibuja una línea en el boceto (un paso de deshacer). Coordenadas en mm sobre el "
             "plano del boceto. Devuelve los ids creados (línea y puntos) y la cantidad de perfiles.", modifica=True)
def draw_line(sesion, start_x: float, start_y: float, end_x: float, end_y: float, sketch: str | None = None,
              construction: bool = False):
    """
    start_x: x del punto inicial (mm).
    start_y: y del punto inicial (mm).
    end_x: x del punto final (mm).
    end_y: y del punto final (mm).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una línea de construcción (no forma perfiles).
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: _linea(b, start_x, start_y, end_x, end_y, construction))


@herramienta("draw_rectangle", "boceto",
             "Dibuja un rectángulo (4 líneas con restricciones horizontal y vertical). Tres formas de darlo: dos esquinas "
             "opuestas (x1, y1, x2, y2); centro y tamaño (center_x, center_y, width, height); o esquina mínima y tamaño "
             "(origin_x, origin_y, width, height). width es el tamaño en x del boceto y height en y.", modifica=True)
def draw_rectangle(sesion, x1: float | None = None, y1: float | None = None, x2: float | None = None,
                   y2: float | None = None, center_x: float | None = None, center_y: float | None = None,
                   origin_x: float | None = None, origin_y: float | None = None, width: float | None = None,
                   height: float | None = None, sketch: str | None = None, construction: bool = False):
    """
    x1: x de la primera esquina (forma de dos esquinas).
    y1: y de la primera esquina.
    x2: x de la esquina opuesta.
    y2: y de la esquina opuesta.
    center_x: x del centro (forma centro + tamaño).
    center_y: y del centro.
    origin_x: x de la esquina mínima (forma esquina + tamaño; 0 si solo se da origin_y).
    origin_y: y de la esquina mínima.
    width: tamaño en x del boceto (mm, mayor que cero), para las formas con tamaño.
    height: tamaño en y del boceto (mm, mayor que cero), para las formas con tamaño.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un rectángulo de construcción (no forma perfiles).
    """
    _exigir_finitos(locals())
    esquinas = (x1, y1, x2, y2)
    if any(v is not None for v in esquinas):
        if any(v is None for v in esquinas):
            raise error("INVALID_ARGUMENTS", "Para la forma de dos esquinas hacen falta x1, y1, x2 e y2.")
        a, b_ = (x1, y1), (x2, y2)
    else:
        if width is None or height is None:
            raise error("INVALID_ARGUMENTS", "Indicá las dos esquinas (x1, y1, x2, y2) o un tamaño (width y height) "
                        "con center_x/center_y o con origin_x/origin_y.")
        if not (width > 0 and height > 0):
            raise error("INVALID_GEOMETRY", f"width y height tienen que ser mayores que cero (llegaron {width:g} y "
                        f"{height:g}).")
        if center_x is not None or center_y is not None:
            cx, cy = center_x or 0.0, center_y or 0.0
            a, b_ = (cx - width / 2, cy - height / 2), (cx + width / 2, cy + height / 2)
        else:
            ox, oy = origin_x or 0.0, origin_y or 0.0
            a, b_ = (ox, oy), (ox + width, oy + height)
    return _dibujar(sesion, sketch, lambda b: _rectangulo(b, a[0], a[1], b_[0], b_[1], construction))


@herramienta("draw_circle", "boceto", "Dibuja un círculo por centro y radio (un paso de deshacer). Un círculo cerrado "
             "forma un perfil; dentro de un rectángulo da dos perfiles (el anillo y el disco).", modifica=True)
def draw_circle(sesion, radius: float, center_x: float = 0.0, center_y: float = 0.0, sketch: str | None = None,
                construction: bool = False):
    """
    radius: radio en mm (positivo).
    center_x: x del centro (mm).
    center_y: y del centro (mm).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un círculo de construcción (no forma perfiles).
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: _circulo(b, center_x, center_y, radius, construction))


@herramienta("draw_arc", "boceto",
             "Dibuja un arco. Dos formas: centro + punto inicial + ángulo de barrido (center_x, center_y, start_x, "
             "start_y, sweep_angle; positivo = antihorario) o tres puntos (start_x, start_y, mid_x, mid_y, end_x, "
             "end_y). Un arco solo forma un perfil si se cierra con otras curvas.", modifica=True)
def draw_arc(sesion, start_x: float, start_y: float, center_x: float | None = None, center_y: float | None = None,
             sweep_angle: float | None = None, mid_x: float | None = None, mid_y: float | None = None,
             end_x: float | None = None, end_y: float | None = None, sketch: str | None = None,
             construction: bool = False):
    """
    start_x: x del punto inicial (mm).
    start_y: y del punto inicial (mm).
    center_x: x del centro (forma centro + barrido).
    center_y: y del centro.
    sweep_angle: ángulo de barrido en grados, entre -360 y 360 sin incluirlos; positivo = antihorario.
    mid_x: x de un punto intermedio del arco (forma de tres puntos).
    mid_y: y del punto intermedio.
    end_x: x del punto final (forma de tres puntos).
    end_y: y del punto final.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un arco de construcción (no forma perfiles).
    """
    _exigir_finitos(locals())
    if sweep_angle is not None:
        if center_x is None or center_y is None:
            raise error("INVALID_ARGUMENTS", "Con sweep_angle hacen falta center_x y center_y.")
        return _dibujar(sesion, sketch, lambda b: _arco(b, center_x, center_y, start_x, start_y, sweep_angle,
                                                        construction))
    if None in (mid_x, mid_y, end_x, end_y):
        raise error("INVALID_ARGUMENTS", "Indicá center_x, center_y y sweep_angle, o los tres puntos: "
                    "start, mid_x/mid_y y end_x/end_y.")
    return _dibujar(sesion, sketch, lambda b: _arco_3_puntos(b, (start_x, start_y), (mid_x, mid_y), (end_x, end_y),
                                                             construction))


@herramienta("create_polygon", "boceto", "Dibuja un polígono regular de n lados (líneas iguales sobre un círculo guía "
             "de construcción, como la interfaz). Inscrito: los vértices están sobre el círculo de radio `radius`; "
             "circunscrito: los lados son tangentes a ese círculo.", modifica=True)
def create_polygon(sesion, sides: int, radius: float, center_x: float = 0.0, center_y: float = 0.0,
                   rotation: float = 0.0, kind: Literal["inscribed", "circumscribed"] = "inscribed",
                   sketch: str | None = None, construction: bool = False):
    """
    sides: cantidad de lados (3 a 64).
    radius: radio del círculo guía en mm (circunradio si es inscrito, apotema si es circunscrito).
    center_x: x del centro (mm).
    center_y: y del centro (mm).
    rotation: ángulo en grados del primer vértice respecto del eje x del boceto.
    kind: "inscribed" (vértices sobre el círculo) o "circumscribed" (lados tangentes al círculo).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un polígono de construcción (no forma perfiles).
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: _poligono(b, sides, radius, center_x, center_y, rotation,
                                                        kind == "circumscribed", construction))


@herramienta("draw_spline", "boceto", "Dibuja una spline: de ajuste (pasa por los puntos) o de puntos de control "
             "(grado 3 o 5, necesita al menos grado+1 puntos).", modifica=True)
def draw_spline(sesion, points: list[list[float]], spline_type: Literal["fit_points", "control_points"] = "fit_points",
                degree: int = 3, closed: bool = False, sketch: str | None = None, construction: bool = False):
    """
    points: lista de puntos [x, y] en mm sobre el plano del boceto.
    spline_type: "fit_points" (pasa por los puntos) o "control_points" (los puntos son los polos).
    degree: grado de la spline de puntos de control (3 o 5); se ignora en la de ajuste.
    closed: true para cerrar la spline de ajuste (forma un perfil).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una spline de construcción (no forma perfiles).
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: _spline(b, points, spline_type, degree, closed, construction))


@herramienta("add_constraint", "boceto",
             "Agrega una restricción geométrica entre entidades del boceto (ids de get_sketch: curvas y puntos). Si "
             "choca con las que ya hay, falla y el boceto queda como estaba. Entidades por tipo: horizontal y "
             "vertical: una línea o dos puntos; parallel, perpendicular, collinear y equal: dos líneas (equal también "
             "dos círculos/arcos); coincident: un punto y otro punto o una curva; midpoint: un punto y una línea o "
             "arco; tangent y concentric: dos curvas; fix: una o más entidades; symmetry: dos entidades y la línea eje.",
             modifica=True)
def add_constraint(sesion, sketch: str,
                   type: Literal["coincident", "horizontal", "vertical", "parallel", "perpendicular", "equal",  # noqa: A002
                                 "tangent", "concentric", "midpoint", "fix", "collinear", "symmetry", "curvature"],
                   entities: list[int]):
    """
    sketch: id o nombre del boceto.
    type: tipo de restricción.
    entities: ids de las entidades (curvas o puntos), en el orden que pide el tipo.
    """
    op = op_boceto(sesion, sketch)
    previo = boceto_resuelto(sesion, op)
    nueva = op.copia()
    b = nueva.boceto
    _exigir_entidades(b, entities)
    antes = _claves(b)
    try:
        rid = b.agregar_restriccion(RESTRICCIONES[type], list(entities))
    except ErrorBoceto as e:
        raise error("INVALID_CONSTRAINT", str(e)) from e
    sesion.doc.reemplazar(op.id, nueva)
    _exigir_sin_conflicto(sesion, nueva, previo is None or previo.solver.ok, f"La restricción «{type}»")
    informe = _informe_edicion(sesion, nueva, b, antes)
    return {"sketch": informe["sketch"], "constraint": {"id": rid, "type": type, "entities": list(entities)},
            "profiles": informe["profiles"], "dof": informe["dof"], "status": informe["status"]}


def _exigir_entidades(b, ids):
    for i in ids:
        if i not in b.puntos and i not in b.curvas:
            cercanos = difflib.get_close_matches(str(i), [str(k) for k in list(b.puntos) + list(b.curvas)], n=3,
                                                 cutoff=0.5)
            raise error("ENTITY_NOT_FOUND", f"El boceto no tiene la entidad {i}.",
                        *([f"¿Quisiste decir: {', '.join(cercanos)}?"] if cercanos else []))


@herramienta("add_dimension", "boceto",
             "Agrega una cota (dimensión) que maneja la geometría. El valor es un número (mm o grados) o una expresión "
             "con parámetros ('ancho / 2'); si se omite, usa la medida actual. Las cotas de largo, radio, diámetro y "
             "desfase tienen que ser mayores que cero y de hasta 1.000.000 mm (1 km). Entidades por tipo: distance: dos "
             "puntos, una línea, un punto y una línea, o dos líneas; horizontal y vertical: dos puntos o una línea; "
             "radius y diameter: un círculo o arco; angle: dos líneas; offset: dos líneas o dos círculos/arcos.",
             modifica=True)
def add_dimension(sesion, sketch: str,
                  type: Literal["distance", "horizontal", "vertical", "radius", "diameter", "angle", "offset"],  # noqa: A002
                  entities: list[int], value: Expr | None = None):
    """
    sketch: id o nombre del boceto.
    type: tipo de cota.
    entities: ids de las entidades acotadas (curvas o puntos), en el orden que pide el tipo.
    value: valor: número (mm; grados en angle) o expresión con parámetros, p. ej. "radio_agujero * 2". Vacío = medida actual.
    """
    op, br = boceto_activo(sesion, sketch)
    nueva = op.copia()
    b = nueva.boceto
    _exigir_entidades(b, entities)
    interno = COTAS[type]
    if value is None:
        try:
            medida = br.boceto.medir_cota(interno, list(entities))
        except (ErrorBoceto, KeyError, ValueError, IndexError) as e:
            raise error("INVALID_DIMENSION", f"No se pudo medir la cota «{type}» con esas entidades: {e}") from e
        expresion = repr(round(medida, 6))
    else:
        expresion = texto_expr(value)
    valor = evaluar(expresion, ANGULO if interno == "angulo" else LONGITUD, sesion.doc.parametros.valores())
    antes = _claves(b)
    try:
        kid = b.agregar_cota(interno, list(entities), expresion)
        validar_valor_cota(interno, valor)
    except ErrorBoceto as e:
        raise error("INVALID_DIMENSION", str(e)) from e
    sesion.doc.reemplazar(op.id, nueva)
    _exigir_sin_conflicto(sesion, nueva, br.solver.ok, f"La cota «{type}» = {expresion}")
    informe = _informe_edicion(sesion, nueva, b, antes)
    valor = _valor_cota(sesion, b.cotas[kid])
    return {"sketch": informe["sketch"], "dimension": {"id": kid, "type": type, "entities": list(entities),
                                                       "expression": expresion, "value": valor},
            "profiles": informe["profiles"], "dof": informe["dof"], "status": informe["status"]}


@herramienta("get_sketch", "boceto",
             "Informe de un boceto: plano y su marco 3D, entidades con ids estables (coordenadas ya resueltas por el "
             "solver), puntos, restricciones, cotas con su valor, perfiles (índice, área mm², centroide, caja "
             "[min/max en coordenadas del boceto] y curvas del borde) y estado (fully_constrained, "
             "under_constrained, over_constrained) con los grados de libertad.")
def get_sketch(sesion, sketch: str | None = None):
    """
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    return info_boceto(sesion, op_boceto(sesion, sketch))


# ---------------------------------------------------------------- sketch_from_spec
def _spec_error(i, tipo, texto):
    return error("INVALID_SPEC", f"Entidad {i} ({tipo}): {texto}")


def _campo(e, i, clave, alternativas=()):
    for k in (clave, *alternativas):
        if k in e:
            return e[k]
    raise _spec_error(i, e.get("type"), f"falta '{clave}'.")


def _numero(v, i, tipo, que):
    if not _finito(v):
        raise _spec_error(i, tipo, f"{que} tiene que ser un número finito.")
    return float(v)


def _construir_entidad(b, i, e):
    tipo = e.get("type")
    c = bool(e.get("construction", False))
    p = lambda k, *alt: _xy(_campo(e, i, k, alt), f"'{k}' de la entidad {i}")  # noqa: E731
    if tipo == "line":
        (x1, y1), (x2, y2) = p("start"), p("end")
        return _linea(b, x1, y1, x2, y2, c)
    if tipo == "rectangle":
        if "corner1" in e or "corner2" in e:
            (x1, y1), (x2, y2) = p("corner1"), p("corner2")
        else:
            w = _numero(_campo(e, i, "width"), i, tipo, "'width'")
            h = _numero(_campo(e, i, "height"), i, tipo, "'height'")
            if not (w > 0 and h > 0):
                raise _spec_error(i, tipo, "'width' y 'height' tienen que ser mayores que cero.")
            if "center" in e:
                cx, cy = p("center")
                x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
            else:
                x1, y1 = p("origin") if "origin" in e else (0.0, 0.0)
                x2, y2 = x1 + w, y1 + h
        return _rectangulo(b, x1, y1, x2, y2, c)
    if tipo == "circle":
        cx, cy = p("center")
        return _circulo(b, cx, cy, _numero(_campo(e, i, "radius"), i, tipo, "'radius'"), c)
    if tipo == "arc":
        if "mid" in e:
            return _arco_3_puntos(b, p("start"), p("mid"), p("end"), c)
        (cx, cy), (sx, sy) = p("center"), p("start")
        return _arco(b, cx, cy, sx, sy, _numero(_campo(e, i, "sweep"), i, tipo, "'sweep'"), c)
    if tipo == "polygon":
        cx, cy = p("center") if "center" in e else (0.0, 0.0)
        lados = _campo(e, i, "sides")
        if isinstance(lados, bool) or not isinstance(lados, int):
            raise _spec_error(i, tipo, "'sides' tiene que ser un entero.")
        return _poligono(b, lados, _numero(_campo(e, i, "radius"), i, tipo, "'radius'"), cx, cy,
                         _numero(e.get("rotation", 0.0), i, tipo, "'rotation'"), e.get("kind") == "circumscribed", c)
    if tipo == "spline":
        tipo_spline = e.get("spline_type", "fit_points")
        if tipo_spline not in ("fit_points", "control_points"):
            raise _spec_error(i, tipo, "'spline_type' es fit_points o control_points.")
        grado = e.get("degree", 3)
        if isinstance(grado, float) and grado.is_integer():
            grado = int(grado)
        if isinstance(grado, bool) or not isinstance(grado, int):
            raise _spec_error(i, tipo, "'degree' tiene que ser un entero (3 o 5).")
        return _spline(b, _campo(e, i, "points"), tipo_spline, grado, bool(e.get("closed", False)), c)
    if tipo == "point":
        x, y = p("at", "position")
        return {"": b.agregar_punto(x, y)}
    raise _spec_error(i, tipo, "tipo desconocido. Tipos: line, rectangle, circle, arc, polygon, spline, point.")


def _citar(token, alias, b, que):
    if isinstance(token, bool):
        raise error("INVALID_SPEC", f"{que}: '{token}' no es una cita válida.")
    if isinstance(token, int):
        _exigir_entidades(b, [token])
        return token
    if token in alias:
        return alias[token]
    base = str(token).split(".")[0]
    if str(token).isdigit() and int(token) in alias.values():
        return int(token)
    if base in {k.split(".")[0] for k in alias} and base == str(token):
        raise error("INVALID_SPEC", f"{que}: '{token}' no es una sola entidad; citá una parte "
                    f"(p. ej. '{token}.bottom' o '{token}.c1').")
    parecidos = difflib.get_close_matches(str(token), list(alias), n=3, cutoff=0.5)
    raise error("INVALID_SPEC", f"{que}: no existe la cita '{token}'.",
                *([f"¿Quisiste decir: {', '.join(parecidos)}?"] if parecidos else []))


@herramienta("sketch_from_spec", "boceto",
             "Crea un boceto COMPLETO en una sola llamada (un paso de deshacer): geometría, restricciones y cotas. "
             "entities: lista de {type, ...}: line{start,end}, rectangle{corner1,corner2 | center,width,height | "
             "origin,width,height}, circle{center,radius}, arc{center,start,sweep | start,mid,end}, "
             "polygon{sides,radius,center,rotation,kind}, spline{points,spline_type,degree,closed}, point{at}; todas "
             "aceptan id (nombre propio para citarla) y construction. Las coordenadas son [x, y] en mm del plano. "
             "constraints: [{type, entities:[citas]}]; dimensions: [{type, entities:[citas], value}] (value puede ser "
             "una expresión con parámetros). Citas: 'id' (la curva), 'id.start', 'id.end', 'id.center', y en un "
             "rectángulo 'id.bottom/right/top/left' (líneas) y 'id.c1..c4' (esquinas); un entero cita un id de "
             "entidad ya existente. Sin id, la entidad se cita 'e0', 'e1'… según su posición en la lista. plane es un "
             "plano o una cara plana (selector '>Z' o id de find_faces), con los mismos ejes que create_sketch sobre "
             "esa cara (find_faces da center_uv); con varios cuerpos, body dice en cuál se evalúa el selector. Devuelve "
             "handles (cita → id real), perfiles, estado y plane_frame (origen y ejes del plano).", modifica=True)
def sketch_from_spec(sesion, plane: str = "XY", entities: list[dict] | None = None,
                     constraints: list[dict] | None = None, dimensions: list[dict] | None = None,
                     name: str | None = None, body: str | None = None):
    """
    plane: "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana: selector (">Z") o id ("Cuerpo1/F6").
    entities: geometría del boceto (ver la descripción de la herramienta).
    constraints: restricciones, cada una {"type": ..., "entities": [citas]}.
    dimensions: cotas, cada una {"type": ..., "entities": [citas], "value": número o expresión}.
    name: nombre del boceto; vacío = "Boceto1", "Boceto2"…
    body: id o nombre del cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo. No se usa con un plano ni con un id de cara.
    """
    ref, marco, cara, ref_cara = plano_o_cara(sesion, plane, body)
    doc = sesion.doc
    b = Boceto()
    alias = {}
    try:
        for i, e in enumerate(entities or []):
            if not isinstance(e, dict):
                raise error("INVALID_SPEC", f"Entidad {i}: tiene que ser un objeto con 'type'.")
            partes = _construir_entidad(b, i, e)
            manejador = str(e.get("id", f"e{i}"))
            if any(k == manejador or k.startswith(manejador + ".") for k in alias):
                raise error("INVALID_SPEC", f"Entidad {i}: el id '{manejador}' está repetido.")
            for sufijo, eid in partes.items():
                alias[f"{manejador}.{sufijo}" if sufijo else manejador] = eid
        for j, r in enumerate(constraints or []):
            tipo = r.get("type") if isinstance(r, dict) else None
            if tipo not in RESTRICCIONES:
                raise error("INVALID_CONSTRAINT", f"Restricción {j}: tipo '{tipo}' desconocido.")
            ids = [_citar(t, alias, b, f"Restricción {j}") for t in (r.get("entities") or [])]
            try:
                b.agregar_restriccion(RESTRICCIONES[tipo], ids)
            except ErrorBoceto as e:
                raise error("INVALID_CONSTRAINT", f"Restricción {j}: {e}") from e
        valores = doc.parametros.valores()
        for j, d in enumerate(dimensions or []):
            tipo = d.get("type") if isinstance(d, dict) else None
            if tipo not in COTAS:
                raise error("INVALID_DIMENSION", f"Cota {j}: tipo '{tipo}' desconocido.")
            ids = [_citar(t, alias, b, f"Cota {j}") for t in (d.get("entities") or [])]
            if d.get("value") is None:
                raise error("INVALID_DIMENSION", f"Cota {j}: falta 'value' (número o expresión).")
            expresion = texto_expr(d["value"])
            valor = evaluar(expresion, ANGULO if tipo == "angle" else LONGITUD, valores)
            try:
                b.agregar_cota(COTAS[tipo], ids, expresion)
                validar_valor_cota(COTAS[tipo], valor)
            except ErrorBoceto as e:
                raise error("INVALID_DIMENSION", f"Cota {j}: {e}") from e
    except ErrorBoceto as e:
        raise error("INVALID_GEOMETRY", str(e)) from e
    nombre = name.strip() if name and name.strip() else nombre_nuevo(doc, "Boceto", OpBoceto)
    op = OpBoceto(doc.nuevo_id(), nombre, plano=ref, marco=marco, cara=ref_cara, boceto=b)
    doc.agregar(op)
    _exigir_sin_conflicto(sesion, op, True, "Las restricciones y cotas del spec")
    br = boceto_resuelto(sesion, op)
    estado, gdl = estado_solver(br)
    info = {"sketch": _paso(op), "plane": ref, "plane_frame": _info_plano(br.plano) if br is not None else None,
            "handles": alias, "entities": len(b.curvas), "constraints": len(b.restricciones),
            "dimensions": len(b.cotas), "profiles": None if br is None else len(br.perfiles), "dof": gdl,
            "status": estado}
    if cara:
        info["face"] = cara
    return info
