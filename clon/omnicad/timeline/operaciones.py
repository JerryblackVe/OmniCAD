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
import json
import math
import re

import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import intercambio
from ..nucleo import referencias as refs
from ..nucleo import revision as rv
from . import entidades as ent
from ..nucleo.perfiles import buscar_por_firma_tolerante, cara_sin_area, detectar_boceto
from ..restricciones import Boceto, resolver
from ..restricciones.boceto import ErrorBoceto, Texto, distancia_punto_recta, expresiones_de_texto, validar_valor_cota
from .parametros import (ANGULO, ESCALAR, LONGITUD, ErrorExpresion, ErrorMagnitud, acotar, evaluar, nombres_usados,
                         renombrar_en, renombrar_en_texto, texto_con_valores)

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


def _regla_plastico(estado, cuerpos=()):
    """Dict de la regla de plástico aplicable: la del componente de `cuerpos` y, sin cuerpos (cuerpo nuevo), la única
    regla asignada en el diseño (Fusion usa la del componente en el que se trabaja). None si no hay regla."""
    for cid in cuerpos:
        cuerpo = estado.cuerpos.get(id_cuerpo(cid))
        regla = (estado.componentes.get((cuerpo.componente if cuerpo else "") or "") or {}).get("regla_plastico")
        if regla:
            return regla
    if cuerpos:                    # el componente del cuerpo que se toca no tiene regla: no se toma la de otro
        return None
    asignadas = [c["regla_plastico"] for c in estado.componentes.values() if c.get("regla_plastico")]
    return asignadas[0] if len(asignadas) == 1 else None


def espesor_plastico(estado, cuerpos=(), por_defecto="1 mm"):
    """Espesor de pared de las herramientas de plástico: el de la regla del componente de `cuerpos` y, sin cuerpos
    (cuerpo nuevo), el de la única regla asignada en el diseño (Fusion usa la del componente en el que se trabaja).
    `por_defecto` (el de cada herramienta) si no hay regla."""
    regla = _regla_plastico(estado, cuerpos)
    return f"{regla['espesor']:g} mm" if regla else por_defecto


def angulo_desmoldeo_plastico(estado, cuerpos=()):
    """Ángulo de desmoldeo (Draft Angle) de la regla de plástico: como `espesor_plastico`, pero devuelve el ángulo
    en grados; 0 deg si no hay regla. Lo usan Nervio y Red al arrancar (Fusion: la regla da Draft Angle y lo usan
    Rib y Web)."""
    regla = _regla_plastico(estado, cuerpos)
    return f"{regla['angulo_desmoldeo']:g} deg" if regla else "0 deg"


def radio_nominal_plastico(estado, cuerpos=()):
    """Radio nominal (Nominal Radius) de la regla de plástico: como `espesor_plastico`, pero devuelve el radio en mm;
    0 mm si no hay regla. Lo usa la Red al arrancar (Fusion: la regla da Nominal Radius y lo usa Web)."""
    regla = _regla_plastico(estado, cuerpos)
    return f"{regla.get('radio_nominal', 0):g} mm" if regla else "0 mm"


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
    solver3d = None          # Resultado3D de la geometría 3D del boceto (None si no tiene)

    def __init__(self, op_id, nombre, boceto, plano, perfiles, solver):
        self.op_id, self.nombre, self.boceto, self.plano = op_id, nombre, boceto, plano
        self.perfiles, self.solver = perfiles, solver


TODAS = None     # lectura de un diccionario entero (se recorrió)


class _DictLeido(dict):
    """Diccionario del estado que anota qué claves lee un paso al calcularse (`TODAS` si lo recorrió): con eso el
    documento sabe si un paso posterior a una edición puede reusar su último resultado (memo por paso)."""

    def __init__(self, datos):
        super().__init__(datos)
        self.leidas = set()

    def _anotar(self, clave):
        if self.leidas is not TODAS:
            self.leidas.add(clave)

    def _todo(self):
        self.leidas = TODAS

    def __getitem__(self, clave):
        self._anotar(clave)
        return super().__getitem__(clave)

    def get(self, clave, defecto=None):
        self._anotar(clave)
        return super().get(clave, defecto)

    def __contains__(self, clave):
        self._anotar(clave)
        return super().__contains__(clave)

    def pop(self, clave, *defecto):
        self._anotar(clave)
        return super().pop(clave, *defecto)

    def setdefault(self, clave, defecto=None):
        self._anotar(clave)
        return super().setdefault(clave, defecto)

    def __iter__(self):
        self._todo()
        return super().__iter__()

    def __len__(self):
        self._todo()
        return super().__len__()

    def keys(self):
        self._todo()
        return super().keys()

    def values(self):
        self._todo()
        return super().values()

    def items(self):
        self._todo()
        return super().items()

    def copy(self):
        self._todo()
        return dict(super().items())

    def __eq__(self, otro):
        self._todo()
        return super().__eq__(otro)

    def __reversed__(self):
        self._todo()
        return super().__reversed__()

    def popitem(self):
        self._todo()
        return super().popitem()

    __hash__ = None


DICTS_ESTADO = ("cuerpos", "bocetos", "planos", "ejes", "puntos", "medidas", "componentes", "uniones", "lienzos", "herramientas")


class EstadoModelo:
    """Resultado acumulado del timeline hasta un paso: cuerpos y bocetos disponibles."""

    def __init__(self):
        self.cuerpos = {}
        self.bocetos = {}
        self.planos = {}           # planos de construcción: id de la operación → geo.Plano
        self.ejes = {}             # ejes de construcción: id → (punto, dirección unitaria, nombre)
        self.puntos = {}           # puntos de construcción: id → (punto, nombre)
        # cómo se dibuja un plano o eje de construcción: id → {"redimensionar", "limites"}, en (u0, v0, u1, v1) o (t0, t1);
        # sin `limites`, el tamaño que da la vista
        self.medidas = {}
        self.componentes = {}      # id → {"nombre", "padre", "matriz" 4x4, "fijo"} (ENSAMBLAR)
        self.uniones = {}          # id → datos de la unión (ENSAMBLAR › Unión)
        self.grupos_rigidos = []   # [[ids de componentes]] que se mueven juntos (ENSAMBLAR › Grupo rígido)
        self.lienzos = {}          # id → imagen sobre un plano (INSERTAR › Lienzo / Calcomanía)
        # id de paso → ((herramienta, operación, objetivo, tipo), …) que aplicó con `aplicar_resultado`: el patrón de
        # operaciones (OpPatron con objeto="operaciones") repite esa herramienta transformada.
        self.herramientas = {}
        # id de cuerpo → forma que tenía antes del último Recortar (Destrimar recupera sus límites; SUP-5)
        self.recortes = {}
        # unión 2 → unión 1 de cada vínculo de movimiento vigente (ASM-2: una sola por unión y sin ciclos)
        self.vinculos = {}
        self.contador_cuerpos = 0

    def copia(self):
        e = EstadoModelo()
        e.cuerpos = {k: c.copia() for k, c in self.cuerpos.items()}
        e.bocetos = dict(self.bocetos)
        e.planos = dict(self.planos)
        e.ejes = dict(self.ejes)
        e.puntos = dict(self.puntos)
        e.medidas = dict(self.medidas)
        e.componentes = {k: dict(v) for k, v in self.componentes.items()}
        e.uniones = dict(self.uniones)
        e.grupos_rigidos = [list(g) for g in self.grupos_rigidos]
        e.lienzos = dict(self.lienzos)
        e.herramientas = dict(self.herramientas)
        e.recortes = dict(self.recortes)
        e.vinculos = dict(self.vinculos)
        e.contador_cuerpos = self.contador_cuerpos
        return e

    def anotar_lecturas(self):
        """Desde ahora los diccionarios del estado anotan qué claves se leen (ver `_DictLeido`)."""
        for nombre in DICTS_ESTADO:
            setattr(self, nombre, _DictLeido(getattr(self, nombre)))

    def cerrar_lecturas(self):
        """Vuelve a diccionarios comunes y devuelve {diccionario: claves leídas o TODAS}."""
        lecturas = {}
        for nombre in DICTS_ESTADO:
            d = getattr(self, nombre)
            if isinstance(d, _DictLeido):
                lecturas[nombre] = d.leidas
                setattr(self, nombre, dict.copy(d))
            else:                       # el paso reemplazó el diccionario entero: cuenta como leído todo
                lecturas[nombre] = TODAS
        return lecturas

    def nuevo_cuerpo(self, op_id, forma, tipo="solido", nombre=None, **atributos):
        self.contador_cuerpos += 1
        # Solo cuentan los cuerpos de este mismo paso (sin anotar que se leyeron todos: así un paso que crea un cuerpo
        # no depende de los cuerpos ajenos y la memoria del documento puede reusarlo).
        k = sum(1 for c in dict.values(self.cuerpos) if c.op_id == op_id) + 1
        cid = f"{op_id}.c{k}"
        while cid in self.cuerpos:
            k += 1
            cid = f"{op_id}.c{k}"
        self.cuerpos[cid] = Cuerpo(cid, nombre or f"Cuerpo{self.contador_cuerpos}", forma, op_id, tipo, **atributos)
        return cid

    def nombre_de_copia(self, nombre):
        """«X (copia)» para la copia de «X»; si ya existe, «X (copia 2)», «X (copia 3)»… La copia de una copia sale de
        la original («Banco (copia)» → «Banco (copia 2)», no «Banco (copia) (copia)»): nombres repetidos obligaban a
        usar el id (T-16 de la prueba de tortura)."""
        base = re.sub(r" \(copia(?: \d+)?\)$", "", nombre)
        usados = {c.nombre for c in self.cuerpos.values()} | {pl.nombre for pl in self.planos.values()}
        usados |= {e[2] for e in self.ejes.values()} | {pt[1] for pt in self.puntos.values()}
        usados |= {c.get("nombre") for c in self.componentes.values()}
        candidato, n = f"{base} (copia)", 2
        while candidato in usados:
            candidato, n = f"{base} (copia {n})", n + 1
        return candidato

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
    def __init__(self, valores_parametros, partir=True):
        self.usados = set()       # nombres de parámetros que leyó la operación al ejecutarse
        self.valores = _Lecturas(valores_parametros, self.usados)
        self.avisos = []
        self.partir = partir      # False en un paso de receta vieja: el corte no divide el cuerpo (`Documento._sin_partir`)
        self.ocultos = ()         # lo oculto al crear el paso (`Operacion.calcular`): sin objetos elegidos no se toca

    def evaluar(self, expr, tipo=LONGITUD):
        """Valor de `expr` para un paso: una longitud de más de 1 km o un ángulo de más de 1e6° es un error. Una
        magnitud que no es la del campo (`w * h` en una longitud) no falla, porque una receta vieja tiene que dar el
        mismo modelo, pero se avisa: la interfaz la rechaza al escribirla."""
        try:
            return acotar(evaluar(expr, tipo, self.valores, estricto=tipo != ESCALAR), tipo)
        except ErrorMagnitud as e:
            self.aviso(f"«{expr}»: {e}")
        return acotar(evaluar(expr, tipo, self.valores), tipo)

    def aviso(self, texto):
        self.avisos.append(texto)


def _orden_parte(solido):
    """Clave para ordenar las partes de un corte: la más grande primero y, entre iguales, por su centro (X, Y, Z), así
    recalcular siempre deja cada parte con el mismo id."""
    return -round(abs(geo.volumen_exacto(solido)), 3), *(round(x, 6) for x in geo.centro_masa(solido))


def poner_resultado(estado, ctx, op_id, c, nueva):
    """`nueva` (lo que dejó Cortar o Intersecar) queda en el cuerpo `c`. Si tiene más sólidos que `c`, cada parte es un
    cuerpo, como en Fusion: la más grande sigue siendo `c` y las demás heredan su aspecto, material y componente. Unir
    no pasa por acá: un cuerpo con sólidos separados por Unir es legítimo. Devuelve los ids de los cuerpos."""
    partes = geo.solidos(nueva)
    if not ctx.partir or len(partes) <= len(geo.solidos(c.forma)):
        c.forma = nueva
        return [c.id]
    partes.sort(key=_orden_parte)
    c.forma = partes[0]
    return [c.id] + [estado.nuevo_cuerpo(op_id, s, c.tipo, **atributos_copia(c)) for s in partes[1:]]


def aplicar_resultado(estado, ctx, op_id, herramienta, operacion, objetivo="", tipo="solido"):
    """Aplica una forma recién creada según FeatureOperations. `objetivo`: id de un cuerpo, lista de ids
    ("Objetos para cortar" de Fusion) o vacío = automático (los cuerpos sólidos que toca).
    Devuelve los ids de cuerpos afectados. La herramienta queda anotada en `estado.herramientas[op_id]` (el patrón
    de operaciones la repite)."""
    if geo.esta_vacia(herramienta):
        raise ErrorOperacion("La operación no generó geometría.")
    anotado = list(objetivo) if isinstance(objetivo, (list, tuple)) else objetivo
    estado.herramientas[op_id] = estado.herramientas.get(op_id, ()) + ((herramienta, operacion, anotado, tipo),)
    if operacion == "nuevo":
        sols = (geo.solidos(herramienta) if tipo == "solido" else []) or [herramienta]
        return [estado.nuevo_cuerpo(op_id, s, tipo) for s in sols]
    if operacion not in OPERACIONES_COMBINAR:
        raise ErrorOperacion(f"Operación desconocida: {operacion}")
    lista = list(objetivo) if isinstance(objetivo, (list, tuple)) else [objetivo] if objetivo else []
    if lista:
        objetivos = [estado.cuerpo(o) for o in lista]
    else:
        objetivos = [c for c in estado.cuerpos.values() if getattr(c, "tipo", "solido") == "solido"
                     and c.id not in ctx.ocultos and c.componente not in ctx.ocultos]
        if operacion == "unir":
            objetivos = [c for c in objetivos if geo.se_tocan(c.forma, herramienta)]
    if not objetivos:
        if operacion == "unir":
            ctx.aviso("No tocó ningún cuerpo: se creó un cuerpo nuevo.")
            return [estado.nuevo_cuerpo(op_id, herramienta)]
        raise ErrorOperacion(f"No hay cuerpos sobre los que {OPERACIONES_COMBINAR[operacion].lower()}.")

    if operacion == "unir":
        resultado = herramienta
        v_previa = None                # volumen de lo acumulado hasta acá (se mide una vez)
        avisos = []
        for c in objetivos:
            nueva = geo.booleano(resultado, c.forma, "unir", avisos)
            # Integración exacta: barata. `geo.volumen` malla el cuerpo entero si tiene caras libres (20 s en 500 B-spline)
            # y solo se pide para confirmar un aviso de pérdida de material.
            v_nueva, v_c = geo.volumen_exacto(nueva), geo.volumen_exacto(c.forma)
            if v_previa is None:
                v_previa = geo.volumen_exacto(herramienta)
            if not lista:
                # Un cuerpo que solo TOCA por cara (tope coplanar) se une sin sumar volumen: avisar, así
                # no se absorbe un cuerpo ajeno en silencio (el join sobre la cara es lo normal).
                v_antes = v_previa + v_c
                if v_nueva >= v_antes - max(v_antes, 1.0) * 1e-7:
                    ctx.aviso(f"{c.nombre} se unió a la herramienta compartiendo solo una cara (sin solape).")
            # Una unión no puede pesar menos que lo que ya había (B-52: unir una primitiva a un cuerpo
            # compuesto descartaba en silencio un sólido entero — la espiral, −3.194 mm³).
            v_menor = max(v_previa, v_c)
            if v_nueva < v_menor - max(v_menor, 1.0) * 5e-4:
                v_nueva, v_menor = geo.volumen(nueva), max(geo.volumen(resultado), geo.volumen(c.forma))
                if v_nueva < v_menor - max(v_menor, 1.0) * 5e-4:
                    ctx.aviso(f"{c.nombre}: la unión perdió {v_menor - v_nueva:.2f} mm³ de material (el kernel "
                              "descartó geometría en un contacto degenerado); revisalo con check_geometry.")
            v_previa = v_nueva
            resultado = nueva
        principal = objetivos[0]
        principal.forma = resultado
        for c in objetivos[1:]:
            del estado.cuerpos[c.id]
        if len(geo.solidos(resultado)) > len(geo.solidos(herramienta)) or not rv.es_estanca(resultado):
            ctx.aviso(f"{principal.nombre}: la unión dejó el cuerpo partido, abierto o con aristas compartidas "
                      "de más (posible contacto tangente o en cuña); revisalo con check_geometry.")
        else:
            for texto in avisos:
                ctx.aviso(f"{principal.nombre}: {texto}")
        return [principal.id]

    afectados = []
    for c in objetivos:
        if not lista and not geo.se_tocan(c.forma, herramienta):
            continue
        if lista and operacion == "cortar" and not geo.se_tocan(c.forma, herramienta):
            ctx.aviso(f"La herramienta no toca a {c.nombre}: no le cortó nada.")
        avisos = []
        nueva = geo.booleano(c.forma, herramienta, operacion, avisos)
        for texto in avisos:
            ctx.aviso(f"{c.nombre}: {texto}")
        if geo.esta_vacia(nueva) and operacion == "intersecar":      # T-22: igual que Combinar, nada se borra
            raise ErrorOperacion(f"El resultado quedó vacío: la herramienta no se interseca con {c.nombre}.")
        if geo.esta_vacia(nueva):
            del estado.cuerpos[c.id]
            ctx.aviso(f"{c.nombre} quedó vacío y se eliminó.")
            afectados.append(c.id)
        else:
            afectados += poner_resultado(estado, ctx, op_id, c, nueva)
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
def _migrador(clave):
    """`migrar_receta` de una operación cuyo cálculo cambió: las recetas viejas (sin `clave`) reciben
    `clave` = 1 y conservan el cálculo de antes, así un ensamblaje compensado a mano (ángulo 180°, Voltear,
    dz) abre igual. Las operaciones nuevas toman el valor de PARAMS (2)."""
    def migrar(d):
        params = d.get("params", {})
        if isinstance(params, dict) and clave not in params:
            d = dict(d, params=dict(params, **{clave: 1}))
        return d
    return staticmethod(migrar)


def _version_de(p, clave):
    """La versión de cálculo guardada en `clave` (1 o 2). Otro valor (texto, lista, None, 3…) es un error que
    nombra el campo."""
    v = p.get(clave)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v not in (1, 2):
        raise ErrorOperacion(f"Parámetro mal formado «{clave}»: llegó {v!r}; tiene que ser 1 (el cálculo de las "
                             "recetas viejas) o 2 (el actual).")
    return int(v)


class Operacion:
    TIPO = ""
    ETIQUETA = ""
    ICONO = ""
    PARAMS = {}
    EXPRESIONES = ()   # claves de `p` que son expresiones (pueden usar parámetros)
    # Claves de `p` con una lista cerrada de valores → los valores válidos (tupla o dict valor → etiqueta). Es la
    # única fuente: `validar_opciones` la usa al calcular y describe_operation la muestra como «choices».
    OPCIONES = {}
    # False si el resultado depende de algo fuera del estado y de los parámetros (un archivo externo) o el paso cambia
    # el documento al calcularse: entonces la memoria por paso del documento nunca lo reusa (`Documento._de_memo`).
    MEMORIZABLE = True

    def __init__(self, id, nombre=None, suprimida=False, **params):
        self.id = id
        self.nombre = nombre or f"{self.ETIQUETA} {id}"
        self.suprimida = suprimida
        self.p = copy.deepcopy(self.PARAMS)
        self.p.update(params)
        self.ocultos = []       # ids ocultos al crear el paso (`Documento._fijar_ocultos`)
        # Pasos cuyos cuerpos modificó la última ejecución con objetivo "Automático": también son
        # dependencias (si no, se podría mover o borrar el cuerpo que esta operación corta o une).
        self._usados = set()

    def dependencias(self):
        return set(self._usados)

    def expresiones(self):
        return [self.p[k] for k in self.EXPRESIONES]

    def claves_modelo(self):
        """Claves de `p` que la tabla de parámetros lista como parámetros del modelo de este paso (PAR-4)."""
        return [k for k in self.EXPRESIONES if not isinstance(self.p.get(k), bool)
                and isinstance(self.p.get(k), (str, int, float)) and str(self.p[k]).strip()]

    def renombrar_parametro(self, viejo, nuevo):
        """Actualiza las expresiones de este paso (de una copia: `Documento.renombrar_parametro`). True si cambió algo."""
        cambios = {e: renombrar_en(e, viejo, nuevo) for e in self.expresiones()
                   if isinstance(e, str) and viejo in nombres_usados(e)}
        if cambios:                 # una opción medida="total" no es el parámetro `total`
            self.p = {k: v if k in self.OPCIONES else _reemplazar_textos(v, cambios) for k, v in self.p.items()}
        return bool(cambios)

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
        ctx.ocultos = self.ocultos
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
                "params": copy.deepcopy(self.p), **({"ocultos": list(self.ocultos)} if self.ocultos else {})}


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


def exigir_sin_ciclo(op, *referencias):
    """B-260: un paso no puede usarse a sí mismo como referencia (vía edit_feature o una receta)."""
    if op.id in ent.dependencias_de(*referencias):
        raise ErrorOperacion(f"«{op.nombre}» no puede usarse a sí mismo como referencia.")


class OpPlano(Operacion):
    """Plano de construcción (CONSTRUIR de Fusion): de desfase, en ángulo, tangente, medio, por dos
    aristas, por tres puntos, perpendicular o en ruta (`tipo`, ver ops_construir.TIPOS_PLANO). Las
    referencias van en `refs`; los proyectos viejos usan `base`/`marco` (plano de desfase)."""
    TIPO, ETIQUETA, ICONO = "plano", "Plano", "▱"
    PARAMS = {"tipo": "desfase", "base": "XY", "marco": None, "distancia": "10 mm", "refs": [], "angulo": "0 deg",
              "posicion": "0.5", "desfase": "0 mm", "extension": "distancia", "objeto": None, "direccion": "U",
              "lugar": None, "tipo_distancia": "proporcional", "cadena_tangente": False, "redimensionar": "predeterminado",
              "tipo_extension": "distancia", "medida": "0 mm", "objeto_extension": None, "eje_0": ""}
    EXPRESIONES = ("distancia", "angulo", "posicion", "desfase", "medida")

    def dependencias(self):
        deps = super().dependencias() | ent.dependencias_de(self.p["objeto"], self.p["lugar"], self.p["objeto_extension"],
                                                            self.p.get("refs"))
        if not self.p.get("refs") and _es_ref_operacion(self.p["base"]):
            deps |= ent.dependencias({"tipo": "plano", "id": self.p["base"]})      # B-263: «op2_xy» depende de «op2»
        return deps - {self.id}       # B-260: una referencia a sí mismo no lo traba; ejecutar la rechaza

    def ejecutar(self, estado, ctx):
        exigir_sin_ciclo(self, self.p["objeto"], self.p["lugar"], self.p["objeto_extension"], self.p.get("refs"))
        if self.p.get("refs"):
            from .ops_construir import calcular_plano, medida_plano
            entidades = [_resolver(r, estado) for r in self.p["refs"]]
            plano = calcular_plano(self.p, entidades, ctx, estado)
            plano.nombre = self.nombre
            estado.planos[self.id] = plano
            estado.medidas[self.id] = medida_plano(self.p, plano, entidades, ctx, estado)
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
    # angulo_plano: giro del plano alrededor de su eje u, después del desplazamiento (boceto de sección de malla).
    PARAMS = {"plano": "XY", "desplazamiento": "0", "marco": None, "cara": None, "angulo_plano": "0 deg"}
    EXPRESIONES = ("desplazamiento", "angulo_plano")

    def __init__(self, id, nombre=None, suprimida=False, boceto=None, **params):
        super().__init__(id, nombre, suprimida, **params)
        self.boceto = boceto if boceto is not None else Boceto()
        self.perdidas = []              # ids de las proyecciones que no coincidieron en el último cálculo (solo memoria)
        self.rehechas = {}              # {id: (primitivas, puntos)} de las siluetas rehechas en el último cálculo (H-77)
        self._textos_parametricos = {}  # contenido leído al calcular, para declarar sus expresiones actuales

    def valores_cotas(self, ctx):
        """Valor de cada cota. Sin el tope de `Contexto.evaluar`: una cota fuera de rango no falla el boceto, la
        valida el propio boceto y avisa (test_cota_manejada_por_parametro_fuera_de_rango_avisa)."""
        return {c.id: evaluar(c.nombre or c.expresion, ANGULO if c.tipo == "angulo" else LONGITUD, ctx.valores)
                for c in self.boceto.cotas.values() if not c.referencia}

    def expresiones(self):
        from ..restricciones import objetos
        en_textos = [e for c in self.boceto.curvas.values() if isinstance(c, Texto)
                     for e in (expresiones_de_texto(self._textos_parametricos.get(c.id, c.texto))
                               + ([c.parametro_texto] if c.parametro_texto else [])
                               + ([c.altura_expr] if c.altura_expr else []))]
        return (super().expresiones() + [e for c in self.boceto.cotas.values() if not c.referencia
                                       for e in (c.nombre, c.expresion)]
                + en_textos + [c["expresion"] for c in self.boceto.geo3d.get("cotas", {}).values()]
                + objetos.expresiones(self.boceto)
                + [e for r in self.boceto.patrones for e in r["params"].get("expresiones", {}).values()])

    def claves_modelo(self):
        return []                # los parámetros de un boceto son sus cotas

    def renombrar_parametro(self, viejo, nuevo):
        cambio = super().renombrar_parametro(viejo, nuevo)
        for objeto in self.boceto.objetos.values():
            for paso in objeto.get("pasos", []):
                for clave, valor in paso.get("parametros", {}).items():
                    if isinstance(valor, str):
                        texto = renombrar_en(valor, viejo, nuevo)
                        cambio = cambio or texto != valor
                        paso["parametros"][clave] = texto
        for c in self.boceto.cotas.values():
            expresion = renombrar_en(c.expresion, viejo, nuevo)
            cambio = cambio or c.nombre == viejo or expresion != c.expresion
            c.nombre, c.expresion = nuevo if c.nombre == viejo else c.nombre, expresion
        for c in self.boceto.geo3d.get("cotas", {}).values():
            expresion = renombrar_en(c["expresion"], viejo, nuevo)
            cambio = cambio or expresion != c["expresion"]
            c["expresion"] = expresion
        for r in self.boceto.patrones:
            expresiones = r["params"].get("expresiones", {})
            for clave, texto in expresiones.items():
                expresion = renombrar_en(texto, viejo, nuevo)
                cambio = cambio or expresion != texto
                expresiones[clave] = expresion
        for c in self.boceto.curvas.values():
            if isinstance(c, Texto):
                antes = c.texto, c.parametro_texto, c.parametro_altura, c.altura_expr
                c.texto = renombrar_en_texto(c.texto, viejo, nuevo)
                c.parametro_texto = nuevo if c.parametro_texto == viejo else c.parametro_texto
                c.parametro_altura = nuevo if c.parametro_altura == viejo else c.parametro_altura
                c.altura_expr = renombrar_en(c.altura_expr, viejo, nuevo) if c.altura_expr else c.altura_expr
                cambio = cambio or antes != (c.texto, c.parametro_texto, c.parametro_altura, c.altura_expr)
        return cambio

    def dependencias(self):
        deps = super().dependencias()
        if _es_ref_operacion(self.p["plano"]):
            deps |= ent.dependencias({"tipo": "plano", "id": self.p["plano"]})     # B-263: «op2_xy» depende de «op2»
        if self.p["plano"] == "cara":
            deps |= ent.dependencias_de(self.p.get("cara"))
        for registro in self.boceto.proyecciones:
            deps |= ent.dependencias_de(registro["refs"], [registro["eje"]] if registro.get("eje") else [])
        for c in self.boceto.geo3d.get("curvas", {}).values():     # Intersection Curve / Project To Surface
            if "origen" in c:
                deps |= ent.dependencias_de(c["origen"].get("refs"), c["origen"].get("curves")) - {self.id}
        for origen in self.boceto.geo3d.get("vinculos", {}).values():      # vértices de Incluir geometría 3D
            deps |= ent.dependencias_de(origen.get("refs")) - {self.id}
        return deps

    def plano(self, estado, ctx):
        base = resolver_plano(self.p["plano"], self.p.get("marco"), estado, self.p.get("cara"))
        d = ctx.evaluar(self.p["desplazamiento"])
        plano = base.desplazado(d) if d else base
        angulo = ctx.evaluar(self.p.get("angulo_plano", "0 deg"), ANGULO)
        return plano.girado(angulo) if angulo else plano

    def _reproyectar(self, boceto, plano, estado, ctx):
        """Recalcula las proyecciones asociativas antes del solver, sin alterar el boceto guardado. Las que ya no
        coinciden con el modelo quedan como estaban y se anotan en `perdidas` (Manage Lost Projections)."""
        self.perdidas, self.rehechas = [], {}
        for registro in list(boceto.proyecciones):      # una silueta rehecha cambia de lugar en la lista
            primitivas, puntos = [], []
            try:
                entidades = [ent.resolver(ref, estado) for ref in registro["refs"]]
                giro = None if registro["modo"] != "giro" else {
                    "eje": ent.como_eje(ent.resolver(registro["eje"], estado)), "tolerancia": registro["tolerancia"],
                    "invertir": registro["invertir"]}
            except (ent.ErrorReferencia, ent.ReferenciaMalFormada):
                coincide = False
            else:
                for e in entidades:
                    p, q = ent.proyectar_entidad(e, plano, registro["modo"], giro)
                    primitivas.extend(p)
                    puntos.extend(q)
                coincide = boceto.reproyectar(registro, primitivas, puntos)
                if not coincide and registro["modo"] == "silueta" and (primitivas or puntos):
                    quitadas = boceto.rehacer_proyeccion(registro, primitivas, puntos)       # H-77: como Fusion
                    self.rehechas[registro["id"]] = (primitivas, puntos)
                    coincide = True
                    if quitadas:
                        ctx.aviso(f"{self.nombre}: la silueta proyectada cambió de forma y se rehízo; se quitaron "
                                  f"{quitadas} restricciones o cotas de tramos que ya no están.")
            if not coincide:
                self.perdidas.append(registro["id"])
                ctx.aviso(f"{self.nombre}: la proyección ya no coincide con el modelo; queda como estaba.")

    def rehacer_en(self, boceto):
        """Aplica a `boceto` (una copia del guardado, para editarla) las siluetas que el último cálculo rehízo (H-77), en
        el mismo orden: así sus tramos tienen los mismos ids que muestran get_sketch y la ventana, y se pueden
        restringir. La edición guarda la silueta nueva, como Fusion. Devuelve `boceto`."""
        for rid, (primitivas, puntos) in self.rehechas.items():
            registro = next((r for r in boceto.proyecciones if r["id"] == rid), None)
            if registro is not None:
                boceto.rehacer_proyeccion(registro, primitivas, puntos)
        return boceto

    def copia(self):
        """Las ediciones (API, parámetros, ventana) parten de una copia: lleva las siluetas rehechas (`rehacer_en`)."""
        nueva = super().copia()
        self.rehacer_en(nueva.boceto)
        return nueva

    def _conservar_lado_cotas(self, boceto):
        """Si un borde proyectado cruzó una entidad acotada, inicia el solver del lado original de la cota."""
        fijos = boceto.puntos_fijos()
        for cota in boceto.cotas.values():
            if cota.referencia or cota.tipo != "distancia" or len(cota.entidades) != 2:
                continue
            linea, entidad = cota.entidades
            curva = boceto.curvas.get(entidad)
            if curva is not None and curva.tipo == "linea" and curva.proyectada:
                linea, entidad = entidad, linea
            curva = boceto.curvas.get(linea)
            if curva is None or curva.tipo != "linea" or not curva.proyectada:
                continue
            puntos = boceto.puntos_de([entidad])
            if not puntos or any(p in fijos for p in puntos):
                continue
            antes = distancia_punto_recta(self.boceto.coords(puntos[0]), *self.boceto._extremos_linea(linea))
            despues = distancia_punto_recta(boceto.coords(puntos[0]), *boceto._extremos_linea(linea))
            if antes != 0 and antes * despues <= 0:
                ux, uy = boceto._direccion(linea)
                for pid in puntos:
                    boceto.puntos[pid].x -= uy * (antes - despues)
                    boceto.puntos[pid].y += ux * (antes - despues)

    def _seguir_al_modelo(self, boceto, plano, estado, ctx):
        """Recalcula EN LA COPIA las curvas 3D de Intersection Curve / Project To Surface / Include 3D Geometry (y los
        vértices incluidos) con el modelo actual, conservando sus ids. Cada curva sigue a la de su «index» en el
        resultado (las que se borraron no cuentan); si
        la referencia se perdió o esa curva ya no existe o cambió de tipo, aviso y queda como estaba."""
        from ..restricciones import boceto3d as b3
        g = b3.datos(boceto)
        grupos = {}
        for cid, c in g["curvas"].items():
            if "origen" in c and not (c["origen"].get("mode") == "vector" and "direction" not in c["origen"]):
                clave = {k: v for k, v in c["origen"].items() if k != "index"}
                grupos.setdefault(json.dumps(clave, sort_keys=True), []).append(cid)
        for ids in grupos.values():
            nuevo = Boceto()
            try:
                nuevas = [b3.agregar_desde_mundo(nuevo, d, plano) for d in aristas_de_origen(g["curvas"][ids[0]]["origen"],
                                                                                            estado)]
            except (ent.ErrorReferencia, ent.ReferenciaMalFormada, geo.ErrorGeometria, ErrorBoceto, KeyError) as e:
                ctx.aviso(f"{self.nombre}: una curva 3D ya no se puede recalcular ({e}); queda como estaba.")
                continue
            h = b3.datos(nuevo)
            for pos, i in enumerate(ids):
                k = g["curvas"][i]["origen"].get("index", pos)       # recetas anteriores: la posición en el grupo
                n = nuevas[k] if isinstance(k, int) and 0 <= k < len(nuevas) else None
                if n is None or (g["curvas"][i]["tipo"], len(g["curvas"][i]["puntos"])) != (
                        h["curvas"][n]["tipo"], len(h["curvas"][n]["puntos"])):
                    ctx.aviso(f"{self.nombre}: la intersección o proyección cambió de forma; la curva 3D queda como "
                              "estaba.")
                    continue
                for viejo, punto in zip(g["curvas"][i]["puntos"], h["curvas"][n]["puntos"], strict=True):
                    g["puntos"][viejo] = h["puntos"][punto]
                for clave in ("radio", "normal", "eje_mayor", "radio_menor", "cerrada"):
                    if clave in h["curvas"][n]:
                        g["curvas"][i][clave] = h["curvas"][n][clave]
        for pid, origen in g.get("vinculos", {}).items():                 # H-79: los vértices incluidos también
            try:
                g["puntos"][pid] = b3.a_boceto(plano, ent.resolver(origen["refs"][0], estado).punto)
            except (ent.ErrorReferencia, ent.ReferenciaMalFormada, KeyError, TypeError) as e:
                ctx.aviso(f"{self.nombre}: un vértice incluido ya no se encuentra ({e}); queda como estaba.")

    def ejecutar(self, estado, ctx):
        plano = self.plano(estado, ctx)
        # Se resuelve una COPIA: el boceto guardado no se toca. Si un parámetro deja el boceto en
        # conflicto, al volver a un valor válido se parte otra vez de la geometría original.
        boceto = self.boceto.copia()
        if boceto.objetos:
            from ..restricciones import objetos
            objetos.evaluar(boceto, lambda v, k: ctx.evaluar(v, ANGULO if k == "angulo" else
                                                            ESCALAR if k in ("sx", "sy") else LONGITUD))
        self._reproyectar(boceto, plano, estado, ctx)
        boceto.evaluar_patrones(ctx.evaluar)
        if boceto.proyecciones:
            self._conservar_lado_cotas(boceto)
        self._textos_parametricos = {}
        for c in boceto.curvas.values():               # {parámetro} dentro de un texto (el fx de Fusion)
            if isinstance(c, Texto):
                try:
                    contenido = _contenido_texto(c, ctx.valores)
                    self._textos_parametricos[c.id] = contenido
                    c.texto = contenido
                    c.texto = texto_con_valores(contenido, ctx.valores)
                except ErrorExpresion as e:
                    ctx.aviso(f"{self.nombre}: texto «{c.texto}»: {e}")
            if isinstance(c, Texto) and c.altura_expr:  # «Text height» de Fusion: la altura sigue al parámetro
                try:
                    altura = ctx.evaluar(c.altura_expr)
                    if c.altura_a and c.altura > 0:           # el % de Fusion no cambia con la altura; los mm, sí
                        c.espaciado *= altura / c.altura
                    c.altura = altura
                except ErrorExpresion as e:
                    ctx.aviso(f"{self.nombre}: altura del texto «{c.altura_expr}»: {e}")
        valores = self.valores_cotas(ctx)
        for c in self.boceto.cotas.values():           # una cota manejada por parámetro puede quedar fuera de rango
            if c.referencia:
                continue
            try:
                validar_valor_cota(c.tipo, valores[c.id])
            except ErrorBoceto as e:                   # aviso y no error: los proyectos viejos abren igual
                ctx.aviso(f"{self.nombre}: {e}")
        res = resolver(boceto, valores)
        if not res.ok:
            ctx.aviso(res.descripcion())
        perfiles = detectar_boceto(boceto, plano)
        br = BocetoResuelto(self.id, self.nombre, boceto, plano, perfiles, res)
        if any(boceto.geo3d.values()):                 # Boceto 3D: su propio solver, sobre la misma copia
            from ..restricciones import boceto3d
            estado.bocetos[self.id] = br               # una curva fuente puede ser de este mismo boceto
            self._seguir_al_modelo(boceto, plano, estado, ctx)
            br.solver3d = boceto3d.resolver(boceto, {
                k: ctx.evaluar(c["expresion"], ANGULO if c.get("tipo") == "angulo" else LONGITUD)
                for k, c in boceto.geo3d.get("cotas", {}).items()})
            if not br.solver3d.ok:
                ctx.aviso(f"{self.nombre}: {br.solver3d.mensaje}")
        estado.bocetos[self.id] = br

    def a_dict(self):
        d = super().a_dict()
        d["boceto"] = self.boceto.a_dict()
        return d


def aristas_de_origen(origen, estado):
    """Curvas (`curvas3d.describir`, coordenadas del mundo) que deja hoy la selección guardada en el «origen» de una
    curva 3D de Intersection Curve o Project To Surface (lo que calculan intersect_curves y project_to_surface). Un
    plano, o una cara elegida como plano («infinito»), se corta como plano infinito."""
    from ..nucleo import curvas3d
    objetivos = []
    for ref in origen["refs"]:
        e = ent.resolver(ref, estado)
        if ref["tipo"] == "plano" or ref.get("infinito"):
            pl = ent.como_plano(e)
            objetivos.append((pl.origen, pl.normal))
        else:
            objetivos.append(e.forma)
    if origen["tool"] == "isoparametric_curve":
        return curvas3d.isoparametricas(objetivos[0], origen["point"], origen["direction"], origen["type"],
                                        origen.get("distance"), origen.get("quantity"))
    if origen["tool"] == "include_3d":           # Include 3D Geometry: las aristas (o el borde de la cara) donde están
        return [curvas3d.describir(a) for f in objetivos for a in geo._aristas_unicas(f)]
    fuente = [(e.forma, e.plano.normal) for e in (ent.resolver(r, estado) for r in origen["curves"])]
    if origen["tool"] == "project_to_surface":
        caras = geo.compuesto(objetivos)
        if origen["mode"] == "vector":
            return [curvas3d.describir(x) for a, _ in fuente
                    for x in curvas3d.proyectar_vector(a, caras, origen["direction"])]
        salida = []
        for a, _ in fuente:
            pts = curvas3d.proyectar_cercano(a, caras)
            cerrada = math.dist(pts[0], pts[-1]) < 1e-7
            salida.append({"tipo": "spline", "puntos": list(pts[:-1] if cerrada else pts), "cerrada": cerrada})
        return salida
    formas = [f for f in objetivos if not isinstance(f, tuple)] + [a for a, _ in fuente]
    lejos = [np.linalg.norm(p) for f in formas for caja in [geo.caja_envolvente(f)] if caja for p in caja]
    medio = 2 * max(lejos + [np.linalg.norm(f[0]) for f in objetivos if isinstance(f, tuple)] + [1.0]) + 100
    destinos = [curvas3d.cara_de_plano(*f, medio) if isinstance(f, tuple) else f for f in objetivos]
    if fuente:
        pares = [(curvas3d.extruir_arista(a, n, medio), f) for a, n in fuente for f in destinos]
    else:
        pares = [(destinos[i], destinos[j]) for i in range(len(destinos)) for j in range(i + 1, len(destinos))]
    return [curvas3d.describir(x) for a, f in pares for x in curvas3d.seccion(a, f)]


def _contenido_texto(texto, valores):
    """Contenido editable de un texto: su parámetro automático, o el texto de una receta anterior."""
    nombre = texto.parametro_texto
    if nombre is None:
        return texto.texto
    if nombre not in valores or not isinstance(valores[nombre], str):
        raise ErrorExpresion(f"El parámetro '{nombre}' del texto no existe o no es de tipo texto.")
    return valores[nombre]


def _exigir_tipos(ref, tipos):
    """Con `tipos` (p. ej. ("cara",)), una referencia bien formada de otro tipo es un ParametroMalFormado: sin esto,
    un cuerpo en un campo de caras llega al núcleo y el kernel falla con un TypeError sin nombre de campo."""
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
    MENSAJE_CARAS = "Las caras elegidas no miran para el mismo lado: hacé la operación con una cara por paso."

    def dependencias(self):
        deps = super().dependencias()
        if self.p.get("boceto") and isinstance(self.p["boceto"], str):
            deps.add(self.p["boceto"].split(".", 1)[0])
        deps |= _deps_objetivo(self.p.get("objetivo")) | _deps_objetivo(self.p.get("objetivos"))
        deps |= ent.dependencias_de(self.p.get("caras"), self.p.get("hasta"), self.p.get("inicio_objeto"),
                                    self.p.get("eje_ref"), self.p.get("hasta2"), self.p.get("curvas"))
        return deps - {self.id}

    def _caras(self, estado, ctx=None):
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
                perfil, nota = buscar_por_firma_tolerante(br.perfiles, ref["firma"], ref.get("centroide"), br.plano)
                if perfil is None:
                    if ent.es_de_texto(ref["firma"], br):
                        raise ErrorOperacion("Un perfil seleccionado era un pedazo de una letra y ya no existe como "
                                             "región: volvé a elegir el texto.")
                    raise ErrorOperacion("Un perfil seleccionado ya no existe en el boceto (cambió su contorno).")
                if nota and ctx is not None:
                    ctx.aviso(nota)
                caras.append(perfil.cara)
            plano = br.plano
        normal_cara = None
        for e in _resolver_todas(self.p.get("caras"), estado):
            if e.plano is None:
                raise ErrorOperacion("Solo se pueden usar caras planas.")
            if normal_cara is None:
                normal_cara = e.plano.normal
            elif float(normal_cara @ e.plano.normal) < 1 - 1e-6:
                # Cada cara se extruye en la normal del perfil: si miran para lados distintos, el resultado es un
                # cuerpo degenerado (B-164). En Fusion las caras de una extrusión tienen que ser coplanares.
                raise ErrorOperacion(self.MENSAJE_CARAS)
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


def _reemplazar_textos(x, cambios):
    """`x` con cada cadena que está en `cambios` reemplazada, a cualquier profundidad de listas y diccionarios.
    shortcut: no se sabe qué cadena es expresión; salvo OPCIONES y «tipo», una opción que se llame igual que el parámetro
    cambia con él. Si aparece un caso, cada paso tendría que listar sus claves de expresión."""
    if isinstance(x, dict):
        return {k: v if k == "tipo" else _reemplazar_textos(v, cambios) for k, v in x.items()}
    if isinstance(x, list):
        return [_reemplazar_textos(v, cambios) for v in x]
    return cambios.get(x, x) if isinstance(x, str) else x


class OpExtrusion(_OpConPerfiles):
    """Extruir de Fusion [SLD-EXTRUDE-SOLID]: tipo (normal o delgada), inicio (plano del perfil, desfase u
    objeto), dirección (un lado, dos lados, simétrica con media longitud o longitud total), extensión
    (distancia, al objeto o todo), ángulo de conicidad y operación (nuevo cuerpo, unir, cortar, intersecar)
    sobre los cuerpos automáticos o los elegidos en «Objetos para cortar»."""
    TIPO, ETIQUETA, ICONO = "extrusion", "Extrusión", "⬆"
    MENSAJE_CARAS = "Las caras elegidas no miran para el mismo lado: extruí cada cara por separado."
    PARAMS = {"boceto": "", "perfiles": [], "caras": [], "tipo": "solida", "inicio": "plano", "desfase_inicio": "0 mm",
              # El panel y la API arrancan en «Longitud total» (H-86); acá queda "mitad": es lo que calcula una
              # receta vieja sin la clave, que tiene que abrir igual (igual que en `proyectar_eje`, CAP-12).
              "inicio_objeto": None, "direccion": "un_lado", "medida": "mitad", "extension": "distancia",
              "distancia": "10 mm", "hasta": None, "extension2": "distancia", "distancia2": "10 mm", "hasta2": None,
              "conicidad": "0 deg", "conicidad2": "0 deg", "espesor": "", "ubicacion": "lado1", "invertir": False,
              "hasta_modo": "cara", "desfase_hasta": "0 mm", "curvas": [],
              "simetrica": False, "operacion": "nuevo", "objetivo": "", "objetivos": []}
    EXPRESIONES = ("distancia", "distancia2", "desfase_inicio", "conicidad", "conicidad2", "espesor", "desfase_hasta")
    # espesor "" = el de la regla de plástico asignada (1 mm sin regla)
    # Lo que no se usa con estas opciones no se lista: Fusion crea AlongDistance y TaperAngle, por lado.
    def claves_modelo(self):
        p = self.p
        dos_lados = p.get("direccion") == "dos_lados"
        activas = {"distancia": p.get("extension") == "distancia", "distancia2": dos_lados and p.get("extension2") == "distancia",
                   "desfase_inicio": p.get("inicio") in ("desfase", "objeto"), "conicidad": True, "conicidad2": dos_lados,
                   "espesor": p.get("tipo") == "delgada",
                   "desfase_hasta": "objeto" in (p.get("extension"), p.get("extension2"))}
        return [k for k in super().claves_modelo() if activas[k]]

    OPCIONES = {"tipo": ("solida", "delgada"), "inicio": ("plano", "desfase", "objeto"), "direccion": DIRECCIONES,
                "medida": ("mitad", "total"), "extension": ("distancia", "objeto", "todo"),
                "extension2": ("distancia", "objeto", "todo"), "hasta_modo": ("cara", "cuerpo", "a_traves"),
                "ubicacion": ("lado1", "lado2", "centro"), "operacion": OPERACIONES_CUERPO}

    def expresiones(self):
        return [self.p[k] for k in self.EXPRESIONES if k in self.p]

    def ejecutar(self, estado, ctx):
        forma = self._forma(estado, ctx)
        afectados = aplicar_resultado(estado, ctx, self.id, forma, self.p["operacion"], self._objetivo())
        self._registrar_usados(afectados)
        _exigir_cuerpo_con_volumen(estado, afectados)

    def _forma(self, estado, ctx):
        """Herramienta común a la previa y al resultado; los límites se calculan por lado."""
        p = self.p
        if not p.get("simetrica") and p.get("direccion") == "dos_lados":
            if p.get("extension2") == "objeto" and not p.get("hasta2"):
                raise ErrorOperacion("Elegí la cara, el plano o el cuerpo hasta donde llega el lado 2 de la extrusión.")
            if p.get("extension") != "distancia" or p.get("extension2") != "distancia":
                if p.get("extension2") == "distancia":
                    geo.exigir_longitud(ctx.evaluar(p["distancia2"]), "La distancia del lado 2")
                formas = []
                for sufijo, signo in (("", 1), ("2", -1)):
                    extension = p.get("extension" + sufijo, "distancia")
                    distancia = abs(ctx.evaluar(p["distancia" + sufijo])) if extension == "distancia" else 1.0
                    lado = type(self)(self.id, self.nombre, **dict(
                        p, direccion="un_lado", extension=extension, distancia=str(signo * distancia),
                        hasta=p.get("hasta" + sufijo), conicidad=p.get("conicidad" + sufijo, "0 deg")))
                    formas.append(lado._forma(estado, ctx))
                return geo.unir_todos(formas)
        curvas = _resolver_todas(p.get("curvas"), estado) if p.get("tipo") == "delgada" else []
        if curvas and not p.get("perfiles") and not p.get("caras"):
            plano = next((e.plano for e in curvas if e.plano is not None), None)
            if plano is None:
                raise ErrorOperacion("Las curvas abiertas tienen que ser de un boceto.")
            caras = []
        else:
            plano, caras = self._caras(estado, ctx)
        n = -plano.normal if p.get("invertir") else plano.normal
        direccion = "simetrica" if p.get("simetrica") else p.get("direccion", "un_lado")
        medida = "total" if p.get("simetrica") else p.get("medida", "mitad")
        d1 = ctx.evaluar(p["distancia"])
        d2 = ctx.evaluar(p.get("distancia2", "0")) if direccion == "dos_lados" else None
        desfase = 0.0
        inclinado = None
        if p.get("inicio") in ("desfase", "objeto"):
            desfase = ctx.evaluar(p.get("desfase_inicio", "0"))
        if p.get("inicio") == "objeto":
            e = _resolver(p.get("inicio_objeto"), estado) if p.get("inicio_objeto") else None
            if e is None or e.plano is None:
                raise ErrorOperacion("Elegí una cara plana o un plano como inicio de la extrusión.")
            if abs(float(e.plano.normal @ n)) < 1 - 1e-9:
                # Fusion (Start = Object): con el objeto inclinado la base de la extrusión es el perfil proyectado
                # sobre él a lo largo de la dirección; con un objeto paralelo basta el desfase, como siempre.
                inclinado = e.plano
            else:
                desfase += float((e.plano.origen - plano.origen) @ n)
        hasta = caja = None
        if p.get("extension") == "objeto":
            if not p.get("hasta"):
                raise ErrorOperacion("Elegí la cara, el plano o el cuerpo hasta donde llega la extrusión.")
            hasta = self._forma_objeto(_resolver(p["hasta"], estado))
        elif p.get("extension") == "todo":
            caja = _caja_todo(estado)
        delgado = None
        if p.get("tipo") == "delgada":
            espesor = str(p.get("espesor") or "").strip() or espesor_plastico(estado, self._cuerpos_objetivo())
            delgado = {"espesor": ctx.evaluar(espesor), "ubicacion": p.get("ubicacion", "lado1")}
        conicidad = ctx.evaluar(p.get("conicidad", "0"), ANGULO)
        conicidad2 = ctx.evaluar(p.get("conicidad2", "0"), ANGULO)
        kernel = _kernel_crear()
        avanzada = delgado or abs(conicidad) > 1e-9 or abs(conicidad2) > 1e-9 or hasta is not None or caja is not None
        if kernel is not None and hasattr(kernel, "extruir_avanzado") and avanzada:
            if hasta is not None and direccion == "simetrica":
                raise ErrorOperacion("«Al objeto» no se combina con la dirección simétrica.")
            forma = kernel.extruir_avanzado(caras, n, inicio_desfase=desfase, direccion=direccion, distancia1=d1,
                                            distancia2=d2, conicidad1=conicidad, conicidad2=conicidad2,
                                            medida_simetrica=medida, delgado=delgado,
                                            aristas=[e.forma for e in curvas] or None, hasta=hasta,
                                            hasta_modo=p.get("hasta_modo", "cara"),
                                            hasta_desfase=ctx.evaluar(p.get("desfase_hasta", "0")), hasta_caja=caja,
                                            inicio_plano=inclinado)
        elif avanzada:
            raise ErrorOperacion("Esta opción de extrusión todavía no está disponible.")
        else:
            if inclinado is not None:
                caras = [geo.proyectar_sobre_plano(c, n, inclinado) for c in caras]
            forma = _extrusion_basica(caras, n, d1, d2, direccion, medida, desfase)
        if not geo.esta_vacia(forma) and caras and all(cara_sin_area(c) for c in caras):
            raise ErrorOperacion("La extrusión no tiene volumen: el perfil elegido casi no tiene área.")
        return forma

    def _cuerpos_objetivo(self):
        """Los cuerpos de «Objetos para cortar», siempre como lista (vacía = automático)."""
        o = self._objetivo()
        return list(o) if isinstance(o, (list, tuple)) else ([o] if o else [])

    @staticmethod
    def _forma_objeto(e):
        if e.forma is not None:
            return e.forma
        if e.plano is not None:
            return geo.cara_de_plano(e.plano)
        raise ErrorOperacion("El objeto elegido no sirve como límite de la extrusión.")


def _exigir_cuerpo_con_volumen(estado, ids):
    """Un cuerpo que sale con volumen 0 (o menos) o con una forma inválida es un fallo del paso, no un resultado:
    extruir caras de distinta dirección dejaba un cuerpo de volumen 0 y el paso salía «ok» (B-164)."""
    for cid in ids:
        c = estado.cuerpos.get(cid)
        if c is None or getattr(c, "tipo", "solido") != "solido":
            continue
        if not geo.es_valida(c.forma):
            raise ErrorOperacion("La extrusión dejó un cuerpo con una forma inválida: revisá las caras elegidas "
                                 "y la distancia.")
        if geo.volumen_exacto(c.forma) <= 0:
            raise ErrorOperacion("La extrusión dejó un cuerpo sin volumen (0 o menos): revisá las caras elegidas "
                                 "y la distancia.")


def _extrusion_basica(caras, n, d1, d2, direccion, medida, desfase):
    geo.exigir_distancias_extrusion(direccion, d1, d2, medida)     # con el campo y el valor escritos
    if abs(desfase) > 1e-12:
        caras = [geo.trasladar(c, n * desfase) for c in caras]
    if direccion == "simetrica":
        return geo.extruir(caras, n, abs(d1) * (2 if medida == "mitad" else 1), simetrica=True)
    if direccion == "dos_lados":
        # Cada lado va al suyo (Fusion: «a unique extrusion on each side»): el número es una magnitud, su signo no
        # invierte el lado. Sin esto, un lado 2 negativo se perdía en la unión y con conicidad no.
        return geo.unir_todos([geo.extruir(caras, n, abs(d1)), geo.extruir(caras, -n, abs(d2))])
    return geo.extruir(caras, n, d1)


class OpRevolucion(_OpConPerfiles):
    """Revolución de Fusion [SLD-REVOLVE-SOLID]: eje (línea, arista, eje de construcción o de origen),
    tipo de extensión (ángulo, completa), dirección (un lado, dos lados, simétrica) y operación."""
    TIPO, ETIQUETA, ICONO = "revolucion", "Revolución", "↻"
    PARAMS = {"boceto": "", "perfiles": [], "caras": [], "eje": "v", "eje_ref": None, "extension": "angulo",
              "angulo": "360 deg", "direccion": "un_lado", "angulo2": "90 deg", "invertir": False,
              "operacion": "nuevo", "objetivo": "", "objetivos": [], "hasta": None,
              # El panel y la API arrancan con el eje proyectado (Fusion lo trae marcado); acá queda False: es lo
              # que calcula una receta guardada sin la clave, que tiene que abrir igual (docs/brechas_herramientas_solido.md › CAP-12).
              "proyectar_eje": False}
    EXPRESIONES = ("angulo", "angulo2")
    OPCIONES = {"extension": ("angulo", "completa", "objeto"), "direccion": DIRECCIONES, "operacion": OPERACIONES_CUERPO}

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

    def _hasta(self, estado):
        """El objeto de «A objeto» como lo entiende `solidos_crear.revolver_hasta`."""
        if not self.p.get("hasta"):
            raise ErrorOperacion("Elegí el vértice, el plano, la cara plana o el cuerpo hasta donde gira el perfil.")
        e = _resolver(self.p["hasta"], estado)
        if e.tipo in ("vertice", "punto", "punto_boceto"):
            return "punto", ent.como_punto(e)
        if e.plano is not None:
            return "plano", e.plano
        if e.tipo == "cuerpo" and e.forma is not None:
            return "forma", e.forma
        raise ErrorOperacion("El objeto de la revolución tiene que ser un vértice, un plano, una cara plana o un cuerpo.")

    def ejecutar(self, estado, ctx):
        plano, caras = self._caras(estado, ctx)
        punto, direccion = self._eje(estado, plano)
        if self.p.get("proyectar_eje"):         # «Eje de proyecto»: el eje se lleva al plano del perfil
            n = np.asarray(plano.normal, float)
            proyectado = np.asarray(direccion, float) - n * float(np.asarray(direccion, float) @ n)
            if np.linalg.norm(proyectado) >= 1e-9:   # eje perpendicular: no se proyecta, queda donde está
                punto = np.asarray(punto, float) - n * float((np.asarray(punto, float) - plano.origen) @ n)
                direccion = proyectado
        direccion = np.asarray(direccion, float) * (-1 if self.p.get("invertir") else 1)
        if self.p.get("extension") == "objeto":
            if self.p.get("direccion", "un_lado") != "un_lado":
                raise ErrorOperacion("«A objeto» gira hacia un solo lado: usá la dirección «Un lado».")
            kernel = _kernel_crear()
            if kernel is None or not hasattr(kernel, "revolver_hasta"):
                raise ErrorOperacion("«A objeto» todavía no está disponible con este motor geométrico.")
            forma = kernel.revolver_hasta(caras, punto, direccion, self._hasta(estado))
            self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, self.p["operacion"], self._objetivo()))
            return
        a1 = 360.0 if self.p.get("extension") == "completa" else ctx.evaluar(self.p["angulo"], ANGULO)
        modo = self.p.get("direccion", "un_lado")
        a2 = ctx.evaluar(self.p.get("angulo2", "0"), ANGULO) if modo == "dos_lados" and self.p.get("extension") != "completa" else 0.0
        if abs(a1) > 360.0 + 1e-9 or abs(a2) > 360.0 + 1e-9 or (modo == "dos_lados" and abs(a1) + abs(a2) > 360.0 + 1e-9):
            raise ErrorOperacion("El ángulo de revolución no puede pasar de 360° (en total): una vuelta completa ya cierra el sólido.")
        if modo == "simetrica" and self.p.get("extension") != "completa":
            caras = [geo.rotar(c, punto, direccion, -a1 / 2) for c in caras]
            forma = geo.revolver(caras, punto, direccion, a1)
        elif modo == "dos_lados" and self.p.get("extension") != "completa":
            # «Dos lados» elige el lado la dirección, no el signo: cada ángulo es una magnitud, como en
            # `revolver_avanzado`, en la revolución de superficie y en la Extrusión de dos lados.
            forma = geo.unir_todos([geo.revolver(caras, punto, direccion, abs(a1)),
                                    geo.revolver(caras, punto, -direccion, abs(a2))])
        else:
            forma = geo.revolver(caras, punto, direccion, a1)
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, self.p["operacion"], self._objetivo()))


class OpPrimitiva(Operacion):
    """Caja, Cilindro, Esfera y Toroide de Fusion (CREAR): primitiva con sus medidas y posición (x, y, z) como
    cuerpo nuevo o unida, cortada o intersecada con los cuerpos existentes.

    Caja: (x, y, z) es la esquina mínima; con caja_centrada (lo que guarda create_box) (x, y) es el centro de la
    base y z la base. ancho = tamaño en X, largo = en Y, alto = en Z.

    `plano` (referencia a un plano o una cara plana, o None): la primitiva se crea sobre ese plano, como en Fusion:
    (x, y) son coordenadas en el plano (ejes u y v), z la distancia sobre su normal y el eje de la caja, el cilindro
    y el toroide es la normal. Sin `plano`, (x, y, z) son coordenadas del mundo y el eje es Z."""
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
              "radio_mayor": "20 mm", "radio_menor": "5 mm", "posicion_toroide": "centro", "x": "0", "y": "0", "z": "0",
              "operacion": "nuevo", "objetivo": "", "caja_centrada": False, "plano": None}
    OPCIONES = {"forma": CAMPOS, "operacion": OPERACIONES_CUERPO, "posicion_toroide": ("interior", "centro", "exterior")}

    def __init__(self, id, nombre=None, suprimida=False, **params):
        forma = params.get("forma", "caja")
        if nombre is None:
            nombre = f"{self.ETIQUETAS.get(forma, 'Primitiva')} {id}"
        super().__init__(id, nombre, suprimida, **params)

    @property
    def icono(self):
        return self.ICONOS.get(self.p["forma"], "■")

    def dependencias(self):
        return super().dependencias() | _deps_objetivo(self.p.get("objetivo")) | ent.dependencias_de(self.p.get("plano"))

    def expresiones(self):
        return [self.p[k] for k in self.CAMPOS.get(self.p["forma"], []) + ["x", "y", "z"]]

    def claves_modelo(self):
        return list(self.CAMPOS.get(self.p["forma"], []))

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
            # Position de Fusion: el tubo va adentro, centrado o afuera del círculo de radio_mayor.
            lado = {"interior": -1, "centro": 0, "exterior": 1}[self.p.get("posicion_toroide", "centro")]
            forma = geo.toroide(v["radio_mayor"] + lado * v["radio_menor"], v["radio_menor"], pos)
        else:
            raise ErrorOperacion(f"Primitiva desconocida: {f}")
        if self.p.get("plano"):                 # sobre un plano o una cara cualquiera: del marco local al del plano
            pl = ent.como_plano(_resolver(self.p["plano"], estado))
            m = np.identity(4)
            m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = pl.u, pl.v, pl.normal, pl.origen
            forma = geo.transformar(forma, m)
        self._registrar_usados(aplicar_resultado(estado, ctx, self.id, forma, self.p["operacion"], self.p["objetivo"]))


class OpCombinar(Operacion):
    """Equivalente a CombineFeature: cuerpo objetivo + herramientas + operación + mantener herramientas."""
    TIPO, ETIQUETA, ICONO = "combinar", "Combinar", "⊕"
    PARAMS = {"objetivo": "", "herramientas": [], "operacion": "unir", "mantener": False}
    OPCIONES = {"operacion": OPERACIONES_COMBINAR}

    def dependencias(self):
        return _deps_objetivo(self.p.get("objetivo")) | _deps_objetivo(self.p.get("herramientas"))

    def _cortar_junto(self, ctx, objetivo, herramientas):
        """Cortar con varias herramientas en una sola pasada (T-20). None si no corresponde o el kernel no puede: se
        corta de a una, con sus reintentos y su mensaje por herramienta. Con menos de 5 no conviene: la comprobación
        ya corta con cada una, y en un cuerpo grande esa pasada de más pesa más que lo que se ahorra."""
        if self.p["operacion"] != "cortar" or len(herramientas) < 5:
            return None
        avisos = []
        try:
            resultado = geo.cortar_varias(objetivo.forma, [h.forma for h in herramientas], avisos)
        except geo.ErrorGeometria:
            return None
        for h in herramientas:
            if not geo.se_tocan(objetivo.forma, h.forma):
                ctx.aviso(f"{h.nombre} no toca a {objetivo.nombre}: no le cortó nada.")
        for texto in avisos:
            ctx.aviso(f"{objetivo.nombre}: {texto}")
        return resultado

    def ejecutar(self, estado, ctx):
        if not self.p["objetivo"] or not self.p["herramientas"]:
            raise ErrorOperacion("Elegí un cuerpo objetivo y al menos una herramienta.")
        objetivo = estado.cuerpo(self.p["objetivo"])
        herramientas = list({h.id: h for h in map(estado.cuerpo, self.p["herramientas"])}.values())   # B-127: sin repetidas
        if any(h.id == objetivo.id for h in herramientas):
            raise ErrorOperacion("El objetivo no puede ser también herramienta.")
        forma_objetivo = objetivo.forma
        junto = self._cortar_junto(ctx, objetivo, herramientas)
        resultado = forma_objetivo if junto is None else junto
        v_previa = None
        for h in herramientas if junto is None else ():
            if self.p["operacion"] == "cortar" and not geo.se_tocan(resultado, h.forma):
                ctx.aviso(f"{h.nombre} no toca a {objetivo.nombre}: no le cortó nada.")
            parcial = resultado
            avisos = []
            resultado = geo.booleano(resultado, h.forma, self.p["operacion"], avisos)
            if self.p["operacion"] == "unir":
                # Una unión no puede pesar menos que lo que ya había (B-52: la unión de la espiral
                # del motor descartaba un sólido entero del compuesto en silencio).
                if v_previa is None:
                    v_previa = geo.volumen(forma_objetivo)
                v_nueva = geo.volumen(resultado)
                if v_nueva < v_previa - max(v_previa, 1.0) * 5e-4:
                    ctx.aviso(f"{objetivo.nombre}: la unión con {h.nombre} perdió {v_previa - v_nueva:.2f} mm³ "
                              "de material (el kernel descartó geometría en un contacto degenerado); "
                              "revisalo con check_geometry.")
                v_previa = v_nueva
                # Tampoco puede quedar peor que las entradas (B-37/B-52): más sólidos que la suma de
                # las partes (explotó), partes que se tocaban y no se fusionaron (la espiral contra la
                # campana quedaba en 2 sólidos), o un resultado abierto. Unir cuerpos que NO se tocan
                # es legítimo (cuerpo multi-sólido): eso no avisa.
                n_antes = len(geo.solidos(parcial)) + len(geo.solidos(h.forma))
                n_despues = len(geo.solidos(resultado))
                if (n_despues > n_antes or (geo.se_tocan(parcial, h.forma) and n_despues == n_antes)
                        or not rv.es_estanca(resultado)):
                    ctx.aviso(f"{objetivo.nombre}: la unión con {h.nombre} dejó el cuerpo partido, sin "
                              "fusionar lo que se toca o abierto (posible contacto tangente o en cuña); "
                              "revisalo con check_geometry.")
                    avisos = []             # ya lo cubre el aviso de arriba
            for texto in avisos:
                ctx.aviso(f"{objetivo.nombre}: {texto}")
        if geo.esta_vacia(resultado):
            raise ErrorOperacion("El resultado quedó vacío (¿los cuerpos no se intersecan?).")
        if self.p["operacion"] == "unir":
            objetivo.forma = resultado
        else:
            poner_resultado(estado, ctx, self.id, objetivo, resultado)
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
    (["op1.c1"]): se congelan en ese momento. Las mallas no entran.

    Opcionales por cuerpo (los trae la apertura de un .f3d con componentes repetidos o movidos): "matriz" (16 números,
    matriz 4×4 por filas, en mm) mueve el B-rep a su lugar, y "ref" (id de un cuerpo anterior de este paso) en vez de
    "brep" toma el B-rep de ese cuerpo: es una copia LIGERA, comparte su geometría sin repetirla en el archivo
    (`solidos_crear.instanciar`). Sin estos campos el cuerpo queda tal cual está guardado."""
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
        locales = {}                                      # B-rep de cada cuerpo con "brep", en su propio lugar
        for d in self.p["cuerpos"]:
            if (not isinstance(d, dict) or not isinstance(d.get("id"), str)
                    or not (isinstance(d.get("brep"), str) or isinstance(d.get("ref"), str))):
                raise ParametroMalFormado(d, 'se esperaba un cuerpo congelado: {"id": "op1.c1", "brep": "…", …} (lo '
                                             'arma Crear operación base, no se escribe a mano)')
            if isinstance(d.get("brep"), str):
                local = locales[d["id"]] = intercambio.forma_de_texto(d["brep"])
            else:
                local = locales.get(d["ref"])
                if local is None:
                    raise ParametroMalFormado(d, f'"ref" apunta a «{d["ref"]}», que no es un cuerpo con "brep" '
                                                 'anterior de este mismo paso')
            forma = local if d.get("matriz") is None else _ubicar_cuerpo(local, d)
            if d["id"] in estado.cuerpos:
                estado.cuerpos[d["id"]].forma = forma
            else:
                estado.nuevo_cuerpo(self.id, forma, d.get("tipo", "solido"), nombre=d.get("nombre"),
                                    apariencia=d.get("apariencia"))


def _ubicar_cuerpo(forma, d):
    """`forma` movida por la "matriz" del cuerpo congelado `d` (copia ligera si el movimiento es rígido)."""
    m = d["matriz"]
    if not (isinstance(m, list) and len(m) == 16
            and all(type(x) in (int, float) and np.isfinite(x) and abs(x) < 1e6 for x in m)):   # 1e6 mm = 1 km
        raise ParametroMalFormado(d, '"matriz" tiene que ser una lista de 16 números finitos (matriz 4×4 por filas, '
                                     'en mm)')
    from ..nucleo import solidos_crear
    try:
        return solidos_crear.instanciar(forma, np.array(m, float).reshape(4, 4))
    except Exception as e:                                # noqa: BLE001 - OpenCascade lanza Standard_Failure
        raise ParametroMalFormado(d, f'"matriz" no es un movimiento válido ({e})') from None


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
        params["boceto"] = Boceto.desde_dict(d.get("boceto", {}))
    op = clase(d["id"], d.get("nombre"), d.get("suprimida", False), **params)
    ocultos = d.get("ocultos")
    op.ocultos = [i for i in ocultos if isinstance(i, str)] if isinstance(ocultos, list) else []
    return op


# Operaciones de los otros módulos (se registran al importarse; van al final por el import circular).
from . import (ops_calibracion, ops_chapa, ops_construir, ops_derivacion, ops_engranaje, ops_ensamblar, ops_fijacion,  # noqa: E402,F401
                ops_grafo, ops_insertar, ops_malla, ops_modificar, ops_revision, ops_solido, ops_superficie)
