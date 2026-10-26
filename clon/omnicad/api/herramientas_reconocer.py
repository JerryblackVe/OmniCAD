# -*- coding: utf-8 -*-
"""SÓLIDO › CREAR › Reconocer funciones (Find Features), sin Qt: `nucleo/reconocer_funciones.py` lee la geometría y
`rebuild_features` la rehace con pasos paramétricos que ya existen (borrar caras + agujero, empalme o chaflán)."""
from typing import Literal

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import reconocer_funciones as rf
from . import selectores as sl
from .errores import ErrorAPI, error
from .registro import herramienta, llamar

Tipo = Literal["hole", "fillet", "chamfer", "extrude", "revolve", "mirror", "circular_pattern", "rectangular_pattern"]
_REHACIBLES = ("hole", "fillet", "chamfer", "extrude")
_POR_DEFECTO = ("hole", "fillet", "chamfer")        # extrude solo si se pide: reemplaza al cuerpo entero
TOL_MEDIDAS = 1e-3                     # volumen y caja del cuerpo rehecho contra el original, relativo


def _solido(sesion, body):
    cuerpo = sl.cuerpo_objetivo(sesion, body)
    if getattr(cuerpo, "tipo", "solido") != "solido":
        raise error("INVALID_ARGUMENTS", f"«{cuerpo.nombre}» no es un sólido.")
    return cuerpo


def _reconocer(cuerpo, types, permitidos=rf.TIPOS):
    try:
        return rf.reconocer_funciones(cuerpo.forma, tuple(types) if types else permitidos)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from e


@herramienta("find_features", "inspeccion", "Reconoce las funciones que forman un cuerpo sin historial, por ejemplo uno "
             "importado (SÓLIDO › CREAR › Reconocer funciones): agujeros (diámetro, profundidad, pasante, avellanado, "
             "punto de entrada), empalmes (radio, convexo o cóncavo), chaflanes (ancho, ángulo y distancia), extrusión "
             "(el cuerpo entero es un prisma: dirección, distancia y área del perfil), revolución (todas las caras "
             "giran alrededor de un eje: eje y ángulo) y grupos de agujeros, empalmes o chaflanes iguales: patrón "
             "rectangular (direcciones, cantidad y paso), circular (eje, cantidad y paso angular) o simetría (plano X, Y "
             "o Z por el centro de la caja del cuerpo). Cada función trae los ids de sus caras (find_faces). Solo lee: "
             "rebuild_features rehace en el timeline los agujeros, empalmes y chaflanes. No cambia el documento.")
def find_features(sesion, body: str | None = None, types: list[Tipo] | None = None):
    """
    body: id o nombre del cuerpo sólido; vacío = el único cuerpo.
    types: qué reconocer: hole, fillet, chamfer, extrude, revolve, mirror, circular_pattern, rectangular_pattern; vacío = todo.
    """
    cuerpo = _solido(sesion, body)
    r = _reconocer(cuerpo, types)
    elementos = {i: next(e for e in sl.listar(cuerpo.forma, "cara") if e.sub.IsSame(f))
                 for i, f in enumerate(r["face_shapes"], 1)}
    usadas = {i for f in r["features"] for i in f["faces"]}
    ids = {i: sl.emitir_id(sesion, cuerpo, elementos[i]) for i in usadas}
    funciones = [dict(f, faces=[ids[i] for i in f["faces"]]) for f in r["features"]]
    return {"body": cuerpo.id, "faces": r["faces"], "features": funciones,
            "summary": {t: sum(f["type"] == t for f in funciones) for t in (types or rf.TIPOS)}}


# ---------------------------------------------------------------- rehacer en el timeline
def _medidas(forma):
    bb = geo.caja_envolvente(forma)
    return abs(geo.volumen(forma)), np.array(bb[0]), np.array(bb[1])


def _coinciden(a, b):
    diagonal = float(np.linalg.norm(a[2] - a[1]))
    return (abs(a[0] - b[0]) <= TOL_MEDIDAS * a[0] and np.abs(a[1] - b[1]).max() <= TOL_MEDIDAS * diagonal
            and np.abs(a[2] - b[2]).max() <= TOL_MEDIDAS * diagonal)


def _clave(f):
    """Dónde y cuánto: identifica la función entre una vuelta y la siguiente (los ids de caras cambian)."""
    if f["type"] == "hole":
        p = np.array(f["axis_point"]) + np.array(f["axis"]) * f["depth"] / 2
        return ("hole", *np.round(p, 3), round(f["diameter"], 3))
    return (f["type"], *np.round(f["center"], 3), round(f.get("radius", f.get("width", 0)), 3))


def _ids(sesion, cuerpo, r, indices):
    caras = sl.listar(cuerpo.forma, "cara")
    return [sl.emitir_id(sesion, cuerpo, next(e for e in caras if e.sub.IsSame(r["face_shapes"][i - 1])))
            for i in indices]


def _llamar(sesion, nombre, args):
    res = llamar(sesion, nombre, args)
    if not res["ok"]:
        raise error("OPERATION_FAILED", f"{nombre}: {res['mensaje']}")
    return res["result"]


def _punto(p):
    return "[" + ",".join(f"{x:.6f}" for x in p) + "]"


def _rehacer(sesion, cuerpo, r, f, socio):
    """Borra las caras de la función (las vecinas cierran el hueco) y la vuelve a crear con su paso paramétrico."""
    nombre = cuerpo.id
    caras = f["faces"] + (socio["faces"] if socio else [])
    _llamar(sesion, "delete_faces", {"faces": _ids(sesion, cuerpo, r, caras), "body": nombre})
    if f["type"] == "fillet":
        return _llamar(sesion, "fillet", {"edges": f"nearest:{_punto(f['center'])}", "radius": f["radius"],
                                          "body": nombre, "tangent_chain": False})
    if f["type"] == "chamfer":
        return _llamar(sesion, "chamfer", {"edges": f"nearest:{_punto(f['center'])}", "distance": f["distance"],
                                           "body": nombre})                      # la cadena tangente rehace la vuelta
    boca = f
    if socio:                                                      # avellanado: el agujero ancho es la boca
        boca, f = (f, socio) if f["diameter"] > socio["diameter"] else (socio, f)
    if boca["entry_point"] is None:
        raise error("OPERATION_FAILED", "El agujero está cerrado por los dos lados: no tiene por dónde entrar.")
    args = {"face": f"%PLANE and nearest:{_punto(boca['entry_point'])}", "body": nombre, "diameter": f["diameter"],
            "points": [boca["entry_point"]]}
    if f["through"]:
        args["through_all"] = True
    else:
        args["depth"] = f["depth"] + (boca["depth"] if socio else 0)
    if socio:
        args.update(hole_type="counterbore", counterbore_diameter=boca["diameter"], counterbore_depth=boca["depth"])
    return _llamar(sesion, "create_hole", args)


class _NoCoincide(Exception):
    pass


def _rehacer_extrusion(sesion, cuerpo, r, f):
    """Un cuerpo que es un prisma (con todos sus agujeros pasantes dentro del perfil) se rehace como boceto + extrusión: el
    boceto se apoya en la primera tapa y proyecta su contorno (con los agujeros), la extrusión entra por el cuerpo. El
    cuerpo nuevo reemplaza al importado, con su mismo nombre."""
    tapa = r["face_shapes"][f["faces"][0] - 1]
    seleccion = f"nearest:{_punto(geo.centro_masa(tapa, True))}"
    d = np.asarray(f["direction"], float)                      # de la primera tapa hacia la segunda
    nombre, previos = cuerpo.nombre, set(sesion.doc.estado_final.cuerpos)
    sk = _llamar(sesion, "create_sketch", {"plane": _ids(sesion, cuerpo, r, f["faces"][:1])[0],
                                           "name": f"Perfil de {nombre}"})["sketch"]["id"]
    _llamar(sesion, "project_to_sketch", {"faces": [seleccion], "body": cuerpo.id, "sketch": sk})
    normal = np.asarray(sesion.doc.estado_final.bocetos[sk].plano.normal, float)
    nuevo = _llamar(sesion, "extrude", {"sketch": sk, "profile": "largest", "operation": "new_body",
                                        "distance": f["distance"] * (1 if float(d @ normal) > 0 else -1)})
    creado = nuevo["bodies_created"][0]["id"]
    _llamar(sesion, "remove_bodies", {"bodies": [cuerpo.id]})
    _llamar(sesion, "rename", {"target": creado, "new_name": nombre, "kind": "body"})
    return creado, previos


@herramienta("rebuild_features", "solido", "Find Features que rehace: reconoce los agujeros (también abocardados), "
             "empalmes y chaflanes de un cuerpo sin historial y los vuelve pasos paramétricos del timeline, uno por uno: "
             "borra las caras de la función (delete_faces, las vecinas cierran el hueco) y la crea de nuevo con "
             "create_hole, fillet o chamfer y las medidas reconocidas; después vuelve a reconocer sobre el cuerpo "
             "nuevo. Cada función rehecha se verifica: el volumen y la caja del cuerpo tienen que seguir iguales a los "
             "del original (1e-3 relativo); si no, ese cambio se deshace y la función queda en not_rebuilt con el "
             "motivo. Extrusiones, revoluciones, simetrías y patrones solo se informan (find_features). Todo es UN paso "
             "de deshacer.", modifica=True)
def rebuild_features(sesion, body: str | None = None,
                     types: list[Literal["hole", "fillet", "chamfer", "extrude"]] | None = None, max_features: int = 50):
    """
    body: id o nombre del cuerpo sólido; vacío = el único cuerpo.
    types: qué rehacer: hole, fillet, chamfer o extrude; vacío = hole, fillet y chamfer. extrude solo para un cuerpo prisma (agujeros pasantes en su perfil): lo rehace como boceto + extrusión y reemplaza al cuerpo; va primero.
    max_features: tope de funciones a intentar (cada una deja dos pasos en el timeline).
    """
    if max_features < 1:
        raise error("INVALID_ARGUMENTS", f"max_features tiene que ser 1 o más (recibió {max_features}).")
    cuerpo = _solido(sesion, body)
    original = _medidas(cuerpo.forma)
    vistas, rehechas, no_rehechas = set(), [], []
    if types and "extrude" in types:
        r = _reconocer(cuerpo, ["extrude"], _REHACIBLES)
        if r["features"]:
            f = r["features"][0]
            info = {k: v for k, v in f.items() if k != "faces"}
            antes = len(sesion.doc.operaciones)
            try:
                with sesion.transaccion():
                    creado, _ = _rehacer_extrusion(sesion, cuerpo, r, f)
                    if not _coinciden(original, _medidas(sesion.cuerpo(creado).forma)):
                        raise _NoCoincide
            except _NoCoincide:
                no_rehechas.append(dict(info, reason="El cuerpo rehecho no coincide con el original (volumen o caja)."))
            except ErrorAPI as e:
                no_rehechas.append(dict(info, reason=e.mensaje))
            else:
                rehechas.append(dict(info, steps=[o.id for o in sesion.doc.operaciones[antes:]]))
                return {"body": creado, "rebuilt": rehechas, "not_rebuilt": no_rehechas,
                        "summary": {t: sum(g["type"] == t for g in rehechas) for t in _REHACIBLES}}
        types = [t for t in types if t != "extrude"]
        if not types:
            sesion.avisar("El cuerpo no es un prisma: no hay una extrusión que rehacer.")
            return {"body": cuerpo.id, "rebuilt": rehechas, "not_rebuilt": no_rehechas,
                    "summary": {t: sum(g["type"] == t for g in rehechas) for t in _REHACIBLES}}
    while len(vistas) < max_features:
        cuerpo = sesion.cuerpo(cuerpo.id)
        r = _reconocer(cuerpo, types, _POR_DEFECTO)
        pendientes = [f for f in r["features"] if _clave(f) not in vistas]
        if not pendientes:
            break
        f = pendientes[0]
        socio = r["features"][f["counterbore_with"]] if "counterbore_with" in f else None
        vistas.update(_clave(g) for g in (f, socio) if g)
        chico, ancho = sorted((f, socio), key=lambda g: g["diameter"]) if socio else (f, None)
        info = {k: v for k, v in chico.items() if k not in ("faces", "counterbore_with")}
        if ancho:
            info.update(counterbore_diameter=ancho["diameter"], counterbore_depth=ancho["depth"],
                        entry_point=ancho["entry_point"])
        antes = len(sesion.doc.operaciones)
        try:
            with sesion.transaccion():
                _rehacer(sesion, cuerpo, r, f, socio)
                if not _coinciden(original, _medidas(sesion.cuerpo(cuerpo.id).forma)):
                    raise _NoCoincide
        except _NoCoincide:
            no_rehechas.append(dict(info, reason="El cuerpo rehecho no coincide con el original (volumen o caja)."))
            continue
        except ErrorAPI as e:
            no_rehechas.append(dict(info, reason=e.mensaje))
            continue
        rehechas.append(dict(info, steps=[o.id for o in sesion.doc.operaciones[antes:]]))
    if not rehechas and not no_rehechas:
        sesion.avisar("No se encontró ningún agujero, empalme ni chaflán para rehacer.")
    return {"body": cuerpo.id, "rebuilt": rehechas, "not_rebuilt": no_rehechas,
            "summary": {t: sum(f["type"] == t for f in rehechas) for t in _POR_DEFECTO}}
