# -*- coding: utf-8 -*-
"""
Informe de cobertura del historial de un .f3d (mejora CL8: lo que no se traduce se declara, no se oculta).

El historial de Fusion (el timeline) vive en el flujo de diseño propietario del archivo
(`FusionDesignSegmentType1/BulkStream.dat`; en los archivos viejos `Design1/BulkStream.dat`). Ese flujo trae una tabla con
los tipos de objeto que contiene —«DcExtrudeFeatureMetaType», «DcSketchMetaType»…— y cuántos hay de cada uno; es lo único
del historial que se lee de forma confiable. Las operaciones en sí (qué perfil se extruye, qué aristas se empalman) no se
traducen: las selecciones se guardan como «recetas de nombre persistente» (`edge_recipe_data`, `face_recipe_data`) que solo
Fusion sabe resolver contra la historia de su modelo, y el archivo guarda únicamente el estado final del B-rep. El modelo
entra como su forma final y los bocetos se reconstruyen de sus perfiles (`f3d_bocetos`).

Sin Qt.
"""
import re
import struct

# Nombre del tipo en el flujo (sin «Dc» ni «MetaType») → cómo se llama en el timeline de Fusion en español.
NOMBRES = {
    "Sketch": "Boceto", "ExtrudeFeature": "Extruir", "RevolveFeature": "Revolución", "SweepFeature": "Barrido",
    "LoftFeature": "Solevación", "FilletEdgeFeature": "Empalme", "ChamferFeature": "Chaflán",
    "CombineFeature": "Combinar", "MirrorPattern": "Simetría", "CircularPattern": "Patrón circular",
    "RectangularPattern": "Patrón rectangular", "DeleteBody": "Eliminar cuerpo", "DeleteFaceFeature": "Eliminar cara",
    "OffsetFacesFeature": "Desfasar caras", "WorkPlane": "Plano de trabajo", "ParaMeshBaseFeature": "Elemento de malla base",
    "ParaMeshToBREP": "Convertir malla", "AlignFeature": "Alinear", "MoveFeature": "Mover/Copiar",
    "PasteBodies": "Pegar cuerpos", "EmbossFeature": "Relieve", "BaseFeature": "Operación base", "Canvas": "Lienzo",
    "ShellFeature": "Vaciado", "HoleFeature": "Agujero", "ThreadFeature": "Rosca", "SplitBodyFeature": "Dividir cuerpo",
    "ScaleFeature": "Escala", "ThickenFeature": "Engrosar", "SplitFaceFeature": "Dividir cara",
    "TrimFeature": "Recortar", "PatchFeature": "Parche", "StitchFeature": "Coser", "DraftFeature": "Ángulo de desmoldeo",
    "RibFeature": "Nervio", "WebFeature": "Alma", "CoilFeature": "Espiral", "PipeFeature": "Tubo",
}
_TIPO = re.compile(rb"([\x05-\x50])\x00\x00\x00(Dc\w+?MetaType)", re.S)


def operaciones(flujo):
    """[(tipo del flujo, cantidad)] de la tabla de tipos del flujo de diseño, en el orden del archivo (lista vacía si no
    se encuentra: un archivo de otra versión). Ej.: [("ExtrudeFeature", 44), ("Sketch", 10)]."""
    salida = []
    for m in _TIPO.finditer(flujo):
        nombre = m.group(2)
        if len(nombre) != m.group(1)[0] or m.end() + 8 > len(flujo):
            continue
        cantidad = struct.unpack_from("<Q", flujo, m.end())[0]
        if cantidad < 1_000_000:                                  # un contador, no basura
            salida.append((nombre[2:-8].decode("ascii"), int(cantidad)))
    return salida


def nombre(tipo):
    """Nombre en español del tipo de operación; los que no se conocen salen con su nombre del flujo."""
    return NOMBRES.get(tipo, tipo)


def aviso(historial, bocetos_importados, archivo="El archivo"):
    """Texto de cobertura para el usuario, o None si no hay historial que declarar. `bocetos_importados` = cuántos
    bocetos se reconstruyeron de los perfiles."""
    otros = [(t, n) for t, n in historial if t != "Sketch"]
    bocetos = next((n for t, n in historial if t == "Sketch"), 0)
    if not otros and not bocetos:
        return None
    partes = [f"{n} × {nombre(t)}" for t, n in otros]
    texto = (f"{archivo} trae el historial de Fusion (el timeline), que NO se traduce: "
             + (", ".join(partes) if partes else "sin más operaciones")
             + f". Fusion cuenta {bocetos} bocetos y se importaron {bocetos_importados} (reconstruidos de los perfiles "
             "cerrados: faltan los trazos abiertos, las cotas y las restricciones). El modelo entra como su forma final: "
             "los cuerpos son operaciones congeladas y los parámetros de las operaciones no se pueden editar.")
    return texto
