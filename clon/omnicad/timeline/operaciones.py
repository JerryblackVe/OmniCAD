# -*- coding: utf-8 -*-
"""
Operaciones (features) del timeline.

Equivalencias con Fusion 360 (informe_analisis.md §3.1, §3.3, §5):
  - Cada operación es un paso del timeline (Feature ↔ TimelineObject 1:1).
  - Patrón "objeto de entrada": cada operación es un objeto de DATOS serializable
    (lo que en Fusion es `createInput(...)`), y `ejecutar()` lo aplica al modelo
    (lo que en Fusion es `add(input)`).
  - `operacion` replica FeatureOperations: nuevo cuerpo / unir / cortar / intersecar.
  - Las primitivas (caja, cilindro, esfera, toroide) son operaciones del timeline,
    como BoxFeature… TorusFeature en Fusion.
"""
import copy

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import intercambio
from ..nucleo import referencias as refs
from . import entidades as ent
from ..nucleo.perfiles import buscar_por_firma, detectar
from ..restricciones import Boceto, resolver
from ..restricciones.boceto import ErrorBoceto, validar_valor_cota
from .parametros import ANGULO, LONGITUD, evaluar

OPERACIONES_CUERPO = {"nuevo": "Cuerpo nuevo", "unir": "Unir", "cortar": "Cortar", "intersecar": "Intersecar"}
OPERACIONES_COMBINAR = {"unir": "Unir", "cortar": "Cortar", "intersecar": "Intersecar"}


class ErrorOperacion(RuntimeError):
    pass


class ParametroMalFormado(ErrorOperacion):
    """Un parámetro del paso no tiene la forma esperada: texto donde va una referencia, None en una lista, un
    dict sin sus claves… `valor` es el objeto que llegó; `Operacion.calcular` lo busca en los parámetros del
    paso para nombrar el `campo` («pivote», «aristas[0]»)."""

    def __init__(self, valor, detalle, campo=""):
        self.valor, self.detalle, self.campo = valor, detalle, campo
        donde = f" «{campo}»" if campo else ""
        super().__init__(f"Parámetro mal formado{donde}: llegó {ent.describir_valor(valor)}; {detalle}")


def id_cuerpo(valor):
    """Id del cuerpo de un campo de cuerpos, que acepta las dos formas: el id (texto, p. ej. "op1.c1") o la
    referencia {"tipo": "cuerpo", "cuerpo": "op1.c1"} (la de los campos de caras). Otra cosa: ParametroMalFormado."""
    if isinstance(valor, str):
        return valor
    if isinstance(valor, dict) and valor.get("tipo") == "cuerpo" and isinstance(valor.get("cuerpo"), str):
        return valor["cuerpo"]
    raise ParametroMalFormado(valor, 'se esperaba un cuerpo: su id (texto, p. ej. "op1.c1") o '
                                     '{"tipo": "cuerpo", "cuerpo": "op1.c1"}')


# ---------------------------------------------------------------- estado del modelo
class Cuerpo:
    """Cuerpo del modelo. `tipo`: "solido" | "superficie" | "malla" (como los cuerpos de Fusion).
    `apariencia` (color RGB 0..1) y `material` (nombre de la biblioteca) los fijan las operaciones
    Aspecto y Material físico; `componente` agrupa cuerpos (ENSAMBLAR › Nuevo componente)."""

    def __init__(self, id, nombre, forma, op_id, tipo="solido", apariencia=None, material=None, componente="",
                 origen=()):
        self.id, self.nombre, self.forma, self.op_id = id, nombre, forma, op_id
        self.tipo, self.apariencia, self.material, self.componente = tipo, apariencia, material, componente
        self.origen = tuple(origen)     # ids de los cuerpos de los que es copia, el más cercano primero (solo memoria)

    def copia(self):
        return Cuerpo(self.id, self.nombre, self.forma, self.op_id, self.tipo, self.apariencia, self.material,
                      self.componente, self.origen)


HEREDABLES = ("apariencia", "acabado", "material")     # propiedades que una copia toma de su original


def atributos_copia(c):
    """Atributos para `EstadoModelo.nuevo_cuerpo` de una copia de `c` (simetría, patrón, mover › copiar…):
    hereda aspecto, material y componente, y recuerda de qué cuerpo sale."""
    return {"apariencia": c.apariencia, "material": c.material, "componente": c.componente,
            "origen": (c.id,) + tuple(getattr(c, "origen", ()))}


def propiedades_cuerpo(propiedades, cuerpo):
    """Propiedades del documento (`Documento.propiedades`) de `cuerpo`, con el aspecto, el acabado y el material
    que no tenga propios tomados del cuerpo del que es copia (como en Fusion, la copia se ve como el original)."""
    props = dict(propiedades.get(cuerpo.id) or {})
    for oid in getattr(cuerpo, "origen", ()):
        for k in HEREDABLES:
            if k not in props and k in (propiedades.get(oid) or {}):
                props[k] = propiedades[oid][k]
    return props


class BocetoResuelto:
    def __init__(self, op_id, nombre, boceto, plano, perfiles, solver):
        self.op_id, self.nombre, self.boceto, self.plano = op_id, nombre, boceto, plano
        self.perfiles, self.solver = perfiles, solver


class EstadoModelo:
    """Resultado acumulado del timeline hasta un paso: cuerpos y bocetos disponibles."""

    def __init__(self):
        self.cuerpos = {}
        self.bocetos = {}
        self.planos = {}           # planos de construcción: id de la operación → geo.Plano
        self.ejes = {}             # ejes de construcción: id → (punto, dirección unitaria, nombre)
        self.puntos = {}           # puntos de construcción: id → (punto, nombre)
        self.componentes = {}      # id → {"nombre", "padre", "matriz" 4x4, "fijo"} (ENSAMBLAR)
        self.uniones = {}          # id → datos de la unión (ENSAMBLAR › Unión)
        self.grupos_rigidos = []   # [[ids de componentes]] que se mueven juntos (ENSAMBLAR › Grupo rígido)
        self.lienzos = {}          # id → imagen sobre un plano (INSERTAR › Lienzo / Calcomanía)
        self.contador_cuerpos = 0

    def copia(self):
        e = EstadoModelo()
        e.cuerpos = {k: c.copia() for k, c in self.cuerpos.items()}
        e.bocetos = dict(self.bocetos)
        e.planos = dict(self.planos)
        e.ejes = dict(self.ejes)
        e.puntos = dict(self.puntos)
        e.componentes = {k: dict(v) for k, v in self.componentes.items()}
        e.uniones = dict(self.uniones)
        e.grupos_rigidos = [list(g) for g in self.grupos_rigidos]
        e.lienzos = dict(self.lienzos)
        e.contador_cuerpos = self.contador_cuerpos
        return e

    def nuevo_cuerpo(self, op_id, forma, tipo="solido", nombre=None, **atributos):
        self.contador_cuerpos += 1
        k = sum(1 for c in self.cuerpos.values() if c.op_id == op_id) + 1
        cid = f"{op_id}.c{k}"
        while cid in self.cuerpos:
            k += 1
            cid = f"{op_id}.c{k}"
        self.cuerpos[cid] = Cuerpo(cid, nombre or f"Cuerpo{self.contador_cuerpos}", forma, op_id, tipo, **atributos)
        return cid

    def cuerpo(self, cid):
        cid = id_cuerpo(cid)
        if cid not in self.cuerpos:
            raise ErrorOperacion(f"El cuerpo '{cid}' no existe en este punto del timeline.")
        return self.cuerpos[cid]


class _Lecturas(dict):
    """Los valores de los parámetros, anotando qué nombres se consultan (también los que no existen):
    el documento sabe así qué pasos recalcular cuando cambia un parámetro."""

    def __init__(self, valores, usados):
        super().__init__(valores)
        self._usados = usados

    def __contains__(self, nombre):
        self._usados.add(nombre)
        return super().__contains__(nombre)

    def __getitem__(self, nombre):
        self._usados.add(nombre)
        return super().__getitem__(nombre)


class Contexto:
    def __init__(self, valores_parametros):
        self.usados = set()       # nombres de parámetros que leyó la operación al ejecutarse
        self.valores = _Lecturas(valores_parametros, self.usados)
        self.avisos = []

    def evaluar(self, expr, tipo=LONGITUD):
        return evaluar(expr, tipo, self.valores)

    def aviso(self, texto):
        self.avisos.append(texto)


def aplicar_resultado(estado, ctx, op_id, herramienta, operacion, objetivo="", tipo="solido"):
    """Aplica una forma recién creada según FeatureOperations. `objetivo`: id de un cuerpo, lista de ids
    ("Objetos para cortar" de Fusion) o vacío = automático (los cuerpos sólidos que toca).
    Devuelve los ids de cuerpos afectados."""
    if geo.esta_vacia(herramienta):
        raise ErrorOperacion("La operación no generó geometría.")
    if operacion == "nuevo":
        sols = (geo.solidos(herramienta) if tipo == "solido" else []) or [herramienta]
        return [estado.nuevo_cuerpo(op_id, s, tipo) for s in sols]
    if operacion not in OPERACIONES_COMBINAR:
        raise ErrorOperacion(f"Operación desconocida: {operacion}")
    lista = list(objetivo) if isinstance(objetivo, (list, tuple)) else [objetivo] if objetivo else []
    if lista:
        objetivos = [estado.cuerpo(o) for o in lista]
    else:
        objetivos = [c for c in estado.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"]
        if operacion == "unir":
            objetivos = [c for c in objetivos if geo.se_tocan(c.forma, herramienta)]
    if not objetivos:
        if operacion == "unir":
            ctx.aviso("No tocó ningún cuerpo: se creó un cuerpo nuevo.")
            return [estado.nuevo_cuerpo(op_id, herramienta)]
        raise ErrorOperacion(f"No hay cuerpos sobre los que {OPERACIONES_COMBINAR[operacion].lower()}.")

    if operacion == "unir":
        resultado = herramienta
        for c in objetivos:
            resultado = geo.booleano(resultado, c.forma, "unir")
        principal = objetivos[0]
        principal.forma = resultado
        for c in objetivos[1:]:
            del estado.cuerpos[c.id]
        return [principal.id]

    afectados = []
    for c in objetivos:
        if not lista and not geo.se_tocan(c.forma, herramienta):
            continue
        if lista and operacion == "cortar" and not geo.se_tocan(c.forma, herramienta):
            ctx.aviso(f"La herramienta no toca a {c.nombre}: no le cortó nada.")
        nueva = geo.booleano(c.forma, herramienta, operacion)
        if geo.esta_vacia(nueva):
            del estado.cuerpos[c.id]
            ctx.aviso(f"{c.nombre} quedó vacío y se eliminó.")
        else:
            c.forma = nueva
        afectados.append(c.id)
    if not afectados:
        ctx.aviso("La herramienta no toca ningún cuerpo: no cambió nada.")
    return afectados


def _dependencia_de_cuerpo(cid):
    """Paso que creó el cuerpo (id o referencia de cuerpo); None si el valor no sirve."""
    if isinstance(cid, dict):
        cid = cid.get("cuerpo")
    return cid.split(".c")[0] if cid and isinstance(cid, str) else None


def _deps_objetivo(objetivo):
    """Pasos de los que dependen los cuerpos de un campo (un id, una referencia o una lista de ellos).
    Tolera valores mal formados: el error con el campo lo da la ejecución."""
    lista = list(objetivo) if isinstance(objetivo, (list, tuple)) else [objetivo]
    return {_dependencia_de_cuerpo(c) for c in lista} - {None}


# ---------------------------------------------------------------- operaciones
class Operacion:
    TIPO = ""
    ETIQUETA = ""
    ICONO = ""
    PARAMS = {}
    EXPRESIONES = ()   # claves de `p` que son expresiones (pueden usar parámetros)
    # Claves de `p` con una lista cerrada de valores → los valores válidos (tupla o dict valor → etiqueta). Es la
    # única fuente: `validar_opciones` la usa al calcular y describe_operation la muestra como «choices».
    OPCIONES = {}

    def __init__(self, id, nombre=None, suprimida=False, **params):
        self.id = id
        self.nombre = nombre or f"{self.ETIQUETA} {id}"
        self.suprimida = suprimida
        self.p = copy.deepcopy(self.PARAMS)
        self.p.update(params)
        # Pasos cuyos cuerpos modificó la última ejecución con objetivo "Automático": también son
        # dependencias (si no, se podría mover o borrar el cuerpo que esta operación corta o une).
        self._usados = set()

    def dependencias(self):
        return set(self._usados)

    def expresiones(self):
        return [self.p[k] for k in self.EXPRESIONES]

    def _registrar_usados(self, afectados):
        self._usados = {_dependencia_de_cuerpo(c) for c in afectados} - {self.id, None}

    def ejecutar(self, estado, ctx):
        raise NotImplementedError

    def revisar_parametros(self):
        """Revisión común de la forma: un parámetro cuyo valor por defecto es una lista (o un dict) tiene que
        serlo; None tampoco vale (las recetas reales nunca lo guardan así)."""
        for k, defecto in self.PARAMS.items():
            v = self.p.get(k, defecto)
            if isinstance(defecto, list) and not isinstance(v, (list, tuple)):
                raise ParametroMalFormado(v, "tiene que ser una lista", k)
            if isinstance(defecto, dict) and not isinstance(v, dict):
                raise ParametroMalFormado(v, "tiene que ser un dict", k)

    def validar_opciones(self):
        """Cada clave de OPCIONES tiene que tener uno de sus valores válidos; si no, un error que nombra el campo y
        los valores. None solo vale si el valor por defecto también es None (campo opcional)."""
        for clave, validos in self.OPCIONES.items():
            valor = self.p.get(clave, self.PARAMS.get(clave))
            if valor is None and self.PARAMS.get(clave) is None:
                continue
            if valor not in list(validos):
                raise ErrorOperacion(f"Valor no válido para «{clave}»: llegó {ent.describir_valor(valor)}. Valores "
                                     f"válidos: {', '.join(map(str, validos))}.")

    def entero(self, clave, minimo=1):
        """El parámetro `clave` como entero: acepta un int, un float sin decimales o un texto de dígitos («3»).
        Otra cosa, o menos que `minimo`, es un ErrorOperacion que nombra el campo."""
        valor = self.p.get(clave, self.PARAMS.get(clave))
        n = None
        if isinstance(valor, (int, np.integer)) and not isinstance(valor, bool):
            n = int(valor)
        elif isinstance(valor, float) and valor.is_integer():
            n = int(valor)
        elif isinstance(valor, str):
            try:
                n = int(valor)
            except ValueError:
                pass
        if n is None or (minimo is not None and n < minimo):
            al_menos = f" (al menos {minimo})" if minimo is not None else ""
            raise ErrorOperacion(f"«{clave}» tiene que ser un número entero{al_menos}: llegó "
                                 f"{ent.describir_valor(valor)}.")
        return n

    def calcular(self, estado, ctx):
        """`ejecutar` con la validación común (lo que usa el documento): revisa los contenedores y los valores de
        lista cerrada (OPCIONES) y, si una referencia o un id de cuerpo llega mal formado, el error nombra el campo
        del paso. No toca `self.p`."""
        self.revisar_parametros()
        self.validar_opciones()
        try:
            self.ejecutar(estado, ctx)
        except (ParametroMalFormado, ent.ReferenciaMalFormada) as e:
            if getattr(e, "campo", ""):
                raise
            raise ParametroMalFormado(e.valor, e.detalle, _ubicar(self.p, e.valor)) from e
        except ent.ErrorReferencia as e:     # como_plano, como_eje…: una referencia del tipo equivocado
            raise ErrorOperacion(str(e)) from e

    def copia(self):
        return operacion_desde_dict(self.a_dict())

    def a_dict(self):
        return {"tipo": self.TIPO, "id": self.id, "nombre": self.nombre, "suprimida": self.suprimida,
                "params": copy.deepcopy(self.p)}


def _ubicar(p, valor):
    """Campo de `p` que guarda `valor` (el MISMO objeto): «clave», «clave[i]» o «clave[i].sub»; "" si no está.
    Un None, booleano o número puede estar en varios lados: se busca primero dentro de las listas y arriba
    solo si una única clave lo tiene."""
    escalar = valor is None or isinstance(valor, (bool, int, float))
    arriba = [k for k, v in p.items() if v is valor]
    if arriba and not escalar:
        return arriba[0]
    for k, v in p.items():
        if not isinstance(v, (list, tuple)):
            continue
        for i, x in enumerate(v):
            if x is valor:
                return f"{k}[{i}]"
            if isinstance(x, dict):
                sub = next((s for s, y in x.items() if y is valor), None)
                if sub is not None:
                    return f"{k}[{i}].{sub}"
    return arriba[0] if len(arriba) == 1 else ""


def _plano_de_cara_asociada(cara, estado):
    """Plano de la cara (referencia persistente, como la de los empalmes) recalculado en ESTE estado."""
    ent.validar(cara)
    cuerpo = estado.cuerpos.get(cara.get("cuerpo"))
    if cuerpo is None:
        raise ErrorOperacion(f"El cuerpo de la cara donde está el boceto («{cara.get('cuerpo')}») ya no existe "
                             "en este punto del timeline.")
    sub = refs.resolver(cuerpo.forma, cara)
    if sub is None:
        raise ErrorOperacion(f"El boceto perdió la cara de {cuerpo.nombre} donde estaba apoyado: la geometría "
                             "cambió demasiado. Deshacé el cambio o volvé a crear el boceto sobre la cara.")
    plano = geo.plano_de_cara(sub)
    if plano is None:
        raise ErrorOperacion(f"La cara de {cuerpo.nombre} donde está el boceto dejó de ser plana.")
    return plano


def resolver_plano(ref, marco, estado, cara=None):
    """Plano de referencia: de origen ("XY", "XZ", "YZ"), una cara ("cara") o un plano de construcción del
    timeline (id de su operación). Con `cara` (referencia persistente) el plano sigue a la cara en cada
    recálculo, como en Fusion; sin ella (proyectos viejos) se usa el `marco` congelado al crear."""
    if not isinstance(ref, str):
        raise ParametroMalFormado(ref, 'se esperaba el plano como texto: "XY", "XZ", "YZ", "cara" o el id de un '
                                       'plano de construcción (p. ej. "op3")')
    if ref in geo.Plano.DEFINICIONES:
        return geo.Plano(ref)
    if ref == "cara":
        if cara:
            return _plano_de_cara_asociada(cara, estado)
        if not marco:
            raise ErrorOperacion("Falta la definición del plano de la cara.")
        return geo.Plano.desde_marco(marco["origen"], marco["normal"], marco["u"])
    if ref not in estado.planos:
        raise ErrorOperacion("El plano de construcción de referencia no está disponible "
                             "(¿borrado, suprimido o después del marcador?).")
    return estado.planos[ref]


def _es_ref_operacion(ref):
    return bool(ref) and isinstance(ref, str) and ref not in geo.Plano.DEFINICIONES and ref != "cara"


class OpPlano(Operacion):
    """Plano de construcción (CONSTRUIR de Fusion): de desfase, en ángulo, tangente, medio, por dos
    aristas, por tres puntos, perpendicular o en ruta (`tipo`, ver ops_construir.TIPOS_PLANO). Las
    referencias van en `refs`; los proyectos viejos usan `base`/`marco` (plano de desfase)."""
    TIPO, ETIQUETA, ICONO = "plano", "Plano", "▱"
    PARAMS = {"tipo": "desfase", "base": "XY", "marco": None, "distancia": "10 mm", "refs": [], "angulo": "0 deg",
              "posicion": "0.5"}
    EXPRESIONES = ("distancia", "angulo", "posicion")

    def dependencias(self):
        deps = super().dependencias()
        if self.p.get("refs"):
            return deps | ent.dependencias_de(self.p["refs"]) - {self.id}
        if _es_ref_operacion(self.p["base"]):
            deps.add(self.p["base"])
        return deps

    def ejecutar(self, estado, ctx):
        if self.p.get("refs"):
            from .ops_construir import calcular_plano
            plano = calcular_plano(self.p, [_resolver(r, estado) for r in self.p["refs"]], ctx)
            plano.nombre = self.nombre
            estado.planos[self.id] = plano
            return
        base = resolver_plano(self.p["base"], self.p["marco"], estado)
        estado.planos[self.id] = base.desplazado(ctx.evaluar(self.p["distancia"]), self.nombre)


class OpBoceto(Operacion):
    """Crear boceto de Fusion: curvas 2D con restricciones y cotas sobre un plano de origen, una cara plana o
    un plano de construcción. Sus perfiles cerrados alimentan Extruir, Revolución y los demás. Sobre una cara
    queda asociado a ella: si un parámetro la mueve o la gira, el boceto la sigue; si se pierde, el paso da error."""
    TIPO, ETIQUETA, ICONO = "boceto", "Boceto", "✎"
    # plano: "XY" | "XZ" | "YZ" | "cara" (con `cara` y `marco`) | id de un plano de construcción.
    # cara: referencia persistente a la cara (nucleo.referencias); `marco` queda de respaldo y es lo único que
    # tienen los proyectos viejos (boceto con marco congelado).
    # desplazamiento: se conserva por compatibilidad con los proyectos anteriores (bocetos desfasados).
    PARAMS = {"plano": "XY", "desplazamiento": "0", "marco": None, "cara": None}
    EXPRESIONES = ("desplazamiento",)

    def __init__(self, id, nombre=None, suprimida=False, boceto=None, **params):
        super().__init__(id, nombre, suprimida, **params)
        self.boceto = boceto if boceto is not None else Boceto()

    def valores_cotas(self, ctx):
        return {c.id: ctx.evaluar(c.expresion, ANGULO if c.tipo == "angulo" else LONGITUD)
                for c in self.boceto.cotas.values()}

    def expresiones(self):
        return super().expresiones() + [c.expresion for c in self.boceto.cotas.values()]

    def dependencias(self):
        deps = super().dependencias()
        if _es_ref_operacion(self.p["plano"]):
            deps.add(self.p["plano"])
        if self.p["plano"] == "cara":
            deps |= ent.dependencias_de(self.p.get("cara"))
        return deps

    def plano(self, estado, ctx):
        base = resolver_plano(self.p["plano"], self.p.get("marco"), estado, self.p.get("cara"))
        d = ctx.evaluar(self.p["desplazamiento"])
        return base.desplazado(d) if d else base

    def ejecutar(self, estado, ctx):
        plano = self.plano(estado, ctx)
        # Se resuelve una COPIA: el boceto guardado no se toca. Si un parámetro deja el boceto en
        # conflicto, al volver a un valor válido se parte otra vez de la geometría original.
        boceto = self.boceto.copia()
        valores = self.valores_cotas(ctx)
        for c in self.boceto.cotas.values():           # una cota manejada por parámetro puede quedar fuera de rango
            try:
                validar_valor_cota(c.tipo, valores[c.id])
            except ErrorBoceto as e:                   # aviso y no error: los proyectos viejos abren igual
                ctx.aviso(f"{self.nombre}: {e}")
        res = resolver(boceto, valores)
        if not res.ok:
            ctx.aviso(res.descripcion())
        perfiles = detectar(boceto.geometria(), plano)
        estado.bocetos[self.id] = BocetoResuelto(self.id, self.nombre, boceto, plano, perfiles, res)

    def a_dict(self):
        d = super().a_dict()
        d["boceto"] = self.boceto.a_dict()
        return d


def _exigir_tipos(ref, tipos):
    """Con `tipos` (p. ej. ("cara",)), una referencia bien formada de otro tipo es un ParametroMalFormado: sin esto,
    un cuerpo en un campo de caras llega al núcleo y OCP falla con un TypeError sin nombre de campo."""
    if tipos and ref["tipo"] not in tipos:
        raise ParametroMalFormado(ref, f"se esperaba una referencia de tipo {' o '.join(tipos)}, no «{ref['tipo']}» "
                                       f"(p. ej. {ent._EJEMPLOS[tipos[0]]})")


def _resolver(ref, estado, tipos=()):
    try:
        e = ent.resolver(ref, estado)
    except ent.ReferenciaMalFormada as e:
        raise ParametroMalFormado(e.valor, e.detalle) from e
    except ent.ErrorReferencia as e:
        raise ErrorOperacion(str(e)) from e
    _exigir_tipos(ref, tipos)
    return e


def _resolver_todas(lista, estado, tipos=()):
    try:
        salida = ent.resolver_todas(lista, estado)
    except ent.ReferenciaMalFormada as e:
        raise ParametroMalFormado(e.valor, e.detalle) from e
    except ent.ErrorReferencia as e:
        raise ErrorOperacion(str(e)) from e
    for ref in lista or []:
        _exigir_tipos(ref, tipos)
    return salida


def _caja_todo(estado):
    """Caja envolvente de todos los cuerpos sólidos (extensión "Todo")."""
    cajas = [geo.caja_envolvente(c.forma) for c in estado.cuerpos.values() if getattr(c, "tipo", "solido") != "malla"]
    cajas = [c for c in cajas if c]
    if not cajas:
        raise ErrorOperacion("La extensión «Todo» necesita cuerpos para atravesar.")
    return (tuple(min(c[0][i] for c in cajas) for i in range(3)), tuple(max(c[1][i] for c in cajas) for i in range(3)))


def _kernel_crear():
    try:
        from ..nucleo import solidos_crear
        return solidos_crear
    except ImportError:
        return None


class _OpConPerfiles(Operacion):
    """Base de extrusión y revolución: perfiles de un boceto (por firma) y/o caras planas (`caras`)."""

    def dependencias(self):
        deps = super().dependencias()
        if self.p.get("boceto") and isinstance(self.p["boceto"], str):
            deps.add(self.p["boceto"])
        deps |= _deps_objetivo(self.p.get("objetivo")) | _deps_objetivo(self.p.get("objetivos"))
        deps |= ent.dependencias_de(self.p.get("caras"), self.p.get("hasta"), self.p.get("inicio_objeto"),
                                    self.p.get("eje_ref"), self.p.get("hasta2"), self.p.get("curvas"))
        return deps - {self.id}

    def _caras(self, estado):
        """(plano, caras): los perfiles elegidos y las caras planas elegidas, todos coplanares."""
        caras, plano = [], None
        if self.p.get("boceto") is not None and not isinstance(self.p["boceto"], str):    # [] y {} también
            raise ParametroMalFormado(self.p["boceto"], 'se esperaba el id del boceto (texto, p. ej. "op1")')
        if self.p.get("perfiles"):
            br = estado.bocetos.get(self.p["boceto"])
            if br is None:
                raise ErrorOperacion("El boceto de referencia no está disponible (¿borrado, suprimido o después del "
                                     "marcador?).")
            for ref in self.p["perfiles"]:
                detalle = ent.problema_perfil(ref)
                if detalle:
                    raise ParametroMalFormado(ref, detalle)
                perfil = buscar_por_firma(br.perfiles, ref["firma"], ref.get("centroide"))
                if perfil is None:
                    raise ErrorOperacion("Un perfil seleccionado ya no existe en el boceto (cambió su contorno).")
                caras.append(perfil.cara)
            plano = br.plano
        for e in _resolver_todas(self.p.get("caras"), estado):
            if e.plano is None:
                raise ErrorOperacion("Solo se pueden usar caras planas.")
            caras.append(e.forma)
            plano = plano or e.plano
        if not caras:
            raise ErrorOperacion("No hay perfiles ni caras seleccionados.")
        return plano, caras

    @staticmethod
    def referencia_perfil(perfil):
        return {"firma": sorted(perfil.firma), "centroide": list(perfil.centroide_uv)}

    def _objetivo(self):
        return self.p.get("objetivos") or self.p.get("objetivo") or ""


DIRECCIONES = {"un_lado": "Un lado", "dos_lados": "Dos lados", "simetrica": "Simétrica"}


class OpExtrusion(_OpConPerfiles):
    """Extruir de Fusion [SLD-EXTRUDE-SOLID]: tipo (normal o delgada), inicio (plano del perfil, desfase u
    objeto), dirección (un lado, dos lados, simétrica con media longitud o longitud total), extensión
    (distancia, al objeto o todo), ángulo de conicidad y operación (nuevo cuerpo, unir, cortar, intersecar)
    sobre los cuerpos automáticos o los elegidos en «Objetos para cortar»."""
    TIPO, ETIQUETA, ICONO = "extrusion", "Extrusión", "⬆"
    PARAMS = {"boceto": "", "perfiles": [], "caras": [], "tipo": "solida", "inicio": "plano", "desfase_inicio": "0 mm",
              "inicio_objeto": None, "direccion": "un_lado", "medida": "mitad", "extension": "distancia",
              "distancia": "10 mm", "hasta": None, "extension2": "distancia", "distancia2": "10 mm", "hasta2": None,
              "conicidad": "0 deg", "conicidad2": "0 deg", "espesor": "1 mm", "ubicacion": "lado1", "invertir": False,
              "hasta_modo": "cara", "desfase_hasta": "0 mm", "curvas": [],
              "simetrica": False, "operacion": "nuevo", "objetivo": "", "objetivos": []}
    EXPRESIONES = ("distancia", "distancia2", "desfase_inicio", "conicidad", "conicidad2", "espesor", "desfase_hasta")
    OPCIONES = {"tipo": ("solida", "delgada"), "inicio": ("plano", "desfase", "objeto"), "direccion": DIRECCIONES,
                "medida": ("mitad", "total"), "extension": ("distancia", "objeto", "todo"),
                "extension2": ("distancia", "objeto", "todo"), "hasta_modo": ("cara", "cuerpo", "a_traves"),
                "ubicacion": ("lado1", "lado2", "centro"), "operacion": OPERACIONES_CUERPO}

    def expresiones(self):
        return [self.p[k] for k in self.EXPRESIONES if k in self.p]

    def ejecutar(self, estado, ctx):
        p = self.p
        curvas = _resolver_todas(p.get("curvas"), estado) if p.get("tipo") == "delgada" else []
        if curvas and not p.get("perfiles") and not p.get("caras"):
            plano = next((e.plano for e in curvas if e.plano is not None), None)
            if plano is None:
                raise ErrorOperacion("Las curvas abiertas tienen que ser de un boceto.")
            caras = []
        else:
            plano, caras = self._caras(estado)
        n = -plano.normal if p.get("invertir") else plano.normal
        direccion = "simetrica" if p.get("simetrica") else p.get("direccion", "un_lado")
        medida = "total" if p.get("simetrica") else p.get("medida", "mitad")
        d1 = ctx.evaluar(p["distancia"])
        d2 = ctx.evaluar(p.get("distancia2", "0")) if direccion == "dos_lados" else None
        desfase = 0.0
        if p.get("inicio") == "desfase":
            desfase = ctx.evaluar(p.get("desfase_inicio", "0"))
        elif p.get("inicio") == "objeto":
            e = _resolver(p.get("inicio_objeto"), estado) if p.get("inicio_objeto") else None
            if e is None or e.plano is None:
                raise ErrorOperacion("Elegí una cara plana o un plano como inicio de la extrusión.")
            desfase = float((e.plano.origen - plano.origen) @ n)
        hasta = hasta2 = caja = None
        if p.get("extension") == "objeto":
            if not p.get("hasta"):
                raise ErrorOperacion("Elegí la cara, el plano o el cuerpo hasta donde llega la extrusión.")
            hasta = self._forma_objeto(_resolver(p["hasta"], estado))
        elif p.get("extension") == "todo":
            caja = _caja_todo(estado)
        if direccion == "dos_lados" and p.get("extension2") == "objeto" and p.get("hasta2"):
            raise ErrorOperacion("«Al objeto» en el lado 2 todavía no está disponible: usá una distancia.")
        delgado = None
        if p.get("tipo") == "delgada":
            delgado = {"espesor": ctx.evaluar(p["espesor"]), "ubicacion": p.get("ubicacion", "lado1")}
        conicidad = ctx.evaluar(p.get("conicidad", "0"), ANGULO)
        conicidad2 = ctx.evaluar(p.get("conicidad2", "0"), ANGULO)
        kernel = _kernel_crear()
        avanzada = delgado or abs(conicidad) > 1e-9 or abs(conicidad2) > 1e-9 or hasta is not None \
            or hasta2 is not None or caja is not None
        if kernel is not None and hasattr(kernel, "extruir_avanzado") and avanzada:
            if hasta is not None and direccion == "simetrica":
                raise ErrorOperacion("«Al objeto» no se combina con la dirección simétrica.")
            forma = kernel.extruir_avanzado(caras, n, inicio_desfase=desfase, direccion=direccion, distancia1=d1,
                                            distancia2=d2, conicidad1=conicidad, conicidad2=conicidad2,
                                            medida_simetrica=medida, delgado=delgado,
                                            aristas=[e.forma for e in curvas] or None, hasta=hasta,
                                            hasta_modo=p.get("hasta_modo", "cara"),
                                            hasta_desfase=ctx.evaluar(p.get("desfase_hasta", "0")), hasta_caja=caja)
        elif avanzada:
            raise ErrorOperacion("Esta opción de extrusión todavía no está disponible.")
        else:
            forma = _extrusion_basica(caras, n, d1, d2, direccion, medida, desfase)
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, p["operacion"], self._objetivo()))

    @staticmethod
    def _forma_objeto(e):
        if e.forma is not None:
            return e.forma
        if e.plano is not None:
            return geo.cara_de_plano(e.plano)
        raise ErrorOperacion("El objeto elegido no sirve como límite de la extrusión.")


def _extrusion_basica(caras, n, d1, d2, direccion, medida, desfase):
    geo.exigir_distancias_extrusion(direccion, d1, d2, medida)     # con el campo y el valor escritos
    if abs(desfase) > 1e-12:
        caras = [geo.trasladar(c, n * desfase) for c in caras]
    if direccion == "simetrica":
        return geo.extruir(caras, n, abs(d1) * (2 if medida == "mitad" else 1), simetrica=True)
    if direccion == "dos_lados":
        return geo.unir_todos([geo.extruir(caras, n, d1), geo.extruir(caras, -n, d2)])
    return geo.extruir(caras, n, d1)


class OpRevolucion(_OpConPerfiles):
    """Revolución de Fusion [SLD-REVOLVE-SOLID]: eje (línea, arista, eje de construcción o de origen),
    tipo de extensión (ángulo, completa), dirección (un lado, dos lados, simétrica) y operación."""
    TIPO, ETIQUETA, ICONO = "revolucion", "Revolución", "↻"
    PARAMS = {"boceto": "", "perfiles": [], "caras": [], "eje": "v", "eje_ref": None, "extension": "angulo",
              "angulo": "360 deg", "direccion": "un_lado", "angulo2": "90 deg", "invertir": False,
              "operacion": "nuevo", "objetivo": "", "objetivos": []}
    EXPRESIONES = ("angulo", "angulo2")
    OPCIONES = {"extension": ("angulo", "completa"), "direccion": DIRECCIONES, "operacion": OPERACIONES_CUERPO}

    def expresiones(self):
        return [self.p[k] for k in self.EXPRESIONES if k in self.p]

    def _eje(self, estado, plano):
        if self.p.get("eje_ref"):
            return ent.como_eje(_resolver(self.p["eje_ref"], estado))
        eje = self.p["eje"]
        br = estado.bocetos.get(self.p.get("boceto"))
        if eje in ("u", "v"):
            return plano.a_3d(0, 0), (plano.u if eje == "u" else plano.v)
        lid = int(eje)
        if br is None or lid not in br.boceto.curvas or br.boceto.curvas[lid].tipo != "linea":
            raise ErrorOperacion("La línea elegida como eje ya no existe en el boceto.")
        (u1, v1), (u2, v2) = br.boceto._extremos_linea(lid)
        punto = plano.a_3d(u1, v1)
        return punto, plano.a_3d(u2, v2) - punto

    def ejecutar(self, estado, ctx):
        plano, caras = self._caras(estado)
        punto, direccion = self._eje(estado, plano)
        direccion = np.asarray(direccion, float) * (-1 if self.p.get("invertir") else 1)
        a1 = 360.0 if self.p.get("extension") == "completa" else ctx.evaluar(self.p["angulo"], ANGULO)
        modo = self.p.get("direccion", "un_lado")
        if modo == "simetrica" and self.p.get("extension") != "completa":
            caras = [geo.rotar(c, punto, direccion, -a1 / 2) for c in caras]
            forma = geo.revolver(caras, punto, direccion, a1)
        elif modo == "dos_lados" and self.p.get("extension") != "completa":
            a2 = ctx.evaluar(self.p.get("angulo2", "0"), ANGULO)
            forma = geo.unir_todos([geo.revolver(caras, punto, direccion, a1),
                                    geo.revolver(caras, punto, -direccion, a2)])
        else:
            forma = geo.revolver(caras, punto, direccion, a1)
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, self.p["operacion"], self._objetivo()))


class OpPrimitiva(Operacion):
    """Caja, Cilindro, Esfera y Toroide de Fusion (CREAR): primitiva con sus medidas y posición (x, y, z) como
    cuerpo nuevo o unida, cortada o intersecada con los cuerpos existentes.

    Caja: (x, y, z) es la esquina mínima; con caja_centrada (lo que guarda create_box) (x, y) es el centro de la
    base y z la base. ancho = tamaño en X, largo = en Y, alto = en Z."""
    TIPO, ETIQUETA, ICONO = "primitiva", "Primitiva", "■"
    CAMPOS = {
        "caja": ["ancho", "largo", "alto"],
        "cilindro": ["radio", "alto"],
        "esfera": ["radio"],
        "toroide": ["radio_mayor", "radio_menor"],
    }
    ETIQUETAS = {"caja": "Caja", "cilindro": "Cilindro", "esfera": "Esfera", "toroide": "Toroide"}
    ICONOS = {"caja": "■", "cilindro": "◯", "esfera": "●", "toroide": "◎"}
    PARAMS = {"forma": "caja", "ancho": "20 mm", "largo": "20 mm", "alto": "20 mm", "radio": "10 mm",
              "radio_mayor": "20 mm", "radio_menor": "5 mm", "x": "0", "y": "0", "z": "0",
              "operacion": "nuevo", "objetivo": "", "caja_centrada": False}
    OPCIONES = {"forma": CAMPOS, "operacion": OPERACIONES_CUERPO}

    def __init__(self, id, nombre=None, suprimida=False, **params):
        forma = params.get("forma", "caja")
        if nombre is None:
            nombre = f"{self.ETIQUETAS.get(forma, 'Primitiva')} {id}"
        super().__init__(id, nombre, suprimida, **params)

    @property
    def icono(self):
        return self.ICONOS.get(self.p["forma"], "■")

    def dependencias(self):
        return super().dependencias() | _deps_objetivo(self.p.get("objetivo"))

    def expresiones(self):
        return [self.p[k] for k in self.CAMPOS.get(self.p["forma"], []) + ["x", "y", "z"]]

    def ejecutar(self, estado, ctx):
        v = {k: ctx.evaluar(self.p[k]) for k in self.CAMPOS[self.p["forma"]] + ["x", "y", "z"]}
        pos = (v["x"], v["y"], v["z"])
        f = self.p["forma"]
        if f == "caja":
            if self.p.get("caja_centrada"):         # create_box: (x, y) es el centro de la base
                pos = (v["x"] - v["ancho"] / 2, v["y"] - v["largo"] / 2, v["z"])
            forma = geo.caja(v["ancho"], v["largo"], v["alto"], pos)
        elif f == "cilindro":
            forma = geo.cilindro(v["radio"], v["alto"], pos)
        elif f == "esfera":
            forma = geo.esfera(v["radio"], pos)
        elif f == "toroide":
            forma = geo.toroide(v["radio_mayor"], v["radio_menor"], pos)
        else:
            raise ErrorOperacion(f"Primitiva desconocida: {f}")
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, self.p["operacion"], self.p["objetivo"]))


class OpCombinar(Operacion):
    """Equivalente a CombineFeature: cuerpo objetivo + herramientas + operación + mantener herramientas."""
    TIPO, ETIQUETA, ICONO = "combinar", "Combinar", "⊕"
    PARAMS = {"objetivo": "", "herramientas": [], "operacion": "unir", "mantener": False}
    OPCIONES = {"operacion": OPERACIONES_COMBINAR}

    def dependencias(self):
        return _deps_objetivo(self.p.get("objetivo")) | _deps_objetivo(self.p.get("herramientas"))

    def ejecutar(self, estado, ctx):
        if not self.p["objetivo"] or not self.p["herramientas"]:
            raise ErrorOperacion("Elegí un cuerpo objetivo y al menos una herramienta.")
        objetivo = estado.cuerpo(self.p["objetivo"])
        herramientas = [estado.cuerpo(h) for h in self.p["herramientas"]]
        if any(h.id == objetivo.id for h in herramientas):
            raise ErrorOperacion("El objetivo no puede ser también herramienta.")
        resultado = objetivo.forma
        for h in herramientas:
            if self.p["operacion"] == "cortar" and not geo.se_tocan(resultado, h.forma):
                ctx.aviso(f"{h.nombre} no toca a {objetivo.nombre}: no le cortó nada.")
            resultado = geo.booleano(resultado, h.forma, self.p["operacion"])
        if geo.esta_vacia(resultado):
            raise ErrorOperacion("El resultado quedó vacío (¿los cuerpos no se intersecan?).")
        objetivo.forma = resultado
        if not self.p["mantener"]:
            for h in herramientas:
                del estado.cuerpos[h.id]


class OpImportarSTEP(Operacion):
    """Importa un STEP como cuerpo(s). El contenido se embebe en la receta para que el proyecto sea autónomo.
    Con `estructura` (Archivo › Abrir) conserva lo que traiga el archivo: nombres de las piezas, colores y
    componentes; sin ella (recetas viejas e Insertar STEP) todo entra como cuerpos sueltos."""
    TIPO, ETIQUETA, ICONO = "importar_step", "Importar STEP", "⇩"
    PARAMS = {"archivo": "", "contenido": "", "estructura": False}

    def ejecutar(self, estado, ctx):
        if not self.p["contenido"]:
            raise ErrorOperacion("La importación no tiene contenido STEP.")
        if not self.p.get("estructura"):
            aplicar_resultado(estado, ctx, self.id, intercambio.leer_step_texto(self.p["contenido"]), "nuevo")
            return
        datos = intercambio.leer_step_estructura_texto(self.p["contenido"])
        ids = {}
        for c in datos["componentes"]:
            ids[c["id"]] = f"{self.id}.{c['id']}"
            estado.componentes[ids[c["id"]]] = {"nombre": c["nombre"], "padre": ids.get(c["padre"], ""),
                                                "fijo": False, "matriz": np.identity(4).tolist()}
        for c in datos["cuerpos"]:
            estado.nuevo_cuerpo(self.id, c["forma"], c["tipo"], nombre=c["nombre"] or None,
                                apariencia=list(c["color"]) if c["color"] else None,
                                componente=ids.get(c["componente"], ""))


class OpOperacionBase(Operacion):
    """Crear operación base de Fusion [SLD-CREATE-BASE-FEATURE]: los cuerpos quedan guardados tal cual (B-rep
    dentro de la receta) y dejan de depender de los pasos anteriores. Si el cuerpo original sigue existiendo
    se reemplaza con la copia congelada (mismo id); si no, se agrega.

    `cuerpos`: lista de copias congeladas {"id", "nombre", "tipo" ("solido"|"superficie"), "apariencia",
    "brep" (texto B-rep de OpenCascade)}. Por run_operation alcanza con los ids o nombres de los cuerpos
    (["op1.c1"]): se congelan en ese momento. Las mallas no entran."""
    TIPO, ETIQUETA, ICONO = "operacion_base", "Operación base", "▣"
    PARAMS = {"cuerpos": []}

    @classmethod
    def desde_cuerpos(cls, op_id, cuerpos):
        datos = [{"id": c.id, "nombre": c.nombre, "tipo": getattr(c, "tipo", "solido"), "apariencia": c.apariencia,
                  "brep": intercambio.brep_a_texto(c.forma)} for c in cuerpos if getattr(c, "tipo", "solido") != "malla"]
        if not datos:
            raise ErrorOperacion("Elegí cuerpos sólidos o de superficie.")
        return cls(op_id, cuerpos=datos)

    def ejecutar(self, estado, ctx):
        for d in self.p["cuerpos"]:
            if not isinstance(d, dict) or not isinstance(d.get("id"), str) or not isinstance(d.get("brep"), str):
                raise ParametroMalFormado(d, 'se esperaba un cuerpo congelado: {"id": "op1.c1", "brep": "…", …} (lo '
                                             'arma Crear operación base, no se escribe a mano)')
            forma = intercambio.forma_de_texto(d["brep"])
            if d["id"] in estado.cuerpos:
                estado.cuerpos[d["id"]].forma = forma
            else:
                estado.nuevo_cuerpo(self.id, forma, d.get("tipo", "solido"), nombre=d.get("nombre"),
                                    apariencia=d.get("apariencia"))


TIPOS_OPERACION = {c.TIPO: c for c in (OpBoceto, OpExtrusion, OpRevolucion, OpPrimitiva, OpCombinar, OpImportarSTEP,
                                       OpPlano, OpOperacionBase)}


def registrar_operacion(*clases):
    """Los módulos `ops_*` registran sus operaciones acá para que las recetas las puedan cargar."""
    for c in clases:
        TIPOS_OPERACION[c.TIPO] = c
    return clases


def operacion_desde_dict(d):
    clase = TIPOS_OPERACION.get(d["tipo"])
    if clase is None:
        raise ErrorOperacion(f"Tipo de operación desconocido: {d['tipo']}")
    params = copy.deepcopy(d.get("params", {}))
    if clase is OpBoceto:
        return OpBoceto(d["id"], d.get("nombre"), d.get("suprimida", False),
                        boceto=Boceto.desde_dict(d.get("boceto", {})), **params)
    return clase(d["id"], d.get("nombre"), d.get("suprimida", False), **params)


# Operaciones de los otros módulos (se registran al importarse; van al final por el import circular).
from . import (ops_chapa, ops_construir, ops_ensamblar, ops_fijacion, ops_insertar, ops_malla,  # noqa: E402,F401
               ops_modificar, ops_solido, ops_superficie)
