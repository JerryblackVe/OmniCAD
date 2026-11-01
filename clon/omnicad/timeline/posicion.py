# -*- coding: utf-8 -*-
"""ENSAMBLAR › Posición [Capture or revert position of components]: arrastrar un componente lo mueve sin tocar el
timeline. Lo movido queda en `doc.posicion_pendiente` hasta Capturar posición o Revertir; cualquier otro cambio del
documento lo descarta. Con una unión el arrastre sigue sus grados de libertad y sus límites; sin unión el componente se
traslada libre. Sin Qt: lo comparten la ventana y la API."""
import numpy as np

from .operaciones import Contexto, ErrorOperacion
from .ops_ensamblar import MOVIMIENTOS, es_fijo, grupo_rigido, poses_de_estudio, valores_de_estudio
from .parametros import ErrorExpresion

ITERACIONES = 12
PASO_DERIVADA = 0.05        # grados o mm
GIRO_POR_ITERACION = 30.0   # grados: un paso mayor saltaría a la otra rama de la solución


class PosicionPendiente:
    """Lo movido sin capturar sobre `estado`. `valores` = {unión: {movimiento: valor}}; `libres` = {componente:
    desplazamiento [x, y, z]} de los que ninguna unión mueve; `historia`, cómo estaba antes de cada arrastre."""

    def __init__(self, estado):
        self.estado = estado
        self.valores, self.libres, self.historia = {}, {}, []

    def foto(self):
        return {k: dict(v) for k, v in self.valores.items()}, {k: list(v) for k, v in self.libres.items()}

    def volver(self, foto):
        self.valores, self.libres = foto

    def poses(self):
        return poses_de_estudio(self.estado, self.valores, self.libres)


def pendiente_de(doc):
    """Lo que está sin capturar, o None. Si el documento cambió desde el arrastre, ya no vale y se descarta."""
    p = doc.posicion_pendiente
    if p is not None and p.estado is not doc.estado_final:
        p = doc.posicion_pendiente = None
    return p


def deshacer_arrastre(doc):
    """Deshace el último arrastre sin capturar. Devuelve si había alguno."""
    p = pendiente_de(doc)
    if p is None or not p.historia:
        return False
    p.volver(p.historia.pop())
    if not p.historia:
        doc.posicion_pendiente = None
    return True


def _variables(estado, uid):
    """Los movimientos que se pueden arrastrar, como (unión, movimiento). El que sigue a un vínculo se mueve desde la
    otra unión."""
    u, salida = estado.uniones[uid], []
    v = u.get("vinculo")
    for clave in sum(MOVIMIENTOS[u["tipo"]], []):
        par = (v["union1"], v["clave1"]) if v and v["clave2"] == clave and v["union1"] != uid else (uid, clave)
        if par not in salida:
            salida.append(par)
    return salida


def que_arrastra(estado, comp):
    """(variables, componentes libres) que mueve arrastrar `comp`. Una unión rígida pasa el arrastre al componente al
    que está sujeto. ErrorOperacion si nada se puede mover."""
    vistos = set()
    while comp and comp not in vistos:
        vistos.add(comp)
        nombre = estado.componentes[comp].get("nombre") or comp
        uid = next((k for k, u in reversed(estado.uniones.items()) if comp in u["componentes"]), None)
        grupo = grupo_rigido(estado, comp) if uid is None else {comp}
        if any(es_fijo(estado, k) for k in grupo):
            raise ErrorOperacion(f"«{nombre}» está fijo o anclado: no se puede arrastrar.")
        if uid is None:
            return [], sorted(grupo)
        if any(u.get("cierra_lazo") for u in estado.uniones.values()):
            # shortcut: frena con cualquier lazo del documento; alcanza hasta que el arrastre resuelva lazos cerrados
            raise ErrorOperacion("El ensamble tiene un lazo cerrado de uniones: arrastrar todavía no lo resuelve. "
                                 "Usá ENSAMBLAR › Accionar uniones.")
        variables = _variables(estado, uid)
        if variables:
            return variables, []
        comp = estado.uniones[uid]["comp2"]
    raise ErrorOperacion("Una unión rígida lo sujeta y no tiene a dónde moverse: no se puede arrastrar.")


def _limites(doc, uid, clave):
    try:
        mn, mx = doc.operacion(uid).limites(Contexto(doc.parametros.valores()), clave)
    except (ErrorExpresion, ErrorOperacion):         # un límite que no se puede calcular no frena el arrastre
        mn = mx = None
    return -np.inf if mn is None else mn, np.inf if mx is None else mx


class Arrastre:
    """Se agarra `cuerpo` en `punto` (mundo, tal como se ve ahora) y `mover` lleva ese punto hacia el objetivo."""

    def __init__(self, doc, cuerpo, punto):
        self.doc = doc
        self.p = pendiente_de(doc) or PosicionPendiente(doc.estado_final)
        self.cuerpo, self.punto = cuerpo, np.asarray(punto, float)
        self.variables, self.libres = que_arrastra(self.p.estado, self.p.estado.cuerpo(cuerpo).componente or "")
        self.limites = [_limites(doc, *v) for v in self.variables]
        self.local = np.linalg.inv(self.p.poses().get(cuerpo, np.identity(4))) @ np.r_[self.punto, 1.0]
        self.antes = self.p.foto()

    def mover(self, objetivo, direccion=None):
        """`objetivo`: punto de destino; con `direccion` (unitaria), la recta que pasa por él (el rayo del cursor), y
        el punto agarrado se acerca a esa recta."""
        objetivo = np.asarray(objetivo, float)
        for k in self.libres:
            self.p.libres[k] = (np.asarray(self.antes[1].get(k, (0.0, 0.0, 0.0))) + objetivo - self.punto).tolist()
        if self.variables:
            self._resolver(objetivo, direccion)
        self.doc.posicion_pendiente = self.p

    def _resolver(self, objetivo, direccion):
        """Levenberg-Marquardt sobre los valores de la unión: sirve para cualquier tipo y sigue vínculos y cadenas."""
        p, variables = self.p, self.variables
        actuales = valores_de_estudio(p.estado, p.valores)
        x = np.array([actuales[u][c] for u, c in variables], float)
        bajo, alto = np.array(self.limites, float).T
        tope = np.array([GIRO_POR_ITERACION if c.startswith("giro") else np.inf for _u, c in variables])

        def residuo(x):
            pedidos = {k: dict(v) for k, v in p.valores.items()}
            for (u, c), v in zip(variables, x, strict=True):
                pedidos.setdefault(u, {})[c] = float(v)
            r = (poses_de_estudio(p.estado, pedidos, p.libres)[self.cuerpo] @ self.local)[:3] - objetivo
            return r if direccion is None else r - (r @ direccion) * direccion

        for _ in range(ITERACIONES):
            r = residuo(x)
            J = np.column_stack([(residuo(x + PASO_DERIVADA * e) - r) / PASO_DERIVADA for e in np.identity(len(x))])
            A = J.T @ J
            paso = np.clip(np.linalg.solve(A + np.diag(1e-3 * np.diag(A) + 1e-9), -J.T @ r), -tope, tope)
            x = np.clip(x + paso, bajo, alto)
            if np.linalg.norm(paso) < 1e-5:
                break
        for (u, c), v in zip(variables, x, strict=True):
            p.valores.setdefault(u, {})[c] = float(v)

    def soltar(self):
        if self.p.foto() != self.antes:
            self.p.historia.append(self.antes)
        elif not self.p.historia:
            self.doc.posicion_pendiente = None

    def cancelar(self):
        self.p.volver(self.antes)
        self.soltar()
