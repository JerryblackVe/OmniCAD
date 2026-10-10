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

Las herramientas que MODIFICAN geometría que ya existe (recortar, empalme, chaflán, desfase, simetría, patrones,
círculo tangente, curva de fusión, restringir automáticamente) calculan sobre la geometría YA RESUELTA por el
solver (la que muestra get_sketch), como el editor de la interfaz, y la guardan así. La lógica de cada una está en
`restricciones.boceto.Boceto` (la misma que usa la interfaz): acá solo se valida y se informa.
"""
import difflib
import math
from typing import Literal

from ..nucleo import geometria as geo
from ..restricciones import Boceto, ErrorBoceto, auto_restringir
from ..restricciones.boceto import ArcoElipse, Circulo, Elipse, Texto, validar_valor_cota
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


def _origen_fijo(b):
    """Punto fijo en (0, 0): el dato del boceto al que se acota (como el origen de Fusion). Usa uno que ya esté
    fijo ahí (también un punto proyectado) o lo crea con la restricción «fijo»."""
    for pid in sorted(b.puntos_fijos()):
        if math.hypot(*b.coords(pid)) < 1e-9:
            return pid
    pid = b.agregar_punto(0.0, 0.0)
    b.agregar_restriccion("fijo", [pid])
    return pid


def _acotar_desde_origen(b, pid):
    """Ubica el punto `pid` respecto del origen fijo con cotas horizontal y vertical (o restricciones horizontal /
    vertical cuando una distancia es cero, porque una cota de largo tiene que ser positiva)."""
    origen = _origen_fijo(b)
    x, y = b.coords(pid)
    if abs(x) < 1e-9:
        b.agregar_restriccion("vertical", [origen, pid])
    else:
        b.agregar_cota("distancia_h", [origen, pid], repr(round(abs(x), 9)))
    if abs(y) < 1e-9:
        b.agregar_restriccion("horizontal", [origen, pid])
    else:
        b.agregar_cota("distancia_v", [origen, pid], repr(round(abs(y), 9)))
    return origen


def _poligono(b, lados, radio, cx, cy, giro, circunscrito, construccion=False, acotar=False, expr_radio=None):
    """Polígono regular como la interfaz. Con `acotar` queda TOTALMENTE restringido: cota de radio del círculo guía
    (con `expr_radio`, la expresión que se guarda), giro fijado (horizontal / vertical o cota de ángulo contra una
    línea de referencia horizontal) y centro acotado desde el origen fijo del boceto."""
    if lados < 3:
        raise ErrorBoceto("Un polígono necesita al menos 3 lados.")
    if lados > 64:      # el mismo tope que la interfaz (ui/editor_boceto.py, _evaluar_campo)
        raise ErrorBoceto(f"Un polígono admite como máximo 64 lados, como la interfaz (recibió {lados}).")
    if radio <= 1e-9:
        raise ErrorBoceto("El radio del polígono tiene que ser positivo.")
    if acotar:
        validar_valor_cota("radio", radio)
    rv = radio / math.cos(math.pi / lados) if circunscrito else radio
    a0 = math.radians(giro)
    esquinas = [(cx + rv * math.cos(a0 + 2 * math.pi * k / lados), cy + rv * math.sin(a0 + 2 * math.pi * k / lados))
                for k in range(lados)]
    centro = (cx, cy)
    if acotar and math.hypot(cx, cy) < 1e-9:
        centro = _origen_fijo(b)                            # el centro ES el origen fijo
    cid = b.agregar_circulo(centro, radio, True)           # círculo de construcción guía, como en la interfaz
    verts = [b.agregar_punto(*q) for q in esquinas]
    ls = [b.agregar_linea(verts[k], verts[(k + 1) % lados], construccion) for k in range(lados)]
    for k in range(1, lados):
        b.agregar_restriccion("igual", [ls[0], ls[k]])
    for v, ln in zip(verts, ls, strict=True):
        b.agregar_restriccion("tangente" if circunscrito else "coincidente", [ln if circunscrito else v, cid])
    if circunscrito:
        # lados iguales y tangentes al círculo NO alcanzan con una cantidad par de lados: los tramos de tangencia
        # pueden alternar (largo a + b, b + a…) y queda un grado de libertad de más (un hexágono daba dof 5). La
        # restricción de polígono regular lo cierra.
        b.agregar_restriccion("poligono", list(ls))
    pc = b.curvas[cid].centro
    alias = {"": cid, "circle": cid, "center": pc}
    alias.update({f"side{k + 1}": ls[k] for k in range(lados)})
    alias.update({f"v{k + 1}": verts[k] for k in range(lados)})
    if not acotar:
        return alias
    alias["radius_dimension"] = b.agregar_cota("radio", [cid], expr_radio or repr(float(radio)))
    radial = b.agregar_linea(pc, verts[0], True)            # del centro al primer vértice: fija el giro
    alias["radial"] = radial
    a = giro % 360.0
    m = a % 180.0
    if min(m, 180.0 - m) < 1e-9:
        b.agregar_restriccion("horizontal", [radial])
    elif abs(m - 90.0) < 1e-9:
        b.agregar_restriccion("vertical", [radial])
    else:
        # una cota de ángulo necesita dos líneas: referencia horizontal del centro hasta el círculo guía
        q = b.agregar_punto(cx + radio, cy)
        ref = b.agregar_linea(pc, q, True)
        b.agregar_restriccion("horizontal", [ref])
        b.agregar_restriccion("coincidente", [q, cid])
        alias["reference"] = ref
        alias["angle_dimension"] = b.agregar_cota("angulo", [ref, radial], repr(round(a if a <= 180 else 360 - a, 9)))
    if pc != _origen_fijo(b):
        _acotar_desde_origen(b, pc)
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


def _elipse(b, cx, cy, radio_mayor, radio_menor, giro, construccion=False):
    """Elipse por centro, radios y giro del eje mayor (con sus ejes de construcción, como la interfaz)."""
    for v, que in ((radio_mayor, "mayor"), (radio_menor, "menor")):
        if not v > 1e-9:
            raise ErrorBoceto(f"El radio {que} de la elipse tiene que ser positivo (llegó {v:g}).")
        validar_valor_cota("radio", v)
    a = math.radians(giro)
    antes = set(b.curvas)
    eid = b.agregar_elipse((cx, cy), (cx + radio_mayor * math.cos(a), cy + radio_mayor * math.sin(a)), radio_menor,
                           construccion)
    e = b.curvas[eid]
    ejes = [c for c in b.curvas if c not in antes and c != eid]
    return {"": eid, "center": e.centro, "major": e.mayor, "major_axis": ejes[0], "minor_axis": ejes[1]}


RANURAS = {"center_to_center": ("centro", 2), "overall": ("total", 2), "center_point": ("punto", 2),
           "arc_three_points": ("arco_3p", 3), "arc_center": ("arco_centro", 3)}


def _ranura(b, tipo, puntos, ancho, construccion=False):
    """Ranura de la interfaz (líneas y arcos tangentes + eje de construcción). Alias: side1, end2, side2, end1 (los
    dos lados y los dos extremos curvos), axis (eje), center1 y center2 (centros de los extremos)."""
    if tipo not in RANURAS:
        raise ErrorBoceto(f"Tipo de ranura desconocido: {tipo}. Tipos: {', '.join(RANURAS)}.")
    interno, n = RANURAS[tipo]
    if not isinstance(puntos, (list, tuple)) or len(puntos) != n:
        raise ErrorBoceto(f"La ranura «{tipo}» necesita {n} puntos [x, y] (llegaron "
                          f"{len(puntos) if isinstance(puntos, (list, tuple)) else 'otra cosa'}).")
    pts = [_xy(p, f"El punto {i + 1} de la ranura") for i, p in enumerate(puntos)]
    if not (_finito(ancho) and ancho > 1e-9):
        raise ErrorBoceto(f"El ancho de la ranura tiene que ser un número positivo (llegó {ancho!r}).")
    validar_valor_cota("distancia", ancho)
    ids = b.agregar_ranura(interno, pts, float(ancho), construccion)
    alias = dict(zip(("side1", "end2", "side2", "end1", "axis"), ids, strict=True))
    alias.update(center1=b.curvas[ids[3]].centro, center2=b.curvas[ids[1]].centro)
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
    informe = {"sketch": _paso(op),
               "entities": [{"id": c.id, "type": _tipo_curva(c)} for c in nuevas],
               "points": [p for p in b.puntos if p not in antes["puntos"]],
               "constraints": [{"id": r.id, "type": _RESTRICCION_A_INGLES.get(r.tipo, r.tipo)}
                               for rid, r in b.restricciones.items() if rid not in antes["restricciones"]],
               "profiles": None if br is None else len(br.perfiles), "dof": gdl, "status": estado}
    cotas = [{"id": k.id, "type": _COTA_A_INGLES.get(k.tipo, k.tipo), "expression": k.expresion}
             for kid, k in b.cotas.items() if kid not in antes["cotas"]]
    if cotas:
        informe["dimensions"] = cotas
    borradas = sorted(antes["curvas"] - set(b.curvas))
    if borradas:
        informe["entities_deleted"] = borradas
    return informe


def valores_cotas(sesion, b):
    """{id de cota: valor en mm o grados} con los parámetros actuales (lo que el solver necesita)."""
    valores = sesion.doc.parametros.valores()
    return {k.id: evaluar(k.expresion, ANGULO if k.tipo == "angulo" else LONGITUD, valores) for k in b.cotas.values()}


def _sincronizar_con_solver(sesion, op, b):
    """Lleva a `b` (copia del boceto guardado de `op`) las coordenadas y los radios que dejó el solver, o sea lo que
    muestra get_sketch: así recortar, empalmar o copiar calculan sobre lo que el agente ve (la interfaz guarda el
    boceto ya resuelto). Si el boceto no está disponible o está en conflicto, queda la geometría guardada."""
    br = boceto_resuelto(sesion, op)
    if br is None or not br.solver.ok:
        return
    r = br.boceto
    for pid, p in b.puntos.items():
        q = r.puntos.get(pid)
        if q is not None:
            p.x, p.y = q.x, q.y
    for cid, c in b.curvas.items():
        k = r.curvas.get(cid)
        if isinstance(c, Circulo) and isinstance(k, Circulo):
            c.radio = k.radio
        elif isinstance(c, (Elipse, ArcoElipse)) and isinstance(k, (Elipse, ArcoElipse)):
            c.radio_menor = k.radio_menor


def _dibujar(sesion, ref, constructor, desde_solver=False):
    """Edita el boceto con `constructor(boceto)` sobre una copia y la reemplaza en el timeline (un paso). Con
    `desde_solver`, la copia parte de la geometría resuelta (ver `_sincronizar_con_solver`)."""
    op = op_boceto(sesion, ref)
    nueva = op.copia()
    b = nueva.boceto
    if desde_solver:
        _sincronizar_con_solver(sesion, op, b)
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
    if c.proyectada:
        d["projected"] = True
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
        (cx, cy), (mx, my) = b.coords(c.centro), b.coords(c.mayor)
        d.update(center=xy(c.centro), major_point=xy(c.mayor), major_radius=_r(math.hypot(mx - cx, my - cy)),
                 minor_radius=_r(c.radio_menor), angle=_r(math.degrees(math.atan2(my - cy, mx - cx))))
        if c.tipo == "arco_elipse":
            d.update(start=xy(c.inicio), end=xy(c.fin))
    elif c.tipo == "conica":
        d.update(start=xy(c.inicio), vertex=xy(c.vertice), end=xy(c.fin), rho=_r(c.rho))
    elif c.tipo == "texto":
        d.update(text=c.texto, position=xy(c.punto), font=c.fuente, height=_r(c.altura), angle=_r(c.angulo),
                 bold=c.negrita, italic=c.cursiva, letter_spacing=_r(c.espaciado), line_spacing=_r(c.interlineado),
                 align={"izq": "left", "centro": "center", "der": "right"}.get(c.alineacion, c.alineacion),
                 anchor={"base": "baseline", "arriba": "top", "medio": "middle", "abajo": "bottom"}.get(
                     c.ancla_v, c.ancla_v), box_width=_r(c.ancho_caja), flip_h=c.voltear_h, flip_v=c.voltear_v)
        if c.camino is not None:
            d.update(path_entity=c.camino, path_side="left" if c.camino_lado == "izq" else "right",
                     path_position=_r(c.camino_pos), path_offset=_r(c.camino_desfase), fit_path=c.camino_ajustar)
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
             "circunscrito: los lados son tangentes a ese círculo (radius = medio entrecaras). Sin más, le quedan 4 "
             "grados de libertad (centro, tamaño y giro); con fully_constrained=true queda TOTALMENTE acotado: cota "
             "de radio del círculo guía (guarda la expresión de radius, así sigue a un parámetro), giro fijado "
             "(restricción horizontal/vertical o cota de ángulo) y centro acotado desde un punto fijo en el origen "
             "del boceto (dof 0).", modifica=True)
def create_polygon(sesion, sides: int, radius: Expr, center_x: float = 0.0, center_y: float = 0.0,
                   rotation: float = 0.0, kind: Literal["inscribed", "circumscribed"] = "inscribed",
                   sketch: str | None = None, construction: bool = False, fully_constrained: bool = False):
    """
    sides: cantidad de lados (3 a 64).
    radius: radio del círculo guía en mm (circunradio si es inscrito, apotema si es circunscrito); número o expresión con parámetros ("entrecaras / 2").
    center_x: x del centro (mm).
    center_y: y del centro (mm).
    rotation: ángulo en grados del primer vértice respecto del eje x del boceto.
    kind: "inscribed" (vértices sobre el círculo) o "circumscribed" (lados tangentes al círculo).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un polígono de construcción (no forma perfiles).
    fully_constrained: true para dejarlo totalmente acotado (radio, giro y posición del centro): dof 0.
    """
    _exigir_finitos(locals())
    expresion = texto_expr(radius)
    valor = evaluar(expresion, LONGITUD, sesion.doc.parametros.valores())
    return _dibujar(sesion, sketch, lambda b: _poligono(b, sides, valor, center_x, center_y, rotation,
                                                        kind == "circumscribed", construction, fully_constrained,
                                                        expresion))


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
                         _numero(e.get("rotation", 0.0), i, tipo, "'rotation'"), e.get("kind") == "circumscribed", c,
                         bool(e.get("fully_constrained", False)))
    if tipo == "ellipse":
        cx, cy = p("center") if "center" in e else (0.0, 0.0)
        return _elipse(b, cx, cy, _numero(_campo(e, i, "major_radius"), i, tipo, "'major_radius'"),
                       _numero(_campo(e, i, "minor_radius"), i, tipo, "'minor_radius'"),
                       _numero(e.get("angle", 0.0), i, tipo, "'angle'"), c)
    if tipo == "slot":
        kind = e.get("kind", "center_to_center")
        if kind not in RANURAS:
            raise _spec_error(i, tipo, f"'kind' es uno de: {', '.join(RANURAS)}.")
        return _ranura(b, kind, _campo(e, i, "points"), _numero(_campo(e, i, "width"), i, tipo, "'width'"), c)
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
    raise _spec_error(i, tipo, "tipo desconocido. Tipos: line, rectangle, circle, arc, polygon, ellipse, slot, "
                      "spline, point.")


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
             "polygon{sides,radius,center,rotation,kind,fully_constrained}, ellipse{center,major_radius,minor_radius,"
             "angle}, slot{kind,points,width} (kind como en draw_slot), spline{points,spline_type,degree,closed}, "
             "point{at}; todas aceptan id (nombre propio para citarla) y construction. Las coordenadas son [x, y] en "
             "mm del plano. constraints: [{type, entities:[citas]}]; dimensions: [{type, entities:[citas], value}] "
             "(value puede ser una expresión con parámetros). Citas: 'id' (la curva), 'id.start', 'id.end', "
             "'id.center', en un rectángulo 'id.bottom/right/top/left' (líneas) y 'id.c1..c4' (esquinas), en un "
             "polígono 'id.side1..', 'id.v1..' y 'id.circle', en una elipse 'id.major' y 'id.major_axis/minor_axis', "
             "en una ranura 'id.side1/side2/end1/end2/axis/center1/center2'; un entero cita un id de "
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


# ================================================================ más geometría (como el editor de la interfaz)
_TIPO_A_TEXTO = {"linea": "una línea", "circulo": "un círculo", "arco": "un arco", "elipse": "una elipse",
                 "arco_elipse": "un arco de elipse", "spline": "una spline", "conica": "una cónica", "texto": "un texto",
                 "punto": "un punto"}


def _curva(b, cid, tipos=None, que="la entidad"):
    """La curva `cid` del boceto, o ENTITY_NOT_FOUND / INVALID_GEOMETRY si no existe o no es de `tipos`."""
    c = b.curvas.get(cid) if isinstance(cid, int) and not isinstance(cid, bool) else None
    if c is None:
        if cid in b.puntos:
            raise error("INVALID_GEOMETRY", f"{que.capitalize()} {cid} es un punto: acá hace falta una curva.")
        _exigir_entidades(b, [cid])
    if tipos and c.tipo not in tipos:
        raise error("INVALID_GEOMETRY", f"{que.capitalize()} {cid} es {_TIPO_A_TEXTO.get(c.tipo, c.tipo)}: acá hace "
                    f"falta {' o '.join(_TIPO_A_TEXTO.get(t, t) for t in tipos)}.")
    return c


def _opcional_xy(v, que):
    return None if v is None else _xy(v, que)


def _valor_expr(sesion, valor, tipo=LONGITUD):
    """(texto de la expresión, valor en mm o grados) de un número o una expresión con parámetros."""
    expresion = texto_expr(valor)
    return expresion, evaluar(expresion, tipo, sesion.doc.parametros.valores())


def _cota_valida(tipo, valor, que):
    try:
        validar_valor_cota(tipo, valor)
    except ErrorBoceto as e:
        raise error("INVALID_DIMENSION", f"{que}: {e}") from e


@herramienta("draw_ellipse", "boceto",
             "Dibuja una elipse (Fusion: Elipse) por centro, radio mayor, radio menor y giro del eje mayor. Como la "
             "interfaz, suma sus ejes mayor y menor como líneas de construcción, con el centro en su punto medio "
             "(sirven para acotarla). Una elipse cerrada forma un perfil.", modifica=True)
def draw_ellipse(sesion, major_radius: float, minor_radius: float, center_x: float = 0.0, center_y: float = 0.0,
                 angle: float = 0.0, sketch: str | None = None, construction: bool = False):
    """
    major_radius: semieje mayor en mm (positivo): distancia del centro al extremo del eje mayor.
    minor_radius: semieje menor en mm (positivo).
    center_x: x del centro (mm).
    center_y: y del centro (mm).
    angle: giro del eje mayor en grados respecto del eje x del boceto (antihorario).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una elipse de construcción (no forma perfiles).
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: _elipse(b, center_x, center_y, major_radius, minor_radius, angle,
                                                      construction))


@herramienta("draw_slot", "boceto",
             "Dibuja una ranura (Fusion: Ranura): dos lados y dos extremos redondos tangentes, más el eje de "
             "construcción. kind y points (cada uno [x, y] en mm): center_to_center = [centro de un extremo, centro "
             "del otro]; overall = [punta de un extremo, punta del otro] (largo total); center_point = [centro de la "
             "ranura, centro de un extremo]; arc_three_points = [centro de un extremo, centro del otro, un punto del "
             "arco del eje]; arc_center = [centro del arco, centro de un extremo, punto en la dirección del otro "
             "extremo] (antihorario). width es el ancho total. Forma un perfil cerrado.", modifica=True)
def draw_slot(sesion, points: list[list[float]], width: float,
              kind: Literal["center_to_center", "overall", "center_point", "arc_three_points",
                            "arc_center"] = "center_to_center",
              sketch: str | None = None, construction: bool = False):
    """
    points: 2 puntos [x, y] (ranuras rectas) o 3 (ranuras de arco), en mm; qué es cada uno depende de kind.
    width: ancho total de la ranura en mm (positivo; en una de arco, menor que el doble del radio del eje).
    kind: center_to_center, overall, center_point, arc_three_points o arc_center.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una ranura de construcción (no forma perfiles).
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: _ranura(b, kind, points, width, construction))


@herramienta("draw_point", "boceto", "Agrega un punto suelto al boceto (Fusion: Punto): sirve de referencia para cotas, "
             "restricciones, agujeros o el centro de un patrón circular.", modifica=True)
def draw_point(sesion, x: float, y: float, sketch: str | None = None):
    """
    x: x del punto (mm).
    y: y del punto (mm).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: b.agregar_punto(float(x), float(y)))


@herramienta("draw_conic", "boceto",
             "Dibuja una curva cónica (Fusion: Curva cónica) entre dos extremos, con el vértice (donde se cruzan las "
             "tangentes de los extremos) y Rho: 0.5 = parábola, menos = elipse, más = hipérbola.", modifica=True)
def draw_conic(sesion, start_x: float, start_y: float, end_x: float, end_y: float, vertex_x: float, vertex_y: float,
               rho: float = 0.5, sketch: str | None = None, construction: bool = False):
    """
    start_x: x del primer extremo (mm).
    start_y: y del primer extremo (mm).
    end_x: x del otro extremo (mm).
    end_y: y del otro extremo (mm).
    vertex_x: x del vértice (mm); no puede estar alineado con los extremos.
    vertex_y: y del vértice (mm).
    rho: forma de la curva, entre 0 y 1 sin incluirlos.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una cónica de construcción.
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: b.agregar_conica((start_x, start_y), (vertex_x, vertex_y),
                                                               (end_x, end_y), rho, construction))


@herramienta("draw_tangent_circle", "boceto",
             "Dibuja un círculo tangente a 2 o 3 líneas del boceto (Fusion: Círculo de 2 / 3 tangentes) y le agrega "
             "las restricciones de tangencia. Con 2 líneas, (x, y) dice en qué ángulo de las dos va y, sin radius, "
             "también su tamaño (el círculo pasa cerca de ese punto); entre dos paralelas el diámetro es la "
             "separación. Con 3 líneas sale el inscrito, o el que tenga sus tangencias más cerca de (x, y).",
             modifica=True)
def draw_tangent_circle(sesion, lines: list[int], x: float | None = None, y: float | None = None,
                        radius: float | None = None, sketch: str | None = None, construction: bool = False):
    """
    lines: ids de 2 o 3 líneas del boceto (get_sketch).
    x: x de un punto que ubica el círculo (mm); vacío = automático.
    y: y de ese punto (mm).
    radius: radio en mm (solo con 2 líneas no paralelas); vacío = el que pasa por (x, y).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un círculo de construcción.
    """
    _exigir_finitos(locals())
    if len(lines) not in (2, 3):
        raise error("INVALID_ARGUMENTS", f"lines lleva 2 o 3 ids de líneas (llegaron {len(lines)}).")
    if (x is None) != (y is None):
        raise error("INVALID_ARGUMENTS", "Pasá x e y juntos, o ninguno de los dos.")
    if radius is not None and (len(lines) == 3 or not radius > 0):
        raise error("INVALID_ARGUMENTS", "radius va solo con 2 líneas y tiene que ser positivo.")
    q = None if x is None else (float(x), float(y))

    def crear(b):
        for k in lines:
            _curva(b, k, ("linea",), "la línea")
        if len(set(lines)) != len(lines):
            raise ErrorBoceto("Elegí líneas distintas.")
        if len(lines) == 2:
            # sin punto: entre los puntos medios de las dos líneas (adentro del ángulo que forman, como al dibujar)
            medios = [tuple((u + v) / 2 for u, v in zip(*b._extremos_linea(k), strict=True)) for k in lines]
            ubicacion = q or ((medios[0][0] + medios[1][0]) / 2, (medios[0][1] + medios[1][1]) / 2)
            b.agregar_circulo_tangente(list(lines), ubicacion, radius, None, construction)
        else:
            b.agregar_circulo_tangente(list(lines), None, None, None if q is None else [q] * 3, construction)
    return _dibujar(sesion, sketch, crear, desde_solver=True)


@herramienta("draw_blend_curve", "boceto",
             "Une los extremos de dos curvas abiertas con una spline suave (Fusion: Curva de fusión), tangente (G1) o "
             "con curvatura continua (G2) en las dos uniones. Sin point1/point2 une los dos extremos más cercanos.",
             modifica=True)
def draw_blend_curve(sesion, entity1: int, entity2: int, point1: list[float] | None = None,
                     point2: list[float] | None = None, continuity: Literal["G1", "G2"] = "G1",
                     sketch: str | None = None):
    """
    entity1: id de la primera curva (línea, arco, spline o cónica; abierta).
    entity2: id de la segunda curva.
    point1: [x, y] cerca del extremo de entity1 que se une; vacío = automático.
    point2: [x, y] cerca del extremo de entity2 que se une; vacío = automático.
    continuity: G1 (tangente) o G2 (curvatura continua).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    p1, p2 = _opcional_xy(point1, "point1"), _opcional_xy(point2, "point2")

    def crear(b):
        c1, c2 = _curva(b, entity1, que="entity1"), _curva(b, entity2, que="entity2")
        if entity1 == entity2:
            raise ErrorBoceto("Elegí dos curvas distintas.")
        e1, e2 = c1.extremos(), c2.extremos()
        if not e1 or not e2 or isinstance(c1, Texto) or isinstance(c2, Texto):
            raise ErrorBoceto("La curva de fusión une extremos de curvas abiertas (no círculos, elipses ni textos).")
        a, c = min(((a, c) for a in e1 for c in e2), key=lambda par: math.dist(b.coords(par[0]), b.coords(par[1])))
        b.curva_fusion(entity1, p1 or b.coords(a), entity2, p2 or b.coords(c), continuity)
    return _dibujar(sesion, sketch, crear, desde_solver=True)


# ---------------------------------------------------------------- modificar: empalme, chaflán, recortar, desfase
@herramienta("sketch_fillet", "boceto",
             "Empalme de boceto (Fusion: Empalme en el boceto): redondea la esquina entre dos curvas (líneas, arcos o "
             "círculos) con un arco tangente; recorta las curvas, agrega las tangencias y la cota de radio. radius "
             "puede ser una expresión con parámetros (queda en la cota). Con point1/point2 se elige qué parte de cada "
             "curva se conserva (útil si se cruzan); sin ellos, la parte más larga.", modifica=True)
def sketch_fillet(sesion, entity1: int, entity2: int, radius: Expr, point1: list[float] | None = None,
                  point2: list[float] | None = None, sketch: str | None = None):
    """
    entity1: id de la primera curva (get_sketch).
    entity2: id de la segunda curva.
    radius: radio del empalme en mm: número o expresión con parámetros.
    point1: [x, y] sobre entity1, del lado que se conserva; vacío = automático.
    point2: [x, y] sobre entity2, del lado que se conserva; vacío = automático.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    expresion, valor = _valor_expr(sesion, radius)
    _cota_valida("radio", valor, "radius")
    p1, p2 = _opcional_xy(point1, "point1"), _opcional_xy(point2, "point2")

    def empalmar(b):
        for k, que in ((entity1, "entity1"), (entity2, "entity2")):
            _curva(b, k, ("linea", "arco", "circulo"), que)
        if entity1 == entity2:
            raise ErrorBoceto("Elegí dos curvas distintas.")
        b.empalme(entity1, entity2, valor, p1, p2, expresion)
    return _dibujar(sesion, sketch, empalmar, desde_solver=True)


@herramienta("sketch_chamfer", "boceto",
             "Chaflán de boceto (Fusion: Chaflán en el boceto) entre dos líneas: de distancias iguales (distance), de "
             "dos distancias (distance y distance2) o de distancia y ángulo (distance y angle). Recorta las líneas, "
             "agrega la línea del chaflán y sus cotas (las distancias pueden ser expresiones con parámetros).",
             modifica=True)
def sketch_chamfer(sesion, line1: int, line2: int, distance: Expr, distance2: Expr | None = None,
                   angle: Expr | None = None, point1: list[float] | None = None, point2: list[float] | None = None,
                   sketch: str | None = None):
    """
    line1: id de la primera línea.
    line2: id de la segunda línea.
    distance: distancia del chaflán sobre line1 (y sobre line2 si no hay distance2 ni angle), en mm o expresión.
    distance2: distancia sobre line2 (chaflán de dos distancias); vacío = igual a distance.
    angle: ángulo en grados del chaflán respecto de line1 (chaflán de distancia y ángulo); no va con distance2.
    point1: [x, y] sobre line1, del lado que se conserva; vacío = automático.
    point2: [x, y] sobre line2, del lado que se conserva; vacío = automático.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    if distance2 is not None and angle is not None:
        raise error("INVALID_ARGUMENTS", "Pasá distance2 (dos distancias) o angle (distancia y ángulo), no los dos.")
    expresion, d1 = _valor_expr(sesion, distance)
    _cota_valida("distancia", d1, "distance")
    expr2, d2 = (None, None) if distance2 is None else _valor_expr(sesion, distance2)
    if d2 is not None:
        _cota_valida("distancia", d2, "distance2")
    ang = None if angle is None else _valor_expr(sesion, angle, ANGULO)[1]
    if ang is not None and not 0 < ang < 180:
        raise error("INVALID_DIMENSION", f"angle tiene que estar entre 0 y 180 grados (llegó {ang:g}).")
    p1, p2 = _opcional_xy(point1, "point1"), _opcional_xy(point2, "point2")

    def chaflan(b):
        for k, que in ((line1, "line1"), (line2, "line2")):
            _curva(b, k, ("linea",), que)
        if line1 == line2:
            raise ErrorBoceto("Elegí dos líneas distintas.")
        previas = set(b.cotas)
        b.chaflan(line1, line2, d1, d2, ang, p1, p2, expresion)
        if expr2 is not None:              # la segunda distancia también guarda su expresión
            nuevas = [k for kid, k in b.cotas.items() if kid not in previas and k.tipo == "distancia"]
            if len(nuevas) == 2:
                nuevas[1].expresion = expr2
    return _dibujar(sesion, sketch, chaflan, desde_solver=True)


@herramienta("trim_sketch_curve", "boceto",
             "Recortar, alargar o partir una curva del boceto (Fusion: Recortar / Alargar / Partir). (x, y) es el "
             "lugar del clic, sobre la curva o cerca: trim quita el tramo de la curva que contiene ese punto, hasta los "
             "cruces más cercanos (si no cruza nada, borra la curva entera); extend lleva el extremo más cercano de una "
             "línea o un arco hasta la próxima curva; break la parte en los cruces más cercanos.", modifica=True)
def trim_sketch_curve(sesion, entity: int, x: float, y: float, mode: Literal["trim", "extend", "break"] = "trim",
                      sketch: str | None = None):
    """
    entity: id de la curva (get_sketch).
    x: x del punto que elige el tramo (mm).
    y: y del punto (mm).
    mode: trim (recortar), extend (alargar) o break (partir).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos(locals())
    hecho = {}

    def modificar(b):
        _curva(b, entity)
        if mode == "trim":
            hecho["queda"] = b.recortar(entity, (x, y))
        elif mode == "extend":
            b.alargar(entity, (x, y))
        else:
            hecho["partes"] = b.partir(entity, (x, y))
    r = _dibujar(sesion, sketch, modificar, desde_solver=True)
    r["mode"] = mode
    if mode == "trim":
        r["deleted"] = hecho["queda"] is None
    if mode == "break":
        r["pieces"] = hecho["partes"]
    return r


@herramienta("offset_sketch_curves", "boceto",
             "Desfase de boceto (Fusion: Desfase): copia paralela de la CADENA de líneas y arcos unida a entity (o de "
             "un círculo), con las esquinas resueltas, la restricción de desfase y su cota (paramétrico: si la cadena "
             "cambia, el desfase la sigue). Por defecto una cadena cerrada crece hacia afuera y una abierta va a la "
             "izquierda de su recorrido; distance negativa va al otro lado, y side_x/side_y eligen el lado con un "
             "punto. Para letras, splines o cualquier contorno (sin parámetros) está offset_profiles.", modifica=True)
def offset_sketch_curves(sesion, entity: int, distance: Expr, side_x: float | None = None,
                         side_y: float | None = None, sketch: str | None = None):
    """
    entity: id de una curva de la cadena (línea o arco) o de un círculo.
    distance: separación en mm, número o expresión con parámetros; negativa = al lado contrario.
    side_x: x de un punto del lado donde va el desfase; vacío = el lado por defecto.
    side_y: y de ese punto.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos(locals())
    if (side_x is None) != (side_y is None):
        raise error("INVALID_ARGUMENTS", "Pasá side_x y side_y juntos, o ninguno de los dos.")
    expresion, valor = _valor_expr(sesion, distance)
    if valor < 0:
        expresion = f"-({expresion})" if isinstance(distance, str) else repr(abs(valor))
    _cota_valida("desfase", abs(valor), "distance")
    lado = None if side_x is None else (float(side_x), float(side_y))

    def desfasar(b):
        _curva(b, entity, ("linea", "arco", "circulo"))
        b.desfase(entity, abs(valor), lado, expresion, invertir=valor < 0)
    return _dibujar(sesion, sketch, desfasar, desde_solver=True)


# ---------------------------------------------------------------- crear: simetría y patrones
def _exigir_seleccion(b, entities):
    if not entities:
        raise error("INVALID_ARGUMENTS", "entities está vacía: pasá ids de curvas o puntos (get_sketch).")
    _exigir_entidades(b, entities)


@herramienta("mirror_sketch", "boceto",
             "Simetría de boceto (Fusion: Simetría): copia espejada de curvas y puntos respecto de una línea del "
             "boceto, con restricciones de simetría (si la geometría original cambia, la copia la sigue). Lo que está "
             "sobre el eje se comparte. Los textos no se espejan (para eso: transform_sketch o edit_text).",
             modifica=True)
def mirror_sketch(sesion, entities: list[int], axis: int, sketch: str | None = None):
    """
    entities: ids de las curvas o puntos a reflejar (get_sketch).
    axis: id de la línea de simetría (puede ser de construcción).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    textos = []

    def reflejar(b):
        _exigir_seleccion(b, entities)
        _curva(b, axis, ("linea",), "el eje")
        textos.extend(i for i in entities if isinstance(b.curvas.get(i), Texto))
        b.simetria(list(entities), axis)
    r = _dibujar(sesion, sketch, reflejar, desde_solver=True)
    if textos:
        sesion.avisar(f"Los textos {textos} no se espejan con simetría: usá transform_sketch o edit_text (flip_h).")
    return r


# Cada copia queda atada al original (restricción de patrón) y el solver resuelve todo junto: medido, 200 círculos
# copiados (200 puntos) tardan 3,6 s y 99 rectángulos (396 puntos) 7,5 s, y eso se repite en cada edición del boceto.
MAX_COPIAS_PATRON = 200
MAX_PUNTOS_PATRON = 200      # copias × puntos de la selección


def _exigir_cantidad(n, que):
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser un entero de 1 en adelante (llegó {n!r}).")


def _exigir_tamano_patron(b, entities, copias, sin=()):
    puntos = len([p for p in b.puntos_de(entities) if p not in sin])
    if copias * puntos > MAX_PUNTOS_PATRON:
        raise error("INVALID_ARGUMENTS", f"El patrón copiaría {copias * puntos} puntos ({copias} copias × {puntos}): un "
                    f"patrón de boceto admite hasta {MAX_PUNTOS_PATRON}, porque cada copia queda atada al original y "
                    "el boceto se vuelve lento.", "Para más copias, patroná el cuerpo (rectangular_pattern o "
                    "circular_pattern) o la operación.")


@herramienta("sketch_rectangular_pattern", "boceto",
             "Patrón rectangular de boceto (Fusion: Patrón rectangular en el boceto): copias de curvas y puntos en una "
             "o dos direcciones, atadas al original con la restricción de patrón (si el original cambia, las copias lo "
             "siguen). La dirección 1 sale del ángulo angle y la 2 es perpendicular (+90°). Con spacing=extent la "
             "distancia es la total (de la primera a la última copia); con spacing la de cada paso. Tope: 200 puntos "
             "copiados (copias × puntos de la selección; un rectángulo tiene 4), para que el boceto no se vuelva lento.",
             modifica=True)
def sketch_rectangular_pattern(sesion, entities: list[int], count1: int, distance1: float, count2: int = 1,
                               distance2: float = 0.0, angle: float = 0.0,
                               spacing: Literal["extent", "spacing"] = "extent", symmetric: bool = False,
                               sketch: str | None = None):
    """
    entities: ids de las curvas o puntos a repetir (get_sketch).
    count1: cantidad en la dirección 1, contando el original.
    distance1: distancia en la dirección 1 (mm; total o por paso según spacing; negativa = sentido contrario).
    count2: cantidad en la dirección 2 (1 = una sola fila).
    distance2: distancia en la dirección 2 (mm).
    angle: dirección 1 en grados respecto del eje x del boceto; la dirección 2 queda a +90°.
    spacing: extent (distancia total) o spacing (distancia entre copias).
    symmetric: true para repartir las copias a los dos lados del original.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos(locals())
    _exigir_cantidad(count1, "count1")
    _exigir_cantidad(count2, "count2")
    if count1 * count2 < 2:
        raise error("INVALID_ARGUMENTS", "El patrón necesita al menos dos ejemplares (count1 × count2 ≥ 2).")
    if count1 * count2 - 1 > MAX_COPIAS_PATRON:
        raise error("INVALID_ARGUMENTS", f"Un patrón de boceto admite hasta {MAX_COPIAS_PATRON} copias (pidió "
                    f"{count1 * count2 - 1}): para más, usá un patrón de cuerpos (rectangular_pattern).")
    a = math.radians(angle)
    d1, d2 = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    modo = "extension" if spacing == "extent" else "espaciado"

    def repetir(b):
        _exigir_seleccion(b, entities)
        _exigir_tamano_patron(b, entities, count1 * count2 - 1)
        b.patron_rectangular(list(entities), count1, distance1, count2, distance2, d1, d2, modo, symmetric)
    return _dibujar(sesion, sketch, repetir, desde_solver=True)


@herramienta("sketch_circular_pattern", "boceto",
             "Patrón circular de boceto (Fusion: Patrón circular en el boceto): copias de curvas y puntos alrededor de "
             "un centro, atadas al original con la restricción de patrón. total_angle = 360 reparte la cantidad en la "
             "vuelta entera; otro ángulo pone la primera y la última copia en sus extremos. Tope: 200 puntos copiados "
             "(copias × puntos de la selección; un círculo tiene 1).",
             modifica=True)
def sketch_circular_pattern(sesion, entities: list[int], count: int, center_x: float = 0.0, center_y: float = 0.0,
                            center_point: int | None = None, total_angle: float = 360.0, symmetric: bool = False,
                            sketch: str | None = None):
    """
    entities: ids de las curvas o puntos a repetir (get_sketch).
    count: cantidad total, contando el original (2 o más).
    center_x: x del centro (mm), si no se da center_point.
    center_y: y del centro (mm).
    center_point: id de un punto del boceto que hace de centro (las copias lo siguen); pisa center_x/center_y.
    total_angle: ángulo total en grados (360 = vuelta entera; negativo = sentido horario).
    symmetric: true para repartir las copias a los dos lados del original (si total_angle no es 360).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos(locals())
    _exigir_cantidad(count, "count")
    if count < 2:
        raise error("INVALID_ARGUMENTS", "El patrón circular necesita al menos 2 ejemplares (count ≥ 2).")
    if count - 1 > MAX_COPIAS_PATRON:
        raise error("INVALID_ARGUMENTS", f"Un patrón de boceto admite hasta {MAX_COPIAS_PATRON} copias (pidió "
                    f"{count - 1}): para más, usá un patrón de cuerpos (circular_pattern).")
    if not 0 < abs(total_angle) <= 360:
        raise error("INVALID_ARGUMENTS", "total_angle va de -360 a 360 grados, distinto de cero.")

    def repetir(b):
        _exigir_seleccion(b, entities)
        if center_point is not None and center_point not in b.puntos:
            raise error("ENTITY_NOT_FOUND", f"center_point {center_point} no es un punto del boceto.")
        centro = center_point if center_point is not None else (float(center_x), float(center_y))
        _exigir_tamano_patron(b, entities, count - 1, sin=(center_point,))
        b.patron_circular(list(entities), centro, count, total_angle, symmetric)
    return _dibujar(sesion, sketch, repetir, desde_solver=True)


# ---------------------------------------------------------------- proyectar, tipo de línea, cotas y AutoConstrain
@herramienta("project_to_sketch", "boceto",
             "Proyecta aristas, caras o cuerpos del modelo sobre el plano del boceto (Fusion: Proyectar) o agrega donde "
             "cortan ese plano (mode=intersect; Fusion: Intersecar). La geometría queda proyectada: fija (violeta en "
             "la interfaz), sirve para restricciones, cotas y perfiles, y NO sigue al modelo si después cambia. "
             "edges y faces aceptan selectores (con body si hay varios cuerpos) o ids de find_edges / find_faces.",
             modifica=True)
def project_to_sketch(sesion, edges: list[str] | str | None = None, faces: list[str] | str | None = None,
                      bodies: list[str] | None = None, mode: Literal["project", "intersect"] = "project",
                      body: str | None = None, sketch: str | None = None):
    """
    edges: aristas a proyectar: selector ('|Z', '%CIRCLE and >Z') o ids ('Cuerpo1/E3'); vacío = ninguna.
    faces: caras a proyectar (su contorno): selector o ids ('Cuerpo1/F6'); vacío = ninguna.
    bodies: ids o nombres de cuerpos enteros; vacío = ninguno.
    mode: project (proyección ortogonal) o intersect (corte con el plano del boceto).
    body: cuerpo donde se evalúan los selectores de edges y faces; vacío = el único cuerpo.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    from ..nucleo.perfiles import intersecar_forma, proyectar_forma
    op, br = boceto_activo(sesion, sketch)
    formas = [e.sub for _c, e in sl.elegir(sesion, edges, "arista", body, permitir_vacio=True)]
    formas += [e.sub for _c, e in sl.elegir(sesion, faces, "cara", body, permitir_vacio=True)]
    for ref in bodies or []:
        c = sesion.cuerpo(ref)
        if getattr(c, "tipo", "solido") == "malla":
            raise error("UNSUPPORTED_BODY_TYPE", f"«{sesion.nombre_cuerpo(c)}» es una malla: no se proyecta.")
        formas.append(c.forma)
    if not formas:
        raise error("INVALID_ARGUMENTS", "Elegí qué proyectar: edges, faces o bodies.")
    funcion = intersecar_forma if mode == "intersect" else proyectar_forma
    prims, puntos = [], []
    for f in formas:
        p, q = funcion(f, br.plano)
        prims += p
        puntos += q
    if not prims and not puntos:
        raise error("INVALID_GEOMETRY", "Eso no deja nada sobre el plano del boceto"
                    + (": no corta su plano." if mode == "intersect" else "."))
    r = _dibujar(sesion, op.id, lambda b: b.agregar_proyeccion(prims, puntos), desde_solver=True)
    r["mode"] = mode
    return r


@herramienta("set_line_type", "boceto",
             "Cambia el tipo de línea de curvas del boceto (Fusion: Construcción / Línea central de la paleta): normal "
             "(forma perfiles), construction (de construcción: guía, no forma perfiles) o centerline (eje: forma "
             "perfiles y sirve de eje de revolución).", modifica=True)
def set_line_type(sesion, entities: list[int], line_type: Literal["normal", "construction", "centerline"],
                  sketch: str | None = None):
    """
    entities: ids de las curvas (get_sketch).
    line_type: normal, construction o centerline (centerline solo en curvas que no son texto).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    def cambiar(b):
        if not entities:
            raise error("INVALID_ARGUMENTS", "entities está vacía: pasá ids de curvas (get_sketch).")
        for i in entities:
            c = _curva(b, i)
            if line_type == "centerline" and isinstance(c, Texto):
                raise ErrorBoceto(f"La entidad {i} es un texto: no puede ser línea central.")
        for i in entities:
            c = b.curvas[i]
            c.construccion = line_type == "construction"
            c.eje = line_type == "centerline"
    r = _dibujar(sesion, sketch, cambiar)
    r["line_type"] = line_type
    return r


@herramienta("edit_dimension", "boceto",
             "Cambia el valor de una cota que ya existe (Fusion: doble clic en la cota): número o expresión con "
             "parámetros. La geometría se mueve para cumplirla. Si choca con las otras restricciones y cotas, falla y "
             "el boceto queda como estaba. Para borrar una cota o una restricción: delete_sketch_entities con su id.",
             modifica=True)
def edit_dimension(sesion, dimension: int, value: Expr, sketch: str | None = None):
    """
    dimension: id de la cota (get_sketch la lista en dimensions).
    value: valor nuevo: número (mm; grados en una cota de ángulo) o expresión con parámetros ("ancho / 2").
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    op, br = boceto_activo(sesion, sketch)
    nueva = op.copia()
    k = nueva.boceto.cotas.get(dimension) if isinstance(dimension, int) and not isinstance(dimension, bool) else None
    if k is None:
        hay = ", ".join(str(i) for i in nueva.boceto.cotas) or "ninguna"
        raise error("ENTITY_NOT_FOUND", f"El boceto «{op.nombre}» ({op.id}) no tiene la cota {dimension!r} (cotas: "
                    f"{hay}).", "get_sketch lista las cotas (dimensions) con su id.")
    tipo = _COTA_A_INGLES.get(k.tipo, k.tipo)
    expresion, valor = _valor_expr(sesion, value, ANGULO if k.tipo == "angulo" else LONGITUD)
    _cota_valida(k.tipo, valor, f"La cota {dimension} ({tipo})")
    if k.tipo == "angulo" and not 0 < valor < 180:
        raise error("INVALID_DIMENSION", f"Una cota de ángulo va entre 0 y 180 grados (llegó {valor:g}).")
    anterior = k.expresion
    k.expresion = expresion
    sesion.doc.reemplazar(op.id, nueva)
    _exigir_sin_conflicto(sesion, nueva, br.solver.ok, f"La cota {dimension} ({tipo}) = {expresion}")
    estado, gdl = estado_solver(boceto_resuelto(sesion, nueva))
    return {"sketch": _paso(nueva), "dimension": {"id": dimension, "type": tipo, "entities": list(k.entidades),
                                                  "previous_expression": anterior, "expression": expresion,
                                                  "value": _valor_cota(sesion, k)},
            "dof": gdl, "status": estado}


@herramienta("auto_constrain", "boceto",
             "Restringe automáticamente el boceto (Fusion: Restringir automáticamente): agrega coincidencias, "
             "horizontales, verticales e igualdades que ya se cumplen y después cotas (largos, radios, ángulos y "
             "posiciones desde un punto fijo en el origen) con las medidas actuales, hasta dejarlo totalmente "
             "restringido si se puede. Cada agregado se prueba solo: nada entra en conflicto. Las cotas quedan como "
             "números (cambialas con edit_dimension).", modifica=True)
def auto_constrain(sesion, sketch: str | None = None):
    """
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    op, _br = boceto_activo(sesion, sketch)
    valores = valores_cotas(sesion, op.boceto)
    agregado = []
    r = _dibujar(sesion, op.id, lambda b: agregado.extend(auto_restringir(b, valores)), desde_solver=True)
    r["added"] = agregado
    return r
