# -*- coding: utf-8 -*-
"""Lectura/escritura STEP, IGES y BREP a nivel kernel (la capa io_archivos los usa para archivos de usuario)."""
import os
import re
import tempfile

from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.IFSelect import IFSelect_RetDone
from OCP.IGESControl import IGESControl_Reader
from OCP.Interface import Interface_Static
from OCP.Message import Message
from OCP.OCP.collections import Sequence_TDF_Label
from OCP.Quantity import Quantity_Color
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Iterator, TopoDS_Shape
from OCP.TopTools import TopTools_FormatVersion
from OCP.XCAFDoc import XCAFDoc_ColorTool, XCAFDoc_ColorType, XCAFDoc_DocumentTool

from .geometria import ErrorGeometria, caras, solidos


def _silenciar_kernel():
    """OpenCascade imprime estadísticas de STEP por consola; se quitan los impresores por defecto."""
    mensajero = Message.DefaultMessenger_s()
    impresoras = mensajero.Printers()
    for i in range(impresoras.Size(), 0, -1):
        try:
            mensajero.RemovePrinter(impresoras.Value(i))
        except Exception:  # noqa: BLE001 — si la API cambia, solo queda el ruido en consola
            break


_silenciar_kernel()


def escribir_step(forma, ruta):
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    w = STEPControl_Writer()
    if w.Transfer(forma, STEPControl_AsIs) != IFSelect_RetDone:
        raise ErrorGeometria("No se pudo convertir la geometría a STEP.")
    if w.Write(str(ruta)) != IFSelect_RetDone:
        raise ErrorGeometria(f"No se pudo escribir el archivo STEP: {ruta}")


def leer_step(ruta):
    r = STEPControl_Reader()
    if r.ReadFile(str(ruta)) != IFSelect_RetDone:
        raise ErrorGeometria(f"No se pudo leer el archivo STEP: {ruta}")
    r.TransferRoots()
    forma = r.OneShape()
    if forma is None or forma.IsNull():
        raise ErrorGeometria("El archivo STEP no contiene geometría.")
    return forma


def leer_step_texto(texto):
    """Lee un STEP guardado como texto (la operación de importación lo embebe en la receta)."""
    fd, ruta = tempfile.mkstemp(suffix=".step")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
        return leer_step(ruta)
    finally:
        os.remove(ruta)


def leer_iges(ruta):
    """IGES → forma (en mm: el lector de OpenCascade convierte desde la unidad del archivo)."""
    r = IGESControl_Reader()
    if r.ReadFile(str(ruta)) != IFSelect_RetDone:
        raise ErrorGeometria(f"No se pudo leer el archivo IGES: {ruta}")
    r.TransferRoots()
    forma = r.OneShape()
    if forma is None or forma.IsNull():
        raise ErrorGeometria("El archivo IGES no contiene geometría.")
    return forma


def leer_iges_texto(texto):
    """Lee un IGES guardado como texto (la operación de importación lo embebe en la receta)."""
    return _desde_texto(texto, ".igs", leer_iges)


def _desde_texto(texto, sufijo, lector):
    fd, ruta = tempfile.mkstemp(suffix=sufijo)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
        return lector(ruta)
    finally:
        os.remove(ruta)


def _nombre_xcaf(etiqueta):
    attr = TDataStd_Name()
    if not etiqueta.FindAttribute(TDataStd_Name.GetID_s(), attr):
        return ""
    nombre = attr.Get().ToExtString().strip()
    return "" if nombre.startswith("=>") else nombre     # «=>[0:1:1:2]»: nombre automático de una instancia


def _color_xcaf(etiqueta):
    color = Quantity_Color()
    for tipo in (XCAFDoc_ColorType.XCAFDoc_ColorSurf, XCAFDoc_ColorType.XCAFDoc_ColorGen):
        if XCAFDoc_ColorTool.GetColor_s(etiqueta, tipo, color):
            return (round(color.Red(), 4), round(color.Green(), 4), round(color.Blue(), 4))
    return None


_ENTIDAD = re.compile(r"\s*#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*)\)\s*$", re.S)
_REF = re.compile(r"#(\d+)")
_TEXTO = re.compile(r"'((?:[^']|'')*)'")
_SOLIDOS_STEP = ("MANIFOLD_SOLID_BREP", "BREP_WITH_VOIDS", "FACETED_BREP")
_PRODUCTO_STEP = ("PRODUCT", "PRODUCT_DEFINITION_FORMATION", "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE",
                  "PRODUCT_DEFINITION", "PRODUCT_DEFINITION_SHAPE", "SHAPE_DEFINITION_REPRESENTATION",
                  "SHAPE_REPRESENTATION_RELATIONSHIP")


def nombres_solidos_step(texto):
    """{nombre de producto: [nombres de sus sólidos, en orden]} leyendo el texto del STEP. Fusion guarda el nombre de
    cada cuerpo en su MANIFOLD_SOLID_BREP, pero OpenCascade 8 (desde Python) solo cuelga del árbol los nombres de
    los productos: un componente con varios cuerpos llega como un compuesto, con los sólidos en el mismo orden en
    que los lista su representación."""
    tipos, args = {}, {}
    # Los saltos de línea del STEP no cuentan, tampoco dentro de un texto: un nombre largo llega partido en dos líneas.
    texto = texto.replace("\r", "").replace("\n", "")
    for sentencia in texto.split(";"):
        m = _ENTIDAD.match(sentencia)
        if m is None:
            continue
        tipo = m.group(2)
        if tipo in _SOLIDOS_STEP or tipo in _PRODUCTO_STEP or tipo.endswith("SHAPE_REPRESENTATION"):
            tipos[int(m.group(1))], args[int(m.group(1))] = tipo, m.group(3)

    def refs(i):
        return [int(r) for r in _REF.findall(args.get(i, ""))]

    def texto_n(i, n=0):
        t = _TEXTO.findall(args.get(i, ""))
        return t[n].replace("''", "'") if len(t) > n else ""

    vecinos = {}
    for i, t in tipos.items():
        if t == "SHAPE_REPRESENTATION_RELATIONSHIP" and len(refs(i)) >= 2:
            a, b = refs(i)[:2]
            vecinos.setdefault(a, []).append(b)
            vecinos.setdefault(b, []).append(a)
    resultado = {}
    for i, t in tipos.items():
        if t != "SHAPE_DEFINITION_REPRESENTATION" or len(refs(i)) < 2:
            continue
        pds, rep = refs(i)[:2]
        cadena = [pds]
        for esperado in ("PRODUCT_DEFINITION_SHAPE", "PRODUCT_DEFINITION", "PRODUCT_DEFINITION_FORMATION", "PRODUCT"):
            actual = cadena[-1]
            if not tipos.get(actual, "").startswith(esperado):
                break
            if esperado != "PRODUCT":
                cadena.append((refs(actual) or [0])[0])
        producto = cadena[-1]
        if tipos.get(producto) != "PRODUCT":
            continue
        nombres, vistos, cola = [], set(), [rep]
        while cola:
            r = cola.pop(0)
            if r in vistos:
                continue
            vistos.add(r)
            if tipos.get(r, "").endswith("SHAPE_REPRESENTATION"):
                resto = _TEXTO.sub("''", args[r], count=1)          # el nombre puede tener paréntesis
                lista = resto.split("(", 1)[1].split(")", 1)[0] if "(" in resto else ""
                nombres += [texto_n(int(s)) for s in _REF.findall(lista) if tipos.get(int(s)) in _SOLIDOS_STEP]
            cola += vecinos.get(r, [])
        if nombres:
            for clave in {texto_n(producto, 0), texto_n(producto, 1)} - {""}:
                resultado.setdefault(clave, nombres)
    return resultado


def leer_step_estructura(ruta):
    """STEP con su árbol (XCAF): nombres de piezas, colores y componentes (ensamblajes), como los guarda Fusion.
    Devuelve {"componentes": [{"id", "nombre", "padre"}], "cuerpos": [{"nombre", "forma", "color", "componente"}]}
    con las formas ya ubicadas en el mundo, en mm; `color` es (r, g, b) 0..1 o None y `componente` el id
    del componente que la contiene ("" = raíz). Si el archivo tiene un solo ensamblaje raíz, ese es el diseño:
    sus hijos quedan en la raíz (como en Fusion, el componente raíz no es un componente más)."""
    doc = TDocStd_Document(TCollection_ExtendedString("XmlXCAF"))
    r = STEPCAFControl_Reader()
    r.SetNameMode(True)
    r.SetColorMode(True)
    if r.ReadFile(str(ruta)) != IFSelect_RetDone or not r.Transfer(doc):
        raise ErrorGeometria(f"No se pudo leer el archivo STEP: {ruta}")
    herramienta = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    try:
        nombres_cuerpos = nombres_solidos_step(open(ruta, encoding="utf-8", errors="replace").read())
    except OSError:
        nombres_cuerpos = {}
    componentes, cuerpos = [], []

    def recorrer(etiqueta, ubicacion, nombre, color, componente):
        color = _color_xcaf(etiqueta) or color
        if herramienta.IsAssembly_s(etiqueta):
            if componente is not None:            # None = raíz del diseño: sus hijos van a la raíz
                componentes.append({"id": f"k{len(componentes) + 1}", "nombre": nombre or f"Componente{len(componentes) + 1}",
                                    "padre": componente})
                componente = componentes[-1]["id"]
            hijos = Sequence_TDF_Label()
            herramienta.GetComponents_s(etiqueta, hijos, False)
            for i in range(1, hijos.Length() + 1):
                instancia, referida = hijos.Value(i), TDF_Label()
                herramienta.GetReferredShape_s(instancia, referida)
                recorrer(referida, ubicacion.Multiplied(herramienta.GetLocation_s(instancia)),
                         _nombre_xcaf(instancia) or _nombre_xcaf(referida), _color_xcaf(instancia) or color,
                         componente or "")
            return
        forma = herramienta.GetShape_s(etiqueta)
        if forma.IsNull():
            return
        forma = forma.Moved(ubicacion)
        # Un producto sin geometría (en Fusion, un componente cuyos cuerpos están ocultos) no crea un cuerpo vacío.
        partes = [(s, "solido") for s in solidos(forma)] or ([(forma, "superficie")] if caras(forma) else [])
        propios = nombres_cuerpos.get(_nombre_xcaf(etiqueta), [])
        if len(propios) != len(partes) or not all(propios):
            propios = [(nombre + (f" ({k})" if len(partes) > 1 else "")) if nombre else "" for k in range(1, len(partes) + 1)]
        for (parte, tipo), nombre_cuerpo in zip(partes, propios, strict=True):
            cuerpos.append({"nombre": nombre_cuerpo, "forma": parte, "tipo": tipo, "color": color,
                            "componente": componente or ""})

    libres = Sequence_TDF_Label()
    herramienta.GetFreeShapes(libres)
    raiz_unica = libres.Length() == 1 and herramienta.IsAssembly_s(libres.Value(1))
    for i in range(1, libres.Length() + 1):
        etiqueta = libres.Value(i)
        recorrer(etiqueta, TopLoc_Location(), _nombre_xcaf(etiqueta), None, None if raiz_unica else "")
    if not cuerpos:
        raise ErrorGeometria("El archivo STEP no contiene geometría.")
    return {"componentes": componentes, "cuerpos": cuerpos}


def leer_step_estructura_texto(texto):
    return _desde_texto(texto, ".step", leer_step_estructura)


def escribir_brep(forma, ruta):
    """Forma → archivo BREP (texto, el formato de siempre). Sin la malla de pantalla de las caras: el visor la rehace
    al mostrar y duplicaba el tamaño de la caché del proyecto. OCC guarda igual la triangulación de las caras que no
    tienen superficie (las que son solo malla), así que no se pierde geometría."""
    if not BRepTools.Write_s(forma, str(ruta), False, False, TopTools_FormatVersion.TopTools_FormatVersion_VERSION_1):
        raise ErrorGeometria(f"No se pudo escribir el BREP: {ruta}")


def leer_brep(ruta):
    forma = TopoDS_Shape()
    if not BRepTools.Read_s(forma, str(ruta), BRep_Builder()):
        raise ErrorGeometria(f"No se pudo leer el BREP: {ruta}")
    return forma


def partes_de_brep(ruta):
    """Las formas de un BREP que guardó un compuesto (`escribir_brep(geo.compuesto(formas), ruta)`), en el mismo
    orden en que entraron."""
    compuesto = leer_brep(ruta)       # vivo mientras se recorre: el iterador no retiene la forma que recorre
    it, partes = TopoDS_Iterator(compuesto), []
    while it.More():
        partes.append(it.Value())
        it.Next()
    return partes


def brep_a_texto(forma):
    """Forma OCC → texto BREP comprimido (zlib + base64) para guardarla dentro de la receta."""
    import base64
    import zlib
    fd, ruta = tempfile.mkstemp(suffix=".brep")
    os.close(fd)
    try:
        escribir_brep(forma, ruta)
        with open(ruta, "rb") as f:
            return base64.b64encode(zlib.compress(f.read(), 6)).decode("ascii")
    finally:
        os.remove(ruta)


def forma_de_texto(texto):
    import base64
    import zlib
    fd, ruta = tempfile.mkstemp(suffix=".brep")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(zlib.decompress(base64.b64decode(texto)))
        return leer_brep(ruta)
    finally:
        os.remove(ruta)
