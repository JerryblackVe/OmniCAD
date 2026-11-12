# -*- coding: utf-8 -*-
"""Comandos de ENSAMBLAR: nuevo componente, unión, unión como está, origen de unión, grupo rígido,
accionar uniones, vínculo de movimiento y fijar componente."""
from ...timeline.operaciones import ErrorOperacion
from ...timeline.ops_ensamblar import (CLAVES_MOVIMIENTO, MODOS_POSICION, MOVIMIENTOS, TIPOS_UNION, OpAnclar,
                                       OpCapturarPosicion, OpComponente, OpGrupoRigido, OpOrigenUnion,
                                       OpPosicionInicial, OpRestriccion, OpRevertirPosicion, OpUnion, OpVinculoMovimiento,
                                       _clave_movimiento, componente_por_ref, direccion_eje, eje_local, ejes_bola,
                                       exigir_numero, marco_desde, pose_de_componente, pose_de_reasignar, principal_de, ruta_componente,
                                       siguiente_accion)
from ...timeline.parametros import ANGULO
from ..comando import (Casilla, Comando, ErrorComando, Expresion, ListaSeleccion, Opciones, OpcionesVivas, Personalizado,
                       Seleccion, exigir, hit_desde_ref, hits_cuerpos as _hits_cuerpos, ref1, refs)
from . import registrar

SNAP = {"cara", "arista", "vertice", "plano", "eje", "punto", "curva_boceto"}
EJE_PROPIO = {"arista", "eje", "cara", "curva_boceto"}      # un eje de movimiento propio: arista, eje de construcción, cilindro
NOMBRE_MOVIMIENTO = {"giro": "Giro", "giro2": "Giro 2 (cabeceo)", "giro3": "Giro 3 (guiñada)",
                     "desliz": "Deslizamiento", "desliz2": "Deslizamiento 2"}


def _ref(v, clave):
    """La referencia elegida en un campo de selección opcional (None si está vacío o ni existe: una receta vieja)."""
    lista = v.get(clave) or []
    return lista[0]["ref"] if lista else None


def _numero(valor):
    """«nan» e «inf» no son números: el panel lo dice (ASM-6) en vez de «Nombre desconocido»."""
    try:
        exigir_numero(valor)
    except ErrorOperacion as e:
        raise ErrorComando(str(e)) from e
EJES = {"Z": "Z", "X": "X", "Y": "Y"}
CLAVES = {"centro": "Centro / punto medio", "inicio": "Inicio (arista o cilindro)", "fin": "Fin (arista o cilindro)"}


def _version(ctx, clase, clave):
    """Al editar, la versión de cálculo del paso (una receta vieja no cambia de marco); un paso nuevo usa
    la actual (la de PARAMS)."""
    return ctx.op.p.get(clave, 1) if ctx.op is not None else clase.PARAMS[clave]


def _gira(v):
    return bool(MOVIMIENTOS[v.get("tipo", "rigida")][0])


def _desliza(v):
    return bool(MOVIMIENTOS[v.get("tipo", "rigida")][1])


def _campos_movimiento():
    """La pestaña Motion de Fusion (Joint reference): el Tipo, los ejes de Rotation/Translation con su eje propio al
    lado y después los valores; los límites van a «Más opciones»."""
    t = lambda *tipos: (lambda v: v.get("tipo") in tipos)  # noqa: E731
    return [
        Opciones("tipo", "Tipo de movimiento", TIPOS_UNION),
        Opciones("eje_giro", "Eje de giro", EJES, visible_si=t("revolucion", "cilindrica", "pasador_ranura", "planar"),
                 etiqueta_si=lambda v: "Normal del plano" if v.get("tipo") == "planar" else "Eje de giro"),
        Seleccion("ref_eje_giro", "Eje de giro propio", EJE_PROPIO, minimo=0,
                  visible_si=t("revolucion", "cilindrica", "pasador_ranura", "planar", "bola"),
                  ayuda="Una arista, un eje de construcción o un cilindro en vez de X, Y o Z del marco."),
        Opciones("eje_desliz", "Eje de deslizamiento", {"X": "X", "Y": "Y", "Z": "Z"}, "X",
                 visible_si=t("deslizante", "pasador_ranura")),
        Seleccion("ref_eje_desliz", "Eje de deslizamiento propio", EJE_PROPIO, minimo=0,
                  visible_si=t("deslizante", "pasador_ranura"),
                  ayuda="Una arista, un eje de construcción o un cilindro en vez de X, Y o Z del marco."),
        Opciones("eje_cabeceo", "Eje de cabeceo (Pitch)", {"": "Automático (Y)", **EJES}, "", visible_si=t("bola"),
                 ayuda="El eje lateral de la bola: el «Ángulo 2» gira sobre él."),
        Seleccion("ref_eje_cabeceo", "Eje de cabeceo propio", EJE_PROPIO, minimo=0, visible_si=t("bola"),
                  ayuda="Una arista, un eje de construcción o un cilindro en vez de X, Y o Z del marco."),
        Opciones("eje_guinada", "Eje de guiñada (Yaw)", {"": "Automático (X)", **EJES}, "", visible_si=t("bola"),
                 ayuda="El eje perpendicular al de cabeceo: el «Ángulo 3» gira sobre él. El balanceo (Roll, «Ángulo de "
                       "giro») sale solo de los dos."),
        Seleccion("ref_eje_guinada", "Eje de guiñada propio", EJE_PROPIO, minimo=0, visible_si=t("bola"),
                  ayuda="Una arista, un eje de construcción o un cilindro en vez de X, Y o Z del marco."),
        Expresion("giro", "Ángulo de giro", "0 deg", ANGULO, visible_si=_gira),
        Expresion("giro2", "Ángulo 2 (cabeceo)", "0 deg", ANGULO, visible_si=t("bola")),
        Expresion("giro3", "Ángulo 3 (guiñada)", "0 deg", ANGULO, visible_si=t("bola")),
        Expresion("desliz", "Distancia", "0 mm", visible_si=_desliza),
        Expresion("desliz2", "Distancia 2", "0 mm", visible_si=t("planar")),
        Expresion("minimo", "Límite mínimo", "", visible_si=lambda v: _gira(v) or _desliza(v), avanzado=True),
        Expresion("maximo", "Límite máximo", "", visible_si=lambda v: _gira(v) or _desliza(v), avanzado=True),
    ] + _campos_limites()


def _tiene(clave):
    return lambda v: clave in sum(MOVIMIENTOS[v.get("tipo", "rigida")], [])


def _campos_limites():
    """Límites de cada movimiento (ASM-12): los del principal están en «Límite mínimo / máximo»; los demás, su reposo y
    «Invertir» van acá."""
    campos = []
    for clave in CLAVES_MOVIMIENTO:
        tipo, nombre = (ANGULO if clave.startswith("giro") else "longitud"), NOMBRE_MOVIMIENTO[clave]
        otro = lambda v, c=clave: _tiene(c)(v) and principal_de(v.get("tipo", "rigida")) != c  # noqa: E731
        campos += [Expresion(f"min_{clave}", f"Límite mínimo · {nombre}", "", tipo, visible_si=otro, avanzado=True),
                   Expresion(f"max_{clave}", f"Límite máximo · {nombre}", "", tipo, visible_si=otro, avanzado=True),
                   Expresion(f"reposo_{clave}", f"Reposo · {nombre}", "", tipo, visible_si=_tiene(clave),
                             avanzado=True),
                   Casilla(f"inv_{clave}", f"Invertir límites · {nombre}", visible_si=_tiene(clave), avanzado=True)]
    return campos


def _limites_dof(v):
    """`limites_dof` de la unión desde los campos de límites del panel."""
    tipo, salida = v.get("tipo", "rigida"), {}
    for clave in sum(MOVIMIENTOS[tipo], []):
        e = {}
        if clave != principal_de(tipo):
            e.update(minimo=v.get(f"min_{clave}") or "", maximo=v.get(f"max_{clave}") or "")
        if str(v.get(f"reposo_{clave}") or "").strip():
            e["reposo"] = v[f"reposo_{clave}"]
        if v.get(f"inv_{clave}"):
            e["invertir"] = True
        if any(e.values()):
            salida[clave] = e
    return salida


def _campos_de_limites(p):
    """Al revés de `_limites_dof`: los campos del panel desde `limites_dof` de la unión."""
    salida = {}
    for clave, e in (p.get("limites_dof") or {}).items():
        if clave != principal_de(p["tipo"]):
            salida.update({f"min_{clave}": e.get("minimo", ""), f"max_{clave}": e.get("maximo", "")})
        salida.update({f"reposo_{clave}": e.get("reposo", ""), f"inv_{clave}": bool(e.get("invertir"))})
    return salida


def _validar(v, ctx):
    for k in ("giro", "giro2", "giro3", "desliz", "desliz2", "dx", "dy", "dz", "angulo", "minimo", "maximo"):
        _numero(v.get(k))
    for k in ("giro", "giro2", "giro3"):
        ctx.evaluar(v.get(k) or "0", ANGULO)
    for k in ("desliz", "desliz2", "dx", "dy", "dz"):
        if k in v:
            ctx.evaluar(v.get(k) or "0")


_MOVIMIENTO = ("tipo", "eje_giro", "eje_desliz", "eje_cabeceo", "eje_guinada", "giro", "giro2", "giro3", "desliz",
               "desliz2", "minimo", "maximo")


class NuevoComponente(Comando):
    CLAVE, TITULO, ICONO = "nuevo_componente", "Nuevo componente", "nuevo_componente"
    AYUDA = "Crea un componente con los cuerpos elegidos (las uniones mueven componentes)."
    CLASE_OP = OpComponente

    def campos(self, ctx):
        # «Parent» de Fusion (ASM-9): la raíz o cualquier componente anterior en el timeline, con su camino en un
        # subensamblaje (`ctx.estado` es el estado ANTES del paso: ni él ni sus hijos pueden ser su padre).
        padres = {"": "(raíz)", **{k: ruta_componente(ctx.estado, k) for k in ctx.estado.componentes}}
        return [Seleccion("cuerpos", "Cuerpos", {"cuerpo"}, maximo=None), Opciones("padre", "Padre", padres, ""),
                Casilla("fijo", "Fijo")]

    def construir(self, v, ctx):
        exigir(v, "cuerpos", "Seleccioná los cuerpos del componente.")
        cuerpos = [h["ref"]["cuerpo"] for h in v["cuerpos"]]
        # B-123: la pose se congela contra el estado en que se eligieron los cuerpos. Al editar, el de antes del
        # paso; un paso nuevo vale el actual (el estado del panel puede haber quedado viejo si cambió el documento).
        estado = ctx.estado if ctx.op is not None else ctx.doc.estado_final
        pose_padre = pose_de_componente(estado, v.get("padre") or "").tolist()
        if ctx.op is not None and v.get("pose_padre") is not None:
            try:        # B-353: con el mismo padre, la pose guardada vale: recalcularla con el padre ya movido separaba al hijo
                antes = componente_por_ref(estado, ctx.op.p["padre"]) if ctx.op.p.get("padre") else ""
            except ErrorOperacion:
                antes = None
            if antes == (v.get("padre") or ""):
                pose_padre = v["pose_padre"]
        return self.crear_op(OpComponente, v, ctx, cuerpos=cuerpos,
                             fijo=v["fijo"], padre=v.get("padre") or "",
                             version_pose=_version(ctx, OpComponente, "version_pose"),
                             pose=pose_de_reasignar(estado, cuerpos).tolist(),
                             pose_padre=pose_padre)

    def desde_op(self, op, ctx):
        try:
            padre = componente_por_ref(ctx.estado, op.p["padre"]) if op.p.get("padre") else ""
        except ErrorOperacion:                 # un nombre repetido de una receta a mano: el panel abre igual
            padre = ""
        return dict(op.p, cuerpos=_hits_cuerpos(op.p["cuerpos"], ctx.estado), padre=padre or "")


class Union(Comando):
    CLAVE, TITULO, ICONO, ATAJO = "union", "Unión", "union", "J"
    AYUDA = "Pone el componente 1 sobre el componente 2 y define cómo se mueven."
    CLASE_OP = OpUnion
    COMO_ESTA = False

    def verificar(self, ctx):
        return None if ctx.estado.componentes else "Primero creá componentes (ENSAMBLAR › Nuevo componente)."

    def campos(self, ctx):
        simple = lambda lado: (lambda v: v.get(f"modo{lado}", "simple") == "simple")  # noqa: E731
        otro = lambda lado: (lambda v: v.get(f"modo{lado}", "simple") != "simple")  # noqa: E731
        campos = [Opciones("modo1", "Modo del origen 1", MODOS_POSICION),
                  Seleccion("origen1", "Componente 1: ajuste", SNAP),
                  Seleccion("origen1b", "Componente 1: segundo ajuste", SNAP, visible_si=otro(1),
                            ayuda="La segunda cara o la segunda arista del modo elegido."),
                  Opciones("clave1", "Punto de ajuste 1", CLAVES, visible_si=simple(1))]
        if self.COMO_ESTA:
            campos += [Seleccion("origen2", "Componente 2", {"cuerpo"}, ayuda="Elegí un cuerpo del componente 2.")]
        else:
            campos += [Opciones("modo2", "Modo del origen 2", MODOS_POSICION),
                       Seleccion("origen2", "Componente 2: ajuste", SNAP),
                       Seleccion("origen2b", "Componente 2: segundo ajuste", SNAP, visible_si=otro(2),
                                 ayuda="La segunda cara o la segunda arista del modo elegido."),
                       Opciones("clave2", "Punto de ajuste 2", CLAVES, visible_si=simple(2)),
                       Expresion("angulo", "Ángulo de ajuste", "0 deg", ANGULO),
                       Expresion("dx", "Desfase X", "0 mm", avanzado=True),
                       Expresion("dy", "Desfase Y", "0 mm", avanzado=True),
                       Expresion("dz", "Desfase Z", "0 mm", avanzado=True), Casilla("voltear", "Voltear", avanzado=True)]
        return campos + _campos_movimiento()      # la pestaña Position de Fusion primero; Motion (con el Tipo) después

    def construir(self, v, ctx):
        exigir(v, "origen1", "Seleccioná el origen en el componente 1.")
        exigir(v, "origen2", "Seleccioná un cuerpo del componente 2." if self.COMO_ESTA else
               "Seleccioná el origen en el componente 2.")
        for lado in (1,) if self.COMO_ESTA else (1, 2):
            if v.get(f"modo{lado}", "simple") != "simple":
                exigir(v, f"origen{lado}b", f"Seleccioná el segundo ajuste del componente {lado}.")
        _validar(v, ctx)
        params = {k: v.get(k) for k in _MOVIMIENTO}
        params.update(origen1=ref1(v, "origen1"), clave1=v.get("clave1", "centro"), como_esta=self.COMO_ESTA,
                      origen2=ref1(v, "origen2"), version_marco=_version(ctx, OpUnion, "version_marco"),
                      modo1=v.get("modo1", "simple"), origen1b=_ref(v, "origen1b"), modo2=v.get("modo2", "simple"),
                      origen2b=_ref(v, "origen2b"), ref_eje_giro=_ref(v, "ref_eje_giro"),
                      ref_eje_desliz=_ref(v, "ref_eje_desliz"), limites_dof=_limites_dof(v),
                      ref_eje_cabeceo=_ref(v, "ref_eje_cabeceo"), ref_eje_guinada=_ref(v, "ref_eje_guinada"))
        if v.get("modo1", "simple") == "simple":
            params["origen1b"] = None
        if self.COMO_ESTA or v.get("modo2", "simple") == "simple":
            params["origen2b"] = None
        if not self.COMO_ESTA:
            params.update({k: v.get(k) for k in ("angulo", "dx", "dy", "dz", "voltear", "clave2")})
        return self.crear_op(OpUnion, v, ctx, **params)

    def desde_op(self, op, ctx):
        v = dict(op.p)
        for k in ("origen1", "origen2", "origen1b", "origen2b", "ref_eje_giro", "ref_eje_desliz", "ref_eje_cabeceo",
                  "ref_eje_guinada"):
            v[k] = [hit_desde_ref(op.p[k], ctx.estado)] if op.p.get(k) else []
        v.update(_campos_de_limites(op.p))
        return v


class RestriccionComponentes(Comando):
    CLAVE, TITULO, ICONO = "restriccion_componentes", "Restricción de componentes", "restriccion_componentes"
    AYUDA = ("Posiciona el componente 1 respecto del 2 (Constrain Components). Alinear: caras coplanares, ejes "
             "concéntricos o puntos coincidentes. Ángulo: gira el 1 hasta el ángulo pedido con el 2. Faltan Centro y Tangente.")
    CLASE_OP = OpRestriccion

    def verificar(self, ctx):
        return None if ctx.estado.componentes else "Primero creá componentes (ENSAMBLAR › Nuevo componente)."

    def campos(self, ctx):
        alinear = lambda v: v.get("tipo", "alinear") == "alinear"  # noqa: E731
        return [Opciones("tipo", "Tipo", {"alinear": "Alinear", "angulo": "Ángulo"}),
                Seleccion("ref1", "Componente 1: geometría", SNAP, ayuda="La cara, arista, vértice, plano, eje o punto que se mueve."),
                Seleccion("ref2", "Componente 2: geometría", SNAP, ayuda="A lo que se alinea; si el 1 está fijo, se mueve este."),
                Seleccion("ref_angulo", "Referencia de ángulo", {"arista", "eje", "curva_boceto"}, minimo=0, visible_si=lambda v: not alinear(v),
                          ayuda="Una arista recta o un eje: el ángulo se mide alrededor de él y queda con signo (sin él, de 0 a 180°)."),
                Expresion("desfase", "Desfase", "0 mm", visible_si=alinear,
                          ayuda="Entre dos planos, la distancia; entre dos ejes, el corrimiento sobre el eje."),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO, visible_si=lambda v: not alinear(v),
                          ayuda="El ángulo entre las dos geometrías (entre caras, el de sus normales)."),
                Casilla("voltear", "Voltear", ayuda="Invierte la orientación que sale sola (al ras ↔ enfrentadas; en Ángulo, da vuelta la geometría 1).")]

    def construir(self, v, ctx):
        exigir(v, "ref1", "Seleccioná la geometría del componente 1.")
        exigir(v, "ref2", "Seleccioná la geometría del componente 2.")
        angulo = v.get("tipo") == "angulo"
        valor = (v.get("angulo") if angulo else v.get("desfase")) or ("0 deg" if angulo else "0 mm")
        ctx.evaluar(valor, ANGULO) if angulo else ctx.evaluar(valor)
        return self.crear_op(OpRestriccion, v, ctx, tipo=v.get("tipo", "alinear"), ref1=ref1(v, "ref1"), ref2=ref1(v, "ref2"),
                             desfase=valor, voltear=bool(v.get("voltear")),
                             ref_angulo=ref1(v, "ref_angulo") if angulo else None)

    def desde_op(self, op, ctx):
        v = dict(op.p)
        for k in ("ref1", "ref2", "ref_angulo"):
            v[k] = [hit_desde_ref(op.p[k], ctx.estado)] if op.p.get(k) else []
        if op.p.get("tipo") == "angulo":
            v["angulo"] = op.p["desfase"]
        return v


class UnionComoEsta(Union):
    CLAVE, TITULO, ICONO, ATAJO = "union_construida", "Unión como está", "union_construida", "Shift+J"
    AYUDA = ("Une dos componentes en la posición en que están y define su movimiento. El componente 1 es "
             "la pieza que sigue al componente 2 cuando este se mueve.")
    COMO_ESTA = True
    VARIANTE = ("como_esta", True)      # doble clic en el timeline: edita con este diálogo, no con el de Unión


class OrigenUnion(Comando):
    CLAVE, TITULO, ICONO = "origen_union", "Origen de la unión", "origen_union"
    AYUDA = "Guarda un punto con orientación para usarlo después en una unión."
    CLASE_OP = OpOrigenUnion

    def campos(self, ctx):
        return [Opciones("modo", "Modo", MODOS_POSICION), Seleccion("origen", "Ajuste", SNAP),
                Seleccion("origen_b", "Segundo ajuste", SNAP, visible_si=lambda v: v.get("modo", "simple") != "simple",
                          ayuda="La segunda cara o la segunda arista del modo elegido."),
                Opciones("clave", "Punto de ajuste", CLAVES, visible_si=lambda v: v.get("modo", "simple") == "simple"),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO), Expresion("dx", "Desfase X", "0 mm"),
                Expresion("dy", "Desfase Y", "0 mm"), Expresion("dz", "Desfase Z", "0 mm")]

    def construir(self, v, ctx):
        exigir(v, "origen", "Seleccioná dónde va el origen.")
        modo = v.get("modo", "simple")
        if modo != "simple":
            exigir(v, "origen_b", "Seleccioná el segundo ajuste.")
        for k in ("angulo", "dx", "dy", "dz"):
            _numero(v.get(k))
        return self.crear_op(OpOrigenUnion, v, ctx, origen=ref1(v, "origen"), modo=modo,
                             origen_b=_ref(v, "origen_b") if modo != "simple" else None,
                             version_marco=_version(ctx, OpOrigenUnion, "version_marco"),
                             **{k: v[k] for k in ("clave", "angulo", "dx", "dy", "dz")})

    def desde_op(self, op, ctx):
        return dict(op.p, **{k: [hit_desde_ref(op.p[k], ctx.estado)] if op.p.get(k) else []
                             for k in ("origen", "origen_b")})


def _componentes_de(v, ctx):
    comps = []
    for h in v.get("cuerpos") or []:
        c = ctx.estado.cuerpos.get(h["ref"]["cuerpo"])
        if c is not None and c.componente and c.componente not in comps:
            comps.append(c.componente)
    return comps


class GrupoRigido(Comando):
    CLAVE, TITULO, ICONO = "grupo_rigido", "Grupo rígido", "grupo_rigido"
    AYUDA = "Hace que varios componentes se muevan juntos."
    CLASE_OP = OpGrupoRigido

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Componentes", {"cuerpo"}, maximo=None,
                          ayuda="Elegí un cuerpo de cada componente."),
                Casilla("incluir_hijos", "Incluir componentes secundarios",
                        ayuda="También entran al grupo los subcomponentes de cada componente elegido.")]

    def construir(self, v, ctx):
        comps = _componentes_de(v, ctx)
        if len(comps) < 2:
            raise ErrorComando("Elegí cuerpos de al menos dos componentes distintos.")
        return self.crear_op(OpGrupoRigido, v, ctx, componentes=comps, incluir_hijos=bool(v.get("incluir_hijos")))

    def desde_op(self, op, ctx):
        comps = []
        for ref in op.p["componentes"]:
            try:
                comps.append(componente_por_ref(ctx.estado, ref))    # id, nombre o cuerpo del componente
            except ErrorOperacion:
                pass
        ids = [next((c for c, cu in ctx.estado.cuerpos.items() if cu.componente == k), None) for k in comps if k]
        return dict(op.p, cuerpos=_hits_cuerpos([i for i in ids if i], ctx.estado))


def _uniones(ctx):
    return {o.id: o.nombre for o in ctx.doc.operaciones if isinstance(o, OpUnion)}


def _vinculo_que_la_mueve(ctx, id_union):
    """El vínculo de movimiento activo que impone el valor de esta unión (la «sigue»), o None."""
    return next((o for o in ctx.doc.operaciones if isinstance(o, OpVinculoMovimiento) and not o.suprimida
                 and o.p.get("union2") == id_union and o.p.get("union1") != id_union), None)


class AccionarUniones(Comando):
    CLAVE, TITULO, ICONO = "accionar_uniones", "Accionar uniones", "accionar_uniones"
    AYUDA = "Cambia el ángulo o la distancia de una unión (mueve el mecanismo)."
    SIN_OP, PREVIA = True, False

    def verificar(self, ctx):
        return None if _uniones(ctx) else "Todavía no hay uniones."

    def campos(self, ctx):
        uniones = _uniones(ctx)
        return [Opciones("union", "Unión", uniones), Expresion("giro", "Ángulo", "0 deg", ANGULO),
                Expresion("desliz", "Distancia", "0 mm")]

    def preparar_panel(self, panel):
        self._panel = panel

    def construir(self, v, ctx):
        return None

    def _nueva(self, v, ctx):
        """La unión con el ángulo y la distancia pedidos, como queda al aceptar."""
        op = ctx.doc.operacion(v["union"])
        vinculo = _vinculo_que_la_mueve(ctx, op.id)
        if vinculo:
            raise ErrorComando(f"La unión «{op.nombre}» la mueve el vínculo «{vinculo.nombre}»: su valor sale de la otra "
                               "unión. Accioná esa.")
        params = dict(op.p)
        _numero(v.get("giro"))
        _numero(v.get("desliz"))
        if MOVIMIENTOS[op.p["tipo"]][0]:
            ctx.evaluar(v["giro"], ANGULO)
            params["giro"] = v["giro"]
        if MOVIMIENTOS[op.p["tipo"]][1]:
            ctx.evaluar(v["desliz"])
            params["desliz"] = v["desliz"]
        params["accionada"] = siguiente_accion(ctx.doc.operaciones)
        return OpUnion(op.id, op.nombre, op.suprimida, **params)

    def _previsualizar(self, v, ctx):
        nueva = self._nueva(v, ctx)
        try:
            return nueva, ctx.doc.previsualizar(nueva, ctx.doc.indice(nueva.id))[0]
        except ErrorOperacion as e:
            raise ErrorComando(str(e)) from e

    def mostrar(self, v, ctx):
        """Vista previa en vivo: el mecanismo con el valor escrito (o tirado con las asas), sin tocar el documento."""
        estado = self._previsualizar(v, ctx)[1]
        panel = getattr(self, "_panel", None)
        if panel is not None:
            panel.previa.emit(estado)

    def aplicar(self, v, ctx):
        nueva = self._previsualizar(v, ctx)[0]       # un valor imposible se rechaza acá, con el panel abierto
        (ctx.ventana._reemplazar if ctx.ventana else lambda o: ctx.doc.reemplazar(o.id, o))(nueva)

    def manipuladores(self, ctx, v):
        """Arco del ángulo y flecha de la distancia sobre el eje de la unión elegida (marco del componente 2)."""
        import numpy as np

        from .. import manipuladores as mp
        datos = ctx.doc.estado_final.uniones.get(v.get("union"))
        if datos is None or _vinculo_que_la_mueve(ctx, v["union"]):
            return []                                  # la mueve un vínculo: las asas no harían nada
        F = np.asarray(datos["marco"], float)
        gira, desliza = MOVIMIENTOS[datos["tipo"]][0], MOVIMIENTOS[datos["tipo"]][1]
        salida = []
        if desliza:
            salida.append(mp.Flecha("desliz", F[:3, 3], direccion_eje(F, datos["eje_desliz"])))
        if gira:
            g = datos["eje_giro"]
            if datos["tipo"] == "bola" and isinstance(datos["eje_desliz"], dict):
                centro, balanceo, *_ = ejes_bola(datos["eje_desliz"])
                g = ([float(x) for x in centro], [float(x) for x in balanceo])
            origen = F[:3, 3] + F[:3, :3] @ eje_local(g)[0]            # un eje propio puede no pasar por el origen
            if isinstance(g, str):
                g = g if datos["tipo"] != "bola" else "Z"
                i = {"X": 0, "Y": 1, "Z": 2}[g]
                ref = F[:3, (i + 1) % 3]
            else:
                ref = marco_desde((0, 0, 0), direccion_eje(F, g))[:3, 0]
            salida.append(mp.Angulo("giro", origen, direccion_eje(F, g), ref, caja=True))
        return salida


class DuplicarConUniones(Comando):
    CLAVE, TITULO, ICONO = "duplicar_con_uniones", "Duplicar con uniones", "duplicar_con_uniones"
    AYUDA = ("Repite el componente que mueve una unión en cada destino que elijas (una cara, una arista, un vértice o "
             "un origen de unión): cada copia lleva su paso «Copiar componente» y una unión como la original.")
    SIN_OP, PREVIA = True, False
    TEXTO_ACEPTAR = "Duplicar"

    def verificar(self, ctx):
        return None if self._uniones(ctx) else "Primero creá una unión (ENSAMBLAR › Unión): es la que se repite."

    @staticmethod
    def _uniones(ctx):
        return {o.id: o.nombre for o in ctx.doc.operaciones if isinstance(o, OpUnion) and not o.p.get("como_esta")}

    def campos(self, ctx):
        return [Opciones("union", "Unión", self._uniones(ctx),
                         ayuda="La unión cuyo componente 1 se copia; sus ejes, límites y valores se repiten."),
                ListaSeleccion("destinos", "Destinos", SNAP, ayuda="Dónde va cada copia: una fila por copia."),
                Casilla("voltear", "Voltear las copias", avanzado=True)]

    def construir(self, v, ctx):
        return None

    def aplicar(self, v, ctx):
        from ... import api
        exigir(v, "destinos", "Elegí al menos un destino para las copias.")
        r = api.llamar(api.Sesion(ctx.doc), "duplicate_with_joints",
                       {"joint": v["union"], "destinations": refs(v, "destinos"), "flip": bool(v.get("voltear"))})
        if not r["ok"]:
            raise ErrorComando(r["mensaje"])
        if ctx.ventana is not None:
            ctx.ventana.mensaje(f"Se duplicó el componente {r['result']['count']} vez/veces con sus uniones.")


class VinculoMovimiento(Comando):
    CLAVE, TITULO, ICONO = "vinculo_movimiento", "Vínculo de movimiento", "vinculo_movimiento"
    AYUDA = "Hace que una unión se mueva en proporción a otra (engranajes, cremalleras…)."
    CLASE_OP = OpVinculoMovimiento

    def verificar(self, ctx):
        return None if len(_uniones(ctx)) >= 2 else "Hacen falta dos uniones."

    def campos(self, ctx):
        uniones = _uniones(ctx)

        def movimientos(clave):
            """Los grados de libertad de la unión elegida (ASM-13); «Automático» es el giro o, si no gira, el deslizamiento."""
            def listar(v):
                u = ctx.doc.estado_final.uniones.get(v.get(clave))
                dof = sum(MOVIMIENTOS[u["tipo"]], []) if u else []
                return {"": "Automático", **{k: NOMBRE_MOVIMIENTO[k] for k in dof}}
            return listar

        return [Opciones("union1", "Unión 1", uniones),
                OpcionesVivas("mov1", "Movimiento de la unión 1", movimientos("union1")),
                Opciones("union2", "Unión 2", uniones, list(uniones)[-1] if uniones else None),
                OpcionesVivas("mov2", "Movimiento de la unión 2", movimientos("union2")),
                Expresion("factor", "Relación 2 / 1", "1", "escalar",
                          ayuda="Relación entre los movimientos: unión 2 / unión 1."), Casilla("invertir", "Invertir"),
                Personalizado("animar", "", lambda panel: self._boton_animar(panel, ctx), ancho_completo=True)]

    @staticmethod
    def _boton_animar(panel, ctx):
        """«Animar» (Motion Link reference): anda y para la animación de la relación con lo que dice el panel."""
        from PySide6.QtWidgets import QPushButton

        from ..estudio_movimiento import alternar_animacion_vinculo
        boton = QPushButton("Animar", checkable=True,
                            toolTip="Mueve la unión 1 de ida y vuelta y la unión 2 la sigue con esta relación.")

        def alternar():
            try:
                _numero(panel.valores.get("factor"))
                anda = ctx.ventana is not None and alternar_animacion_vinculo(ctx.ventana, panel.valores, ctx)
            except (ErrorComando, ErrorOperacion) as e:
                panel._mostrar(str(e))
                anda = False
            boton.setChecked(anda)

        def parar(*_):
            if ctx.ventana is not None and getattr(ctx.ventana, "_t_vinculo", None) is not None:
                ctx.ventana._t_vinculo.stop()

        boton.clicked.connect(lambda _c=False: alternar())
        panel.destroyed.connect(parar)
        return boton

    def construir(self, v, ctx):
        if v["union1"] == v["union2"]:
            u = ctx.doc.estado_final.uniones.get(v["union1"])
            if u is not None and _clave_movimiento(u, v.get("mov1")) == _clave_movimiento(u, v.get("mov2")):
                raise ErrorComando("Con la misma unión en las dos puntas hay que elegir dos movimientos distintos de ella "
                                   "(por ejemplo Giro y Deslizamiento de una cilíndrica).")
        _numero(v["factor"])
        return self.crear_op(OpVinculoMovimiento, v, ctx, union1=v["union1"], union2=v["union2"], factor=v["factor"],
                             invertir=v["invertir"], mov1=v.get("mov1") or "", mov2=v.get("mov2") or "",
                             version_vinculo=_version(ctx, OpVinculoMovimiento, "version_vinculo"))


class FijarComponente(Comando):
    CLAVE, TITULO, ICONO = "fijar_componente", "Fijar / liberar componente", "fijar_componente"
    AYUDA = "Fija un componente en su lugar (Ground): las uniones no lo mueven."
    SIN_OP, PREVIA = True, False

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Componente", {"cuerpo"}, ayuda="Elegí un cuerpo del componente.")]

    def construir(self, v, ctx):
        return None

    def aplicar(self, v, ctx):
        comps = _componentes_de(v, ctx)
        if not comps:
            raise ErrorComando("Ese cuerpo no está en un componente.")
        op = ctx.doc.operacion(comps[0])
        # misma clase que el paso original: un diseño insertado (OpInsertarDiseno) también es un componente con «fijo»;
        # rehacerlo como OpComponente perdía sus cuerpos
        nueva = op.__class__(op.id, op.nombre, op.suprimida, **dict(op.p, fijo=not op.p.get("fijo")))
        (ctx.ventana._reemplazar if ctx.ventana else lambda o: ctx.doc.reemplazar(o.id, o))(nueva)


class AnclarComponente(Comando):
    CLAVE, TITULO, ICONO = "anclar_componente", "Anclar / desanclar componente", "anclar_componente"
    AYUDA = "Ancla un componente a la raíz como un paso del timeline (Pin): las uniones no lo mueven."
    CLASE_OP = OpAnclar

    def verificar(self, ctx):
        return None if ctx.estado.componentes else "Primero creá componentes (ENSAMBLAR › Nuevo componente)."

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Componente", {"cuerpo"}, ayuda="Elegí un cuerpo del componente."),
                Casilla("anclado", "Anclado", True)]

    def construir(self, v, ctx):
        comps = _componentes_de(v, ctx)
        if not comps:
            raise ErrorComando("Ese cuerpo no está en un componente.")
        return self.crear_op(OpAnclar, v, ctx, componente=comps[0], anclado=bool(v.get("anclado")))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_de_componentes([op.p["componente"]], ctx))


class PosicionInicial(Comando):
    CLAVE, TITULO, ICONO = "posicion_inicial", "Editar posición inicial", "posicion_inicial"
    AYUDA = "Mueve y gira un componente respecto de donde se creó (Edit Initial Position)."
    CLASE_OP = OpPosicionInicial

    def verificar(self, ctx):
        return None if ctx.estado.componentes else "Primero creá componentes (ENSAMBLAR › Nuevo componente)."

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Componente", {"cuerpo"}, ayuda="Elegí un cuerpo del componente."),
                Expresion("x", "Distancia X", "0 mm"), Expresion("y", "Distancia Y", "0 mm"),
                Expresion("z", "Distancia Z", "0 mm"), Expresion("rx", "Ángulo X", "0 deg", ANGULO),
                Expresion("ry", "Ángulo Y", "0 deg", ANGULO), Expresion("rz", "Ángulo Z", "0 deg", ANGULO)]

    def construir(self, v, ctx):
        comps = _componentes_de(v, ctx)
        if not comps:
            raise ErrorComando("Ese cuerpo no está en un componente.")
        for k in ("x", "y", "z", "rx", "ry", "rz"):
            _numero(v.get(k))
        return self.crear_op(OpPosicionInicial, v, ctx, componente=comps[0],
                             **{k: v[k] for k in ("x", "y", "z", "rx", "ry", "rz")})

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_de_componentes([op.p["componente"]], ctx))


class _PosicionDeComponentes(Comando):
    """Capturar y Revertir: sin elegir nada afectan a todos los componentes."""
    CLASE_OP = None

    def verificar(self, ctx):
        return None if ctx.estado.componentes else "Primero creá componentes (ENSAMBLAR › Nuevo componente)."

    def campos(self, ctx):
        return [Seleccion("cuerpos", "Componentes", {"cuerpo"}, minimo=0, maximo=None,
                          ayuda="Un cuerpo de cada componente; sin elegir ninguno, todos.")]

    def construir(self, v, ctx):
        return self.crear_op(self.CLASE_OP, v, ctx, componentes=_componentes_de(v, ctx))

    def desde_op(self, op, ctx):
        return dict(op.p, cuerpos=_hits_de_componentes(op.p["componentes"], ctx))


class CapturarPosicion(_PosicionDeComponentes):
    CLAVE, TITULO, ICONO = "capturar_posicion", "Capturar posición", "capturar_posicion"
    AYUDA = "Deja la posición de ahora como la de referencia a la que vuelve «Revertir posición»."
    CLASE_OP = OpCapturarPosicion


class RevertirPosicion(_PosicionDeComponentes):
    CLAVE, TITULO, ICONO = "revertir_posicion", "Revertir posición", "revertir_posicion"
    AYUDA = "Devuelve los componentes a su última posición capturada (o a donde se modelaron)."
    CLASE_OP = OpRevertirPosicion


def _hits_de_componentes(ids, ctx):
    """Un cuerpo de cada componente `ids` (id, nombre o cuerpo) como selección del panel."""
    salida = []
    for ref in ids:
        try:
            k = componente_por_ref(ctx.estado, ref)
        except ErrorOperacion:
            continue
        cid = next((c for c, cu in ctx.estado.cuerpos.items() if cu.componente == k), None)
        if cid:
            salida.append(cid)
    return _hits_cuerpos(salida, ctx.estado)


registrar(NuevoComponente, Union, UnionComoEsta, RestriccionComponentes, OrigenUnion, GrupoRigido, AccionarUniones, DuplicarConUniones,
          VinculoMovimiento, FijarComponente, AnclarComponente, PosicionInicial, CapturarPosicion, RevertirPosicion)
