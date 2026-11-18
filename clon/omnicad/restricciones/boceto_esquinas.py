"""Boceto 2D: esquinas."""
import math

from .boceto_entidades import CIRCULARES, Circulo, ErrorBoceto, _es_numero, _numero
from .boceto_geometria import (
    _cruces_circulos, _cruces_recta_circulo, evaluar_primitiva, mas_cercano, recta_interseccion,
)


class _Esquinas:
    # ------------------------------------------------------------ MODIFICAR: empalme y chaflán
    def _esquina_por_vertice(self, pid, tipos):
        """Empalme/Chaflán de Fusion por vértice: dos curvas incidentes y sus lados a conservar."""
        if pid not in self.puntos:
            raise ErrorBoceto(f"No existe el vértice {pid} en el boceto.")
        curvas = sorted(c.id for c in self.curvas.values() if pid in (c.extremos() or ()))
        if len(curvas) != 2:
            raise ErrorBoceto("El vértice debe unir exactamente dos curvas.")
        if any(self.curvas[k].tipo not in tipos for k in curvas):
            raise ErrorBoceto("El vértice debe unir dos líneas." if tipos == ("linea",) else
                              "El vértice debe unir dos curvas de tipo línea o arco circular.")
        for k in curvas:
            self._curva_modificable(k)
            if len(set(self.curvas[k].extremos())) != 2:
                raise ErrorBoceto("El vértice une dos curvas abiertas distintas.")
        lados = [self.coords(next(p for p in self.curvas[k].extremos() if p != pid)) for k in curvas]
        return curvas, lados

    def _esquina(self, l1, l2, pick1, pick2):
        """Datos de la esquina entre dos líneas: vértice X (cruce), direcciones desde X hacia lo que se
        conserva y, para cada línea, (punto cercano a X, punto lejano, largo disponible)."""
        (a1, b1), (a2, b2) = self._extremos_linea(l1), self._extremos_linea(l2)
        d1 = (b1[0] - a1[0], b1[1] - a1[1])
        d2 = (b2[0] - a2[0], b2[1] - a2[1])
        X = recta_interseccion(a1, d1, a2, d2)
        if X is None:
            raise ErrorBoceto("Líneas paralelas: no forman esquina.")
        salida = []
        for lid, (a, b), pick in ((l1, (a1, b1), pick1), (l2, (a2, b2), pick2)):
            ln = self.curvas[lid]
            if pick is None:
                pick = a if math.dist(a, X) > math.dist(b, X) else b
            L = math.dist(a, b)
            u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            s = 1.0 if (pick[0] - X[0]) * u[0] + (pick[1] - X[1]) * u[1] >= 0 else -1.0
            d = (u[0] * s, u[1] * s)
            pa = (a[0] - X[0]) * d[0] + (a[1] - X[1]) * d[1]
            pb = (b[0] - X[0]) * d[0] + (b[1] - X[1]) * d[1]
            cerca, lejos = (ln.p1, ln.p2) if pa < pb else (ln.p2, ln.p1)
            salida.append((d, cerca, lejos, max(pa, pb)))
        return X, salida

    def _recortar_esquina(self, l1, l2, X, lados, t1, t2):
        """Lleva los extremos cercanos a la esquina hasta T1 y T2. Si el vértice viejo seguía en uso,
        queda como "vértice virtual" (punto suelto coincidente con ambas líneas) y las cotas de largo de
        las líneas pasan a medirse desde él."""
        (_d1, c1, f1, _L1), (_d2, c2, f2, _L2) = lados
        pt1, pt2 = self.agregar_punto(*t1), self.agregar_punto(*t2)
        cotas_largo = [k for k in self.cotas.values() if k.entidades in ([l1], [l2]) and k.tipo.startswith("distancia")]
        # El punto medio y la igualdad siguen midiendo el lado completo, no el tramo recortado.
        for r in self.restricciones.values():
            if len(r.entidades) != 2 or not set(r.entidades) & {l1, l2}:
                continue
            if r.tipo == "punto_medio":
                punto, lid = r.entidades
                r.entidades = [punto, *self.curvas[lid].extremos()]
            elif r.tipo == "igual":
                r.entidades = [p for lid in r.entidades for p in self.curvas[lid].extremos()]
        for lid, cerca, nuevo in ((l1, c1, pt1), (l2, c2, pt2)):
            ln = self.curvas[lid]
            if ln.p1 == cerca:
                ln.p1 = nuevo
            else:
                ln.p2 = nuevo
        virtual = None
        vertices = {c1, c2}
        if cotas_largo or any(self._punto_en_uso(v) or self._punto_referenciado(v) for v in vertices):
            virtual = c1 if c1 == c2 else self.agregar_punto(*X)
            self.puntos[virtual].x, self.puntos[virtual].y = X
            for lid in (l1, l2):
                self.agregar_restriccion("coincidente", [virtual, lid])
            for k in cotas_largo:
                lejos = f1 if k.entidades == [l1] else f2
                ln = self.curvas[k.entidades[0]]
                k.entidades = [virtual, lejos] if ln.p2 == lejos else [lejos, virtual]
            # Los extremos distintos de la misma esquina pasan al único vértice virtual.
            for p in vertices - {virtual}:
                if math.dist(self.coords(p), X) < 1e-9:
                    self._fusionar_punto(virtual, p)
        self._soltar_puntos_viejos(vertices, virtual, X)
        self._depurar(vertices - {virtual})
        return pt1, pt2, virtual

    def empalme(self, c1, c2, radio, pick1=None, pick2=None, expresion=None, vertice=None):
        """Empalme (SKT-ADD-FILLETS): redondea la esquina entre dos curvas con un arco tangente de
        radio dado; recorta las curvas, agrega las tangencias y la cota de radio. Entre paralelas,
        crea un semicírculo de radio igual a la mitad de su separación. `vertice` identifica la unión
        elegida si las curvas se cruzan otra vez. Devuelve el arco."""
        if radio <= 0:
            raise ErrorBoceto("El radio del empalme debe ser positivo.")
        for k in (c1, c2):
            self._curva_modificable(k)
        tipos = (self.tipo_de(c1), self.tipo_de(c2))
        paralelas = False
        if tipos == ("linea", "linea"):
            d1, d2 = self._direccion(c1), self._direccion(c2)
            paralelas = abs(d1[0] * d2[1] - d1[1] * d2[0]) < 1e-12
        if paralelas:
            F, pt1, pt2, radio = self._empalme_paralelas(c1, c2, pick1, pick2)
            expresion = None       # el radio lo determina la separación, no la expresión pedida
        elif tipos == ("linea", "linea"):
            X, lados = self._esquina(c1, c2, pick1, pick2)
            (d1, *_r1), (d2, *_r2) = lados
            theta = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))
            if theta < 1e-6 or theta > math.pi - 1e-6:
                raise ErrorBoceto("Las líneas no forman una esquina.")
            tang = radio / math.tan(theta / 2)
            if tang < 1e-4:            # B-510: casi colineales o radio ínfimo, el arco quedaría de largo ~0 (Fusion: «Failed to create fillet»)
                raise ErrorBoceto("El empalme no entra: radio muy chico.")
            if tang >= lados[0][3] - 1e-9 or tang >= lados[1][3] - 1e-9:
                raise ErrorBoceto("El radio es muy grande para esas líneas.")
            t1 = (X[0] + tang * d1[0], X[1] + tang * d1[1])
            t2 = (X[0] + tang * d2[0], X[1] + tang * d2[1])
            bis = (d1[0] + d2[0], d1[1] + d2[1])
            nb = math.hypot(*bis)
            h = radio / math.sin(theta / 2)
            F = (X[0] + bis[0] / nb * h, X[1] + bis[1] / nb * h)
            pt1, pt2, _v = self._recortar_esquina(c1, c2, X, lados, t1, t2)
        else:
            F, pt1, pt2 = self._empalme_general(c1, c2, radio, pick1, pick2, vertice)
        a = (self.coords(pt1)[0] - F[0], self.coords(pt1)[1] - F[1])
        b = (self.coords(pt2)[0] - F[0], self.coords(pt2)[1] - F[1])
        ini, fin = (pt1, pt2) if paralelas or a[0] * b[1] - a[1] * b[0] > 0 else (pt2, pt1)
        arco = self.agregar_arco_centro(F, ini, fin)
        self.agregar_restriccion("tangente", [c1, arco])
        self.agregar_restriccion("tangente", [c2, arco])
        self.agregar_cota("radio", [arco], expresion or _numero(radio))
        return arco

    def _empalme_paralelas(self, c1, c2, pick1, pick2):
        """Semicírculo tangente entre paralelas: cierra del lado opuesto a los puntos que se conservan."""
        a1, b1 = self._extremos_linea(c1)
        a2, b2 = self._extremos_linea(c2)
        if min(math.dist(a1, b1), math.dist(a2, b2)) < 1e-9:
            raise ErrorBoceto("Empalme: dos líneas de largo positivo.")
        d = self._direccion(c1)
        if pick1 is not None:
            invertir = math.dist(pick1, a1) > math.dist(pick1, b1)
        elif pick2 is not None:
            conservar, cerrar = (a2, b2) if math.dist(pick2, a2) <= math.dist(pick2, b2) else (b2, a2)
            invertir = (cerrar[0] - conservar[0]) * d[0] + (cerrar[1] - conservar[1]) * d[1] < 0
        else:
            invertir = False
        if invertir:
            d = (-d[0], -d[1])
        distancia = (a2[0] - a1[0]) * -d[1] + (a2[1] - a1[1]) * d[0]
        if abs(distancia) < 1e-9:
            raise ErrorBoceto("Líneas sobre la misma recta: no hay hueco.")
        lados = []
        for cid, pick in ((c1, pick1), (c2, pick2)):
            ids = sorted(self.curvas[cid].extremos(), key=lambda pid: (
                (self.coords(pid)[0] - a1[0]) * d[0] + (self.coords(pid)[1] - a1[1]) * d[1]))
            if pick is not None and math.dist(pick, self.coords(ids[0])) > math.dist(pick, self.coords(ids[1])):
                raise ErrorBoceto("Elegí el mismo lado en las dos líneas.")
            lados.append(ids)
        cierre = max((self.coords(ids[1])[0] - a1[0]) * d[0] +
                     (self.coords(ids[1])[1] - a1[1]) * d[1] for ids in lados)
        t1 = (a1[0] + cierre * d[0], a1[1] + cierre * d[1])
        t2 = (t1[0] - distancia * d[1], t1[1] + distancia * d[0])
        F = ((t1[0] + t2[0]) / 2, (t1[1] + t2[1]) / 2)
        pts, viejos = [], []
        for cid, ids, t in zip((c1, c2), lados, (t1, t2), strict=True):
            pid = self.agregar_punto(*t)
            pts.append(pid)
            ln = self.curvas[cid]
            if ln.p1 == ids[1]:
                ln.p1 = pid
            else:
                ln.p2 = pid
            viejos.append(ids[1])
            self._sin_cotas_de_largo(cid)
        self._soltar_puntos_viejos(viejos)
        self._depurar(viejos)
        if (t1[0] - F[0]) * d[1] - (t1[1] - F[1]) * d[0] < 0:
            pts.reverse()
        return F, *pts, abs(distancia) / 2

    def _empalme_general(self, c1, c2, r, pick1, pick2, vertice=None):
        """Empalme con arcos o círculos: el centro sale de cruzar las curvas desfasadas en r."""
        def portadoras(cid):
            prim = self.primitivas(cid)[0]
            if prim[0] == "linea":
                a, b = prim[2], prim[3]
                L = math.dist(a, b)
                d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
                n = (-d[1], d[0])
                return prim, [("recta", (a[0] + s * r * n[0], a[1] + s * r * n[1]), d) for s in (1, -1)]
            if prim[0] in CIRCULARES:
                c, R = prim[2], prim[3]
                return prim, [("circ", c, R + r)] + ([("circ", c, abs(R - r))] if abs(R - r) > 1e-9 else [])
            raise ErrorBoceto("Empalme: líneas, arcos y círculos.")
        p1, o1 = portadoras(c1)
        p2, o2 = portadoras(c2)
        candidatos = []
        for g1 in o1:
            for g2 in o2:
                if g1[0] == "recta" and g2[0] == "recta":
                    q = recta_interseccion(g1[1], g1[2], g2[1], g2[2])
                    candidatos += [q] if q else []
                elif g1[0] == "recta":
                    candidatos += _cruces_recta_circulo(g1[1], g1[2], g2[1], g2[2])
                elif g2[0] == "recta":
                    candidatos += _cruces_recta_circulo(g2[1], g2[2], g1[1], g1[2])
                else:
                    candidatos += _cruces_circulos(g1[1], g1[2], g2[1], g2[2])
        mejor = None
        for F in candidatos:
            pies = []
            for prim in (p1, p2):
                if prim[0] == "linea":
                    a, b = prim[2], prim[3]
                    L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
                    t = ((F[0] - a[0]) * (b[0] - a[0]) + (F[1] - a[1]) * (b[1] - a[1])) / L2
                    pies.append(((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), t, prim))
                else:
                    c, R = prim[2], prim[3]
                    dd = math.dist(F, c) or 1e-12
                    q = (c[0] + (F[0] - c[0]) * R / dd, c[1] + (F[1] - c[1]) * R / dd)
                    pies.append((q, mas_cercano(prim, q)[0], prim))
            if any(math.dist(evaluar_primitiva(prim, t)[0], q) > 1e-6 for q, t, prim in pies if prim[0] == "arco"):
                continue
            ref1 = pick1 or pies[0][0]
            ref2 = pick2 or pies[1][0]
            referencia = self.coords(vertice) if vertice is not None else None
            puntaje = math.dist(pies[0][0], referencia or ref1) + math.dist(pies[1][0], referencia or ref2)
            if mejor is None or puntaje < mejor[0]:
                mejor = (puntaje, F, pies)
        if mejor is None:
            raise ErrorBoceto("No entra un empalme de ese radio.")
        _, F, pies = mejor
        if math.dist(pies[0][0], pies[1][0]) < 1e-4:      # B-510: casi tangentes, el arco quedaría de largo ~0
            raise ErrorBoceto("El empalme no entra: radio muy chico.")
        puntos_t, viejos = [], []
        for cid, (q, t, prim), pick in ((c1, pies[0], pick1), (c2, pies[1], pick2)):
            pid = self.agregar_punto(*q)
            puntos_t.append(pid)
            c = self.curvas[cid]
            if isinstance(c, Circulo):
                self.agregar_restriccion("coincidente", [pid, cid])
                continue
            tp = mas_cercano(prim, pick)[0] if pick is not None else None
            ini, fin = c.extremos()
            if vertice is not None:
                reemplazo = vertice
            elif tp is None:
                reemplazo = ini if math.dist(self.coords(ini), q) < math.dist(self.coords(fin), q) else fin
            else:
                reemplazo = ini if tp > t else fin
            for a in ("p1", "p2", "inicio", "fin"):
                if getattr(c, a, None) == reemplazo:
                    setattr(c, a, pid)
            viejos.append(reemplazo)
            self._sin_cotas_de_largo(cid)
        self._soltar_puntos_viejos(viejos)
        self._depurar(viejos)
        return F, puntos_t[0], puntos_t[1]

    def chaflan(self, l1, l2, distancia, distancia2=None, angulo=None, pick1=None, pick2=None, expresion=None,
                expresion2=None):
        """Chaflán (SKT-ADD-CHAMFERS) entre dos líneas: de distancias iguales, de dos distancias
        (`distancia2`) o de distancia y ángulo (`angulo`, grados). Agrega la línea, el vértice virtual
        y las cotas; `expresion` y `expresion2` son los textos del primer y del segundo valor, para que las
        cotas sigan a sus parámetros. Devuelve la línea del chaflán."""
        for k in (l1, l2):
            if self.tipo_de(self._curva_modificable(k).id) != "linea":
                raise ErrorBoceto("El chaflán se aplica entre dos líneas.")
        if distancia <= 0:
            raise ErrorBoceto("La distancia del chaflán debe ser positiva.")
        X, lados = self._esquina(l1, l2, pick1, pick2)
        (d1, *_r1), (d2, *_r2) = lados
        theta = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))
        if angulo is not None:
            alfa = math.radians(angulo)
            if not 0 < alfa < math.pi - theta:
                raise ErrorBoceto("Ese ángulo no corta la esquina.")
            distancia2 = distancia * math.sin(alfa) / math.sin(theta + alfa)
        e1, e2 = distancia, (distancia if distancia2 is None else distancia2)
        if e1 >= lados[0][3] - 1e-9 or e2 >= lados[1][3] - 1e-9:
            raise ErrorBoceto("La distancia es demasiado grande.")
        t1 = (X[0] + e1 * d1[0], X[1] + e1 * d1[1])
        t2 = (X[0] + e2 * d2[0], X[1] + e2 * d2[1])
        pt1, pt2, virtual = self._recortar_esquina(l1, l2, X, lados, t1, t2)
        if virtual is None:
            virtual = self.agregar_punto(*X)
            for lid in (l1, l2):
                self.agregar_restriccion("coincidente", [virtual, lid])
        ln = self.agregar_linea(pt1, pt2)
        expr = expresion or _numero(e1)
        primera = self.agregar_cota("distancia", [virtual, pt1], expr)
        if angulo is not None:
            # La cota mide entre el chaflán y l1: según el lado puede ser el suplemento del ángulo pedido.
            directo = abs(self.medir_cota("angulo", [ln, l1]) - angulo) < 1e-6
            texto = _numero(angulo if directo else 180 - angulo)
            if expresion2 and not _es_numero(expresion2):
                texto = expresion2 if directo else f"180 deg - ({expresion2})"
            self.agregar_cota("angulo", [ln, l1], texto)
        elif distancia2 is None:
            # Distancias iguales (BOC-25): al nombrarse las cotas, la 2.ª pasa a ser «dN» de la 1.ª
            # (Documento._tabla_cotas), así editar una arrastra a la otra. Con distancia2, cada una es independiente.
            self.agregar_cota("distancia", [virtual, pt2], expr, {"igual_a": primera})
        else:
            self.agregar_cota("distancia", [virtual, pt2], expresion2 or _numero(e2))
        return ln
