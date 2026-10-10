# -*- coding: utf-8 -*-
"""
SÓLIDO › CREAR › Engranaje y Eje como pasos del timeline (el núcleo está en `nucleo/engranajes.py`).

  - `OpEngranaje`: engranaje de evolvente recto o helicoidal (o un PAR que engrana), cremallera o rueda de cadena
    sobre un plano y un centro, con todas las medidas como expresiones. Equivale al complemento «Spur Gear» de
    Fusion y a PartDesign › Involute Gear / Sprocket de FreeCAD.
  - `agregar_ensamblaje`: después de un par, los dos componentes, una unión de revolución «como está» en el eje de
    cada engranaje y el vínculo de movimiento con la relación de dientes, con las operaciones de ENSAMBLAR que ya
    existen (`ops_ensamblar`): al accionar la unión del primero, el segundo gira en sentido contrario.
  - `OpEje`: asistente de ejes (PartDesign › Shaft Design Wizard de FreeCAD): eje escalonado de revolución con una
    tabla de tramos (diámetro, largo, chaflán o empalme en cada extremo).
"""
import numpy as np

from ..nucleo import engranajes as en
from ..nucleo import geometria as geo
from ..nucleo import referencias as refs
from . import entidades as ent
from .operaciones import (OPERACIONES_CUERPO, ErrorOperacion, Operacion, ParametroMalFormado, _deps_objetivo,
                          _resolver, aplicar_resultado, registrar_operacion)
from .ops_ensamblar import OpComponente, OpUnion, OpVinculoMovimiento
from .parametros import ANGULO, ESCALAR

TIPOS = {"engranaje": "Engranaje (recto o helicoidal)", "cremallera": "Cremallera", "rueda_cadena": "Rueda de cadena"}
PERSONALIZADA = "personalizada"
CADENAS = (PERSONALIZADA,) + tuple(en.CADENAS)


def _ubicacion(p, estado, ctx):
    """(plano, centro 3D) del paso: el plano elegido (XY si no hay) y el centro elegido (o el origen del plano)
    corrido x, y sobre los ejes del plano."""
    plano = ent.como_plano(_resolver(p["plano"], estado)) if p.get("plano") else geo.Plano("XY")
    centro = ent.como_punto(_resolver(p["centro"], estado)) if p.get("centro") else plano.origen
    centro = np.asarray(centro, float) + plano.u * ctx.evaluar(p.get("x", "0")) + plano.v * ctx.evaluar(p.get("y", "0"))
    return plano, centro


def _entero(ctx, expr, que):
    v = ctx.evaluar(expr, ESCALAR)
    if abs(v - round(v)) > 1e-9:
        raise ErrorOperacion(f"{que} tiene que ser un número entero; «{expr}» da {v:g}.")
    return int(round(v))


class OpEngranaje(Operacion):
    """Engranaje [CREAR › Engranaje; complemento «Spur Gear» de Fusion; PartDesign › Involute Gear y Sprocket de
    FreeCAD]: `tipo` engranaje de evolvente (recto, o helicoidal con `helice` ≠ 0), cremallera o rueda de cadena
    (ISO 606), sobre un plano (`plano`, XY si falta) y un punto (`centro`, el origen del plano si falta) corrido
    `x`, `y` sobre los ejes del plano; el eje del engranaje sigue la normal del plano.

    Engranaje: `modulo` (normal), `dientes`, `angulo_presion`, `ancho`, `helice` (β > 0 a derechas),
    `desplazamiento` (coeficiente x), `holgura` (c* de fondo), `juego` (juego del par en el primitivo, mm),
    `agujero` (Ø central, 0 = macizo) y `giro`. Con `par` crea también el segundo (`dientes2`, `desplazamiento2`,
    `agujero2`) a la distancia entre centros de trabajo, en la `direccion` dada, girado medio diente para que
    engranen y con la hélice contraria. Cremallera: `modulo`, `dientes`, `angulo_presion`, `ancho`, `alto` (de la
    base a la línea primitiva), `holgura`, `juego`. Rueda de cadena: `cadena` de ISO 606 (o «personalizada» con
    `paso` y `rodillo`), `dientes`, `ancho`, `agujero`."""
    TIPO, ETIQUETA, ICONO = "engranaje", "Engranaje", "✲"
    PARAMS = {"tipo": "engranaje", "plano": None, "centro": None, "x": "0 mm", "y": "0 mm", "modulo": "2 mm",
              "dientes": "20", "angulo_presion": "20 deg", "ancho": "10 mm", "helice": "0 deg", "desplazamiento": "0",
              "holgura": "0.25", "juego": "0 mm", "agujero": "0 mm", "giro": "0 deg", "par": False, "dientes2": "40",
              "desplazamiento2": "0", "agujero2": "0 mm", "direccion": "0 deg", "alto": "10 mm", "cadena": "08B",
              "paso": "12.7 mm", "rodillo": "8.51 mm"}
    EXPRESIONES = ("x", "y", "modulo", "dientes", "angulo_presion", "ancho", "helice", "desplazamiento", "holgura",
                   "juego", "agujero", "giro", "dientes2", "desplazamiento2", "agujero2", "direccion", "alto", "paso",
                   "rodillo")
    OPCIONES = {"tipo": TIPOS, "cadena": CADENAS}

    def dependencias(self):
        return (super().dependencias() | ent.dependencias_de(self.p.get("plano"), self.p.get("centro"))) - {self.id}

    def medidas(self, ctx):
        """Valores evaluados del paso (mm, grados, enteros) para el núcleo; también los usa el diálogo."""
        p = self.p
        L = lambda k: ctx.evaluar(p[k])  # noqa: E731
        A = lambda k: ctx.evaluar(p[k], ANGULO)  # noqa: E731
        E = lambda k: ctx.evaluar(p[k], ESCALAR)  # noqa: E731
        tipo = p.get("tipo", "engranaje")
        if tipo == "rueda_cadena":
            if p.get("cadena") == PERSONALIZADA:
                paso, rodillo = L("paso"), L("rodillo")
            else:
                paso, rodillo, _b1 = en.CADENAS[p["cadena"]]
            return {"paso": paso, "rodillo": rodillo, "dientes": _entero(ctx, p["dientes"], "La cantidad de dientes"),
                    "ancho": L("ancho"), "agujero": L("agujero"), "giro": A("giro")}
        v = {"modulo": L("modulo"), "dientes": _entero(ctx, p["dientes"], "La cantidad de dientes"),
             "angulo_presion": A("angulo_presion"), "ancho": L("ancho"), "holgura": E("holgura"), "juego": L("juego"),
             "giro": A("giro")}
        if tipo == "cremallera":
            v["alto"] = L("alto")
            return v
        v.update(helice=A("helice"), desplazamiento=E("desplazamiento"), agujero=L("agujero"))
        if p.get("par"):
            v.update(dientes2=_entero(ctx, p["dientes2"], "La cantidad de dientes del segundo engranaje"),
                     desplazamiento2=E("desplazamiento2"), agujero2=L("agujero2"), direccion=A("direccion"))
        return v

    def formas(self, ctx):
        """[(forma en posición canónica, nombre)] y los avisos: lo que el paso crea, antes de ubicarlo."""
        v, tipo, avisos = self.medidas(ctx), self.p.get("tipo", "engranaje"), []
        if tipo == "rueda_cadena":
            forma = en.rueda_cadena(v["paso"], v["rodillo"], v["dientes"], ancho=v["ancho"], agujero=v["agujero"])
            return [(_girar(forma, v["giro"]), f"Rueda de cadena z{v['dientes']}")], avisos
        if tipo == "cremallera":
            forma = en.cremallera(v["modulo"], v["dientes"], angulo_presion=v["angulo_presion"], ancho=v["ancho"],
                                  alto=v["alto"], holgura=v["holgura"], juego=v["juego"])
            return [(_girar(forma, v["giro"]), f"Cremallera m{v['modulo']:g}")], avisos
        comunes = {"angulo_presion": v["angulo_presion"], "ancho": v["ancho"], "helice": v["helice"],
                   "holgura": v["holgura"], "juego": v["juego"]}
        so = en.socavado(v["dientes"], v["angulo_presion"], v["desplazamiento"], v["helice"])
        if so["socavado"]:
            avisos.append(f"Con {v['dientes']} dientes y x = {v['desplazamiento']:g} el diente tallado quedaría socavado "
                          f"(x mínimo {so['desplazamiento_minimo']:.3g}; sin desplazamiento, al menos "
                          f"{so['dientes_minimos']} dientes): el modelo no representa el socavado.")
        if not self.p.get("par"):
            forma = en.engranaje(v["modulo"], v["dientes"], desplazamiento=v["desplazamiento"], agujero=v["agujero"],
                                 giro=v["giro"], **comunes)
            return [(forma, f"Engranaje z{v['dientes']}")], avisos
        par = en.par_engranajes(v["modulo"], v["dientes"], v["dientes2"], desplazamiento1=v["desplazamiento"],
                                desplazamiento2=v["desplazamiento2"], agujero1=v["agujero"], agujero2=v["agujero2"],
                                direccion=v["direccion"], giro=v["giro"], **comunes)
        for k in (1, 2):
            if par[f"interferencia{k}"]:
                avisos.append(f"Interferencia: la cabeza del engranaje {3 - k} entra bajo el círculo base del "
                              f"{k}; con dientes reales tallados haría falta desplazamiento de perfil.")
        if par["socavado2"]:
            avisos.append(f"El segundo engranaje ({v['dientes2']} dientes) quedaría socavado al tallarlo.")
        if par["recubrimiento"] < 1.1:
            avisos.append(f"El grado de recubrimiento es {par['recubrimiento']:.2f} (conviene ≥ 1,2).")
        return [(par["engranaje1"], f"Engranaje z{v['dientes']}"),
                (par["engranaje2"], f"Engranaje z{v['dientes2']}")], avisos

    def ejecutar(self, estado, ctx):
        plano, centro = _ubicacion(self.p, estado, ctx)
        formas, avisos = self.formas(ctx)
        for a in avisos:
            ctx.aviso(a)
        for forma, nombre in formas:
            estado.nuevo_cuerpo(self.id, en.colocar(forma, centro, plano.normal, plano.u), "solido", nombre=nombre)


def _girar(forma, grados):
    return geo.rotar(forma, (0, 0, 0), (0, 0, 1), grados) if abs(grados) > 1e-12 else forma


# ---------------------------------------------------------------- par: componentes, uniones y vínculo
def _cara_superior(forma, normal):
    """La cara plana de arriba del engranaje (normal = eje): su centro de contorno queda sobre el eje."""
    normal = np.asarray(normal, float)
    mejor, alto = None, -np.inf
    for cara in refs.subformas(forma, "cara"):
        f = refs.firma_cara(cara)
        if f["geom"] == "plano" and float(np.dot(f["normal"], normal)) > 0.999:
            h = float(np.dot(f["centro"], normal))
            if h > alto:
                mejor, alto = cara, h
    if mejor is None:
        raise ErrorOperacion("No se encontró la cara de arriba del engranaje para ubicar la unión.")
    return mejor


def agregar_ensamblaje(doc, op_id, un_paso=False):
    """Después de un paso Engranaje con «par»: crea los dos componentes, una unión «como está» de revolución en el
    eje de cada engranaje (contra la raíz: quedan donde están) y el vínculo de movimiento con la relación de dientes
    (factor dientes1 / dientes2, invertido: giran en sentidos contrarios). Son las operaciones de ENSAMBLAR de
    siempre, en pasos propios, editables. Con `un_paso` todo queda en el mismo paso de deshacer que el engranaje
    (el diálogo lo agrega primero). Devuelve {"componentes", "uniones", "vinculo"} con los ids de los pasos."""
    op = doc.operacion(op_id)
    if not isinstance(op, OpEngranaje) or op.p.get("tipo", "engranaje") != "engranaje" or not op.p.get("par"):
        raise ErrorOperacion("El ensamblaje automático es para un paso Engranaje con «Par de engranajes».")
    pila = list(doc._deshacer)
    estado = doc.estado_en(doc.indice(op_id) + 1)
    cuerpos = [c for c in estado.cuerpos.values() if c.op_id == op_id]
    if len(cuerpos) != 2:
        raise ErrorOperacion("El par de engranajes tiene que estar calculado (sin error) para ensamblarlo.")
    plano = ent.como_plano(ent.resolver(op.p["plano"], estado)) if op.p.get("plano") else geo.Plano("XY")
    origenes = [refs.referencia(c.id, _cara_superior(c.forma, plano.normal), c.forma) for c in cuerpos]
    comps, uniones = [], []
    for c in cuerpos:
        comp = OpComponente(doc.nuevo_id(), c.nombre, cuerpos=[c.id])
        doc.agregar(comp)
        comps.append(comp.id)
    for c, origen in zip(cuerpos, origenes, strict=True):
        union = OpUnion(doc.nuevo_id(), f"Giro {c.nombre}", tipo="revolucion", origen1=origen, origen2=None,
                        como_esta=True)
        doc.agregar(union)
        uniones.append(union.id)
    z1, z2 = op.p["dientes"], op.p["dientes2"]
    vinculo = OpVinculoMovimiento(doc.nuevo_id(), f"Engrane {cuerpos[0].nombre} – {cuerpos[1].nombre}",
                                  union1=uniones[0], union2=uniones[1], factor=f"({z1}) / ({z2})", invertir=True)
    doc.agregar(vinculo)
    if un_paso:
        doc._deshacer[:] = pila
    return {"componentes": comps, "uniones": uniones, "vinculo": vinculo.id}


# ---------------------------------------------------------------- eje escalonado
TRAMO = {"diametro": "20 mm", "largo": "30 mm", "inicio": "ninguno", "medida_inicio": "1 mm", "fin": "ninguno",
         "medida_fin": "1 mm"}
_CLAVES_TRAMO = tuple(TRAMO)


class OpEje(Operacion):
    """Eje escalonado [CREAR › Eje; asistente de ejes, PartDesign › Shaft Design Wizard de FreeCAD]: sólido de
    revolución armado con una tabla de tramos. Cada tramo de `tramos` es {"diametro", "largo", "inicio", "fin",
    "medida_inicio", "medida_fin"}: diámetro y largo (expresiones), y en cada extremo un remate "ninguno",
    "chaflan" (45°) o "empalme" con su medida. Sale del punto `centro` (el origen del plano si falta, corrido `x`,
    `y`) a lo largo de la normal del `plano`. Cuerpo nuevo, o unido, cortado (agujero escalonado) o intersecado."""
    TIPO, ETIQUETA, ICONO = "eje_escalonado", "Eje escalonado", "⊟"
    PARAMS = {"plano": None, "centro": None, "x": "0 mm", "y": "0 mm",
              "tramos": [dict(TRAMO, inicio="chaflan"), dict(TRAMO, diametro="30 mm", largo="20 mm"),
                         dict(TRAMO, diametro="16 mm", largo="25 mm", fin="chaflan")],
              "operacion": "nuevo", "objetivos": []}
    EXPRESIONES = ("x", "y")
    OPCIONES = {"operacion": OPERACIONES_CUERPO}

    def dependencias(self):
        return (super().dependencias() | ent.dependencias_de(self.p.get("plano"), self.p.get("centro"))
                | _deps_objetivo(self.p.get("objetivos"))) - {self.id}

    def expresiones(self):
        salida = super().expresiones()
        for t in self.p.get("tramos") or []:
            if isinstance(t, dict):
                salida += [t[k] for k in ("diametro", "largo", "medida_inicio", "medida_fin") if isinstance(t.get(k), str)]
        return salida

    def tramos(self, ctx):
        """La tabla evaluada (mm) para `nucleo.engranajes.eje_escalonado`."""
        salida = []
        for i, t in enumerate(self.p.get("tramos") or []):
            if not isinstance(t, dict):
                raise ParametroMalFormado(t, 'se esperaba un tramo como {"diametro": "20 mm", "largo": "30 mm"}',
                                          f"tramos[{i}]")
            sobran = [k for k in t if k not in _CLAVES_TRAMO]
            if sobran:
                raise ErrorOperacion(f"El tramo {i + 1} tiene claves desconocidas ({', '.join(map(str, sobran))}); "
                                     f"valen: {', '.join(_CLAVES_TRAMO)}.")
            d = dict(TRAMO, **t)
            for k in ("diametro", "largo", "medida_inicio", "medida_fin"):
                if isinstance(d[k], bool) or not isinstance(d[k], (str, int, float)):
                    raise ParametroMalFormado(d[k], 'se esperaba una medida (número o expresión como "20 mm")',
                                              f"tramos[{i}].{k}")
            fila = {"diametro": ctx.evaluar(d["diametro"]), "largo": ctx.evaluar(d["largo"])}
            for lado in ("inicio", "fin"):
                fila[lado] = d[lado]
                if d[lado] not in en.REMATES:
                    raise ErrorOperacion(f"Valor no válido para «tramos[{i}].{lado}»: llegó {ent.describir_valor(d[lado])}."
                                         f" Valores válidos: {', '.join(en.REMATES)}.")
                if d[lado] != "ninguno":
                    fila[f"medida_{lado}"] = ctx.evaluar(d[f"medida_{lado}"])
            salida.append(fila)
        if not salida:
            raise ErrorOperacion("El eje necesita al menos un tramo (diámetro y largo).")
        return salida

    def ejecutar(self, estado, ctx):
        plano, centro = _ubicacion(self.p, estado, ctx)
        tramos = self.tramos(ctx)
        forma = en.colocar(en.eje_escalonado(tramos), centro, plano.normal, plano.u)
        if self.p.get("operacion", "nuevo") == "nuevo":
            estado.nuevo_cuerpo(self.id, forma, "solido", nombre=f"Eje Ø{max(t['diametro'] for t in tramos):g}")
            return
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, self.p["operacion"],
                                                 self.p.get("objetivos") or ""))


registrar_operacion(OpEngranaje, OpEje)
