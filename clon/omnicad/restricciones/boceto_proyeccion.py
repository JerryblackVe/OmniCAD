"""Boceto 2D: proyeccion."""
import math
import copy

from .boceto_entidades import (
    Arco, ArcoElipse, Circulo, Elipse, ELIPTICAS, ErrorBoceto, LARGO_EJE_VACIO, Linea, MITAD_EJE_MINIMA, Spline,
)
from .boceto_geometria import distancia_primitiva, dominio, evaluar_primitiva, firma_primitiva


class _Proyeccion:
    def _firma_proyectada(self, c):
        """Lo que identifica a una curva proyectada al compararla con otra (ver `agregar_proyeccion`)."""
        return frozenset(c.puntos()) if isinstance(c, Linea) else firma_primitiva(self.primitivas(c.id)[0])

    def agregar_proyeccion(self, primitivas, puntos=(), construccion=False, origen=None, unir=True):
        """Agrega geometría proyectada (Proyectar / Intersecar de Fusion): curvas violetas, fijas.
        Los extremos que coinciden se comparten para que cierren perfiles. Con `construccion` las curvas quedan
        como líneas de construcción (no forman perfiles). Con `origen` recuerda las referencias para reproyectar (y
        aplica `derivar_proyeccion`).
        Lo que coincide con geometría ya proyectada no se duplica: esa curva entra en los ids, en el lugar de su
        primitiva (`reproyectar` depende de ese orden), y toma el tipo de línea pedido. Si con eso alguna deja de ser solo
        del contorno automático o gana vínculo, nace un registro propio (se ve y guarda sus referencias); si todas ya
        eran explícitas, no cambia nada. Sin `origen` (vínculo apagado), lo que era solo del contorno automático se
        suelta de él. Con `unir=False` solo se unen líneas y círculos: lo usan los registros anteriores a unir también
        arcos, elipses y splines. Devuelve los ids, los reutilizados incluidos."""
        if origen is not None:
            primitivas = self.derivar_proyeccion(origen, primitivas)
        existentes = [p for p in self.puntos.values() if p.proyectado]
        previas = self.ocultos_por_proyeccion_auto()[0]
        vinculados = self._puntos_vinculados() if origen is None else ()
        propios = {}

        def buscar(xy):
            for p in existentes:
                if math.hypot(p.x - xy[0], p.y - xy[1]) < 1e-6:
                    return p.id
            pid = self.agregar_punto(xy[0], xy[1], proyectado=True)
            existentes.append(self.puntos[pid])
            return pid

        def punto(xy):
            """El punto de la curva nueva. Sin vínculo no comparte uno que sigue al modelo: si no, se movería con él."""
            pid = buscar(xy)
            if pid not in vinculados:
                return pid
            if pid not in propios:
                propios[pid] = self.agregar_punto(xy[0], xy[1], proyectado=True)
            return propios[pid]
        ids, reusadas = [], []
        vistas = {self._firma_proyectada(c): c.id for c in self.curvas.values() if c.proyectada and c.id > 0}
        for prim in primitivas:
            t = prim[0]
            if t == "linea" and math.dist(prim[2], prim[3]) < 1e-9:
                continue
            if t == "linea":
                firma = frozenset((buscar(prim[2]), buscar(prim[3])))
            else:
                firma = firma_primitiva(prim) if unir or t == "circulo" else None
            if firma in vistas:               # dos aristas que se proyectan sobre lo mismo: una sola curva
                if vistas[firma] not in ids:
                    ids.append(vistas[firma])
                    reusadas.append(vistas[firma])
                continue
            if t == "linea":
                c = Linea(self._nuevo_id(), punto(prim[2]), punto(prim[3]), construccion, proyectada=True)
            elif t == "circulo":
                c = Circulo(self._nuevo_id(), punto(prim[2]), prim[3], construccion, proyectada=True)
            elif t == "arco":
                (cx, cy), r = prim[2], prim[3]
                c = Arco(self._nuevo_id(), punto((cx, cy)), punto((cx + r * math.cos(prim[4]), cy + r * math.sin(prim[4]))),
                         punto((cx + r * math.cos(prim[5]), cy + r * math.sin(prim[5]))), construccion, proyectada=True)
            elif t in ELIPTICAS:
                (cx, cy), a, b, ang = prim[2], prim[3], prim[4], prim[5]
                centro, mayor = punto((cx, cy)), punto((cx + a * math.cos(ang), cy + a * math.sin(ang)))
                if t == "elipse":
                    c = Elipse(self._nuevo_id(), centro, mayor, b, construccion, proyectada=True)
                else:
                    p0, p1 = evaluar_primitiva(prim, 0.0)[0], evaluar_primitiva(prim, dominio(prim)[1])[0]
                    c = ArcoElipse(self._nuevo_id(), centro, mayor, b, punto(p0), punto(p1), construccion, proyectada=True)
            elif t == "spline":
                polos = [punto(q) for q in prim[2]]
                c = Spline(self._nuevo_id(), polos, "control", prim[4], False, prim[5], prim[3], construccion, proyectada=True)
            else:
                continue
            ids.append(self._agregar_curva(c))
            if firma is not None:
                vistas[firma] = c.id
        ids += [punto(xy) for xy in puntos]
        for i in reusadas:
            self.curvas[i].construccion = bool(construccion)
        if origen is None:
            for i in previas.intersection(reusadas):
                self._soltar_de_auto(i)
        elif ids and (origen.get("auto") or not set(ids) <= self._explicitas()):
            self.proyecciones.append({"id": max((r["id"] for r in self.proyecciones), default=0) + 1,
                                      "construccion": construccion, "ids": list(ids),
                                      **copy.deepcopy(origen)})
        return ids

    def simular_proyecciones(self, tandas):
        """Qué harían `tandas` (argumentos de `agregar_proyeccion`), sin tocar el boceto: "curvas" y "puntos" creados,
        "visibles" (curvas que dejan de estar ocultas), "vinculadas" (las que ya se veían y ganan vínculo), "reusadas"
        (lo existente que entra) y si "cambia" algo. La vista previa y el resultado del comando salen de acá."""
        copia = self.copia()
        antes = copia.a_dict()
        ids = []
        for tanda in tandas:
            ids += [i for i in copia.agregar_proyeccion(*tanda) if i not in ids]
        ocultas, explicitas = self.ocultos_por_proyeccion_auto()[0], self._explicitas()
        reusadas = [i for i in ids if i in self.curvas or i in self.puntos]
        return {"curvas": [i for i in ids if i in copia.curvas and i not in self.curvas],
                "puntos": [i for i in ids if i in copia.puntos and i not in self.puntos],
                "visibles": sorted(ocultas - copia.ocultos_por_proyeccion_auto()[0]),
                "vinculadas": [i for i in reusadas if i not in ocultas and i not in explicitas and i in copia._explicitas()],
                "reusadas": reusadas, "cambia": copia.a_dict() != antes}

    def _explicitas(self):
        """Ids de las proyecciones con vínculo que no son el contorno automático."""
        return {i for r in self.proyecciones if not r.get("auto") for i in r["ids"]}

    def ocultos_por_proyeccion_auto(self):
        """(curvas, puntos) que solo vienen de la proyección automática de la cara elegida al crear el boceto
        (`auto`): Fusion no las dibuja (se ve solo el celeste del perfil), pero siguen siendo geometría real."""
        explicitas = self._explicitas()
        auto = {i for r in self.proyecciones if r.get("auto") for i in r["ids"]} - explicitas
        if not auto:
            return frozenset(), frozenset()
        puntos = {q for c in self.curvas.values() if c.id in auto for q in c.puntos()} | auto
        puntos -= {q for c in self.curvas.values() if c.id not in auto for q in c.puntos()} | explicitas
        return frozenset(auto), frozenset(puntos)

    def _puntos_vinculados(self):
        """Puntos que mueve alguna proyección con vínculo al reproyectar."""
        return {q for r in self.proyecciones for i in r["ids"] for q in (self.curvas[i].puntos() if i in self.curvas else [i])}

    def _soltar_de_auto(self, cid):
        """Saca la curva del contorno automático (vínculo apagado o roto): queda donde está, sin seguir a la cara y con
        puntos propios si los compartía con otra proyección. Su lugar queda en `huecos`, para que `reproyectar` no
        corra a las demás. Un registro que se queda sin ids desaparece."""
        autos = [r for r in self.proyecciones if r.get("auto") and cid in r["ids"]]
        if not autos:
            return
        for r in autos:
            huecos = r.setdefault("huecos", [])
            libres = [k for k in range(len(r["ids"]) + len(huecos)) if k not in huecos]
            huecos.append(libres[r["ids"].index(cid)])
            r["ids"].remove(cid)
            if not r["ids"]:
                self.proyecciones.remove(r)
        c = self.curvas[cid]
        nuevos = {q: self.agregar_punto(*self.coords(q), proyectado=True) for q in set(c.puntos()) & self._puntos_vinculados()}
        if nuevos:
            self.curvas[cid] = c.remapear(nuevos)

    def derivar_proyeccion(self, datos, primitivas):
        """Ajustes de una proyección según sus `datos` (los del registro de proyección):
        - "contorno" = (punto, dirección) del eje proyectado de un perfil giratorio: deja solo su contorno exterior
          (BOC-18, `nucleo.contorno_giro`). shortcut: el eje queda guardado como estaba al proyectar; si el eje del
          modelo se mueve, el contorno se calcula con el viejo hasta re-proyectar.
        - "infinitas" = {índice de primitiva: alcance del modelo en mm}: líneas de un eje o de la traza de un plano (son
          infinitas): se recortan, alrededor de su punto medio, al 110 % de lo más lejano entre el modelo y la
          geometría propia del boceto (BOC-17); sin nada alrededor, ±LARGO_EJE_VACIO."""
        if datos.get("contorno"):
            from ..nucleo.contorno_giro import contorno_exterior
            primitivas = contorno_exterior(primitivas, datos["contorno"], datos.get("tolerancia") or 0.1)
        infinitas = datos.get("infinitas") or {}
        if infinitas:
            propios = [(p.x, p.y) for p in self.puntos.values() if p.id > 0 and not p.proyectado]
            primitivas = list(primitivas)
            for i, modelo in infinitas.items():
                _t, _x, a, b = primitivas[int(i)]
                m, largo = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), math.dist(a, b)
                u = ((b[0] - a[0]) / largo, (b[1] - a[1]) / largo)
                alcance = max([float(modelo)] + [math.dist(m, q) for q in propios])
                mitad = max(MITAD_EJE_MINIMA, 1.1 * alcance) if alcance > 1e-9 else LARGO_EJE_VACIO
                primitivas[int(i)] = ("linea", None, (m[0] - u[0] * mitad, m[1] - u[1] * mitad),
                                      (m[0] + u[0] * mitad, m[1] + u[1] * mitad))
        return primitivas

    def _proyeccion(self, pid):
        r = next((r for r in self.proyecciones if r["id"] == pid), None)
        if r is None:
            raise ErrorBoceto(f"No existe la proyección {pid}.")
        return r

    def romper_vinculo(self, pid):
        """Romper vínculo (Fusion: Break Link): la geometría proyectada queda donde está, como geometría normal
        (editable, ya no fija) que no sigue más al modelo. Lo que sigue en otra proyección explícita no se toca."""
        r = self.proyecciones.pop(self.proyecciones.index(self._proyeccion(pid)))
        for i in r["ids"]:
            if i in self.curvas and i not in self._explicitas():
                self._soltar_de_auto(i)
        siguen = {i for otra in self.proyecciones for i in otra["ids"]}
        for i in r["ids"]:
            if i in siguen:
                continue
            if i in self.curvas:
                self.curvas[i].proyectada = False
                for q in self.curvas[i].puntos():
                    if not any(q in self.curvas[k].puntos() for k in siguen if k in self.curvas):
                        self.puntos[q].proyectado = False
            elif i in self.puntos:
                self.puntos[i].proyectado = False

    def eliminar_proyeccion(self, pid):
        """Borrar geometría (Manage Lost Projections › Delete Geometry): quita la proyección y sus curvas y puntos. Lo
        que comparte con otra proyección queda (con el contorno automático vuelve a ocultarse)."""
        r = self.proyecciones.pop(self.proyecciones.index(self._proyeccion(pid)))
        siguen = {i for otra in self.proyecciones for i in otra["ids"]}
        for i in r["ids"]:
            if i not in siguen and (i in self.curvas or i in self.puntos):
                self.eliminar(i)

    def revincular(self, pid, refs, primitivas, puntos, infinitas=None):
        """Re-vincular (Manage Lost Projections › Re-Link): la proyección pasa a seguir las referencias `refs`, cuya
        proyección (`primitivas`, `puntos`) tiene que tener la misma forma que la que había (una silueta se rehace,
        H-77). `infinitas`: las líneas de ejes o planos de la selección nueva (ver `derivar_proyeccion`); None = las
        que tenía."""
        r = self._proyeccion(pid)
        if infinitas is not None:
            r["infinitas"] = dict(infinitas)
        r["refs"], viejas = copy.deepcopy(refs), r["refs"]
        if not self.reproyectar(r, primitivas, puntos):
            if r["modo"] != "silueta":
                r["refs"] = viejas
                raise ErrorBoceto("La proyección cambió: rompé el vínculo.")
            self.rehacer_proyeccion(r, primitivas, puntos)        # H-77: una silueta se rehace con lo nuevo

    def rehacer_proyeccion(self, registro, primitivas, puntos=()):
        """H-77 (Fusion: la proyección de un cuerpo se regenera): la silueta cambió de cantidad o tipo de tramos, así que
        se rehace entera con `primitivas` en lugar de quedar perdida. Los tramos que no se movieron conservan su id (se
        reutilizan); una restricción o cota de un tramo que cambió pasa al tramo nuevo del mismo tipo que pasa por su
        punto medio. Devuelve cuántas restricciones y cotas se quitaron porque su tramo ya no está."""
        medios = {}
        for i in (i for i in registro["ids"] if i in self.curvas):
            prim = self.primitivas(i)[0]
            t0, t1, _ = dominio(prim)
            medios[i] = (self.curvas[i].tipo, evaluar_primitiva(prim, (t0 + t1) / 2)[0])
        self.proyecciones.remove(registro)
        datos = {k: v for k, v in registro.items() if k not in ("id", "ids", "huecos", "construccion")}
        ids = self.agregar_proyeccion(primitivas, puntos, registro["construccion"], origen=datos)
        nuevo = next((r for r in self.proyecciones if r["ids"] == ids), None)
        if nuevo is None:                     # todo reutilizado por otra proyección explícita: no queda registro propio
            nuevo = {**copy.deepcopy(datos), "construccion": registro["construccion"], "ids": list(ids)}
            self.proyecciones.append(nuevo)
        nuevo["id"] = registro["id"]
        cambio = {}
        for i, (tipo, centro) in medios.items():
            if i not in ids:
                cambio[i] = next((j for j in ids if j in self.curvas and self.curvas[j].tipo == tipo
                                  and distancia_primitiva(self.primitivas(j)[0], centro) < 1e-6), None)
        antes = len(self.restricciones) + len(self.cotas)
        for r in list(self.restricciones.values()) + list(self.cotas.values()):
            r.entidades = [cambio.get(e) or e for e in r.entidades]
        siguen = {i for r in self.proyecciones for i in r["ids"]}
        for i in cambio:
            if i in self.curvas and i not in siguen:
                self.eliminar(i)
        return antes - len(self.restricciones) - len(self.cotas)
