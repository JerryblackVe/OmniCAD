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
import re
import tempfile
import zipfile
from pathlib import Path

from .. import NOMBRE_APP, VERSION, carpeta_datos
from ..nucleo import geometria as geo
from ..nucleo import intercambio
from ..nucleo import motor
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
# Tope de cada miembro del ZIP al abrir un proyecto (512 MB): un .omnicad es un archivo de OTRO (o
# directamente hostil) y un miembro declarado gigante no puede quedarse con toda la memoria (zip bomb).
TOPE_MIEMBRO_ZIP = 512 * 1024 * 1024
# Tope de la miniatura (16 MB): una captura PNG del visor pesa mucho menos que eso, así que un proyecto
# hostil no necesita el tope general para fallar. `leer_miniatura` la lee sin abrir el proyecto (panel de
# datos recientes), y sin tope llenaría la memoria igual que cualquier otro miembro.
TOPE_MINIATURA = 16 * 1024 * 1024

log = logging.getLogger(__name__)


class ErrorProyecto(RuntimeError):
    pass


def _leer_miembro(z, nombre, tope=None):
    """Lee un miembro del ZIP con tope de tamaño (`TOPE_MIEMBRO_ZIP`, u otro más chico pasado por `tope`):
    un proyecto hostil (zip bomb) falla con un error claro en vez de quedarse con la memoria."""
    if tope is None:
        tope = TOPE_MIEMBRO_ZIP
    if z.getinfo(nombre).file_size > tope:
        raise ErrorProyecto(f"El miembro «{nombre}» del proyecto pesa {z.getinfo(nombre).file_size} bytes "
                            f"descomprimidos, más que el tope de {tope}: parece dañado o hostil.")
    return z.read(nombre)


def _ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _huella(receta):
    """Huella de la caché: la receta tal cual está en el ZIP (bytes) y la versión de la app que la calculó."""
    return hashlib.sha256(receta + VERSION.encode("utf-8")).hexdigest()


def _escribir_cache(z, doc, receta):
    """cache/cuerpos.brep (cuerpos finales + formas de los pasos lentos, en un solo compuesto: comparten caras y
    no ocupan dos veces) y cache/pasos.json. Las mallas no son B-rep: viajan solo en la receta."""
    if doc.motor == "omnikernel":
        _escribir_cache_omnikernel(z, doc, receta)
        return
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
        z.writestr("cache/pasos.json", json.dumps({"version": VERSION_CACHE, "motor": "opencascade", "huella": _huella(receta),
                                                   "finales": finales, "pasos": pasos}, ensure_ascii=False))


def _leer_cache(z, receta):
    """{índice de paso: (datos, formas)} para `Documento.desde_dict`, o None si no hay caché de pasos, es de otra
    receta o versión (huella distinta) o está dañada: entonces se recalcula todo, como en los proyectos viejos."""
    if motor.motor_activo() == "omnikernel":
        return _leer_cache_omnikernel(z, receta)
    if "cache/pasos.json" not in z.namelist():
        return None
    try:
        meta = json.loads(_leer_miembro(z, "cache/pasos.json"))
        if (meta.get("motor", "opencascade") != "opencascade" or meta.get("version") != VERSION_CACHE
                or meta.get("huella") != _huella(receta)):
            log.info("La caché del proyecto no corresponde a esta receta o versión: se recalcula todo.")
            return None
        fd, brep = tempfile.mkstemp(suffix=".brep")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(_leer_miembro(z, "cache/cuerpos.brep"))
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
            geo.ErrorGeometria, RecursionError) as e:
        log.warning("La caché del proyecto está dañada (%s): se recalcula todo.", e)
        return None


def _escribir_cache_omnikernel(z, doc, receta):
    formas, indice, pasos = [], {}, []
    for datos, propias in doc.pasos_para_cache():
        for f in propias:
            if id(f) not in indice:
                indice[id(f)] = len(formas)
                formas.append(f)
        pasos.append(dict(datos, formas=[indice[id(f)] for f in propias]))
    for i, forma in enumerate(formas):
        z.writestr(f"cache/omnikernel/{i}.v1", forma.exportar("v1"))
    if pasos:
        z.writestr("cache/omnikernel/pasos.json", json.dumps(
            {"version": VERSION_CACHE, "motor": "omnikernel", "huella": _huella(receta), "pasos": pasos},
            ensure_ascii=False))


def _leer_cache_omnikernel(z, receta):
    nombre = "cache/omnikernel/pasos.json"
    if nombre not in z.namelist():
        return None
    import omnikernel
    try:
        meta = json.loads(_leer_miembro(z, nombre))
        if (meta.get("motor") != "omnikernel" or meta.get("version") != VERSION_CACHE
                or meta.get("huella") != _huella(receta)):
            return None
        formas, cache = {}, {}
        for datos in meta["pasos"]:
            propias = []
            for i in datos["formas"]:
                if not isinstance(i, int) or i < 0:
                    raise ValueError("Índice de forma inválido en la caché OmniKernel.")
                if i not in formas:
                    formas[i] = omnikernel.importar(_leer_miembro(z, f"cache/omnikernel/{i}.v1"))
                propias.append(formas[i])
            cache[int(datos["indice"])] = (datos, propias)
        return cache
    except (KeyError, IndexError, AttributeError, TypeError, ValueError, OSError, RecursionError,
            zipfile.BadZipFile, omnikernel.ErrorOmniKernel) as e:
        log.warning("La caché OmniKernel está dañada (%s): se recalcula todo.", e)
        return None


from ..registro_uso.ganchos import archivo as _registrar_archivo


@_registrar_archivo("archivo_guardar")
def guardar(doc, ruta, miniatura_png=None, incluir_cache=True):
    return _escribir(*_preparar(doc, ruta), miniatura_png, doc if incluir_cache else None)


def _preparar(doc, ruta):
    """(ruta con extensión, manifiesto, receta en bytes): lo que hay que leer del documento para guardarlo."""
    ruta = Path(ruta)
    if ruta.suffix.lower() not in EXTENSIONES:
        ruta = ruta.with_suffix(EXTENSION)
    manifiesto = {"formato": FORMATO, "version_formato": VERSION_FORMATO, "aplicacion": NOMBRE_APP,
                  "version_aplicacion": VERSION, "guardado": _ahora(), "nombre": doc.nombre,
                  "unidades": {"longitud": "mm", "angulo": "deg"}}
    return ruta, manifiesto, json.dumps(doc.a_dict(), indent=1, ensure_ascii=False).encode("utf-8")


def _escribir(ruta, manifiesto, receta, miniatura_png=None, doc_cache=None):
    """Escribe el ZIP (por un temporal, así un corte no deja el archivo a medias). Sin `doc_cache` no lee nada del
    documento: el autoguardado lo corre en un hilo."""
    fd, temporal = tempfile.mkstemp(suffix=EXTENSION, dir=str(ruta.parent))
    os.close(fd)
    try:
        with zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifiesto.json", json.dumps(manifiesto, indent=2, ensure_ascii=False))
            z.writestr("receta.json", receta)
            if doc_cache is not None:
                _escribir_cache(z, doc_cache, receta)
            if miniatura_png:
                z.writestr("miniatura.png", miniatura_png)
        os.replace(temporal, ruta)
    except BaseException:
        if os.path.exists(temporal):
            os.remove(temporal)
        raise
    return ruta


def _json(texto):
    """json.loads de un miembro del proyecto: el JSON roto o anidado a más no poder (RecursionError) es un proyecto
    dañado, no un error interno (T-08 de la prueba de tortura)."""
    try:
        return json.loads(texto)
    except RecursionError:
        raise ErrorProyecto("El archivo está dañado: su JSON está anidado a una profundidad imposible.") from None
    except ValueError as e:
        raise ErrorProyecto(f"El archivo está dañado: no se pudo leer su JSON ({e}).") from None


@_registrar_archivo("archivo_abrir")
def abrir(ruta, esperar=None):
    """`esperar(segundos)`: la ventana avisa y repinta mientras el hijo ensaya un proyecto grande (B-48)."""
    ruta = Path(ruta)
    calculo, cache = None, None
    try:
        with zipfile.ZipFile(ruta) as z:
            nombres = set(z.namelist())
            if "manifiesto.json" not in nombres or "receta.json" not in nombres:
                raise ErrorProyecto("El archivo no es un proyecto de OmniCAD (faltan manifiesto o receta).")
            manifiesto = _json(_leer_miembro(z, "manifiesto.json"))
            texto_receta = _leer_miembro(z, "receta.json")
            receta = _json(texto_receta)
            if not isinstance(manifiesto, dict) or manifiesto.get("formato") not in FORMATOS_LEGIBLES:
                raise ErrorProyecto("Formato desconocido.")
            if manifiesto.get("version_formato", 1) > VERSION_FORMATO:
                raise ErrorProyecto("El proyecto fue guardado con una versión más nueva de OmniCAD.")
            if not isinstance(receta, dict) or not isinstance(receta.get("operaciones", []), list):
                raise ErrorProyecto("La receta del proyecto está dañada: las operaciones deben ser una lista.")
            from ..nucleo import aislado
            if (not aislado.EN_HIJO and motor.motor_activo() == "opencascade"
                    and len(receta.get("operaciones", [])) >= aislado.UMBRAL_PREVUELO_PARAMETROS):
                try:
                    from ..timeline.calculo_aislado import _leer_calculo
                    salida = aislado.correr_json("prevuelo_abrir", {"ruta": str(ruta.resolve())}, aislado.TOPE_PREVUELO_ABRIR,
                                        esperar)
                    calculo = _leer_calculo(salida)
                except (aislado.TareaAislada, ValueError, geo.ErrorGeometria) as e:
                    raise ErrorProyecto(f"El proyecto es grande y el ensayo de apertura falló: {e}. No se abrió y OmniCAD "
                                        "sigue andando; guardá una copia y probá de nuevo.") from e
            else:
                cache = _leer_cache(z, texto_receta)
    except zipfile.BadZipFile:
        raise ErrorProyecto("El archivo está dañado o no es un ZIP.") from None
    try:
        doc = Documento.desde_dict(receta, cache, _calculo=calculo)
    except ErrorOperacion as e:
        if "Tipo de operación desconocido" in str(e):
            raise ErrorProyecto(f"El proyecto tiene una operación que esta OmniCAD ({VERSION}) no conoce "
                                f"({e}): fue guardado con una versión más nueva aunque comparta el mismo "
                                "número de versión.") from None
        raise ErrorProyecto(f"La receta del proyecto está dañada o es incompatible: {e}") from None
    except (ErrorDocumento, ErrorExpresion, KeyError, TypeError, ValueError) as e:
        raise ErrorProyecto(f"La receta del proyecto está dañada o es incompatible: {e}") from None
    doc.nombre = manifiesto.get("nombre") or ruta.stem
    doc.ruta = str(ruta)
    return doc


def leer_miniatura(ruta):
    with zipfile.ZipFile(ruta) as z:
        return _leer_miembro(z, "miniatura.png", TOPE_MINIATURA) if "miniatura.png" in z.namelist() else None


# ---------------------------------------------------------------- autoguardado
def carpeta_autoguardado():
    carpeta = carpeta_datos() / "autoguardado"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def ruta_autoguardado(doc):
    """Junto al proyecto si ya tiene ruta; si no, en la carpeta de la aplicación. Cada «Sin título» lleva el
    token de su documento (B-22): dos documentos abiertos no se pisan el autoguardado entre sí."""
    if doc.ruta:
        r = Path(doc.ruta)
        return r.with_name(r.stem + ".autoguardado" + EXTENSION)
    return carpeta_autoguardado() / f"sin_titulo_{getattr(doc, 'token', '0')}.autoguardado{EXTENSION}"


def autoguardar(doc, miniatura_png=None):
    """Guarda una copia de seguridad SIN marcar el documento como guardado."""
    esperar_autoguardado()
    destino = ruta_autoguardado(doc)
    guardar(doc, destino, miniatura_png, incluir_cache=False)
    return destino


_HILOS = []        # autoguardados que se están escribiendo (`autoguardar_en_hilo`)


def esperar_autoguardado():
    """Espera a que terminen los autoguardados en curso. Se llama antes de borrar o leer una copia: si no, el hilo la
    volvería a escribir después de un guardado a mano."""
    while _HILOS:
        _HILOS.pop().join()


def autoguardar_en_hilo(doc, al_terminar):
    """Como `autoguardar`, pero solo la receta se lee acá (rápido, y queda la foto de este momento); comprimir y
    escribir el ZIP va en un hilo, así la ventana no se traba con un proyecto grande. `al_terminar(destino, error)`
    se llama EN EL HILO (error es None o la excepción OSError/RuntimeError). Devuelve el hilo."""
    import threading
    esperar_autoguardado()
    ruta, manifiesto, receta = _preparar(doc, ruta_autoguardado(doc))

    def trabajar():
        try:
            al_terminar(_escribir(ruta, manifiesto, receta), None)
        except (OSError, RuntimeError) as e:
            al_terminar(ruta, e)

    hilo = threading.Thread(target=trabajar, name="autoguardado", daemon=True)
    hilo.start()
    _HILOS.append(hilo)
    return hilo


def autoguardados_pendientes():
    """Autoguardados de documentos «Sin título», del más nuevo al más viejo (B-22)."""
    esperar_autoguardado()
    return sorted(carpeta_autoguardado().glob("sin_titulo*.autoguardado" + EXTENSION),
                   key=lambda p: p.stat().st_mtime, reverse=True)


def autoguardado_pendiente(ruta_proyecto=None):
    """Si hay un autoguardado más nuevo que el proyecto (o huérfano), devuelve su ruta. Con varios huérfanos,
    el más nuevo (el resto los lista `autoguardados_pendientes`)."""
    esperar_autoguardado()
    if ruta_proyecto:
        p = Path(ruta_proyecto)
        a = p.with_name(p.stem + ".autoguardado" + EXTENSION)
        # ">=": la hora de archivo de Windows puede repetirse en guardados seguidos. Al guardar a mano
        # el autoguardado se borra, así que si sigue existiendo con la misma hora, hay trabajo sin guardar.
        if a.exists() and (not p.exists() or a.stat().st_mtime >= p.stat().st_mtime):
            return a
        return None
    pendientes = autoguardados_pendientes()
    return pendientes[0] if pendientes else None


def pendientes_de_recuperacion(recientes=()):
    """Lista del diálogo «Documentos recuperados» (pendiente 21, como Fusion 360), del más nuevo al más
    viejo: los autoguardados huérfanos (documentos «Sin título») y, de cada proyecto dado en
    ``recientes``, el autoguardado más nuevo que el proyecto. Cada fila trae el nombre a mostrar, la
    fecha de recuperación, la carpeta de la copia, la copia misma (``backup``) y el proyecto original
    (``project``, None para huérfanos). Pura: solo mira archivos."""
    filas = {}
    for copia in autoguardados_pendientes():
        filas.setdefault(copia, {"backup": str(copia), "name": "Sin título", "project": None})
    for ruta in recientes:
        try:
            copia = autoguardado_pendiente(ruta)
        except OSError:
            continue                     # un reciente borrado o inaccesible no puede frenar la lista
        if copia is not None:
            filas.setdefault(copia, {"backup": str(copia), "name": Path(ruta).stem, "project": str(ruta)})
    resultado = []
    for copia, fila in filas.items():
        try:
            mtime = copia.stat().st_mtime
        except OSError:
            continue
        resultado.append({**fila,
                          "date": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                          "folder": str(copia.parent)})
    return sorted(resultado, key=lambda fila: fila["date"], reverse=True)


def borrar_autoguardado(doc):
    """Borra la copia de autoguardado del documento. Un archivo bloqueado no puede hacer fallar un guardado que
    ya salió bien: se avisa en el registro y se sigue."""
    esperar_autoguardado()
    destino = ruta_autoguardado(doc)
    try:
        destino.unlink(missing_ok=True)
    except OSError as e:
        log.warning("No se pudo borrar el autoguardado %s: %s", destino, e)


def es_copia_de_autoguardado(ruta):
    """True si el archivo es una copia de autoguardado (`*.autoguardado.omnicad`), nunca un proyecto."""
    return Path(ruta).name.lower().endswith(".autoguardado" + EXTENSION)


def suprimir_copia(ruta):
    """«Suprimir» de Documentos recuperados: borra SOLO una copia de autoguardado. Un proyecto guardado (o
    cualquier otro archivo) que llegue por error se rechaza, no se borra."""
    if not es_copia_de_autoguardado(ruta):
        raise ErrorProyecto(f"«{Path(ruta).name}» no es una copia de autoguardado (*.autoguardado{EXTENSION}): "
                            "no se borra.")
    Path(ruta).unlink(missing_ok=True)


def abrir_recuperado(copia, proyecto_original=None):
    """Documento de una copia de autoguardado, como lo deja «Abrir» de Documentos recuperados: con
    `proyecto_original` guardar a mano pisa ESE proyecto; sin él es un «Recuperado» sin ruta que hereda el
    token de la copia (sin_titulo_<token>), así su autoguardado vuelve a ser la misma copia y al guardar se borra:
    si no, la copia vieja seguía apareciendo en cada arranque."""
    doc = abrir(copia)
    doc.ruta = str(proyecto_original) if proyecto_original else None
    doc.nombre = Path(proyecto_original).stem if proyecto_original else "Recuperado"
    if not proyecto_original:
        m = re.fullmatch(r"sin_titulo_(\w+)\.autoguardado" + re.escape(EXTENSION), Path(copia).name, re.IGNORECASE)
        if m:
            doc.token = m.group(1)
    doc.modificado = True
    return doc
