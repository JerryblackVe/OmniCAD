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

import numpy as np

from ..nucleo import fuentes
from ..nucleo import geometria as geo
from ..nucleo import perfiles as perfiles_mod
from ..restricciones import (TIPOS_AUTO, Boceto, ErrorBoceto, auto_restringir, resolver,
                             sugerir_auto_restricciones)
from ..restricciones.boceto import (MEDIDA_MAXIMA, MEDIDA_MINIMA, ArcoElipse, Circulo, Elipse, Texto,
                                    agregar_arco_tangente, agregar_circulo_puntos, agregar_linea_medio, agregar_poligono,
                                    agregar_rectangulo_3p, agregar_rectangulo_centro,
                                    aviso_radio_empalme, aviso_tangencias_fuera, expresion_sin_signo, _medidas_marco, centro_arco_tangente,
                                    centro_poligono_arista, evaluar_primitiva, mas_cercano, peine_curvatura,
                                    validar_lados_poligono, validar_valor_cota)
from ..restricciones.solver import (acomodar_tangente, restricciones_en_conflicto, restricciones_redundantes,
                                     restriccion_quita_grados)
from ..timeline import entidades as ent
from ..timeline.operaciones import OpBoceto, OpPlano
from ..timeline.parametros import (ANGULO, LONGITUD, TEXTO, ErrorExpresion, TablaParametros, evaluar,
                                   validar_nombre)
from . import selectores as sl
from .errores import ErrorAPI, error
from .registro import Expr, herramienta

PLANOS_ORIGEN = ("XY", "XZ", "YZ")
_ENTIDADES = {"linea": "line", "circulo": "circle", "arco": "arc", "elipse": "ellipse", "arco_elipse": "elliptical_arc",
              "spline": "spline", "conica": "conic", "texto": "text"}
RESTRICCIONES = {"coincident": "coincidente", "horizontal": "horizontal", "vertical": "vertical",
                 "parallel": "paralela", "perpendicular": "perpendicular", "equal": "igual", "tangent": "tangente",
                 "concentric": "concentrica", "midpoint": "punto_medio", "fix": "fijo", "collinear": "colineal",
                 "symmetry": "simetrica", "curvature": "curvatura", "polygon": "poligono"}
COTAS = {"distance": "distancia", "horizontal": "distancia_h", "vertical": "distancia_v", "radius": "radio",
         "diameter": "diametro", "angle": "angulo", "offset": "desfase"}
_RESTRICCION_A_INGLES = {v: k for k, v in RESTRICCIONES.items()} | {"poligono": "polygon", "desfase": "offset",
                                                                     "patron": "pattern"}
_COTA_A_INGLES = {v: k for k, v in COTAS.items()}


def _r(x):
    return round(float(x), 4) + 0.0


def texto_expr(valor):
    """Número (mm o grados) o expresión de texto → texto de expresión del timeline."""
    return valor.strip() if isinstance(valor, str) else repr(float(valor) + 0.0)         # + 0.0: el −0.0 sale «0.0»


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


def referencia_plano_o_cara(sesion, plane, body=None):
    """Referencia de entidad de un plano para una operación: «XY»/«XZ»/«YZ» o un plano de construcción (id o nombre)
    → {"tipo": "plano", "id": …}; una cara plana (selector como '>Z' o id 'Cuerpo1/F6', evaluado sobre `body` o el único
    cuerpo) → su referencia persistente (la operación sigue a la cara en cada recálculo)."""
    try:
        return {"tipo": "plano", "id": referencia_plano(sesion, plane)}
    except ErrorAPI as e:
        if e.error_kind != "PLANE_NOT_FOUND" or not (sl.es_id(plane) or sl.parece_selector(plane)):
            raise
    cuerpo, elem = sl.elegir_uno(sesion, plane, "cara", body)
    return sl.referencia(cuerpo, elem)


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


def op_boceto(sesion, ref=None, derivados=False):
    """`OpBoceto` por id o nombre; sin `ref`, el último boceto activo del timeline. Con `derivados` también los pasos
    que generan un boceto fijo (`BOCETO_DERIVADO`, p. ej. el desfase de aristas): sirven para leer perfiles, no para
    dibujar en ellos. También admite los ids compuestos de bocetos de una derivación externa."""
    doc = sesion.doc
    es_boceto = lambda o: isinstance(o, OpBoceto) or (derivados and getattr(o, "BOCETO_DERIVADO", False))  # noqa: E731
    if ref is None or not str(ref).strip():
        activos = [o for o in doc.operaciones[:doc.marcador] if es_boceto(o)]
        if not activos:
            raise error("SKETCH_NOT_FOUND", "El documento todavía no tiene ningún boceto.")
        return activos[-1]
    ref = str(ref).strip()
    if "." in ref and ref in doc.estado_final.bocetos:
        br = doc.estado_final.bocetos[ref]
        if not derivados:
            raise error("INVALID_ARGUMENTS", f"El boceto «{br.nombre}» ({ref}) es derivado y de solo lectura: "
                        "no se puede dibujar ni editar en él.")
        # Vista de lectura: este boceto resuelto no tiene un paso propio en el timeline.
        return OpBoceto(ref, br.nombre, boceto=br.boceto, plano=None, marco=br.plano.marco())
    bocetos = [o for o in doc.operaciones if es_boceto(o)]
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


def boceto_activo(sesion, ref=None, derivados=True):
    """(op, resuelto) o error SKETCH_NOT_FOUND si el boceto está suprimido, con error o después del marcador. Con
    `derivados=False` (las herramientas que escriben en el boceto) no vale un boceto fijo como el desfase de aristas."""
    op = op_boceto(sesion, ref, derivados=derivados)
    br = boceto_resuelto(sesion, op)
    if br is None:
        estado = next((r.estado for o, r in zip(sesion.doc.operaciones, sesion.doc.resultados, strict=False)
                       if o.id == op.id), "")
        raise error("SKETCH_NOT_FOUND", f"El boceto «{op.nombre}» ({op.id}) no está disponible ahora (estado: "
                    f"{estado or 'desconocido'}): puede estar suprimido, con error o después del marcador.")
    return op, br


def _letras(br, op, cual):
    """Perfiles de las letras de los textos del boceto (de todos, o del de id `cual`)."""
    textos = [c.id for c in br.boceto.curvas.values() if c.tipo == "texto"]
    if cual:
        if not cual.isdigit() or int(cual) not in textos:
            raise error("PROFILE_NOT_FOUND", f"El boceto «{op.nombre}» ({op.id}) no tiene el texto {cual!r}: sus "
                        f"textos son {textos or 'ninguno'} (ids de get_sketch).")
        textos = [int(cual)]
    if not textos:
        raise error("PROFILE_NOT_FOUND", f"El boceto «{op.nombre}» ({op.id}) no tiene textos.")
    letras = perfiles_mod.letras_de_texto(br.perfiles, textos)
    if not letras:
        raise error("PROFILE_NOT_FOUND", f"Los textos {textos} del boceto «{op.nombre}» no forman perfiles cerrados.")
    return letras


def seleccionar_perfiles(br, op, profile):
    """Índice, lista de índices, 'all', 'largest', 'text' (las letras de todos los textos, sin los huecos de la «o»),
    'text:<id>' (las de un texto) o 'sketch' (todo el boceto sin esos huecos, como elegirlo en el navegador) → lista de
    perfiles del boceto. Errores PROFILE_*."""
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
        if clave == "text" or clave.startswith("text:"):
            return _letras(br, op, clave[5:].strip())
        if clave == "sketch":
            return perfiles_mod.perfiles_de_boceto(br)
        if clave.startswith("object:"):
            from ..restricciones import objetos
            try:
                oid = int(clave.partition(":")[2])
                if oid not in br.boceto.objetos:
                    raise ValueError
                ids = set(objetos.curvas(br.boceto, [oid]))
            except ValueError:
                raise error("PROFILE_NOT_FOUND", "El objeto vectorial indicado no existe en ese boceto.") from None
            return [p for p in perfiles_mod.sin_huecos(perfiles, br.boceto) if p.firma and p.firma <= ids]
        if clave.lstrip("-").isdigit():
            profile = int(clave)
        else:
            raise error("PROFILE_NOT_FOUND", f"Selección de perfil desconocida: '{profile}'.",
                        "Usá un índice, una lista de índices, 'all', 'largest', 'text', 'text:<id>' o 'sketch'.")
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


def _extremo_de_linea(b, x, y):
    """El punto de un extremo de línea ya dibujado en (x, y), o (x, y) si no hay: así las líneas seguidas comparten
    la esquina, como al dibujar en cadena (dos puntos sueltos superpuestos abren el perfil al mover uno)."""
    for c in b.curvas.values():
        if c.tipo == "linea" and c.id > 0:
            for pid in (c.p1, c.p2):
                if abs(b.puntos[pid].x - x) < 1e-9 and abs(b.puntos[pid].y - y) < 1e-9:
                    return pid
    return (x, y)


def _linea(b, x1, y1, x2, y2, construccion=False, encadenar=False):
    if math.hypot(x2 - x1, y2 - y1) < 1e-9:
        raise ErrorBoceto("Una línea necesita dos puntos distintos.")
    a, z = ((_extremo_de_linea(b, x1, y1), _extremo_de_linea(b, x2, y2)) if encadenar else ((x1, y1), (x2, y2)))
    lid = b.agregar_linea(a, z, construccion)
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


def _inicio_tangente(b, curva, inicio, extremo=None):
    """Punto compartido y dirección de salida; una elipse cerrada recibe un punto sobre su curva."""
    c = _curva(b, curva, ("linea", "arco", "elipse", "arco_elipse", "spline", "conica"), "tangent_to")
    ext = c.extremos()
    if ext:
        pid = min(ext, key=lambda p: math.dist(b.coords(p), inicio)) if extremo is None else ext[extremo == "end"]
        if math.dist(b.coords(pid), inicio) > 1e-7:
            raise ErrorBoceto("El inicio debe coincidir con el extremo indicado de la curva tangente.")
        _p, direccion = b._salida_extremo(curva, pid)
    elif isinstance(c, Elipse):
        prim = b.primitivas(curva)[0]
        t, distancia, p = mas_cercano(prim, inicio)
        if distancia > 1e-7:
            raise ErrorBoceto("El inicio debe estar sobre la elipse tangente.")
        direccion = evaluar_primitiva(prim, t, 1)[1]
        pid = b.agregar_punto(*p)
        b.agregar_restriccion("coincidente", [pid, curva])
    else:
        raise ErrorBoceto("La curva tangente debe tener extremos: la spline cerrada no los tiene.")
    n = math.hypot(*direccion)
    if n < 1e-9:
        raise ErrorBoceto("La curva no tiene una tangente definida en ese extremo.")
    return pid, (direccion[0] / n, direccion[1] / n)


def _arco_tangente(b, curva, inicio, fin, construccion=False, radio=None, barrido=None):
    """Arco tangente a otra curva; comparte el extremo y guarda la tangencia."""
    pid, direccion = _inicio_tangente(b, curva, inicio)
    geometria = None
    if radio is None:
        p = b.coords(pid)
        otro = (p[0] - direccion[0], p[1] - direccion[1])
        geometria = centro_arco_tangente(p, otro, fin)
        if geometria is None:
            raise ErrorBoceto("El final no puede coincidir con el inicio ni estar sobre la recta tangente.")
    aid, destino = agregar_arco_tangente(b, curva, pid, fin, geometria, construccion,
                                        radio=radio, barrido=barrido, direccion=direccion)
    arco = b.curvas[aid]
    return {"": aid, "center": arco.centro, "start": pid, "end": destino}


def _circulo_tangente(b, lineas, x=None, y=None, radio=None, construccion=False):
    """Círculo de dos o tres tangentes, compartido por dibujo y especificación."""
    if len(lineas) not in (2, 3):
        raise error("INVALID_ARGUMENTS", f"lines lleva 2 o 3 ids de líneas (llegaron {len(lineas)}).")
    if (x is None) != (y is None):
        raise error("INVALID_ARGUMENTS", "Pasá x e y juntos, o ninguno de los dos.")
    if radio is not None and (len(lineas) == 3 or not radio > 0):
        raise error("INVALID_ARGUMENTS", "radius va solo con 2 líneas y tiene que ser positivo.")
    q = None if x is None else (float(x), float(y))
    for k in lineas:
        _curva(b, k, ("linea",), "la línea")
    if len(set(lineas)) != len(lineas):
        raise ErrorBoceto("Elegí líneas distintas.")
    if len(lineas) == 2:
        medios = [tuple((u + v) / 2 for u, v in zip(*b._extremos_linea(k), strict=True)) for k in lineas]
        ubicacion = q or ((medios[0][0] + medios[1][0]) / 2, (medios[0][1] + medios[1][1]) / 2)
        cid = b.agregar_circulo_tangente(list(lineas), ubicacion, radio, None, construccion)
    else:
        cid = b.agregar_circulo_tangente(list(lineas), None, None, None if q is None else [q] * 3, construccion)
    return {"": cid, "center": b.curvas[cid].centro}


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
    validar_lados_poligono(lados)
    if radio <= 1e-9:
        raise ErrorBoceto("El radio del polígono tiene que ser positivo.")
    if acotar:
        validar_valor_cota("radio", radio)
    centro_pid = None
    if acotar and math.hypot(cx, cy) < 1e-9:
        centro_pid = _origen_fijo(b)                            # el centro ES el origen fijo
    ls, cid = agregar_poligono(b, (cx, cy), radio, lados, math.radians(giro), circunscrito, construccion, centro_pid)
    verts = [b.curvas[ln].p1 for ln in ls]
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


def _poligono_arista(b, lados, puntos, construccion=False, acotar=False):
    """Polígono por arista A→B y punto del lado elegido, como create_polygon."""
    if len(puntos) != 3:
        raise ErrorBoceto("kind=edge necesita tres edge_points: A, B y un punto del lado hacia donde crece.")
    a, z, lado = (_xy(q, "Cada punto de edge_points") for q in puntos)
    largo = math.dist(a, z)
    if largo < 1e-9:
        raise ErrorBoceto("El lado del polígono no puede medir cero.")
    cx, cy = centro_poligono_arista(a, z, lado, lados)
    radio = math.dist((cx, cy), a)
    giro = math.degrees(math.atan2(a[1] - cy, a[0] - cx))
    return _poligono(b, lados, radio, cx, cy, giro, False, construccion, acotar)


def _spline(b, puntos, tipo, grado, cerrada, construccion=False, tangente=None, extremo="end"):
    pts = [_xy(p, "Cada punto de la spline") for p in puntos]
    control = tipo == "control_points"
    if control and grado not in (3, 5):
        raise ErrorBoceto(f"Una spline de puntos de control tiene grado 3 o 5 (llegó {grado}).")
    if tangente is not None:
        if len(pts) < 2:
            raise ErrorBoceto("La spline necesita al menos dos puntos.")
        pts[0], _direccion = _inicio_tangente(b, tangente, pts[0], extremo)
    # como Fusion, la spline de ajuste es siempre cúbica: su grado se ignora (con 0 o −1 rompía la interpolación)
    sid = b.agregar_spline(pts, "control" if control else "ajuste", grado if control else 3, cerrada,
                           construccion=construccion)
    if tangente is not None:
        b.agregar_restriccion("tangente", [tangente, sid])
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
    cotas = [{"id": k.id, "name": k.nombre, "type": _COTA_A_INGLES.get(k.tipo, k.tipo), "expression": k.expresion}
             for kid, k in b.cotas.items() if kid not in antes["cotas"]]
    if cotas:
        informe["dimensions"] = cotas
    for clave, actuales, salida in (("curvas", b.curvas, "entities_deleted"),
                                   ("restricciones", b.restricciones, "constraints_deleted"),
                                   ("cotas", b.cotas, "dimensions_deleted")):
        borradas = sorted(antes[clave] - set(actuales))
        if borradas:
            informe[salida] = borradas
    return informe


def valores_cotas(sesion, b):
    """{id de cota: valor en mm o grados} con los parámetros actuales (lo que el solver necesita)."""
    valores = sesion.doc.parametros.valores()
    return {k.id: evaluar(k.expresion, ANGULO if k.tipo == "angulo" else LONGITUD, valores)
            for k in b.cotas.values() if not k.referencia}


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


def _marcar_centrales(b, anteriores):
    """Marca las curvas nuevas normales como centrales; conserva las guías de construcción."""
    for cid, c in b.curvas.items():
        if cid not in anteriores and not c.construccion:
            if isinstance(c, Texto):
                raise ErrorBoceto("Un texto no puede ser línea central.")
            c.eje = True


def _nombre_libre(tabla, base):
    nombre, numero = base, 0
    while nombre in tabla:
        numero += 1
        nombre = f"{base}_{numero}"
    return nombre


def ligar_parametro_texto(doc, t, texto):
    """Crea los parámetros automáticos «Text» y «Text height» del texto `t` y lo liga a ellos (Fusion los crea solos).
    La altura que ya era una expresión queda como expresión del parámetro."""
    tabla = TablaParametros.desde_lista(doc.parametros.a_lista())
    nombre = _nombre_libre(tabla, "Text")
    tabla.agregar(nombre, texto, tipo=TEXTO)
    alto = _nombre_libre(tabla, "Text_height")
    tabla.agregar(alto, t.altura_expr or f"{t.altura:.12g} mm")
    doc.aplicar_parametros(tabla)
    t.parametro_texto, t.parametro_altura, t.altura_expr = nombre, alto, alto
    t.texto = texto if "{" in texto else "{" + nombre + "}"


def actualizar_alturas_texto(boceto, resuelto):
    """`op.boceto` guarda la altura de cuando se escribió: la que vale es la que dio el recálculo (`resuelto`, el
    BocetoResuelto del paso; None si el paso no se calculó)."""
    for c in boceto.curvas.values() if resuelto else ():
        if c.tipo == "texto" and c.altura_expr and c.id in resuelto.boceto.curvas:
            c.altura, c.espaciado = resuelto.boceto.curvas[c.id].altura, resuelto.boceto.curvas[c.id].espaciado


def alturas_sueltas(boceto):
    """Textos con una altura escrita a mano: su «Text height» todavía no la tiene."""
    return [t for t in boceto.curvas.values() if t.tipo == "texto" and t.parametro_altura
            and t.altura_expr != t.parametro_altura]


def sincronizar_alturas_texto(doc, boceto):
    """Una altura escrita sobre un texto ligado (barra del texto, edit_text, escalar) pasa a su «Text height». Una
    expresión que cita al propio parámetro no puede: queda en el texto, que igual la calcula."""
    sueltas = alturas_sueltas(boceto)
    if not sueltas:
        return
    tabla = TablaParametros.desde_lista(doc.parametros.a_lista())
    for t in sueltas:
        try:
            tabla.modificar(t.parametro_altura, t.altura_expr)
        except ErrorExpresion:
            continue
        t.altura_expr = t.parametro_altura
    doc.aplicar_parametros(tabla)


def parametros_de_textos(boceto):
    return {t.id: (t.parametro_altura, t.parametro_texto) for t in boceto.curvas.values() if t.tipo == "texto"}


def soltar_parametros_texto(doc, antes, boceto):
    """Fusion, al desglosar: los parámetros automáticos de un texto que ya no está se borran, salvo los que use otro.
    `antes`: lo que dio `parametros_de_textos` antes del cambio."""
    nombres = [n for tid, par in antes.items() if tid not in boceto.curvas for n in par if n]
    if not nombres:
        return
    usados = doc.parametros_usados()
    tabla = TablaParametros.desde_lista(doc.parametros.a_lista())
    for n in nombres:
        if n in tabla and n not in usados:
            try:
                tabla.eliminar(n)
            except ErrorExpresion:
                continue
    if len(tabla) != len(doc.parametros):
        doc.aplicar_parametros(tabla)


def _dibujar(sesion, ref, constructor, desde_solver=False, anclar=False, construccion=False, central=False,
             sin_conflicto: str | None = None):
    """Edita el boceto con `constructor(boceto)` sobre una copia y la reemplaza en el timeline (un paso). Con
    `desde_solver`, la copia parte de la geometría resuelta (ver `_sincronizar_con_solver`).
    `sin_conflicto` nombra la edición que se rechaza si deja en conflicto un boceto antes válido."""
    if construccion and central:
        raise error("INVALID_ARGUMENTS", "construction y centerline no pueden ser true a la vez.")
    op = op_boceto(sesion, ref)
    if sin_conflicto is not None:
        previo = boceto_resuelto(sesion, op)
        previo_ok = previo is not None and previo.solver.ok
    nueva = op.copia()
    b = nueva.boceto
    actualizar_alturas_texto(b, sesion.doc.estado_final.bocetos.get(op.id))
    if desde_solver:
        _sincronizar_con_solver(sesion, op, b)
    antes = _claves(b)
    textos = parametros_de_textos(b)
    try:
        constructor(b)
        if central:
            _marcar_centrales(b, antes["curvas"])
        _exigir_tamano(b, antes)
        if anclar:
            b.anclar_al_origen(set(b.puntos) - antes["puntos"])
    except ErrorBoceto as e:
        raise error("INVALID_GEOMETRY", str(e)) from e
    sincronizar_alturas_texto(sesion.doc, b)
    sesion.doc.reemplazar(op.id, nueva)
    if sin_conflicto is not None:
        _exigir_sin_conflicto(sesion, nueva, previo_ok, sin_conflicto)
    soltar_parametros_texto(sesion.doc, textos, b)
    return _informe_edicion(sesion, nueva, b, antes)


def _exigir_tamano(b, antes=None):
    """ErrorBoceto si un punto o una curva (los nuevos respecto de `antes`; con None, todos) se sale de lo que el
    núcleo calcula bien: coordenadas hasta MEDIDA_MAXIMA del origen y radios de círculo o elipse entre MEDIDA_MINIMA
    y MEDIDA_MAXIMA (mm), como el tope de las cotas."""
    def fuera(v, minimo=0.0):
        return not minimo <= abs(v) <= MEDIDA_MAXIMA
    nuevos = lambda todos, previos: [k for k in todos if antes is None or k not in antes[previos]]  # noqa: E731
    for pid in nuevos(b.puntos, "puntos"):
        if any(fuera(v) for v in b.coords(pid)):
            raise ErrorBoceto(f"El punto {pid} cae fuera del rango del boceto: las coordenadas llegan hasta "
                              f"{MEDIDA_MAXIMA:,.0f} mm (1 km) del origen.".replace(",", "."))
    for cid in nuevos(b.curvas, "curvas"):
        c = b.curvas[cid]
        radios = [c.radio] if isinstance(c, Circulo) else [c.radio_menor] if isinstance(c, (Elipse, ArcoElipse)) else []
        if any(fuera(r, MEDIDA_MINIMA) for r in radios):
            raise ErrorBoceto(f"El radio de la curva {cid} tiene que medir entre {MEDIDA_MINIMA:g} mm y "
                              f"{MEDIDA_MAXIMA:,.0f} mm (1 km).".replace(",", "."))


def _info_plano(plano):
    return {"origin": [_r(c) for c in plano.origen], "u_axis": [_r(c) for c in plano.u],
            "v_axis": [_r(c) for c in plano.v], "normal": [_r(c) for c in plano.normal]}


def _caja_uv(plano, perfil):
    if perfil.caja_uv is not None:                    # el arreglo planar de Rust ya la trae: no hace falta armar la cara (BOC-28)
        x0, y0, x1, y1 = perfil.caja_uv
        return {"min": [_r(x0), _r(y0)], "max": [_r(x1), _r(y1)]}
    caja = geo.caja_envolvente(perfil.cara)
    if not caja:
        return None
    (x0, y0, z0), (x1, y1, z1) = caja
    uv = [plano.a_uv((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    return {"min": [_r(min(p[0] for p in uv)), _r(min(p[1] for p in uv))],
            "max": [_r(max(p[0] for p in uv)), _r(max(p[1] for p in uv))]}


def info_perfiles(br):
    return [{"index": i, "area": _r(p.area), "centroid": [_r(p.centroide_uv[0]), _r(p.centroide_uv[1])],
             "bounding_box": _caja_uv(br.plano, p), "curves": sorted(p.firma)}
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
        d.update(text=c.texto, position=xy(c.punto), font=c.fuente, height=_r(c.altura),
                 height_basis="letter_a" if c.altura_a else "font_size", angle=_r(c.angulo),
                 bold=c.negrita, italic=c.cursiva, letter_spacing=_r(c.espaciado),
                 character_spacing=_r(100 * c.espaciado / max(fuentes.espaciado_cien(c.fuente, c.altura, c.negrita, c.cursiva), 1e-9)),
                 line_spacing=_r(c.interlineado),
                 align={"izq": "left", "centro": "center", "der": "right"}.get(c.alineacion, c.alineacion),
                 anchor={"base": "baseline", "arriba": "top", "medio": "middle", "abajo": "bottom"}.get(
                     c.ancla_v, c.ancla_v), box_width=_r(c.ancho_caja), flip_h=c.voltear_h, flip_v=c.voltear_v,
                 kerning=c.kerning, skew=_r(c.inclinacion), scale_x=_r(c.escala_h), scale_y=_r(c.escala_v),
                 baseline_shift=_r(c.desfase_base),
                 case={"ninguno": "none", "mayusculas": "upper", "minusculas": "lower", "titulo": "title",
                       "versalitas": "small_caps"}.get(c.capitalizacion, c.capitalizacion),
                 underline={"ninguno": "none", "simple": "single", "doble": "double"}.get(c.subrayado, c.subrayado),
                 strikethrough={"ninguno": "none", "simple": "single", "doble": "double"}.get(c.tachado, c.tachado),
                 decoration_thickness=_r(c.grosor_decoracion), no_wrap=c.sin_division,
                 kerning_pairs=[[i, _r(x)] for i, x in c.ajustes_kerning])
        if c.camino is not None:
            d.update(path_entity=c.camino, path_side="left" if c.camino_lado == "izq" else "right",
                     path_placement="above" if c.camino_colocacion == "arriba" else "below",
                     path_position=_r(c.camino_pos), path_aligned=c.camino_alineado,
                     path_offset=_r(c.camino_desfase), fit_path=c.camino_ajustar)
        if c.altura_expr:
            d["height_expression"] = c.altura_expr
        if c.marco:
            ang, ancho, alto = _medidas_marco(*map(b.coords, c.puntos()))
            d["angle"] = _r(math.degrees(ang))
            d["frame"] = {"lines": b._lineas_auxiliares(c), "width": _r(ancho), "height": _r(alto)}
    if c.tipo == "spline" and c.manijas:
        d["handles"] = [{"point": a, "end": e, "angle": _r(math.degrees(math.atan2(ey - fy, ex - fx))),
                         "length": _r(math.hypot(ex - fx, ey - fy)), "curvature": None if k is None else _r(k)}
                        for a, e, k in c.manijas for (fx, fy), (ex, ey) in [(b.coords(a), b.coords(e))]]
    return d


def _valor_cota(sesion, k):
    try:
        valores = sesion.doc.parametros.valores()
        return _r(evaluar(k.nombre if k.referencia and k.nombre else k.expresion,
                         ANGULO if k.tipo == "angulo" else LONGITUD, valores))
    except Exception:  # noqa: BLE001 — informe: un valor ilegible no debe tumbar get_sketch
        return None


def _ubicacion_cota(k, b=None):
    """Dónde dibuja el editor la cota (si se la movió): offset de la línea y del texto, en mm; `mode` (center o
    tangent) en una distancia con un círculo o arco; `quadrant` (0..3) en un ángulo con cuadrante elegido; y, con el
    boceto `b`, `measured_segment` [x1, y1, x2, y2]: la línea de cota que dibuja la ventana en una distancia o un
    desfase que no es la lineal de una línea o dos puntos (BOC-37)."""
    segmento = None if b is None else b.segmento_cota(k)
    return {**{n: k.datos[c] for n, c in (("offset", "desfase"), ("text_offset", "texto"), ("quadrant", "cuadrante"),
                                                   ("position", "ubic"))
               if c in k.datos},
            **({"mode": _MODOS_A_INGLES[k.datos["modo"]]} if "modo" in k.datos else {}),
            **({"measured_segment": [_r(v) for q in segmento for v in q]} if segmento else {})}


def _cuadrante(b, tipo, entities, near):
    """Cuadrante (0..3) de una cota de ángulo según el punto `near` [x, y] (BOC-25); None si no hay `near`."""
    if near is None:
        return None
    if tipo != "angulo":
        raise error("INVALID_DIMENSION", "near solo vale en una cota de ángulo (type=angle).")
    punto = _xy(near, "near")
    try:
        return b.cuadrante_angulo(*entities, punto)
    except ErrorBoceto as e:
        raise error("INVALID_DIMENSION", str(e)) from e


_MODOS = {"center": "centro", "tangent": "tangente"}
_MODOS_A_INGLES = {v: k for k, v in _MODOS.items()}


def _fijar_ubicacion(b, k, offset, text_offset, position=None):
    """Guarda `offset` y `text_offset` (mm) en la cota k; solo las cotas lineales de una línea o de dos puntos.
    `position` [x, y] es lo que hace arrastrar la cota con el ratón (`Boceto.mover_cota`): vale en todas."""
    if position is not None:
        if offset is not None or text_offset is not None:
            raise error("INVALID_ARGUMENTS", "position no se combina con offset ni text_offset.")
        b.mover_cota(k, _xy(position, "position"))
        return
    if offset is None and text_offset is None:
        return
    for nombre, v in (("offset", offset), ("text_offset", text_offset)):
        if v is not None and not _finito(v):
            raise error("INVALID_ARGUMENTS", f"'{nombre}' tiene que ser un número finito (llegó {v!r}).")
    if b.ejes_cota(k) is None:
        raise error("INVALID_DIMENSION", "offset y text_offset solo valen en una cota lineal (distance, horizontal "
                    "o vertical) de una línea o de dos puntos.")
    if offset is not None:
        k.datos["desfase"] = float(offset)
    if text_offset is not None:
        k.datos["texto"] = float(text_offset)


def info_boceto(sesion, op):
    """Informe completo de un boceto (lo que devuelve get_sketch)."""
    br = boceto_resuelto(sesion, op)
    b = br.boceto if br is not None else op.boceto
    estado, gdl = estado_solver(br)
    fijos = b.puntos_fijos()
    determinadas = br.solver.determinadas if br is not None else frozenset()
    fijas = {e for r in b.restricciones.values() if r.tipo == "fijo" for e in r.entidades}
    fijas.update(c.id for c in b.curvas.values() if c.proyectada)
    # Una coincidencia con el origen también es un anclaje, aunque no sea un «fijo» explícito.
    anclados = {b.ORIGEN} | {e for r in b.restricciones.values() if r.datos.get("origen") for e in r.entidades}
    coincidencias = [r.entidades for r in b.restricciones.values() if r.tipo == "coincidente"
                    and all(e in b.puntos for e in r.entidades)]
    while True:
        nuevos = {e for par in coincidencias if anclados.intersection(par) for e in par} - anclados
        if not nuevos:
            break
        anclados.update(nuevos)
    fijos.update(anclados)

    def estado_entidad(ident):
        if ident in fijos or ident in fijas:
            return "fixed"
        return "determined" if ident in determinadas else "free"

    resultado = next((r for o, r in zip(sesion.doc.operaciones, sesion.doc.resultados, strict=False) if o.id == op.id),
                     None)
    info = {"id": op.id, "name": op.nombre, "plane": op.p.get("plano"), "available": br is not None,
            "plane_frame": _info_plano(br.plano) if br is not None else None,
            "status": estado, "dof": gdl, "origin": b.ORIGEN, "axes": {"x": b.EJE_X, "y": b.EJE_Y},
            "conflicts": restricciones_en_conflicto(op.boceto, valores_cotas(sesion, op.boceto))
            if estado == "over_constrained" else [],
            "message": br.solver.descripcion() if br is not None else (resultado.mensaje if resultado else ""),
            "entities": [{**_info_curva(b, c), "state": estado_entidad(c.id)} for c in b.curvas.values()],
            "points": [{"id": p.id, "x": _r(p.x), "y": _r(p.y), "fixed": p.id in fijos,
                        "state": estado_entidad(p.id)} for p in b.puntos.values()],
            "constraints": [{"id": r.id, "type": _RESTRICCION_A_INGLES.get(r.tipo, r.tipo), "entities": r.entidades}
                            for r in b.restricciones.values()],
            "tangents_off_arc": b.tangencias_fuera_del_arco(),
            "dimensions": [{"id": k.id, "name": k.nombre, "type": _COTA_A_INGLES.get(k.tipo, k.tipo), "entities": k.entidades,
                            "expression": k.expresion, "reference": k.referencia,
                            "value": _r(b.medir(k)) if k.referencia else _valor_cota(sesion, k),
                            **_ubicacion_cota(k, b)}
                           for k in b.cotas.values()],
            "profiles": info_perfiles(br) if br is not None else []}
    if b.proyecciones:
        info["projections"] = [{"id": r["id"], "mode": {"silueta": "silhouette"}.get(r["modo"], r["modo"]), "lost": r["id"] in op.perdidas, "entities": r["ids"],
                                "automatic": bool(r.get("auto"))} for r in b.proyecciones]
    if b.patrones:
        info["patterns"] = [{"id": r["id"], "type": "rectangular" if r["tipo"] == "rectangular" else "circular",
                             "entities": r["ids"], "suppressed": r["suprimidos"], "parameters": _parametros_patron(r),
                             "instances": {n: ids for n, ids in r["copias"].items()}} for r in b.patrones]
    if any(b.geo3d.values()):
        from .herramientas_boceto3d import info_3d
        info.update(info_3d(sesion, b, br))
    return info


def _parametros_patron(r):
    """Los parámetros de un patrón con los nombres de las herramientas (los mismos que acepta edit_sketch_pattern)."""
    p = r["params"]
    if r["tipo"] == "circular":
        return {"count": p["cantidad"], "total_angle": _r(p["angulo_total"]), "symmetric": p["simetrico"],
                "center": p["centro"] if isinstance(p["centro"], int) else [_r(c) for c in p["centro"]]}
    angulo = lambda v: _r(math.degrees(math.atan2(v[1], v[0])))  # noqa: E731
    return {"count1": p["cantidad1"], "distance1": _r(p["distancia1"]), "count2": p["cantidad2"],
            "distance2": _r(p["distancia2"]), "spacing": "extent" if p["modo"] == "extension" else "spacing",
            "angle": angulo(p["dir1"]), "angle2": angulo(p["dir2"]), "direction1_line": p.get("linea1"),
            "direction2_line": p.get("linea2"), "symmetric": p["simetrico"],
            "symmetric2": p.get("simetrico2", p["simetrico"])}


# ================================================================ herramientas
_TIPOS_PLANO = {"offset": "desfase", "angle": "angulo", "tangent": "tangente", "middle": "medio",
                "two_edges": "dos_aristas", "three_points": "tres_puntos", "perpendicular": "perpendicular", "path": "ruta"}


@herramienta("create_construction_plane", "boceto",
             "Crea un plano de construcción (CONSTRUIR › Plano). type=offset (por defecto): desfasado de un plano de origen "
             "(XY, XZ, YZ), de otro plano de construcción o de una CARA PLANA (selector o id de find_faces), sobre su "
             "normal; extent=to_object lo lleva hasta un punto. Los demás tipos usan references en orden: angle (un eje o "
             "arista + angle), tangent (una cara curva + angle, y opcional un plano de referencia), middle (dos planos o "
             "caras), two_edges (dos aristas o ejes), three_points (tres puntos), perpendicular (una cara o plano + location, "
             "direction y un Objeto de referencia opcional; también una arista + un punto) y path (una arista, curva, cadena "
             "o eje, con extent proportional, absolute o to_object). extra_offset es el campo Desfase. Sirve para dibujar "
             "bocetos fuera del origen: va en el grupo «boceto» porque su uso típico es create_sketch(plane=<este plano>).",
             modifica=True)
def create_construction_plane(sesion, plane: str = "XY", offset: Expr = "10 mm", name: str | None = None,
                              type: Literal["offset", "angle", "tangent", "middle", "two_edges", "three_points",
                                            "perpendicular", "path"] = "offset",
                              references: list[str | dict | list[float]] | None = None, angle: Expr = 0,
                              position: Expr = 0.5, distance: Expr = 0, body: str | None = None,
                              extent: Literal["distance", "to_object", "proportional", "absolute"] | None = None,
                              object: str | dict | list[float] | None = None, extra_offset: Expr = 0,
                              direction: Literal["U", "V"] = "U", location: list[float] | None = None,
                              tangent_chain: bool = True, resize: Literal["default", "extended"] = "default",
                              size_type: Literal["distance", "to_object"] = "distance", size: Expr = 0,
                              size_object: str | dict | list[float] | None = None):
    """
    plane: type=offset: plano base: "XY", "XZ", "YZ", el id/nombre de otro plano de construcción, o una cara plana (selector ">Z" o id de find_faces).
    offset: type=offset: desfase en mm sobre la normal del plano base (número o expresión con parámetros, p. ej. "alto / 2").
    name: nombre del plano; vacío = "Plano1", "Plano2"…
    type: "offset" (desfase), "angle" (en ángulo), "tangent" (tangente a una cara curva), "middle" (plano medio), "two_edges" (por dos aristas), "three_points" (por tres puntos), "perpendicular" (perpendicular a una curva en un punto) o "path" (en un punto de una ruta).
    references: referencias en orden según type (ver la descripción): planos de origen o de construcción, ejes, caras, aristas, selectores, ids de find_faces / find_edges, puntos de construcción, vértices [x, y, z] o {sketch, point | curve}.
    angle: type=angle o tangent: ángulo en grados (número o expresión).
    position: type=path con extent=proportional: posición sobre la ruta entre 0 (inicio) y 1 (fin).
    distance: type=perpendicular: corre el plano sobre su normal; type=path con extent=absolute o sobre un eje: mm a lo largo de la ruta.
    body: cuerpo donde se evalúan los selectores de references y de plane (cara); vacío = el único cuerpo.
    extent: type=offset: distance o to_object; type=path: proportional (por defecto), absolute o to_object.
    object: punto para extent=to_object (vértice, punto de boceto o de construcción). En una ruta que es un eje, ancla la distancia.
    extra_offset: campo Desfase: corre el plano sobre su normal, en mm; no va con middle ni perpendicular.
    direction: type=perpendicular sobre cara plana o plano: U o V, la dirección de la cara que da la normal del plano.
    location: type=perpendicular sin punto: [x, y, z] del lugar de la cara o plano; vacío = su centro.
    tangent_chain: type=path con una sola curva: suma las curvas que siguen por tangencia.
    resize: Redimensionar: default ajusta el dibujo a lo elegido, extended llena la vista. Solo cambia cómo se ve.
    size_type: Tipo de extensión: distance fija el lado con size; to_object lo lleva hasta size_object.
    size: lado del plano en mm; 0 = el que sale de lo elegido.
    size_object: objeto hasta donde llega el plano, con size_type=to_object.
    """
    from .herramientas_construccion import (_EJE, _PLANO, _PUNTO, _referencia, _referencias, agregar_construccion,
                                            parametros_tamano, referencia_lugar, referencias_ruta)
    doc = sesion.doc
    nombre = name.strip() if name and name.strip() else nombre_nuevo(doc, "Plano", OpPlano)
    validos = {"offset": ("distance", "to_object"), "path": ("proportional", "absolute", "to_object")}.get(type, ())
    if extent is not None and extent not in validos:
        raise error("INVALID_ARGUMENTS", f"extent={extent} no va con type={type}.", f"Con este tipo vale: {', '.join(validos) or 'nada'}.")
    if type in ("middle", "perpendicular") and str(extra_offset) not in ("0", "0.0"):
        raise error("INVALID_ARGUMENTS", f"extra_offset no va con type={type}.")
    if extent == "to_object" and object is None:
        raise error("INVALID_ARGUMENTS", "Con extent=to_object falta object.")
    comunes = dict(desfase=texto_expr(distance if type == "perpendicular" else extra_offset),
                   objeto=None if object is None else _referencia(sesion, object, _PUNTO, body),
                   **parametros_tamano(sesion, resize, size_type, size, size_object, body))
    if type == "offset" and not references:
        try:
            base = referencia_plano(sesion, plane)
        except ErrorAPI as e:                               # una cara plana como base del desfase
            if e.error_kind != "PLANE_NOT_FOUND" or not (sl.es_id(plane) or sl.parece_selector(plane)):
                raise
            base = None
            ref = referencia_plano_o_cara(sesion, plane, body)
        else:
            ref = {"tipo": "plano", "id": base}
        op = OpPlano(doc.nuevo_id(), nombre, tipo="desfase", refs=[ref], distancia=texto_expr(offset),
                     extension="objeto" if extent == "to_object" else "distancia", **comunes)
    else:
        base = None
        refs = list(references or [])
        lugar = None
        if type == "path":
            refs = referencias_ruta(sesion, refs, body, con_eje=True)
        else:
            todos = _PLANO | _EJE | {"cuerpo"}
            filtros = {"offset": [(_PLANO, "plano")], "angle": [(_EJE, "eje")], "tangent": [({"cara"}, None)],
                       "middle": [(_PLANO, "plano")] * 2, "two_edges": [(_EJE, "eje")] * 2,
                       "three_points": [(_PUNTO, None)] * 3, "perpendicular": [(todos, None), (_PUNTO | _PLANO, None)]}[type]
            if type == "tangent" and len(refs) == 2:
                filtros = filtros + [(_PLANO, "plano")]
            if type == "perpendicular" and len(refs) == 1:
                filtros = filtros[:1]
            refs = _referencias(sesion, refs, filtros, body)
            if type == "perpendicular" and len(refs) == 1:
                lugar = referencia_lugar(sesion, refs[0], location)
        op = OpPlano(doc.nuevo_id(), nombre, tipo=_TIPOS_PLANO[type], refs=refs, distancia=texto_expr(distance if type == "path" else offset),
                     angulo=texto_expr(angle), posicion=texto_expr(position), direccion=direction, lugar=lugar,
                     extension="objeto" if extent == "to_object" else "distancia",
                     tipo_distancia={"absolute": "absoluto", "to_object": "objeto"}.get(extent, "proporcional"),
                     cadena_tangente=tangent_chain and type == "path", **comunes)
    if object is not None and extent != "to_object" and not (type == "path" and op.p["refs"][0]["tipo"] == "eje"):
        raise error("INVALID_ARGUMENTS", "object solo va con extent=to_object o en una ruta que es un eje.")
    agregar_construccion(sesion, op)
    plano = doc.estado_final.planos[op.id]
    return {"plane": _paso(op), "base": base, "type": type, "offset": op.p["distancia"], **_info_plano(plano),
            "display": doc.estado_final.medidas[op.id]}


@herramienta("create_sketch", "boceto",
             "Crea un boceto vacío sobre un plano o sobre una cara plana. Coordenadas del boceto (mm): en XY x→X e y→Y "
             "(normal +Z); en XZ x→X e y→Z (normal −Y: una extrusión positiva avanza hacia −Y); en YZ x→Y e y→Z "
             "(normal +X). Un plano de construcción usa el marco de su plano base. SOBRE UNA CARA (plane = selector como "
             "'>Z' o id de find_faces como 'Cuerpo1/F6'; tiene que ser UNA cara plana): el boceto queda sobre la cara con "
             "la normal exterior como normal (extruir con join crece hacia afuera; con cut entra al material solo, como Fusion). Ejes: en "
             "caras horizontales x→+X e y = normal × x (y→+Y con normal +Z; y→−Y con normal −Z, como en Fusion la "
             "vista queda espejada al mirarla desde abajo); en las demás y→+Z (hacia arriba) y x = y × normal; el origen es la proyección del "
             "origen del mundo sobre el plano de la cara, no una esquina (plane_frame lo da y find_faces trae center_uv, "
             "el centro de cada cara en estos ejes). El boceto queda asociado a la cara, como en Fusion: si un parámetro "
             "la mueve o la gira, el boceto la sigue; si la cara desaparece, el paso da error. Con varios cuerpos, body dice en cuál se evalúa "
             "el selector de la cara.",
             modifica=True)
def create_sketch(sesion, plane: str = "XY", name: str | None = None, body: str | None = None,
                  project_edges: bool = False):
    """
    plane: "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana: selector (">Z") o id ("Cuerpo1/F6").
    name: nombre del boceto; vacío = "Boceto1", "Boceto2"…
    body: id o nombre del cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo. No se usa con un plano ni con un id de cara.
    project_edges: true (solo sobre una cara) proyecta sus aristas de forma asociativa, como Fusion al crear el boceto; false la deja vacía.
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
    if project_edges:
        info.update(_proyectar_aristas_de_cara(sesion, op, ref_cara))
    return info


def _proyectar_aristas_de_cara(sesion, op, ref_cara):
    """Proyecta de forma asociativa el contorno de la cara sobre la que está el boceto `op` (Fusion lo hace al crear
    el boceto). Devuelve lo que cambió en el informe: perfiles y cantidad de entidades proyectadas; con un plano, nada."""
    if ref_cara is None:
        sesion.avisar("project_edges solo vale sobre una cara plana: el boceto quedó vacío.")
        return {}
    br = boceto_resuelto(sesion, op)
    prims, puntos = ent.proyectar_entidad(ent.resolver(ref_cara, sesion.doc.estado_final), br.plano)
    r = _dibujar(sesion, op.id, lambda b: b.agregar_proyeccion(
        prims, puntos, origen={"modo": "project", "refs": [ref_cara]}), desde_solver=True)
    return {"profiles": r["profiles"], "projected": len(r["entities"])}


@herramienta("draw_line", "boceto", "Dibuja una línea en el boceto (un paso de deshacer). Coordenadas en mm sobre el "
             "plano del boceto. Con midpoint=true es una línea de punto medio: el primer punto es su punto medio y el "
             "segundo un extremo (el otro es el simétrico) y queda con la restricción de punto medio. Un extremo que "
             "cae sobre el de otra línea comparte su punto (cadena); si no, queda suelto. Devuelve los ids creados "
             "(línea y puntos) y la cantidad de perfiles.", modifica=True)
def draw_line(sesion, start_x: float, start_y: float, end_x: float, end_y: float, sketch: str | None = None,
              construction: bool = False, midpoint: bool = False, centerline: bool = False):
    """
    start_x: x del punto inicial (mm); con midpoint, x del punto medio.
    start_y: y del punto inicial (mm); con midpoint, y del punto medio.
    end_x: x del punto final (mm); con midpoint, x de un extremo.
    end_y: y del punto final (mm); con midpoint, y de un extremo.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una línea de construcción (no forma perfiles).
    midpoint: true dibuja la línea desde su punto medio (start) y un extremo (end), con la restricción de punto medio.
    centerline: true para geometría central (forma perfiles); incompatible con construction=true.
    """
    _exigir_finitos(locals())
    if midpoint:
        def crear(b):
            if math.hypot(end_x - start_x, end_y - start_y) < 1e-9:
                raise ErrorBoceto("Una línea necesita dos puntos distintos.")
            lid = agregar_linea_medio(b, (start_x, start_y), (end_x, end_y), construction)
            ln = b.curvas[lid]
            return {"": lid, "start": ln.p1, "end": ln.p2}
        return _dibujar(sesion, sketch, crear, construccion=construction, central=centerline)
    # un extremo que cae sobre el de otra línea la une (como al dibujar en cadena); si no, la línea queda suelta
    return _dibujar(sesion, sketch, lambda b: _linea(b, start_x, start_y, end_x, end_y, construction, encadenar=True),
                    construccion=construction, central=centerline)


@herramienta("draw_rectangle", "boceto",
             "Dibuja un rectángulo (4 líneas con restricciones horizontal y vertical). Tres formas de darlo: dos esquinas "
             "opuestas (x1, y1, x2, y2); centro y tamaño (center_x, center_y, width, height); o esquina mínima y tamaño "
             "(origin_x, origin_y, width, height). width es el tamaño en x del boceto y height en y. Con "
             "center_diagonals=true, la forma centro y tamaño agrega las dos diagonales de construcción y deja el "
             "centro como punto medio de una (el «Rectángulo central» de la interfaz). Con three_points=[A, B, C] es "
             "el rectángulo de 3 puntos: el lado A→B y un punto C que da el ancho, perpendicular al lado (queda "
             "girado si A→B no es horizontal). Un punto nuevo sobre (0,0) queda anclado al origen, como en la interfaz.", modifica=True)
def draw_rectangle(sesion, x1: float | None = None, y1: float | None = None, x2: float | None = None,
                   y2: float | None = None, center_x: float | None = None, center_y: float | None = None,
                   origin_x: float | None = None, origin_y: float | None = None, width: float | None = None,
                   height: float | None = None, sketch: str | None = None, construction: bool = False,
                   center_diagonals: bool = False, three_points: list[list[float]] | None = None,
                   centerline: bool = False):
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
    center_diagonals: true (con center_x/center_y y tamaño) agrega las diagonales de construcción y el punto central con restricción de punto medio.
    three_points: [[ax, ay], [bx, by], [cx, cy]]: lado A→B y punto C que da el ancho; no se combina con las otras formas.
    centerline: true para geometría central (forma perfiles); incompatible con construction=true.
    """
    _exigir_finitos(locals())
    if three_points is not None:
        if any(v is not None for v in (x1, y1, x2, y2, center_x, center_y, origin_x, origin_y, width, height)):
            raise error("INVALID_ARGUMENTS", "three_points no se combina con las otras formas de rectángulo.")
        if len(three_points) != 3:
            raise error("INVALID_ARGUMENTS", "three_points necesita tres puntos [x, y]: A, B y C.")
        a, b_, c = (_xy(p, "Cada punto de three_points") for p in three_points)
        return _dibujar(sesion, sketch, lambda b: {"": agregar_rectangulo_3p(b, a, b_, c, construction)[0]}, anclar=True,
                        construccion=construction, central=centerline)
    esquinas = (x1, y1, x2, y2)
    if any(v is not None for v in esquinas):
        if any(v is None for v in esquinas):
            raise error("INVALID_ARGUMENTS", "Para la forma de dos esquinas hacen falta x1, y1, x2 e y2.")
        if any(v is not None for v in (center_x, center_y, origin_x, origin_y, width, height)):
            raise error("INVALID_ARGUMENTS", "La forma de dos esquinas (x1, y1, x2, y2) no se combina con "
                        "center_x/center_y, origin_x/origin_y, width ni height.")
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
    if center_diagonals:
        if center_x is None and center_y is None:
            raise error("INVALID_ARGUMENTS", "center_diagonals necesita la forma de centro y tamaño (center_x/center_y, width, height).")
        centro = ((a[0] + b_[0]) / 2, (a[1] + b_[1]) / 2)
        return _dibujar(sesion, sketch, lambda b: {"": agregar_rectangulo_centro(b, centro, b_, construction)[0]}, anclar=True,
                        construccion=construction, central=centerline)
    return _dibujar(sesion, sketch, lambda b: _rectangulo(b, a[0], a[1], b_[0], b_[1], construction), anclar=True,
                    construccion=construction, central=centerline)


@herramienta("draw_circle", "boceto", "Dibuja un círculo (un paso de deshacer): por centro y radio (por defecto), por "
             "2 puntos (los extremos de un diámetro) o por 3 puntos (points). Un círculo cerrado forma un perfil; "
             "dentro de un rectángulo da dos perfiles (el anillo y el disco).", modifica=True)
def draw_circle(sesion, radius: float | None = None, center_x: float = 0.0, center_y: float = 0.0,
                sketch: str | None = None, construction: bool = False,
                kind: Literal["center_radius", "two_points", "three_points"] = "center_radius",
                points: list[list[float]] | None = None, centerline: bool = False):
    """
    radius: radio en mm (positivo); obligatorio con kind=center_radius.
    center_x: x del centro (mm); solo con kind=center_radius.
    center_y: y del centro (mm); solo con kind=center_radius.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un círculo de construcción (no forma perfiles).
    kind: "center_radius" (centro y radio), "two_points" (extremos de un diámetro) o "three_points" (pasa por tres puntos).
    points: [[x, y], …] con dos puntos (two_points) o tres (three_points), en mm sobre el plano del boceto.
    centerline: true para geometría central (forma perfiles); incompatible con construction=true.
    """
    _exigir_finitos(locals())
    if kind == "center_radius":
        if radius is None:
            raise error("INVALID_ARGUMENTS", "kind=center_radius necesita radius.")
        if points is not None:
            raise error("INVALID_ARGUMENTS", "points es de two_points y three_points; con center_radius usá radius.")
        return _dibujar(sesion, sketch, lambda b: _circulo(b, center_x, center_y, radius, construction),
                        construccion=construction, central=centerline)
    if radius is not None:
        raise error("INVALID_ARGUMENTS", f"kind={kind} no usa radius: el círculo sale de los puntos.")
    n = 2 if kind == "two_points" else 3
    if points is None or len(points) != n:
        raise error("INVALID_ARGUMENTS", f"kind={kind} necesita {n} puntos [x, y] en points.")
    p = [_xy(q, "Cada punto de points") for q in points]

    def crear(b):
        cid = agregar_circulo_puntos(b, p, construction)
        return {"": cid, "center": b.curvas[cid].centro}
    return _dibujar(sesion, sketch, crear, construccion=construction, central=centerline)


@herramienta("draw_arc", "boceto",
             "Dibuja un arco. Tres formas: centro + punto inicial + ángulo de barrido (center_x, center_y, start_x, "
             "start_y, sweep_angle; positivo = antihorario) o tres puntos (start_x, start_y, mid_x, mid_y, end_x, "
             "end_y), o tangente a una curva (tangent_to, inicio y final o radius + sweep_angle). "
             "La forma tangente comparte el extremo y agrega la restricción de tangencia. "
             "Un arco solo forma un perfil si se cierra con otras curvas.", modifica=True)
def draw_arc(sesion, start_x: float, start_y: float, center_x: float | None = None, center_y: float | None = None,
             sweep_angle: float | None = None, mid_x: float | None = None, mid_y: float | None = None,
             end_x: float | None = None, end_y: float | None = None, sketch: str | None = None,
             construction: bool = False, tangent_to: int | None = None, centerline: bool = False,
             radius: float | None = None):
    """
    start_x: x del punto inicial (mm).
    start_y: y del punto inicial (mm).
    center_x: x del centro (forma centro + barrido).
    center_y: y del centro.
    sweep_angle: ángulo de barrido en grados, entre -360 y 360 sin incluirlos; positivo = antihorario.
    mid_x: x de un punto intermedio del arco (forma de tres puntos).
    mid_y: y del punto intermedio.
    end_x: x del punto final (forma de tres puntos o tangente).
    end_y: y del punto final.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un arco de construcción (no forma perfiles).
    tangent_to: id de la línea, arco, arco de elipse, spline abierta o cónica de partida; el inicio coincide con un extremo. También acepta una elipse cerrada si el inicio está sobre ella. Usá final o radius + sweep_angle, sin centro ni punto intermedio.
    centerline: true para geometría central (forma perfiles); incompatible con construction=true.
    radius: radio positivo (mm), solo con tangent_to y sweep_angle; excluyente con end_x/end_y. El barrido positivo pone el centro a la izquierda de la salida tangente, negativo a la derecha; en la ventana ese lado lo elige el cursor.
    """
    _exigir_finitos(locals())
    if tangent_to is not None:
        if any(v is not None for v in (center_x, center_y, mid_x, mid_y)):
            raise error("INVALID_ARGUMENTS", "Con tangent_to no se usa centro ni punto intermedio.")
        if radius is not None:
            if end_x is not None or end_y is not None:
                raise error("INVALID_ARGUMENTS", "Con tangent_to, radius y end_x/end_y son excluyentes.")
            if sweep_angle is None:
                raise error("INVALID_ARGUMENTS", "Con tangent_to y radius hace falta sweep_angle.")
        elif end_x is None or end_y is None or sweep_angle is not None:
            raise error("INVALID_ARGUMENTS", "Con tangent_to indicá end_x/end_y o radius y sweep_angle, "
                        "sin combinar ambas formas.")
        op, previo = boceto_activo(sesion, sketch, derivados=False)

        informe = _dibujar(sesion, op.id, lambda b: _arco_tangente(
            b, tangent_to, (start_x, start_y), (end_x, end_y), construction, radius, sweep_angle), desde_solver=True,
            construccion=construction, central=centerline)
        _exigir_sin_conflicto(sesion, op, previo.solver.ok, "El arco tangente")
        return informe
    if radius is not None:
        raise error("INVALID_ARGUMENTS", "radius solo se usa con tangent_to y sweep_angle.")
    if sweep_angle is not None:
        if center_x is None or center_y is None:
            raise error("INVALID_ARGUMENTS", "Con sweep_angle hacen falta center_x y center_y.")
        if any(v is not None for v in (mid_x, mid_y, end_x, end_y)):
            raise error("INVALID_ARGUMENTS", "La forma centro + barrido no se combina con mid_x/mid_y ni "
                        "end_x/end_y (son de la forma de tres puntos).")
        return _dibujar(sesion, sketch, lambda b: _arco(b, center_x, center_y, start_x, start_y, sweep_angle,
                                                         construction), construccion=construction, central=centerline)
    if None in (mid_x, mid_y, end_x, end_y):
        raise error("INVALID_ARGUMENTS", "Indicá center_x, center_y y sweep_angle, o los tres puntos: "
                    "start, mid_x/mid_y y end_x/end_y.")
    if center_x is not None or center_y is not None:
        raise error("INVALID_ARGUMENTS", "La forma de tres puntos no usa center_x/center_y (sí la de centro + "
                    "sweep_angle).")
    return _dibujar(sesion, sketch, lambda b: _arco_3_puntos(b, (start_x, start_y), (mid_x, mid_y), (end_x, end_y),
                                                             construction), construccion=construction, central=centerline)


@herramienta("create_polygon", "boceto", "Dibuja un polígono regular de n lados (líneas iguales sobre un círculo guía "
             "de construcción, como la interfaz). Inscrito: los vértices están sobre el círculo de radio `radius`; "
             "circunscrito: los lados son tangentes a ese círculo (radius = medio entrecaras). Sin más, le quedan 4 "
             "grados de libertad (centro, tamaño y giro); con fully_constrained=true queda TOTALMENTE acotado: cota "
             "de radio del círculo guía (guarda la expresión de radius, así sigue a un parámetro), giro fijado "
             "(restricción horizontal/vertical o cota de ángulo) y centro acotado desde un punto fijo en el origen "
             "del boceto (dof 0).", modifica=True)
def create_polygon(sesion, sides: int, radius: Expr | None = None, center_x: float = 0.0, center_y: float = 0.0,
                   rotation: float = 0.0, kind: Literal["inscribed", "circumscribed", "edge"] = "inscribed",
                   sketch: str | None = None, construction: bool = False, fully_constrained: bool = False,
                   edge_points: list[list[float]] | None = None, centerline: bool = False):
    """
    sides: cantidad de lados (3 a 64; tope propio igual al de la interfaz: la ayuda de Fusion no publica un máximo).
    radius: radio del círculo guía en mm (circunradio si es inscrito, apotema si es circunscrito); número o expresión con parámetros ("entrecaras / 2"). No se usa con kind=edge.
    center_x: x del centro (mm).
    center_y: y del centro (mm).
    rotation: ángulo en grados del primer vértice respecto del eje x del boceto.
    kind: "inscribed" (vértices sobre el círculo), "circumscribed" (lados tangentes al círculo) o "edge" (polígono por arista: se da un lado con edge_points).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para un polígono de construcción (no forma perfiles).
    fully_constrained: true para dejarlo totalmente acotado (radio, giro y posición del centro): dof 0.
    edge_points: kind=edge: [[x, y], [x, y], [x, y]] = extremos A y B del primer lado y un punto del lado hacia donde crece el polígono.
    centerline: true para geometría central (forma perfiles); incompatible con construction=true.
    """
    _exigir_finitos(locals())
    if kind == "edge":
        if edge_points is None or len(edge_points) != 3:
            raise error("INVALID_ARGUMENTS", "kind=edge necesita edge_points: los extremos A y B del lado y un punto del lado hacia donde crece.")
        return _dibujar(sesion, sketch, lambda b: _poligono_arista(b, sides, edge_points, construction, fully_constrained),
                        construccion=construction, central=centerline)
    if radius is None:
        raise error("INVALID_ARGUMENTS", "radius es obligatorio salvo con kind=edge.")
    expresion = texto_expr(radius)
    valor = evaluar(expresion, LONGITUD, sesion.doc.parametros.valores())
    return _dibujar(sesion, sketch, lambda b: _poligono(b, sides, valor, center_x, center_y, rotation,
                                                         kind == "circumscribed", construction, fully_constrained,
                                                         expresion), construccion=construction, central=centerline)


@herramienta("draw_spline", "boceto", "Dibuja una spline: de ajuste (pasa por los puntos) o de puntos de control "
             "(grado 3 o 5; con menos de grado+1 puntos el grado baja a puntos−1, como Fusion). "
             "Con tangent_to, una spline de ajuste abierta "
             "comparte el extremo de otra curva y agrega tangencia; el solver ajusta los puntos libres.", modifica=True)
def draw_spline(sesion, points: list[list[float]], spline_type: Literal["fit_points", "control_points"] = "fit_points",
                degree: int = 5, closed: bool = False, sketch: str | None = None, construction: bool = False,
                centerline: bool = False, tangent_to: int | None = None,
                tangent_end: Literal["start", "end"] = "end"):
    """
    points: lista de puntos [x, y] en mm sobre el plano del boceto.
    spline_type: "fit_points" (pasa por los puntos) o "control_points" (los puntos son los polos).
    degree: grado de control (3 o 5, por defecto 5); baja a puntos−1 si faltan puntos. Se ignora en la de ajuste.
    closed: true para cerrar la spline de ajuste (forma un perfil); no compatible con control_points (Fusion no lo permite: lanza INVALID_ARGUMENTS).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una spline de construcción (no forma perfiles).
    centerline: true para geometría central (forma perfiles); incompatible con construction=true.
    tangent_to: id de la curva de partida (línea, arco, arco de elipse, spline abierta, cónica o elipse); solo para una spline de ajuste abierta. El primer punto debe coincidir con su extremo (o estar sobre la elipse cerrada).
    tangent_end: extremo de la curva de partida, "start" o "end"; se ignora en una elipse cerrada. El solver puede ajustar los puntos libres para cumplir la tangencia.
    """
    _exigir_finitos(locals())
    if tangent_to is not None:
        if spline_type != "fit_points" or closed:
            raise error("INVALID_ARGUMENTS", "tangent_to requiere una spline de ajuste abierta (fit_points, closed=false).")
        op, previo = boceto_activo(sesion, sketch, derivados=False)
        informe = _dibujar(sesion, op.id, lambda b: _spline(
            b, points, spline_type, degree, closed, construction, tangent_to, tangent_end), desde_solver=True,
            construccion=construction, central=centerline)
        _exigir_sin_conflicto(sesion, op, previo.solver.ok, "La spline tangente")
        return informe
    if closed and spline_type == "control_points":
        raise error("INVALID_ARGUMENTS", "Una spline de puntos de control no se puede cerrar (Fusion tampoco lo "
                    "permite). Para un perfil cerrado usá fit_points con closed=true, o uní los extremos con "
                    "una línea o arco.")
    return _dibujar(sesion, sketch, lambda b: _spline(b, points, spline_type, degree, closed, construction),
                    construccion=construction, central=centerline)


@herramienta("add_constraint", "boceto",
             "Agrega una restricción geométrica entre entidades del boceto (ids de get_sketch: curvas y puntos). Si "
             "choca con las que ya hay, falla y el boceto queda como estaba. Entidades por tipo: horizontal y "
             "vertical: una línea o dos puntos; parallel, perpendicular, collinear y equal: dos líneas (equal también "
             "dos círculos/arcos o dos elipses/arcos de elipse); coincident: un punto y otro punto o una curva; "
             "midpoint: un punto y una línea o arco; tangent: dos curvas geométricas, salvo dos líneas; "
             "concentric: dos curvas con centro; curvature: dos curvas encadenadas, al menos una spline o cónica; "
             "fix: una o más entidades; symmetry: dos entidades y la línea eje; polygon: tres o más líneas en cadena "
             "cerrada, o un solo lado (toma su cadena). Referencias reservadas: origen 0, eje X -1, "
             "eje Y -2 (origin/axes de get_sketch). Un fix repetido devuelve el existente. Con tangent, el primer arco o "
             "círculo queda quieto y no cambian radios ni largos; si la otra curva no puede moverse, se mueve el arco "
             "entero.",
             modifica=True)
def add_constraint(sesion, sketch: str,
                   type: Literal["coincident", "horizontal", "vertical", "parallel", "perpendicular", "equal",  # noqa: A002
                                 "tangent", "concentric", "midpoint", "fix", "collinear", "symmetry", "curvature", "polygon"],
                   entities: list[int]):
    """
    sketch: id o nombre del boceto.
    type: tipo de restricción.
    entities: ids de las entidades (curvas o puntos); en coincident, midpoint y tangent el orden no importa, en symmetry el eje va último; origen 0, eje X -1 y eje Y -2 son referencias fijas reservadas.
    """
    op = op_boceto(sesion, sketch)
    previo = boceto_resuelto(sesion, op)
    nueva = op.copia()
    b = nueva.boceto
    if type in ("fix", "tangent"):
        _sincronizar_con_solver(sesion, op, b)
    b.asegurar_referencias(entities)
    _exigir_entidades(b, entities)
    antes = _claves(b)
    try:
        if type == "tangent" and len(entities) == 2:
            b.deslizar_a_tangente(*entities)
        if type == "polygon" and len(entities) == 1:
            _curva(b, entities[0], ("linea",))
            cadena, cerrada = b.cadena(entities[0])
            if not cerrada or any(b.tipo_de(k) != "linea" for k, _ in cadena):
                raise ErrorBoceto("Polígono necesita una cadena cerrada de líneas.")
            entities = [k for k, _ in cadena]
        rid = b.agregar_restriccion(RESTRICCIONES[type], list(entities))
        if type == "tangent" and len(entities) == 2:
            acomodar_tangente(b, entities, valores_cotas(sesion, b))
    except ErrorBoceto as e:
        raise error("INVALID_CONSTRAINT", str(e)) from e
    if rid not in antes["restricciones"]:
        sesion.doc.reemplazar(op.id, nueva)
    _exigir_sin_conflicto(sesion, nueva, previo is None or previo.solver.ok, f"La restricción «{type}»")
    despues = boceto_resuelto(sesion, nueva)
    if (type != "fix" and rid not in antes["restricciones"] and previo is not None and despues is not None
            and previo.solver.ok and despues.solver.ok and despues.solver.gdl >= previo.solver.gdl):
        raise error("SKETCH_OVERCONSTRAINED", f"La restricción «{type}» no quita ningún grado de libertad: el boceto "
                    f"«{op.nombre}» ya la cumple por otras restricciones o cotas (sobre-definiría). No se agregó.")
    fuera = despues.boceto.tangencias_fuera_del_arco() if type == "tangent" and despues is not None else []
    if fuera:
        sesion.avisar(aviso_tangencias_fuera(fuera))
    informe = _informe_edicion(sesion, nueva, b, antes)
    return {"sketch": informe["sketch"], "constraint": {"id": rid, "type": type, "entities": b.restricciones[rid].entidades},
            "profiles": informe["profiles"], "dof": informe["dof"], "status": informe["status"]}


@herramienta("replace_constraint", "boceto",
             "Cambia una restricción por otra sobre las mismas entidades y con el mismo id, en un solo paso (en la "
             "ventana: clic derecho en su símbolo › Cambiar por; si la nueva no quita ningún grado de libertad —el boceto "
             "ya la cumple por otras—, falla con SKETCH_OVERCONSTRAINED y queda la anterior, igual que add_constraint). "
             "Una restricción no tiene valores que editar: lo "
             "que se cambia es qué relación pide. Valen horizontal, vertical, coincident, parallel, perpendicular, "
             "equal, tangent, concentric, midpoint y collinear, siempre que la nueva aplique a esas entidades "
             "(horizontal ↔ vertical en una línea o dos puntos, parallel ↔ perpendicular ↔ equal ↔ collinear en dos "
             "líneas…). Si no aplica o choca con las demás, falla y queda la anterior. Para otras (fix, symmetry, "
             "curvature, polygon): delete_sketch_entities y add_constraint.", modifica=True)
def replace_constraint(sesion, sketch: str, constraint: int,
                       type: Literal["horizontal", "vertical", "coincident", "parallel", "perpendicular",  # noqa: A002
                                     "equal", "tangent", "concentric", "midpoint", "collinear"]):
    """
    sketch: id o nombre del boceto.
    constraint: id de la restricción a cambiar (constraints de get_sketch).
    type: tipo nuevo.
    """
    op = op_boceto(sesion, sketch)
    previo = boceto_resuelto(sesion, op)
    nueva = op.copia()
    b = nueva.boceto
    if constraint not in b.restricciones:
        raise error("ENTITY_NOT_FOUND", f"El boceto no tiene la restricción {constraint}.")
    antes = _claves(b)
    try:
        if type == "tangent":
            _sincronizar_con_solver(sesion, op, b)
        b.reemplazar_restriccion(constraint, RESTRICCIONES[type])
        if type == "tangent":
            acomodar_tangente(b, b.restricciones[constraint].entidades, valores_cotas(sesion, b))
    except ErrorBoceto as e:
        raise error("INVALID_CONSTRAINT", str(e)) from e
    sesion.doc.reemplazar(op.id, nueva)
    _exigir_sin_conflicto(sesion, nueva, previo is None or previo.solver.ok, f"La restricción «{type}»")
    despues = boceto_resuelto(sesion, nueva)
    if (previo is not None and previo.solver.ok and despues is not None and despues.solver.ok
            and not restriccion_quita_grados(b, constraint, valores_cotas(sesion, b))):
        raise error("SKETCH_OVERCONSTRAINED", f"La restricción «{type}» no quita ningún grado de libertad: el boceto "
                    f"«{op.nombre}» ya la cumple por otras restricciones o cotas (sobre-definiría). No se cambió.")
    informe = _informe_edicion(sesion, nueva, b, antes)
    return {"sketch": informe["sketch"], "constraint": {"id": constraint, "type": type,
                                                         "entities": b.restricciones[constraint].entidades},
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
             "puntos, una línea, un punto y una línea, o dos líneas paralelas (si no son paralelas, usá angle); horizontal y vertical: dos puntos o una línea; "
             "radius y diameter: un círculo o arco (diameter también acepta un punto o una línea con una línea central: mide el doble de la distancia al eje, como Fusion); angle: dos líneas; "
             "offset: dos líneas, dos círculos/arcos, dos splines, una elipse/arco de elipse seguida de una spline, "
             "o dos elipses. distance "
             "también acepta un círculo o arco con un punto, una línea u otro círculo o arco (`mode`: center mide al "
             "centro, tangent al borde más cercano; entre círculos, de borde a borde) y un punto con una spline (la "
             "distancia a la curva). En una cota "
             "lineal (distance, horizontal o vertical de una línea o de dos puntos), `offset` y `text_offset` fijan "
             "dónde se dibuja: no cambian el valor ni la geometría; `position` [x, y] (mm) hace lo mismo que arrastrar la "
             "cota con el ratón y vale en todas: en las lineales fija offset y text_offset, en un ángulo el radio del "
             "arco, en un radio o diámetro hacia dónde sale la línea y en las demás dónde va el texto. Origen 0, eje X -1, "
             "eje Y -2. Cada cota recibe un name dN único en el documento, "
             "visible en get_parameters y citable en expresiones de otras cotas, parámetros y operaciones. "
             "reference=true crea una cota de referencia: mide sin restringir e ignora value. Una cota driving "
             "redundante o en conflicto se crea como referencia con aviso y converted_to_reference=true. En angle, "
             "`near` [x, y] elige qué ángulo se mide, como el cursor en Fusion: el del cuadrante entre las dos rectas "
             "que contiene ese punto (45° o 135° en la misma figura); sin near mide entre las líneas tal como se "
             "dibujaron. El cuadrante (0..3) se guarda y get_sketch lo muestra como quadrant.",
             modifica=True)
def add_dimension(sesion, sketch: str,
                  type: Literal["distance", "horizontal", "vertical", "radius", "diameter", "angle", "offset"],  # noqa: A002
                  entities: list[int], value: Expr | None = None, offset: float | None = None,
                  text_offset: float | None = None, reference: bool = False,
                  mode: Literal["center", "tangent"] = "center", near: list[float] | None = None,
                  position: list[float] | None = None, name: str | None = None):
    """
    sketch: id o nombre del boceto.
    name: nombre del parámetro de la cota (como tipear «ANCHO=20» en la caja de la cota de la ventana); vacío = el dN automático. Tiene que estar libre.
    type: tipo de cota.
    entities: ids de las entidades acotadas (curvas o puntos), en el orden que pide el tipo; origen 0, eje X -1 y eje Y -2 son referencias fijas reservadas.
    value: valor: número (mm; grados en angle) o expresión con parámetros, p. ej. "radio_agujero * 2". Vacío = medida actual.
    offset: mm que se separa la línea de cota de la medida (con signo, hacia +Y en horizontal, +X en vertical, a la izquierda de la línea en distance); vacío = lo automático.
    text_offset: mm que se corre el texto a lo largo de la línea de cota desde su centro; vacío = centrado.
    reference: true = cota de referencia (driven): mide la geometría sin restringirla; ignora value.
    mode: en una distancia con un círculo o arco: "center" (al centro) o "tangent" (al borde más cercano).
    near: [x, y] en mm, solo en angle: el ángulo medido es el del cuadrante entre las dos rectas que contiene este punto; vacío = entre las líneas tal como se dibujaron.
    position: [x, y] en mm: donde queda la cota, como si se la arrastrara con el ratón (no cambia el valor; en una cota de ángulo también elige qué ángulo mide, como near); no se combina con offset ni text_offset; vacío = lo automático.
    """
    op, br = boceto_activo(sesion, sketch, derivados=False)
    nueva = op.copia()
    b = nueva.boceto
    _sincronizar_con_solver(sesion, op, b)
    b.asegurar_referencias(entities)
    _exigir_entidades(b, entities)
    interno = COTAS[type]
    # Fusion: una cota con la línea central es un DIÁMETRO (el doble de la distancia al eje).
    diametral = type == "diameter" and len(entities) == 2 and any(
        getattr(b.curvas.get(i), "eje", False) for i in entities)
    if diametral:
        interno = "distancia"
    try:
        b._validar_cota(interno, list(entities))     # el tipo de entidad, antes de medir
    except ErrorBoceto as e:
        raise error("INVALID_DIMENSION", str(e)) from e
    cuadrante = _cuadrante(b, interno, list(entities), near)
    datos = {"modo": _MODOS[mode], **({} if cuadrante is None else {"cuadrante": cuadrante}),
             **({"diametral": True} if diametral else {})}
    if value is None or reference:
        try:
            medida = b.medir_cota(interno, list(entities), _MODOS[mode], cuadrante)
        except (ErrorBoceto, KeyError, ValueError, IndexError) as e:
            raise error("INVALID_DIMENSION", f"No se pudo medir la cota «{type}» con esas entidades: {e}") from e
        expresion = repr(round(medida * (2 if diametral else 1), 6))
    else:
        expresion = texto_expr(value)
    valor = evaluar(expresion, ANGULO if interno == "angulo" else LONGITUD, sesion.doc.parametros.valores())
    if not reference:
        _cota_valida(interno, valor, f"La cota «{type}»")
    antes = _claves(b)
    try:
        kid = b.agregar_cota(interno, list(entities), expresion, datos, referencia=reference)
    except ErrorBoceto as e:
        raise error("INVALID_DIMENSION", str(e)) from e
    _fijar_ubicacion(b, b.cotas[kid], offset, text_offset, position)
    if name:
        validar_nombre(name)
        b.cotas[kid].nombre = name              # el documento rechaza el duplicado al reemplazar el paso
    convertida = not reference and _cota_sobre_restringe(sesion, b, br.solver)
    if convertida:
        b.cotas[kid].referencia = True
        b.cotas[kid].expresion = repr(b.medir(b.cotas[kid]))
        sesion.avisar("La cota sobre-restringiría el boceto: se creó como cota de referencia (driven).")
    sesion.doc.reemplazar(op.id, nueva)
    informe = _informe_edicion(sesion, nueva, b, antes)
    k = b.cotas[kid]
    valor = _valor_cota(sesion, k)
    return {"sketch": informe["sketch"], "dimension": {"id": kid, "name": b.cotas[kid].nombre, "type": type, "entities": list(entities),
                                                       "expression": k.expresion, "value": valor, "reference": k.referencia,
                                                        **_ubicacion_cota(b.cotas[kid])},
            "profiles": informe["profiles"], "dof": informe["dof"], "status": informe["status"],
            "converted_to_reference": convertida}


def _cota_sobre_restringe(sesion, boceto, anterior):
    """Prueba sin mover el documento: una cota driving debe bajar los GDL sin dejar residuo."""
    resultado = resolver(boceto.copia(), valores_cotas(sesion, boceto))
    return not resultado.ok or resultado.gdl >= anterior.gdl


@herramienta("get_sketch", "boceto",
             "Informe de un boceto: plano y su marco 3D, entidades con ids estables (coordenadas ya resueltas por el "
             "solver), puntos, restricciones, cotas con su valor, perfiles (índice, área mm², centroide, caja "
             "[min/max en coordenadas del boceto] y curvas del borde) y estado del solver en la clave `status` "
             "(fully_constrained, under_constrained, over_constrained) con los grados de libertad en `dof`. Cada punto "
             "y curva trae state: free, determined o fixed. conflicts lista los ids de restricciones/cotas cuya "
             "retirada individual resuelve el conflicto (vacía sin conflicto o si hacen falta varias retiradas). "
             "origin=0 y axes={x:-1,y:-2} son ids reservados citables en add_constraint/add_dimension; las referencias "
             "se materializan como construcción fija al citarlas y no forman perfiles. dimensions incluye name (dN), "
             "el parámetro de cada cota, sincronizado con get_parameters/set_parameter, y reference: true indica "
             "una cota driven cuyo value es la medida actual y no aporta restricciones ni reduce dof. Si el boceto "
             "tiene geometría 3D (draw_line_3d y las demás *_3d) trae además entities_3d, points_3d (x, y, z; source "
             "si sigue a un vértice del modelo), "
             "constraints_3d, dimensions_3d, status_3d y dof_3d. tangents_off_arc lista los pares [a, b] tangentes cuyo "
             "contacto cae fuera del tramo dibujado de un arco: la tangencia se resuelve contra su círculo entero.")
def get_sketch(sesion, sketch: str | None = None):
    """
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    return info_boceto(sesion, op_boceto(sesion, sketch, derivados=True))


@herramienta("find_redundant_constraints", "boceto",
             "Dice qué restricciones y cotas SOBRAN en un boceto: las que no quitan ningún grado de libertad porque "
             "otras ya fijan lo mismo (el boceto está sobre-definido pero se puede cumplir; no es un conflicto, para "
             "eso mirá `conflicts` de get_sketch). Se suman de a una en orden de id y se marca la que no baja el rango: "
             "de tres paralelas que se implican entre sí sale solo la última. No cambia el boceto: para sacar una, "
             "delete_sketch_entities con su id. Con más de 150 restricciones y cotas no se calcula (checked=false).")
def find_redundant_constraints(sesion, sketch: str | None = None):
    """
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    op, br = boceto_activo(sesion, sketch, derivados=False)
    b = op.boceto.copia()
    _sincronizar_con_solver(sesion, op, b)
    sobran = restricciones_redundantes(b, valores_cotas(sesion, b))
    estado, gdl = estado_solver(br)

    def item(i):
        if i in b.restricciones:
            r = b.restricciones[i]
            return {"kind": "constraint", "id": i, "type": _RESTRICCION_A_INGLES.get(r.tipo, r.tipo), "entities": r.entidades}
        k = b.cotas[i]
        return {"kind": "dimension", "id": i, "type": _COTA_A_INGLES.get(k.tipo, k.tipo), "entities": k.entidades}
    return {"sketch": _paso(op), "status": estado, "dof": gdl, "checked": sobran is not None,
            "redundant": [item(i) for i in sobran or []]}


@herramienta("find_underconstrained", "boceto",
             "Lista la geometría SUBRESTRINGIDA del boceto (Fusion: Find Under-Constrained, en la Paleta de boceto): "
             "las curvas y los puntos que todavía se pueden mover porque ninguna restricción ni cota los fija. Los "
             "mismos ids de get_sketch (entities y points); su `state` es «free». Un boceto totalmente restringido "
             "devuelve las dos listas vacías y count=0. No cambia el boceto.")
def find_underconstrained(sesion, sketch: str | None = None):
    """
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    op, _br = boceto_activo(sesion, sketch, derivados=True)
    info = info_boceto(sesion, op)
    curvas = [{"id": e["id"], "type": e["type"]} for e in info["entities"] if e["state"] == "free"]
    puntos = [{"id": p["id"], "x": p["x"], "y": p["y"]} for p in info["points"] if p["state"] == "free"]
    return {"sketch": _paso(op), "status": info["status"], "dof": info["dof"],
            "count": len(curvas) + len(puntos), "entities": curvas, "points": puntos}


@herramienta("compute_sketch", "boceto",
             "Vuelve a analizar el boceto entero y devuelve el estado de restricción de cada entidad (Fusion: Compute "
             "Sketch, en la Paleta de boceto): resuelve el boceto de nuevo desde sus restricciones y cotas actuales y "
             "cuenta qué quedó fijo. `constrained` son las entidades que ya no se mueven, `free` las que sí, y "
             "`dof` los grados de libertad que sobran. No cambia el boceto.")
def compute_sketch(sesion, sketch: str | None = None):
    """
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    op, br = boceto_activo(sesion, sketch, derivados=True)
    b = br.boceto.copia()
    _sincronizar_con_solver(sesion, op, b)
    r = resolver(b, valores_cotas(sesion, b))
    total = len(b.puntos) + len(b.curvas)
    fijas = len(r.determinadas)
    estado = "over_constrained" if not r.ok else ("fully_constrained" if r.gdl == 0 else "under_constrained")
    return {"sketch": _paso(op), "ok": r.ok, "status": estado, "dof": r.gdl,
            "constrained": fijas, "free": total - fijas, "message": r.descripcion()}


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


def _booleano(e, i, clave):
    v = e.get(clave, False)
    if not isinstance(v, bool):
        raise _spec_error(i, e.get("type"), f"'{clave}' tiene que ser true o false (llegó {v!r}).")
    return v


def _texto_spec(b, i, e, alias, sesion):
    """Texto de especificación con las mismas opciones y validaciones que add_text."""
    from .herramientas_vectores import _mm_de_caracter, _opciones_camino, _opciones_texto, _verificar_fuente

    for clave in ("bold", "italic", "flip_h", "flip_v", "kerning", "fit_path", "no_wrap"):
        if clave in e:
            _booleano(e, i, clave)
    for clave in ("x", "y", "height", "angle", "letter_spacing", "character_spacing", "line_spacing", "box_width", "skew", "scale_x",
                  "scale_y", "baseline_shift", "decoration_thickness", "path_position", "path_offset"):
        if clave in e:
            _numero(e[clave], i, "text", clave)
    texto = str(_campo(e, i, "text")).replace("\\n", "\n")
    fuente, negrita, cursiva = e.get("font", "Arial"), e.get("bold", False), e.get("italic", False)
    _verificar_fuente(fuente, negrita, cursiva)
    camino = _citar(e["path_entity"], alias, b, f"Texto {i}") if e.get("path_entity") is not None else None
    alineacion = e.get("align")
    if alineacion is None:
        alineacion = "center" if camino else "left"
    espaciado = e.get("letter_spacing", 0.0)
    if "character_spacing" in e:
        espaciado = _mm_de_caracter(e["character_spacing"], espaciado, fuente, e.get("height", 5.0), negrita, cursiva)
    opciones = _opciones_texto(espaciado, e.get("line_spacing", 1.0), alineacion,
                              e.get("anchor", "baseline"), e.get("box_width", 0.0), e.get("flip_h", False),
                              e.get("flip_v", False), **{k: e[k] for k in (
                                  "kerning", "skew", "scale_x", "scale_y", "baseline_shift", "case", "underline",
                                  "strikethrough", "decoration_thickness", "no_wrap", "kerning_pairs") if k in e})
    if camino is not None:
        opciones |= _opciones_camino(camino, e.get("path_side", "left"), e.get("path_position"),
                                    e.get("path_offset", 0.0), e.get("fit_path", False),
                                    e.get("path_placement", "above"))
        if e.get("underline", "none") != "none" or e.get("strikethrough", "none") != "none":
            sesion.avisar("El subrayado y el tachado no se dibujan en un texto en curva.")
    tid = b.agregar_texto((e.get("x", 0.0), e.get("y", 0.0)), texto, altura=e.get("height", 5.0),
                          angulo=e.get("angle", 0.0), fuente=fuente, negrita=negrita, cursiva=cursiva, **opciones)
    b.curvas[tid].construccion = _booleano(e, i, "construction")
    ligar_parametro_texto(sesion.doc, b.curvas[tid], texto)
    return {"": tid, "position": b.curvas[tid].punto}


def _construir_entidad(b, i, e, alias, sesion):
    tipo = e.get("type")
    c = _booleano(e, i, "construction")
    p = lambda k, *alt: _xy(_campo(e, i, k, alt), f"'{k}' de la entidad {i}")  # noqa: E731
    if tipo == "line":
        (x1, y1), (x2, y2) = p("start"), p("end")
        return _linea(b, x1, y1, x2, y2, c, encadenar=True)
    if tipo == "midpoint_line":
        centro, extremo = p("center"), p("end")
        if math.dist(centro, extremo) < 1e-9:
            raise ErrorBoceto("Una línea necesita dos puntos distintos.")
        medio = b.agregar_punto(*centro)
        lid = agregar_linea_medio(b, medio, extremo, c)
        ln = b.curvas[lid]
        return {"": lid, "start": ln.p1, "end": ln.p2, "center": medio}
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
    if tipo == "tangent_arc":
        cita = _campo(e, i, "from")
        pid = _citar(cita, alias, b, f"Arco tangente {i}")
        lineas = [ln.id for ln in b.curvas.values() if ln.tipo == "linea" and pid in ln.extremos()]
        origen = alias.get(cita.rsplit(".", 1)[0]) if isinstance(cita, str) and "." in cita else None
        if origen in lineas:
            lineas = [origen]
        if len(lineas) != 1:
            raise _spec_error(i, tipo, "'from' debe citar un extremo de una sola línea.")
        return _arco_tangente(b, lineas[0], b.coords(pid), p("end"), c)
    if tipo == "tangent_circle":
        citas = _campo(e, i, "lines")
        if not isinstance(citas, list):
            raise _spec_error(i, tipo, "'lines' debe ser una lista de 2 o 3 citas de líneas.")
        lineas = [_citar(t, alias, b, f"Círculo tangente {i}") for t in citas]
        numeros = {k: None if e.get(k) is None else _numero(e[k], i, tipo, k) for k in ("x", "y", "radius")}
        return _circulo_tangente(b, lineas, numeros["x"], numeros["y"], numeros["radius"], c)
    if tipo == "conic":
        cid = b.agregar_conica(p("start"), p("vertex"), p("end"), _numero(e.get("rho", 0.5), i, tipo, "rho"), c)
        curva = b.curvas[cid]
        return {"": cid, "start": curva.inicio, "end": curva.fin, "vertex": curva.vertice}
    if tipo == "text":
        return _texto_spec(b, i, e, alias, sesion)
    if tipo == "polygon":
        cx, cy = p("center") if "center" in e else (0.0, 0.0)
        lados = _campo(e, i, "sides")
        if isinstance(lados, bool) or not isinstance(lados, int):
            raise _spec_error(i, tipo, "'sides' tiene que ser un entero.")
        kind = e.get("kind", "inscribed")
        if kind == "edge":
            if "edge_points" in e:
                puntos = e["edge_points"]
                if not isinstance(puntos, list):
                    raise _spec_error(i, tipo, "'edge_points' debe ser una lista de tres puntos.")
            else:
                a, z = p("start"), p("end")
                # Sin punto de orientación crece a la izquierda del lado dirigido A→B.
                puntos = [a, z, (a[0] - (z[1] - a[1]), a[1] + (z[0] - a[0]))]
            return _poligono_arista(b, lados, puntos, c, _booleano(e, i, "fully_constrained"))
        if kind not in ("inscribed", "circumscribed"):
            raise _spec_error(i, tipo, "'kind' es inscribed, circumscribed o edge.")
        return _poligono(b, lados, _numero(_campo(e, i, "radius"), i, tipo, "'radius'"), cx, cy,
                         _numero(e.get("rotation", 0.0), i, tipo, "'rotation'"), kind == "circumscribed", c,
                         _booleano(e, i, "fully_constrained"))
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
        grado = e.get("degree", 5)
        if isinstance(grado, float) and grado.is_integer():
            grado = int(grado)
        if isinstance(grado, bool) or not isinstance(grado, int):
            raise _spec_error(i, tipo, "'degree' tiene que ser un entero (3 o 5).")
        return _spline(b, _campo(e, i, "points"), tipo_spline, grado, _booleano(e, i, "closed"), c)
    if tipo == "point":
        x, y = p("at", "position")
        return {"": b.agregar_punto(x, y)}
    if tipo in _TIPOS_3D:
        return _entidad_3d(b, i, e, tipo, c)
    raise _spec_error(i, tipo, "tipo desconocido. Tipos: line, midpoint_line, rectangle, circle, tangent_circle, "
                      "arc, tangent_arc, polygon, ellipse, slot, spline, conic, text, point, " + ", ".join(_TIPOS_3D)
                      + ".")


_TIPOS_3D = ("line_3d", "spline_3d", "point_3d", "arc_3d", "circle_3d", "ellipse_3d", "rectangle_3d", "conic_3d",
             "text_3d")


def _entidad_3d(b, i, e, tipo, c):
    """Curva del Boceto 3D de un spec (las mismas que draw_*_3d), en coordenadas [x, y, z] del boceto."""
    from ..restricciones import boceto3d as b3
    from .herramientas_boceto3d import _PLANOS

    def xyz(v, clave):
        if not (isinstance(v, (list, tuple)) and len(v) == 3 and all(_finito(x) for x in v)):
            raise _spec_error(i, tipo, f"'{clave}' tiene que ser [x, y, z] con tres números finitos.")
        return [float(x) for x in v]

    p = lambda k: xyz(_campo(e, i, k), k)  # noqa: E731

    n = lambda k: _numero(_campo(e, i, k), i, tipo, f"'{k}'")  # noqa: E731
    normal = p("normal") if "normal" in e else [0.0, 0.0, 1.0]
    plano = e.get("plane", "xy")
    if tipo in ("rectangle_3d", "text_3d") and plano not in _PLANOS:
        raise _spec_error(i, tipo, "'plane' es xy, yz o zx.")
    if tipo == "line_3d":
        return {"": b3.agregar_linea(b, p("start"), p("end"), c)}
    if tipo == "spline_3d":
        puntos = _campo(e, i, "points")
        if not isinstance(puntos, list):
            raise _spec_error(i, tipo, "'points' es una lista de [x, y, z].")
        return {"": b3.agregar_spline(b, [xyz(q, f"points[{k}]") for k, q in enumerate(puntos)], c,
                                      _booleano(e, i, "closed"))}
    if tipo == "point_3d":
        return {"": b3.agregar_punto(b, p("at"), unir=False)}
    if tipo == "arc_3d":
        return {"": b3.agregar_arco(b, p("start"), p("through"), p("end"), c)}
    if tipo == "circle_3d":
        return {"": b3.agregar_circulo(b, p("center"), n("radius"), normal, c)}
    if tipo == "ellipse_3d":
        centro, k = np.array(p("center")), np.array(normal) / (np.linalg.norm(normal) or 1.0)
        eje = (np.array(p("major_end")) - centro) - ((np.array(p("major_end")) - centro) @ k) * k
        return {"": b3.agregar_elipse(b, centro, eje, n("minor_radius"), normal, c)}
    if tipo == "rectangle_3d":
        lineas = b3.agregar_rectangulo(b, p("corner"), p("opposite"), *_PLANOS[plano], c)
        return {f"l{k}": lid for k, lid in enumerate(lineas, start=1)}
    if tipo == "conic_3d":
        return {"": b3.agregar_conica(b, p("start"), p("shoulder"), p("end"), n("rho") if "rho" in e else 0.5, c)}
    return {"": b3.agregar_texto(b, p("origin"), str(_campo(e, i, "text")), n("height") if "height" in e else 5.0,
                                 *_PLANOS[plano], e.get("font", "Arial"), c)}


def _citar(token, alias, b, que):
    if isinstance(token, bool):
        raise error("INVALID_SPEC", f"{que}: '{token}' no es una cita válida.")
    if isinstance(token, int):
        _exigir_entidades(b, [token])
        return token
    if not isinstance(token, str):
        raise error("INVALID_SPEC", f"{que}: {token!r} no es una cita válida (texto o entero).")
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
             "point{at}, conic{start,end,vertex,rho}, text{text,...} (opciones de add_text, path_entity admite cita), "
             "midpoint_line{center,end}, polygon{kind:edge,start,end,sides,edge_points?} (sin edge_points crece a la "
             "izquierda de start→end; edge_points permite elegir el lado como create_polygon), "
             "tangent_circle{lines:[citas],x?,y?,radius?}, tangent_arc{from:cita de extremo de línea,end}. "
             "Boceto 3D (como draw_*_3d, coordenadas [x, y, z]): line_3d{start,end}, spline_3d{points,closed?}, "
             "point_3d{at}, arc_3d{start,through,end}, circle_3d{center,radius,normal?}, ellipse_3d{center,major_end,"
             "minor_radius,normal?}, rectangle_3d{corner,opposite,plane?} (citas 'id.l1..l4'), conic_3d{start,"
             "shoulder,end,rho?}, text_3d{text,origin,height?,plane?,font?}; normal vacía = [0, 0, 1], plane = xy, "
             "yz o zx (por defecto xy). "
             "Todas aceptan id (nombre propio para citarla), construction y centerline (mutuamente excluyentes; "
             "texto no admite centerline, los puntos sueltos no tienen tipo de línea). Las coordenadas son [x, y] en "
             "mm del plano. constraints: [{type, entities:[citas]}]; dimensions: [{type, entities:[citas], value, reference?}] "
             "(value puede ser una expresión con parámetros). Citas: 'id' (la curva), 'id.start', 'id.end', "
             "'id.center', en un rectángulo 'id.bottom/right/top/left' (líneas) y 'id.c1..c4' (esquinas), en un "
             "polígono 'id.side1..', 'id.v1..' y 'id.circle', en una elipse 'id.major' y 'id.major_axis/minor_axis', "
             "en una ranura 'id.side1/side2/end1/end2/axis/center1/center2'; un entero cita un id de "
             "entidad ya existente. Sin id, la entidad se cita 'e0', 'e1'… según su posición en la lista. plane es un "
             "plano o una cara plana (selector '>Z' o id de find_faces), con los mismos ejes que create_sketch sobre "
             "esa cara (find_faces da center_uv); con varios cuerpos, body dice en cuál se evalúa el selector. Devuelve "
             "handles (cita → id real), perfiles, estado y plane_frame (origen y ejes del plano). "
             "Sin entities crea un boceto vacío y devuelve un aviso. reference=true mide sin restringir.", modifica=True)
def sketch_from_spec(sesion, plane: str = "XY", entities: list[dict] | None = None,
                     constraints: list[dict] | None = None, dimensions: list[dict] | None = None,
                     name: str | None = None, body: str | None = None, project_edges: bool = False):
    """
    plane: "XY", "XZ", "YZ", el id/nombre de un plano de construcción, o una cara plana: selector (">Z") o id ("Cuerpo1/F6").
    entities: geometría del boceto (ver la descripción de la herramienta).
    constraints: restricciones, cada una {"type": ..., "entities": [citas]}.
    dimensions: cotas, cada una {"type": ..., "entities": [citas], "value": número o expresión, "reference": false}; reference=true mide sin restringir y permite omitir value.
    name: nombre del boceto; vacío = "Boceto1", "Boceto2"…
    body: id o nombre del cuerpo donde se evalúa el selector de cara de plane; vacío = el único cuerpo. No se usa con un plano ni con un id de cara.
    project_edges: true (solo sobre una cara) proyecta además el contorno de la cara de forma asociativa; false no proyecta nada.
    """
    ref, marco, cara, ref_cara = plano_o_cara(sesion, plane, body)
    doc = sesion.doc
    b = Boceto()
    alias = {}
    if not entities:
        sesion.avisar("entities está vacío: se creó un boceto vacío.")
    try:
        for i, e in enumerate(entities or []):
            if not isinstance(e, dict):
                raise error("INVALID_SPEC", f"Entidad {i}: tiene que ser un objeto con 'type'.")
            central = _booleano(e, i, "centerline")
            if central and _booleano(e, i, "construction"):
                raise _spec_error(i, e.get("type"), "construction y centerline no pueden ser true a la vez.")
            anteriores = set(b.curvas) if central else ()
            if (e.get("type") == "spline"
                    and e.get("spline_type") == "control_points"
                    and _booleano(e, i, "closed")):
                raise error("INVALID_ARGUMENTS",
                            f"Entidad {i}: una spline de puntos de control no se puede cerrar (Fusion tampoco lo "
                            "permite). Para un perfil cerrado usá fit_points con closed=true, o uní los extremos "
                            "con una línea o arco.")
            partes = _construir_entidad(b, i, e, alias, sesion)
            if central:
                _marcar_centrales(b, anteriores)
            manejador = str(e.get("id", f"e{i}"))
            if any(k == manejador or k.startswith(manejador + ".") for k in alias):
                raise error("INVALID_SPEC", f"Entidad {i}: el id '{manejador}' está repetido.")
            for sufijo, eid in partes.items():
                alias[f"{manejador}.{sufijo}" if sufijo else manejador] = eid
        _exigir_tamano(b)
        for j, r in enumerate(constraints or []):
            tipo = r.get("type") if isinstance(r, dict) else None
            if tipo not in RESTRICCIONES:
                raise error("INVALID_CONSTRAINT", f"Restricción {j}: tipo '{tipo}' desconocido.")
            ids = [_citar(t, alias, b, f"Restricción {j}") for t in (r.get("entities") or [])]
            if tipo == "coincident" and len(ids) == 2 and ids[0] == ids[1]:
                continue                                    # extremos ya unidos al encadenar las líneas
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
            referencia = _booleano(d, j, "reference")
            if d.get("value") is None and not referencia:
                raise error("INVALID_DIMENSION", f"Cota {j}: falta 'value' (número o expresión).")
            expresion = texto_expr(d["value"]) if d.get("value") is not None else "0"
            try:
                if not referencia:
                    valor = evaluar(expresion, ANGULO if tipo == "angle" else LONGITUD, valores)
                    _cota_valida(COTAS[tipo], valor, f"Cota {j}")
                b.agregar_cota(COTAS[tipo], ids, expresion, referencia=referencia)
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
    if project_edges:
        info.update(_proyectar_aristas_de_cara(sesion, op, ref_cara))
        info["entities"] += info.get("projected", 0)
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
                 angle: float = 0.0, sketch: str | None = None, construction: bool = False, centerline: bool = False):
    """
    major_radius: semieje mayor en mm (positivo): distancia del centro al extremo del eje mayor.
    minor_radius: semieje menor en mm (positivo).
    center_x: x del centro (mm).
    center_y: y del centro (mm).
    angle: giro del eje mayor en grados respecto del eje x del boceto (antihorario).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una elipse de construcción (no forma perfiles).
    centerline: true para geometría central (forma perfiles); incompatible con construction=true.
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: _elipse(b, center_x, center_y, major_radius, minor_radius, angle,
                                                      construction), construccion=construction, central=centerline)


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
              sketch: str | None = None, construction: bool = False, centerline: bool = False):
    """
    points: 2 puntos [x, y] (ranuras rectas) o 3 (ranuras de arco), en mm; qué es cada uno depende de kind.
    width: ancho total de la ranura en mm (positivo; en una de arco, menor que el doble del radio del eje).
    kind: center_to_center, overall, center_point, arc_three_points o arc_center.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true para una ranura de construcción (no forma perfiles).
    centerline: true para geometría central (forma perfiles); incompatible con construction=true.
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: _ranura(b, kind, points, width, construction),
                    construccion=construction, central=centerline)


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
               rho: float = 0.5, sketch: str | None = None, construction: bool = False, centerline: bool = False):
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
    centerline: true para geometría central (forma perfiles); incompatible con construction=true.
    """
    _exigir_finitos(locals())
    return _dibujar(sesion, sketch, lambda b: b.agregar_conica((start_x, start_y), (vertex_x, vertex_y),
                                                               (end_x, end_y), rho, construction),
                    construccion=construction, central=centerline)


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
    return _dibujar(sesion, sketch, lambda b: _circulo_tangente(b, lines, x, y, radius, construction), desde_solver=True)


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
    return _dibujar(sesion, sketch, crear, desde_solver=True, sin_conflicto="La curva de fusión")


# ---------------------------------------------------------------- modificar: empalme, chaflán, recortar, desfase
def _exigir_seleccion_esquina(vertice, primera, segunda, nombres):
    if ((vertice is not None and (primera is not None or segunda is not None)) or
            (vertice is None and (primera is None or segunda is None))):
        raise error("INVALID_ARGUMENTS", f"Pasá vertex o {nombres}, nunca ambos ni ninguno.")


@herramienta("sketch_fillet", "boceto",
             "Empalme de boceto (Fusion: Empalme en el boceto): redondea la esquina entre dos curvas (líneas, arcos o "
             "círculos) con un arco tangente; recorta las curvas, agrega las tangencias y la cota de radio. radius "
             "puede ser una expresión con parámetros (queda en la cota). Con point1/point2 se elige qué parte de cada "
             "curva se conserva; sin ellos, la parte más larga. Admite vertex en lugar de las curvas.", modifica=True)
def sketch_fillet(sesion, radius: Expr, entity1: int | None = None, entity2: int | None = None,
                  point1: list[float] | None = None, point2: list[float] | None = None,
                  sketch: str | None = None, vertex: int | None = None):
    """
    entity1: id de la primera curva (get_sketch).
    entity2: id de la segunda curva.
    radius: radio del empalme en mm: número o expresión con parámetros.
    point1: [x, y] sobre entity1, del lado que se conserva; vacío = automático.
    point2: [x, y] sobre entity2, del lado que se conserva; vacío = automático.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    vertex: id del punto extremo de exactamente dos curvas; excluye entity1/entity2.
    """
    _exigir_seleccion_esquina(vertex, entity1, entity2, "entity1 y entity2")
    expresion, valor = _valor_expr(sesion, radius)
    _cota_valida("radio", valor, "radius")
    p1, p2 = _opcional_xy(point1, "point1"), _opcional_xy(point2, "point2")

    def empalmar(b):
        a, c, xy1, xy2 = entity1, entity2, p1, p2
        if vertex is not None:
            (a, c), (xy1, xy2) = b._esquina_por_vertice(vertex, ("linea", "arco"))
        for k, que in ((a, "entity1"), (c, "entity2")):
            _curva(b, k, ("linea", "arco", "circulo"), que)
        if a == c:
            raise ErrorBoceto("Elegí dos curvas distintas.")
        arco = b.empalme(a, c, valor, xy1, xy2, expresion, vertice=vertex)
        aviso = aviso_radio_empalme(valor, b.radio(arco))
        if aviso:
            sesion.avisar(aviso)
    return _dibujar(sesion, sketch, empalmar, desde_solver=True, sin_conflicto="El empalme")


@herramienta("sketch_chamfer", "boceto",
             "Chaflán de boceto (Fusion: Chaflán en el boceto) entre dos líneas: de distancias iguales (distance), de "
             "dos distancias (distance y distance2) o de distancia y ángulo (distance y angle). Recorta las líneas, "
             "agrega la línea y sus cotas paramétricas. Admite vertex en lugar de las líneas.",
             modifica=True)
def sketch_chamfer(sesion, distance: Expr, line1: int | None = None, line2: int | None = None, distance2: Expr | None = None,
                   angle: Expr | None = None, point1: list[float] | None = None, point2: list[float] | None = None,
                   sketch: str | None = None, vertex: int | None = None):
    """
    line1: id de la primera línea.
    line2: id de la segunda línea.
    distance: distancia del chaflán sobre line1 (y sobre line2 si no hay distance2 ni angle), en mm o expresión.
    distance2: distancia sobre line2 (chaflán de dos distancias); vacío = igual a distance.
    angle: ángulo en grados del chaflán respecto de line1 (chaflán de distancia y ángulo); no va con distance2.
    point1: [x, y] sobre line1, del lado que se conserva; vacío = automático.
    point2: [x, y] sobre line2, del lado que se conserva; vacío = automático.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    vertex: id del punto extremo de exactamente dos líneas; excluye line1/line2.
    """
    _exigir_seleccion_esquina(vertex, line1, line2, "line1 y line2")
    if distance2 is not None and angle is not None:
        raise error("INVALID_ARGUMENTS", "Pasá distance2 (dos distancias) o angle (distancia y ángulo), no los dos.")
    expresion, d1 = _valor_expr(sesion, distance)
    _cota_valida("distancia", d1, "distance")
    expr2, d2 = (None, None) if distance2 is None else _valor_expr(sesion, distance2)
    if d2 is not None:
        _cota_valida("distancia", d2, "distance2")
    expr_ang, ang = (None, None) if angle is None else _valor_expr(sesion, angle, ANGULO)
    if ang is not None and not 0 < ang < 180:
        raise error("INVALID_DIMENSION", f"angle tiene que estar entre 0 y 180 grados (llegó {ang:g}).")
    p1, p2 = _opcional_xy(point1, "point1"), _opcional_xy(point2, "point2")

    def chaflan(b):
        a, c, xy1, xy2 = line1, line2, p1, p2
        if vertex is not None:
            (a, c), (xy1, xy2) = b._esquina_por_vertice(vertex, ("linea",))
        for k, que in ((a, "line1"), (c, "line2")):
            _curva(b, k, ("linea",), que)
        if a == c:
            raise ErrorBoceto("Elegí dos líneas distintas.")
        b.chaflan(a, c, d1, d2, ang, xy1, xy2, expresion, expr2 or expr_ang)
    return _dibujar(sesion, sketch, chaflan, desde_solver=True, sin_conflicto="El chaflán")


@herramienta("trim_sketch_curve", "boceto",
             "Recortar, alargar o partir una curva del boceto (Fusion: Recortar / Alargar / Partir). (x, y) es el "
             "lugar del clic, sobre la curva o cerca: trim quita el tramo de la curva que contiene ese punto, hasta los "
             "cruces más cercanos (si no cruza nada, borra la curva entera); extend lleva el extremo más cercano de una "
             "línea, un arco o una spline abierta hasta la próxima curva; break la parte en los cruces más cercanos "
             "(el punto, sobre la curva).",
             modifica=True)
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
    if mode != "trim":
        # P-69: alargar y partir validan como extend_sketch_curve y split_sketch_curve (el punto sobre la curva y
        # el conflicto del boceto). El import es local porque herramientas_boceto_extra importa de este módulo.
        from .herramientas_boceto_extra import _editar_curva
        r = _editar_curva(sesion, sketch, entity, (x, y), partir=mode == "break")
        r["mode"] = mode
        return r
    hecho = {}

    def modificar(b):
        _curva(b, entity)
        hecho["queda"] = b.recortar(entity, (x, y))
    r = _dibujar(sesion, sketch, modificar, desde_solver=True, sin_conflicto="El recorte")
    r["mode"] = mode
    r["deleted"] = hecho["queda"] is None
    return r


@herramienta("offset_sketch_curves", "boceto",
             "Desfase de boceto (Fusion: Desfase): copia paralela de la CADENA de líneas y arcos unida a entity (o de "
             "un círculo), con las esquinas resueltas, la restricción de desfase y su cota (paramétrico: si la cadena "
             "cambia, el desfase la sigue; si se borra la cota, la relación queda y la distancia se libera, también en "
             "splines y elipses). Por defecto una cadena cerrada crece hacia afuera y una abierta va a la "
             "izquierda de su recorrido; distance negativa va al lado contrario (la cota queda positiva) y side_x/side_y "
             "eligen el lado con un punto (la positiva va hacia él). Si el desfase deja un radio o un segmento en cero "
             "o al revés (p. ej. -30 en un círculo de radio 30), falla con INVALID_GEOMETRY y dice cuál. direction=two: "
             "distance y distance2 llevan signo sobre la MISMA normal, como Fusion (20 y -10 en un círculo: una copia a "
             "20 afuera y otra a 10 adentro); una de las dos puede ser 0 y entonces no se crea esa copia. "
             "direction=symmetric, distance a los dos lados con las dos cotas ligadas (editar una mueve la otra). "
             "chain=false desfasa solo la curva entity (Fusion sin Selección de cadena). match_topology=true (Fusion: Match Topology) limita la distancia para que el desfase "
             "conserve la topología de la curva madre (ningún segmento desaparece) y avisa la distancia usada. "
             "ellipse_result=ellipse (solo con una elipse entera): da otra elipse concéntrica de semiejes a±d y b±d "
             "(Fusion, al elegirla cerca de un eje; la distancia varía alrededor) y la deja atada con la restricción y "
             "la cota de desfase; con oval (por defecto) es la curva a distancia constante. Con "
             "profile (índice del perfil, el de get_sketch/extrusiones) en vez de entity se desfasa el perfil entero "
             "(Fusion acepta una curva, una cadena o un perfil): su contorno exterior y los de sus huecos, de modo que "
             "la región crezca con una distancia positiva. Una "
             "spline, una elipse o un arco de elipse dan una spline libre (sin asociación). Para "
             "soltar la asociación: release_offset. Para letras o cualquier contorno (sin parámetros): "
             "offset_profiles.", modifica=True)
def offset_sketch_curves(sesion, distance: Expr, entity: int | None = None, side_x: float | None = None,
                         side_y: float | None = None, sketch: str | None = None,
                         direction: Literal["one", "two", "symmetric"] = "one", distance2: Expr | None = None,
                         match_topology: bool = False, chain: bool = True, profile: int | None = None,
                         ellipse_result: Literal["oval", "ellipse"] = "oval"):
    """
    entity: id de una curva de la cadena (línea o arco), de un círculo, elipse o spline; vacío si se pasa profile.
    distance: separación en mm, número o expresión con parámetros; negativa = al lado contrario.
    side_x: x de un punto del lado donde va el desfase; vacío = el lado por defecto.
    side_y: y de ese punto.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    direction: one (un lado), two (distance y distance2, cada una con su signo sobre la misma normal) o symmetric (distance a los dos lados).
    distance2: segunda distancia con direction=two (obligatoria en ese caso): positiva = el mismo lado que distance positiva, negativa = el otro; 0 = sin segunda copia.
    match_topology: true = si la distancia haría desaparecer un segmento (o anular un radio), se usa la mayor que conserva la topología, como número fijo, y se avisa.
    chain: true = se desfasa toda la cadena conectada a entity (como Selección de cadena de Fusion); false = solo esa curva.
    profile: índice de un perfil (región cerrada) del boceto: se desfasan todos sus contornos; se pasa en vez de entity y side_x/side_y no valen.
    ellipse_result: oval = curva a distancia constante (por defecto); ellipse = otra elipse de semiejes a±d y b±d (solo si entity es una elipse entera).
    """
    _exigir_finitos(locals())
    if (entity is None) == (profile is None):
        raise error("INVALID_ARGUMENTS", "Pasá entity (una curva) o profile (un perfil), uno de los dos.")
    if profile is not None and side_x is not None:
        raise error("INVALID_ARGUMENTS", "Con profile el lado lo da el signo de distance: no pases side_x ni side_y.")
    firma = None
    if profile is not None:
        op = op_boceto(sesion, sketch)
        firma = seleccionar_perfiles(boceto_resuelto(sesion, op), op, profile)[0].firma
    if (side_x is None) != (side_y is None):
        raise error("INVALID_ARGUMENTS", "Pasá side_x y side_y juntos, o ninguno de los dos.")
    if direction == "two" and distance2 is None:
        raise error("INVALID_ARGUMENTS", "direction=two necesita distance2 (la separación del segundo lado).")
    lado = None if side_x is None else (float(side_x), float(side_y))

    def firmada(d):
        """(texto sin signo para la cota, valor con signo) de una distancia (con direction=two, 0 = sin esa copia)."""
        expresion, valor = _valor_expr(sesion, d)
        if valor != 0 or direction != "two":
            _cota_valida("desfase", abs(valor), "distance")
        if not isinstance(d, str):
            expresion = repr(abs(valor))
        else:
            expresion = expresion_sin_signo(expresion, valor, lambda t: _valor_expr(sesion, t)[1])
        return expresion, valor
    expresion, valor = firmada(distance)
    expresion2, valor2 = firmada(distance2) if direction == "two" else (None, None)

    def desfasar(b):
        modo = "dos" if direction == "two" else "simetrico" if direction == "symmetric" else "un"
        elipse = ellipse_result == "ellipse"
        if firma is not None:
            _nuevos, avisos = b.desfasar_perfil(firma, valor, expresion=expresion, direccion=modo, distancia2=valor2,
                                                expresion2=expresion2, topologia=match_topology)
        else:
            _curva(b, entity, ("linea", "arco", "circulo", "elipse", "arco_elipse", "spline"))
            if elipse and b.curvas[entity].tipo != "elipse":
                raise error("INVALID_ARGUMENTS", "ellipse_result=ellipse solo vale con una elipse entera.")
            _nuevos, avisos = b.desfasar(entity, valor, lado, expresion, modo, valor2, expresion2,
                                         topologia=match_topology, cadena=chain, elipse=elipse)
        for aviso in avisos:
            sesion.avisar(aviso)
    return _dibujar(sesion, sketch, desfasar, desde_solver=True, sin_conflicto="El desfase")


@herramienta("release_offset", "boceto",
             "Suelta la asociación de un desfase (Fusion: borrar el glifo de desfase): la copia deja de seguir a la "
             "original, pero las curvas quedan. Con keep_dimension=true se conserva la cota del desfase.",
             modifica=True)
def release_offset(sesion, entity: int, keep_dimension: bool = False, sketch: str | None = None):
    """
    entity: id de la curva original o de su copia desfasada (get_sketch).
    keep_dimension: true = deja la cota de desfase; false = la borra junto con la asociación.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    def soltar(b):
        _curva(b, entity)
        b.soltar_desfase(entity, keep_dimension)
    return _dibujar(sesion, sketch, soltar, desde_solver=True, sin_conflicto="Soltar el desfase")


@herramienta("edit_sketch_spline", "boceto",
             "Edita una spline ya dibujada (Fusion: manijas, Open/Close Spline, Insert Fit/Control Point y Change "
             "Spline Degree). Acciones: activate_handle (manija de tangente en un punto de ajuste: una línea de "
             "construcción que se puede acotar; con angle, length y curvature), edit_handle, deactivate_handle, "
             "open / close (solo la de ajuste), insert_point (punto de ajuste sobre la curva o punto de control sin "
             "cambiar la forma, cerca de x, y) y set_degree (3 o 5, solo la de puntos de control). Las manijas van "
             "en splines de ajuste abiertas. El peine de curvatura: get_spline_curvature.", modifica=True)
def edit_sketch_spline(sesion, entity: int,
                       action: Literal["activate_handle", "edit_handle", "deactivate_handle", "open", "close",
                                       "insert_point", "set_degree"],
                       point: int | None = None, angle: float | None = None, length: float | None = None,
                       curvature: float | None = None, x: float | None = None, y: float | None = None,
                       degree: int | None = None, sketch: str | None = None):
    """
    entity: id de la spline (get_sketch).
    action: qué hacer (ver la descripción de la herramienta).
    point: id del punto de ajuste de la manija (vertices / points de get_sketch); para las acciones de manija.
    angle: dirección de la tangente en grados (antihoraria desde +x); vacío = la tangente actual.
    length: largo de la manija en mm (más largo = la curva sigue más esa dirección); vacío = el natural.
    curvature: curvatura en ese punto, en 1/mm (1 / radio; positiva gira a la izquierda); vacío = sin cambio (al activar: libre).
    x: x del punto a insertar (insert_point), en mm; se usa el punto de la curva más cercano.
    y: y del punto a insertar (insert_point), en mm.
    degree: grado nuevo de la spline de puntos de control (3 o 5) para set_degree.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos({k: v for k, v in (("angle", angle), ("length", length), ("curvature", curvature), ("x", x),
                                       ("y", y)) if v is not None})
    manija = action in ("activate_handle", "edit_handle", "deactivate_handle")
    if manija and point is None:
        raise error("INVALID_ARGUMENTS", f"{action} necesita point (id del punto de ajuste).")
    if action == "insert_point" and (x is None or y is None):
        raise error("INVALID_ARGUMENTS", "insert_point necesita x e y.")
    if action == "set_degree" and degree is None:
        raise error("INVALID_ARGUMENTS", "set_degree necesita degree (3 o 5).")

    def editar(b):
        _curva(b, entity, ("spline",))
        if action == "activate_handle":
            b.activar_manija(entity, point, angle, length, curvature)
        elif action == "edit_handle":
            b.editar_manija(entity, point, angle, length, curvature)
        elif action == "deactivate_handle":
            b.desactivar_manija(entity, point)
        elif action in ("open", "close"):
            b.cerrar_spline(entity, action == "close")
        elif action == "insert_point":
            b.insertar_punto_spline(entity, (x, y))
        else:
            b.cambiar_grado_spline(entity, degree)
    return _dibujar(sesion, sketch, editar, desde_solver=True)


@herramienta("get_spline_curvature", "boceto",
             "Peine de curvatura de una curva del boceto (Fusion: Toggle Curvature Display): curvatura con signo "
             "en muestras repartidas por el parámetro, con el punto y la punta de cada púa (salen del lado opuesto "
             "al centro de curvatura, con largo curvatura × factor). No cambia el documento.")
def get_spline_curvature(sesion, entity: int, density: int = 30, scale: float = 1.0, sketch: str | None = None):
    """
    entity: id de la curva (spline, cónica, arco, círculo, elipse o línea) en get_sketch.
    density: cuántas púas (2 a 200).
    scale: escala del largo de las púas (1 = la más larga mide el 20 % del tamaño de la curva).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    if not 2 <= int(density) <= 200:
        raise error("INVALID_ARGUMENTS", "density va de 2 a 200.")
    _exigir_finitos({"scale": scale})
    br = boceto_resuelto(sesion, op_boceto(sesion, sketch))
    if br is None:
        raise error("OPERATION_FAILED", "El boceto no se pudo calcular.")
    c = _curva(br.boceto, entity, ("spline", "conica", "arco", "circulo", "elipse", "arco_elipse", "linea"))
    puas, factor = peine_curvatura(br.boceto.primitivas(c.id)[0], int(density), float(scale))
    ks = [abs(k) for _p, k, _t in puas]
    return {"samples": [{"point": [_r(v) for v in p], "curvature": _r(k), "tip": [_r(v) for v in t]}
                        for p, k, t in puas],
            "max_curvature": _r(max(ks)), "min_radius": None if max(ks) < 1e-12 else _r(1 / max(ks)),
            "factor": _r(factor)}


@herramienta("copy_sketch_entities", "boceto",
             "Copia y pega elementos entre bocetos (Fusion: Copiar y Pegar en el boceto): copia las curvas y puntos de "
             "source_sketch en sketch (el último boceto por defecto; puede ser el mismo), corridos (dx, dy), con las "
             "restricciones y cotas que quedan enteras dentro de la selección. Lo pegado es geometría normal y "
             "nueva: no queda asociada al original. Para copiar dentro del mismo boceto con vínculo: transform_sketch "
             "con copy.", modifica=True)
def copy_sketch_entities(sesion, entities: list[int], source_sketch: str, sketch: str | None = None,
                         dx: float = 0.0, dy: float = 0.0):
    """
    entities: ids de las curvas o puntos de source_sketch a copiar (get_sketch).
    source_sketch: id o nombre del boceto de origen.
    sketch: id o nombre del boceto de destino; vacío = el último boceto del timeline.
    dx: corrimiento en x del pegado, en mm; 0 = en el mismo lugar.
    dy: corrimiento en y del pegado, en mm.
    """
    _exigir_finitos(locals())
    origen = op_boceto(sesion, source_sketch)
    fuente = origen.copia().boceto
    actualizar_alturas_texto(fuente, boceto_resuelto(sesion, origen))
    _sincronizar_con_solver(sesion, origen, fuente)
    _exigir_seleccion(fuente, entities)

    def pegar(b):
        b.pegar_de(fuente, list(entities), dx, dy)
    return _dibujar(sesion, sketch, pegar, desde_solver=True)


# ---------------------------------------------------------------- crear: simetría y patrones
def _exigir_seleccion(b, entities):
    if not entities:
        raise error("INVALID_ARGUMENTS", "entities está vacía: pasá ids de curvas o puntos (get_sketch).")
    _exigir_entidades(b, entities)


@herramienta("mirror_sketch", "boceto",
             "Simetría de boceto (Fusion: Simetría / Mirror): CREA la copia espejada de curvas y puntos respecto de una "
             "línea del boceto (recta, también de construcción) o un eje del origen (axis=-1 el X, -2 el Y, como Fusion) "
             "y la deja con restricciones "
             "de simetría: si la geometría original cambia, la copia la sigue. No es la restricción de simetría "
             "(add_constraint type=symmetry), que solo acomoda geometría que ya existe. Lo que está sobre el eje se "
             "comparte; lo que ya es su propio reflejo (una línea sobre el eje, un círculo centrado en él) no se copia, "
             "y el eje puede estar entre entities. Los textos no se espejan (para eso: transform_sketch o edit_text).",
             modifica=True)
def mirror_sketch(sesion, entities: list[int], axis: int, sketch: str | None = None):
    """
    entities: ids de las curvas o puntos a reflejar (get_sketch).
    axis: id de la línea de simetría (recta, puede ser de construcción o una de entities), o -1 / -2 para el eje X / Y del origen.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    textos = []

    def reflejar(b):
        _exigir_seleccion(b, entities)
        if axis not in (b.EJE_X, b.EJE_Y):
            _curva(b, axis, ("linea",), "el eje")
        textos.extend(i for i in entities if isinstance(b.curvas.get(i), Texto))
        b.simetria(list(entities), axis)
    r = _dibujar(sesion, sketch, reflejar, desde_solver=True)
    if textos:
        sesion.avisar(f"Los textos {textos} no se espejan con simetría: usá transform_sketch o edit_text (flip_h).")
    return r


def _exigir_patron(tipo, params):
    """Las reglas de la ventana (`Boceto.validar_patron`), con el tipo de error de las herramientas."""
    try:
        Boceto.validar_patron(tipo, params)
    except ErrorBoceto as e:
        raise error("INVALID_ARGUMENTS", str(e), "La cantidad cuenta el original; la distancia negativa invierte el "
                    "sentido; el ángulo total va de -360 a 360 (negativo = horario).") from e


def _exigir_tamano_patron(b, entities, copias, sin=()):
    try:
        b.exigir_tamano_patron(entities, copias, sin)
    except ErrorBoceto as e:
        raise error("INVALID_ARGUMENTS", str(e)) from e


def _exigir_supresion(suppress):
    if suppress is not None and any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in suppress):
        raise error("INVALID_ARGUMENTS", "suppress lleva índices de copia enteros desde 0 (get_sketch › patterns).")


def _informar_patron(r, b):
    """Agrega al informe de edición el patrón recién hecho o editado: su id y las copias por índice."""
    registro = next(x for x in b.patrones if x["id"] == b.ultimo_patron)
    r["pattern"] = registro["id"]
    r["instances"] = {n: ids for n, ids in registro["copias"].items()}
    return r


@herramienta("sketch_rectangular_pattern", "boceto",
             "Patrón rectangular de boceto (Fusion: Patrón rectangular en el boceto): copias de curvas y puntos en una "
             "o dos direcciones, atadas al original con la restricción de patrón (si el original cambia, las copias lo "
             "siguen). La dirección 1 sale del ángulo angle (o de la línea direction1_line) y la 2 de angle2 (por "
             "defecto perpendicular, +90°) o de direction2_line. Con spacing=extent la distancia es la total (de la "
             "primera a la última copia); con spacing la de cada paso. suppress omite copias por índice (get_sketch › "
             "patterns); después se edita con edit_sketch_pattern. Tope: 200 puntos copiados (copias × puntos de la "
             "selección; un rectángulo tiene 4) y 200 copias, para que el boceto no se vuelva lento: tope propio, la "
             "ayuda de Fusion no publica un máximo.",
             modifica=True)
def sketch_rectangular_pattern(sesion, entities: list[int], count1: int, distance1: Expr, count2: int = 1,
                               distance2: Expr = 0.0, angle: Expr = 0.0,
                               spacing: Literal["extent", "spacing"] = "extent", symmetric: bool = False,
                               sketch: str | None = None, angle2: Expr | None = None,
                               direction1_line: int | None = None, direction2_line: int | None = None,
                               suppress: list[int] | None = None, symmetric2: bool | None = None):
    """
    entities: ids de las curvas o puntos a repetir (get_sketch).
    count1: cantidad en la dirección 1, contando el original.
    distance1: mm o expresión en la dirección 1 (total o por paso según spacing; negativa = sentido contrario).
    count2: cantidad en la dirección 2 (1 = una sola fila).
    distance2: distancia en la dirección 2 (mm o expresión).
    angle: dirección 1 en grados o expresión respecto del eje x del boceto.
    spacing: extent (distancia total) o spacing (distancia entre copias).
    symmetric: true para repartir las copias a los dos lados del original (el original queda en el medio; con cantidad par, una copia más de un lado).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    symmetric2: lo mismo para la dirección 2; vacío = igual que symmetric.
    angle2: dirección 2 en grados o expresión respecto del eje x; vacío = angle + 90°.
    direction1_line: id de una línea del boceto que da la dirección 1 (de su inicio a su fin); pisa a angle.
    direction2_line: id de una línea del boceto que da la dirección 2; pisa a angle2.
    suppress: índices de las copias que no se crean (get_sketch › patterns las lista).
    """
    _exigir_finitos(locals())
    _exigir_supresion(suppress)
    expr1, distance1 = _valor_expr(sesion, distance1)
    expr2, distance2 = _valor_expr(sesion, distance2)
    expr_ang, angle = _valor_expr(sesion, angle, ANGULO)
    expr_ang2, angle2 = _valor_expr(sesion, f"({expr_ang}) + 90 deg" if angle2 is None else angle2, ANGULO)
    expresiones = {"distancia1": expr1, "distancia2": expr2, "angulo1": expr_ang, "angulo2": expr_ang2}
    a = math.radians(angle)
    a2 = math.radians(angle2)
    d1, d2 = (math.cos(a), math.sin(a)), (math.cos(a2), math.sin(a2))
    modo = "extension" if spacing == "extent" else "espaciado"
    _exigir_patron("rectangular", {"cantidad1": count1, "distancia1": distance1, "cantidad2": count2,
                                   "distancia2": distance2, "dir1": d1, "dir2": d2, "modo": modo,
                                   "linea1": direction1_line, "linea2": direction2_line})
    hecho = {}

    def repetir(b):
        _exigir_seleccion(b, entities)
        for linea in (direction1_line, direction2_line):
            if linea is not None:
                _curva(b, linea, ("linea",), "la dirección")
        _exigir_tamano_patron(b, entities, count1 * count2 - 1)
        b.patron_rectangular(list(entities), count1, distance1, count2, distance2, d1, d2, modo, symmetric,
                             direction1_line, direction2_line, suppress or (), symmetric2, expresiones)
        hecho["b"] = b
    r = _dibujar(sesion, sketch, repetir, desde_solver=True)
    return _informar_patron(r, hecho["b"])


@herramienta("sketch_circular_pattern", "boceto",
             "Patrón circular de boceto (Fusion: Patrón circular en el boceto): copias de curvas y puntos alrededor de "
             "un centro, atadas al original con la restricción de patrón. total_angle = 360 reparte la cantidad en la "
             "vuelta entera; otro ángulo pone la primera y la última copia en sus extremos. suppress omite copias por "
             "índice; después se edita con edit_sketch_pattern. Tope: 200 puntos copiados (copias × puntos de la "
             "selección; un círculo tiene 1) y 200 copias: tope propio, la ayuda de Fusion no publica un máximo.",
             modifica=True)
def sketch_circular_pattern(sesion, entities: list[int], count: int, center_x: float = 0.0, center_y: float = 0.0,
                            center_point: int | None = None, total_angle: Expr = 360.0, symmetric: bool = False,
                            sketch: str | None = None, suppress: list[int] | None = None):
    """
    entities: ids de las curvas o puntos a repetir (get_sketch).
    count: cantidad total, contando el original (2 o más).
    center_x: x del centro (mm), si no se da center_point.
    center_y: y del centro (mm).
    center_point: id de un punto del boceto que hace de centro (las copias lo siguen); pisa center_x/center_y.
    total_angle: ángulo total en grados o expresión (360 = vuelta entera; negativo = sentido horario).
    symmetric: true para repartir las copias a los dos lados del original (si total_angle no es 360).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    suppress: índices de las copias que no se crean (get_sketch › patterns las lista).
    """
    _exigir_finitos(locals())
    expresion, total_angle = _valor_expr(sesion, total_angle, ANGULO)
    _exigir_patron("circular", {"cantidad": count, "angulo_total": total_angle})
    _exigir_supresion(suppress)
    hecho = {}

    def repetir(b):
        _exigir_seleccion(b, entities)
        if center_point is not None and center_point not in b.puntos:
            raise error("ENTITY_NOT_FOUND", f"center_point {center_point} no es un punto del boceto.")
        centro = center_point if center_point is not None else (float(center_x), float(center_y))
        _exigir_tamano_patron(b, entities, count - 1, sin=(center_point,))
        b.patron_circular(list(entities), centro, count, total_angle, symmetric, suppress or (),
                          {"angulo_total": expresion})
        hecho["b"] = b
    r = _dibujar(sesion, sketch, repetir, desde_solver=True)
    return _informar_patron(r, hecho["b"])


@herramienta("edit_sketch_pattern", "boceto",
             "Edita un patrón de boceto ya hecho (Fusion: doble clic en el glifo del patrón): cantidades, distancias, "
             "direcciones, simetría y copias suprimidas. Regenera las copias: las restricciones y cotas puestas sobre "
             "una copia pasan a la copia nueva del mismo índice; las de copias que ya no existen se borran y se listan "
             "en lost_references (con aviso). pattern es el id que devolvió la herramienta que lo creó (o get_sketch › "
             "patterns). Los parámetros count1, distance1, count2, distance2, angle, angle2, spacing, "
             "direction1_line y direction2_line son de un patrón rectangular; count y total_angle, de uno circular. "
             "suppress reemplaza la lista de copias suprimidas ([] = ninguna).", modifica=True)
def edit_sketch_pattern(sesion, pattern: int, count1: int | None = None, distance1: Expr | None = None,
                        count2: int | None = None, distance2: Expr | None = None, angle: Expr | None = None,
                        angle2: Expr | None = None, spacing: Literal["extent", "spacing"] | None = None,
                        symmetric: bool | None = None, direction1_line: int | None = None,
                        direction2_line: int | None = None, count: int | None = None,
                        total_angle: Expr | None = None, suppress: list[int] | None = None,
                        sketch: str | None = None, symmetric2: bool | None = None, center_x: float | None = None,
                        center_y: float | None = None, center_point: int | None = None):
    """
    pattern: id del patrón (lo devuelve la herramienta que lo creó; get_sketch › patterns lo lista).
    count1: cantidad en la dirección 1 (rectangular).
    distance1: distancia en mm o expresión en la dirección 1 (rectangular).
    count2: cantidad en la dirección 2 (rectangular).
    distance2: distancia en mm o expresión en la dirección 2 (rectangular).
    angle: dirección 1 en grados o expresión (rectangular); sin angle2, la dirección 2 pasa a angle + 90°.
    angle2: dirección 2 en grados o expresión (rectangular).
    spacing: extent o spacing (rectangular).
    symmetric: repartir las copias a los dos lados del original.
    symmetric2: lo mismo para la dirección 2 (rectangular); vacío = no cambia.
    center_x: x del nuevo centro (mm, circular); hay que dar también center_y.
    center_y: y del nuevo centro (mm, circular).
    center_point: id de un punto del boceto que pasa a ser el centro (circular); pisa a center_x/center_y.
    direction1_line: id de una línea que da la dirección 1 (rectangular).
    direction2_line: id de una línea que da la dirección 2 (rectangular).
    count: cantidad total, contando el original (circular).
    total_angle: ángulo total en grados o expresión (circular).
    suppress: índices de copias suprimidas; reemplaza la lista actual ([] = ninguna).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    _exigir_finitos(locals())
    _exigir_supresion(suppress)
    hecho = {}

    def editar(b):
        b.evaluar_patrones(lambda v, k: _valor_expr(sesion, v, k)[1])
        registro = next((r for r in b.patrones if r["id"] == pattern), None)
        if registro is None:
            hay = ", ".join(str(r["id"]) for r in b.patrones) or "ninguno"
            raise error("ENTITY_NOT_FOUND", f"El boceto no tiene el patrón {pattern!r} (patrones: {hay}).")
        cambios = {}
        p = registro["params"]
        expresiones = dict(p.get("expresiones", {}))
        if registro["tipo"] == "rectangular":
            if any(v is not None for v in (count, total_angle)):
                raise error("INVALID_ARGUMENTS", "count y total_angle son de un patrón circular: usá count1 y count2.")
            n1, n2 = p["cantidad1"] if count1 is None else count1, p["cantidad2"] if count2 is None else count2
            if any(v is not None for v in (center_x, center_y, center_point)):
                raise error("INVALID_ARGUMENTS", "El centro es de un patrón circular.")
            for linea in (direction1_line, direction2_line):
                if linea is not None:
                    _curva(b, linea, ("linea",), "la dirección")
            cambios = {"cantidad1": n1, "cantidad2": n2}
            if distance1 is not None:
                expresiones["distancia1"], cambios["distancia1"] = _valor_expr(sesion, distance1)
            if distance2 is not None:
                expresiones["distancia2"], cambios["distancia2"] = _valor_expr(sesion, distance2)
            if spacing is not None:
                cambios["modo"] = "extension" if spacing == "extent" else "espaciado"
            if symmetric is not None:
                cambios["simetrico"] = symmetric
            if symmetric2 is not None:
                cambios["simetrico2"] = symmetric2
            if angle is not None:
                expresiones["angulo1"], valor = _valor_expr(sesion, angle, ANGULO)
                a = math.radians(valor)
                cambios.update(dir1=[math.cos(a), math.sin(a)], linea1=None)
                if angle2 is None and direction2_line is None:
                    expresiones["angulo2"] = f"({expresiones['angulo1']}) + 90 deg"
                    cambios.update(dir2=[-math.sin(a), math.cos(a)], linea2=None)
            if angle2 is not None:
                expresiones["angulo2"], valor = _valor_expr(sesion, angle2, ANGULO)
                a2 = math.radians(valor)
                cambios.update(dir2=[math.cos(a2), math.sin(a2)], linea2=None)
            if direction1_line is not None:
                cambios["linea1"] = direction1_line
            if direction2_line is not None:
                cambios["linea2"] = direction2_line
            _exigir_patron("rectangular", {**p, **cambios})
            _exigir_tamano_patron(b, registro["ids"], n1 * n2 - 1)
        else:
            if any(v is not None for v in (count1, distance1, count2, distance2, angle, angle2, spacing,
                                           direction1_line, direction2_line, symmetric2)):
                raise error("INVALID_ARGUMENTS", "Ese parámetro es de un patrón rectangular: acá van count y total_angle.")
            n, total = p["cantidad"] if count is None else count, p["angulo_total"] if total_angle is None else total_angle
            if total_angle is not None:
                expresiones["angulo_total"], total = _valor_expr(sesion, total_angle, ANGULO)
            cambios = {"cantidad": n, "angulo_total": total}
            if symmetric is not None:
                cambios["simetrico"] = symmetric
            if center_point is not None:
                if center_point not in b.puntos:
                    raise error("ENTITY_NOT_FOUND", f"center_point {center_point} no es un punto del boceto.")
                cambios["centro"] = int(center_point)
            elif center_x is not None or center_y is not None:
                if center_x is None or center_y is None:
                    raise error("INVALID_ARGUMENTS", "Para mover el centro dá center_x y center_y juntos.")
                cambios["centro"] = [float(center_x), float(center_y)]
            _exigir_patron("circular", {**p, **cambios})
            centro = cambios.get("centro", p["centro"])
            _exigir_tamano_patron(b, registro["ids"], n - 1, sin=(centro,) if isinstance(centro, int) else ())
        if suppress is not None:
            cambios["suprimidos"] = suppress
        cambios["expresiones"] = expresiones
        hecho["perdidas"] = b.editar_patron(pattern, **cambios)
        hecho["b"] = b
    r = _dibujar(sesion, sketch, editar, desde_solver=True)
    if hecho["perdidas"]:
        sesion.avisar("Se borraron porque su copia ya no existe: " + ", ".join(hecho["perdidas"]) + ".")
    r["lost_references"] = hecho["perdidas"]
    return _informar_patron(r, hecho["b"])


# ---------------------------------------------------------------- proyectar, tipo de línea, cotas y AutoConstrain
_REFERENCIAS_PROYECTABLES = {"plano", "eje", "punto", "curva_boceto", "punto_boceto"}


def _proyectar_seleccion(sesion, plano, mode, edges, faces, bodies, vertices, references, body, giro=None):
    """(primitivas, puntos, referencias, infinitas) de lo elegido proyectado (o intersecado) sobre `plano`: aristas,
    caras, cuerpos y vértices del modelo, y `references` (planos, ejes y puntos de trabajo, curvas y puntos de otro
    boceto). infinitas = {índice: alcance del modelo} de las líneas de ejes y trazas (`Boceto.derivar_proyeccion`)."""
    from .herramientas_construccion import _referencia
    elegidos = sl.elegir(sesion, edges, "arista", body, permitir_vacio=True)
    elegidos += sl.elegir(sesion, faces, "cara", body, permitir_vacio=True)
    entidades = [ent.Entidad("forma", forma=e.sub) for _c, e in elegidos]
    refs = [sl.referencia(c, e) for c, e in elegidos]
    for punto in vertices or []:
        if not sl.es_punto3(punto):
            raise error("INVALID_ARGUMENTS", f"Cada vértice va como [x, y, z] con números finitos: llegó {punto!r}.")
        _c, ref, v = sl.vertice_cercano(sesion, punto, body)
        entidades.append(ent.Entidad("vertice", forma=v))
        refs.append(ref)
    for ref in bodies or []:
        c = sesion.cuerpo(ref)
        if getattr(c, "tipo", "solido") == "malla":
            raise error("UNSUPPORTED_BODY_TYPE", f"«{sesion.nombre_cuerpo(c)}» es una malla: no se proyecta.")
        entidades.append(ent.Entidad("cuerpo", forma=c.forma, cuerpo=c.id))
        refs.append({"tipo": "cuerpo", "cuerpo": c.id})
    for valor in references or []:
        ref = _referencia(sesion, valor, _REFERENCIAS_PROYECTABLES, body)
        entidades.append(ent.resolver(ref, sesion.doc.estado_final))
        refs.append(ref)
    prims, puntos, infinitas = [], [], {}
    for e in entidades:
        p, q = ent.proyectar_entidad(e, plano, mode, giro)
        if giro is None and e.forma is None and e.punto is None and (e.eje is not None or e.plano is not None):
            for k, prim in enumerate(p, start=len(prims)):
                infinitas[str(k)] = _alcance_modelo(sesion, plano, prim)
        prims += p
        puntos += q
    return prims, puntos, refs, infinitas


def _alcance_modelo(sesion, plano, linea):
    """Distancia (mm) del punto medio de `linea` a la esquina más lejana de la caja de los cuerpos, vista en el
    plano del boceto; 0 sin cuerpos. shortcut: se mide al proyectar; si el modelo crece, el eje no lo sigue (sí la
    geometría del boceto) hasta proyectarlo de nuevo."""
    m = ((linea[2][0] + linea[3][0]) / 2, (linea[2][1] + linea[3][1]) / 2)
    alcance = 0.0
    for c in sesion.doc.estado_final.cuerpos.values():
        forma = getattr(c, "forma", None) if getattr(c, "tipo", "solido") != "malla" else None
        caja = geo.caja_envolvente(forma) if forma is not None else None
        if caja:
            (x0, y0, z0), (x1, y1, z1) = caja
            alcance = max([alcance] + [math.dist(m, plano.a_uv((x, y, z)))
                                       for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
    return alcance


@herramienta("project_to_sketch", "boceto",
             "Proyecta aristas, caras, cuerpos, planos, ejes y puntos de trabajo, o curvas y puntos de otro boceto, "
             "sobre el plano del boceto (Fusion: Proyectar) o agrega donde cortan ese plano (mode=intersect; "
             "Fusion: Intersecar). Un cuerpo entero (bodies) se proyecta como su silueta: el contorno cerrado de lo "
             "que tapa sobre el plano, aunque sea curvo y se vea de costado. La geometría queda proyectada: fija (violeta en la interfaz), sirve para "
             "restricciones, cotas y perfiles, y con link=true (por defecto) sigue al modelo si después cambia; con "
             "link=false queda congelada. Si el vínculo se pierde: manage_lost_projections; para soltarlo: "
             "break_projection_link. Un eje o la traza de un plano (infinitos) se dibujan como una línea que llega "
             "al 110 % de lo más lejano entre el modelo y la geometría del boceto, y crece con el boceto al "
             "recalcular (±100 mm si no hay nada alrededor). "
             "edges y faces aceptan selectores (con body si hay varios cuerpos) o ids de find_edges / find_faces; "
             "vertices, las coordenadas [x, y, z] de vértices del modelo (proyecta o interseca puntos). "
             "Lo que coincide con geometría ya proyectada no se duplica: se reutiliza, y si era el contorno automático de "
             "la cara queda visible con la referencia elegida. result dice qué pasó: created (hay geometría nueva), reused "
             "(solo se reutilizó; reused lista sus ids) o unchanged (ya estaba: no hay paso de deshacer).",
             modifica=True)
def project_to_sketch(sesion, edges: list[str] | str | None = None, faces: list[str] | str | None = None,
                      bodies: list[str] | None = None, mode: Literal["project", "intersect"] = "project",
                      body: str | None = None, sketch: str | None = None, construction: bool = False,
                      vertices: list[list[float]] | None = None, link: bool = True,
                      references: list[str | dict] | None = None):
    """
    edges: aristas a proyectar: selector ('|Z', '%CIRCLE and >Z') o ids ('Cuerpo1/E3'); vacío = ninguna.
    faces: caras a proyectar (su contorno): selector o ids ('Cuerpo1/F6'); vacío = ninguna.
    bodies: ids o nombres de cuerpos enteros; vacío = ninguno. Con mode=project cada cuerpo da su silueta: el contorno cerrado de lo que tapa sobre el plano, listo para perfil (Fusion: filtro Bodies).
    mode: project (proyección ortogonal) o intersect (corte con el plano del boceto).
    body: cuerpo donde se evalúan los selectores de edges y faces; vacío = el único cuerpo.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    construction: true = la geometría proyectada queda como línea de construcción (no forma perfiles).
    vertices: vértices del modelo por sus coordenadas [[x, y, z], …] (a menos de 0,001 mm de un vértice; con body, solo los de ese cuerpo): se proyectan (o intersecan) como puntos del boceto.
    link: true = asociativa (sigue al modelo); false = congelada, sin vínculo.
    references: planos ("XY", id o nombre), ejes ("X", id o nombre), puntos de trabajo ("O", id o nombre), y curvas o puntos de otro boceto ({"sketch": "Boceto1", "curve": 3} o {"sketch": …, "point": 2}).
    """
    op, br = boceto_activo(sesion, sketch, derivados=False)
    modo = "silueta" if mode == "project" and bodies else mode      # un cuerpo da su silueta cerrada (B-119)
    prims, puntos, refs, infinitas = _proyectar_seleccion(sesion, br.plano, modo, edges, faces, bodies, vertices,
                                                          references, body)
    if not refs:
        raise error("INVALID_ARGUMENTS", "Elegí qué proyectar: edges, faces, vertices, bodies o references.")
    if not prims and not puntos:
        raise error("INVALID_GEOMETRY", "Eso no deja nada sobre el plano del boceto"
                    + (": no corta su plano." if mode == "intersect" else "."))
    datos = {"modo": modo, "refs": refs, "infinitas": infinitas}
    r, ids = _sumar_proyecciones(sesion, op, [(prims, puntos, construction, link, datos)])
    r["mode"] = "silhouette" if modo == "silueta" else mode
    r["projection"] = ids[0]
    return r


def _sumar_proyecciones(sesion, op, tandas):
    """Agrega `tandas` = [(primitivas, puntos, construcción, vínculo, datos)] en un paso. Devuelve el informe, con `result`
    (created, reused o unchanged: todo ya estaba, sin paso de deshacer ni recálculo) y `reused`, y el id de cada proyección."""
    b = op.boceto
    plan = b.simular_proyecciones([(p if link else b.derivar_proyeccion(datos, p), q, c, datos if link else None)
                                   for p, q, c, link, datos in tandas])
    if not plan["cambia"]:
        sesion.avisar("Eso ya estaba proyectado: el boceto no cambió.")
        return {"sketch": _paso(op), "result": "unchanged", "entities": [], "points": [], "reused": plan["reusadas"]}, \
            [None] * len(tandas)
    ids = []
    r = _dibujar(sesion, op.id, lambda copia: ids.extend(_sumar_proyeccion(copia, *t) for t in tandas), desde_solver=True)
    r["result"] = "created" if plan["curvas"] or plan["puntos"] else "reused"
    r["reused"] = plan["reusadas"]
    return r, ids


def _sumar_proyeccion(b, prims, puntos, construccion, link, datos):
    """Agrega una proyección al boceto: con `link`, asociativa (devuelve su id); sin vínculo igual se recortan los
    ejes y se saca el contorno (`Boceto.derivar_proyeccion`) y devuelve None."""
    if link:
        antes = len(b.proyecciones)
        b.agregar_proyeccion(prims, puntos, construccion, origen=datos)
        return b.proyecciones[-1]["id"] if len(b.proyecciones) > antes else None    # todo repetido: no queda nada
    b.agregar_proyeccion(b.derivar_proyeccion(datos, prims), puntos, construccion)
    return None


@herramienta("project_spun_profile", "boceto",
             "Proyecta el perfil giratorio de la geometría (Fusion: Proyectar › Spun Profile): gira aristas, caras, "
             "cuerpos o vértices alrededor de un eje y deja su perfil sobre el plano del boceto, para referenciarlo en el "
             "boceto o en operaciones de revolución y torneado. El eje se proyecta en el plano; cada punto va a su "
             "posición a lo largo del eje y su distancia a él (hacia +u del boceto, o al otro lado con flip). Las curvas se aproximan "
             "con segmentos a tolerance mm. Por defecto queda solo el contorno exterior (la silueta de radio máximo y "
             "los frentes de sus extremos, sin las aristas que caen dentro); outer_contour=false gira todas las "
             "aristas. project_axis=true (Fusion: Project Axis) proyecta también el eje como línea, con vínculo "
             "(axis_projection). Con link=true (por defecto) sigue al modelo, igual que project_to_sketch "
             "(break_projection_link, manage_lost_projections, incluido relink). result dice qué pasó, como en "
             "project_to_sketch: lo repetido da unchanged y no deja paso de deshacer.", modifica=True)
def project_spun_profile(sesion, axis: str | dict, edges: list[str] | str | None = None,
                         faces: list[str] | str | None = None, bodies: list[str] | None = None,
                         vertices: list[list[float]] | None = None, tolerance: float = 0.1, flip: bool = False,
                         link: bool = True, construction: bool = False, body: str | None = None,
                         sketch: str | None = None, outer_contour: bool = True, project_axis: bool = False):
    """
    axis: eje de giro: "X", "Y", "Z", un eje de construcción (id o nombre), una arista recta, una línea de boceto ({"sketch", "curve"}) o una cara cilíndrica.
    edges: aristas a girar: selector o ids ('Cuerpo1/E3').
    faces: caras a girar: selector o ids ('Cuerpo1/F6').
    bodies: ids o nombres de cuerpos enteros.
    vertices: vértices del modelo por sus coordenadas [[x, y, z], …].
    tolerance: distancia máxima en mm entre la curva y los segmentos del perfil (mayor que cero).
    flip: true pone el perfil del otro lado del eje.
    link: true = asociativo (sigue al modelo); false = congelado.
    construction: true = el perfil queda como líneas de construcción.
    body: cuerpo donde se evalúan los selectores; vacío = el único cuerpo.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    outer_contour: true = solo el contorno exterior; false = todas las aristas giradas, también las internas.
    project_axis: true = proyecta también el eje de giro al boceto (otra proyección, con el mismo link).
    """
    from .herramientas_construccion import _referencia
    _exigir_finitos(locals())
    if tolerance <= 0:
        raise error("INVALID_ARGUMENTS", "tolerance tiene que ser mayor que cero.")
    op, br = boceto_activo(sesion, sketch, derivados=False)
    ref_eje = _referencia(sesion, axis, {"eje", "arista", "curva_boceto", "cara"}, body, "eje")
    entidad_eje = ent.resolver(ref_eje, sesion.doc.estado_final)
    giro = {"eje": ent.como_eje(entidad_eje), "tolerancia": tolerance, "invertir": flip}
    try:
        prims, puntos, refs, _inf = _proyectar_seleccion(sesion, br.plano, "giro", edges, faces, bodies, vertices,
                                                         None, body, giro)
    except geo.ErrorGeometria as e:
        raise error("INVALID_GEOMETRY", str(e)) from e
    if not refs:
        raise error("INVALID_ARGUMENTS", "Elegí qué girar: edges, faces, vertices o bodies.")
    if not prims and not puntos:
        raise error("INVALID_GEOMETRY", "Eso no deja ningún perfil sobre el plano del boceto.")
    origen = {"modo": "giro", "refs": refs, "eje": ref_eje, "tolerancia": tolerance, "invertir": flip}
    if outer_contour and prims:
        origen["contorno"] = _eje_en_plano(br.plano, giro["eje"])
    tandas = [(prims, puntos, construction, link, origen)]
    if project_axis:
        p_eje, q_eje = ent.proyectar_entidad(entidad_eje, br.plano)
        infinitas = ({str(k): _alcance_modelo(sesion, br.plano, prim) for k, prim in enumerate(p_eje)}
                     if entidad_eje.forma is None else {})
        tandas.append((p_eje, q_eje, construction, link, {"modo": "project", "refs": [ref_eje], "infinitas": infinitas}))
    r, ids = _sumar_proyecciones(sesion, op, tandas)
    r["projection"] = ids[0]
    if project_axis:
        r["axis_projection"] = ids[1]
    return r


def _eje_en_plano(plano, eje):
    """[punto, dirección] en coordenadas del boceto del eje 3D (punto, dirección) proyectado en `plano`."""
    p, d, n = (np.asarray(v, float) for v in (eje[0], eje[1], plano.normal))
    q = p - n * float((p - plano.origen) @ n)
    d2 = d - n * float(d @ n)
    o, f = plano.a_uv(q), plano.a_uv(q + d2 / float(np.linalg.norm(d2)))
    return [[float(o[0]), float(o[1])], [float(f[0] - o[0]), float(f[1] - o[1])]]


def _proyecciones_a_tratar(op, pid):
    """Ids de las proyecciones a tratar: la pedida (que tiene que estar perdida) o todas las perdidas."""
    if pid is None:
        return list(op.perdidas)
    if not any(r["id"] == pid for r in op.boceto.proyecciones):
        raise error("ENTITY_NOT_FOUND", f"El boceto no tiene la proyección {pid!r} (get_sketch › projections).")
    return [pid]


@herramienta("break_projection_link", "boceto",
             "Rompe el vínculo de una proyección (Fusion: Break Link): la geometría proyectada queda donde está como "
             "geometría normal, editable y ya no fija, y no sigue más al modelo.", modifica=True)
def break_projection_link(sesion, projection: int, sketch: str | None = None):
    """
    projection: id de la proyección (lo devuelve project_to_sketch; get_sketch › projections lo lista).
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    op = op_boceto(sesion, sketch)
    _proyecciones_a_tratar(op, projection)
    return _dibujar(sesion, sketch, lambda b: b.romper_vinculo(projection), desde_solver=True)


@herramienta("manage_lost_projections", "boceto",
             "Administra las proyecciones perdidas de un boceto (Fusion: Manage Lost Projections): las que ya no "
             "coinciden con el modelo (get_sketch › projections las marca con lost). relink las vuelve a vincular a otra selección (misma forma "
             "que la original: edges, faces, bodies, vertices o references); break les rompe el vínculo y delete borra "
             "su geometría. Con break y delete, sin projection actúa sobre todas las perdidas (Break Link All / "
             "Delete All).", modifica=True)
def manage_lost_projections(sesion, action: Literal["relink", "break", "delete"], projection: int | None = None, edges: list[str] | str | None = None,
                            faces: list[str] | str | None = None, bodies: list[str] | None = None,
                            vertices: list[list[float]] | None = None, references: list[str | dict] | None = None,
                            body: str | None = None, sketch: str | None = None):
    """
    action: relink, break o delete.
    projection: id de la proyección; vacío = todas las perdidas (solo con break y delete).
    edges: relink: aristas nuevas (selector o ids).
    faces: relink: caras nuevas.
    bodies: relink: cuerpos nuevos.
    vertices: relink: vértices nuevos por coordenadas [x, y, z].
    references: relink: planos, ejes, puntos de trabajo o curvas de otro boceto, como en project_to_sketch.
    body: cuerpo donde se evalúan los selectores.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    """
    op = op_boceto(sesion, sketch)
    if action == "relink":
        if projection is None:
            raise error("INVALID_ARGUMENTS", "relink necesita projection (el id de la proyección a vincular).")
        _proyecciones_a_tratar(op, projection)
        _op, br = boceto_activo(sesion, sketch, derivados=False)
        reg = next(r for r in op.boceto.proyecciones if r["id"] == projection)
        modo = reg["modo"]
        giro = None
        if modo == "giro":      # el perfil giratorio conserva su eje, tolerancia y sentido
            giro = {"eje": ent.como_eje(ent.resolver(reg["eje"], sesion.doc.estado_final)),
                    "tolerancia": reg["tolerancia"], "invertir": reg["invertir"]}
        prims, puntos, refs, infinitas = _proyectar_seleccion(sesion, br.plano, modo, edges, faces, bodies, vertices,
                                                              references, body, giro)
        if not refs:
            raise error("INVALID_ARGUMENTS", "Elegí a qué re-vincular: edges, faces, vertices, bodies o references.")
        return _dibujar(sesion, sketch, lambda b: b.revincular(projection, refs, prims, puntos, infinitas),
                        desde_solver=True)
    ids = _proyecciones_a_tratar(op, projection)
    if not ids:
        raise error("INVALID_ARGUMENTS", "El boceto no tiene proyecciones perdidas.")
    accion = (lambda b, i: b.romper_vinculo(i)) if action == "break" else (lambda b, i: b.eliminar_proyeccion(i))
    return _dibujar(sesion, sketch, lambda b: [accion(b, i) for i in ids], desde_solver=True)


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
             "el boceto queda como estaba. Con `offset` y `text_offset` mueve la línea de cota y su texto sin cambiar el "
             "valor (cotas lineales); `position` [x, y] la mueve como el arrastre con el ratón, en cualquier cota. Mantiene sincronizado el parámetro dN; rechaza dependencias circulares. "
             "reference alterna driving/driven. Al pasar a referencia se pierde la expresión y se mide la geometría; "
             "su valor no es editable. Si volver a driving sobre-restringiría, sigue de referencia con aviso "
             "y el documento queda como estaba. `type` alterna radius ↔ diameter conservando el valor equivalente "
             "(la geometría no cambia). `mode` cambia una distancia con un círculo o arco entre center y tangent: la "
             "expresión queda y la geometría se mueve para cumplirla. `near` [x, y] cambia qué ángulo mide una cota "
             "de ángulo (el del cuadrante que contiene el punto): igual que mode, la expresión queda. "
             "Para borrar una cota o una restricción: delete_sketch_entities con su id.",
             modifica=True)
def edit_dimension(sesion, dimension: int, value: Expr | None = None, sketch: str | None = None,
                   offset: float | None = None, text_offset: float | None = None, reference: bool | None = None,
                   type: Literal["radius", "diameter"] | None = None,  # noqa: A002
                   mode: Literal["center", "tangent"] | None = None, near: list[float] | None = None,
                   position: list[float] | None = None, name: str | None = None):
    """
    dimension: id de la cota (get_sketch la lista en dimensions).
    name: renombra el parámetro de la cota (como tipear «ANCHO=20» en su caja de la ventana); tiene que estar libre y las expresiones que citaban el nombre viejo dejan de valer; vacío = no cambia.
    value: valor nuevo: número (mm; grados en una cota de ángulo) o expresión con parámetros ("ancho / 2"); vacío = no cambia el valor. En una cota de desfase, un negativo pasa la copia al otro lado, como en Fusion.
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    offset: mm que se separa la línea de cota de la medida (con signo); vacío = no cambia.
    text_offset: mm que se corre el texto a lo largo de la línea de cota desde su centro; vacío = no cambia.
    reference: true = convertir a referencia (driven); false = driving; vacío = no cambia. Una alternancia redundante o en conflicto avisa y conserva la referencia sin modificar el documento.
    type: radius o diameter: pasa una cota de radio a diámetro (o al revés) con el valor equivalente; vacío = no cambia.
    mode: center o tangent en una distancia con un círculo o arco; vacío = no cambia.
    near: [x, y] en mm, solo en una cota de ángulo: pasa a medir el ángulo del cuadrante que contiene este punto; vacío = no cambia.
    position: [x, y] en mm: mueve la cota ahí, como arrastrarla con el ratón (no cambia el valor; en una cota de ángulo también elige qué ángulo mide, como near); no se combina con offset ni text_offset; vacío = no cambia.
    """
    if all(v is None for v in (value, offset, text_offset, reference, type, mode, near, position, name)):
        raise error("INVALID_ARGUMENTS",
                    "Falta qué cambiar: value, name, offset, text_offset, reference, type, mode, near o position.")
    op, br = boceto_activo(sesion, sketch, derivados=False)
    nueva = op.copia()
    k = nueva.boceto.cotas.get(dimension) if isinstance(dimension, int) and not isinstance(dimension, bool) else None
    if k is None:
        hay = ", ".join(str(i) for i in nueva.boceto.cotas) or "ninguna"
        raise error("ENTITY_NOT_FOUND", f"El boceto «{op.nombre}» ({op.id}) no tiene la cota {dimension!r} (cotas: "
                    f"{hay}).", "get_sketch lista las cotas (dimensions) con su id.")
    anterior = k.expresion
    if near is not None:                       # el cuadrante se mide sobre la geometría resuelta
        _sincronizar_con_solver(sesion, op, nueva.boceto)
    cuadrante = _cuadrante(nueva.boceto, k.tipo, k.entidades, near)
    try:
        nueva.boceto.cambiar_cota(dimension, None if type is None else COTAS[type], None if mode is None else _MODOS[mode],
                                  cuadrante)
    except ErrorBoceto as e:
        raise error("INVALID_DIMENSION", str(e)) from e
    tipo = _COTA_A_INGLES.get(k.tipo, k.tipo)
    era_referencia = k.referencia
    if value is not None and (era_referencia or reference is True):
        raise error("INVALID_DIMENSION", "Una cota de referencia mide la geometría: su valor no se puede editar.",
                    "Convertí primero la cota a driving con reference=false.")
    if reference is not None and reference != era_referencia:
        _sincronizar_con_solver(sesion, op, nueva.boceto)
        k.referencia = reference
        k.expresion = repr(nueva.boceto.medir(k))
        if not reference and _cota_sobre_restringe(sesion, nueva.boceto, br.solver):
            sesion.avisar("La cota sobre-restringiría el boceto: sigue como cota de referencia (driven).")
            return {"sketch": _paso(op), "dimension": next(c for c in info_boceto(sesion, op)["dimensions"]
                                                         if c["id"] == dimension),
                    "dof": br.solver.gdl, "status": estado_solver(br)[0]}
    if value is not None:
        expresion, valor = _valor_expr(sesion, value, ANGULO if k.tipo == "angulo" else LONGITUD)
        _cota_valida(k.tipo, valor, f"La cota {dimension} ({tipo})")
        k.expresion = expresion
    expresion = k.expresion
    _fijar_ubicacion(nueva.boceto, k, offset, text_offset, position)
    if name:
        validar_nombre(name)
        k.nombre = name
    sesion.doc.reemplazar(op.id, nueva)
    _exigir_sin_conflicto(sesion, nueva, br.solver.ok, f"La cota {dimension} ({tipo}) = {expresion}")
    estado, gdl = estado_solver(boceto_resuelto(sesion, nueva))
    return {"sketch": _paso(nueva), "dimension": {"id": dimension, "name": k.nombre, "type": tipo, "entities": list(k.entidades),
                                                  "previous_expression": anterior, "expression": expresion,
                                                  "value": _valor_cota(sesion, k), "reference": k.referencia,
                                                  **_ubicacion_cota(k)},
            "dof": gdl, "status": estado}


_AUTO_TIPOS = {nombre: tipo for nombre, tipo in RESTRICCIONES.items() if tipo in TIPOS_AUTO} | {"dimensions": "cota"}


def _opciones_auto(tolerance_angle, tolerance_distance, types, max_items, datum, exclude):
    """Opciones de `auto_restringir` desde los argumentos de la herramienta (INVALID_ARGUMENTS si no valen)."""
    if not _finito(tolerance_angle) or not 0 < tolerance_angle <= 45:
        raise error("INVALID_ARGUMENTS", "tolerance_angle tiene que estar entre 0 y 45 grados (mayor a 0).")
    if not _finito(tolerance_distance) or not 0 < tolerance_distance <= 10:
        raise error("INVALID_ARGUMENTS", "tolerance_distance tiene que estar entre 0 y 10 mm (mayor a 0).")
    tipos = None
    if types is not None:
        desconocidos = [t for t in types if t not in _AUTO_TIPOS]
        if desconocidos:
            raise error("INVALID_ARGUMENTS", f"Tipos desconocidos en types: {desconocidos}.",
                        f"Los válidos son: {', '.join(_AUTO_TIPOS)}.")
        tipos = [_AUTO_TIPOS[t] for t in types]
    if max_items is not None and (isinstance(max_items, bool) or max_items < 0):
        raise error("INVALID_ARGUMENTS", "max_items tiene que ser un entero de 0 o más.")
    excluir = []
    for e in exclude or []:
        dimension = e.get("kind") == "dimension"
        tipo = (COTAS if dimension else RESTRICCIONES).get(e.get("type"))
        entidades = e.get("entities")
        if tipo is None or not isinstance(entidades, list):
            raise error("INVALID_ARGUMENTS", f"Cada elemento de exclude necesita type y entities válidos: {e!r}.",
                        "Es un item de una respuesta anterior: {kind, type, entities}.")
        excluir.append(("cota" if dimension else "restriccion", tipo, tuple(entidades)))
    return {"tol_angulo": tolerance_angle, "tol_distancia": tolerance_distance, "tipos": tipos, "limite": max_items,
            "datum": datum, "excluir": excluir}


def _item_auto(s):
    cota = s.clase == "cota"
    nombres = _COTA_A_INGLES if cota else _RESTRICCION_A_INGLES
    return {"kind": "dimension" if cota else "constraint", "type": nombres.get(s.tipo, s.tipo),
            "entities": list(s.entidades), "value": s.valor, "description": s.descripcion, "dof": s.gdl}


@herramienta("auto_constrain", "boceto",
             "Restringe automáticamente el boceto (Fusion: AutoConstrain): detecta lo que ya se cumple y lo agrega como "
             "restricción (coincidente, concéntrica, horizontal, vertical, colineal, paralela, perpendicular, tangente, "
             "igual, punto medio, simetría respecto de una línea central o de construcción) y después cotas con las "
             "medidas actuales (largos, radios, ángulos y posiciones desde un punto fijo en el origen o desde el datum) "
             "hasta dejarlo totalmente restringido si se puede. Cada agregado se prueba solo: nada entra en conflicto ni "
             "mueve la geometría fuera de las tolerancias. Con suggest_auto_constraints se ven las alternativas antes de "
             "aplicar; acá las cotas quedan como números (cambialas con edit_dimension).", modifica=True)
def auto_constrain(sesion, sketch: str | None = None, tolerance_angle: float = 1.0, tolerance_distance: float = 0.001,
                   types: list[str] | None = None, max_items: int | None = None, datum: int | None = None,
                   exclude: list[dict] | None = None):
    """
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    tolerance_angle: grados (0 a 45) dentro de los cuales una línea cuenta como horizontal, vertical, paralela o perpendicular.
    tolerance_distance: mm (hasta 10) dentro de los cuales dos cosas cuentan como coincidentes, tangentes, colineales, concéntricas, en el punto medio o simétricas.
    types: familias a inferir: coincident, concentric, horizontal, vertical, collinear, parallel, perpendicular, tangent, equal, midpoint, symmetry y dimensions (dato y cotas); vacío = todas.
    max_items: tope de restricciones y cotas a agregar (las primeras por prioridad); vacío = sin tope.
    datum: id de un punto del boceto desde el que se miden las posiciones (como Set datum de Fusion); vacío = el origen.
    exclude: sugerencias a no agregar, como los items de la respuesta: {kind: constraint o dimension, type, entities}.
    """
    opciones = _opciones_auto(tolerance_angle, tolerance_distance, types, max_items, datum, exclude)
    op, _br = boceto_activo(sesion, sketch, derivados=False)
    valores = valores_cotas(sesion, op.boceto)
    agregado = []
    r = _dibujar(sesion, op.id, lambda b: agregado.extend(auto_restringir(b, valores, **opciones)), desde_solver=True)
    r["added"] = [s.descripcion for s in agregado]
    r["items"] = [_item_auto(s) for s in agregado]
    return r


@herramienta("suggest_auto_constraints", "boceto",
             "Calcula alternativas de AutoConstrain SIN cambiar el boceto (Fusion: el diálogo con varios resultados). "
             "Cada resultado trae lo que agregaría (items, en orden de prioridad, con los grados de libertad que quedan "
             "tras cada uno) y si deja el boceto totalmente restringido: «Completo», «Solo restricciones», «Estricto» "
             "(tolerancias 10 veces menores) y una por cada punto elegido como datum. Para aplicar una, llamá a "
             "auto_constrain con las mismas opciones (max_items = cuántos items querés; exclude = los que sacás; "
             "datum). Las alternativas que dan lo mismo que otra anterior se saltean.")
def suggest_auto_constraints(sesion, sketch: str | None = None, results: int = 1, tolerance_angle: float = 1.0,
                             tolerance_distance: float = 0.001, types: list[str] | None = None,
                             max_items: int | None = None, datum: int | None = None, exclude: list[dict] | None = None):
    """
    sketch: id o nombre del boceto; vacío = el último boceto del timeline.
    results: cuántas alternativas pedir (1 a 12); pedir más es «Generate more».
    tolerance_angle: grados (0 a 45) dentro de los cuales una línea cuenta como horizontal, vertical, paralela o perpendicular.
    tolerance_distance: mm (hasta 10) dentro de los cuales dos cosas cuentan como coincidentes, tangentes, colineales, concéntricas, en el punto medio o simétricas.
    types: familias a inferir: coincident, concentric, horizontal, vertical, collinear, parallel, perpendicular, tangent, equal, midpoint, symmetry y dimensions (dato y cotas); vacío = todas.
    max_items: tope de restricciones y cotas por resultado (las primeras por prioridad); vacío = sin tope.
    datum: id de un punto del boceto desde el que se miden las posiciones; vacío = el origen.
    exclude: sugerencias a no incluir, como los items de una respuesta anterior: {kind: constraint o dimension, type, entities}.
    """
    if isinstance(results, bool) or not isinstance(results, int) or not 1 <= results <= 12:
        raise error("INVALID_ARGUMENTS", "results tiene que ser un entero de 1 a 12.")
    opciones = _opciones_auto(tolerance_angle, tolerance_distance, types, max_items, datum, exclude)
    op, br = boceto_activo(sesion, sketch, derivados=False)
    b = op.boceto.copia()
    _sincronizar_con_solver(sesion, op, b)
    try:
        alternativas = sugerir_auto_restricciones(b, valores_cotas(sesion, b), resultados=results, **opciones)
    except ErrorBoceto as e:
        raise error("INVALID_GEOMETRY", str(e)) from e
    estado, gdl = estado_solver(br)
    return {"sketch": _paso(op), "dof": gdl, "status": estado,
            "results": [{"name": a.nombre, "initial_dof": a.gdl_inicial, "dof": a.gdl,
                         "fully_constrained": a.totalmente_restringido,
                         "constraints": sum(s.clase == "restriccion" for s in a.sugerencias),
                         "dimensions": sum(s.clase == "cota" for s in a.sugerencias),
                         "items": [_item_auto(s) for s in a.sugerencias]} for a in alternativas]}
