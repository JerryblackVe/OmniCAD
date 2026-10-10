# -*- coding: utf-8 -*-
"""
Herramientas del grupo "solido" para transmisiones: engranaje de evolvente (recto o helicoidal), par de engranajes
que engranan (con su ensamblaje: componentes, uniones de revolución y vínculo de movimiento), cremallera, rueda de
cadena (ISO 606), eje escalonado (asistente de ejes) y el cálculo de medidas sin modelar (`gear_info`).

Cada una agrega UN paso del timeline (`engranaje` o `eje_escalonado`, editables con edit_feature usando las claves
de get_timeline) y devuelve lo de las demás de "solido" (`feature`, `bodies_created`…) más las medidas calculadas.
La posición: `plane` (XY, XZ, YZ o un plano de construcción) y `center` = [x, y] sobre ese plano; el eje del
engranaje o del eje escalonado sigue la normal del plano (en XY, +Z). Unidades: mm y grados.
"""
from typing import Literal

from ..nucleo import engranajes as en
from ..nucleo import geometria as geo
from ..timeline.operaciones import Contexto
from ..timeline.ops_engranaje import PERSONALIZADA, OpEje, OpEngranaje, agregar_ensamblaje
from . import herramientas_modificar  # noqa: F401  (antes: el grupo «solido» lista primero empalmes, vaciado…)
from .errores import error
from .herramientas_boceto import nombre_nuevo, referencia_plano, texto_expr
from .herramientas_solido import OPERACIONES, Cuerpos, Operacion, _agregar, _numero_positivo, _objetivos
from .registro import Expr, herramienta

Cadena = Literal[tuple(en.CADENAS) + ("custom",)]
REMATES = {"none": "ninguno", "chamfer": "chaflan", "fillet": "empalme"}
_CLAVES_TRAMO = {"diameter": "diametro", "length": "largo", "start": "inicio", "start_size": "medida_inicio",
                 "end": "fin", "end_size": "medida_fin"}


def _r(x):
    return None if x is None else round(float(x), 4) + 0.0


def _entero_expr(valor):
    """Cantidad de dientes como expresión: 20 → «20» (no «20.0»), un texto queda como está."""
    if isinstance(valor, (int, float)) and not isinstance(valor, bool) and float(valor).is_integer():
        return str(int(valor))
    return texto_expr(valor)


def _ubicacion(sesion, plane, center):
    ref = referencia_plano(sesion, plane)
    c = [0, 0] if center is None else list(center)
    if len(c) != 2:
        raise error("INVALID_ARGUMENTS", f"center tiene que ser [x, y] sobre el plano (2 valores); llegaron {len(c)}.")
    return {"plano": {"tipo": "plano", "id": ref}, "x": texto_expr(c[0]), "y": texto_expr(c[1])}


def _ctx(sesion):
    try:
        return Contexto(sesion.doc.parametros.valores())
    except Exception:  # noqa: BLE001 — con parámetros rotos el paso mismo ya falló y lo informa
        return Contexto({})


def _medidas(g):
    """Medidas del núcleo (claves en español) → resultado de la API (claves en inglés)."""
    return {"module": _r(g["modulo"]), "teeth": g["dientes"], "transverse_module": _r(g["modulo_transversal"]),
            "transverse_pressure_angle": _r(g["angulo_presion_transversal"]),
            "pitch_diameter": _r(g["diametro_primitivo"]), "base_diameter": _r(g["diametro_base"]),
            "tip_diameter": _r(g["diametro_exterior"]), "root_diameter": _r(g["diametro_fondo"]),
            "circular_pitch": _r(g["paso"]), "base_pitch": _r(g["paso_base"]),
            "tooth_thickness": _r(g["espesor_primitivo"]), "tip_thickness": _r(g["espesor_exterior"])}


def _datos_par(d):
    return {"center_distance": _r(d["distancia_centros"]), "ratio": _r(d["relacion"]),
            "working_pressure_angle": _r(d["angulo_presion_trabajo"]), "contact_ratio": _r(d["recubrimiento"]),
            "tip_clearance": [_r(d["holgura_fondo1"]), _r(d["holgura_fondo2"])],
            "interference": bool(d["interferencia1"] or d["interferencia2"]),
            "undercut": [bool(d["socavado1"]), bool(d["socavado2"])], "gear2": _medidas(d["engranaje2"])}


def _sin_error(funcion, *args, **kw):
    try:
        return funcion(*args, **kw)
    except geo.ErrorGeometria as e:
        raise error("INVALID_ARGUMENTS", str(e)) from None


# ---------------------------------------------------------------- cálculo (sin modelar)
@herramienta("gear_info", "solido",
             "Calcula las medidas de un engranaje cilíndrico de evolvente sin modelarlo (ISO 21771, perfil de "
             "referencia ISO 53): diámetros primitivo, base, exterior y de fondo, paso, espesor del diente, dientes "
             "mínimos sin socavado (criterio estricto: 18 con 20°; el límite teórico, 17,1, va en "
             "min_teeth_theoretical) y desplazamiento mínimo. Con teeth2, también el par exterior: distancia entre "
             "centros, relación, ángulo de presión de trabajo, grado de recubrimiento e interferencia.")
def gear_info(sesion, module: float, teeth: int, pressure_angle: float = 20, helix_angle: float = 0,
              profile_shift: float = 0, clearance: float = 0.25, backlash: float = 0, teeth2: int | None = None,
              profile_shift2: float = 0):
    """
    module: módulo normal en mm (en un engranaje recto, el módulo).
    teeth: cantidad de dientes.
    pressure_angle: ángulo de presión en grados (20 es el normal de ISO 53).
    helix_angle: ángulo de hélice en grados (0 = recto; positivo = hélice a derechas).
    profile_shift: coeficiente de desplazamiento de perfil x (0 = sin desplazar).
    clearance: holgura de fondo como fracción del módulo (0.25 en ISO 53).
    backlash: juego circunferencial del par en el primitivo, en mm (cada rueda adelgaza la mitad).
    teeth2: dientes del segundo engranaje para calcular el par; vacío = solo este engranaje.
    profile_shift2: desplazamiento de perfil del segundo engranaje.
    """
    g = _sin_error(en.medidas_engranaje, module, teeth, pressure_angle, helix_angle, profile_shift, clearance, backlash)
    so = en.socavado(g["dientes"], pressure_angle, profile_shift, helix_angle)
    resultado = dict(_medidas(g), min_teeth_no_undercut=so["dientes_minimos"],
                     min_teeth_theoretical=_r(en.dientes_minimos_teorico(pressure_angle, helix_angle)),
                     min_profile_shift=_r(so["desplazamiento_minimo"]), undercut=bool(so["socavado"]))
    if teeth2 is not None:
        d = _sin_error(en.datos_par, module, teeth, teeth2, pressure_angle, profile_shift, profile_shift2, helix_angle,
                       clearance)
        resultado["pair"] = _datos_par(d)
    return resultado


# ---------------------------------------------------------------- engranajes
def _comunes(module, width, pressure_angle, helix_angle, clearance, backlash):
    _numero_positivo(module, "module")
    _numero_positivo(width, "width")
    return {"modulo": texto_expr(module), "ancho": texto_expr(width), "angulo_presion": texto_expr(pressure_angle),
            "helice": texto_expr(helix_angle), "holgura": texto_expr(clearance), "juego": texto_expr(backlash)}


def _crear(sesion, nombre, params):
    """(paso, informe, calculado): agrega el paso Engranaje; `calculado` es False si quedó con error (la transacción
    lo informa y deshace al salir de la herramienta)."""
    doc = sesion.doc
    tipo, par = params["tipo"], bool(params.get("par"))
    op = OpEngranaje(doc.nuevo_id(), nombre_nuevo(doc, nombre, OpEngranaje,
                                                  lambda o: o.p.get("tipo") == tipo and bool(o.p.get("par")) == par),
                     **params)
    resultado = _agregar(sesion, op)
    return op, resultado, doc.resultado(op.id).estado != "error"


@herramienta("create_gear", "solido",
             "Crea un engranaje cilíndrico de evolvente (perfil de referencia ISO 53), recto o, con helix_angle, "
             "helicoidal, como un paso del timeline (tipo «engranaje»; medidas como expresiones con parámetros). El eje "
             "sigue la normal del plano y el primer diente apunta al eje x del plano. Devuelve también sus diámetros "
             "(gear). Para dos que engranan, create_gear_pair.", modifica=True)
def create_gear(sesion, module: Expr, teeth: Expr, width: Expr = 10, pressure_angle: Expr = 20,
                helix_angle: Expr = 0, profile_shift: Expr = 0, clearance: Expr = 0.25, backlash: Expr = 0,
                bore: Expr = 0, rotation: Expr = 0, plane: str = "XY", center: list[Expr] | None = None):
    """
    module: módulo normal en mm (número o expresión).
    teeth: cantidad de dientes (entero, o expresión que dé un entero).
    width: ancho del engranaje a lo largo del eje, en mm.
    pressure_angle: ángulo de presión en grados (20 es el normal).
    helix_angle: ángulo de hélice en grados; 0 = recto, positivo = a derechas.
    profile_shift: coeficiente de desplazamiento de perfil x.
    clearance: holgura de fondo como fracción del módulo (0.25 en ISO 53).
    backlash: juego del par en el primitivo, en mm (este engranaje adelgaza la mitad).
    bore: diámetro del agujero central en mm; 0 = macizo.
    rotation: giro del engranaje alrededor de su eje, en grados.
    plane: plano donde se apoya: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
    center: [x, y] del centro sobre el plano, en mm; vacío = el origen del plano.
    """
    params = dict(_comunes(module, width, pressure_angle, helix_angle, clearance, backlash), tipo="engranaje",
                  dientes=_entero_expr(teeth), desplazamiento=texto_expr(profile_shift), agujero=texto_expr(bore),
                  giro=texto_expr(rotation), **_ubicacion(sesion, plane, center))
    op, resultado, calculado = _crear(sesion, "Engranaje", params)
    if not calculado:
        return resultado
    v = op.medidas(_ctx(sesion))
    resultado["gear"] = _medidas(en.medidas_engranaje(v["modulo"], v["dientes"], v["angulo_presion"], v["helice"],
                                                      v["desplazamiento"], v["holgura"], v["juego"]))
    return resultado


@herramienta("create_gear_pair", "solido",
             "Crea dos engranajes de evolvente que engranan, en UN paso del timeline: el segundo a la distancia entre "
             "centros de trabajo (m·(z1+z2)/2 sin desplazamientos), en la dirección dada y girado medio diente para "
             "que los dientes entren en los huecos (con hélice, el segundo es de la mano contraria). Con assembly "
             "(por defecto) agrega además, con las operaciones de ENSAMBLAR, un componente por engranaje, una unión "
             "de revolución «como está» en cada eje y el vínculo de movimiento con la relación de dientes (giran en "
             "sentidos contrarios): todo es un solo paso de deshacer.", modifica=True)
def create_gear_pair(sesion, module: Expr, teeth1: Expr, teeth2: Expr, width: Expr = 10,
                     pressure_angle: Expr = 20, helix_angle: Expr = 0, profile_shift1: Expr = 0,
                     profile_shift2: Expr = 0, clearance: Expr = 0.25, backlash: Expr = 0, bore1: Expr = 0,
                     bore2: Expr = 0, direction: Expr = 0, rotation: Expr = 0, plane: str = "XY",
                     center: list[Expr] | None = None, assembly: bool = True):
    """
    module: módulo normal en mm de los dos engranajes.
    teeth1: dientes del primer engranaje (el del centro).
    teeth2: dientes del segundo engranaje.
    width: ancho de los dos engranajes, en mm.
    pressure_angle: ángulo de presión en grados.
    helix_angle: ángulo de hélice del primero en grados (el segundo lleva el contrario); 0 = rectos.
    profile_shift1: desplazamiento de perfil x del primero.
    profile_shift2: desplazamiento de perfil x del segundo (con x1 + x2 ≠ 0 cambia la distancia entre centros).
    clearance: holgura de fondo como fracción del módulo.
    backlash: juego del par en el primitivo, en mm (cada engranaje adelgaza la mitad).
    bore1: diámetro del agujero central del primero en mm; 0 = macizo.
    bore2: diámetro del agujero central del segundo en mm; 0 = macizo.
    direction: dirección del centro del segundo vista desde el primero, en grados desde el eje x del plano.
    rotation: giro del primero alrededor de su eje, en grados (el segundo gira lo que le corresponde para engranar).
    plane: plano donde se apoyan: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
    center: [x, y] del centro del primero sobre el plano, en mm; vacío = el origen del plano.
    assembly: true para crear además los componentes, las uniones de revolución y el vínculo de movimiento.
    """
    params = dict(_comunes(module, width, pressure_angle, helix_angle, clearance, backlash), tipo="engranaje",
                  par=True, dientes=_entero_expr(teeth1), dientes2=_entero_expr(teeth2),
                  desplazamiento=texto_expr(profile_shift1), desplazamiento2=texto_expr(profile_shift2),
                  agujero=texto_expr(bore1), agujero2=texto_expr(bore2), direccion=texto_expr(direction),
                  giro=texto_expr(rotation), **_ubicacion(sesion, plane, center))
    op, resultado, calculado = _crear(sesion, "Par de engranajes", params)
    if not calculado:
        return resultado
    v = op.medidas(_ctx(sesion))
    d = en.datos_par(v["modulo"], v["dientes"], v["dientes2"], v["angulo_presion"], v["desplazamiento"],
                     v["desplazamiento2"], v["helice"], v["holgura"])
    resultado.update(_datos_par(d), gear1=_medidas(d["engranaje1"]))
    resultado["assembly"] = None
    if assembly:
        pasos = agregar_ensamblaje(sesion.doc, op.id)
        resultado["assembly"] = {"components": pasos["componentes"], "joints": pasos["uniones"],
                                 "motion_link": pasos["vinculo"]}
    return resultado


@herramienta("create_rack", "solido",
             "Crea una cremallera recta con el perfil de referencia ISO 53 (paso π·módulo, flancos rectos al ángulo "
             "de presión) como un paso del timeline. La línea primitiva va sobre el eje x del plano desde center, "
             "los dientes hacia +y del plano y el ancho por la normal; los extremos caen en el medio de un hueco.",
             modifica=True)
def create_rack(sesion, module: Expr, teeth: Expr, width: Expr = 10, height: Expr = 10,
                pressure_angle: Expr = 20, clearance: Expr = 0.25, backlash: Expr = 0, rotation: Expr = 0,
                plane: str = "XY", center: list[Expr] | None = None):
    """
    module: módulo en mm.
    teeth: cantidad de dientes (el largo es teeth × π × module).
    width: ancho a lo largo de la normal del plano, en mm.
    height: alto de la base a la línea primitiva, en mm (mayor que 1.25 × module).
    pressure_angle: ángulo de presión (de los flancos) en grados.
    clearance: holgura de fondo como fracción del módulo.
    backlash: juego en la línea primitiva, en mm (el diente adelgaza la mitad).
    rotation: giro alrededor de la normal del plano, en grados.
    plane: plano donde se apoya: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
    center: [x, y] del inicio de la línea primitiva sobre el plano, en mm; vacío = el origen del plano.
    """
    params = dict(_comunes(module, width, pressure_angle, 0, clearance, backlash), tipo="cremallera",
                  dientes=_entero_expr(teeth), alto=texto_expr(height), giro=texto_expr(rotation),
                  **_ubicacion(sesion, plane, center))
    op, resultado, calculado = _crear(sesion, "Cremallera", params)
    if not calculado:
        return resultado
    v = op.medidas(_ctx(sesion))
    resultado["rack"] = {"pitch": _r(3.141592653589793 * v["modulo"]),
                         "length": _r(3.141592653589793 * v["modulo"] * v["dientes"]),
                         "tooth_height": _r(v["modulo"] * (2 + v["holgura"]))}
    return resultado


@herramienta("create_sprocket", "solido",
             "Crea una rueda dentada para cadena de rodillos con la forma de diente de ISO 606 (hueco medio) como un "
             "paso del timeline. chain elige la cadena (05B…16B, 08A…16A = ANSI 40…80) o 'custom' con pitch y "
             "roller_diameter propios; sin width, el ancho del diente sale de la norma (0,93 o 0,95 × ancho interior "
             "de la cadena).", modifica=True)
def create_sprocket(sesion, teeth: Expr, chain: Cadena = "08B", pitch: Expr | None = None,
                    roller_diameter: Expr | None = None, width: Expr | None = None, bore: Expr = 0,
                    rotation: Expr = 0, plane: str = "XY", center: list[Expr] | None = None):
    """
    teeth: cantidad de dientes (6 o más).
    chain: designación ISO 606 de la cadena ("08B", "10A"…) o "custom".
    pitch: paso de la cadena en mm (solo con chain="custom").
    roller_diameter: diámetro del rodillo en mm (solo con chain="custom").
    width: ancho del diente en mm; vacío = el de ISO 606 para la cadena (obligatorio con "custom").
    bore: diámetro del agujero central en mm; 0 = macizo.
    rotation: giro alrededor del eje, en grados.
    plane: plano donde se apoya: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
    center: [x, y] del centro sobre el plano, en mm; vacío = el origen del plano.
    """
    propia = chain == "custom"
    if propia and (pitch is None or roller_diameter is None or width is None):
        raise error("INVALID_ARGUMENTS", "Con chain='custom' hacen falta pitch, roller_diameter y width.")
    if not propia and (pitch is not None or roller_diameter is not None):
        raise error("INVALID_ARGUMENTS", f"La cadena {chain} ya trae paso y rodillo: pitch y roller_diameter van solo "
                                         "con chain='custom'.")
    params = {"tipo": "rueda_cadena", "dientes": _entero_expr(teeth), "agujero": texto_expr(bore),
              "giro": texto_expr(rotation), "cadena": PERSONALIZADA if propia else chain}
    if propia:
        _numero_positivo(pitch, "pitch")
        _numero_positivo(roller_diameter, "roller_diameter")
        params.update(paso=texto_expr(pitch), rodillo=texto_expr(roller_diameter))
    if width is None:
        p, _d1, b1 = en.CADENAS[chain]
        width = round(en.ancho_diente_cadena(b1, p), 3)
    _numero_positivo(width, "width")
    params["ancho"] = texto_expr(width)
    params.update(_ubicacion(sesion, plane, center))
    op, resultado, calculado = _crear(sesion, "Rueda de cadena", params)
    if not calculado:
        return resultado
    v = op.medidas(_ctx(sesion))
    d = en.datos_rueda_cadena(v["paso"], v["rodillo"], v["dientes"])
    resultado["sprocket"] = {"pitch": _r(d["paso"]), "roller_diameter": _r(d["rodillo"]),
                             "pitch_diameter": _r(d["diametro_primitivo"]), "root_diameter": _r(d["diametro_fondo"]),
                             "tip_diameter_min": _r(d["diametro_exterior_min"]),
                             "tip_diameter_max": _r(d["diametro_exterior_max"]), "width": _r(v["ancho"])}
    return resultado


# ---------------------------------------------------------------- eje escalonado
def _tramo(i, s):
    if not isinstance(s, dict):
        raise error("INVALID_ARGUMENTS", f"segments[{i}] tiene que ser un objeto como "
                                         '{"diameter": 20, "length": 30, "start": "chamfer", "start_size": 1}.')
    sobran = [k for k in s if k not in _CLAVES_TRAMO]
    if sobran:
        raise error("INVALID_ARGUMENTS", f"segments[{i}] tiene claves desconocidas: {', '.join(sobran)}.",
                    f"Claves válidas: {', '.join(_CLAVES_TRAMO)}.")
    faltan = [k for k in ("diameter", "length") if k not in s]
    if faltan:
        raise error("INVALID_ARGUMENTS", f"A segments[{i}] le falta: {', '.join(faltan)}.")
    tramo = {}
    for k, v in s.items():
        if k in ("start", "end"):
            if v not in REMATES:
                raise error("INVALID_ARGUMENTS", f"segments[{i}].{k} tiene que ser none, chamfer o fillet; llegó {v!r}.")
            tramo[_CLAVES_TRAMO[k]] = REMATES[v]
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float, str)):
            raise error("INVALID_ARGUMENTS", f"segments[{i}].{k} tiene que ser un número (mm) o una expresión.")
        if k in ("diameter", "length"):
            _numero_positivo(v, f"segments[{i}].{k}")
        tramo[_CLAVES_TRAMO[k]] = texto_expr(v)
    for lado in ("start", "end"):
        if tramo.get(_CLAVES_TRAMO[lado], "ninguno") != "ninguno" and f"{lado}_size" not in s:
            raise error("INVALID_ARGUMENTS", f"segments[{i}] tiene {lado}={s[lado]!r} pero le falta {lado}_size.")
    return tramo


@herramienta("create_shaft", "solido",
             "Asistente de ejes: crea un eje escalonado de revolución a partir de una tabla de tramos (diámetro, largo "
             "y, en cada extremo, chaflán a 45° o empalme) como un paso del timeline (tipo «eje_escalonado»). El eje "
             "sale de center por la normal del plano (en XY, hacia +Z), con los tramos en orden. Un chaflán o empalme "
             "va sobre la esquina de ese tramo: convexa en la punta o en un escalón que baja, cóncava en uno que sube. "
             "operation cut hace un agujero escalonado.", modifica=True)
def create_shaft(sesion, segments: list[dict], plane: str = "XY", center: list[Expr] | None = None,
                 operation: Operacion = "new_body", target: Cuerpos | None = None):
    """
    segments: tramos en orden, cada uno {"diameter": mm, "length": mm, "start": "none"|"chamfer"|"fillet", "start_size": mm, "end": "none"|"chamfer"|"fillet", "end_size": mm}; diameter y length son obligatorios y todos aceptan expresiones.
    plane: plano de donde sale el eje: "XY", "XZ", "YZ" o el id/nombre de un plano de construcción.
    center: [x, y] del comienzo del eje sobre el plano, en mm; vacío = el origen del plano.
    operation: "new_body", "join", "cut" o "intersect".
    target: cuerpo(s) afectados por join, cut o intersect (id o nombre); vacío = los sólidos que toca.
    """
    if not segments:
        raise error("INVALID_ARGUMENTS", "segments necesita al menos un tramo con diameter y length.")
    tramos = [_tramo(i, s) for i, s in enumerate(segments)]
    doc = sesion.doc
    op = OpEje(doc.nuevo_id(), nombre_nuevo(doc, "Eje", OpEje), tramos=tramos, operacion=OPERACIONES[operation],
               objetivos=_objetivos(sesion, operation, target), **_ubicacion(sesion, plane, center))
    resultado = _agregar(sesion, op, operation != "new_body")
    if doc.resultado(op.id).estado == "error":
        return resultado                    # la transacción informa el error del paso y deja el documento como estaba
    numeros = op.tramos(_ctx(sesion))
    resultado["shaft"] = {"length": _r(sum(t["largo"] for t in numeros)),
                          "max_diameter": _r(max(t["diametro"] for t in numeros)),
                          "volume": _r(en.volumen_eje(numeros))}
    return resultado
