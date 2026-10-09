# -*- coding: utf-8 -*-
"""
DXF ASCII: escritor (R2000 = AC1015, o R12 = AC1009) y lector básico de geometría 2D.

Equivalencia con Fusion: Drawing › Export › Export Sheet as DXF; en el diseño, "Insertar DXF" y
"Exportar boceto como DXF" (los usan otros módulos con estas mismas primitivas). Sin dependencias externas.

Primitivas 2D (mm):
  ('linea', (x1, y1), (x2, y2))
  ('circulo', (cx, cy), r)
  ('arco', (cx, cy), r, a0, a1)        radianes, antihorario; el lector garantiza 0 ≤ a0 < 2π y a0 < a1 ≤ a0 + 2π
  ('polilinea', [(x, y), ...], cerrada)
  ('texto', (x, y), altura, texto)     el escritor acepta además rotación (grados) y alineación
                                        ('izq' | 'centro' | 'der'): ('texto', p, h, t, rot, alin)
  Solo escritor:
  ('elipse', (cx, cy), (mx, my), razon, t0, t1)   semieje mayor (mx, my) relativo al centro, t en radianes
  ('spline', [(x, y), ...])                        se escribe como polilínea por esos puntos
  ('solido', [(x, y), ...])                        triángulo o cuadrilátero relleno (SOLID)
El lector devuelve solo las cinco primeras: elipses, splines, curvas de polilíneas (bulge), sólidos y
MTEXT se convierten. Los bloques (INSERT y DIMENSION) se expanden; las unidades ($INSUNITS) pasan a mm.
"""
import math
import re
from pathlib import Path


class ErrorDXF(ValueError):
    pass


TIPOS_LINEA = {"continua": "CONTINUOUS", "trazos": "DASHED", "trazo_punto": "CENTER"}
_PATRONES = {"DASHED": ("Trazos __ __ __", (3.0, -1.5)), "CENTER": ("Centro ____ _ ____", (12.0, -3.0, 2.0, -3.0))}
_GROSORES = (0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100, 106, 120, 140, 158, 200, 211)
_UNIDADES = {0: 1.0, 1: 25.4, 2: 304.8, 3: 1609344.0, 4: 1.0, 5: 10.0, 6: 1000.0, 7: 1e6, 8: 2.54e-5,
             9: 0.0254, 10: 914.4, 14: 100.0}
_SEGMENTOS_ARCO = math.radians(5.0)    # paso al aproximar curvas con polilíneas


# =============================================================== escritor
def _num(v):
    t = f"{float(v):.6f}".rstrip("0").rstrip(".")
    return "0" if t in ("-0", "") else t


def _cadena(texto):
    """Texto para un TEXT: códigos de control de AutoCAD (%%c ⌀, %%d °, %%p ±) y \\U+XXXX fuera de cp1252."""
    t = str(texto).replace("\r", " ").replace("\n", " ")
    t = t.replace("%%", "%%%").replace("⌀", "%%c").replace("Ø", "%%c").replace("°", "%%d").replace("±", "%%p")
    salida = []
    for ch in t:
        try:
            ch.encode("cp1252")
            salida.append(ch)
        except UnicodeEncodeError:
            salida.append(f"\\U+{ord(ch):04X}")
    return "".join(salida)


def _nombre_capa(nombre):
    t = re.sub(r'[<>/\\":;?*|=`]', "_", str(nombre)).strip() or "0"
    return _cadena(t)


class _Escritor:
    def __init__(self, version):
        if version not in ("2000", "R12"):
            raise ErrorDXF(f"Versión de DXF no soportada: {version} (usar '2000' o 'R12').")
        self.r12 = version == "R12"
        self.lineas = []
        self.h = 0x20

    def g(self, codigo, valor):
        self.lineas.append(f"{codigo:>3}\n{valor}\n")

    def handle(self):
        self.h += 1
        return f"{self.h:X}"

    def cabecera_entidad(self, tipo, capa, dueno, subclase):
        self.g(0, tipo)
        if not self.r12:
            self.g(5, self.handle())
            self.g(330, dueno)
            self.g(100, "AcDbEntity")
        self.g(8, capa)
        if not self.r12 and subclase:
            self.g(100, subclase)

    def punto(self, base, p):
        self.g(base, _num(p[0]))
        self.g(base + 10, _num(p[1]))
        self.g(base + 20, "0")


def _puntos_elipse(c, m, razon, t0, t1, nz=1.0):
    """Puntos de la elipse; el semieje menor es razon · (N × M), con N = (0, 0, nz) la extrusión."""
    if t1 <= t0:
        t1 += 2 * math.pi
    n = max(8, math.ceil((t1 - t0) / _SEGMENTOS_ARCO))
    mx, my = m
    s = 1.0 if nz >= 0 else -1.0
    nx, ny = -my * razon * s, mx * razon * s
    return [(c[0] + mx * math.cos(t) + nx * math.sin(t), c[1] + my * math.cos(t) + ny * math.sin(t))
            for t in (t0 + (t1 - t0) * k / n for k in range(n + 1))]


def _entidad(w, capa, prim, dueno):
    tipo = prim[0]
    if tipo == "linea":
        w.cabecera_entidad("LINE", capa, dueno, "AcDbLine")
        w.punto(10, prim[1])
        w.punto(11, prim[2])
    elif tipo == "circulo":
        w.cabecera_entidad("CIRCLE", capa, dueno, "AcDbCircle")
        w.punto(10, prim[1])
        w.g(40, _num(prim[2]))
    elif tipo == "arco":
        w.cabecera_entidad("ARC", capa, dueno, "AcDbCircle")
        w.punto(10, prim[1])
        w.g(40, _num(prim[2]))
        if not w.r12:
            w.g(100, "AcDbArc")
        w.g(50, _num(math.degrees(prim[3]) % 360.0))
        w.g(51, _num(math.degrees(prim[4]) % 360.0))
    elif tipo in ("polilinea", "spline"):
        pts = [tuple(p) for p in prim[1]]
        cerrada = bool(prim[2]) if tipo == "polilinea" and len(prim) > 2 else False
        if len(pts) < 2:
            return
        if w.r12:
            w.cabecera_entidad("POLYLINE", capa, dueno, None)
            w.g(66, "1")
            w.g(70, "1" if cerrada else "0")
            w.punto(10, (0.0, 0.0))
            for p in pts:
                w.cabecera_entidad("VERTEX", capa, dueno, None)
                w.punto(10, p)
            w.cabecera_entidad("SEQEND", capa, dueno, None)
        else:
            w.cabecera_entidad("LWPOLYLINE", capa, dueno, "AcDbPolyline")
            w.g(90, str(len(pts)))
            w.g(70, "1" if cerrada else "0")
            w.g(43, "0")
            for p in pts:
                w.g(10, _num(p[0]))
                w.g(20, _num(p[1]))
    elif tipo == "texto":
        _, p, altura, texto = prim[:4]
        rot = prim[4] if len(prim) > 4 else 0.0
        alin = {"izq": 0, "centro": 1, "der": 2}.get(prim[5] if len(prim) > 5 else "izq", 0)
        w.cabecera_entidad("TEXT", capa, dueno, "AcDbText")
        w.punto(10, p)
        w.g(40, _num(altura))
        w.g(1, _cadena(texto))
        if rot:
            w.g(50, _num(rot % 360.0))
        w.g(7, "Standard" if not w.r12 else "STANDARD")
        if alin:
            w.g(72, str(alin))
            w.punto(11, p)
        if not w.r12:
            w.g(100, "AcDbText")
    elif tipo == "elipse":
        _, c, m, razon, t0, t1 = prim
        if w.r12:
            completa = abs((t1 - t0) - 2 * math.pi) < 1e-9 or abs(t1 - t0) < 1e-12
            _entidad(w, capa, ("polilinea", _puntos_elipse(c, m, razon, t0, t0 + 2 * math.pi if completa else t1),
                               completa), dueno)
            return
        w.cabecera_entidad("ELLIPSE", capa, dueno, "AcDbEllipse")
        w.punto(10, c)
        w.punto(11, m)
        w.g(210, "0")
        w.g(220, "0")
        w.g(230, "1")
        w.g(40, _num(razon))
        w.g(41, _num(t0))
        w.g(42, _num(t1))
    elif tipo == "solido":
        pts = [tuple(p) for p in prim[1]]
        if len(pts) < 3:
            return
        orden = [pts[0], pts[1], pts[2], pts[2]] if len(pts) == 3 else [pts[0], pts[1], pts[3], pts[2]]
        w.cabecera_entidad("SOLID", capa, dueno, "AcDbTrace")
        for k, p in enumerate(orden):
            w.punto(10 + k, p)
    else:
        raise ErrorDXF(f"Primitiva desconocida para DXF: {tipo}")


def _puntos_de(prim):
    t = prim[0]
    if t in ("linea",):
        return [prim[1], prim[2]]
    if t in ("circulo", "arco"):
        c, r = prim[1], prim[2]
        return [(c[0] - r, c[1] - r), (c[0] + r, c[1] + r)]
    if t in ("polilinea", "spline", "solido"):
        return list(prim[1])
    if t == "texto":
        return [prim[1]]
    if t == "elipse":
        c, m = prim[1], prim[2]
        r = math.hypot(*m)
        return [(c[0] - r, c[1] - r), (c[0] + r, c[1] + r)]
    return []


def _normalizar(entidades):
    salida = []
    for e in entidades:
        if isinstance(e, tuple) and len(e) == 2 and isinstance(e[0], str) and isinstance(e[1], tuple):
            salida.append((_nombre_capa(e[0]), e[1]))
        else:
            salida.append(("0", e))
    return salida


def _tablas_2000(w, capas_usadas, capas, ext):
    tablas_h = {}

    def tabla(nombre, n, extra=None):
        w.g(0, "TABLE")
        w.g(2, nombre)
        h = w.handle()
        tablas_h[nombre] = h
        w.g(5, h)
        w.g(330, "0")
        w.g(100, "AcDbSymbolTable")
        w.g(70, str(n))
        if extra:
            extra()
        return h

    def registro(tipo, th, subclase, nombre, codigo_handle=5):
        w.g(0, tipo)
        w.g(codigo_handle, w.handle())
        w.g(330, th)
        w.g(100, "AcDbSymbolTableRecord")
        w.g(100, subclase)
        w.g(2, nombre)
        w.g(70, "0")

    w.g(0, "SECTION")
    w.g(2, "TABLES")
    th = tabla("VPORT", 1)
    registro("VPORT", th, "AcDbViewportTableRecord", "*Active")
    (x0, y0), (x1, y1) = ext
    for c, v in ((10, 0), (20, 0), (11, 1), (21, 1), (12, (x0 + x1) / 2), (22, (y0 + y1) / 2), (13, 0), (23, 0),
                 (14, 10), (24, 10), (15, 10), (25, 10), (16, 0), (26, 0), (36, 1), (17, 0), (27, 0), (37, 0),
                 (40, max(y1 - y0, 1.0) * 1.1), (41, max((x1 - x0) / max(y1 - y0, 1.0), 0.1)), (42, 50), (43, 0),
                 (44, 0), (50, 0), (51, 0)):
        w.g(c, _num(v))
    for c, v in ((71, 0), (72, 100), (73, 1), (74, 3), (75, 0), (76, 0), (77, 0), (78, 0)):
        w.g(c, str(v))
    w.g(0, "ENDTAB")

    tipos = ["ByBlock", "ByLayer", "Continuous"] + [t for t in ("DASHED", "CENTER")
                                                    if any(TIPOS_LINEA.get(capas.get(c, {}).get("tipo"), "") == t
                                                           for c in capas_usadas)]
    th = tabla("LTYPE", len(tipos))
    for t in tipos:
        registro("LTYPE", th, "AcDbLinetypeTableRecord", t)
        desc, patron = _PATRONES.get(t, ("Continua" if t == "Continuous" else "", ()))
        w.g(3, desc)
        w.g(72, "65")
        w.g(73, str(len(patron)))
        w.g(40, _num(sum(abs(x) for x in patron)))
        for x in patron:
            w.g(49, _num(x))
            w.g(74, "0")
    w.g(0, "ENDTAB")

    nombres = ["0"] + [c for c in capas_usadas if c != "0"]
    th = tabla("LAYER", len(nombres))
    marcador_h = w.handle()   # ACDBPLACEHOLDER del estilo de trazado "Normal" (se escribe en OBJECTS)
    for n in nombres:
        conf = capas.get(n, {})
        registro("LAYER", th, "AcDbLayerTableRecord", n)
        w.g(62, str(int(conf.get("color", 7))))
        tipo = TIPOS_LINEA.get(conf.get("tipo", "continua"), "CONTINUOUS")
        w.g(6, "Continuous" if tipo == "CONTINUOUS" else tipo)
        grosor = int(round(float(conf.get("grosor", 0.25)) * 100))
        w.g(370, str(min(_GROSORES, key=lambda g: abs(g - grosor))))
        w.g(390, marcador_h)
    w.g(0, "ENDTAB")

    th = tabla("STYLE", 1)
    registro("STYLE", th, "AcDbTextStyleTableRecord", "Standard")
    for c, v in ((40, "0"), (41, "1"), (50, "0"), (71, "0"), (42, "2.5"), (3, "txt"), (4, "")):
        w.g(c, v)
    w.g(0, "ENDTAB")
    for nombre in ("VIEW", "UCS"):
        tabla(nombre, 0)
        w.g(0, "ENDTAB")
    th = tabla("APPID", 1)
    registro("APPID", th, "AcDbRegAppTableRecord", "ACAD")
    w.g(0, "ENDTAB")

    def marcador_dimstyle():
        w.g(100, "AcDbDimStyleTable")
        w.g(71, "0")
    th = tabla("DIMSTYLE", 1, marcador_dimstyle)
    registro("DIMSTYLE", th, "AcDbDimStyleTableRecord", "Standard", codigo_handle=105)
    w.g(0, "ENDTAB")

    th = tabla("BLOCK_RECORD", 2)
    bloques = {}
    for n in ("*Model_Space", "*Paper_Space"):
        w.g(0, "BLOCK_RECORD")
        h = w.handle()
        bloques[n] = h
        w.g(5, h)
        w.g(330, th)
        w.g(100, "AcDbSymbolTableRecord")
        w.g(100, "AcDbBlockTableRecord")
        w.g(2, n)
    w.g(0, "ENDTAB")
    w.g(0, "ENDSEC")
    return bloques, marcador_h


def a_texto_dxf(entidades, capas=None, version="2000"):
    """Contenido DXF (str) de las entidades; ver `escribir_dxf`."""
    capas = {_nombre_capa(k): v for k, v in (capas or {}).items()}
    ents = _normalizar(entidades)
    usadas = []
    for c, _ in ents:
        if c not in usadas:
            usadas.append(c)
    pts = [p for _, e in ents for p in _puntos_de(e)]
    if pts:
        ext = ((min(p[0] for p in pts), min(p[1] for p in pts)), (max(p[0] for p in pts), max(p[1] for p in pts)))
    else:
        ext = ((0.0, 0.0), (0.0, 0.0))
    w = _Escritor(version)
    cuerpo = _Escritor(version)
    cuerpo.h = w.h
    if w.r12:
        _tablas_r12(cuerpo, usadas, capas)
        dueno = None
    else:
        bloques, marcador_h = _tablas_2000(cuerpo, usadas, capas, ext)
        cuerpo.g(0, "SECTION")
        cuerpo.g(2, "BLOCKS")
        for n, extra in (("*Model_Space", False), ("*Paper_Space", True)):
            for tipo, sub in (("BLOCK", "AcDbBlockBegin"), ("ENDBLK", "AcDbBlockEnd")):
                cuerpo.g(0, tipo)
                cuerpo.g(5, cuerpo.handle())
                cuerpo.g(330, bloques[n])
                cuerpo.g(100, "AcDbEntity")
                if extra:
                    cuerpo.g(67, "1")
                cuerpo.g(8, "0")
                cuerpo.g(100, sub)
                if tipo == "BLOCK":
                    cuerpo.g(2, n)
                    cuerpo.g(70, "0")
                    cuerpo.punto(10, (0.0, 0.0))
                    cuerpo.g(3, n)
                    cuerpo.g(1, "")
        cuerpo.g(0, "ENDSEC")
        dueno = bloques["*Model_Space"]
    cuerpo.g(0, "SECTION")
    cuerpo.g(2, "ENTITIES")
    for capa, e in ents:
        _entidad(cuerpo, capa, e, dueno)
    cuerpo.g(0, "ENDSEC")
    if not w.r12:
        raiz, grupo, estilos = cuerpo.handle(), cuerpo.handle(), cuerpo.handle()
        cuerpo.g(0, "SECTION")
        cuerpo.g(2, "OBJECTS")
        for c, v in ((0, "DICTIONARY"), (5, raiz), (330, "0"), (100, "AcDbDictionary"), (281, "1"),
                     (3, "ACAD_GROUP"), (350, grupo), (3, "ACAD_PLOTSTYLENAME"), (350, estilos),
                     (0, "DICTIONARY"), (5, grupo), (330, raiz), (100, "AcDbDictionary"), (281, "1"),
                     (0, "ACDBDICTIONARYWDFLT"), (5, estilos), (330, raiz), (100, "AcDbDictionary"), (281, "1"),
                     (3, "Normal"), (350, marcador_h), (100, "AcDbDictionaryWithDefault"), (340, marcador_h),
                     (0, "ACDBPLACEHOLDER"), (5, marcador_h), (330, estilos)):
            cuerpo.g(c, v)
        cuerpo.g(0, "ENDSEC")
    cuerpo.g(0, "EOF")
    # cabecera al final: $HANDSEED tiene que superar a todos los handles usados
    w.g(0, "SECTION")
    w.g(2, "HEADER")
    w.g(9, "$ACADVER")
    w.g(1, "AC1009" if w.r12 else "AC1015")
    if not w.r12:
        w.g(9, "$DWGCODEPAGE")
        w.g(3, "ANSI_1252")
    w.g(9, "$INSBASE")
    w.punto(10, (0.0, 0.0))
    w.g(9, "$EXTMIN")
    w.punto(10, ext[0])
    w.g(9, "$EXTMAX")
    w.punto(10, ext[1])
    w.g(9, "$LIMMIN")
    w.g(10, "0")
    w.g(20, "0")
    w.g(9, "$LIMMAX")
    w.g(10, _num(max(ext[1][0], 1.0)))
    w.g(20, _num(max(ext[1][1], 1.0)))
    w.g(9, "$LTSCALE")
    w.g(40, "1")
    if not w.r12:
        w.g(9, "$INSUNITS")
        w.g(70, "4")
        w.g(9, "$MEASUREMENT")
        w.g(70, "1")
        w.g(9, "$HANDSEED")
        w.g(5, f"{cuerpo.h + 1:X}")
    w.g(0, "ENDSEC")
    if not w.r12:
        w.g(0, "SECTION")
        w.g(2, "CLASSES")
        w.g(0, "ENDSEC")
    return "".join(w.lineas + cuerpo.lineas)


def _tablas_r12(w, capas_usadas, capas):
    w.g(0, "SECTION")
    w.g(2, "TABLES")
    w.g(0, "TABLE")
    w.g(2, "LTYPE")
    w.g(70, "3")
    for t in ("CONTINUOUS", "DASHED", "CENTER"):
        desc, patron = _PATRONES.get(t, ("Continua", ()))
        for c, v in ((0, "LTYPE"), (2, t), (70, "0"), (3, desc), (72, "65"), (73, str(len(patron))),
                     (40, _num(sum(abs(x) for x in patron)))):
            w.g(c, v)
        for x in patron:
            w.g(49, _num(x))
    w.g(0, "ENDTAB")
    nombres = ["0"] + [c for c in capas_usadas if c != "0"]
    w.g(0, "TABLE")
    w.g(2, "LAYER")
    w.g(70, str(len(nombres)))
    for n in nombres:
        conf = capas.get(n, {})
        for c, v in ((0, "LAYER"), (2, n), (70, "0"), (62, str(int(conf.get("color", 7)))),
                     (6, TIPOS_LINEA.get(conf.get("tipo", "continua"), "CONTINUOUS"))):
            w.g(c, v)
    w.g(0, "ENDTAB")
    w.g(0, "TABLE")
    w.g(2, "STYLE")
    w.g(70, "1")
    for c, v in ((0, "STYLE"), (2, "STANDARD"), (70, "0"), (40, "0"), (41, "1"), (50, "0"), (71, "0"),
                 (42, "2.5"), (3, "txt"), (4, "")):
        w.g(c, v)
    w.g(0, "ENDTAB")
    w.g(0, "ENDSEC")


def escribir_dxf(ruta, entidades, capas=None, version="2000"):
    """Escribe un DXF ASCII en `ruta`.

    entidades: primitivas (van a la capa "0") o pares (capa, primitiva).
    capas: {nombre: {"color": ACI, "tipo": "continua" | "trazos" | "trazo_punto", "grosor": mm}} opcional
           (una capa usada sin datos queda blanca, continua y de 0,25 mm).
    version: "2000" (AC1015: LWPOLYLINE, ELLIPSE, grosores) o "R12" (AC1009, lo lee cualquier programa;
             polilíneas como POLYLINE y elipses aproximadas). Unidades: mm ($INSUNITS = 4)."""
    texto = a_texto_dxf(entidades, capas, version)
    Path(ruta).write_bytes(texto.encode("cp1252"))
    return Path(ruta)


# =============================================================== lector
def _pares(texto):
    lineas = texto.splitlines()
    pares = []
    for i in range(0, len(lineas) - 1, 2):
        cod = lineas[i].strip()
        if not cod:
            continue
        try:
            codigo = int(cod)
        except ValueError:
            raise ErrorDXF(f"DXF dañado: código de grupo no válido «{cod[:20]}» en la línea {i + 1}.") from None
        valor = lineas[i + 1]
        pares.append((codigo, valor if codigo in (1, 3) else valor.strip()))
    return pares


def _f(datos, codigo, defecto=0.0):
    for c, v in datos:
        if c == codigo:
            try:
                return float(v)
            except ValueError:
                return defecto
    return defecto


def _s(datos, codigo, defecto=""):
    for c, v in datos:
        if c == codigo:
            return v
    return defecto


def _todos(datos, codigo):
    salida = []
    for c, v in datos:
        if c == codigo:
            try:
                salida.append(float(v))
            except ValueError:
                pass
    return salida


_UNICODE = re.compile(r"\\U\+([0-9A-Fa-f]{4})")


def _texto_dxf(t):
    t = _UNICODE.sub(lambda m: chr(int(m.group(1), 16)), t)
    t = re.sub(r"%%[uUoOkK]", "", t)
    return (t.replace("%%c", "⌀").replace("%%C", "⌀").replace("%%d", "°").replace("%%D", "°")
             .replace("%%p", "±").replace("%%P", "±").replace("%%%", "%"))


def _texto_mtext(t):
    t = _UNICODE.sub(lambda m: chr(int(m.group(1), 16)), t)
    t = t.replace("\\P", "\n").replace("\\~", " ")
    t = re.sub(r"\\S([^^/#;]*)[\^/#]([^;]*);", r"\1/\2", t)
    t = re.sub(r"\\[ACFHQTWfacfhqtwp][^;]*;", "", t)
    t = re.sub(r"\\[LlOoKkNX]", "", t)
    t = t.replace("{", "").replace("}", "").replace("\\\\", "\\")
    return _texto_dxf(t)


def _puntos_bulge(p0, p1, bulge):
    """Puntos intermedios (sin p0, con p1) del tramo de polilínea con curvatura `bulge` (tan(θ/4))."""
    if abs(bulge) < 1e-12:
        return [p1]
    cuerda = math.dist(p0, p1)
    if cuerda < 1e-12:
        return [p1]
    theta = 4.0 * math.atan(bulge)
    m = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    ux, uy = (p1[0] - p0[0]) / cuerda, (p1[1] - p0[1]) / cuerda
    d = (cuerda / 2) / math.tan(theta / 2)
    c = (m[0] - uy * d, m[1] + ux * d)
    r = math.dist(c, p0)
    a0 = math.atan2(p0[1] - c[1], p0[0] - c[0])
    n = max(2, math.ceil(abs(theta) / _SEGMENTOS_ARCO))
    pts = [(c[0] + r * math.cos(a0 + theta * k / n), c[1] + r * math.sin(a0 + theta * k / n)) for k in range(1, n)]
    return pts + [p1]


def _polilinea_con_bulges(vertices, cerrada):
    """vertices: [(x, y, bulge)] → ('polilinea', puntos, cerrada) con los arcos aproximados."""
    if not vertices:
        return None
    pts = [(vertices[0][0], vertices[0][1])]
    tramos = list(zip(vertices, vertices[1:] + ([vertices[0]] if cerrada else []), strict=False))
    for k, (a, b) in enumerate(tramos):
        nuevos = _puntos_bulge((a[0], a[1]), (b[0], b[1]), a[2])
        if cerrada and k == len(tramos) - 1:
            nuevos = nuevos[:-1]      # el último vuelve al primero: no se repite
        pts += nuevos
    return ("polilinea", pts, cerrada)


def _de_boor(grado, nudos, ctrl, u):
    """Punto de la B-spline (coordenadas homogéneas) en u: algoritmo de De Boor."""
    k = len(ctrl) - 1
    while k > grado and not (nudos[k] <= u and nudos[k] < nudos[k + 1]):
        k -= 1
    d = [list(ctrl[j + k - grado]) for j in range(grado + 1)]
    for r in range(1, grado + 1):
        for j in range(grado, r - 1, -1):
            i = j + k - grado
            den = nudos[i + 1 + grado - r] - nudos[i]
            alfa = 0.0 if den == 0 else (u - nudos[i]) / den
            d[j] = [(1 - alfa) * a + alfa * b for a, b in zip(d[j - 1], d[j], strict=True)]
    return d[grado]


def _spline(datos):
    grado = int(_f(datos, 71, 3))
    nudos = _todos(datos, 40)
    xs, ys = _todos(datos, 10), _todos(datos, 20)
    pesos = _todos(datos, 41)
    cerrada = bool(int(_f(datos, 70, 0)) & 1)
    ctrl = list(zip(xs, ys, strict=False))
    if len(ctrl) >= 2 and len(nudos) == len(ctrl) + grado + 1 and grado >= 1:
        if len(pesos) != len(ctrl):
            pesos = [1.0] * len(ctrl)
        homog = [(x * w, y * w, w) for (x, y), w in zip(ctrl, pesos, strict=True)]
        u0, u1 = nudos[grado], nudos[len(ctrl)]
        n = max(16, 8 * len(ctrl))
        pts = []
        for k in range(n + 1):
            x, y, w = _de_boor(grado, nudos, homog, u0 + (u1 - u0) * k / n)
            pts.append((x / w, y / w) if w else (x, y))
        return ("polilinea", pts, cerrada)
    ajuste = list(zip(_todos(datos, 11), _todos(datos, 21), strict=False))
    if len(ajuste) >= 2:
        return ("polilinea", ajuste, cerrada)
    return ("polilinea", ctrl, cerrada) if len(ctrl) >= 2 else None


def _elipse(datos):
    c = (_f(datos, 10), _f(datos, 20))
    m = (_f(datos, 11), _f(datos, 21))
    razon = _f(datos, 40, 1.0)
    t0, t1 = _f(datos, 41, 0.0), _f(datos, 42, 2 * math.pi)
    resto = (t1 - t0) % (2 * math.pi)
    completa = resto < 1e-5 or 2 * math.pi - resto < 1e-5     # los parámetros llegan redondeados
    if completa:
        t1 = t0 + 2 * math.pi
    pts = _puntos_elipse(c, m, razon, t0, t1, _f(datos, 230, 1.0))
    return ("polilinea", pts[:-1] if completa else pts, completa)


def _arco_normalizado(c, r, a0, a1):
    a0 = a0 % (2 * math.pi)
    barrido = (a1 - a0) % (2 * math.pi)
    if barrido < 1e-12:
        barrido = 2 * math.pi
    return ("arco", c, r, a0, a0 + barrido)


def _espejar_x(prim):
    """OCS con extrusión (0, 0, −1): la X del sistema del objeto es la −X del mundo."""
    return _transformar(prim, lambda p: (-p[0], p[1]), 1.0, True)


def _transformar(prim, f, escala, espejo):
    """Aplica una transformación afín (f sobre puntos, factor de escala uniforme y si invierte el sentido)."""
    t = prim[0]
    if t == "linea":
        return ("linea", f(prim[1]), f(prim[2]))
    if t == "polilinea":
        return ("polilinea", [f(p) for p in prim[1]], prim[2])
    if t == "texto":
        return ("texto", f(prim[1]), prim[2] * abs(escala), prim[3])
    if t in ("circulo", "arco"):
        if escala is None:   # escala no uniforme: se aproxima con polilínea
            c, r = prim[1], prim[2]
            a0, a1 = (0.0, 2 * math.pi) if t == "circulo" else (prim[3], prim[4])
            n = max(8, math.ceil((a1 - a0) / _SEGMENTOS_ARCO))
            pts = [f((c[0] + r * math.cos(a0 + (a1 - a0) * k / n), c[1] + r * math.sin(a0 + (a1 - a0) * k / n)))
                   for k in range(n + (0 if t == "circulo" else 1))]
            return ("polilinea", pts, t == "circulo")
        c = f(prim[1])
        r = prim[2] * abs(escala)
        if t == "circulo":
            return ("circulo", c, r)
        angulos = []
        for a in (prim[3], prim[4]):
            q = f((prim[1][0] + prim[2] * math.cos(a), prim[1][1] + prim[2] * math.sin(a)))
            angulos.append(math.atan2(q[1] - c[1], q[0] - c[0]))
        a0, a1 = (angulos[1], angulos[0]) if espejo else angulos
        return _arco_normalizado(c, r, a0, a1)
    return prim


def _ocs(prim, datos):
    return _espejar_x(prim) if _f(datos, 230, 1.0) < -0.5 else prim


def _convertir(tipo, datos, extra, bloques, profundidad):
    """Una entidad DXF → lista de primitivas."""
    if tipo == "LINE":
        return [("linea", (_f(datos, 10), _f(datos, 20)), (_f(datos, 11), _f(datos, 21)))]
    if tipo == "CIRCLE":
        return [_ocs(("circulo", (_f(datos, 10), _f(datos, 20)), _f(datos, 40)), datos)]
    if tipo == "ARC":
        arco = _arco_normalizado((_f(datos, 10), _f(datos, 20)), _f(datos, 40), math.radians(_f(datos, 50)),
                                 math.radians(_f(datos, 51, 360.0)))
        return [_ocs(arco, datos)]
    if tipo == "LWPOLYLINE":
        vertices = []
        for c, v in datos:
            if c == 10:
                vertices.append([float(v), 0.0, 0.0])
            elif c == 20 and vertices:
                vertices[-1][1] = float(v)
            elif c == 42 and vertices:
                vertices[-1][2] = float(v)
        p = _polilinea_con_bulges([tuple(x) for x in vertices], bool(int(_f(datos, 70, 0)) & 1))
        return [_ocs(p, datos)] if p else []
    if tipo == "POLYLINE":
        banderas = int(_f(datos, 70, 0))
        if banderas & (16 | 64):     # mallas 3D y caras múltiples: no son geometría 2D
            return []
        vertices = [(_f(d, 10), _f(d, 20), _f(d, 42)) for d in extra]
        p = _polilinea_con_bulges(vertices, bool(banderas & 1))
        return [_ocs(p, datos)] if p else []
    if tipo == "ELLIPSE":
        return [_elipse(datos)]
    if tipo == "SPLINE":
        s = _spline(datos)
        return [s] if s else []
    if tipo in ("TEXT", "ATTRIB"):
        alin = int(_f(datos, 72, 0)) or int(_f(datos, 73 if tipo == "TEXT" else 74, 0))
        alineado = alin and any(c == 11 for c, _ in datos)      # con justificación vale el punto 11/21
        p = (_f(datos, 11), _f(datos, 21)) if alineado else (_f(datos, 10), _f(datos, 20))
        return [_ocs(("texto", p, _f(datos, 40, 2.5), _texto_dxf(_s(datos, 1))), datos)]
    if tipo == "MTEXT":
        cuerpo = "".join(v for c, v in datos if c == 3) + _s(datos, 1)
        return [("texto", (_f(datos, 10), _f(datos, 20)), _f(datos, 40, 2.5), _texto_mtext(cuerpo))]
    if tipo in ("SOLID", "TRACE", "3DFACE"):
        p = [(_f(datos, 10 + k), _f(datos, 20 + k)) for k in range(4)]
        orden = p if tipo == "3DFACE" else [p[0], p[1], p[3], p[2]]   # SOLID se recorre 1-2-4-3
        unicos = [q for k, q in enumerate(orden) if q not in orden[:k]]
        return [_ocs(("polilinea", unicos, True), datos)] if len(unicos) >= 2 else []
    if tipo in ("INSERT", "DIMENSION"):
        nombre = _s(datos, 2)
        if nombre not in bloques or profundidad > 8:
            return []
        base, contenido = bloques[nombre]
        geometria = []
        for t, d, e in contenido:
            geometria += _convertir(t, d, e, bloques, profundidad + 1)
        if tipo == "DIMENSION":      # el bloque de la cota ya está en coordenadas del mundo
            return geometria
        sx, sy = _f(datos, 41, 1.0), _f(datos, 42, 1.0)
        rot = math.radians(_f(datos, 50, 0.0))
        ins = (_f(datos, 10), _f(datos, 20))
        cr, sr = math.cos(rot), math.sin(rot)

        def f(p):
            x, y = (p[0] - base[0]) * sx, (p[1] - base[1]) * sy
            return (ins[0] + x * cr - y * sr, ins[1] + x * sr + y * cr)

        uniforme = abs(abs(sx) - abs(sy)) < 1e-9
        salida = [_transformar(g, f, abs(sx) if uniforme else None, sx * sy < 0) for g in geometria]
        return [_ocs(g, datos) for g in salida]
    return []


def leer_dxf_texto(texto, con_capas=False, a_mm=True):
    """Como `leer_dxf`, pero desde el contenido del archivo (str)."""
    pares = _pares(texto)
    seccion, i = None, 0
    unidades = 0
    bloques = {}          # nombre → (punto base, [(tipo, datos, extra)])
    entidades = []        # [(capa, tipo, datos, extra)]
    bloque_actual = None
    n = len(pares)
    while i < n:
        codigo, valor = pares[i]
        if codigo == 0 and valor == "SECTION":
            seccion = pares[i + 1][1] if i + 1 < n and pares[i + 1][0] == 2 else None
            i += 2
            continue
        if codigo == 0 and valor == "ENDSEC":
            seccion = None
            i += 1
            continue
        if seccion == "HEADER" and codigo == 9 and valor == "$INSUNITS" and i + 1 < n:
            try:
                unidades = int(float(pares[i + 1][1]))
            except ValueError:
                unidades = 0
            i += 2
            continue
        if codigo != 0 or seccion not in ("ENTITIES", "BLOCKS"):
            i += 1
            continue
        tipo = valor
        j = i + 1
        datos = []
        while j < n and pares[j][0] != 0:
            datos.append(pares[j])
            j += 1
        i = j
        extra = []
        if tipo == "POLYLINE":
            while i < n and pares[i][0] == 0 and pares[i][1] in ("VERTEX", "SEQEND"):
                t = pares[i][1]
                j = i + 1
                d = []
                while j < n and pares[j][0] != 0:
                    d.append(pares[j])
                    j += 1
                i = j
                if t == "SEQEND":
                    break
                extra.append(d)
        if seccion == "BLOCKS":
            if tipo == "BLOCK":
                bloque_actual = _s(datos, 2)
                bloques[bloque_actual] = ((_f(datos, 10), _f(datos, 20)), [])
            elif tipo == "ENDBLK":
                bloque_actual = None
            elif bloque_actual is not None:
                bloques[bloque_actual][1].append((tipo, datos, extra))
            continue
        entidades.append((_s(datos, 8, "0"), tipo, datos, extra))
    k = _UNIDADES.get(unidades, 1.0) if a_mm else 1.0
    salida = []
    for capa, tipo, datos, extra in entidades:
        if int(_f(datos, 67, 0)):      # entidades del espacio papel: no son el dibujo del modelo
            continue
        for p in _convertir(tipo, datos, extra, bloques, 0):
            if k != 1.0:
                p = _transformar(p, lambda q, k=k: (q[0] * k, q[1] * k), k, False)
            if p[0] == "texto":
                p = ("texto", (float(p[1][0]), float(p[1][1])), float(p[2]), p[3])
            salida.append((_texto_dxf(capa), p) if con_capas else p)
    return salida


def leer_dxf(ruta, con_capas=False, a_mm=True):
    """Lee la geometría 2D de un DXF ASCII (cualquier versión): lista de primitivas, o de pares
    (capa, primitiva) con con_capas=True. Con a_mm=True convierte según $INSUNITS (pulgadas, cm, m…).
    Ignora la Z, el espacio papel y las entidades sin equivalente 2D (HATCH, IMAGE, 3DSOLID…)."""
    datos = Path(ruta).read_bytes()
    if datos.startswith(b"AutoCAD Binary DXF"):
        raise ErrorDXF("El DXF es binario: guardalo como DXF ASCII para importarlo.")
    try:
        texto = datos.decode("utf-8")
    except UnicodeDecodeError:
        texto = datos.decode("cp1252", errors="replace")
    if texto.startswith("\ufeff"):
        texto = texto[1:]
    if "SECTION" not in texto:
        raise ErrorDXF("El archivo no parece un DXF (no tiene secciones).")
    return leer_dxf_texto(texto, con_capas, a_mm)
