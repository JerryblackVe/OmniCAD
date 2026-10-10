# -*- coding: utf-8 -*-
"""Exportar glTF 2.0 (.glb y .gltf): se escribe y se vuelve a leer con un lector mínimo propio (json + struct), sin
librerías de glTF: triángulos, posiciones en metros, eje Y arriba y el material con el color del cuerpo."""
import base64
import json
import struct

import numpy as np
import pytest

from omnicad import api
from omnicad.io_archivos import exportar as ex
from omnicad.io_archivos import gltf
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import malla as ml

TIPOS = {5126: "<f4", 5123: "<u2", 5125: "<u4"}
COMPONENTES = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}


class _Cuerpo:
    def __init__(self, forma, tipo="solido", nombre="Pieza", cid="op1.c1"):
        self.forma, self.tipo, self.nombre, self.id = forma, tipo, nombre, cid
        self.apariencia = self.material = None


# ---------------------------------------------------------------- lector mínimo (no usa el código de OmniCAD)
def leer_glb(ruta):
    """(json, búfer binario) de un .glb, comprobando la cabecera y los dos chunks."""
    datos = ruta.read_bytes()
    magico, version, largo = struct.unpack_from("<III", datos, 0)
    assert (magico, version, largo) == (0x46546C67, 2, len(datos))
    largo_json, tipo_json = struct.unpack_from("<II", datos, 12)
    assert tipo_json == 0x4E4F534A and largo_json % 4 == 0
    texto = datos[20:20 + largo_json]
    largo_bin, tipo_bin = struct.unpack_from("<II", datos, 20 + largo_json)
    assert tipo_bin == 0x004E4942 and largo_bin % 4 == 0
    inicio = 28 + largo_json
    assert inicio + largo_bin == len(datos)
    return json.loads(texto.decode("utf-8")), datos[inicio:inicio + largo_bin]


def leer_gltf(ruta):
    js = json.loads(ruta.read_text(encoding="utf-8"))
    uri = js["buffers"][0]["uri"]
    assert uri.startswith("data:application/octet-stream;base64,")
    return js, base64.b64decode(uri.split(",", 1)[1])


def accessor(js, binario, i):
    a = js["accessors"][i]
    vista = js["bufferViews"][a["bufferView"]]
    assert vista["byteOffset"] % 4 == 0
    n = a["count"] * COMPONENTES[a["type"]]
    datos = np.frombuffer(binario, TIPOS[a["componentType"]], n, vista["byteOffset"] + a.get("byteOffset", 0))
    return datos.reshape(a["count"], -1) if a["type"] != "SCALAR" else datos


def primitivas(js, binario):
    """[(nombre, posiciones, normales, triángulos, material)] de cada malla."""
    salida = []
    for m in js["meshes"]:
        (p,) = m["primitives"]
        assert p.get("mode", 4) == 4
        pos = accessor(js, binario, p["attributes"]["POSITION"])
        nor = accessor(js, binario, p["attributes"]["NORMAL"])
        tris = accessor(js, binario, p["indices"]).reshape(-1, 3)
        salida.append((m["name"], pos, nor, tris, js["materials"][p["material"]]))
    return salida


def lineal(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def rotar(q, v):
    """Gira el vector v con el cuaternión glTF (x, y, z, w)."""
    x, y, z, w = q
    u = np.array([x, y, z])
    v = np.asarray(v, float)
    return 2 * (u @ v) * u + (w * w - u @ u) * v + 2 * w * np.cross(u, v)


def volumen(pos, tris):
    t = pos[tris].astype(float)
    return float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6)


# ---------------------------------------------------------------- pruebas
def test_caja_de_10_mm_en_glb_con_el_color_del_cuerpo(tmp_path):
    s = api.Sesion()
    caja = api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10, "z": -5})["result"]
    cid = caja["bodies_created"][0]["id"]
    assert api.llamar(s, "set_appearance", {"bodies": [cid], "appearance": "Aluminio - Anodizado (rojo)"})["ok"]
    r = api.llamar(s, "export", {"path": str(tmp_path / "caja.glb")})
    assert r["ok"] and r["result"]["format"] == "glb" and r["result"]["triangles"] == 12
    js, binario = leer_glb(tmp_path / "caja.glb")
    assert js["asset"]["version"] == "2.0" and js["buffers"][0]["byteLength"] == len(binario)
    ((nombre, pos, nor, tris, material),) = primitivas(js, binario)
    assert nombre == "Cuerpo1" and len(tris) == 12 and tris.max() < len(pos)
    a = js["accessors"][js["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
    assert a["min"] == pytest.approx([-0.005] * 3) and a["max"] == pytest.approx([0.005] * 3)
    assert a["min"] == pos.min(0).tolist() and a["max"] == pos.max(0).tolist()     # lo declarado = lo guardado
    assert volumen(pos, tris) == pytest.approx(1e-6, rel=1e-5)                   # 1000 mm³ = 1e-6 m³, hacia afuera
    assert np.allclose(np.linalg.norm(nor, axis=1), 1, atol=1e-6)
    pbr = material["pbrMetallicRoughness"]
    assert pbr["baseColorFactor"] == pytest.approx(list(lineal((0.62, 0.06, 0.07))) + [1.0], abs=1e-6)
    assert pbr["metallicFactor"] == pytest.approx(0.85) and pbr["roughnessFactor"] == pytest.approx(0.35)
    assert "alphaMode" not in material and not material.get("doubleSided")
    # Y arriba: el nodo raíz gira −90° en X (Z de OmniCAD → Y de glTF) y la caja es su hija.
    raiz = js["nodes"][js["scenes"][js["scene"]]["nodes"][0]]
    assert raiz["children"] == [1] and js["nodes"][1]["mesh"] == 0
    assert rotar(raiz["rotation"], [0, 0, 1]) == pytest.approx([0, 1, 0], abs=1e-12)
    assert rotar(raiz["rotation"], [0, -1, 0]) == pytest.approx([0, 0, 1], abs=1e-12)     # frente → +Z


def test_gltf_con_bufer_embebido_y_un_nodo_por_cuerpo(tmp_path):
    cuerpos = [_Cuerpo(geo.caja(10, 10, 10, (0, 0, 0)), nombre="A", cid="op1.c1"),
               _Cuerpo(geo.cilindro(5, 20), nombre="B", cid="op2.c1")]
    props = {"op2.c1": {"apariencia": [0.1, 0.2, 0.9], "acabado": {"metalico": 0.0, "rugosidad": 0.6,
                                                                    "transparencia": 0.5}, "nombre": "Eje"}}
    n = ex.exportar(cuerpos, tmp_path / "dos.gltf", props)
    js, binario = leer_gltf(tmp_path / "dos.gltf")
    prims = primitivas(js, binario)
    assert [p[0] for p in prims] == ["A", "Eje"] and len(js["nodes"]) == 3
    assert n == sum(len(p[3]) for p in prims)
    assert volumen(prims[0][1], prims[0][3]) == pytest.approx(1e-6, rel=1e-5)
    assert volumen(prims[1][1], prims[1][3]) == pytest.approx(np.pi * 25 * 20 * 1e-9, rel=0.01)
    vidrio = prims[1][4]
    assert vidrio["alphaMode"] == "BLEND" and vidrio["pbrMetallicRoughness"]["baseColorFactor"][3] == 0.5
    assert vidrio["pbrMetallicRoughness"]["baseColorFactor"][:3] == pytest.approx(lineal((0.1, 0.2, 0.9)), abs=1e-6)
    assert vidrio["pbrMetallicRoughness"]["roughnessFactor"] == 0.6
    assert len(js["materials"]) == 2


def test_malla_y_superficie(tmp_path):
    v = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]], float)
    malla = ml.Malla(v, [[0, 1, 2], [0, 2, 3]])
    lamina = geo.caja(10, 10, 10, (20, 0, 0))
    cuerpos = [_Cuerpo(malla, "malla", "Malla"), _Cuerpo(lamina, "superficie", "Lámina", "op2.c1")]
    ex.exportar(cuerpos, tmp_path / "varios.glb")
    js, binario = leer_glb(tmp_path / "varios.glb")
    prims = primitivas(js, binario)
    assert len(prims[0][3]) == 2 and len(prims[0][1]) == 4                    # 4 vértices compartidos
    assert prims[0][2] == pytest.approx(np.tile([0, 0, 1], (4, 1)))
    assert prims[1][4].get("doubleSided") is True and not prims[0][4].get("doubleSided")
    assert prims[1][0] == "Lámina"                                            # nombres en UTF-8


def test_errores_y_formatos(tmp_path):
    with pytest.raises(ex.ErrorExportacion, match="No hay cuerpos"):
        ex.exportar([], tmp_path / "nada.glb")
    for ext in ("fbx", "usd", "usdz"):                                        # FBX y USD no: formatos fuera de alcance
        with pytest.raises(ex.ErrorExportacion, match="Formato no soportado"):
            ex.exportar([_Cuerpo(geo.caja(1, 1, 1))], tmp_path / f"x.{ext}")
    assert {"glb", "gltf"} <= set(ex.FORMATOS)
    datos, binario, n = gltf.armar_gltf([_Cuerpo(geo.caja(1, 2, 3))])
    assert n == 12 and len(binario) % 4 == 0 and len(gltf.a_glb(datos, binario)) % 4 == 0
    assert gltf.srgb_a_lineal([0, 1, 0.5]) == pytest.approx([0, 1, 0.21404114], abs=1e-7)
