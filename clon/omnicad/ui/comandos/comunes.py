# -*- coding: utf-8 -*-
"""Campos y conversiones que comparten varios comandos (operación booleana, perfiles, objetivos)."""
from ...timeline.operaciones import OPERACIONES_CUERPO
from ...timeline.parametros import LONGITUD
from ..comando import ErrorComando, Opciones, Seleccion, hits

OPCIONES_OPERACION = {"unir": ("Unir", "op_unir"), "cortar": ("Cortar", "op_cortar"),
                      "intersecar": ("Intersecar", "op_intersecar"), "nuevo": ("Nuevo cuerpo", "op_nuevo")}
assert set(OPCIONES_OPERACION) == set(OPERACIONES_CUERPO)


def campo_operacion(defecto="nuevo"):
    return Opciones("operacion", "Operación", OPCIONES_OPERACION, defecto)


def campo_objetivos():
    """«Objetos para cortar» de Fusion: vacío = automático (los cuerpos que toca)."""
    return Seleccion("objetivos", "Objetos", {"cuerpo"}, minimo=0, maximo=None,
                     visible_si=lambda v: v.get("operacion") != "nuevo",
                     ayuda="Cuerpos afectados. Sin selección: los que toca la herramienta.")


def objetivos(v):
    return [h["ref"]["cuerpo"] for h in v.get("objetivos") or [] if h["ref"].get("tipo") == "cuerpo"]


def perfiles_a_params(seleccion):
    """Selección de perfiles y caras planas → (boceto, perfiles, caras) como los guarda la operación."""
    boceto, perfiles, caras = "", [], []
    for h in seleccion or []:
        ref = h["ref"]
        if ref["tipo"] == "perfil":
            if boceto and ref["boceto"] != boceto:
                raise ErrorComando("Los perfiles tienen que ser de un mismo boceto.")
            boceto = ref["boceto"]
            perfiles.append({"firma": ref["firma"], "centroide": ref["centroide"]})
        elif ref["tipo"] == "cara":
            caras.append(ref)
    if not perfiles and not caras:
        raise ErrorComando("Seleccioná uno o más perfiles o caras planas.")
    return boceto, perfiles, caras


def perfiles_desde_op(op, estado):
    refs_lista = [{"tipo": "perfil", "boceto": op.p["boceto"], **r} for r in op.p.get("perfiles", [])]
    return hits(refs_lista + list(op.p.get("caras") or []), estado)


def objetivos_desde_op(op, estado):
    lista = op.p.get("objetivos") or ([op.p["objetivo"]] if op.p.get("objetivo") else [])
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in lista], estado)


def evaluar_o_cero(ctx, expr, tipo=LONGITUD):
    """Valor de una expresión del panel para ubicar manipuladores (0 si todavía no se puede evaluar)."""
    try:
        return float(ctx.evaluar(str(expr if expr not in (None, "") else "0"), tipo))
    except Exception:  # noqa: BLE001 — una expresión inválida deja el manipulador en 0
        return 0.0
