# -*- coding: utf-8 -*-
"""
Abre archivos de Fusion 360 (.f3d y .f3z) SIN Fusion: lee el B-rep que el archivo trae adentro.

Un .f3d es un ZIP. Cada componente guarda su geometría actual en `FusionAssetName[Active]/Breps.BlobParts/
BREP.*.smbh`: un bloque SAB de ShapeManager (el núcleo de Autodesk, derivado de ACIS), comprimido con Zstandard
(método 93 del ZIP). Este módulo saca esos bloques (`zstd_puro`), los lee (`sab`) y los pasa a OpenCascade
(`acis_occ`). Los `.smb` (sin «h») son los perfiles de los bocetos y geometría auxiliar: de ahí salen los bocetos (`f3d_bocetos`).

Filtros (medidos en archivos reales de Fusion, ver PROJECT_LOG): los cuerpos sin la marca de tiempo de Fusion son
auxiliares y quedan afuera (`acis_occ.convertir`); si un componente está guardado dos veces (versión vieja y
actual) entra la versión más nueva; un cuerpo idéntico a otro no se repite (`_sin_repetidos`); y los cuerpos viejos
del historial que Fusion deja en el bloque de un componente, que la escena del archivo no muestra, tampoco entran
(`f3d_escena.asignar`).

Posición de los componentes (P11.a): el B-rep de cada componente está en SUS coordenadas; dónde va en el ensamblaje
lo dicen las matrices de la escena de dibujo que el archivo guarda aparte (`f3d_escena`). Cada cuerpo se ubica con la
matriz de su componente, y un componente repetido entra una vez por copia, como instancias que comparten la geometría
(`solidos_crear.instanciar`). Lo que no se puede ubicar queda donde está guardado, con un aviso.

Nombres (P11.a d): el flujo de diseño (`FusionDesignSegmentType1/BulkStream.dat`, propietario) escribe el nombre
del componente en el registro que precede al texto «BREP.<guid>.smbh» de su bloque; si lo que precede no es un nombre
(un material, un GUID, el de un boceto: así guarda Fusion los componentes que vienen de un STEP), no se inventa uno.
Qué NO trae: el historial, los parámetros y los nombres de los cuerpos. Un .f3z es un paquete con varios .f3d: se lee el diseño principal (el que nadie referencia).

Sin Qt.
"""
import io
import json
import re
import struct
import zipfile
from pathlib import Path

import numpy as np

from ..nucleo import consultas

from . import acis_occ, f3d_escena, f3d_historial, sab, zstd_puro

CARPETA_BREPS = "Breps.BlobParts/"
CARAS_MAX_VERIFICAR = 5000        # cuerpos más grandes no se verifican (BRepCheck tarda segundos en ellos)
# Tope de cada miembro del ZIP de un .f3d/.f3z (512 MB): un archivo hostil (zip bomb, con cualquier método de
# compresión) falla con un error claro en vez de quedarse con la memoria al leerse.
TOPE_MIEMBRO_F3D = 512 * 1024 * 1024


class ErrorF3D(ValueError):
    """El archivo no es un .f3d/.f3z que se pueda leer, o no trae geometría."""


def leer(ruta):
    """Cuerpos de un .f3d o .f3z, cada uno en su lugar del ensamblaje y con una copia por cada ocurrencia de su
    componente. Devuelve (partes, avisos): `partes` = lista de (forma OCC en mm, "solido" | "superficie"); `avisos` =
    textos para el usuario."""
    comps, avisos = leer_componentes(ruta)
    return expandir(comps), avisos


def leer_componentes(ruta, resumen=None, progreso=None, bocetos=None):
    """Como `leer`, pero sin repetir la geometría de las copias: devuelve (componentes, avisos) con una lista
    `{"forma": B-rep en las coordenadas del componente, "tipo", "bloque", "marcos": [matriz 4×4 de columnas en mm, una
    por copia]}`. Si se pasa un dict en `resumen`, se llena con lo que se vio en la escena (`nodos`, `copias`,
    `cuerpos_escena`, `cuerpos_con_malla`, `bloques`, `bloques_ubicados`). `progreso(texto)`, si se pasa, se llama al empezar
    cada etapa (para mostrarla en la ventana mientras abre). Si se pasa la lista `bocetos`, se le agregan los bocetos del
    archivo (`f3d_bocetos.leer_bocetos`) ya puestos en el diseño: {"marco": {"origen", "normal", "u"} en mm, "boceto":
    Boceto, "caras", "curvas"}."""
    ruta = Path(ruta)
    _etapa(progreso, f"Leyendo {ruta.name}…")
    try:
        datos = ruta.read_bytes()
    except OSError as e:
        raise ErrorF3D(f"No se pudo leer {ruta.name}: {e}") from None
    if ruta.suffix.lower() == ".f3z":
        datos = _f3d_principal(datos, ruta.name)
    return leer_componentes_bytes(datos, ruta.stem, resumen, progreso, bocetos)


def expandir(componentes):
    """[(forma, tipo)] con una entrada por copia: la forma del componente movida a cada matriz; las copias rígidas
    comparten la geometría (`solidos_crear.instanciar`)."""
    from ..nucleo import solidos_crear
    salida = []
    for c in componentes:
        for M in c["marcos"]:
            forma = c["forma"] if f3d_escena.es_identidad(M) else solidos_crear.instanciar(c["forma"], M)
            salida.append((forma, c["tipo"]))
    return salida


def _etapa(progreso, texto):
    if progreso is not None:
        progreso(texto)


def leer_componentes_bytes(datos, nombre="Fusion", resumen=None, progreso=None, bocetos=None):
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile:
        raise ErrorF3D(f"{nombre} no es un archivo de Fusion válido (no es un ZIP).") from None
    bloques = [i for i in z.infolist() if CARPETA_BREPS in i.filename and i.filename.lower().endswith(".smbh")]
    if not bloques:
        raise ErrorF3D(f"{nombre} no trae geometría 3D (el diseño está vacío o solo tiene bocetos).")
    leidos, archivos, avisos = [], [], []
    for k, info in enumerate(sorted(bloques, key=lambda i: i.filename), 1):
        _etapa(progreso, f"Descomprimiendo la geometría ({info.file_size / 1048576:.0f} MB)…")
        try:
            datos_sab = miembro(datos, info)
            _etapa(progreso, "Leyendo el B-rep de Fusion…")
            archivo = sab.leer(datos_sab)
        except (sab.ErrorSAB, zstd_puro.ErrorZstd) as e:
            avisos.append(f"Un componente de {nombre} no se pudo leer: {e}")
            continue
        del datos_sab
        _etapa(progreso, f"Armando sólidos y superficies ({len(archivo.de_tipo('face'))} caras)…")
        p, a = acis_occ.convertir(archivo, f"{nombre} (componente {k})" if len(bloques) > 1 else nombre)
        avisos += a
        if p:
            leidos.append([(forma, tipo, _firma(forma, tipo), marca) for forma, tipo, marca in p])
            archivos.append(info.filename.rsplit("/", 1)[-1])
    partes = _sin_repetidos(leidos)
    if not partes:
        raise ErrorF3D(f"{nombre} no tiene sólidos ni superficies que se puedan leer."
                       + (f" {avisos[0]}" if avisos else ""))
    _etapa(progreso, "Ubicando los componentes…")
    marcos, fuera, ocultos = _ubicar(datos, partes, avisos, resumen)
    if fuera:
        avisos.append(f"{len(fuera)} cuerpos guardados en el archivo no están en el diseño actual (versiones viejas "
                      "del historial de Fusion que la escena del archivo no muestra): no se importan.")
        ocultos = {k - sum(1 for f in fuera if f < k) for k in ocultos}          # sus índices tras quitar los de `fuera`
        partes = [p for k, p in enumerate(partes) if k not in fuera]
        marcos = [m for k, m in enumerate(marcos) if k not in fuera]
    malos = sum(1 for forma, tipo, firma, _ in partes if firma[1] <= CARAS_MAX_VERIFICAR
                and not (tipo == "superficie" and firma[1] > acis_occ.CARAS_SIN_ARREGLO)   # mallas sin reparar: a propósito
                and not acis_occ.es_valida(forma))
    if malos:
        avisos.append(f"{malos} de {len(partes)} cuerpos quedaron con errores de geometría (caras que tocan un polo "
                      "o un vértice de cono): se ven y se miden, pero una operación booleana con ellos puede fallar.")
    if resumen is not None:
        resumen.update(descartados=len(fuera), sin_ubicar=sum(1 for m in marcos if m is None) if any(marcos) else 0)
    if bocetos is not None:
        _etapa(progreso, "Leyendo los bocetos…")
        smb = [i for i in z.infolist() if CARPETA_BREPS in i.filename and i.filename.lower().endswith(".smb")]
        bocetos += _bocetos_ubicados(datos, smb, partes, marcos, nombre, avisos)
    uno = [np.eye(4)]
    flujo, nuevo = _flujo_de_diseno(datos)
    nombres = _nombres_de_componentes(flujo if nuevo else None, archivos)       # los nombres: solo del formato nuevo
    if resumen is not None:
        resumen["historial"] = f3d_historial.operaciones(flujo) if flujo else []
    return [{"forma": forma, "tipo": tipo, "bloque": bloque, "marcos": m or uno, "nombre": nombres.get(archivos[bloque]),
             "oculto": k in ocultos}
            for k, ((forma, tipo, _, bloque), m) in enumerate(zip(partes, marcos, strict=True))], avisos


def _bocetos_ubicados(datos, bloques_smb, partes, marcos, nombre, avisos):
    """Bocetos de los bloques `.smb` puestos en el diseño. Están en las coordenadas de su componente y el archivo no dice
    (fuera del flujo propietario) de cuál es cada bloque: con un solo componente son de ese y se mueven con su matriz; con
    varios no se importan —ni por la caja de los cuerpos, que se pisa entre componentes (medido: 415 de 418 perfiles de
    CARTERA GOTICA caen en más de un componente)— y se declara en un aviso."""
    from . import f3d_bocetos
    todos = []
    for info in sorted(bloques_smb, key=lambda i: i.filename):
        try:
            crudo = miembro(datos, info)
        except (ErrorF3D, zstd_puro.ErrorZstd) as e:
            avisos.append(f"Un bloque de bocetos de {nombre} no se pudo leer: {e}")
            continue
        try:
            b, a = f3d_bocetos.leer_bocetos(crudo, nombre)
        except Exception as e:                    # noqa: BLE001 - los bocetos son una mejora: un bloque raro no tumba la apertura
            avisos.append(f"Los bocetos de {nombre} no se pudieron leer: {e}")
            continue
        todos += b
        avisos += a
    todos = f3d_bocetos.sin_repetidos(todos)
    componentes = {bloque for _, _, _, bloque in partes}
    if len(componentes) != 1:
        if todos:
            avisos.append(f"{len(todos)} bocetos de {nombre} no se importaron: el archivo tiene {len(componentes)} "
                          "componentes y no dice a cuál pertenece cada boceto.")
        return []
    M = next((m[0] for m in marcos if m), np.eye(4))
    R, o = M[:3, :3], M[:3, 3]
    salida = f3d_bocetos.limitar(todos, avisos, nombre)
    for b in salida:
        m = {k: np.asarray(v, float) for k, v in b["marco"].items()}
        b["marco"] = {"origen": [float(x) for x in R @ m["origen"] + o], "normal": [float(x) for x in R @ m["normal"]],
                      "u": [float(x) for x in R @ m["u"]]}
    return salida


_TEXTO = re.compile(rb"(?:[\x20-\x7e\xa0-\xff]\x00){1,200}")     # caracteres UTF-16; el largo va en los 4 bytes previos
_NO_ES_NOMBRE = re.compile(r"[0-9A-Fa-f-]{36}.*|BREP\..*|Prism.*|\d+_\d+|\d+")
_VENTANA_NOMBRE = 2000      # bytes entre el nombre y el texto del bloque (reales: 288 a 1324)


def _flujo_de_diseno(datos):
    """(bytes del flujo de diseño propietario, si es del formato nuevo): `FusionDesignSegmentType1/BulkStream.dat`; los
    archivos viejos lo llaman `Design1/`. (None, False) si no está o no se puede leer."""
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            info = {i.filename.rsplit("/", 2)[-2]: i for i in z.infolist() if i.filename.endswith("/BulkStream.dat")}
        for carpeta in ("FusionDesignSegmentType1", "Design1"):
            if carpeta in info:
                return miembro(datos, info[carpeta]), carpeta != "Design1"
    except (ErrorF3D, zstd_puro.ErrorZstd, zipfile.BadZipFile):
        pass
    return None, False


def _nombres_de_componentes(flujo, archivos):
    """{archivo BREP.*.smbh: nombre de su componente} según el flujo de diseño. Lo que no se encuentra no está."""
    if flujo is None:
        return {}
    nombres = {}
    for archivo in archivos:
        q = flujo.find(archivo.encode("utf-16-le"))
        if q < 4:
            continue
        previo = None
        for m in _TEXTO.finditer(flujo, max(4, q - 4 - _VENTANA_NOMBRE), q - 4):
            if struct.unpack_from("<I", flujo, m.start() - 4)[0] == len(m.group()) // 2:
                previo = m.group().decode("utf-16-le")
        if previo and not _NO_ES_NOMBRE.fullmatch(previo.strip()) and previo.strip():
            nombres[archivo] = previo.strip()
    return nombres


def _ubicar(datos, partes, avisos, resumen=None):
    """(matrices, fuera, ocultos) según la escena del archivo (`f3d_escena`): `matrices` = una lista de 4×4 por parte o
    None si no se la pudo ubicar (queda donde está guardado su B-rep); sin escena, o si ningún componente se mueve, todo
    None. `fuera` = índices de las partes que no están en el diseño actual (cuerpos viejos del historial); `ocultos` =
    índices de las que el diseño tiene con el ojo cerrado (sin malla en la escena)."""
    ninguna = ([None] * len(partes), set(), set())
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            info = {i.filename: i for i in z.infolist()}
        mundo = next((i for n, i in info.items() if n.endswith("OGS/DefaultScene/world")), None)
        malla = next((i for n, i in info.items() if n.endswith("OGS/DefaultScene/Fusion_mesh_000")), None)
        if mundo is None or malla is None:
            return ninguna
        escena = f3d_escena.Escena(miembro(datos, mundo), miembro(datos, malla))
        if not escena.nodos:
            return ninguna
        from ..nucleo import geometria as geo
        solidos = []
        for forma, tipo, firma, bloque in partes:
            lo, hi = (np.array(firma[2:5]), np.array(firma[5:8])) if len(firma) >= 8 else (np.full(3, 1e9),) * 2
            solidos.append({"bloque": bloque, "tipo": tipo, "caras": firma[1], "lo": lo, "hi": hi,
                            "caja": _una_vez(lambda f=forma: tuple(np.array(p) for p in geo.caja_envolvente(f))),
                            "vol": _una_vez(lambda f=forma: geo.volumen(f)),
                            "centro": _una_vez(lambda f=forma: geo.centro_masa(f))})
        matrices, visto = f3d_escena.asignar(escena, solidos)
        fuera = set(visto.pop("descartados"))
        ocultos = set(visto.pop("ocultos"))
        if resumen is not None:
            resumen.update(visto, nodos=len(escena.nodos), copias=sum(1 for n in escena.nodos if n["es_ref"]),
                           cuerpos_escena=len(escena.cuerpos),
                           cuerpos_con_malla=sum(1 for c in escena.cuerpos if c["vol_mm3"] is not None))
    except Exception as e:                    # noqa: BLE001 - ubicar es una mejora: si algo falla, el archivo abre igual
        avisos.append(f"No se pudo leer la posición de los componentes ({e}): cada cuerpo queda donde está guardado "
                      "su B-rep.")
        return ninguna
    if not any(m and (len(m) > 1 or not f3d_escena.es_identidad(m[0])) for m in matrices):
        return [None] * len(partes), fuera, ocultos
    sin = sum(1 for k, m in enumerate(matrices) if m is None and k not in fuera)
    if sin:
        avisos.append(f"{sin} de {len(partes) - len(fuera)} cuerpos no se pudieron ubicar en el ensamblaje: quedan "
                      "donde está guardado su B-rep.")
    return matrices, fuera, ocultos


def _una_vez(funcion):
    """Función sin argumentos que calcula una sola vez y recuerda el resultado."""
    guardado = []

    def f():
        if not guardado:
            guardado.append(funcion())
        return guardado[0]
    return f


def _firma(forma, tipo):
    """Huella barata de un cuerpo: tipo, cantidad de caras y caja envolvente redondeada a 0,01 mm."""
    return consultas.firma_importacion(forma, tipo)


def _sin_repetidos(leidos):
    """Junta los cuerpos de todos los bloques sin repetir: lista de (forma, tipo, firma, bloque). Fusion puede guardar el mismo componente en dos bloques
    (una versión vieja y la actual): si la mitad o más de los cuerpos de un bloque están, idénticos, en otro bloque
    más nuevo (marca de tiempo mayor), el viejo se descarta entero. Después, un cuerpo idéntico a otro ya tomado
    (mismas caras y misma caja) no se repite."""
    def mas_nueva(bloque):
        return max((m for *_, m in bloque if m is not None), default=0.0)

    firmas = [{f for _, _, f, _ in b} for b in leidos]
    vivos = []
    for i, b in enumerate(leidos):
        viejo = any(j != i and mas_nueva(leidos[j]) > mas_nueva(b) and len(firmas[i] & firmas[j]) * 2 >= len(firmas[i])
                    for j in range(len(leidos)))
        if not viejo:
            vivos.append((i, b))
    partes, vistas = [], set()
    for i, b in vivos:
        for forma, tipo, firma, _ in b:
            if firma not in vistas:
                vistas.add(firma)
                partes.append((forma, tipo, firma, i))
    return partes


def miembro(datos, info):
    """Bytes descomprimidos de un miembro del ZIP. El método 93 (Zstandard) lo descomprime `zstd_puro`."""
    if info.file_size > TOPE_MIEMBRO_F3D:
        raise ErrorF3D(f"El miembro «{info.filename}» del archivo pesa {info.file_size} bytes descomprimidos, "
                       f"más que el tope de {TOPE_MIEMBRO_F3D}: parece dañado o hostil (zip bomb).")
    if info.compress_type != zstd_puro.METODO_ZIP_ZSTD:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            return z.read(info)
    h = info.header_offset
    if datos[h:h + 4] != b"PK\x03\x04":
        raise ErrorF3D("ZIP dañado (cabecera local inválida).")
    largo_nombre, largo_extra = struct.unpack_from("<HH", datos, h + 26)
    inicio = h + 30 + largo_nombre + largo_extra
    salida = zstd_puro.descomprimir(datos[inicio:inicio + info.compress_size], tope=info.file_size)
    if len(salida) != info.file_size:
        raise ErrorF3D(f"{info.filename}: el tamaño descomprimido no coincide.")
    return salida


def _f3d_principal(datos, nombre):
    """Un .f3z trae los diseños (.f3d) y un `DesignDescription.json` con quién referencia a quién: el principal es
    el .f3d que ningún otro referencia (el ensamblaje de arriba); si hay varios, el más grande."""
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile:
        raise ErrorF3D(f"{nombre} no es un paquete .f3z válido.") from None
    nombres = [i for i in z.infolist() if i.filename.lower().endswith(".f3d") and "/" not in i.filename.strip("/")]
    if not nombres:
        raise ErrorF3D(f"{nombre} no trae ningún diseño .f3d.")
    try:
        descripcion = next(i for i in z.infolist() if i.filename == "DesignDescription.json")
        objetos = json.loads(miembro(datos, descripcion))["designDescription"]["designGraphs"][0]["designObjects"]
    except (StopIteration, KeyError, IndexError, ValueError, TypeError):
        objetos = []
    disenos = {o.get("id"): o for o in objetos if isinstance(o, dict) and o.get("contentType") == "f3d"}
    referidos = {i for o in disenos.values() for ref in o.get("references") or [] for i in ref.get("ids") or []}
    arriba = {o.get("relativePath") for i, o in disenos.items() if i not in referidos}
    candidatos = [i for i in nombres if i.filename in arriba] or nombres
    return miembro(datos, max(candidatos, key=lambda i: i.file_size))
