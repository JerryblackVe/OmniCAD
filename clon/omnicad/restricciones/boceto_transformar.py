"""Boceto 2D: transformar."""
import math
import copy

from .boceto_entidades import (
    Arco, ArcoElipse, _cambia_orientacion, Circulo, _COTAS_ORIENTADAS, distancia_punto_recta, Elipse, ErrorBoceto,
    _invertir_curvatura, Linea, _numero, _ORIENTADAS, Spline, Texto,
)
from .boceto_geometria import _rot


class _Transformar:
    def pegar_de(self, origen, ids, dx=0.0, dy=0.0):
        """Pegar elementos de OTRO boceto (Fusion: Copiar y Pegar entre bocetos): copia las curvas y los puntos
        `ids` de `origen`, corridos (dx, dy), con las restricciones y cotas que quedan enteras dentro de la selección.
        Lo pegado es geometría normal (la proyectada deja de ser fija). Devuelve los ids de las curvas y puntos nuevos."""
        ids = [i for i in ids if i > 0 and (i in origen.curvas or i in origen.puntos)]
        if not ids:
            raise ErrorBoceto("Seleccioná la geometría a copiar.")
        mapa = {p: self.agregar_punto(origen.puntos[p].x + dx, origen.puntos[p].y + dy)
                for p in origen._con_vertices_virtuales(ids, origen.puntos_de(ids))}
        mapa_c = {}
        for i in ids:
            if i in origen.curvas:
                c = origen.curvas[i].remapear(mapa, self._nuevo_id())
                c.proyectada = False
                self.curvas[c.id] = c
                mapa_c[i] = c.id
        for c in self.curvas.values():                      # el texto sobre una curva no copiada vuelve a ser recto
            if isinstance(c, Texto) and c.id in mapa_c.values():
                c.camino = mapa_c.get(c.camino)
        todo = {**mapa, **mapa_c}
        for r in origen.restricciones.values():
            if r.tipo not in ("fijo", "patron", "desfase") and set(r.entidades) <= set(todo):
                self.agregar_restriccion(r.tipo, [todo[e] for e in r.entidades], copy.deepcopy(r.datos))
        copias = {k.id: self.agregar_cota(k.tipo, [todo[e] for e in k.entidades], k.expresion, copy.deepcopy(k.datos),
                                          k.referencia) for k in origen.cotas.values() if set(k.entidades) <= set(todo)}
        self._ligar_cotas_copiadas(origen, copias)
        return list(mapa_c.values()) + [q for p, q in mapa.items() if p in ids]

    def _ligar_cotas_copiadas(self, origen, copias):
        """La copia de una cota que sigue a otra copiada («d1» o `igual_a`: el par de un chaflán) sigue a la copia
        de su par, no al original; el documento la liga al nombrarla (B-236). `copias`: id en `origen` → id nuevo."""
        por_nombre = {origen.cotas[k].nombre: k for k in copias if origen.cotas[k].nombre}
        for k, nueva in copias.items():
            par = por_nombre.get(origen.cotas[k].expresion.strip(), origen.cotas[k].datos.get("igual_a"))
            if par in copias:
                self.cotas[nueva].datos["igual_a"] = copias[par]

    # ------------------------------------------------------------ MODIFICAR: escala, mover/copiar
    def _transformar_puntos(self, pids, f):
        for p in pids:
            q = self.puntos[p]
            q.x, q.y = f((q.x, q.y))

    def _copiar(self, ids, f, restricciones=True, angulo=0.0, compartidos=()):
        """Copia curvas y puntos sueltos aplicando `f` a las coordenadas (los `compartidos` no se
        duplican). Devuelve (mapa de puntos nuevos, mapa de curvas)."""
        pts = self.puntos_de(ids)
        if restricciones:                       # el vértice virtual de un chaflán viaja con sus cotas (B-236)
            pts = self._con_vertices_virtuales(ids, pts)
        pts = [p for p in pts if p not in compartidos]
        mapa ={p: self.agregar_punto(*f(self.coords(p))) for p in pts}
        mapa_c = {}
        for i in ids:
            if i in self.curvas:
                c = self.curvas[i].remapear(mapa, self._nuevo_id())
                c.proyectada = False
                if isinstance(c, Texto):
                    c.angulo += angulo
                    c.parametro_texto = c.parametro_altura = None
                self.curvas[c.id] = c
                mapa_c[i] = c.id
        if restricciones:
            todo = {**mapa, **mapa_c}
            gira = _cambia_orientacion(angulo)
            for r in list(self.restricciones.values()):
                if r.tipo not in ("fijo", "patron", "desfase") and set(r.entidades) <= set(todo) and not (
                        gira and r.tipo in _ORIENTADAS):
                    self.agregar_restriccion(r.tipo, [todo[e] for e in r.entidades], r.datos)
            copias = {}
            for k in list(self.cotas.values()):
                if set(k.entidades) <= set(todo) and not (gira and k.tipo in _COTAS_ORIENTADAS):
                    copias[k.id] = self.agregar_cota(k.tipo, [todo[e] for e in k.entidades], k.expresion, k.datos,
                                                     k.referencia)
            self._ligar_cotas_copiadas(self, copias)
        return mapa, mapa_c

    def comprobar_mover(self, ids):
        """ErrorBoceto si `transformar` (sin copiar) no puede mover lo elegido: lo de adentro es fijo o proyectado.
        Es la misma comprobación de `transformar`; el panel la usa para avisar antes de aceptar sin copiar el boceto."""
        fijos = self.puntos_fijos(origen=False)
        if any(self.objetos[i]["bloqueado"] for i in ids if i in self.objetos):
            raise ErrorBoceto("Desbloqueá el objeto antes de moverlo.")
        self.exigir_desbloqueadas(ids, "moverla")
        if any(p in fijos for p in self.puntos_de(ids)):
            raise ErrorBoceto("Hay geometría fija: no se puede mover.")

    def transformar(self, ids, dx=0.0, dy=0.0, angulo=0.0, centro=(0.0, 0.0), copiar=False):
        """Mover/copiar (M): traslada (dx, dy) y gira `angulo` grados alrededor de `centro`. Con `copiar`
        duplica la geometría con sus restricciones internas. Devuelve los ids resultantes."""
        from . import objetos
        ids = objetos.normalizar_seleccion(self, ids)
        objetos_ids = [i for i in ids if i in self.objetos]
        if objetos_ids:
            if copiar:
                objetos_ids = objetos.duplicar(self, objetos_ids, 0, 0)
            objetos.transformar(self, objetos_ids, objetos.afin(dx, dy, angulo, pivote=centro))
            ids = [i for i in ids if i not in self.objetos]
        a = math.radians(angulo)

        def f(q):
            x, y = _rot(q[0] - centro[0], q[1] - centro[1], a)
            return x + centro[0] + dx, y + centro[1] + dy
        if copiar:
            mapa, mapa_c = self._copiar(ids, f, True, angulo)
            return objetos_ids + list(mapa_c.values()) + [mapa[i] for i in ids if i in mapa]
        self.comprobar_mover(ids)
        pts = self._con_vertices_virtuales(ids, self.puntos_de(ids))
        for k in [k for k, r in self.restricciones.items()     # B-538: el anclaje al origen se suelta al moverlo
                  if r.tipo == "fijo" and r.datos.get("origen") and set(r.entidades) <= set(pts)]:
            del self.restricciones[k]
        self._transformar_puntos(pts, f)
        for i in ids:
            if isinstance(self.curvas.get(i), Texto):
                self.curvas[i].angulo += angulo
        if _cambia_orientacion(angulo):        # una horizontal girada 90° ya no es horizontal: si quedara, colapsa
            afectados = set(ids) | set(pts)
            for k in [k for k, r in self.restricciones.items()
                      if r.tipo in _ORIENTADAS and set(r.entidades) <= afectados]:
                del self.restricciones[k]
            for k in [k for k, c in self.cotas.items()
                      if c.tipo in _COTAS_ORIENTADAS and set(c.entidades) <= afectados]:
                del self.cotas[k]
        return objetos_ids + list(ids)

    # ------------------------------------------------------------ limpiar geometría importada
    def _referencias(self):
        """Ids usados por alguna restricción o cota (eso no se toca al limpiar)."""
        return {e for t in (self.restricciones, self.cotas) for v in t.values() for e in v.entidades}

    def _usos_de_puntos(self):
        usos = {}
        for c in self.curvas.values():
            for p in c.puntos():
                usos.setdefault(p, []).append(c.id)
        return usos

    def _fusionar_punto(self, queda, sale):
        """Todo lo que usaba el punto `sale` pasa a usar `queda`; `sale` se borra."""
        for c in self.curvas.values():
            for a in c.PUNTOS:
                if getattr(c, a) == sale:
                    setattr(c, a, queda)
            if isinstance(c, Spline):
                c.pts = [queda if p == sale else p for p in c.pts]
                c.manijas = [[queda if p == sale else p for p in m[:2]] + m[2:] for m in c.manijas]
            if isinstance(c, Texto) and c.marco:
                c.marco = [queda if p == sale else p for p in c.marco]
        for t in (self.restricciones, self.cotas):
            for v in t.values():
                v.entidades = [queda if e == sale else e for e in v.entidades]
        self.puntos.pop(sale, None)

    def _clave_curva(self, c, tol):
        r = lambda q: (round(q[0] / tol), round(q[1] / tol))  # noqa: E731
        if isinstance(c, Linea):
            return ("linea", frozenset((r(self.coords(c.p1)), r(self.coords(c.p2)))))
        if isinstance(c, Circulo):
            return ("circulo", r(self.coords(c.centro)), round(c.radio / tol))
        if isinstance(c, Arco):
            return ("arco", r(self.coords(c.centro)), r(self.coords(c.inicio)), r(self.coords(c.fin)))
        if isinstance(c, Spline):
            pts = tuple(r(self.coords(p)) for p in c.pts)
            return ("spline", c.modo, c.grado, min(pts, pts[::-1]))
        return None

    def limpiar(self, tolerancia=0.01, duplicados=True, huecos=True, colineales=True):
        """Limpieza de geometría importada (SVG, DXF, imagen vectorizada), sin tocar lo que tiene restricciones o
        cotas: borra curvas repetidas, une extremos sueltos que quedaron a menos de `tolerancia` mm (cierra
        huecos para que los contornos formen perfiles) y junta líneas seguidas que están alineadas en una sola.
        Devuelve {"duplicadas": n, "huecos": n, "colineales": n}."""
        if not tolerancia > 0:
            raise ErrorBoceto("La tolerancia tiene que ser positiva.")
        refs = self._referencias()
        salida = {"duplicadas": 0, "huecos": 0, "colineales": 0}
        if duplicados:
            vistas = {}
            for cid in list(self.curvas):
                c = self.curvas[cid]
                clave = None if cid in refs or c.proyectada else self._clave_curva(c, tolerancia)
                if clave is None:
                    continue
                clave = (clave, c.construccion)
                if clave in vistas:
                    self.eliminar(cid)
                    salida["duplicadas"] += 1
                else:
                    vistas[clave] = cid
        if huecos:
            usos = self._usos_de_puntos()
            sueltos = [p for p, cs in usos.items() if len(cs) == 1 and p not in refs
                       and self.curvas[cs[0]].extremos() and p in self.curvas[cs[0]].extremos()
                       and not self.puntos[p].proyectado]
            hechos = set()
            for i, a in enumerate(sueltos):
                if a in hechos:
                    continue
                qa = self.coords(a)
                for b in sueltos[i + 1:]:
                    if b in hechos or usos[b] == usos[a]:
                        continue
                    if math.dist(qa, self.coords(b)) <= tolerancia:
                        self._fusionar_punto(a, b)
                        hechos.update((a, b))
                        salida["huecos"] += 1
                        break
        if colineales:
            cambio = True
            while cambio:
                cambio = False
                usos = self._usos_de_puntos()
                for p, cs in usos.items():
                    if len(cs) != 2 or p in refs or self.puntos[p].proyectado:
                        continue
                    l1, l2 = (self.curvas.get(k) for k in cs)
                    if not (isinstance(l1, Linea) and isinstance(l2, Linea)) or l1.construccion != l2.construccion \
                            or l1.id in refs or l2.id in refs:
                        continue
                    a = l1.p1 if l1.p2 == p else l1.p2
                    b = l2.p1 if l2.p2 == p else l2.p2
                    if a == b or abs(distancia_punto_recta(self.coords(p), self.coords(a), self.coords(b))) > tolerancia:
                        continue
                    qa, qb, qp = self.coords(a), self.coords(b), self.coords(p)
                    if (qp[0] - qa[0]) * (qb[0] - qp[0]) + (qp[1] - qa[1]) * (qb[1] - qp[1]) <= 0:
                        continue                       # vuelve para atrás: no es una sola recta
                    if l1.p1 == p:
                        l1.p1 = b
                    else:
                        l1.p2 = b
                    self.curvas.pop(l2.id)
                    self.puntos.pop(p, None)
                    salida["colineales"] += 1
                    cambio = True
                    break
        self._quitar_huerfanas()
        return salida

    def reflejar(self, ids, centro, horizontal=True):
        """Espejo en el lugar (sin copia) respecto de la recta vertical (horizontal=True) u horizontal que pasa
        por `centro`. Los arcos invierten su sentido para seguir siendo antihorarios. Los textos rectos no se
        pueden espejar así (sus letras no se reflejan): se dejan como están y se devuelven aparte.
        Devuelve (ids espejados, ids de textos que no se espejaron)."""
        from . import objetos
        ids = objetos.normalizar_seleccion(self, ids)
        objetos_ids = [i for i in ids if i in self.objetos]
        if objetos_ids:
            objetos.transformar(self, objetos_ids, objetos.afin(sx=-1 if horizontal else 1,
                                                              sy=1 if horizontal else -1, pivote=centro))
            ids = [i for i in ids if i not in self.objetos]
        cx, cy = centro
        textos = [i for i in ids if isinstance(self.curvas.get(i), Texto) and self.curvas[i].camino is None]
        ids = [i for i in ids if i not in textos]
        self.exigir_desbloqueadas(ids, "espejarla")
        pts = self.puntos_de(ids)
        if any(p in self.puntos_fijos() for p in pts):
            raise ErrorBoceto("Hay geometría fija: no se puede espejar.")
        self._transformar_puntos(pts, (lambda q: (2 * cx - q[0], q[1])) if horizontal else
                                 (lambda q: (q[0], 2 * cy - q[1])))
        for i in ids:
            c = self.curvas.get(i)
            if isinstance(c, (Arco, ArcoElipse)):
                c.inicio, c.fin = c.fin, c.inicio
            elif isinstance(c, Spline):
                _invertir_curvatura(c)
            elif isinstance(c, Texto):                   # texto en curva: sigue a su curva, del otro lado
                c.camino_lado = "der" if c.camino_lado == "izq" else "izq"
                c.camino_pos = 1.0 - c.camino_pos
        return objetos_ids + list(ids), textos

    def comprobar_escalar(self, ids, base):
        """ErrorBoceto si `escalar` no puede mover lo elegido desde `base`: un punto fijo solo vale como base."""
        fijos = self.puntos_fijos(origen=False)
        if any(self.objetos[i]["bloqueado"] for i in ids if i in self.objetos):
            raise ErrorBoceto("Desbloqueá el objeto antes de escalarlo.")
        self.exigir_desbloqueadas(ids, "escalarla")
        if any(p in fijos and math.dist(self.coords(p), base) > 1e-9 for p in self.puntos_de(ids)):
            raise ErrorBoceto("Geometría fija fuera de base: no se escala.")

    def escalar(self, ids, base, factor):
        """Escala del boceto (SKT-SCALE): agranda o achica la geometría desde el punto base; las cotas
        de longitud de esa geometría se multiplican por el factor. Un punto fijo puede ser la base."""
        if factor <= 0:
            raise ErrorBoceto("El factor de escala debe ser positivo.")
        from . import objetos
        ids = objetos.normalizar_seleccion(self, ids)
        objetos_ids = [i for i in ids if i in self.objetos]
        if objetos_ids:
            objetos.transformar(self, objetos_ids, objetos.afin(sx=factor, sy=factor, pivote=base))
            ids = [i for i in ids if i not in self.objetos]
        self.comprobar_escalar(ids, base)
        pts = self._con_vertices_virtuales(ids, self.puntos_de(ids))
        for k in [k for k, r in self.restricciones.items()     # B-512: el anclaje al origen se suelta si el punto se mueve
                  if r.tipo == "fijo" and r.datos.get("origen") and set(r.entidades) <= set(pts)
                  and math.dist(self.coords(r.entidades[0]), base) > 1e-9]:
            del self.restricciones[k]
        self._transformar_puntos(pts, lambda q: (base[0] + factor * (q[0] - base[0]), base[1] + factor * (q[1] - base[1])))
        afectados = set(pts) | set(ids)
        for i in ids:
            c = self.curvas.get(i)
            if isinstance(c, Circulo):
                c.radio *= factor
            elif isinstance(c, (Elipse, ArcoElipse)):
                c.radio_menor *= factor
            elif isinstance(c, Spline):          # la curvatura es 1/mm: crece el tamaño, baja la curvatura
                c.manijas = [[a, b, None if k is None else k / factor] for a, b, k in c.manijas]
            elif isinstance(c, Texto):
                c.altura *= factor
                if c.parametro_altura and c.altura_expr == c.parametro_altura:
                    c.altura_expr = _numero(c.altura) + " mm"  # la API actualiza Text_height; sin autorreferencia
                elif c.altura_expr:                # si no, el recálculo vuelve a la altura de antes
                    try:
                        c.altura_expr = _numero(float(c.altura_expr.replace(",", ".")) * factor)
                    except ValueError:
                        c.altura_expr = f"({c.altura_expr}) * {_numero(factor)}"
                c.espaciado *= factor
                c.ancho_caja *= factor
                c.camino_desfase *= factor
                c.desfase_base *= factor
                c.grosor_decoracion *= factor
                c.ajustes_kerning = [[i, x * factor] for i, x in c.ajustes_kerning]
        escaladas = {kid for kid, k in self.cotas.items() if k.tipo != "angulo" and set(k.entidades) <= afectados}
        nombres = {self.cotas[kid].nombre for kid in escaladas} - {None}
        for kid in escaladas:
            k = self.cotas[kid]
            for clave in ("desfase", "texto"):          # la ubicación de la cota crece con la figura
                if clave in k.datos:
                    k.datos[clave] *= factor
            # Una cota que copia a otra que también se escala («d1» o `igual_a`, el chaflán de distancias iguales)
            # ya crece con ella: multiplicarla otra vez la duplicaba.
            if k.datos.get("igual_a") in escaladas or k.expresion.strip() in nombres:
                continue
            try:
                k.expresion = _numero(float(k.expresion.replace(",", ".")) * factor)
            except ValueError:
                k.expresion = f"({k.expresion}) * {_numero(factor)}"
        return objetos_ids + list(ids)
