"""LienzoCrearMixin: métodos del lienzo por tema."""

from .editor_boceto_comun import (
    ANGULO,
    AYUDA_RESTRICCION,
    COMANDO_PROYECCION,
    CURVA_TEXTO,
    EJES_ORIGEN,
    ErrorBoceto,
    HERRAMIENTAS,
    NOMBRES_RESTRICCION,
    PATRON,
    QColor,
    QPen,
    QPointF,
    Qt,
    RANURAS_RECTAS,
    RESTRICCIONES_HERRAMIENTA,
    SELECCION,
    SPLINES,
    TRANSFORMAR,
    Texto,
    _barrido,
    _espaciado_mm,
    _espaciado_porcentaje,
    _numero,
    _registro_uso,
    agregar_arco_tangente,
    agregar_circulo_puntos,
    agregar_estrella,
    agregar_linea_medio,
    agregar_poligono,
    agregar_rectangulo_3p,
    agregar_rectangulo_centro,
    centro_arco_tangente,
    centro_poligono_arista,
    circunferencia_3_puntos,
    formato,
    fraccion_en_camino,
    lado_natural,
    math,
    proporcion_estrella,
    puntos_espiral,
    puntos_primitiva,
    redondear_estrella,
    redondeos_estrella,
    resolver,
    validar_lados_poligono,
    validar_puntas_estrella,
)


class LienzoCrearMixin:
    def set_herramienta(self, h):
        self.confirmar_texto_pendiente()          # cambiar de herramienta no pierde el texto escrito
        nota = self.descartar_proyeccion()        # lo no aceptado no se confirma solo: se descarta y se avisa
        self.patron.cerrar()
        self.transformar.cerrar()
        self._iso_pos = self._iso_texto = None
        self._borrar_previa_iso()
        if h == "texto":
            self.opciones.update(pivote_texto=None, marco_texto=False, parametro_texto=None, valor_parametro_texto="")
        if self._ultima_figura is not None and self._ultima_figura["h"] != h:
            self._ultima_figura = None            # P-154: Lados rehace solo lo recién dibujado con esta herramienta
        self.herramienta = h
        if h != "seleccionar":
            self.ultima_herramienta = h           # para «Repetir» del menú radial
        self.clics, self.picks, self.picks_xy = [], [], []
        self.inf_actual = self.inferencia = self._inf_inicio = self._inf_bloqueo = None
        self.inf_lista, self._inf_alt = [], 0
        self.fase = None
        self._eje_simetria = self._previa_sim = self._firma_sim = self._estado_sim = None
        self._error_simetria = ""
        self._previa_recorte = None
        self._recorte_arrastre = None
        self._esperando_ubicacion = False
        self._opc_cota = {}
        self._revincular = self._eje_giro = None
        self._cerrar_entrada()
        self._reiniciar_vivo()
        nombre, ayuda = HERRAMIENTAS.get(h, (NOMBRES_RESTRICCION.get(h, h), ""))
        if h in RESTRICCIONES_HERRAMIENTA:
            ayuda = AYUDA_RESTRICCION[h]
            if self._restriccion_con_seleccion():
                if nota:
                    self.mensaje.emit(nota)
                return
        if h in PATRON:
            self.patron.iniciar(h)
        elif h in TRANSFORMAR:
            self.transformar.iniciar(h)
        elif h in SELECCION:
            self.fase = "seleccion"
            if self._seleccion_util():
                self._avanzar_seleccion(avisar=False)
        elif h == "desfase":
            self._desfase_con_seleccion()
        texto = f"{nombre}: {ayuda}" if ayuda else nombre
        self.mensaje.emit(f"{nota} {texto}" if nota else texto)
        self._emitir_simetria()
        self.herramienta_cambiada.emit(h)
        _registro_uso("boceto_herramienta", {"herramienta": h})
        self._emitir_proyeccion()
        self.update()

    def _hay_operacion(self):
        """Algo a medias en la herramienta: clics puestos, cota o selección a medio elegir, caja de valor o texto
        abiertos, o una fase de la herramienta."""
        return bool(self.clics or self.picks or self.entrada is not None or self._tangente is not None
                    or self.fase not in (None, "seleccion"))

    def cancelar(self):
        """Esc y clic derecho sin arrastrar: si hay algo a medias lo corta y la herramienta sigue; si no, sale de la
        herramienta y vuelve a Seleccionar; en Seleccionar, borra la selección."""
        if self.objetos.cancelar():
            return
        if self._eligiendo_punto is not None:
            self._terminar_eleccion()
            return
        if self._arrastre is not None:             # B-111: Esc en pleno arrastre lo cancela y deja el boceto como estaba
            self._arrastre = None
            self._restaurar(self.historial.pop())
            self._cache_cortes = {}
            self.cambio.emit()
            self.update()
            return
        if self.herramienta in ("desfase", "texto") or self.herramienta in RESTRICCIONES_HERRAMIENTA:
            self.set_herramienta("seleccionar")    # B-654/B-655: como Fusion, un solo Esc sale del comando
            return
        if self.herramienta == "simetria":         # el panel SIMETRÍA se cierra entero, sin tocar el boceto
            self.cancelar_simetria()
            return
        if self.herramienta in COMANDO_PROYECCION and self._revincular is None:     # y la tarjeta de Proyectar
            self.cancelar_proyeccion()
            return
        if self.herramienta in PATRON:             # lo mismo con el panel del patrón
            self.patron.cancelar()
            return
        if self.herramienta in TRANSFORMAR:        # y con el de Escala y Mover/copiar
            self.transformar.cancelar()
            return
        self.inf_actual = self.inferencia = self._inf_inicio = self._inf_bloqueo = None
        self.inf_lista, self._inf_alt = [], 0
        if self._hay_operacion():
            self._cerrar_entrada()
            if self._proy_fusion:
                self._quitar_proyecciones(self._proy_fusion)
            self.clics, self.picks, self.picks_xy = [], [], []
            self._esperando_ubicacion = False
            self._opc_cota = {}
            self._ultima_linea = None
            self._reiniciar_vivo()
            if self.fase is not None:
                self.fase = "seleccion"
        elif self.herramienta != "seleccionar":
            self.set_herramienta("seleccionar")
        else:
            self.seleccion, self.perfiles_sel = [], []
        self._notificar_seleccion()
        self.update()

    def _crear_linea(self, a, b, inferencia=None, cota=None):
        (p1, xa), (p2, xb) = a, b
        nueva = {}
        inf_inicio, inf_fin = self._inf_inicio, self.inf_actual
        post_crear = self._post_crear

        def restringir(nuevas):
            if post_crear is not None:
                post_crear(nuevas)
            linea = self.b.curvas[nueva["id"]]
            pendientes = [(linea.p1, inf_inicio), (linea.p2, inf_fin)]
            if not inferencia or (p1 is not None and p2 is not None):
                pendientes = [(pid, inf) for pid, inf in pendientes
                              if inf is None or inf.tipo not in ("horizontal", "vertical")]
            self._restringir_inferencias(linea.id, pendientes)

        def crear():
            lid = self.b.agregar_linea(p1 if p1 is not None else xa, p2 if p2 is not None else xb, self.construccion)
            nueva["id"] = lid
            if inferencia and inf_fin is None and not (p1 is not None and p2 is not None):
                self.b.agregar_restriccion(inferencia, [lid])
            if cota:
                self.b.agregar_cota("distancia", [lid], cota)
        self._post_crear = restringir
        try:
            if self.aplicar_cambio(crear):
                return nueva["id"]
        finally:
            self._post_crear = post_crear
        return None

    def _restringir_inferencias(self, linea, extremos):
        """Ensaya las restricciones inferidas sin perder la geometría si alguna entra en conflicto."""
        pendientes = [(pid, inf) for pid, inf in extremos if inf is not None and inf.restriccion]
        if not pendientes:
            return
        antes = self.b.a_dict()
        try:
            for pid, inf in pendientes:
                tipo, *objetivos = inf.restriccion
                entidad = pid if tipo in ("punto_medio", "coincidente") else linea
                self.b.agregar_restriccion(tipo, [entidad, objetivos[0]] if objetivos else [entidad])
                for adicional, destino in objetivos[1:]:
                    self.b.agregar_restriccion(adicional, [pid, destino])
            if not resolver(self.b.copia(), self.valores_cotas()).ok:
                raise ErrorBoceto("Conflicto con las restricciones existentes.")
        except ErrorBoceto:
            self._restaurar(antes)

    def _guardar_inferencia_clic(self, pid, xy):
        """BOC-9: qué une el clic en `xy` (punto existente, punto medio o punto sobre una curva), para restringir el
        punto que la herramienta cree ahí. Línea, línea de punto medio y rectángulo 3p también restringen su lado;
        círculo convierte el radio perpendicular en tangencia con la línea objetivo."""
        inf = self.inf_actual
        if pid is not None:
            union = ("coincidente", pid)
        elif inf is None or not inf.restriccion or inf.objetivo is None:
            return
        elif inf.restriccion[0] in ("coincidente", "punto_medio"):
            union = inf.restriccion[:2]
        elif inf.tipo == "tangente" or ("coincidente", inf.objetivo) in inf.restriccion[2:]:
            union = ("coincidente", inf.objetivo)          # el punto de contacto queda sobre la curva
        else:
            return
        self._inf_clics.append((xy, *union))
        if inf is not None and inf.tipo == "interseccion":
            self._inf_clics.append((xy, *inf.restriccion[2]))      # el punto queda sobre las dos curvas

    def _restringir_clics(self, puntos_nuevos, curvas_nuevas):
        """Agrega las uniones guardadas por `_guardar_inferencia_clic` a los puntos nuevos que quedaron en el lugar
        del clic. Cada una se ensaya sola: si choca con lo que ya hay, se descarta sin perder la geometría."""
        pendientes, self._inf_clics = self._inf_clics, []
        for xy, tipo, objetivo in pendientes:
            if objetivo in curvas_nuevas or objetivo in puntos_nuevos:
                continue
            pid = next((p for p in sorted(puntos_nuevos) if math.dist(self.b.coords(p), xy) < 1e-6), None)
            if pid is None or any(r.tipo == tipo and set(r.entidades) == {pid, objetivo}
                                  for r in self.b.restricciones.values()):
                continue
            antes = self.b.a_dict()
            try:
                self.b.agregar_restriccion(tipo, [pid, objetivo])
                if not resolver(self.b.copia(), self.valores_cotas()).ok:
                    raise ErrorBoceto("Conflicto con las restricciones existentes.")
            except ErrorBoceto:
                self._restaurar(antes)

    def _curvas_con_extremo(self, pid):
        """Curvas abiertas (línea, arco, spline, cónica…) que terminan en el punto `pid`."""
        return [k.id for k in self.b.curvas.values() if pid in (k.extremos() or ())]

    def _crear_arco_tangente(self, pid, linea, fin):
        """Arco desde el punto `pid` (extremo de la curva `linea`) hasta `fin`, tangente a ella."""
        (pfin, xyf) = fin
        p, salida = self.b._salida_extremo(linea, pid)
        geometria = centro_arco_tangente(p, (p[0] - salida[0], p[1] - salida[1]), xyf)
        if geometria is None:
            return None
        nuevo = {}

        def crear():
            destino = pfin if pfin is not None else xyf
            nuevo["arco"] = agregar_arco_tangente(self.b, linea, pid, destino, geometria, self.construccion)
        if self.aplicar_cambio(crear):
            return nuevo["arco"]
        return None

    def _rectangulo_3p(self, a, b, c):
        return agregar_rectangulo_3p(self.b, a, b, c, self.construccion)

    def _poligono(self, centro, vertice, lados, tipo, centro_pid=None):
        validar_lados_poligono(lados)
        r = math.dist(centro, vertice)
        if r < 1e-9:
            raise ErrorBoceto("El polígono necesita un tamaño.")
        giro = math.atan2(vertice[1] - centro[1], vertice[0] - centro[0])
        if tipo == "circunscrito":
            giro -= math.pi / lados
        antes = set(self.b.puntos)
        ls, cid = agregar_poligono(self.b, centro, r, lados, giro, tipo == "circunscrito", self.construccion, centro_pid)
        self._ultima_figura = {"h": "poligono_" + tipo, "lineas": ls, "circulos": [cid], "arcos": [],
                               "puntos": set(self.b.puntos) - antes}
        return ls, cid

    def _estrella(self, centro, punta, centro_pid=None, existentes=None):
        """Estrella (BOC-84) con las opciones de la tarjeta: puntas, interior (0 = la regular) y redondeos."""
        o = self.opciones
        puntas = validar_puntas_estrella(int(o["puntas_estrella"]))
        r = math.dist(centro, punta)
        if r < 1e-9:
            raise ErrorBoceto("La estrella necesita un tamaño.")
        interior = self._interior_estrella(r)
        if existentes is not None:
            ci = existentes[1]
            if not any(k.entidades == [ci] for k in self.b.cotas.values()):   # B-496: Interior y Salto valen al rehacer
                self.b.curvas[ci].radio = interior
            interior = self.b.radio(ci)
        giro = math.atan2(punta[1] - centro[1], punta[0] - centro[0])
        antes = set(self.b.puntos)
        ls, ce, ci = agregar_estrella(self.b, centro, r, puntas, giro, interior, self.construccion, centro_pid,
                                      bool(o["circulos_estrella"]), existentes)
        pedidos = (o["redondeo_puntas"], o["redondeo_valles"])
        rp, rv = redondeos_estrella(r, interior, puntas, *pedidos)
        if (rp, rv) != pedidos:                  # B-496: achicados, así el redondeo no se come puntas
            self.mensaje.emit(f"⚠ El redondeo no entraba: va a {formato.numero(rp)} mm en las puntas y "
                              f"{formato.numero(rv)} mm en los valles.")
        arcos = redondear_estrella(self.b, ls, rp, rv)
        # sin círculos guía no hay centro ni radio que conservar: no se rehace
        self._ultima_figura = None if ce is None else {"h": "estrella", "lineas": ls, "circulos": [ce, ci],
                                                         "arcos": arcos[0] + arcos[1], "giro": giro,
                                                         "puntos": set(self.b.puntos) - antes}
        return ls

    def _vertices_virtuales_estrella(self):
        """B-496: las esquinas filosas de una estrella redondeada (puntos sin curva) no se dibujan, como Fusion."""
        sueltos = {e for r in self.b.restricciones.values() if str(r.datos.get("grupo", "")).startswith("estrella")
                   for e in r.entidades if e in self.b.puntos}
        return sueltos and sueltos - {q for c in self.b.curvas.values() for q in c.puntos()}

    def _interior_estrella(self, r):
        """Radio de los valles: el % escrito o, con 0, el de la estrella regular {puntas/salto}."""
        o = self.opciones
        if o["interior_estrella"]:
            return r * o["interior_estrella"] / 100
        puntas = int(o["puntas_estrella"])
        return r * proporcion_estrella(puntas, max(2, min(int(o["salto_estrella"]), math.ceil(puntas / 2) - 1)))

    def cambiar_lados(self, n):
        """Lados desde la tarjeta: valen para el polígono que se va a dibujar y, si recién se dibujó uno, lo rehacen
        (P-154)."""
        self.lados = n
        self.rehacer_figura()

    def rehacer_figura(self):
        """P-154: el polígono o la estrella recién dibujados, con la cantidad de lados (o las opciones de la estrella)
        de ahora. Mismo centro, radio, giro y tipo; los círculos guía no se tocan, así sus cotas siguen. Un paso de
        deshacer. False si no hay figura que rehacer (otra herramienta, un dibujo en curso o ya se borró)."""
        f = self._ultima_figura
        if f is None or self.clics or self.herramienta != f["h"] or \
                not all(k in self.b.curvas for k in f["lineas"] + f["circulos"]):
            self.update()
            return False
        b = self.b
        ce = f["circulos"][0]
        centro_pid = b.curvas[ce].centro
        centro, radio = b.coords(centro_pid), b.radio(ce)
        if f["h"] == "estrella":
            giro = f["giro"]
        else:
            v0 = b.coords(b.curvas[f["lineas"][0]].p1)
            giro = math.atan2(v0[1] - centro[1], v0[0] - centro[0])
        punta = (centro[0] + radio * math.cos(giro), centro[1] + radio * math.sin(giro))

        def rehacer():
            for k in f["lineas"] + f["arcos"]:
                if k in b.curvas:
                    b.eliminar(k)
            # solo los puntos que creó la figura (vértices, extremos recortados, vértices virtuales) y que ya nadie usa:
            # un punto de otra curva donde se enganchó un clic se queda
            for p in f["puntos"] - {centro_pid}:
                if p in b.puntos and not b._punto_en_uso(p):
                    b.eliminar(p)
            antes = set(b.puntos)
            if f["h"] == "estrella":
                self._estrella(centro, punta, existentes=tuple(f["circulos"]))
            else:
                tipo = "circunscrito" if f["h"] == "poligono_circunscrito" else "inscrito"
                ls, _cid = agregar_poligono(b, centro, radio, self.lados, giro, tipo == "circunscrito",
                                            self.construccion, circulo=ce)
                self._ultima_figura = dict(f, lineas=ls, puntos=set(b.puntos) - antes)
        return self.aplicar_cambio(rehacer, anclar=False)

    @staticmethod
    def _eje_ranura(h, pts):
        """Centros de los extremos de una ranura recta."""
        if h == "ranura_punto":
            m, b = pts[0], pts[1]
            return (2 * m[0] - b[0], 2 * m[1] - b[1]), b
        return pts[0], pts[1]

    @staticmethod
    def _arco_ranura(h, pts):
        """(centro, radio) del eje de una ranura de arco."""
        if h == "ranura_arco_3p":
            circ = circunferencia_3_puntos(pts[0], pts[2], pts[1])
            return ((circ[0], circ[1]), circ[2]) if circ else (pts[0], 0.0)
        return pts[0], math.dist(pts[0], pts[1])

    def _ancho_ranura(self, h, c, cur):
        """Medio ancho de la ranura: distancia del último clic al eje (recto o de arco)."""
        pts = [p for _, p in c]
        if h not in RANURAS_RECTAS:
            centro, R = self._arco_ranura(h, pts)
            return abs(math.dist(cur, centro) - R)
        a, b = self._eje_ranura(h, pts)
        L = math.dist(a, b) or 1e-9
        return abs((b[0] - a[0]) * (cur[1] - a[1]) - (b[1] - a[1]) * (cur[0] - a[0])) / L

    def _crear_ranura(self, h, c, cur):
        tipo = {"ranura_centro": "centro", "ranura_total": "total", "ranura_punto": "punto",
                "ranura_arco_3p": "arco_3p", "ranura_arco_centro": "arco_centro"}[h]
        n = 2 if tipo in ("centro", "total", "punto") else 3
        puntos = [pid if pid is not None and tipo == "centro" else xy for pid, xy in c[:n]]
        if tipo == "arco_3p":
            puntos = [c[0][1], c[1][1], c[2][1]]
        ancho = 2 * self._ancho_ranura(h, c[:n], cur)
        self.aplicar_cambio(lambda: self.b.agregar_ranura(tipo, puntos, ancho, self.construccion))

    def _espiral(self, centro, inicio, vueltas, paso):
        pts = puntos_espiral(centro, inicio, vueltas, paso)
        return self.b.agregar_spline(pts, "ajuste", 3, False, construccion=self.construccion)

    def _rho_conica(self, punto):
        """Rho de Fusion: proyección relativa sobre el segmento punto medio–vértice."""
        a, b, v = [xy for _, xy in self.clics[:3]]
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        dx, dy = v[0] - m[0], v[1] - m[1]
        largo2 = dx * dx + dy * dy
        if largo2 < 1e-18:
            return 0.5
        rho = ((punto[0] - m[0]) * dx + (punto[1] - m[1]) * dy) / largo2
        return max(1e-6, min(1 - 1e-6, rho))      # 0 y 1 son cónicas degeneradas

    def _actualizar_rho_conica(self, pos):
        """El ratón cambia Rho sin ajuste a rejilla; lo escrito conserva prioridad."""
        self.cursor = self.a_mm(pos)
        self.inf_actual = self.inferencia = None
        campo = self.entrada.campos[0]
        if not campo.isModified():
            campo.setText(f"{self._rho_conica(self.cursor):.12g}")
            campo.selectAll()

    def _procesar_clics(self):
        h, c = self.herramienta, self.clics
        if h == "linea" and len(c) == 2:
            if math.dist(c[0][1], c[1][1]) < 1e-9:
                c.pop()
                return
            lid = self._crear_linea(c[0], c[1], self.inferencia)
            if lid is not None:
                fin = self.b.curvas[lid].p2
                self.clics, self._ultima_linea = [(fin, self.b.coords(fin))], lid
            else:
                self.clics = []
        elif h == "linea_medio" and len(c) == 2:
            (pm, m), (pe, e) = c
            self.aplicar_cambio(lambda: agregar_linea_medio(self.b, pm if pm is not None else m,
                                                            pe if pe is not None else e, self.construccion))
            self.clics = []
        elif h == "rectangulo" and len(c) == 2:
            (p1, a), (p2, b) = c

            def crear():
                ls = self.b.agregar_rectangulo(a, b, self.construccion)
                if p1 is not None:
                    self.b.agregar_restriccion("coincidente", [self.b.curvas[ls[0]].p1, p1])
                if p2 is not None:
                    self.b.agregar_restriccion("coincidente", [self.b.curvas[ls[2]].p1, p2])
            self.aplicar_cambio(crear)
            self.clics = []
        elif h == "rectangulo_3p" and len(c) == 3:
            self.aplicar_cambio(lambda: self._rectangulo_3p(c[0][1], c[1][1], c[2][1]))
            self.clics = []
        elif h == "rectangulo_centro" and len(c) == 2:
            (pc, m), (_, k) = c
            self.aplicar_cambio(lambda: agregar_rectangulo_centro(self.b, pc if pc is not None else m, k,
                                                                  self.construccion))
            self.clics = []
        elif h == "circulo" and len(c) == 2:
            (pc, a), (_, b) = c
            r = math.dist(a, b)
            if r < 1e-9:
                c.pop()
                return
            self.aplicar_cambio(lambda: self.b.agregar_circulo(pc if pc is not None else a, r, self.construccion))
            self.clics = []
        elif h == "circulo_2p" and len(c) == 2:
            (_, a), (_, b) = c
            r = math.dist(a, b) / 2
            if r < 1e-9:
                c.pop()
                return
            self.aplicar_cambio(lambda: agregar_circulo_puntos(self.b, [a, b], self.construccion))
            self.clics = []
        elif h == "circulo_3p" and len(c) == 3:
            self.aplicar_cambio(lambda: agregar_circulo_puntos(self.b, [p for _, p in c], self.construccion))
            self.clics = []
        elif h == "circulo_2t" and c:
            ubicacion = c[-1][1]
            self.clics = []
            if len(self.picks) == 2:
                lineas = list(self.picks)
                self.aplicar_cambio(lambda: self.b.agregar_circulo_tangente(lineas, ubicacion, None, None,
                                                                            self.construccion))
                self.picks, self.picks_xy = [], []
        elif h == "arco" and len(c) == 3:
            (pi, a), (pf, b), (_, m) = c
            self.aplicar_cambio(lambda: self.b.agregar_arco_3_puntos(pi if pi is not None else a, m,
                                                                     pf if pf is not None else b, self.construccion))
            self.clics = []
        elif h == "arco_centro" and len(c) == 3:
            (pc, ce), (pi, ini), (_, f) = c
            r = math.dist(ce, ini)
            a1 = math.atan2(f[1] - ce[1], f[0] - ce[0])
            fin = (ce[0] + r * math.cos(a1), ce[1] + r * math.sin(a1))
            a0 = math.atan2(ini[1] - ce[1], ini[0] - ce[0])
            antihorario = _barrido(a0, a1) <= math.pi      # se toma el arco corto, como al mover el ratón
            if self._sentido_vivo is not None:             # …salvo que se haya escrito el barrido
                antihorario = self._sentido_vivo
            centro = pc if pc is not None else ce
            inicio = pi if pi is not None else ini
            self.aplicar_cambio(lambda: (self.b.agregar_arco_centro(centro, inicio, fin, self.construccion)
                                         if antihorario else
                                         self.b.agregar_arco_centro(centro, fin, inicio, self.construccion)))
            self.clics = []
        elif h == "arco_tangente":
            if len(c) == 1:
                if c[0][0] is None or not self._curvas_con_extremo(c[0][0]):
                    self.mensaje.emit("Hacé clic en el extremo de una curva abierta.")
                    self.clics = []
            elif len(c) == 2:
                pid = c[0][0]
                self._crear_arco_tangente(pid, self._curvas_con_extremo(pid)[0], c[1])
                self.clics = []
        elif h in ("poligono_inscrito", "poligono_circunscrito") and len(c) == 2:
            (pc, ce), (_, v) = c
            tipo = "inscrito" if h == "poligono_inscrito" else "circunscrito"
            self.aplicar_cambio(lambda: self._poligono(ce, v, self.lados, tipo, pc))
            self.clics = []
        elif h == "estrella" and len(c) == 2:
            (pc, ce), (_, v) = c
            self.aplicar_cambio(lambda: self._estrella(ce, v, pc))
            self.clics = []
        elif h == "poligono_arista" and len(c) == 3:
            (_, a), (_, b), (_, lado) = c
            L = math.dist(a, b)

            def crear():
                if L < 1e-9:
                    raise ErrorBoceto("La arista no puede medir cero.")
                centro = centro_poligono_arista(a, b, lado, self.lados)
                self._poligono(centro, a, self.lados, "inscrito")
            self.aplicar_cambio(crear)
            self.clics = []
        elif h == "elipse" and len(c) == 3:
            (pc, ce), (_, m), (_, q) = c
            a = math.dist(ce, m) or 1e-9
            radio_menor = abs((m[0] - ce[0]) * (q[1] - ce[1]) - (m[1] - ce[1]) * (q[0] - ce[0])) / a
            self.aplicar_cambio(lambda: self.b.agregar_elipse(pc if pc is not None else ce, m, radio_menor,
                                                              self.construccion))
            self.clics = []
        elif h.startswith("ranura_") and len(c) == (3 if h in ("ranura_centro", "ranura_total", "ranura_punto") else 4):
            self._crear_ranura(h, c, c[-1][1])
            self.clics = []
        elif h in SPLINES and len(c) >= 2:
            if h == "spline_ajuste" and len(c) >= 4 and math.dist(c[-1][1], c[0][1]) < 1e-9:
                self._terminar_spline(cerrar=True)
            elif math.dist(c[-1][1], c[-2][1]) < 1e-9:
                c.pop()
        elif h == "conica" and len(c) == 3:
            def aceptar(v):
                rho = _numero(v[0] or "0.5")
                (p0, a), (p2, b), (pv, vx) = self.clics
                ok = self.aplicar_cambio(lambda: self.b.agregar_conica(p0 if p0 is not None else a,
                                                                       pv if pv is not None else vx,
                                                                       p2 if p2 is not None else b, rho,
                                                                       self.construccion))
                if ok:
                    self.clics = []
                return ok
            self._abrir_entrada(["Rho"], ["0.5"], self._pos_cursor, aceptar)
            self.entrada.campos[0].textChanged.connect(lambda _t: self.update())
        elif h == "punto" and len(c) == 1:
            if c[0][0] is None:
                self.aplicar_cambio(lambda: self.b.agregar_punto(*c[0][1]))
            self.clics = []
        elif h == "texto" and c:
            if len(c) > 1 and self.entrada is not None:
                c.pop()                                 # ya hay una caja de texto abierta
                return
            pid, xy = c[0]
            # El clic elige el camino; en uno abierto, la alineación usa todo el recorrido (Fusion).
            camino = None
            if len(c) == 1 and pid is None:
                camino = self._curva_cercana(self.a_px(*xy))
                if camino is not None and isinstance(self.b.curvas.get(camino), Texto):
                    camino = None
                if camino is None:
                    self.mensaje.emit("Texto: clic en la esquina opuesta para dibujar el cuadro del texto "
                                      "(o clic otra vez en el mismo lugar para un texto de 5 mm).")
                    return                              # falta la 2.ª esquina del cuadro
            en_curva, caja, altura_ini, rect = {}, {}, self.opciones["altura_texto"], None
            if camino is not None:
                prim_camino = self.b.primitivas(camino)[0]
                cerrada = prim_camino[0] in ("circulo", "elipse") or bool(getattr(self.b.curvas[camino], "cerrada", False))
                en_curva = {"camino": camino, "camino_alineado": not cerrada}
                if cerrada:
                    en_curva["camino_pos"] = fraccion_en_camino(prim_camino, xy)
                self.opciones["alineacion"] = "centro"
                self.opciones["camino_lado"] = lado_natural(prim_camino)
            elif len(c) == 2:
                fin_xy = c[1][1]
                x0, x1 = sorted((xy[0], fin_xy[0]))
                y0, y1 = sorted((xy[1], fin_xy[1]))
                if x1 - x0 > 1e-6 and y1 - y0 > 1e-6:   # cuadro dibujado: su alto es el de la letra, su ancho parte líneas
                    pid, xy, altura_ini = None, (x0, y1), y1 - y0
                    caja = {"ancho_caja": x1 - x0, "ancla_v": "arriba"}
                    rect = (x0, y0, x1, y1)

            def aceptar(v):
                v = (list(v) + [""] * 5)[:5]          # los campos de más (espaciado, interlineado) son opcionales
                altura, ang = self.evaluar(v[1] or "5"), self.evaluar(v[2] or "0", ANGULO)
                espaciado, interlineado = _espaciado_mm(v[3], altura, self.opciones), _numero(v[4] or "1")
                o = self.opciones
                extra = {"alineacion": o["alineacion"], "ancla_v": o["ancla_v"], "voltear_h": o["voltear_h"],
                         "voltear_v": o["voltear_v"]} | en_curva | caja | {k: o[k] for k in Texto.TIPOGRAFIA}
                if en_curva:
                    extra |= {k: o[k] for k in CURVA_TEXTO}
                ok = self.aplicar_cambio(lambda: self.b.agregar_texto(
                    pid if pid is not None else xy, v[0].replace("\\n", "\n"), altura, ang, o["fuente"],
                    o["negrita"], o["cursiva"], espaciado=espaciado, interlineado=interlineado, **extra))
                self.clics = []
                self.opciones["ajustes_kerning"] = []          # el kerning a mano es de ESE texto
                return ok
            if camino is not None:
                self.mensaje.emit("Texto en curva: las letras siguen la curva elegida (Lado en curva, en el panel "
                                  "Carácter).")
            self.opciones["ajustes_kerning"] = []
            from .asas_boceto import asas_texto
            self._abrir_entrada(["Texto", "Altura", "∠", "Espaciado (%)", "Interlineado"],
                                ["Texto", formato.numero(altura_ini), "0",
                                 _espaciado_porcentaje(self.opciones["espaciado"], self.opciones["altura_texto"], self.opciones),
                                 formato.numero(self.opciones["interlineado"])], self._pos_cursor, aceptar,
                                None if camino is not None else asas_texto(self, xy, caja.get("ancho_caja", 0.0)))
            self._previa_texto = {"pos": pid if pid is not None else xy, "existente": None,
                                  "extra": en_curva | caja, "caja": rect, "reemplazar": True}
            self._conectar_previa_texto()
            if camino is not None:                       # el panel muestra el lado elegido para esta curva
                self.opciones.update(parametro_texto=None, valor_parametro_texto="")
                self.texto_en_edicion.emit()
        elif h == "espiral" and len(c) == 2:
            (_, ce), (_, ini) = c

            def aceptar(v):
                vueltas, paso = _numero(v[0] or "3"), self.evaluar(v[1] or "2")
                ok = self.aplicar_cambio(lambda: self._espiral(ce, ini, vueltas, paso))
                self.clics = []
                return ok
            self._abrir_entrada(["Vueltas", "Paso"], ["3", formato.numero(max(math.dist(ce, ini), 1.0) / 2)],
                                self._pos_cursor, aceptar)

    def _terminar_spline(self, cerrar=False):
        """Enter, doble clic o clic en el primer punto: crea la spline con los puntos marcados."""
        h, c = self.herramienta, list(self.clics)
        if cerrar and c and len(c) > 1 and math.dist(c[-1][1], c[0][1]) < 1e-9:
            c.pop()
        self.clics = []
        if len(c) < 2:
            return None
        puntos = [pid if pid is not None else xy for pid, xy in c]
        modo = "ajuste" if h == "spline_ajuste" else "control"
        grado = self.opciones["grado_spline"] if modo == "control" else 3
        nuevo = {}

        def crear():
            nuevo["id"] = self.b.agregar_spline(puntos, modo, grado, cerrar, construccion=self.construccion)
        self.aplicar_cambio(crear)
        return nuevo.get("id")

    def _seleccion_util(self):
        return [i for i in self.seleccion if i in self.b.curvas or i in self.b.puntos
                or self.herramienta in TRANSFORMAR and i in self.b.objetos]

    def _avanzar_seleccion(self, avisar=True):
        """Enter en la fase de selección: pasa al paso siguiente de la herramienta."""
        h = self.herramienta
        ids = self._seleccion_util()
        if not ids:
            if avisar:
                self.mensaje.emit("Seleccioná primero la geometría (clic en las curvas).")
            return
        if h == "simetria":
            self.elegir_campo_simetria("eje")
            self.mensaje.emit("Simetría: elegí la línea de simetría.")
        self.update()

    def _calcular_simetria(self):
        """(polilíneas de la copia, error) de reflejar lo elegido respecto de la línea elegida. Se arma en un boceto
        aparte y queda en caché mientras no cambie lo elegido ni el boceto."""
        ids = [i for i in self._seleccion_util() if i != self._eje_simetria]
        clave = (tuple(ids), self._eje_simetria, self._generacion)
        if self._previa_sim is None or self._previa_sim[0] != clave:
            polis, error = [], ""
            copia = self.b.copia()
            try:
                if not ids:
                    raise ErrorBoceto("Elegí qué reflejar, además del eje.")
                if all(isinstance(copia.curvas.get(i), Texto) for i in ids):
                    raise ErrorBoceto("Los textos no se reflejan: usá Voltear.")
                polis = [puntos_primitiva(prim) for k in copia.simetria(ids, self._eje_simetria)
                         for prim in copia.primitivas(k)]
            except ErrorBoceto as e:
                error = str(e)
            self._previa_sim = (clave, polis, error)
        return self._previa_sim[1], self._previa_sim[2]

    def estado_simetria(self):
        """Lo que muestra el panel SIMETRÍA: cuántos objetos hay, si hay línea de simetría, el campo activo, si se puede
        aceptar y qué decirle a la persona (una guía o un reparo)."""
        objetos = self._seleccion_util()
        eje = self._eje_simetria if self._eje_simetria in self.b.curvas or self._eje_simetria in EJES_ORIGEN else None
        e = {"objetos": len(objetos), "eje": eje is not None, "campo": self.fase, "valido": False,
             "previa": self.previa_simetria, "guia": "", "error": self._error_simetria}
        if not objetos:
            e["guia"] = "Elegí la geometría a reflejar: clic en cada curva o arrastrá una ventana."
        elif eje is None:
            e["guia"] = ("Elegí la línea de simetría (puede ser de construcción o un eje del origen)." if self.fase == "eje" else
                         "Con la geometría lista, Enter pasa a elegir la línea de simetría.")
        else:
            error = self._calcular_simetria()[1]
            e["valido"], e["error"] = not error, error or e["error"]
            if not error:
                e["guia"] = "Enter acepta y Esc cancela." + (
                    " Los textos no se reflejan." if any(isinstance(self.b.curvas.get(i), Texto) for i in objetos) else "")
        return e

    def _emitir_simetria(self):
        """Le manda el estado al panel (solo si cambió). Elegir otra cosa borra el último reparo."""
        if self.herramienta != "simetria":
            return
        firma = (tuple(self._seleccion_util()), self._eje_simetria, self.fase)
        if firma != self._firma_sim:
            self._firma_sim, self._error_simetria = firma, ""
        estado = self.estado_simetria()
        if estado != self._estado_sim:
            self._estado_sim = estado
            self.simetria_estado.emit(estado)

    def elegir_campo_simetria(self, campo):
        """Panel: lo que llena el próximo clic, la geometría (`seleccion`) o la línea de simetría (`eje`)."""
        if campo == "eje" and not self._seleccion_util():
            self._error_simetria = "Primero elegí la geometría a reflejar."
        else:
            self.fase = campo
        self._emitir_simetria()
        self.update()

    def limpiar_campo_simetria(self, campo):
        """Panel: la ✕ de un campo lo vacía y lo deja listo para elegir de nuevo."""
        if campo == "eje":
            self._eje_simetria = None
        else:
            self.seleccion = []
        self.fase = campo
        self._emitir_simetria()
        self.update()

    def set_previa_simetria(self, activa):
        self.previa_simetria = bool(activa)
        self._emitir_simetria()
        self.update()

    def aceptar_simetria(self):
        """Aceptar (botón o Enter): crea la copia reflejada en un solo paso de deshacer y sale de la herramienta."""
        e = self.estado_simetria()
        if not e["valido"]:
            self.mensaje.emit(e["error"] or e["guia"])
            return False
        ids, eje = [i for i in self._seleccion_util() if i != self._eje_simetria], self._eje_simetria
        if not self.aplicar_cambio(lambda: self.b.simetria(ids, eje)):
            return False
        self.seleccion = []
        self.set_herramienta("seleccionar")
        return True

    def cancelar_simetria(self):
        """Cancelar (botón, ✕ o Esc): sale de la herramienta sin tocar el boceto."""
        self.set_herramienta("seleccionar")

    def _enter_simetria(self):
        """Enter: con todo elegido acepta; con la geometría lista pasa a la línea de simetría; si no, dice qué falta."""
        e = self.estado_simetria()
        if e["valido"]:
            self.aceptar_simetria()
        elif self.fase == "seleccion" and self._seleccion_util():
            self.elegir_campo_simetria("eje")
        else:
            self.mensaje.emit(e["error"] or e["guia"])

    def _dibujar_previa_simetria(self, p, acento):
        """La recta de simetría entera (trazo y raya, hasta el borde de la vista) y, con la casilla activa, la copia."""
        eje = self._eje_simetria
        if eje in EJES_ORIGEN:
            extremos = EJES_ORIGEN[eje]
        elif eje in self.b.curvas:
            extremos = self.b._extremos_linea(eje)
        else:
            return
        a, b = (self.a_px(*q) for q in extremos)
        n = math.hypot(b.x() - a.x(), b.y() - a.y())
        if n > 1e-6:
            k = (self.width() + self.height()) / n
            d = QPointF(b.x() - a.x(), b.y() - a.y()) * k
            p.setPen(QPen(QColor(255, 140, 0), 1, Qt.DashDotLine))
            p.drawLine(a - d, b + d)
        if self.previa_simetria:
            p.setPen(QPen(acento, 2.0))
            for poli in self._calcular_simetria()[0]:
                self._dibujar_polilinea(p, poli)

    def _esquina_en_vertice(self, pos):
        pid = self._punto_cercano(pos)
        if pid is None or sum(pid in (c.extremos() or ()) for c in self.b.curvas.values()) < 2:
            return None                        # una punta libre no es esquina: el clic elige la curva
        tipos = ("linea", "arco") if self.herramienta == "empalme" else ("linea",)
        curvas, lados = self.b._esquina_por_vertice(pid, tipos)
        return (pid, curvas, lados) if all(self._visible(self.b.curvas[k]) for k in curvas) else None
