# -*- coding: utf-8 -*-
"""
Formato de proyecto propio `.omnicad` + autoguardado.

Inspiración (informe_analisis.md §4): el `.f3d` de Fusion es un ZIP que guarda por separado
la receta/historial (segmentos de diseño), la geometría cacheada (B-rep `.smb`) y una miniatura.
`.omnicad` sigue la MISMA idea con contenido propio y abierto (no copia el formato de Autodesk):

    proyecto.omnicad (ZIP, deflate)
    ├── manifiesto.json      formato, versión, app, fechas
    ├── receta.json          parámetros + timeline (la fuente de verdad)
    ├── cache/cuerpos.brep   compuesto B-rep (opcional): primero los sólidos y superficies al final del timeline
    │                        (sin las mallas; sirve a otras herramientas), después las formas de los pasos lentos
    ├── cache/pasos.json     resultado de los pasos lentos (opcional): huella de la receta, cuántas formas del
    │                        BREP son las finales y, por paso, qué cuerpos dejó y en qué forma del BREP están
    └── miniatura.png        captura del visor (opcional)

Al abrir, los pasos lentos se toman de la caché en vez de recalcularlos (un agujero roscado modelado tarda
segundos); el resto se calcula desde `receta.json`. La caché vale solo si la huella coincide (la misma receta,
byte a byte, y la misma versión de la app): si no, o si está dañada, se recalcula todo. Editar un paso recalcula
como siempre. La escritura es atómica (archivo temporal + reemplazo).
"""
import datetime
import hashlib
import json
import logging
import os
import tempfile
import zipfile
from pathlib import Path

from .. import NOMBRE_APP, VERSION, carpeta_datos
from ..nucleo import geometria as geo
from ..nucleo import intercambio
from ..timeline.documento import Documento, ErrorDocumento
from ..timeline.operaciones import ErrorOperacion
from ..timeline.parametros import ErrorExpresion

EXTENSION = ".omnicad"
FORMATO = "OmniCAD-proyecto"
# Proyectos guardados cuando el programa se llamaba FusionClone (antes del 2026-10-09): se abren y se guardan igual.
EXTENSIONES = (EXTENSION, ".fclone")
FORMATOS_LEGIBLES = (FORMATO, "FusionClone-proyecto")
VERSION_FORMATO = 1
VERSION_CACHE = 1

log = logging.getLogger(__name__)


class ErrorProyecto(RuntimeError):
    pass


def _ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _huella(receta):
    """Huella de la caché: la receta tal cual está en el ZIP (bytes) y la versión de la app que la calculó."""
    return hashlib.sha256(receta + VERSION.encode("utf-8")).hexdigest()


def _escribir_cache(z, doc, receta):
    """cache/cuerpos.brep (cuerpos finales + formas de los pasos lentos, en un solo compuesto: comparten caras y
    no ocupan dos veces) y cache/pasos.json. Las mallas no son B-rep: viajan solo en la receta."""
    formas = [c.forma for c in doc.estado_final.cuerpos.values() if getattr(c, "tipo", "solido") != "malla"]
    finales = len(formas)
    indice = {id(f): k for k, f in enumerate(formas)}
    pasos = []
    for datos, propias in doc.pasos_para_cache():
        for f in propias:
            if id(f) not in indice:
                indice[id(f)] = len(formas)
                formas.append(f)
        pasos.append(dict(datos, formas=[indice[id(f)] for f in propias]))
    if not formas:
        return
    fd, brep = tempfile.mkstemp(suffix=".brep")
    os.close(fd)
    try:
        intercambio.escribir_brep(geo.compuesto(formas), brep)
        z.write(brep, "cache/cuerpos.brep")
    finally:
        os.remove(brep)
    if pasos:
        z.writestr("cache/pasos.json", json.dumps({"version": VERSION_CACHE, "huella": _huella(receta),
                                                   "finales": finales, "pasos": pasos}, ensure_ascii=False))


def _leer_cache(z, receta):
    """{índice de paso: (datos, formas)} para `Documento.desde_dict`, o None si no hay caché de pasos, es de otra
    receta o versión (huella distinta) o está dañada: entonces se recalcula todo, como en los proyectos viejos."""
    if "cache/pasos.json" not in z.namelist():
        return None
    try:
        meta = json.loads(z.read("cache/pasos.json"))
        if meta.get("version") != VERSION_CACHE or meta.get("huella") != _huella(receta):
            log.info("La caché del proyecto no corresponde a esta receta o versión: se recalcula todo.")
            return None
        fd, brep = tempfile.mkstemp(suffix=".brep")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(z.read("cache/cuerpos.brep"))
            partes = intercambio.partes_de_brep(brep)
        finally:
            os.remove(brep)
        cache = {}
        for datos in meta["pasos"]:
            ks = datos["formas"]
            if not all(isinstance(k, int) and 0 <= k < len(partes) for k in ks):
                raise ValueError(f"forma fuera del BREP en el paso {datos.get('op')}")
            cache[int(datos["indice"])] = (datos, [partes[k] for k in ks])
        return cache
    except (KeyError, IndexError, TypeError, ValueError, AttributeError, OSError, zipfile.BadZipFile,
            geo.ErrorGeometria) as e:
        log.warning("La caché del proyecto está dañada (%s): se recalcula todo.", e)
        return None


def guardar(doc, ruta, miniatura_png=None, incluir_cache=True):
    ruta = Path(ruta)
    if ruta.suffix.lower() not in EXTENSIONES:
        ruta = ruta.with_suffix(EXTENSION)
    manifiesto = {"formato": FORMATO, "version_formato": VERSION_FORMATO, "aplicacion": NOMBRE_APP,
                  "version_aplicacion": VERSION, "guardado": _ahora(), "nombre": doc.nombre,
                  "unidades": {"longitud": "mm", "angulo": "deg"}}
    fd, temporal = tempfile.mkstemp(suffix=EXTENSION, dir=str(ruta.parent))
    os.close(fd)
    try:
        with zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifiesto.json", json.dumps(manifiesto, indent=2, ensure_ascii=False))
            receta = json.dumps(doc.a_dict(), indent=1, ensure_ascii=False).encode("utf-8")
            z.writestr("receta.json", receta)
            if incluir_cache:
                _escribir_cache(z, doc, receta)
            if miniatura_png:
                z.writestr("miniatura.png", miniatura_png)
        os.replace(temporal, ruta)
    except BaseException:
        if os.path.exists(temporal):
            os.remove(temporal)
        raise
    return ruta


def leer_manifiesto(ruta):
    with zipfile.ZipFile(ruta) as z:
        return json.loads(z.read("manifiesto.json"))


def abrir(ruta):
    ruta = Path(ruta)
    try:
        with zipfile.ZipFile(ruta) as z:
            nombres = set(z.namelist())
            if "manifiesto.json" not in nombres or "receta.json" not in nombres:
                raise ErrorProyecto("El archivo no es un proyecto de OmniCAD (faltan manifiesto o receta).")
            manifiesto = json.loads(z.read("manifiesto.json"))
            texto_receta = z.read("receta.json")
            receta = json.loads(texto_receta)
            cache = _leer_cache(z, texto_receta)
    except zipfile.BadZipFile:
        raise ErrorProyecto("El archivo está dañado o no es un ZIP.") from None
    if manifiesto.get("formato") not in FORMATOS_LEGIBLES:
        raise ErrorProyecto("Formato desconocido.")
    if manifiesto.get("version_formato", 1) > VERSION_FORMATO:
        raise ErrorProyecto("El proyecto fue guardado con una versión más nueva de OmniCAD.")
    try:
        doc = Documento.desde_dict(receta, cache)
    except (ErrorOperacion, ErrorDocumento, ErrorExpresion, KeyError, TypeError, ValueError) as e:
        raise ErrorProyecto(f"La receta del proyecto está dañada o es incompatible: {e}") from None
    doc.nombre = manifiesto.get("nombre") or ruta.stem
    doc.ruta = str(ruta)
    return doc


def leer_miniatura(ruta):
    with zipfile.ZipFile(ruta) as z:
        return z.read("miniatura.png") if "miniatura.png" in z.namelist() else None


# ---------------------------------------------------------------- autoguardado
def carpeta_autoguardado():
    carpeta = carpeta_datos() / "autoguardado"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def ruta_autoguardado(doc):
    """Junto al proyecto si ya tiene ruta; si no, en la carpeta de la aplicación."""
    if doc.ruta:
        r = Path(doc.ruta)
        return r.with_name(r.stem + ".autoguardado" + EXTENSION)
    return carpeta_autoguardado() / ("sin_titulo.autoguardado" + EXTENSION)


def autoguardar(doc, miniatura_png=None):
    """Guarda una copia de seguridad SIN marcar el documento como guardado."""
    destino = ruta_autoguardado(doc)
    guardar(doc, destino, miniatura_png, incluir_cache=False)
    return destino


def autoguardado_pendiente(ruta_proyecto=None):
    """Si hay un autoguardado más nuevo que el proyecto (o huérfano), devuelve su ruta."""
    if ruta_proyecto:
        p = Path(ruta_proyecto)
        a = p.with_name(p.stem + ".autoguardado" + EXTENSION)
        # ">=": la hora de archivo de Windows puede repetirse en guardados seguidos. Al guardar a mano
        # el autoguardado se borra, así que si sigue existiendo con la misma hora, hay trabajo sin guardar.
        if a.exists() and (not p.exists() or a.stat().st_mtime >= p.stat().st_mtime):
            return a
        return None
    a = carpeta_autoguardado() / ("sin_titulo.autoguardado" + EXTENSION)
    return a if a.exists() else None


def borrar_autoguardado(doc):
    destino = ruta_autoguardado(doc)
    if destino.exists():
        destino.unlink()
