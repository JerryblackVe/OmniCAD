# -*- coding: utf-8 -*-
"""
Abre archivos de Fusion 360 (.f3d y .f3z) SIN Fusion: lee el B-rep que el archivo trae adentro.

Un .f3d es un ZIP. Cada componente guarda su geometría actual en `FusionAssetName[Active]/Breps.BlobParts/
BREP.*.smbh`: un bloque SAB de ShapeManager (el núcleo de Autodesk, derivado de ACIS), comprimido con Zstandard
(método 93 del ZIP). Este módulo saca esos bloques (`zstd_puro`), los lee (`sab`) y los pasa a OpenCascade
(`acis_occ`). Los `.smb` (sin «h») son bocetos y geometría auxiliar: no se importan.

Filtros (medidos en archivos reales de Fusion, ver PROJECT_LOG): los cuerpos sin la marca de tiempo de Fusion son
auxiliares y quedan afuera (`acis_occ.convertir`); si un componente está guardado dos veces (versión vieja y
actual) entra la versión más nueva; un cuerpo idéntico a otro no se repite (`_sin_repetidos`).

Qué NO trae (vive en el flujo de diseño propietario de Fusion, que no se lee): el historial, los parámetros, los
nombres de los cuerpos y la posición de los componentes movidos en un ensamblaje (cada uno entra donde está
guardado su B-rep). Un .f3z es un paquete con varios .f3d: se lee el diseño principal (el que nadie referencia).

Sin Qt.
"""
import io
import json
import struct
import zipfile
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer

from . import acis_occ, sab, zstd_puro

CARPETA_BREPS = "Breps.BlobParts/"
CARAS_MAX_VERIFICAR = 5000        # cuerpos más grandes no se verifican (BRepCheck tarda segundos en ellos)


class ErrorF3D(ValueError):
    """El archivo no es un .f3d/.f3z que se pueda leer, o no trae geometría."""


def leer(ruta):
    """Cuerpos de un .f3d o .f3z. Devuelve (partes, avisos): `partes` = lista de (forma OCC en mm,
    "solido" | "superficie"); `avisos` = textos para el usuario."""
    ruta = Path(ruta)
    try:
        datos = ruta.read_bytes()
    except OSError as e:
        raise ErrorF3D(f"No se pudo leer {ruta.name}: {e}") from None
    if ruta.suffix.lower() == ".f3z":
        datos = _f3d_principal(datos, ruta.name)
    return leer_bytes(datos, ruta.stem)


def leer_bytes(datos, nombre="Fusion"):
    try:
        z = zipfile.ZipFile(io.BytesIO(datos))
    except zipfile.BadZipFile:
        raise ErrorF3D(f"{nombre} no es un archivo de Fusion válido (no es un ZIP).") from None
    bloques = [i for i in z.infolist() if CARPETA_BREPS in i.filename and i.filename.lower().endswith(".smbh")]
    if not bloques:
        raise ErrorF3D(f"{nombre} no trae geometría 3D (el diseño está vacío o solo tiene bocetos).")
    leidos, avisos = [], []
    for k, info in enumerate(sorted(bloques, key=lambda i: i.filename), 1):
        try:
            archivo = sab.leer(miembro(datos, info))
        except (sab.ErrorSAB, zstd_puro.ErrorZstd) as e:
            avisos.append(f"Un componente de {nombre} no se pudo leer: {e}")
            continue
        p, a = acis_occ.convertir(archivo, f"{nombre} (componente {k})" if len(bloques) > 1 else nombre)
        avisos += a
        if p:
            leidos.append([(forma, tipo, _firma(forma, tipo), marca) for forma, tipo, marca in p])
    partes = _sin_repetidos(leidos)
    if not partes:
        raise ErrorF3D(f"{nombre} no tiene sólidos ni superficies que se puedan leer."
                       + (f" {avisos[0]}" if avisos else ""))
    malos = sum(1 for forma, tipo, n in partes if n <= CARAS_MAX_VERIFICAR and not acis_occ.es_valida(forma))
    if malos:
        avisos.append(f"{malos} de {len(partes)} cuerpos quedaron con errores de geometría (caras que tocan un polo "
                      "o un vértice de cono): se ven y se miden, pero una operación booleana con ellos puede fallar.")
    return [(forma, tipo) for forma, tipo, _ in partes], avisos


def _firma(forma, tipo):
    """Huella barata de un cuerpo: tipo, cantidad de caras y caja envolvente redondeada a 0,01 mm."""
    caja = Bnd_Box()
    BRepBndLib.Add_s(forma, caja, False)
    caras = TopExp_Explorer(forma, TopAbs_FACE)
    n = 0
    while caras.More():
        n += 1
        caras.Next()
    if caja.IsVoid():
        return (tipo, n)
    p0, p1 = caja.CornerMin(), caja.CornerMax()
    return (tipo, n) + tuple(round(v, 2) for v in (p0.X(), p0.Y(), p0.Z(), p1.X(), p1.Y(), p1.Z()))


def _sin_repetidos(leidos):
    """Junta los cuerpos de todos los bloques sin repetir: lista de (forma, tipo, cantidad de caras). Fusion puede guardar el mismo componente en dos bloques
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
            vivos.append(b)
    partes, vistas = [], set()
    for b in vivos:
        for forma, tipo, firma, _ in b:
            if firma not in vistas:
                vistas.add(firma)
                partes.append((forma, tipo, firma[1]))
    return partes


def miembro(datos, info):
    """Bytes descomprimidos de un miembro del ZIP. El método 93 (Zstandard) lo descomprime `zstd_puro`."""
    if info.compress_type != zstd_puro.METODO_ZIP_ZSTD:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            return z.read(info)
    h = info.header_offset
    if datos[h:h + 4] != b"PK\x03\x04":
        raise ErrorF3D("ZIP dañado (cabecera local inválida).")
    largo_nombre, largo_extra = struct.unpack_from("<HH", datos, h + 26)
    inicio = h + 30 + largo_nombre + largo_extra
    salida = zstd_puro.descomprimir(datos[inicio:inicio + info.compress_size])
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
