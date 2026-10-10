# -*- coding: utf-8 -*-
"""
Selectores de caras y aristas al estilo CadQuery, e ids efímeros para el agente. Sin herramientas: acá solo
está la lógica; las herramientas están en `herramientas_inspeccion.py` (find_faces, find_edges, measure_angle)
y `herramientas_modificar.py` (fillet, chamfer, shell, create_hole, draft).

SINTAXIS (se evalúa sobre las caras o las aristas de UN cuerpo; "centro" = centro de masa de la cara o arista):

    >X  >Y  >Z      las de centro más alto en ese eje (con tolerancia: pueden ser varias).
                    >Z[1] es el segundo nivel más alto, >Z[-1] el más bajo.
    <X  <Y  <Z      las de centro más bajo (<Z[1]: el segundo nivel más bajo).
    |X  |Y  |Z      aristas rectas paralelas al eje; caras planas con la NORMAL paralela al eje (como CadQuery:
                    |Z en una caja = tapa y base).
    #X  #Y  #Z      lo perpendicular: aristas rectas perpendiculares al eje; caras planas con la normal
                    perpendicular al eje (#Z en una caja = las 4 laterales).
    +X  -X  +Y ...  caras planas cuya normal apunta en ese sentido. En aristas +Z y -Z valen como |Z (una
                    arista no tiene sentido).
    |Z~3  #Z~3  +Z~3 ...   lo mismo con una tolerancia de N grados (0 < N <= 45): elige también lo APENAS
                    inclinado, p. ej. las caras y aristas laterales tras un desmoldeo. Sin «~» la tolerancia es
                    casi nula (TOL_DIR). Tras un desmoldeo de θ en las 4 laterales de una caja, las aristas de
                    esquina quedan a atan(√2·tan θ) de la vertical (1,5° → 2,1°).
    %PLANE %CYLINDER %CONE %SPHERE %TORUS %BSPLINE %OTHER        tipo de superficie (caras).
    %LINE %CIRCLE %ELLIPSE %BSPLINE %OTHER                      tipo de curva (aristas).
    nearest:[x,y,z] la cara o arista MÁS CERCANA al punto (distancia real a la forma); una sola.
    all  (o *)      todas.

Se combinan con `and`, `or`, `not` y paréntesis; cada término se evalúa sobre TODAS las caras (o aristas) y
después se intersecan, unen o complementan (como CadQuery): `|Z and >X` = aristas verticales del lado +X;
`#Z and not <X`. `not` ata más que `and`, y `and` más que `or`.

IDS EFÍMEROS: `find_faces` y `find_edges` devuelven cada elemento con un id corto, "<cuerpo>/F3" (cara) o
"<cuerpo>/E7" (arista), donde <cuerpo> es el nombre del cuerpo (o su id si el nombre se repite). Valen HASTA EL
PRÓXIMO CAMBIO del documento: el número es la posición de la subforma en el cuerpo actual y cualquier cambio
(un paso nuevo, un parámetro, deshacer) puede reordenarlas. Un id viejo da `STALE_ID`. Por dentro las
herramientas NUNCA guardan el id: guardan la referencia persistente de `nucleo.referencias` (firma geométrica
relativa a la caja del cuerpo), que es la que sobrevive a cambios de parámetros.

Dónde se espera un elemento suelto (measure_distance, measure_angle, create_sketch, sketch_from_spec) el selector
se evalúa sobre las CARAS; para aristas se escribe `edges:|Z` (o `faces:` para ser explícito) o se usa un id.
Todas esas herramientas tienen `body` para decir sobre qué cuerpo se evalúa el selector cuando hay varios.
"""
import hashlib
import json
import math
import re

import numpy as np
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Pnt

from ..nucleo import geometria as geo
from ..nucleo import referencias as refs
from .errores import error

TOL_POS = 1e-3          # mm: dos centros a menos de esto están en el mismo nivel
TOL_DIR = 1e-3          # seno del ángulo máximo para decir "paralelo" / "perpendicular" (sin «~»)
TOL_MAX_GRADOS = 45     # tope de la tolerancia «~N»: más que esto, paralelo y perpendicular se pisan
MAX_ELEMENTOS = 300     # tope de elementos que devuelve find_faces / find_edges

EJES = {"X": np.array([1.0, 0.0, 0.0]), "Y": np.array([0.0, 1.0, 0.0]), "Z": np.array([0.0, 0.0, 1.0])}
TIPOS_CARA = {"plano": "PLANE", "cilindro": "CYLINDER", "cono": "CONE", "esfera": "SPHERE", "toro": "TORUS",
              "bspline": "BSPLINE", "otra": "OTHER"}
TIPOS_ARISTA = {"linea": "LINE", "circulo": "CIRCLE", "elipse": "ELLIPSE", "bspline": "BSPLINE", "otra": "OTHER"}
NOMBRE_TIPO = {"cara": "cara", "arista": "arista"}


# ---------------------------------------------------------------- elementos (caras o aristas de un cuerpo)
class Elemento:
    """Una cara o arista de un cuerpo con lo que los selectores necesitan. `i` es su posición (1, 2, …)."""

    def __init__(self, tipo, i, sub, firma):
        self.tipo, self.i, self.sub, self.firma = tipo, i, sub, firma
        self.geom = (TIPOS_CARA if tipo == "cara" else TIPOS_ARISTA).get(firma["geom"], "OTHER")
        self.normal = self.direccion = None
        if tipo == "cara":
            self.centro = np.array(firma["centro"], float)
            if "normal" in firma:
                self.normal = np.array(firma["normal"], float)
        else:
            p = GProp_GProps()
            BRepGProp.LinearProperties_s(sub, p)
            c = p.CentreOfMass()
            self.centro = np.array([c.X(), c.Y(), c.Z()], float)
            if self.geom == "LINE":
                a, b = (np.array(x, float) for x in firma["extremos"])
                d = b - a
                self.direccion = d / (np.linalg.norm(d) or 1.0)

    @property
    def vector(self):
        """Normal (cara plana) o dirección (arista recta); None si no tiene."""
        return self.normal if self.tipo == "cara" else self.direccion


def listar(forma, tipo):
    """Todas las caras ("cara") o aristas ("arista") de la forma, en el orden estable de `referencias.subformas`."""
    f = refs.firma_cara if tipo == "cara" else refs.firma_arista
    return [Elemento(tipo, i, s, f(s)) for i, s in enumerate(refs.subformas(forma, tipo), 1)]


def resumen_tipos(elementos):
    """'6 PLANE, 2 CYLINDER' de una lista de elementos."""
    cuenta = {}
    for e in elementos:
        cuenta[e.geom] = cuenta.get(e.geom, 0) + 1
    return ", ".join(f"{n} {g}" for g, n in sorted(cuenta.items())) or "ninguno"


# ---------------------------------------------------------------- análisis del texto
_TOKEN = re.compile(r"""\s*(?:
      (?P<par>[()])
    | (?P<kw>(?:and|or|not)\b)
    | (?P<cerca>nearest\s*:\s*\[(?P<coords>[^\]]*)\])
    | (?P<mm>[<>])\s*(?P<eje1>[XYZ])\b(?:\s*\[\s*(?P<idx>-?\d+)\s*\])?
    | (?P<dir>[|\#+\-])\s*(?P<eje2>[XYZ])\b(?:\s*~\s*(?P<tol>\d+(?:\.\d+)?)\b)?
    | %\s*(?P<geom>[A-Za-z]+)\b
    | (?P<todo>all\b|\*)
    )""", re.IGNORECASE | re.VERBOSE)


def _invalido(texto, motivo):
    return error("INVALID_SELECTOR", f"Selector inválido «{texto}»: {motivo}")


def _tokens(texto):
    salida, pos = [], 0
    while True:
        while pos < len(texto) and texto[pos].isspace():
            pos += 1
        if pos >= len(texto):
            return salida
        m = _TOKEN.match(texto, pos)
        if not m or m.end() == pos:
            raise _invalido(texto, f"no se entiende «{texto[pos:pos + 12]}» (posición {pos + 1}).")
        pos = m.end()
        if m.group("par"):
            salida.append(("par", m.group("par")))
        elif m.group("kw"):
            salida.append(("kw", m.group("kw").lower()))
        elif m.group("cerca"):
            try:
                xyz = [float(c) for c in m.group("coords").split(",")]
                if len(xyz) != 3 or not all(math.isfinite(c) for c in xyz):
                    raise ValueError
            except ValueError:
                raise _invalido(texto, "nearest necesita tres números: nearest:[x,y,z].") from None
            salida.append(("atomo", ("cerca", xyz)))
        elif m.group("mm"):
            salida.append(("atomo", ("mm", m.group("mm"), m.group("eje1").upper(), int(m.group("idx") or 0))))
        elif m.group("dir"):
            grados = None if m.group("tol") is None else float(m.group("tol"))
            if grados is not None and not 0 < grados <= TOL_MAX_GRADOS:
                raise _invalido(texto, f"la tolerancia «~» va en grados, mayor que 0 y hasta {TOL_MAX_GRADOS} "
                                "(p. ej. |Z~3).")
            salida.append(("atomo", ("dir", m.group("dir"), m.group("eje2").upper(), grados)))
        elif m.group("geom"):
            salida.append(("atomo", ("geom", m.group("geom").upper())))
        else:
            salida.append(("atomo", ("todo",)))


def compilar(texto):
    """Texto → árbol ('or'|'and', izq, der), ('not', x) o átomo. Lanza INVALID_SELECTOR."""
    if not isinstance(texto, str) or not texto.strip():
        raise _invalido(str(texto), "está vacío.")
    # Algunos modelos mandan «<» y «>» escapados como HTML (&lt;Z): se aceptan igual. Visto en la prueba real con
    # Claude Code del 2026-10-09 (paquete K): create_hole(face="&lt;Z") fallaba con INVALID_SELECTOR.
    texto = texto.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    toks = _tokens(texto)
    pos = [0]

    def ver():
        return toks[pos[0]] if pos[0] < len(toks) else (None, None)

    def tomar():
        pos[0] += 1
        return toks[pos[0] - 1]

    def o():
        izq = y()
        while ver() == ("kw", "or"):
            tomar()
            izq = ("or", izq, y())
        return izq

    def y():
        izq = no()
        while ver() == ("kw", "and"):
            tomar()
            izq = ("and", izq, no())
        return izq

    def no():
        if ver() == ("kw", "not"):
            tomar()
            return ("not", no())
        return atomo()

    def atomo():
        tipo, valor = ver()
        if tipo == "par" and valor == "(":
            tomar()
            x = o()
            if ver() != ("par", ")"):
                raise _invalido(texto, "falta cerrar un paréntesis.")
            tomar()
            return x
        if tipo == "atomo":
            tomar()
            return valor
        raise _invalido(texto, "falta un término (>Z, |X, %PLANE…)" + (f" antes de «{valor}»." if valor else " al final."))

    arbol = o()
    if pos[0] != len(toks):
        raise _invalido(texto, f"sobra «{toks[pos[0]][1]}»: falta and u or entre dos términos.")
    return arbol


def parece_selector(texto):
    try:
        compilar(texto)
        return True
    except Exception:  # noqa: BLE001 — solo importa si es válido
        return False


# ---------------------------------------------------------------- evaluación
def _niveles(valores):
    """Valores distintos (con tolerancia) de mayor a menor."""
    niveles = []
    for v in sorted(valores, reverse=True):
        if not niveles or niveles[-1] - v > TOL_POS:
            niveles.append(v)
    return niveles


def _distancia_a_punto(e, p):
    d = BRepExtrema_DistShapeShape(e.sub, BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, p))).Vertex())
    return d.Value() if d.IsDone() else math.inf


def _atomo(a, elementos, tipo, texto):
    n = len(elementos)
    clase = a[0]
    if clase == "todo":
        return set(range(n))
    if clase == "mm":
        _, signo, eje, idx = a
        k = "XYZ".index(eje)
        niveles = _niveles([float(e.centro[k]) * (1 if signo == ">" else -1) for e in elementos])
        if not niveles:
            return set()
        try:
            nivel = niveles[idx]
        except IndexError:
            raise _invalido(texto, f"{signo}{eje}[{idx}] pide un nivel que no existe: hay {len(niveles)}.") from None
        return {i for i, e in enumerate(elementos)
                if abs(float(e.centro[k]) * (1 if signo == ">" else -1) - nivel) <= TOL_POS}
    if clase == "dir":
        _, simbolo, eje, grados = a
        d = EJES[eje]
        tol = TOL_DIR if grados is None else math.sin(math.radians(grados))   # seno del desvío admitido
        salida = set()
        for i, e in enumerate(elementos):
            v = e.vector
            if v is None:
                continue
            paralelo = float(np.linalg.norm(np.cross(v, d))) < tol
            if simbolo == "#":
                ok = abs(float(v @ d)) < tol
            elif simbolo == "|" or tipo == "arista":
                ok = paralelo
            else:                                    # + o - sobre una cara plana: sentido de la normal
                ok = paralelo and float(v @ d) * (1 if simbolo == "+" else -1) > 0
            if ok:
                salida.add(i)
        return salida
    if clase == "geom":
        validos = TIPOS_CARA if tipo == "cara" else TIPOS_ARISTA
        if a[1] not in validos.values():
            raise _invalido(texto, f"%{a[1]} no es un tipo de {NOMBRE_TIPO[tipo]}; los de {NOMBRE_TIPO[tipo]} son: "
                            + ", ".join(sorted(set(validos.values()))) + ".")
        return {i for i, e in enumerate(elementos) if e.geom == a[1]}
    if clase == "cerca":
        if not elementos:
            return set()
        p = np.array(a[1], float)
        return {min(range(n), key=lambda i: (round(_distancia_a_punto(elementos[i], p), 6),
                                              float(np.linalg.norm(elementos[i].centro - p))))}
    raise _invalido(texto, "término desconocido.")   # inalcanzable: el analizador solo emite los de arriba


def _eval(nodo, elementos, tipo, texto):
    if nodo[0] == "or":
        return _eval(nodo[1], elementos, tipo, texto) | _eval(nodo[2], elementos, tipo, texto)
    if nodo[0] == "and":
        return _eval(nodo[1], elementos, tipo, texto) & _eval(nodo[2], elementos, tipo, texto)
    if nodo[0] == "not":
        return set(range(len(elementos))) - _eval(nodo[1], elementos, tipo, texto)
    return _atomo(nodo, elementos, tipo, texto)


def evaluar(texto, elementos, tipo, nombre_cuerpo=""):
    """Elementos (en su orden) que elige el selector. INVALID_SELECTOR si no se entiende; NO_MATCH si es válido
    pero no elige nada."""
    elegidos = sorted(_eval(compilar(texto), elementos, tipo, texto))
    if not elegidos:
        donde = f" de «{nombre_cuerpo}»" if nombre_cuerpo else ""
        raise error("NO_MATCH", f"El selector «{texto}» no eligió ninguna {NOMBRE_TIPO[tipo]}{donde}: el cuerpo tiene "
                    f"{len(elementos)} {'caras' if tipo == 'cara' else 'aristas'} ({resumen_tipos(elementos)}).")
    return [elementos[i] for i in elegidos]


# ---------------------------------------------------------------- sesión: ids, cuerpos y referencias
_ID = re.compile(r"^(?P<cuerpo>.+)/(?P<t>[FE])(?P<n>\d+)$", re.IGNORECASE)
_PREFIJO = re.compile(r"^\s*(faces|edges)\s*:\s*(?=\S)", re.IGNORECASE)


def _huella(sesion):
    """Identifica el estado del documento: si cambia, los ids emitidos antes dejan de valer."""
    return hashlib.md5(json.dumps(sesion.doc.a_dict(), sort_keys=True, default=str).encode()).hexdigest()


def _emitidos(sesion):
    if not hasattr(sesion, "_ids_efimeros"):
        sesion._ids_efimeros = {}
    return sesion._ids_efimeros


def etiqueta_cuerpo(sesion, cuerpo):
    """Nombre del cuerpo si es único entre los cuerpos del documento; si no, su id."""
    nombre = sesion.nombre_cuerpo(cuerpo)
    repetidos = [c for c in sesion.doc.estado_final.cuerpos.values() if sesion.nombre_cuerpo(c) == nombre]
    return nombre if len(repetidos) == 1 and "/" not in nombre else cuerpo.id


def emitir_id(sesion, cuerpo, elem):
    """Id efímero "<cuerpo>/F3" del elemento; queda registrado para detectar si se vence."""
    letra = "F" if elem.tipo == "cara" else "E"
    _emitidos(sesion)[(cuerpo.id, letra, elem.i)] = _huella(sesion)
    return f"{etiqueta_cuerpo(sesion, cuerpo)}/{letra}{elem.i}"


def es_id(texto):
    return isinstance(texto, str) and bool(_ID.match(texto.strip()))


def cuerpo_objetivo(sesion, body=None):
    """El cuerpo sobre el que se evalúan los selectores: `body`, o el único cuerpo (no malla) del documento."""
    if body is not None and str(body).strip():
        c = sesion.cuerpo(body)
        if getattr(c, "tipo", "solido") == "malla":
            raise error("UNSUPPORTED_BODY_TYPE", f"«{sesion.nombre_cuerpo(c)}» es una malla: no tiene caras ni aristas "
                        "seleccionables.")
        return c
    cuerpos = [c for c in sesion.doc.estado_final.cuerpos.values() if getattr(c, "tipo", "solido") != "malla"]
    if len(cuerpos) == 1:
        return cuerpos[0]
    if not cuerpos:
        raise error("BODY_NOT_FOUND", "El documento no tiene cuerpos con caras o aristas.")
    raise error("AMBIGUOUS_REFERENCE", f"Hay {len(cuerpos)} cuerpos ({', '.join(sesion.nombre_cuerpo(c) for c in cuerpos)}): "
                "con un selector hay que decir cuál (argumento body), o usar ids de find_faces / find_edges.")


def resolver_id(sesion, texto, tipo=None):
    """(cuerpo, elemento) de un id efímero. STALE_ID si el documento cambió desde que se emitió;
    ELEMENT_NOT_FOUND si el cuerpo no tiene ese número."""
    m = _ID.match(texto.strip())
    t = "cara" if m.group("t").upper() == "F" else "arista"
    if tipo is not None and t != tipo:
        raise error("INVALID_ARGUMENTS", f"«{texto}» es {'una cara' if t == 'cara' else 'una arista'}, y acá se "
                    f"necesitan {'caras' if tipo == 'cara' else 'aristas'}.",
                    "Las caras llevan F (Cuerpo1/F3) y las aristas E (Cuerpo1/E7).")
    cuerpo = sesion.cuerpo(m.group("cuerpo").strip())
    n = int(m.group("n"))
    vence = _emitidos(sesion).get((cuerpo.id, m.group("t").upper(), n))
    if vence is not None and vence != _huella(sesion):
        raise error("STALE_ID", f"El id «{texto}» se obtuvo antes de un cambio del documento y ya no es confiable.")
    elementos = listar(cuerpo.forma, t)
    if not 1 <= n <= len(elementos):
        raise error("ELEMENT_NOT_FOUND", f"«{sesion.nombre_cuerpo(cuerpo)}» tiene {len(elementos)} "
                    f"{'caras' if t == 'cara' else 'aristas'}: no existe {m.group('t').upper()}{n}.")
    return cuerpo, elementos[n - 1]


def _separar_prefijo(texto):
    m = _PREFIJO.match(texto)
    if not m:
        return None, texto
    return ("cara" if m.group(1).lower() == "faces" else "arista"), texto[m.end():]


def elegir(sesion, spec, tipo, body=None, permitir_vacio=False):
    """[(cuerpo, elemento)] de un selector (texto), un id, o una lista mezclada de ids y selectores (se unen).
    Sin repetidos. Los selectores se evalúan sobre `body` o el único cuerpo del documento."""
    items = [spec] if isinstance(spec, str) else list(spec or [])
    if not items:
        if permitir_vacio:
            return []
        raise error("INVALID_ARGUMENTS", f"Falta elegir {'caras' if tipo == 'cara' else 'aristas'}: pasá un selector "
                    "(p. ej. '>Z') o ids de find_faces / find_edges.")
    salida, vistos = [], set()
    for item in items:
        if not isinstance(item, str):
            raise error("INVALID_ARGUMENTS", f"Cada elemento tiene que ser un texto (selector o id), no {item!r}.")
        pref, texto = _separar_prefijo(item)
        if pref is not None and pref != tipo:
            raise error("INVALID_ARGUMENTS", f"«{item}» elige {'caras' if pref == 'cara' else 'aristas'}, y acá se "
                        f"necesitan {'caras' if tipo == 'cara' else 'aristas'}.")
        if es_id(texto):
            hallados = [resolver_id(sesion, texto, tipo)]
        else:
            cuerpo = cuerpo_objetivo(sesion, body)
            hallados = [(cuerpo, e) for e in evaluar(texto, listar(cuerpo.forma, tipo), tipo, sesion.nombre_cuerpo(cuerpo))]
        for c, e in hallados:
            if (c.id, e.i) not in vistos:
                vistos.add((c.id, e.i))
                salida.append((c, e))
    return salida


def elegir_uno(sesion, spec, preferido="cara", body=None):
    """(cuerpo, elemento) de UNA sola cara o arista: un id, o un selector (sobre caras salvo prefijo `edges:`)."""
    if not isinstance(spec, str):
        raise error("INVALID_ARGUMENTS", f"Se esperaba un selector o un id (texto), no {spec!r}.")
    pref, resto = _separar_prefijo(spec)
    if pref:
        tipo = pref
    elif es_id(resto):
        tipo = "cara" if _ID.match(resto.strip()).group("t").upper() == "F" else "arista"
    else:
        tipo = preferido
    hallados = elegir(sesion, spec, tipo, body)
    if len(hallados) != 1:
        ids = ", ".join(emitir_id(sesion, c, e) for c, e in hallados[:6])
        raise error("AMBIGUOUS_REFERENCE", f"«{spec}» eligió {len(hallados)} {'caras' if tipo == 'cara' else 'aristas'} "
                    f"({ids}{'…' if len(hallados) > 6 else ''}) y acá hace falta exactamente una.",
                    "Afiná el selector (p. ej. con and) o usá nearest:[x,y,z] o un id de find_faces / find_edges.")
    c, e = hallados[0]
    emitir_id(sesion, c, e)
    return c, e


def referencia(cuerpo, elem):
    """Referencia PERSISTENTE (`nucleo.referencias`) al elemento: lo que se guarda en los pasos del timeline."""
    return refs.referencia(cuerpo.id, elem.sub, cuerpo.forma)


def plano_de_cara(elem):
    """`geo.Plano` de una cara plana (con el marco de ejes que usa el boceto sobre cara), o UNSUPPORTED_ELEMENT."""
    plano = geo.plano_de_cara(elem.sub) if elem.tipo == "cara" else None
    if plano is None:
        raise error("UNSUPPORTED_ELEMENT", "Hace falta una cara PLANA: la elegida no lo es "
                    f"({elem.geom if elem.tipo == 'cara' else 'es una arista'}).",
                    "find_faces(selector='%PLANE') lista las caras planas.")
    return plano


# ---------------------------------------------------------------- descripción para el agente
def _r(x):
    return round(float(x), 4) + 0.0


def _v(x):
    return [_r(c) for c in x]


def info_elemento(sesion, cuerpo, elem):
    """Dict JSON del elemento, con su id efímero, tipo, tamaño, centro y normal/dirección. Unidades: mm y mm²."""
    f = elem.firma
    info = {"id": emitir_id(sesion, cuerpo, elem), "body": cuerpo.id, "type": elem.geom.lower(), "center": _v(elem.centro)}
    if elem.tipo == "cara":
        info["area"] = _r(f["area"])
        if elem.normal is not None:
            info["normal"] = _v(elem.normal)
            info["center_uv"] = _v(geo.plano_de_cara(elem.sub).a_uv(elem.centro))
        if "eje" in f:
            info["axis"] = _v(f["eje"])
        if "radio" in f:
            info["radius"] = _r(f["radio"])
    else:
        info["length"] = _r(f["largo"])
        if elem.direccion is not None:
            info["direction"] = _v(elem.direccion)
        if "radio" in f:
            info["radius"] = _r(f["radio"])
            info["circle_center"] = _v(f["centro"])
    return info
