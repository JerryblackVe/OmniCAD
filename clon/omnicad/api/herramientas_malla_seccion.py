# -*- coding: utf-8 -*-
"""
Herramientas de sección de malla (ingeniería inversa de una malla, núcleo en `nucleo/malla_seccion.py`):

- create_mesh_section_sketch: MALLA › CREAR › Crear boceto de sección de malla de Fusion. Boceto nuevo sobre el plano
  con la línea de sección (una spline fija, de construcción, por lazo del corte).
- fit_curves_to_mesh_section: BOCETO › CREAR › Ajustar curvas a sección de malla. Curvas de boceto normales (líneas,
  arcos, splines, círculo, elipse) que siguen la sección, con su desviación real.

La sección queda guardada en el boceto (se abre igual); no sigue a la malla si después cambia.
"""
from typing import Literal

from ..nucleo import geometria as geo
from ..nucleo import malla_seccion as ms
from ..restricciones import ErrorBoceto
from ..timeline.operaciones import OpBoceto
from ..timeline.parametros import LONGITUD, evaluar
from .errores import error
from .herramientas_boceto import (_dibujar, _info_plano, _paso, boceto_activo, boceto_resuelto, nombre_nuevo,
                                  plano_o_cara, texto_expr)
from .herramientas_malla import _cuerpos
from .registro import Expr, herramienta

_TIPOS = {"line": "linea", "arc": "arco", "spline": "spline", "closed_spline": "spline_cerrada", "circle": "circulo",
          "ellipse": "elipse", "lines_and_arcs": "lineas_arcos"}
_A_INGLES = {"linea": "line", "arco": "arc", "spline": "spline", "circulo": "circle", "elipse": "ellipse"}


def _mm(sesion, valor, que, minimo=0.0):
    v = evaluar(texto_expr(valor), LONGITUD, sesion.doc.parametros.valores())
    if not v > minimo:
        raise error("INVALID_ARGUMENTS", f"{que} tiene que ser mayor que {minimo:g} mm (recibió {v:g}).")
    return v


def _r(x):
    return round(float(x), 4) + 0.0


@herramienta("create_mesh_section_sketch", "malla",
             "Crea un boceto de sección de malla (MALLA › CREAR › Crear boceto de sección de malla de Fusion): un "
             "boceto nuevo sobre el plano con la línea donde el plano corta la malla, como spline fija de construcción "
             "(una por lazo). offset desplaza el plano de sección sobre su normal. Después, "
             "fit_curves_to_mesh_section dibuja curvas que la siguen. Coordenadas del boceto como en create_sketch.",
             modifica=True)
def create_mesh_section_sketch(sesion, body: str, plane: str = "XY", offset: Expr = 0, name: str | None = None,
                               plane_body: str | None = None, angle: Expr = 0):
    """
    body: id o nombre del cuerpo de malla.
    plane: "XY", "XZ", "YZ", el id o nombre de un plano de construcción, o una cara plana de un sólido (selector como ">Z" o id de find_faces).
    offset: distancia en mm del plano de sección al plano elegido, sobre su normal (número o expresión).
    name: nombre del boceto; vacío = "Boceto1", "Boceto2"…
    plane_body: cuerpo sólido donde se evalúa el selector de cara de plane; vacío = el único sólido.
    angle: giro en grados (número o expresión) del plano de sección alrededor de su eje u, después del offset.
    """
    (cuerpo,) = _cuerpos(sesion, body, que="body")
    doc = sesion.doc
    ref, marco, _cara, ref_cara = plano_o_cara(sesion, plane, plane_body)
    nombre = name.strip() if name and name.strip() else nombre_nuevo(doc, "Boceto", OpBoceto)
    op = OpBoceto(doc.nuevo_id(), nombre, plano=ref, marco=marco, cara=ref_cara, desplazamiento=texto_expr(offset),
                  angulo_plano=texto_expr(angle))
    doc.agregar(op)
    br = boceto_resuelto(sesion, op)
    if br is None:
        raise error("OPERATION_FAILED", f"No se pudo ubicar el plano de sección «{plane}».")
    try:
        polilineas = ms.seccion(cuerpo.forma, br.plano)
    except geo.ErrorGeometria as e:
        raise error("OPERATION_FAILED", f"{e} Revisá el plano y offset (get_mesh_info da la caja de la malla).") from e
    informe = _dibujar(sesion, op.id, lambda b: b.agregar_proyeccion(ms.primitivas_seccion(polilineas), construccion=True))
    ids = [e["id"] for e in informe["entities"]]
    return {"sketch": _paso(op), "body": cuerpo.id, "plane_frame": _info_plano(br.plano),
            "sections": [{"entity": cid, "closed": cerrada, "points": len(P),
                          "length": _r(ms.largo(ms.cerrar(P) if cerrada else P))}
                         for cid, (P, cerrada) in zip(ids, polilineas, strict=True)]}


@herramienta("fit_curves_to_mesh_section", "malla",
             "Ajusta curvas a la sección de malla de un boceto (BOCETO › CREAR › Ajustar curvas a sección de malla de "
             "Fusion). curve_type: line, arc o spline (abiertas: de start a end sobre la sección, por el camino short o "
             "long), closed_spline, circle o ellipse (siguen toda la sección), o lines_and_arcs (no está en Fusion: "
             "líneas y arcos dentro de max_deviation, toda la sección o de start a end). Las curvas son geometría normal "
             "del boceto: un extremo que cae en un punto ya dibujado lo comparte (la curva siguiente arranca donde "
             "terminó la anterior) y un lazo cerrado da perfil. Sin restricciones (como Fusion, salvo la tangencia). "
             "Devuelve la desviación real de cada curva; avisa si pasa de max_deviation.", modifica=True)
def fit_curves_to_mesh_section(sesion, sketch: str, curve_type: Literal["line", "arc", "spline", "closed_spline",
                                                                        "circle", "ellipse", "lines_and_arcs"],
                               section: int | None = None, start: list[float] | None = None,
                               end: list[float] | None = None, path: Literal["short", "long"] = "short",
                               tolerance: Expr = 0.1, max_deviation: Expr = 0.1):
    """
    sketch: id o nombre del boceto de sección de malla (create_mesh_section_sketch).
    curve_type: "line", "arc", "spline", "closed_spline", "circle", "ellipse" o "lines_and_arcs".
    section: id de la línea de sección (sections de create_mesh_section_sketch); vacío = la más cercana a start, o todas las cerradas para las curvas cerradas sin start.
    start: [x, y] del primer punto sobre la sección (mm, coordenadas del boceto); se toma el punto de la sección más cercano.
    end: [x, y] del segundo punto sobre la sección.
    path: "short" (camino corto) o "long" (camino largo) entre start y end en una sección cerrada.
    tolerance: tolerancia de ajuste de spline en mm: más chica, más puntos y mejor ajuste.
    max_deviation: desviación máxima en mm entre cada curva y la sección (límite de lines_and_arcs; si una curva lo pasa, avisa).
    """
    op, br = boceto_activo(sesion, sketch, derivados=False)
    secciones = ms.secciones_de_boceto(br.boceto)
    if not secciones:
        raise error("INVALID_ARGUMENTS", f"El boceto «{op.nombre}» ({op.id}) no tiene sección de malla.",
                    "create_mesh_section_sketch crea un boceto con la sección de una malla.")
    if section is not None and section not in secciones:
        raise error("ENTITY_NOT_FOUND", f"La entidad {section} no es una sección de malla del boceto «{op.nombre}»: "
                    f"son {sorted(secciones)}.")
    tol, desvio = _mm(sesion, tolerance, "tolerance"), _mm(sesion, max_deviation, "max_deviation")
    tipo = _TIPOS[curve_type]
    if (start is None) != (end is None):
        raise error("INVALID_ARGUMENTS", "start y end van juntos: los dos puntos sobre la sección.")
    if start is None and tipo in ("linea", "arco", "spline"):
        raise error("INVALID_ARGUMENTS", f"curve_type={curve_type} va de start a end: pasá los dos puntos [x, y].")
    if start is not None and tipo in ms.CERRADOS:
        raise error("INVALID_ARGUMENTS", f"curve_type={curve_type} sigue toda la sección: no lleva start ni end.")
    if section is not None:
        elegidas = [section]
    elif start is not None:
        elegidas = [min(secciones, key=lambda k: float(ms.distancia([start], ms.cerrar(secciones[k][0])
                                                                     if secciones[k][1] else secciones[k][0])[0]))]
    else:
        elegidas = [k for k, (_P, cerrada) in secciones.items() if cerrada or tipo == "lineas_arcos"]
        if not elegidas:
            raise error("INVALID_ARGUMENTS", "Las secciones del boceto son abiertas: una curva cerrada necesita una "
                        "sección cerrada (o usá start y end).")
    try:
        curvas = [c for k in elegidas
                  for c in ms.ajustar(*secciones[k], tipo, inicio=start, fin=end,
                                      camino="corto" if path == "short" else "largo", tolerancia=tol,
                                      desviacion=desvio)]
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from e
    hechas = []

    def dibujar(b):
        hechas.extend(ms.agregar_curvas(b, curvas))
    try:
        informe = _dibujar(sesion, op.id, dibujar, desde_solver=True)
    except ErrorBoceto as e:
        raise error("INVALID_GEOMETRY", str(e)) from e
    pasan = [cid for cid, d in hechas if d > desvio]
    if pasan:
        sesion.avisar(f"Las curvas {pasan} se apartan de la sección más que max_deviation ({desvio:g} mm): "
                      "partí el tramo, usá otro tipo de curva o bajá tolerance.")
    return {"sketch": informe["sketch"], "sections": elegidas,
            "curves": [{"id": cid, "type": _A_INGLES[c["tipo"]], "max_deviation": _r(d)}
                       for (cid, d), c in zip(hechas, curvas, strict=True)],
            "profiles": informe["profiles"], "status": informe["status"], "dof": informe["dof"]}
