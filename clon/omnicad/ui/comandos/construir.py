# -*- coding: utf-8 -*-
"""Comandos de CONSTRUIR (planos, ejes, puntos y SCU) con diálogo al estilo Fusion."""
from ...timeline.operaciones import OpPlano
from ...timeline.ops_construir import TIPOS_EJE, TIPOS_PLANO, TIPOS_PUNTO, OpEje, OpPunto, OpSCU
from ...timeline.parametros import ANGULO, ESCALAR
from ..comando import Comando, ErrorComando, Expresion, Seleccion, hit_desde_ref, hits, ref1
from . import registrar

PLANO = {"plano", "cara_plana"}
EJE = {"eje", "arista_lineal"}
PUNTO = {"vertice", "punto"}
ARISTA = {"arista", "curva_boceto"}

# tipo → (clase de op, título, ícono, [(clave, etiqueta, filtros, obligatoria)], [campos de valor])
DEFINICIONES = {
    "plano_desfase": (OpPlano, "desfase", "plano_desfase", [("r0", "Plano", PLANO, True)],
                      [("distancia", "Distancia", "10 mm", None)]),
    "plano_angulo": (OpPlano, "angulo", "plano_angulo", [("r0", "Línea", EJE | {"curva_boceto"}, True)],
                     [("angulo", "Ángulo", "0 deg", ANGULO)]),
    "plano_tangente": (OpPlano, "tangente", "plano_tangente", [("r0", "Cara", {"cara"}, True),
                                                              ("r1", "Plano de referencia", PLANO, False)],
                       [("angulo", "Ángulo", "0 deg", ANGULO)]),
    "plano_medio": (OpPlano, "medio", "plano_medio", [("r0", "Plano 1", PLANO, True), ("r1", "Plano 2", PLANO, True)],
                    []),
    "plano_dos_aristas": (OpPlano, "dos_aristas", "plano_dos_aristas",
                          [("r0", "Línea 1", EJE | {"curva_boceto"}, True), ("r1", "Línea 2", EJE | {"curva_boceto"}, True)],
                          []),
    "plano_tres_puntos": (OpPlano, "tres_puntos", "plano_tres_puntos",
                          [("r0", "Punto 1", PUNTO, True), ("r1", "Punto 2", PUNTO, True), ("r2", "Punto 3", PUNTO, True)],
                          []),
    "plano_perpendicular": (OpPlano, "perpendicular", "plano_perpendicular",
                            [("r0", "Cara o arista", {"cara", "plano"} | ARISTA, True), ("r1", "Punto", PUNTO, True)], []),
    "plano_ruta": (OpPlano, "ruta", "plano_ruta", [("r0", "Ruta", ARISTA, True)],
                   [("posicion", "Distancia (0 a 1)", "0.5", ESCALAR)]),
    "eje_cilindro": (OpEje, "cilindro", "eje_cilindro", [("r0", "Cara", {"cara"}, True)], []),
    "eje_perpendicular": (OpEje, "perpendicular_cara", "eje_perpendicular",
                          [("r0", "Cara", {"cara", "plano"}, True), ("r1", "Punto", PUNTO, True)], []),
    "eje_dos_planos": (OpEje, "dos_planos", "eje_dos_planos", [("r0", "Plano 1", PLANO, True),
                                                               ("r1", "Plano 2", PLANO, True)], []),
    "eje_dos_puntos": (OpEje, "dos_puntos", "eje_dos_puntos", [("r0", "Punto 1", PUNTO, True),
                                                               ("r1", "Punto 2", PUNTO, True)], []),
    "eje_arista": (OpEje, "arista", "eje_arista", [("r0", "Arista", EJE | {"curva_boceto"}, True)], []),
    "punto_vertice": (OpPunto, "vertice", "punto_vertice", [("r0", "Vértice", PUNTO, True)], []),
    "punto_dos_aristas": (OpPunto, "dos_aristas", "punto_dos_aristas", [("r0", "Arista 1", ARISTA | {"eje"}, True),
                                                                        ("r1", "Arista 2", ARISTA | {"eje"}, True)], []),
    "punto_tres_planos": (OpPunto, "tres_planos", "punto_tres_planos",
                          [("r0", "Plano 1", PLANO, True), ("r1", "Plano 2", PLANO, True), ("r2", "Plano 3", PLANO, True)],
                          []),
    "punto_centro": (OpPunto, "centro", "punto_centro", [("r0", "Círculo/esfera/toroide",
                                                          {"arista_circular", "cara", "curva_boceto"}, True)], []),
    "punto_arista_plano": (OpPunto, "arista_plano", "punto_arista_plano",
                           [("r0", "Arista", EJE | {"curva_boceto"}, True), ("r1", "Plano", PLANO, True)], []),
    "punto_ruta": (OpPunto, "ruta", "punto_ruta", [("r0", "Ruta", ARISTA, True)],
                   [("posicion", "Distancia (0 a 1)", "0.5", ESCALAR)]),
}
def _titulo(clave, clase, tipo):
    if clase is OpPlano:
        return TIPOS_PLANO[tipo]
    if clase is OpEje:
        return TIPOS_EJE[tipo]
    return TIPOS_PUNTO[tipo]


def _crear_clase(clave, clase, tipo, ico, selecciones, valores):
    base_nombre = {OpPlano: "Plano", OpEje: "Eje", OpPunto: "Punto"}[clase]

    class _Construir(Comando):
        CLAVE, TITULO, ICONO = clave, _titulo(clave, clase, tipo), ico
        AYUDA = f"CONSTRUIR › {_titulo(clave, clase, tipo)}."
        CLASE_OP = clase
        TIPO_CONSTR = tipo

        def campos(self, ctx):
            salida = [Seleccion(k, et, f, minimo=1 if obl else 0) for k, et, f, obl in selecciones]
            salida += [Expresion(k, et, defecto, t or "longitud") for k, et, defecto, t in valores]
            return salida

        def construir(self, v, ctx):
            lista = []
            for k, et, _f, obligatoria in selecciones:
                r = ref1(v, k)
                if r is None and obligatoria:
                    raise ErrorComando(f"Seleccioná: {et.lower()}.")
                if r is not None:
                    lista.append(r)
            for k, _et, _d, t in valores:
                ctx.evaluar(v[k], t or "longitud")
            params = {"tipo": tipo, "refs": lista}
            params.update({k: v[k] for k, *_ in valores})
            return self.crear_op(clase, v, ctx, **params)

        def desde_op(self, op, ctx):
            v = dict(op.p)
            lista = op.p.get("refs") or []
            if clase is OpPlano and not lista and op.p.get("base") and op.p.get("base") != "cara":
                lista = [{"tipo": "plano", "id": op.p["base"]}]       # proyectos viejos (base/marco)
            for (k, *_), ref in zip(selecciones, lista, strict=False):
                v[k] = [hit_desde_ref(ref, ctx.estado)]
            return v

        def nombre_nuevo(self, ctx):
            usados = {o.nombre for o in ctx.doc.operaciones}
            n = 1
            while f"{base_nombre}{n}" in usados:
                n += 1
            return f"{base_nombre}{n}"

    _Construir.__name__ = f"Construir_{clave}"
    if clase is OpPlano and tipo == "desfase":
        _Construir.manipuladores = _manipuladores_plano_desfase
    return _Construir


def _manipuladores_plano_desfase(self, ctx, v):
    """Flecha de distancia desde el centro del plano o de la cara de referencia, por su normal."""
    from ...timeline import entidades as ent
    from .. import manipuladores as mp
    e = mp.entidad(v["r0"][0], ctx.estado) if v.get("r0") else None
    if e is None:
        return []
    try:
        plano = ent.como_plano(e)
        centro = ent.como_punto(e) if e.tipo == "cara" else plano.origen
    except Exception:  # noqa: BLE001
        return []
    return [mp.Flecha("distancia", centro, plano.normal)]


COMANDOS = [_crear_clase(k, *d) for k, d in DEFINICIONES.items()]
CATALOGO_LOCAL = {c.CLAVE: c for c in COMANDOS}


class SCU(Comando):
    CLAVE, TITULO, ICONO = "scu", "Sistema de coordenadas de usuario (SCU)", "scu"
    AYUDA = "Crea un sistema de coordenadas con su origen, ejes y planos."
    CLASE_OP = OpSCU

    def campos(self, ctx):
        return [Seleccion("origen", "Origen", PUNTO), Seleccion("eje_x", "Eje X", EJE | {"curva_boceto"}),
                Seleccion("eje_y", "Eje Y", EJE | {"curva_boceto"}, minimo=0),
                Expresion("dx", "Desfase X", "0 mm"), Expresion("dy", "Desfase Y", "0 mm"),
                Expresion("dz", "Desfase Z", "0 mm"), Expresion("rx", "Ángulo X", "0 deg", ANGULO),
                Expresion("ry", "Ángulo Y", "0 deg", ANGULO), Expresion("rz", "Ángulo Z", "0 deg", ANGULO)]

    def construir(self, v, ctx):
        if not v.get("origen"):
            raise ErrorComando("Seleccioná el origen.")
        return self.crear_op(OpSCU, v, ctx, origen=ref1(v, "origen"), eje_x=ref1(v, "eje_x"), eje_y=ref1(v, "eje_y"),
                             **{k: v[k] for k in ("dx", "dy", "dz", "rx", "ry", "rz")})

    def desde_op(self, op, ctx):
        v = dict(op.p)
        for k in ("origen", "eje_x", "eje_y"):
            v[k] = hits([op.p[k]], ctx.estado) if op.p.get(k) else []
        return v

    def nombre_nuevo(self, ctx):
        usados = {o.nombre for o in ctx.doc.operaciones}
        n = 1
        while f"SCU{n}" in usados:
            n += 1
        return f"SCU{n}"


registrar(*COMANDOS, SCU)
# Editar un plano/eje/punto abre el comando de SU tipo (no el primero registrado para la clase).
POR_TIPO_CONSTRUCCION = {(c.CLASE_OP.TIPO, c.TIPO_CONSTR): c for c in COMANDOS}
