# -*- coding: utf-8 -*-
"""
Exportar glTF 2.0: .glb (contenedor binario, un solo archivo) y .gltf (JSON con el búfer embebido en base64).
Escritor propio, sin dependencias: la norma de Khronos (https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
es un JSON que describe escena, nodos, mallas y materiales más un búfer binario con los números. Sirve para la web
(three.js, model-viewer), realidad aumentada y otros programas (Blender, el visor 3D de Windows).

- Un nodo y una malla por cuerpo, hijos de un nodo raíz girado −90° en X: OmniCAD tiene Z arriba y glTF Y arriba
  (el frente de la pieza, −Y en OmniCAD, queda hacia +Z, el frente de glTF).
- Posiciones en metros (mm × 0,001: glTF usa metros), normales por vértice (las del visor: exactas en las caras
  B-rep, con ángulo de pliegue en las mallas) e índices uint16 o uint32.
- Un material PBR (metallicRoughness) por aspecto: baseColorFactor = el color del cuerpo con la prioridad del visor
  (aspecto, material físico, color propio del cuerpo) pasado de sRGB a lineal, como pide la norma; metallicFactor y
  roughnessFactor del acabado; la transparencia y la opacidad del cuerpo van al alfa (alphaMode BLEND) y las
  superficies abiertas son doubleSided. El barniz y las vetas de madera no se exportan (pedirían extensiones KHR).

FBX y USD no se escriben: FBX es un formato propietario sin especificación pública y USD necesita una biblioteca
grande (pxr) que no está entre las dependencias.
"""
import base64
import json
import struct
from pathlib import Path

import numpy as np

from .. import NOMBRE_APP, VERSION
from ..nucleo import render_cpu as rc
from .exportar import ErrorExportacion

MAGICO_GLB, CHUNK_JSON, CHUNK_BIN = 0x46546C67, 0x4E4F534A, 0x004E4942      # "glTF", "JSON", "BIN\0"
FLOAT, UINT16, UINT32 = 5126, 5123, 5125                                     # componentType
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963                            # target de los bufferView
TRIANGULOS = 4                                                               # mode de la primitiva
ESCALA = 0.001                                                               # mm → m
ROTACION_Y_ARRIBA = [-0.7071067811865476, 0.0, 0.0, 0.7071067811865476]      # cuaternión (x, y, z, w): −90° en X


def srgb_a_lineal(color):
    """Color sRGB 0..1 → lineal (la conversión de la norma sRGB): glTF guarda baseColorFactor en lineal."""
    c = np.clip(np.asarray(color, float), 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _geometria(forma, deflexion):
    """(posiciones en m, normales unitarias, triángulos) de un cuerpo: los vértices de igual posición y normal se
    comparten. None si el cuerpo no tiene triángulos."""
    v, n = rc.malla_suave(forma, deflexion)
    if not len(v):
        return None
    v = np.asarray(v, np.float64).reshape(-1, 3)
    n = np.asarray(n, np.float64).reshape(-1, 3)
    largo = np.linalg.norm(n, axis=1)
    malas = ~(largo > 0.5)
    if malas.any():                                     # normal nula (triángulo degenerado): la de su triángulo o +Z
        t = v.reshape(-1, 3, 3)
        cara = np.repeat(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), 3, axis=0)
        lc = np.linalg.norm(cara, axis=1)
        n[malas] = np.where((lc[malas] > 0)[:, None], cara[malas] / np.maximum(lc[malas], 1e-300)[:, None],
                            [0.0, 0.0, 1.0])
        largo = np.linalg.norm(n, axis=1)
    n = (n / largo[:, None]).astype(np.float32)
    p = (v * ESCALA).astype(np.float32)
    claves = np.concatenate([p, n], axis=1)
    unicas, primero, inv = np.unique(claves, axis=0, return_index=True, return_inverse=True)
    orden = np.argsort(primero)                         # orden de primera aparición (archivo estable)
    rango = np.empty_like(orden)
    rango[orden] = np.arange(len(orden))
    tris = rango[inv.reshape(-1)].reshape(-1, 3)
    tris = tris[(tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2]) & (tris[:, 0] != tris[:, 2])]
    if not len(tris):
        return None
    unicas = unicas[orden]
    return np.ascontiguousarray(unicas[:, :3]), np.ascontiguousarray(unicas[:, 3:]), tris


def _props(cuerpo, propiedades):
    if propiedades is None:
        return {}
    from ..timeline.operaciones import propiedades_cuerpo     # local: io_archivos no carga el timeline al importarse
    return propiedades_cuerpo(propiedades, cuerpo)


def material_pbr(cuerpo, props=None):
    """Material glTF (pbrMetallicRoughness) de un cuerpo: su color y acabado con la prioridad del visor."""
    props = props or {}
    color, acabado = rc.color_y_acabado(cuerpo, props)
    alfa = (1.0 - float(acabado["transparencia"])) * float(props.get("opacidad", 1.0))
    alfa = min(1.0, max(0.0, alfa))
    hexa = "#" + "".join(f"{round(255 * min(1.0, max(0.0, float(x)))):02x}" for x in color)
    material = {"name": f"{acabado.get('nombre') or 'Color'} {hexa}",
                "pbrMetallicRoughness": {"baseColorFactor": [round(float(x), 6) for x in srgb_a_lineal(color)]
                                         + [round(alfa, 6)],
                                         "metallicFactor": round(float(acabado["metalico"]), 6),
                                         "roughnessFactor": round(float(acabado["rugosidad"]), 6)}}
    if alfa < 1.0:
        material["alphaMode"] = "BLEND"
    if getattr(cuerpo, "tipo", "solido") == "superficie":
        material["doubleSided"] = True
    return material


def _agregar_vista(buffer, vistas, datos, target):
    """Agrega `datos` al búfer (alineado a 4 bytes) y su bufferView; devuelve el índice de la vista."""
    while len(buffer) % 4:
        buffer.append(0)
    vistas.append({"buffer": 0, "byteOffset": len(buffer), "byteLength": len(datos), "target": target})
    buffer.extend(datos)
    return len(vistas) - 1


def armar_gltf(cuerpos, *, propiedades=None, deflexion=0.02, nombre=NOMBRE_APP):
    """(json, búfer binario, triángulos) de un glTF 2.0 con los cuerpos (sólidos, superficies o mallas).
    `propiedades`: las del documento (`Documento.propiedades`) para el aspecto, el acabado, la opacidad y el nombre
    visible de cada cuerpo. deflexion: desvío máximo del teselado de los B-rep (mm)."""
    cuerpos = list(cuerpos)
    if not cuerpos:
        raise ErrorExportacion("No hay cuerpos para exportar.")
    buffer, vistas, accesores, mallas, nodos, materiales, claves_material = bytearray(), [], [], [], [], [], {}
    total = 0
    for c in cuerpos:
        props = _props(c, propiedades)
        geo_c = _geometria(c.forma, deflexion)
        if geo_c is None:
            continue
        pos, nor, tris = geo_c
        nombre_c = str(props.get("nombre") or getattr(c, "nombre", "") or getattr(c, "id", "Cuerpo"))
        material = material_pbr(c, props)
        clave = json.dumps(material, sort_keys=True)
        if clave not in claves_material:
            claves_material[clave] = len(materiales)
            materiales.append(material)
        tipo_indice, dt = (UINT16, "<u2") if len(pos) <= 65535 else (UINT32, "<u4")
        i_pos = len(accesores)
        accesores.append({"bufferView": _agregar_vista(buffer, vistas, pos.astype("<f4").tobytes(), ARRAY_BUFFER),
                          "componentType": FLOAT, "count": len(pos), "type": "VEC3",
                          "min": [float(x) for x in pos.min(0)], "max": [float(x) for x in pos.max(0)]})
        accesores.append({"bufferView": _agregar_vista(buffer, vistas, nor.astype("<f4").tobytes(), ARRAY_BUFFER),
                          "componentType": FLOAT, "count": len(nor), "type": "VEC3"})
        accesores.append({"bufferView": _agregar_vista(buffer, vistas, tris.astype(dt).tobytes(), ELEMENT_ARRAY_BUFFER),
                          "componentType": tipo_indice, "count": int(tris.size), "type": "SCALAR"})
        mallas.append({"name": nombre_c, "primitives": [{"attributes": {"POSITION": i_pos, "NORMAL": i_pos + 1},
                                                         "indices": i_pos + 2, "material": claves_material[clave],
                                                         "mode": TRIANGULOS}]})
        nodos.append({"name": nombre_c, "mesh": len(mallas) - 1})
        total += len(tris)
    if not total:
        raise ErrorExportacion("La malla quedó vacía.")
    while len(buffer) % 4:
        buffer.append(0)
    raiz = {"name": nombre, "rotation": ROTACION_Y_ARRIBA, "children": list(range(1, len(nodos) + 1))}
    datos = {"asset": {"version": "2.0", "generator": f"{NOMBRE_APP} {VERSION}"},
             "scene": 0, "scenes": [{"name": nombre, "nodes": [0]}], "nodes": [raiz] + nodos, "meshes": mallas,
             "materials": materiales, "accessors": accesores, "bufferViews": vistas,
             "buffers": [{"byteLength": len(buffer)}]}
    return datos, bytes(buffer), total


def a_glb(datos, buffer):
    """Bytes del contenedor GLB: cabecera de 12 bytes, chunk JSON (relleno con espacios) y chunk BIN (con ceros)."""
    texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    texto += b" " * (-len(texto) % 4)
    buffer = bytes(buffer) + b"\0" * (-len(buffer) % 4)
    partes = [struct.pack("<II", len(texto), CHUNK_JSON), texto]
    if buffer:
        partes += [struct.pack("<II", len(buffer), CHUNK_BIN), buffer]
    cuerpo = b"".join(partes)
    return struct.pack("<III", MAGICO_GLB, 2, 12 + len(cuerpo)) + cuerpo


def escribir_gltf(cuerpos, ruta, *, propiedades=None, deflexion=0.02, nombre=None):
    """Archivo › Exportar › glTF: .glb (binario) o .gltf (JSON con el búfer en base64), según la extensión.
    Devuelve la cantidad de triángulos."""
    ruta = Path(ruta)
    datos, buffer, total = armar_gltf(cuerpos, propiedades=propiedades, deflexion=deflexion,
                                      nombre=nombre or ruta.stem or NOMBRE_APP)
    if ruta.suffix.lower() == ".glb":
        ruta.write_bytes(a_glb(datos, buffer))
    else:
        datos["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(buffer).decode("ascii")
        ruta.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return total
