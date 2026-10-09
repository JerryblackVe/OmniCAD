# -*- coding: utf-8 -*-
"""
Archivo › Abrir para archivos que no son proyectos de OmniCAD: cada uno crea un documento nuevo con UN paso
en el timeline (como Fusion, que al abrir un STEP o un STL crea un diseño nuevo con su paso de importación).

  STEP (.step/.stp)   → Importar STEP con nombres, colores y componentes (XCAF)
  IGES (.iges/.igs)   → Importar IGES
  Mallas (.stl/.obj/.3mf/.ply) → Insertar malla (las unidades del archivo se eligen; el 3MF trae las suyas)
  DXF (.dxf)          → Boceto sobre el plano XY
  Fusion (.f3d/.f3z)  → Fusion 360 instalado lo convierte a STEP por el puente (`puente_fusion`) y se crean
                        sus parámetros de usuario. El historial de pasos de Fusion NO se traduce.

Sin Qt: lo usan la ventana, la API, la CLI y el MCP.
"""
import math
from pathlib import Path

from ..nucleo import geometria as geo
from ..nucleo import malla
from ..timeline.documento import Documento
from ..timeline.operaciones import OpBoceto, OpImportarSTEP
from ..timeline.ops_insertar import OpImportarIGES
from ..timeline.ops_malla import OpInsertarMalla
from ..timeline.parametros import ANGULO, ESCALAR, LONGITUD, ErrorExpresion, TablaParametros
from . import puente_fusion
from .dxf import leer_dxf

FORMATOS = {".step": "STEP", ".stp": "STEP", ".iges": "IGES", ".igs": "IGES", ".stl": "STL", ".obj": "OBJ",
            ".3mf": "3MF", ".ply": "PLY", ".dxf": "DXF", ".f3d": "Fusion 360", ".f3z": "Fusion 360"}
MALLAS = (".stl", ".obj", ".3mf", ".ply")
UNIDADES_MALLA = ("mm", "cm", "m", "pulgadas", "pies")
_LONGITUDES_FUSION = {"mm", "cm", "m", "in", "ft"}
_TOLERANCIA_VOLUMEN = 0.01            # con Fusion: 1 % (en superficies libres los núcleos difieren ~0,5 %)


class ErrorAbrir(ValueError):
    """No se pudo abrir el archivo: el mensaje dice por qué y qué hacer."""


def es_externo(ruta):
    return Path(ruta).suffix.lower() in FORMATOS


def pide_unidades(ruta):
    """Las mallas sin unidades en el archivo (STL, OBJ, PLY) necesitan que se elija la unidad."""
    return Path(ruta).suffix.lower() in (".stl", ".obj", ".ply")


def documento_desde_archivo(ruta, unidades="mm"):
    """Abre `ruta` como documento nuevo. Devuelve (documento, avisos). Lanza ErrorAbrir o
    puente_fusion.ErrorPuenteFusion (Fusion no disponible: el mensaje trae los pasos para hacerlo a mano)."""
    ruta = Path(ruta)
    ext = ruta.suffix.lower()
    if ext not in FORMATOS:
        raise ErrorAbrir(f"Formato no soportado: {ext or '(sin extensión)'}. "
                         f"Se abren: .omnicad, {', '.join(sorted(FORMATOS))}.")
    if not ruta.is_file():
        raise ErrorAbrir(f"No existe el archivo: {ruta}")
    doc, avisos = Documento(), []
    doc.nombre = ruta.stem
    nombre = f"Importar {ruta.name}"
    fusion = None
    if ext in (".step", ".stp"):
        op = OpImportarSTEP(doc.nuevo_id(), nombre, archivo=ruta.name, contenido=_texto(ruta), estructura=True)
    elif ext in (".iges", ".igs"):
        op = OpImportarIGES(doc.nuevo_id(), nombre, archivo=ruta.name, contenido=_texto(ruta))
    elif ext in MALLAS:
        op = OpInsertarMalla(doc.nuevo_id(), f"Insertar {ruta.name}", archivo=ruta.stem, datos=_malla(ruta, unidades))
    elif ext == ".dxf":
        op = OpBoceto(doc.nuevo_id(), "Boceto1", boceto=_boceto_dxf(ruta), plano="XY")
    else:
        fusion = puente_fusion.convertir(ruta)
        op = OpImportarSTEP(doc.nuevo_id(), nombre, archivo=ruta.name, contenido=fusion["step_texto"], estructura=True)
        doc.parametros, extra = parametros_desde_fusion(fusion.get("parametros") or [])
        avisos += extra
        avisos.append("El historial de pasos de Fusion no se traduce todavía: entra la forma y los parámetros de "
                      "usuario (que no mueven la geometría importada).")
    doc.operaciones = [op]
    doc.marcador = 1
    doc.recalcular(0)
    r = doc.resultados[0]
    if r.estado == "error":
        raise ErrorAbrir(f"No se pudo leer {ruta.name}: {r.mensaje}")
    if r.estado == "aviso":
        avisos.append(r.mensaje)
    if fusion is not None:
        avisos += comparar_con_fusion(doc, fusion.get("cuerpos") or [])
    doc.modificado = False
    return doc, avisos


def _texto(ruta):
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise ErrorAbrir(f"No se pudo leer {ruta.name}: {e}") from None


def _malla(ruta, unidades):
    if unidades not in UNIDADES_MALLA:
        raise ErrorAbrir(f"Unidades de malla inválidas: {unidades} (usá {', '.join(UNIDADES_MALLA)}).")
    try:
        m = malla.leer(ruta) if ruta.suffix.lower() == ".3mf" else malla.leer(ruta, unidades=unidades)
    except (geo.ErrorGeometria, OSError, ValueError) as e:
        raise ErrorAbrir(f"No se pudo leer la malla {ruta.name}: {e}") from None
    return m.a_dict()


def _boceto_dxf(ruta):
    from .boceto_archivos import boceto_desde_primitivas
    try:
        primitivas = leer_dxf(ruta)
    except (ValueError, OSError) as e:
        raise ErrorAbrir(f"No se pudo leer el DXF {ruta.name}: {e}") from None
    if not primitivas:
        raise ErrorAbrir(f"El DXF {ruta.name} no tiene geometría 2D que se pueda leer.")
    return boceto_desde_primitivas(primitivas)


# ---------------------------------------------------------------- parámetros de Fusion
def _tipo_y_valor(p):
    """(tipo de OmniCAD, valor en mm/grados/número) de un parámetro de Fusion; valor en unidades internas de
    Fusion: cm para longitudes y radianes para ángulos. (None, None) si la unidad no es de longitud ni ángulo."""
    unidad, valor = (p.get("unidad") or "").strip(), p.get("valor")
    if not isinstance(valor, (int, float)):
        return None, None
    if unidad in _LONGITUDES_FUSION:
        return LONGITUD, valor * 10.0
    if unidad in ("deg", "rad"):
        return ANGULO, math.degrees(valor)
    if unidad == "":
        return ESCALAR, float(valor)
    return None, None


def _como_numero(tipo, valor):
    texto = f"{valor:.10g}"
    return {LONGITUD: f"{texto} mm", ANGULO: f"{texto} deg"}.get(tipo, texto)


def parametros_desde_fusion(lista):
    """Parámetros de usuario de Fusion → (TablaParametros, avisos). Se conserva la expresión si OmniCAD la entiende
    y da el MISMO valor que en Fusion; si no, queda el valor y el aviso dice cuál era la expresión. (En Fusion un
    número sin unidad toma la unidad del parámetro, p. ej. «2» en pulgadas: acá se compara para no equivocarse.)"""
    avisos, esperados, pendientes = [], {}, []
    for p in lista:
        nombre = str(p.get("nombre") or "")
        tipo, valor = _tipo_y_valor(p)
        if tipo is None:
            avisos.append(f"Parámetro «{nombre}» no se trajo: su unidad «{p.get('unidad')}» no es de longitud ni de ángulo.")
            continue
        esperados[nombre] = (tipo, valor)
        pendientes.append((nombre, str(p.get("expresion") or ""), tipo, str(p.get("comentario") or "")))
    tabla = TablaParametros()
    # Varias pasadas: un parámetro puede usar otro que viene más abajo en la lista.
    while pendientes:
        quedan = []
        for nombre, expr, tipo, comentario in pendientes:
            try:
                tabla.agregar(nombre, expr, tipo, comentario)
            except ErrorExpresion:
                quedan.append((nombre, expr, tipo, comentario))
        if len(quedan) == len(pendientes):
            break
        pendientes = quedan
    for nombre, expr, tipo, comentario in pendientes:
        try:
            tabla.agregar(nombre, _como_numero(tipo, esperados[nombre][1]), tipo, comentario)
            avisos.append(f"Parámetro «{nombre}»: la expresión «{expr}» no se pudo leer; quedó el valor.")
        except ErrorExpresion as e:
            del esperados[nombre]
            avisos.append(f"Parámetro «{nombre}» no se trajo: {e}")
    # Que cada uno valga lo mismo que en Fusion; si no, se fija el valor (y los que lo usan se recalculan).
    for _ in range(len(esperados) + 1):
        valores = tabla.valores()
        malos = [n for n, (_, v) in esperados.items() if not math.isclose(valores[n], v, rel_tol=1e-6, abs_tol=1e-9)]
        if not malos:
            break
        n = malos[0]
        expr = tabla.obtener(n).expresion
        tabla.modificar(n, _como_numero(esperados[n][0], esperados[n][1]))
        avisos.append(f"Parámetro «{n}»: «{expr}» no da lo mismo que en Fusion; quedó el valor.")
    return tabla, avisos


def comparar_con_fusion(doc, cuerpos_fusion):
    """Avisos si el volumen total importado no coincide con el que midió Fusion (control de la conversión)."""
    medidos = [c.get("volumen_mm3") for c in cuerpos_fusion if c.get("visible", True) and c.get("volumen_mm3") is not None]
    if not medidos or any(not isinstance(v, (int, float)) for v in medidos):
        return []
    fusion = sum(medidos)
    propio = sum(geo.volumen(c.forma) for c in doc.estado_final.cuerpos.values() if c.tipo == "solido")
    if fusion <= 0 or math.isclose(propio, fusion, rel_tol=_TOLERANCIA_VOLUMEN):
        return []
    return [f"El volumen importado ({propio:.3f} mm³) no coincide con el de Fusion ({fusion:.3f} mm³): revisá que "
            "estén todos los cuerpos (Fusion solo exporta los visibles)."]
