# -*- coding: utf-8 -*-
"""
Herramienta del grupo "solido" para impresión 3D: la pieza de calibración de holguras (`create_clearance_test`).
Agrega UN paso del timeline («calibracion_holguras», editable con edit_feature) que crea dos cuerpos: la placa de
agujeros y el peine de pernos. El núcleo está en `nucleo/calibracion.py`. Unidades: mm.
"""
from ..nucleo import calibracion as cal
from ..timeline.operaciones import Contexto
from ..timeline.ops_calibracion import OpCalibracionHolguras
from .errores import error
from .herramientas_boceto import nombre_nuevo, texto_expr
from .herramientas_solido import _agregar, _numero_positivo
from .registro import Expr, herramienta


@herramienta("create_clearance_test", "solido",
             "Crea la pieza de calibración de holguras para impresión 3D (como la tira de tolerancias de Cura): una "
             "placa con count agujeros pasantes de Ø diameter + 2·holgura, con la holgura radial creciente desde "
             "start_clearance en saltos de step y su valor grabado junto a cada agujero, más un peine con los pernos de "
             "Ø diameter a la misma distancia. Se imprimen los dos (quedan lado a lado en el plano XY, apoyados en "
             "Z = 0), se prueba cuál agujero encaja bien y ese valor es el print_clearance de create_hole y "
             "create_thread. Es UN paso del timeline con dos cuerpos nuevos.", modifica=True)
def create_clearance_test(sesion, diameter: Expr, start_clearance: Expr = 0.1, step: Expr = 0.1, count: int = 5,
                          thickness: Expr = 3, labels: bool = True):
    """
    diameter: diámetro del perno en mm; los agujeros miden diameter + 2·holgura.
    start_clearance: holgura radial del primer agujero en mm (0 o más).
    step: lo que sube la holgura de un agujero al siguiente, en mm (positivo).
    count: cantidad de agujeros (de 1 a 20).
    thickness: espesor de la placa en mm; el peine tiene un perno que la atraviesa.
    labels: true para grabar la holgura de cada agujero (0,4 mm de profundidad).
    """
    _numero_positivo(diameter, "diameter")
    _numero_positivo(step, "step")
    _numero_positivo(thickness, "thickness")
    if isinstance(start_clearance, (int, float)) and start_clearance < 0:
        raise error("INVALID_ARGUMENTS", f"start_clearance no puede ser negativa (recibió {start_clearance:g}).")
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= cal.CANTIDAD_MAXIMA:
        raise error("INVALID_ARGUMENTS", f"count es un entero de 1 a {cal.CANTIDAD_MAXIMA} (recibió {count!r}).")
    doc = sesion.doc
    op = OpCalibracionHolguras(doc.nuevo_id(), nombre_nuevo(doc, "Calibración de holguras", OpCalibracionHolguras),
                               diametro=texto_expr(diameter), holgura_inicial=texto_expr(start_clearance),
                               paso=texto_expr(step), cantidad=count, espesor=texto_expr(thickness), etiquetas=labels)
    resultado = _agregar(sesion, op)
    if doc.resultado(op.id).estado != "error":          # con error la transacción lo informa y deshace al salir
        ctx = Contexto(doc.parametros.valores())
        resultado["clearances"] = cal.holguras(ctx.evaluar(op.p["holgura_inicial"]), ctx.evaluar(op.p["paso"]), count)
    return resultado
