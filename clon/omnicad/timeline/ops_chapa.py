# -*- coding: utf-8 -*-
"""
Operaciones del entorno CHAPA de Fusion [GUID-309ACAF1] (núcleo en `nucleo/chapa.py`).

Cada cuerpo de chapa es un `CuerpoChapa`: un `Cuerpo` común que además guarda `chapa`, el modelo de la pieza
(regla, patrón plano y pliegues; datos JSON), y `forma_chapa`, la forma que generó ese modelo. Las reglas viven
en la operación que crea el cuerpo (pestaña base o de contorno, convertir a chapa: params "regla" y "ajustes") y
en el modelo ("op_regla" dice qué operación las tiene). Los modelos se tratan como inmutables: cada operación
arma uno nuevo, así `copia()` los comparte sin riesgo. Si otra herramienta cambió la forma (un agujero
extruido, por ejemplo), la siguiente operación de chapa incorpora esos cortes a las partes planas.
"""
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Curve

from ..nucleo import chapa
from ..nucleo import geometria as geo
from . import entidades as ent
from .operaciones import (ANGULO, Cuerpo, ErrorOperacion, Operacion, ParametroMalFormado, _deps_objetivo, _resolver,
                          _resolver_todas, registrar_operacion)
from .parametros import ESCALAR, LONGITUD


class CuerpoChapa(Cuerpo):
    """Cuerpo de chapa (ver el docstring del módulo)."""
    chapa = None
    forma_chapa = None

    def copia(self):
        c = super().copia()
        c.__class__ = CuerpoChapa
        c.chapa, c.forma_chapa = self.chapa, self.forma_chapa
        return c


def es_chapa(cuerpo):
    """¿El cuerpo es de chapa (pieza plegable, no su patrón plano)?"""
    m = getattr(cuerpo, "chapa", None)
    return m is not None and not m.get("patron_de")


def es_patron_plano(cuerpo):
    """¿El cuerpo es un patrón plano? Como en Fusion, no es una pieza del modelo: se ve en su propio modo (Activar
    patrón plano) y no cuenta para interferencias, propiedades, exportar «todo» ni la lista de materiales."""
    m = getattr(cuerpo, "chapa", None)
    return m is not None and bool(m.get("patron_de"))


def cuerpos_del_modelo(estado):
    """Los cuerpos del estado sin los patrones planos."""
    return [c for c in estado.cuerpos.values() if not es_patron_plano(c)]


def modelo_actual(cuerpo, aviso=None):
    """Modelo de chapa del cuerpo, con los cortes que le hicieron otras herramientas ya incorporados."""
    m = getattr(cuerpo, "chapa", None)
    if m is None:
        raise ErrorOperacion(f"«{cuerpo.nombre}» no es un cuerpo de chapa: creálo con Pestaña o usá Convertir a "
                             "chapa.")
    if cuerpo.forma is not cuerpo.forma_chapa:
        m, avisos = chapa.absorber(m, cuerpo.forma)
        for a in avisos:
            if aviso is not None:
                aviso(a)
    return m


def _modelo(estado, ctx, cid):
    c = estado.cuerpo(cid)
    m = modelo_actual(c, ctx.aviso)
    if m.get("patron_de"):
        raise ErrorOperacion("El patrón plano no se edita: cambiá la pieza plegada.")
    return c, m


def _guardar(c, m):
    forma = chapa.solido(m)
    c.__class__ = CuerpoChapa
    c.chapa, c.forma_chapa, c.forma = m, forma, forma


def _cuerpo_nuevo(estado, op_id, m, forma=None, nombre=None, como=None):
    """Cuerpo de chapa nuevo: con el aspecto, material y componente de `como`, si se da; si no, con el material
    de la regla (como en Fusion, la regla de chapa trae el material)."""
    forma = chapa.solido(m) if forma is None else forma
    extra = {"material": m["regla"].get("material")} if como is None else {
        "apariencia": como.apariencia, "material": como.material, "componente": como.componente}
    cid = estado.nuevo_cuerpo(op_id, forma, "solido", nombre, **extra)
    c = estado.cuerpos[cid]
    c.__class__ = CuerpoChapa
    c.chapa, c.forma_chapa = m, forma
    return cid


def _ajustes(p, ctx):
    """Ajustes de la regla ("Override rules"): campo → valor (las medidas son expresiones)."""
    salida = {}
    for k, v in (p.get("ajustes") or {}).items():
        if v in (None, ""):
            continue
        salida[k] = v if k in ("alivio_forma", "esquina_forma") else ctx.evaluar(v, ESCALAR if k == "k" else LONGITUD)
    return salida


def _definicion(p):
    """La regla propia copiada en el paso («regla_propia», la de `chapa.definicion_regla`), si es la de `regla`.
    Si el nombre ya no coincide (alguien eligió otra regla de la biblioteca), manda el nombre."""
    d = p.get("regla_propia")
    if d is None:
        return None
    if not isinstance(d, dict):
        raise ParametroMalFormado(d, "tiene que ser un dict con la regla propia (espesor, k, material…) o null",
                                  "regla_propia")
    return d if d.get("nombre") == (p.get("regla") or chapa.REGLA_DEFECTO) else None


def _regla(p, ctx):
    """Regla de la operación: la de la biblioteca (`regla`) o la propia copiada en el paso, con sus ajustes."""
    return chapa.regla(p.get("regla") or chapa.REGLA_DEFECTO, _definicion(p), **_ajustes(p, ctx))


def _expresiones_ajustes(p):
    return [v for k, v in (p.get("ajustes") or {}).items() if k not in ("alivio_forma", "esquina_forma") and v]


def _extremos(arista):
    c = BRepAdaptor_Curve(arista)
    p, q = c.Value(c.FirstParameter()), c.Value(c.LastParameter())
    return np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])


def _por_cuerpo(ents, que):
    grupos = {}
    for e in ents:
        if e.cuerpo is None:
            raise ErrorOperacion(f"Elegí {que} de un cuerpo de chapa.")
        grupos.setdefault(e.cuerpo, []).append(e.forma)
    if not grupos:
        raise ErrorOperacion(f"Elegí {que}.")
    return grupos


class _OpChapa(Operacion):
    REFS = ()

    def dependencias(self):
        deps = super().dependencias() | ent.dependencias_de(*(self.p.get(k) for k in self.REFS))
        return (deps | _deps_objetivo(self.p.get("cuerpo"))) - {self.id, None}

    def expresiones(self):
        return [self.p[k] for k in self.EXPRESIONES if self.p.get(k)] + _expresiones_ajustes(self.p)


DIRECCIONES_CONTORNO = {"un_lado": "Un lado", "dos_lados": "Dos lados", "simetrica": "Simétrica"}


class OpPestana(_OpChapa):
    """CHAPA › CREAR › Pestaña [SM-REF-BASE-EDGE-CONTOUR-FLANGE]. tipo "base": perfiles cerrados → placa
    (orientación lado 1, lado 2 o centro); "contorno": curvas abiertas de un boceto → chapa plegada extruida
    (distancia, dirección); "arista": aristas de chapa → pestaña (altura, ángulo, referencia de altura, posición
    del pliegue, ancho, invertir y anular radio y alivio de la regla). La base y el contorno crean cuerpos nuevos
    con la regla elegida (`regla` + `ajustes`; una regla propia viaja copiada en `regla_propia`)."""
    TIPO, ETIQUETA, ICONO = "pestana", "Pestaña", "▭"
    PARAMS = {"tipo": "base", "perfiles": [], "curvas": [], "aristas": [], "orientacion": "lado1",
              "regla": chapa.REGLA_DEFECTO, "regla_propia": None, "ajustes": {}, "distancia": "20 mm",
              "direccion": "un_lado",
              "distancia2": "10 mm", "altura": "20 mm", "angulo": "90 deg", "referencia": "exterior",
              "posicion": "interior", "ancho": "completo", "ancho_distancia": "20 mm", "ancho1": "10 mm",
              "ancho2": "10 mm", "invertir": False, "anular": False, "radio": "", "alivio_forma": "",
              "alivio_ancho": "", "alivio_profundidad": ""}
    EXPRESIONES = ("distancia", "distancia2", "altura", "angulo", "ancho_distancia", "ancho1", "ancho2", "radio",
                   "alivio_ancho", "alivio_profundidad")
    OPCIONES = {"tipo": ("base", "contorno", "arista"), "orientacion": chapa.ORIENTACIONES,
                "direccion": DIRECCIONES_CONTORNO, "referencia": chapa.REFERENCIAS_ALTURA,
                "posicion": chapa.POSICIONES, "ancho": chapa.TIPOS_ANCHO,
                "alivio_forma": ("", *chapa.FORMAS_ALIVIO)}       # "": el alivio de la regla
    REFS = ("perfiles", "curvas", "aristas")

    def ejecutar(self, estado, ctx):
        tipo = self.p["tipo"]
        if tipo == "base":
            ents = _resolver_todas(self.p["perfiles"], estado)
            if not ents:
                raise ErrorOperacion("Elegí uno o más perfiles cerrados.")
            plano = self._plano_comun(ents)
            for m in chapa.pestana_base([e.forma for e in ents], plano, _regla(self.p, ctx), self.p["orientacion"]):
                m["op_regla"] = self.id
                _cuerpo_nuevo(estado, self.id, m)
        elif tipo == "contorno":
            ents = _resolver_todas(self.p["curvas"], estado)
            if not ents or any(e.tipo != "curva_boceto" for e in ents):
                raise ErrorOperacion("Elegí las curvas de un perfil abierto de boceto.")
            m = chapa.pestana_contorno([e.forma for e in ents], self._plano_comun(ents), _regla(self.p, ctx),
                                       ctx.evaluar(self.p["distancia"]), self.p["orientacion"],
                                       self.p["direccion"], ctx.evaluar(self.p["distancia2"]))
            m["op_regla"] = self.id
            _cuerpo_nuevo(estado, self.id, m)
        elif tipo == "arista":
            for cid, aristas in _por_cuerpo(_resolver_todas(self.p["aristas"], estado), "aristas").items():
                c, m = _modelo(estado, ctx, cid)
                p = self.p
                anular = bool(p.get("anular"))
                radio = ctx.evaluar(p["radio"]) if anular and p.get("radio") else None
                alivio = {"forma": p.get("alivio_forma") or None,
                          "ancho": ctx.evaluar(p["alivio_ancho"]) if anular and p.get("alivio_ancho") else None,
                          "profundidad": ctx.evaluar(p["alivio_profundidad"])
                          if anular and p.get("alivio_profundidad") else None} if anular else None
                m = chapa.pestana_arista(m, aristas, ctx.evaluar(p["altura"]), ctx.evaluar(p["angulo"], ANGULO),
                                         p["posicion"], p["referencia"], p["ancho"],
                                         ctx.evaluar(p["ancho_distancia"]), ctx.evaluar(p["ancho1"]),
                                         ctx.evaluar(p["ancho2"]), p["invertir"], radio, alivio)
                _guardar(c, m)
        else:
            raise ErrorOperacion(f"Tipo de pestaña desconocido: {tipo}")

    @staticmethod
    def _plano_comun(ents):
        plano = ents[0].plano
        if plano is None:
            raise ErrorOperacion("Los perfiles tienen que ser de un boceto.")
        for e in ents[1:]:
            if e.plano is None or abs(abs(float(e.plano.normal @ plano.normal)) - 1) > 1e-9 or \
                    abs(float((e.plano.origen - plano.origen) @ plano.normal)) > 1e-6:
                raise ErrorOperacion("Los perfiles tienen que estar en un mismo plano.")
        return plano


class OpDobladillo(_OpChapa):
    """CHAPA › CREAR › Dobladillo [SM-REF-HEM-FLANGE]: cerrado (plano), abierto o en lágrima (simplificada);
    longitud, separación, radio, posición (adyacente o tangente) e invertir."""
    TIPO, ETIQUETA, ICONO = "dobladillo", "Dobladillo", "⊐"
    PARAMS = {"aristas": [], "tipo": "cerrado", "longitud": "10 mm", "separacion": "", "radio": "",
              "posicion": "adyacente", "invertir": False}
    EXPRESIONES = ("longitud", "separacion", "radio")
    OPCIONES = {"tipo": chapa.TIPOS_DOBLADILLO, "posicion": ("adyacente", "tangente")}
    REFS = ("aristas",)

    def ejecutar(self, estado, ctx):
        p = self.p
        for cid, aristas in _por_cuerpo(_resolver_todas(p["aristas"], estado), "aristas").items():
            c, m = _modelo(estado, ctx, cid)
            m = chapa.dobladillo(m, aristas, p["tipo"], ctx.evaluar(p["longitud"]),
                                 ctx.evaluar(p["separacion"]) if p.get("separacion") else None,
                                 ctx.evaluar(p["radio"]) if p.get("radio") else None, p["posicion"], p["invertir"])
            _guardar(c, m)


class OpPlegar(_OpChapa):
    """CHAPA › CREAR › Plegar [GUID-D11BA900] (Fold): cara estacionaria (con el punto del clic, que dice qué lado
    queda fijo), líneas rectas de boceto sobre esa cara, ángulo, posición de la línea e invertir."""
    TIPO, ETIQUETA, ICONO = "plegar", "Plegado", "⌐"
    PARAMS = {"cara": None, "punto": None, "lineas": [], "angulo": "90 deg", "posicion": "centro", "invertir": False,
              "anular": False, "radio": ""}
    EXPRESIONES = ("angulo", "radio")
    OPCIONES = {"posicion": chapa.POSICIONES_LINEA}
    REFS = ("cara", "lineas")

    def ejecutar(self, estado, ctx):
        p = self.p
        if not p["cara"]:
            raise ErrorOperacion("Elegí la cara estacionaria.")
        e = _resolver(p["cara"], estado)
        ents = _resolver_todas(p["lineas"], estado)
        if any(x.eje is None for x in ents):
            raise ErrorOperacion("Las líneas de plegado tienen que ser rectas.")
        lineas = [_extremos(x.forma) for x in ents]
        if not lineas:
            raise ErrorOperacion("Elegí las líneas de plegado (rectas de un boceto sobre la cara).")
        c, m = _modelo(estado, ctx, e.cuerpo)
        radio = ctx.evaluar(p["radio"]) if p.get("anular") and p.get("radio") else None
        m = chapa.plegar(m, e.forma, lineas, ctx.evaluar(p["angulo"], ANGULO), p["posicion"], p["invertir"], radio,
                         None if p.get("punto") is None else np.asarray(p["punto"], float))
        _guardar(c, m)


class OpDesplegar(_OpChapa):
    """CHAPA › MODIFICAR › Desplegar / Volver a plegar [GUID-5125C823]. Desplegar: cara estacionaria (queda fija)
    y los pliegues elegidos (caras curvas) o todos. Volver a plegar: el cuerpo (y opcionalmente otra cara fija)."""
    TIPO, ETIQUETA, ICONO = "desplegar", "Desplegado", "⇱"
    PARAMS = {"modo": "desplegar", "cuerpo": "", "cara": None, "punto": None, "pliegues": [], "todos": True}
    OPCIONES = {"modo": ("desplegar", "replegar")}
    REFS = ("cara", "pliegues")

    def __init__(self, id, nombre=None, suprimida=False, **params):
        if nombre is None and params.get("modo") == "replegar":
            nombre = f"Replegado {id}"
        super().__init__(id, nombre, suprimida, **params)

    def ejecutar(self, estado, ctx):
        p = self.p
        e = _resolver(p["cara"], estado) if p.get("cara") else None
        cid = e.cuerpo if e is not None else p.get("cuerpo")
        if not cid:
            raise ErrorOperacion("Elegí la cara estacionaria." if p["modo"] == "desplegar" else "Elegí el cuerpo.")
        c, m = _modelo(estado, ctx, cid)
        punto = None if p.get("punto") is None else np.asarray(p["punto"], float)
        cara = e.forma if e is not None else None
        if p["modo"] == "replegar":
            m = chapa.replegar(m, cara, punto)
        else:
            bids = None
            if not p.get("todos") and p.get("pliegues"):
                bids = [chapa.pliegue_de_cara(m, x.forma) for x in _resolver_todas(p["pliegues"], estado)]
            m = chapa.desplegar(m, cara, punto, bids)
        _guardar(c, m)


UBICACIONES_PATRON = {"junto": "Al lado de la pieza", "en_lugar": "Sobre la cara estacionaria"}


class OpPatronPlano(_OpChapa):
    """CHAPA › CREAR › Crear patrón plano [GUID-7EBD9424]: cuerpo nuevo con la pieza desplegada sobre la cara
    estacionaria (o al lado de la pieza, sin tocarla a ella ni a los otros cuerpos que ya existen en ese punto
    del timeline). Guarda el modelo para exportar el DXF; no se edita con las herramientas de chapa."""
    TIPO, ETIQUETA, ICONO = "patron_plano", "Patrón plano", "▱"
    PARAMS = {"cara": None, "punto": None, "ubicacion": "en_lugar"}
    OPCIONES = {"ubicacion": UBICACIONES_PATRON}
    REFS = ("cara",)

    def ejecutar(self, estado, ctx):
        if not self.p["cara"]:
            raise ErrorOperacion("Elegí la cara estacionaria.")
        e = _resolver(self.p["cara"], estado, ("cara",))
        c, m = _modelo(estado, ctx, e.cuerpo)
        punto = None if self.p.get("punto") is None else np.asarray(self.p["punto"], float)
        fija = chapa.placa_de_cara(m, e.forma, punto)[0]
        forma = chapa.patron_plano(m, fija)
        if self.p.get("ubicacion", "junto") == "junto":
            eje = (np.array(m["marco"]) @ chapa.transformaciones(m)[fija])[:3, 0]
            forma = _al_lado(estado, c, forma, eje)
        patron = dict(m, patron_de=c.id, estacionaria=fija)
        _cuerpo_nuevo(estado, self.id, patron, forma, f"Patrón plano ({c.nombre})", como=c)


def _caja(cuerpo):
    """Caja envolvente ((x0, y0, z0), (x1, y1, z1)) de un cuerpo (también de malla); None si está vacío."""
    return cuerpo.forma.caja() if cuerpo.tipo == "malla" else geo.caja_envolvente(cuerpo.forma)


def _separacion(a, b, eje):
    """Cuánto correr la caja `b` a lo largo de `eje` para que quede 10 mm más allá de la caja `a`."""
    def extremos(caja):
        (x0, y0, z0), (x1, y1, z1) = caja
        proy = [float(np.dot((x, y, z), eje)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        return min(proy), max(proy)
    return extremos(a)[1] - extremos(b)[0] + 10.0


def _al_lado(estado, cuerpo, forma, eje):
    """`forma` corrida a lo largo de `eje` hasta quedar 10 mm más allá de `cuerpo` y sin solaparse con la caja de
    ningún otro cuerpo del estado. Cada cuerpo que estorba la empuja 10 mm más allá de él: la distancia crece en
    cada vuelta y un cuerpo ya salteado no vuelve a estorbar, así que termina."""
    caja = geo.caja_envolvente(forma)
    d = _separacion(_caja(cuerpo), caja, eje)
    otras = [x for x in (_caja(c) for c in estado.cuerpos.values()) if x is not None]
    while True:
        p0, p1 = np.asarray(caja[0]) + eje * d, np.asarray(caja[1]) + eje * d
        choca = next((x for x in otras if np.all(p0 < np.asarray(x[1]) - 1e-6) and
                      np.all(np.asarray(x[0]) + 1e-6 < p1)), None)
        if choca is None:
            return geo.trasladar(forma, eje * d)
        d = _separacion(choca, caja, eje)


class OpConvertirChapa(_OpChapa):
    """CHAPA › CREAR › Convertir a chapa [SM-TO-CONVERT-TO-SM]: una placa plana de espesor constante pasa a ser de
    chapa; el espesor se mide desde la cara elegida y reemplaza al de la regla plantilla (de la biblioteca o propia,
    copiada en `regla_propia`)."""
    TIPO, ETIQUETA, ICONO = "convertir_chapa", "Convertir a chapa", "⇄"
    PARAMS = {"cara": None, "regla": chapa.REGLA_DEFECTO, "regla_propia": None, "ajustes": {}}
    REFS = ("cara",)

    def ejecutar(self, estado, ctx):
        if not self.p["cara"]:
            raise ErrorOperacion("Elegí una cara plana ancha del cuerpo.")
        e = _resolver(self.p["cara"], estado, ("cara",))
        c = estado.cuerpo(e.cuerpo)
        if getattr(c, "chapa", None) is not None:
            raise ErrorOperacion(f"«{c.nombre}» ya es un cuerpo de chapa.")
        if c.tipo != "solido":
            raise ErrorOperacion("Solo se convierten cuerpos sólidos.")
        ajustes = {k: v for k, v in _ajustes(self.p, ctx).items() if k != "espesor"}   # el espesor se mide
        m = chapa.convertir(c.forma, e.forma, self.p.get("regla") or chapa.REGLA_DEFECTO, _definicion(self.p),
                            **ajustes)
        m["op_regla"] = self.id
        _guardar(c, m)
        c.material = m["regla"].get("material") or c.material      # el de la regla plantilla


MODOS_DESGARRO = {"cara": "Cara", "puntos": "Puntos"}


class OpDesgarro(_OpChapa):
    """CHAPA › MODIFICAR › Desgarro [SM-RIP]. modo "cara": quita la cara elegida (un pliegue o una parte plana);
    modo "puntos": ranura de ancho `separacion` (vacío = la de la regla) entre dos puntos del borde de la cara
    elegida, del lado 1, del lado 2 o centrada. Si la pieza queda partida, cada pedazo es un cuerpo."""
    TIPO, ETIQUETA, ICONO = "desgarro", "Desgarro", "⫽"
    PARAMS = {"modo": "cara", "cara": None, "puntos": [], "lado": "centro", "separacion": ""}
    EXPRESIONES = ("separacion",)
    OPCIONES = {"modo": MODOS_DESGARRO, "lado": chapa.ORIENTACIONES}
    REFS = ("cara", "puntos")

    def ejecutar(self, estado, ctx):
        p = self.p
        if not p["cara"]:
            raise ErrorOperacion("Elegí la cara.")
        e = _resolver(p["cara"], estado)
        c, m = _modelo(estado, ctx, e.cuerpo)
        if p["modo"] == "puntos":
            puntos = [ent.como_punto(x) for x in _resolver_todas(p["puntos"], estado)]
            partes = chapa.desgarrar(m, "puntos", puntos=puntos, lado=p["lado"],
                                     separacion=ctx.evaluar(p["separacion"]) if p.get("separacion") else None)
        else:
            partes = chapa.desgarrar(m, "cara", cara=e.forma)
        _guardar(c, partes[0])
        for x in partes[1:]:
            _cuerpo_nuevo(estado, self.id, x, como=c)
        if len(partes) > 1:
            ctx.aviso(f"La chapa quedó en {len(partes)} cuerpos.")


class OpUnirPlegando(_OpChapa):
    """CHAPA › MODIFICAR › Unir plegando [SM-REF-JOIN-BY-BEND]: dos aristas rectas de cuerpos de chapa distintos
    del mismo espesor; se agrega el pliegue que los une (radio de la regla o anulado) y quedan en un cuerpo."""
    TIPO, ETIQUETA, ICONO = "unir_plegando", "Unión por pliegue", "⌒"
    PARAMS = {"aristas": [], "anular": False, "radio": ""}
    EXPRESIONES = ("radio",)
    REFS = ("aristas",)

    def ejecutar(self, estado, ctx):
        ents = _resolver_todas(self.p["aristas"], estado)
        if len(ents) != 2 or ents[0].cuerpo == ents[1].cuerpo or None in (ents[0].cuerpo, ents[1].cuerpo):
            raise ErrorOperacion("Elegí dos aristas, una de cada cuerpo de chapa.")
        ca, ma = _modelo(estado, ctx, ents[0].cuerpo)
        cb, mb = _modelo(estado, ctx, ents[1].cuerpo)
        radio = ctx.evaluar(self.p["radio"]) if self.p.get("anular") and self.p.get("radio") else None
        _guardar(ca, chapa.unir_plegando(ma, ents[0].forma, mb, ents[1].forma, radio))
        del estado.cuerpos[cb.id]


def exportar_dxf(estado, cid, ruta, centros=True, extensiones=False):
    """Exporta el patrón plano del cuerpo de chapa (o de su patrón plano) a DXF. Devuelve la ruta."""
    c = estado.cuerpo(cid)
    return chapa.exportar_dxf(modelo_actual(c), ruta, centros, extensiones)


registrar_operacion(OpPestana, OpDobladillo, OpPlegar, OpDesplegar, OpPatronPlano, OpConvertirChapa, OpDesgarro,
                    OpUnirPlegando)
