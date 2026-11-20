"""LienzoInteraccionMixin: métodos del lienzo por tema."""

from .editor_boceto_comun import (
    Arco,
    CONFLICTO,
    Circulo,
    ErrorBoceto,
    ErrorExpresion,
    FONDO_LIENZO,
    Linea,
    NOMBRES_ENTIDAD,
    PATRON,
    PICKS,
    PORTAPAPELES,
    PROYECCION,
    QColor,
    QEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QPointF,
    QPolygonF,
    QRectF,
    QToolTip,
    Qt,
    RESTRICCIONES_HERRAMIENTA,
    SELECCION,
    SPLINES,
    TOL_MANIJA,
    TOL_PX,
    TRANSFORMAR,
    Texto,
    VENTANA_BORDE,
    VENTANA_CRUCE,
    VENTANA_RELLENO,
    VIOLETA,
    _barrido,
    _distancia_a_raya,
    _segmento_en_rect,
    cambiar_radio,
    dominio,
    evaluar_primitiva,
    formato,
    fraccion_en_camino,
    math,
    puntos_primitiva,
    resolver,
    temas,
    texto_valor,
)
from ..restricciones.solver import _grupos, foto


class LienzoInteraccionMixin:
    def _zona_en(self, pos):
        """Cota o símbolo bajo `pos`: su texto o ícono, o (la cota) cualquier raya de su línea de cota, su flecha, su
        arco o su guía, salvo que ahí haya una curva o punto del boceto (esa gana)."""
        for tabla in (self._zonas_cotas, self._zonas_glifos):
            for ident, rect in tabla.items():
                if rect.adjusted(-4, -4, 4, 4).contains(pos):
                    return ident
        for ident, rect in self._zonas_glifos_extra:
            if rect.adjusted(-4, -4, 4, 4).contains(pos):
                return ident
        for cid, rayas in self._trazos_cotas.items():
            if any(_distancia_a_raya(pos, a, b) <= 5 for a, b in rayas) and self.entidad_en(pos) is None:
                return cid
        return None

    def _para_visor(self, e):
        if self.visor is None:
            return False
        if e.button() != Qt.LeftButton:
            return True
        return self.visor.modo in ("orbita", "encuadre", "zoom", "ventana", "mirar")

    def mousePressEvent(self, e):
        pos = e.position()
        self._modificadores_raton = e.modifiers()
        if self.objetos.arrastre is not None:
            self.objetos.cancelar()
            return
        if self._asas is not None and e.button() == Qt.LeftButton and self._asas.empezar(pos):
            return                                   # se tira de un asa de la herramienta
        if (e.button() == Qt.LeftButton and self.herramienta == "desfase" and self.picks and self.entrada is not None
                and not self._para_visor(e)):
            self._clic_con_desfase_abierto(pos)      # el Desfase abierto sigue abierto (Enter acepta, Esc cancela)
            return
        if e.button() == Qt.LeftButton and self.herramienta == "seleccionar" and self._clic_casilla_patron(pos):
            return                                   # casilla de supresión de una copia del patrón
        if e.button() == Qt.LeftButton and self.herramienta in PATRON and self.patron.clic_casilla(pos):
            return                                   # casilla de una copia del patrón que se está armando
        if self.entrada is not None and e.button() == Qt.LeftButton and self._citar_cota(pos):
            return                                   # antes de setFocus: este saca el foco y la selección de la caja
        self._camara()
        self.setFocus()
        if self._eligiendo_punto is not None and not self._para_visor(e):
            pid = self._punto_cercano(pos) if e.button() == Qt.LeftButton else None
            if pid is not None or e.button() == Qt.RightButton:
                self._terminar_eleccion(pid)
            else:
                self.mensaje.emit("Ahí no hay un punto del boceto: hacé clic sobre uno (Esc cancela).")
            return
        if self._previa_texto is not None and self.entrada is not None and e.button() in (Qt.LeftButton,
                                                                                          Qt.RightButton):
            if e.button() == Qt.LeftButton and self._sobre_texto(pos):
                self._clic_en_texto(pos, e.modifiers())      # clic en el texto: mueve el cursor
                return
            self.confirmar_texto_pendiente()          # clic afuera o clic derecho (menú radial): el texto queda
            if e.button() == Qt.LeftButton:
                return
        if (self.herramienta == "conica" and len(self.clics) == 3 and self.entrada is not None
                and e.button() == Qt.LeftButton and not self._para_visor(e)):
            self._actualizar_rho_conica(pos)
            self._presion = (pos, None, self.cursor)
            self.update()
            return
        if self.entrada is not None and e.button() == Qt.LeftButton:
            if self._editando is not None:          # clic con una caja a medio escribir: el valor queda fijo
                texto = self.entrada.campos[0].text()
                if not self._fin_edicion_viva(texto):
                    self._cerrar_entrada()
            elif (self._cota_abierta is not None and self._cota_abierta[0] in ("radio", "diametro")
                  and self.entidad_en(pos) in (None, self._cota_abierta[1][0])):
                # B-439: como Fusion, el clic ubica la cota del círculo o arco ahí, con su caja y lo ya escrito
                texto = self.entrada.campos[0].text()
                self._abrir_cota(*self._cota_abierta[:2], pos)
                self.entrada.campos[0].setText(texto)
                self.entrada.campos[0].selectAll()   # B-671: setText borra la selección; Fusion deja el valor elegido
                return
            else:
                self._cerrar_entrada()
        zona = self._zona_en(pos) if e.button() == Qt.RightButton and not self.clics else None
        if zona in self.b.cotas:
            self._menu_cota(zona, pos).exec(e.globalPosition().toPoint())
            return
        if zona in self.b.restricciones:
            self._menu_restriccion(zona).exec(e.globalPosition().toPoint())
            return
        if e.button() == Qt.RightButton and (self.herramienta != "seleccionar" or self._hay_operacion()):
            # en una herramienta, el clic derecho rápido cancela o sale (al soltar); arrastrado, pasa al visor o al
            # desplazamiento; mantenido con una cota a medias, abre sus opciones
            self._derecho = (pos, e.globalPosition().toPoint())
            if self.herramienta == "cota" and self.picks:
                self._t_derecho.start(400)
            return
        if self._para_visor(e):
            self._reenvio = (e.button(), pos)
            self.visor.mousePressEvent(e)
            return
        if self.visor is None and (e.button() == Qt.MiddleButton or (e.button() == Qt.RightButton and not self.clics)):
            self._pan = pos
            return
        if e.button() == Qt.RightButton:
            self.cancelar()
            return
        if e.button() != Qt.LeftButton:
            return
        h = self.herramienta
        if h == "seleccionar" and self._presionar_marco(pos):
            pass
        elif h == "seleccionar":
            self._presionar_seleccion(pos, e.modifiers())
        elif h == "cota":
            self._clic_cota(pos)
        elif h == "recortar":
            self._recorte_arrastre = False
            self._clic_pick(pos)
        elif h in RESTRICCIONES_HERRAMIENTA:
            self._clic_restriccion(pos)
        elif h in PROYECCION:
            self._clic_proyectar(pos)
        elif h in PATRON and self.fase in ("centro", "dir1", "dir2") and self.patron.clic(pos):
            pass
        elif h in TRANSFORMAR and self.fase in ("base", "destino") and self.transformar.clic(pos):
            pass
        elif h in SELECCION and self.fase == "seleccion":
            self._presionar_seleccion(pos, Qt.ControlModifier, arrastrar=False)
        elif (h in PICKS or (h in SELECCION and self.fase == "eje")) and self._clic_pick(pos):
            pass
        else:
            base = self.clics[-1][1] if self.clics else None
            self._presion = (pos, *self._ajustar(pos, base=base))
            self._presion_inferencia = self.inferencia
            self._presion_inf_actual = self.inf_actual
        self.update()

    def _ids_marco(self):
        return [i for i in self.seleccion if i in self.b.curvas or i in self.b.puntos]

    def _giro_marco(self):
        """Grados con que se gira el marco: los del texto cuando lo elegido es un solo texto (el marco lo envuelve
        girado, como Fusion); 0 en cualquier otro caso."""
        ids = self._ids_marco()
        if len(ids) == 1 and isinstance(self.b.curvas.get(ids[0]), Texto):
            return self.b.angulo_texto(ids[0])
        return 0.0

    def _esquinas_marco(self, caja, giro):
        """Las 4 esquinas (mm) de la caja medida en los ejes girados `giro`: abajo-izq., abajo-der., arriba-der., arriba-izq."""
        c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))
        x0, y0, x1, y1 = caja
        return [(x * c - y * s, x * s + y * c) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]

    def _caja_marco(self):
        """Caja (xmin, ymin, xmax, ymax) en mm de lo elegido (en los ejes girados `_giro_marco()`), o None si el marco
        no corresponde: hace falta estar seleccionando y tener al menos dos curvas (o un texto)."""
        if not self.mostrar_marco or self.herramienta != "seleccionar" or self.fase not in (None, "", "seleccion"):
            return None
        ids = self._ids_marco()
        curvas = [i for i in ids if i in self.b.curvas]
        if len(curvas) < 2 and not any(isinstance(self.b.curvas[i], Texto) for i in curvas):
            return None
        pts = []
        for i in ids:
            if i in self.b.puntos:
                pts.append(self.b.coords(i))
                continue
            if isinstance(self.b.curvas[i], Texto):        # con su contenido, no el «{Text}» que guarda
                pts += [q for poli in self._polilineas(self.b.curvas[i]) for q in poli]
                continue
            for prim in self.b.primitivas(i):
                if prim[0] == "linea":
                    pts += [prim[2], prim[3]]
                elif prim[0] == "circulo":
                    (cx, cy), r = prim[2], prim[3]
                    pts += [(cx - r, cy - r), (cx + r, cy + r)]
                elif prim[0] == "spline":         # la curva queda dentro de su polígono de control
                    pts += list(prim[2])
                else:
                    pts += puntos_primitiva(prim, 24)
        if not pts:
            return None
        giro = self._giro_marco()
        if giro:
            c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))
            pts = [(q[0] * c + q[1] * s, -q[0] * s + q[1] * c) for q in pts]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        caja = (min(xs), min(ys), max(xs), max(ys))
        esq = self._esquinas_marco(caja, giro)
        a, b = self.a_px(*esq[0]), self.a_px(*esq[2])
        if abs(b.x() - a.x()) < 4 and abs(b.y() - a.y()) < 4:
            return None
        return caja

    def _manijas_marco(self, caja):
        """{nombre: punto en píxeles} de las manijas del marco."""
        x0, y0, x1, y1 = caja
        g = self._marco["giro"] if self._marco is not None else self._giro_marco()
        c, s = math.cos(math.radians(g)), math.sin(math.radians(g))
        px = lambda x, y: self.a_px(x * c - y * s, x * s + y * c)        # noqa: E731  (ejes del marco → pantalla)
        esq = [px(x0, y0), px(x1, y0), px(x1, y1), px(x0, y1)]
        arriba = px((x0 + x1) / 2, y1)
        derecha, abajo = px(x1, (y0 + y1) / 2), px((x0 + x1) / 2, y0)
        # los asas de giro y de espejo salen hacia afuera del marco, en la dirección de sus ejes en pantalla
        sube = px((x0 + x1) / 2, y1 + 1) - arriba
        sale = px(x1 + 1, (y0 + y1) / 2) - derecha
        baja = px((x0 + x1) / 2, y0 - 1) - abajo
        unit = lambda v, largo: v * (largo / math.hypot(v.x(), v.y())) if math.hypot(v.x(), v.y()) > 1e-9 else QPointF(0, 0)  # noqa: E731
        m = {f"escala{k}": q for k, q in enumerate(esq)}
        m["rotar"] = arriba + unit(sube, 28)
        m["mover"] = px((x0 + x1) / 2, (y0 + y1) / 2)
        m["espejo_h"] = derecha + unit(sale, 18)
        m["espejo_v"] = abajo + unit(baja, 18)
        return m

    def _presionar_marco(self, pos):
        if self.objetos.seleccion():
            return self.objetos.presionar(pos)
        caja = self._caja_marco()
        if caja is None:
            return False
        for nombre, q in self._manijas_marco(caja).items():
            if math.hypot(q.x() - pos.x(), q.y() - pos.y()) <= TOL_MANIJA:
                mm = self.a_mm(pos)
                self._marco = {"tipo": nombre, "caja": caja, "giro": self._giro_marco(), "inicio": mm, "actual": mm,
                               "px_inicio": pos, "px_actual": pos, "shift": False}
                return True
        return False

    def _transformacion_marco(self):
        """(descripción, función punto → punto, acción sobre el boceto) del arrastre en curso."""
        m = self._marco
        esq = self._esquinas_marco(m["caja"], m["giro"])
        c = ((esq[0][0] + esq[2][0]) / 2, (esq[0][1] + esq[2][1]) / 2)
        (ix, iy), (ax, ay) = m["inicio"], m["actual"]
        tipo, ids = m["tipo"], self._ids_marco()
        if tipo == "mover":
            dx, dy = ax - ix, ay - iy
            if m["shift"]:                       # Shift: solo en el eje donde más se movió
                dx, dy = (dx, 0.0) if abs(dx) >= abs(dy) else (0.0, dy)
            return (f"Δ {formato.numero(dx)} ; {formato.numero(dy)} mm", lambda q: (q[0] + dx, q[1] + dy),
                    lambda: self.b.transformar(ids, dx=dx, dy=dy))
        if tipo.startswith("escala"):
            k = int(tipo[-1])
            ancla = c if m["shift"] else esq[(k + 2) % 4]
            d0 = math.dist(esq[k], ancla)
            f = max(math.dist((ax, ay), ancla) / d0, 1e-3) if d0 > 1e-12 else 1.0
            return (f"× {formato.numero(f)}", lambda q: (ancla[0] + f * (q[0] - ancla[0]), ancla[1] + f * (q[1] - ancla[1])),
                    lambda: self.b.escalar(ids, ancla, f))
        if tipo == "rotar":
            ang = math.degrees(math.atan2(ay - c[1], ax - c[0]) - math.atan2(iy - c[1], ix - c[0]))
            ang = (ang + 180.0) % 360.0 - 180.0
            if m["shift"]:
                ang = round(ang / 15.0) * 15.0
            a = math.radians(ang)

            def girar(q):
                u, v = q[0] - c[0], q[1] - c[1]
                return (c[0] + u * math.cos(a) - v * math.sin(a), c[1] + u * math.sin(a) + v * math.cos(a))
            return (f"{formato.numero(ang)}°", girar, lambda: self.b.transformar(ids, angulo=ang, centro=c))
        horizontal = tipo == "espejo_h"
        return ("Espejo", (lambda q: (2 * c[0] - q[0], q[1])) if horizontal else (lambda q: (q[0], 2 * c[1] - q[1])),
                lambda: self._espejar_marco(ids, c, horizontal))

    def _espejar_marco(self, ids, centro, horizontal):
        _hechos, textos = self.b.reflejar(ids, centro, horizontal)
        if textos:
            self.mensaje.emit("Los textos rectos no se espejan con el marco: usá los botones de volteo del panel «Carácter».")

    def _soltar_marco(self):
        m, self._marco = self._marco, None
        if m is None:
            return
        movio = math.hypot(m["px_actual"].x() - m["px_inicio"].x(), m["px_actual"].y() - m["px_inicio"].y()) > 3
        if not movio and not m["tipo"].startswith("espejo"):
            return
        self._marco = m
        _texto, f, accion = self._transformacion_marco()
        self._marco = None
        self.aplicar_movimiento(accion, self._ids_marco(), f)

    def aplicar_movimiento(self, accion, ids, f):
        """`aplicar_cambio` de un mover / girar / escalar de `ids` (f: punto → punto pedido). B-245/B-253: si las
        restricciones (p. ej. una coincidencia con el origen) devolvieron todo a su lugar, no fue un movimiento: se
        deshace y se dice por qué, como hace transform_sketch. Devuelve si quedó aplicado."""
        origen = {q: self.b.coords(q) for q in self.b.puntos_de(ids)}
        if not self.aplicar_cambio(accion, operacion=True):    # B-538: avisa si soltó el anclaje al origen
            return False
        if (any(math.dist(f(xy), xy) > 1e-6 for xy in origen.values())
                and all(math.dist(self.b.coords(q), xy) < 1e-6 for q, xy in origen.items() if q in self.b.puntos)):
            self.deshacer()
            self.mensaje.emit("Las restricciones o cotas que atan la selección a lo que no se mueve (p. ej. una "
                              "coincidencia con el origen) no la dejan llegar: borrá ese anclaje y volvé a moverla.")
            return False
        return True

    def _dibujar_marco(self, p):
        if self.objetos.seleccion():
            return
        caja = self._marco["caja"] if self._marco is not None else self._caja_marco()
        if caja is None:
            return
        azul = QColor(0, 150, 255)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(azul, 1, Qt.DashLine))
        esq = self._esquinas_marco(caja, self._marco["giro"] if self._marco is not None else self._giro_marco())
        p.drawPolygon(QPolygonF([self.a_px(*q) for q in esq]))
        manijas = self._manijas_marco(caja)
        arriba = self.a_px((esq[2][0] + esq[3][0]) / 2, (esq[2][1] + esq[3][1]) / 2)
        p.setPen(QPen(azul, 1))
        p.drawLine(arriba, manijas["rotar"])
        for nombre, q in manijas.items():
            p.setBrush(QColor(255, 170, 40) if nombre == self._manija_sobre else QColor(255, 255, 255))
            if nombre == "rotar":
                p.drawEllipse(q, 5, 5)
            elif nombre == "mover":
                p.drawLine(QPointF(q.x() - 6, q.y()), QPointF(q.x() + 6, q.y()))
                p.drawLine(QPointF(q.x(), q.y() - 6), QPointF(q.x(), q.y() + 6))
            elif nombre.startswith("espejo"):        # flecha doble dibujada (no depende de la fuente)
                h = nombre == "espejo_h"
                a = QPointF(q.x() - 7, q.y()) if h else QPointF(q.x(), q.y() - 7)
                b = QPointF(q.x() + 7, q.y()) if h else QPointF(q.x(), q.y() + 7)
                p.drawLine(a, b)
                for punta, s in ((a, 1), (b, -1)):
                    if h:
                        p.drawLine(punta, QPointF(punta.x() + 4 * s, punta.y() - 3))
                        p.drawLine(punta, QPointF(punta.x() + 4 * s, punta.y() + 3))
                    else:
                        p.drawLine(punta, QPointF(punta.x() - 3, punta.y() + 4 * s))
                        p.drawLine(punta, QPointF(punta.x() + 3, punta.y() + 4 * s))
            else:
                p.drawRect(QRectF(q.x() - 4, q.y() - 4, 8, 8))
        p.setBrush(Qt.NoBrush)
        if self._marco is not None:                 # vista previa del resultado
            texto, f, _accion = self._transformacion_marco()
            p.setPen(QPen(QColor(255, 140, 0), 1.5, Qt.DashLine))
            p.drawPolygon(QPolygonF([self.a_px(*f(q)) for q in esq]))
            p.setPen(QPen(QColor(255, 140, 0), 1))
            q = self._marco["px_actual"]
            p.drawText(QPointF(q.x() + 14, q.y() - 10), texto)

    def _presionar_seleccion(self, pos, mods, arrastrar=True):
        suma = bool(mods & (Qt.ControlModifier | Qt.ShiftModifier))
        ent = self._zona_en(pos)
        if ent is None:
            ent = self.entidad_en(pos)
        if not suma:
            self.perfiles_sel = []
        if mods & Qt.AltModifier and not suma and ent in self.b.objetos:
            debajo = self.objetos.todos_en(pos)           # Alt+clic: el siguiente objeto superpuesto, en ciclo
            if len(debajo) > 1:
                actual = self.objetos.seleccion()
                k = debajo.index(actual[0]) + 1 if len(actual) == 1 and actual[0] in debajo else 1
                ent = debajo[k % len(debajo)]
                self.seleccion = []
                self.mensaje.emit(f"Objeto {debajo.index(ent) + 1} de {len(debajo)} bajo el cursor: "
                                  f"{self.b.objetos[ent]['nombre']} (Alt+clic elige el de abajo)")
        if ent is None:
            if not suma:
                self.seleccion = []
            self._ventana = (pos, pos)
        elif suma:
            if ent in self.seleccion:
                self.seleccion.remove(ent)
            else:
                self.seleccion.append(ent)
        elif ent not in self.b.objetos or ent not in self.seleccion:
            self.seleccion = [ent]
        if arrastrar and ent is not None:
            if ent in self.b.objetos:
                if not suma:
                    self.objetos.iniciar("mover", pos)
            else:
                self._empezar_arrastre(ent, pos)
        if ent not in self.b.objetos:
            self.cambio.emit()
        self._notificar_seleccion()

    def _determinada(self, ent):
        r = self.resultado
        return r is not None and r.ok and ent in r.determinadas

    def _empezar_arrastre(self, ent, pos):
        """Arrastre en Seleccionar: puntos, líneas (sus dos extremos juntos), círculos y arcos. Lo fijo o
        totalmente restringido no se mueve (como en Fusion)."""
        fijos = self.b.puntos_fijos()
        try:
            self.b.exigir_desbloqueadas([ent] if ent in self.b.puntos or ent in self.b.curvas else [], "moverla")
        except ErrorBoceto as e:                     # H-69: una curva bloqueada (o su punto) no se arrastra
            self.mensaje.emit(str(e))
            return
        if ent in self.b.puntos:
            if ent in fijos:
                self.mensaje.emit("Ese punto está fijo (o es proyectado): quitá la restricción «Fijo» para moverlo.")
                return
            if self._determinada(ent):
                self.mensaje.emit("Ese punto está totalmente restringido: no se puede arrastrar.")
                return
            self._arrastre = ent
            self._foto_arrastre = None
        elif ent in self.b.curvas:
            c = self.b.curvas[ent]
            if isinstance(c, Texto) and c.camino in self.b.curvas:
                # texto en curva: arrastrarlo lo desliza por la curva (la posición sigue al ratón)
                cam = self.b.curvas[c.camino]
                inicio = fraccion_en_camino(self.b.primitivas(c.camino)[0], self.a_mm(pos))
                cerrada = isinstance(cam, Circulo) or bool(getattr(cam, "cerrada", False))
                self._arrastre = ("curva", ent, "deslizar")
                self._desliz = (inicio, c.camino_pos, cerrada)
                self._ultimo = self.a_mm(pos)
                self._movio = False
                self._instantanea()
                self.mensaje.emit("Arrastrá el texto para deslizarlo por la curva.")
                return
            if not isinstance(c, (Linea, Circulo, Arco, Texto)) or c.proyectada:
                return
            if set(c.puntos()) <= fijos or self._determinada(ent):
                self.mensaje.emit("Esa curva está totalmente restringida (o fija): no se puede arrastrar.")
                return
            self._arrastre = ("curva", ent, self._modo_arrastre(ent))
            self._ultimo = self.a_mm(pos)
        elif ent in self.b.cotas:
            # solo mueve la cota (línea, arco o texto): el valor no cambia. Agarrada de la línea y no del texto, el
            # texto de una cota lineal se queda donde está.
            QToolTip.hideText()
            self._cita_sobre = None
            sobre_texto = self._zonas_cotas[ent].adjusted(-4, -4, 4, 4).contains(pos)
            self._arrastre = ("cota", ent, None if sobre_texto else "linea")
        else:
            return
        self._movio = False
        self._instantanea()

    def _cambiar_radio(self, b, cid, radio):
        return cambiar_radio(b, cid, radio)

    def _modo_arrastre(self, cid):
        """"radio" si arrastrar la curva puede cambiar el radio (está libre); si no, "mover"."""
        c = self.b.curvas[cid]
        if isinstance(c, (Linea, Texto)):
            return "mover"
        copia = self.b.copia()
        r0 = copia.radio(cid)
        ref = self._cambiar_radio(copia, cid, r0 * 1.25 + 1.0)
        try:
            resolver(copia, self.valores_cotas(), ref)
        except (ErrorBoceto, ErrorExpresion, ValueError, ZeroDivisionError):
            return "mover"
        return "radio" if abs(copia.radio(cid) - r0) > 1e-4 else "mover"

    def _deslizar_texto(self, cid, cur):
        """Mueve un texto en curva a lo largo de su camino: conserva el punto del texto que se agarró."""
        t = self.b.curvas[cid]
        inicio, pos0, cerrada = self._desliz
        ahora = fraccion_en_camino(self.b.primitivas(t.camino)[0], cur)
        delta = ahora - inicio
        if cerrada:
            delta = (delta + 0.5) % 1.0 - 0.5         # por el camino corto: da la vuelta sin saltar
            t.camino_pos = (pos0 + delta) % 1.0
        else:
            t.camino_pos = min(max(pos0 + delta, 0.0), 1.0)
        self.cambio.emit()                            # los rellenos de los perfiles siguen al texto (B-137)
        self.update()

    def _mover_curva(self, cid, modo, cur):
        if modo == "deslizar":
            self._deslizar_texto(cid, cur)
            return
        c = self.b.curvas[cid]
        fijos = self.b.puntos_fijos()
        if modo == "radio":
            cx, cy = self.b.coords(c.centro)
            ref = self._cambiar_radio(self.b, cid, max(math.hypot(cur[0] - cx, cur[1] - cy), 1e-3))
        else:
            dx, dy = cur[0] - self._ultimo[0], cur[1] - self._ultimo[1]
            libres = [pid for pid in c.puntos() if pid not in fijos]
            for pid in libres:
                p = self.b.puntos[pid]
                p.x, p.y = p.x + dx, p.y + dy
            ref = min(libres, key=lambda q: math.dist(self.b.coords(q), cur)) if libres else None
            partes = [g["p"] & set(libres) for g in _grupos(self.b) if g["p"].intersection(libres)]
            if len(partes) == 1 and self.resultado is not None:
                # Lo movido está en una sola parte: se resuelve solo esa, como al arrastrar un punto (antes, el boceto
                # entero en cada evento: 140 ms con 100 piezas). Entera, sin ventana: la ventana rodea a un solo punto y
                # congelaría el resto de la curva ya movido. Soltar resuelve todo.
                self.resultado.sin_ventana = True
                self._ultimo = cur
                self.resolver(arrastrado=min(partes[0], key=lambda q: math.dist(self.b.coords(q), cur)), rapido=True)
                return
        self._ultimo = cur
        self.resolver(arrastrado=ref)

    def _mover_punto(self, pid, cur):
        """Arrastra un punto; si es el centro de arcos, el arco entero lo acompaña."""
        if getattr(self, "_foto_arrastre", None) is None:
            self._foto_arrastre = foto(self.b)         # B-732: el menor cambio se mide desde acá, como Fusion
        p = self.b.puntos[pid]
        dx, dy = cur[0] - p.x, cur[1] - p.y
        p.x, p.y = cur
        fijos = self.b.puntos_fijos()
        for c in self.b.curvas.values():
            if isinstance(c, Arco) and c.centro == pid:
                for q in (c.inicio, c.fin):
                    if q not in fijos and q != pid:
                        self.b.puntos[q].x += dx
                        self.b.puntos[q].y += dy
                        ref = self._foto_arrastre[0]          # B-740: la referencia de B-732 los acompaña también,
                        if q in ref:                          # si no, el solver los vuelve atrás y el radio crece
                            ref[q] = (ref[q][0] + dx, ref[q][1] + dy)
        # Rápido: lo movido es un punto (y, si es centro de arcos, sus arcos: misma parte del boceto). Arrastrar una
        # curva entera mueve puntos que pueden estar en partes distintas: `_mover_curva` resuelve todo en ese caso.
        self.resolver(arrastrado=pid, rapido=True, referencia=self._foto_arrastre)

    def _manija_en(self, pos):
        """Nombre de la manija del marco de control bajo `pos` (o None)."""
        caja = self._caja_marco() if self.mostrar_marco else None
        if caja is None:
            return None
        for nombre, q in self._manijas_marco(caja).items():
            if math.hypot(q.x() - pos.x(), q.y() - pos.y()) <= TOL_MANIJA:
                return nombre
        return None

    def _actualizar_sobre(self, pos):
        """Seleccionar: resalta lo que hay bajo el ratón (manija, cota, símbolo, curva o punto) y cambia el
        cursor, para que se vea dónde agarrar. Orden igual al del clic: manija, cota/símbolo, entidad."""
        manija = self.objetos.manija_en(pos) if self.objetos.seleccion() else self._manija_en(pos)
        zona = None if manija is not None else self._zona_en(pos)
        ent = None
        if manija is None and zona is None:
            ent = self.objetos.en(pos)
        if manija is None and zona is None and ent is None:      # RS-X3: sin tope (2000 curvas: ~4 ms)
            ent = self.entidad_en(pos)
            if ent is not None and ent not in self.b.curvas and ent not in self.b.puntos and ent not in self.b.objetos:
                ent = None
        if (ent, manija, zona) != (self._sobre, self._manija_sobre, self._zona_sobre):
            self._sobre, self._manija_sobre, self._zona_sobre = ent, manija, zona
            from ..restricciones import objetos
            self.objetos._sobre = objetos.indice(self.b).get(ent, (ent,))[0]
            if manija is not None:
                cursores = {"escala0": Qt.SizeBDiagCursor, "escala4": Qt.SizeBDiagCursor,
                            "escala2": Qt.SizeFDiagCursor, "escala6": Qt.SizeFDiagCursor,
                            "escala1": Qt.SizeVerCursor, "escala5": Qt.SizeVerCursor,
                            "escala3": Qt.SizeHorCursor, "escala7": Qt.SizeHorCursor,
                            "rotar": Qt.CrossCursor, "pivote": Qt.CrossCursor}
                self.setCursor(cursores.get(manija, Qt.SizeAllCursor))
            elif zona is not None:
                self.setCursor(Qt.PointingHandCursor)
            elif ent is not None:
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.unsetCursor()
            self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        self._modificadores_raton = e.modifiers()
        self._pos_cursor = pos
        self._camara()
        if self.objetos.arrastre is not None:
            if e.buttons() & Qt.LeftButton:
                self.objetos.mover(pos, e.modifiers())
            else:
                self.objetos.soltar()  # un botón liberado fuera de la ventana no deja un gesto colgado
            return
        if self._asas is not None:
            if self._asas.arrastrando:
                self._asas.mover(pos)
                return
            if not (e.buttons() & Qt.LeftButton):
                self._asas.pasar(pos)
        if self._previa_texto is not None and self.entrada is not None:
            if self._arrastre_texto and e.buttons() & Qt.LeftButton:       # arrastrando: selecciona texto
                d = self._previa_texto
                tid = d.get("existente")
                if (tid is not None and tid in self.b.curvas and isinstance(self.b.curvas[tid], Texto)
                        and self.b.curvas[tid].camino in self.b.curvas
                        and (pos - self._pos_clic_texto).manhattanLength() > 8):
                    # arrastrar las letras de un texto en ruta con la paleta abierta lo desliza (B-187)
                    self._arrastre_texto = False
                    self._empezar_arrastre(tid, self._pos_clic_texto)   # desde donde se agarró, no del umbral
                else:
                    i = self._indice_en_texto(pos)
                    if i is not None and i != d["cursor"]:
                        d["cursor"], d["col"] = i, None
                        self._actualizar_cursor()
                        self.update()
                    return
            self.setCursor(Qt.IBeamCursor if self._sobre_texto(pos) else Qt.ArrowCursor)
        if (self.herramienta == "seleccionar" and not (e.buttons() & Qt.LeftButton) and self.entrada is None
                and self._reenvio is None and self._marco is None):
            self._actualizar_sobre(pos)
        elif self._sobre is not None or self._manija_sobre is not None or self._zona_sobre is not None:
            self._sobre = self._manija_sobre = self._zona_sobre = None
            self.unsetCursor()
        self._actualizar_cita(pos)
        if self._derecho is not None and (pos - self._derecho[0]).manhattanLength() > 4:
            self._t_derecho.stop()
            inicio, global_ = self._derecho
            self._derecho = None
            if self.visor is not None:               # arrastre con el derecho: es del visor (gesto del menú radial)
                self._reenvio = (Qt.RightButton, inicio)
                self.visor.mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, inicio, global_, Qt.RightButton,
                                                       Qt.RightButton, e.modifiers()))
            else:
                self._pan = inicio
        if self._reenvio is not None:
            self.visor.mouseMoveEvent(e)
            return
        if self._pan is not None:
            d = pos - self._pan
            self._pan = pos
            self.centro[0] -= d.x() / self.escala
            self.centro[1] += d.y() / self.escala
            self.update()
            return
        if self._ventana is not None:
            self._ventana = (self._ventana[0], pos)
            self.update()
            return
        if self._marco is not None:
            self._marco["actual"] = self.a_mm(pos)
            self._marco["px_actual"] = pos
            self._marco["shift"] = bool(e.modifiers() & Qt.ShiftModifier)
            self.update()
            return
        if self.herramienta == "conica" and len(self.clics) == 3 and self.entrada is not None:
            self._actualizar_rho_conica(pos)
            self.update()
            return
        excluir = self._arrastre if isinstance(self._arrastre, int) else None
        self.cursor = self._ajustar(pos, excluir=excluir, base=self._base_inferencia())[1]
        if (self._presion is not None and self.herramienta == "linea" and e.buttons() & Qt.LeftButton
                and self.clics and self._presion[1] is not None and self._presion[1] == self.clics[-1][0]
                and math.hypot(pos.x() - self._presion[0].x(), pos.y() - self._presion[0].y()) > 8):
            # arrastrar desde el extremo de la línea anterior, o de un arco, spline o cónica (BOC-12), da un arco tangente
            curvas = [k for k in self._curvas_con_extremo(self._presion[1]) if k == self._ultima_linea
                      or not isinstance(self.b.curvas[k], Linea)]
            if curvas:
                self._tangente = (self._presion[1], curvas[0])
        if isinstance(self._arrastre, tuple):
            _, cid, modo = self._arrastre
            if cid in self.b.curvas:
                self._mover_curva(cid, modo, self.a_mm(pos))
                self._movio = True
            elif cid in self.b.cotas:
                self.b.mover_cota(self.b.cotas[cid], self.a_mm(pos), con_texto=modo != "linea")
                self._movio = True
        elif self._arrastre is not None:
            self._mover_punto(self._arrastre, self.cursor)
            self._movio = True
        if self.herramienta == "recortar":
            if not (e.buttons() & Qt.LeftButton):
                self._recorte_arrastre = None     # también termina si se soltó fuera de la ventana
            elif self._recorte_arrastre is not None and (cid := self._curva_cercana(pos)) is not None:
                self.agregar_pick(cid, self.a_mm(pos), pos)    # el mismo recorte del clic, sobre la geometría actual
            self._previa_recorte = self._tramo_a_recortar(pos)
        elif self.herramienta == "isoparametrica":
            self.programar_previa_iso(pos)
        self.update()

    def mouseReleaseEvent(self, e):
        pos = e.position()
        self._modificadores_raton = e.modifiers()
        if e.button() == Qt.LeftButton:
            self._recorte_arrastre = None
        if self.objetos.arrastre is not None:
            if e.button() == Qt.LeftButton:
                self.objetos.mover(pos, e.modifiers())
                self.objetos.soltar()
            else:
                self.objetos.cancelar()
            return
        if self._asas is not None and self._asas.arrastrando:
            self._asas.soltar()
            return
        if self._arrastre_texto:
            self._arrastre_texto = False
            d = self._previa_texto
            if d is not None and d["ancla"] == d["cursor"]:
                d["ancla"] = None            # un clic sin arrastre no deja selección
                self._actualizar_cursor()
                self.update()
            return
        if self._derecho is not None and e.button() == Qt.RightButton:
            self._t_derecho.stop()
            self._derecho = None
            self.cancelar()
            return
        if self._reenvio is not None:
            boton, inicio = self._reenvio
            self._reenvio = None
            self.visor.mouseReleaseEvent(e)     # clic derecho: el visor abre el menú radial (Aceptar / Cancelar…)
            return
        self._pan = None
        if self._marco is not None:
            self._marco["shift"] = bool(e.modifiers() & Qt.ShiftModifier)
            self._soltar_marco()
            self.update()
            return
        if self._ventana is not None:
            a, b = self._ventana
            self._ventana = None
            if abs(b.x() - a.x()) < 3 and abs(b.y() - a.y()) < 3:
                self._clic_perfil(a)                  # BOC-23: clic (sin arrastrar) dentro de una región cerrada
            else:
                self._seleccionar_ventana(a, b)
        if self._arrastre is not None:
            if not self._movio:
                self.historial.pop()
            else:
                self.pila_rehacer.clear()
                self.resolver()
            self._arrastre = self._foto_arrastre = None
        if self._presion is not None and e.button() == Qt.LeftButton:
            if self.herramienta == "conica" and len(self.clics) == 3 and self.entrada is not None:
                self._actualizar_rho_conica(pos)
                self._presion = None
                self.entrada.aceptado.emit([self.entrada.campos[0].text()])
                self.update()
                return
            _pos, pid, xy = self._presion
            self._presion = None
            if self._tangente is not None:
                inicio, linea = self._tangente
                self._tangente = None
                fin = self._ajustar(pos)
                res = self._crear_arco_tangente(inicio, linea, fin)
                if res is not None:
                    aid, punto_fin = res
                    self.clics = [(punto_fin, self.b.coords(punto_fin))]
                    self._ultima_linea = None
                    self._reiniciar_vivo()
                    self.mensaje.emit("Arco tangente creado. Seguí con la línea o Esc.")
            else:
                self.inferencia = self._presion_inferencia
                self.inf_actual = self._presion_inf_actual
                if (self.herramienta == "spline_ajuste" and len(self.clics) >= 3 and pid is not None
                        and pid == self.clics[0][0]):
                    xy = self.clics[0][1]            # clic en el primer punto: cierra la spline
                elif (self.herramienta == "spline_ajuste" and len(self.clics) >= 3 and pid is None
                      and self.clics[0][0] is None and math.dist(xy, self.clics[0][1]) * self.px_por_mm() < TOL_PX):
                    xy = self.clics[0][1]
                self._registrar_clic(pid, xy)
        self.update()

    def colores_ventana(self, a=None, b=None):
        """(relleno, borde o None) de la ventana de selección, con los colores de Fusion."""
        if a is None:
            a, b = self._ventana
        if b.x() < a.x():
            return VENTANA_CRUCE, None          # de derecha a izquierda: amarillo, elige lo que toca
        return VENTANA_RELLENO, VENTANA_BORDE   # de izquierda a derecha: naranja, elige lo que queda adentro

    def _seleccionar_ventana(self, a, b):
        if self.objetos.modo_perfiles:
            self.mensaje.emit("Perfiles CAD: usá Ctrl o Mayús + clic para seleccionar varias regiones.")
            return
        rect = QRectF(a, b).normalized()
        if rect.width() < 3 and rect.height() < 3:
            return
        cruce = b.x() < a.x()       # de derecha a izquierda: alcanza con tocar (como en Fusion)
        sel = list(self.seleccion)
        internos = self._ocultos()[1]
        visibles = {q for c in self.b.curvas.values() if self._visible(c) for q in c.puntos()}
        sueltos = {p for p in self.b.puntos if not any(p in c.puntos() for c in self.b.curvas.values())}
        for p in self.b.puntos.values():
            if p.id not in internos and (p.id in visibles or p.id in sueltos) and rect.contains(self.a_px(p.x, p.y)) and p.id not in sel:
                sel.append(p.id)
        for c in self.b.curvas.values():
            if not self._visible(c) or c.id in sel:
                continue
            if self.b.objetos:
                from ..restricciones import objetos
                if c.id in objetos.indice(self.b):
                    continue
            polis = [self._poli_px(poli) for poli in self._polilineas(c, 24)]
            pts = [q for poli in polis for q in poli]
            if not pts:
                continue
            if cruce:
                toca = any(rect.contains(q) for q in pts) or any(
                    _segmento_en_rect(rect, q1, q2) for poli in polis for q1, q2 in zip(poli, poli[1:], strict=False))
            else:
                toca = all(rect.contains(q) for q in pts)
            if toca:
                sel.append(c.id)
        for oid, (camino, _borde) in self.objetos._datos().items():
            o = self.b.objetos[oid]
            if o["visible"] and not o["bloqueado"] and oid not in sel and (
                    rect.intersects(camino.boundingRect()) if cruce else rect.contains(camino.boundingRect())):
                sel.append(oid)
        self.seleccion = sel
        self.cambio.emit()
        self._notificar_seleccion()

    def cadena_conectada(self, cid):
        """Curvas unidas por sus extremos a `cid` (doble clic de Fusion): puntos compartidos o coincidentes.
        Se recorren solo las del mismo tipo (normal / construcción)."""
        base = self.b.curvas[cid]
        gemelos = {}
        for r in self.b.restricciones.values():
            if r.tipo == "coincidente" and len(r.entidades) == 2 and all(e in self.b.puntos for e in r.entidades):
                a, b = r.entidades
                gemelos.setdefault(a, set()).add(b)
                gemelos.setdefault(b, set()).add(a)
        por_punto = {}
        for c in self.b.curvas.values():
            if self._visible(c) and not isinstance(c, Texto) and c.construccion == base.construccion:
                for p in c.extremos() or ():
                    por_punto.setdefault(p, []).append(c.id)
        salida, pendientes = [cid], [cid]
        while pendientes:
            k = pendientes.pop()
            for p in self.b.curvas[k].extremos() or ():
                for q in {p} | gemelos.get(p, set()):
                    for otra in por_punto.get(q, []):
                        if otra not in salida:
                            salida.append(otra)
                            pendientes.append(otra)
        return salida

    def _largo(self, cid):
        c = self.b.curvas[cid]
        if isinstance(c, Linea):
            return math.dist(*self.b._extremos_linea(cid))
        if isinstance(c, Circulo):
            return 2 * math.pi * c.radio
        if isinstance(c, Arco):
            (cx, cy), (sx, sy), (ex, ey) = (self.b.coords(q) for q in (c.centro, c.inicio, c.fin))
            return self.b.radio(cid) * _barrido(math.atan2(sy - cy, sx - cx), math.atan2(ey - cy, ex - cx))
        return sum(math.dist(a, b) for poli in self._polilineas(c, 256) for a, b in zip(poli, poli[1:], strict=False))

    def describir_seleccion(self):
        """Medidas de lo elegido con el formato de Fusion ("1 línea de boceto | Longitud: 123.698 mm")."""
        elegidos = self.objetos.seleccion()
        if elegidos:
            return f"{len(elegidos)} objeto(s) vectorial(es)" + (f" · {self.b.objetos[elegidos[0]]['nombre']}" if len(elegidos) == 1 else "")
        curvas = [i for i in self.seleccion if i in self.b.curvas]
        puntos = [i for i in self.seleccion if i in self.b.puntos]
        perfiles = self.perfiles_seleccionados() if self.perfiles_sel else []
        if perfiles:
            nombre = "1 perfil de boceto" if len(perfiles) == 1 else f"{len(perfiles)} perfiles de boceto"
            return f"{nombre} | Área: {formato.numero(sum(p.area for p in perfiles))} mm²"
        if curvas:
            if len(curvas) == 1 and not puntos:
                c = self.b.curvas[curvas[0]]
                nombre = f"1 {NOMBRES_ENTIDAD.get(c.tipo, c.tipo)} de boceto"
                if isinstance(c, Texto):
                    return nombre
                if isinstance(c, Circulo):
                    return f"{nombre} | Radio: {texto_valor(c.radio)}"
                return f"{nombre} | Longitud: {texto_valor(self._largo(c.id))}"
            total = sum(self._largo(k) for k in curvas if not isinstance(self.b.curvas[k], Texto))
            return f"{len(curvas)} curvas de boceto | Longitud: {texto_valor(total)}"
        if puntos:
            return "1 punto de boceto" if len(puntos) == 1 else f"{len(puntos)} puntos de boceto"
        cotas = sum(1 for i in self.seleccion if i in self.b.cotas)
        if cotas:
            return "1 cota de boceto" if cotas == 1 else f"{cotas} cotas de boceto"
        restricciones = sum(1 for i in self.seleccion if i in self.b.restricciones)
        if restricciones:
            return "1 restricción de boceto" if restricciones == 1 else f"{restricciones} restricciones de boceto"
        return ""

    def _notificar_seleccion(self):
        self.objetos.registrar_textos()
        self.objetos.notificar()
        texto = self.describir_seleccion()
        if texto != self._info:
            self._info = texto
            self.info.emit(texto)
        self._emitir_simetria()
        self.patron.notificar()
        self.seleccion_cambiada.emit()
        self.transformar.notificar()

    def mouseDoubleClickEvent(self, e):
        if self.visor is not None and e.button() == Qt.MiddleButton:
            self.visor.mouseDoubleClickEvent(e)
            return
        if (e.button() == Qt.LeftButton and self._previa_texto is not None and self.entrada is not None
                and self._sobre_texto(e.position())):
            self._seleccionar_palabra(e.position())          # doble clic en el texto: elige la palabra
            return
        if e.button() == Qt.LeftButton:
            if self.herramienta in SPLINES:
                self._terminar_spline()          # el primer clic ya agregó el punto; el segundo solo termina
                return
            zona = self._zona_en(e.position())
            glifo = self.b.restricciones.get(zona) if zona not in self.b.cotas else None
            pid = self.patron_de(glifo.entidades) if glifo is not None and glifo.tipo == "patron" else None
            if pid is not None:                      # doble clic en el glifo del patrón: editarlo (BOC-16)
                self.editar_patron(pid)
            elif zona in self.b.cotas and e.modifiers() & Qt.ShiftModifier:
                self.alternar_referencia(zona)
            elif zona in self.b.cotas:
                self.editar_cota(zona, e.position())
            elif self.herramienta == "linea":
                self.cancelar()
            elif self.herramienta == "seleccionar":
                cid = self._curva_cercana(e.position(), tipos=("texto",))
                if cid is not None:
                    self.editar_texto(cid, e.position())
                    return
                cid = self._curva_cercana(e.position())
                if cid is not None:                  # doble clic: toda la cadena de curvas unidas
                    cadena = self.cadena_conectada(cid)
                    if e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
                        cadena = self.seleccion + [k for k in cadena if k not in self.seleccion]
                    self.seleccion = cadena
                    self.cambio.emit()
                    self._notificar_seleccion()
                    self.update()

    def wheelEvent(self, e):
        if self.visor is not None:
            self.visor.wheelEvent(e)
            return
        antes = self.a_mm(e.position())
        self.escala = max(0.05, min(500.0, self.escala * (1.4 ** (e.angleDelta().y() / 120.0))))
        despues = self.a_mm(e.position())
        self.centro[0] += antes[0] - despues[0]
        self.centro[1] += antes[1] - despues[1]
        self.update()

    def _admite_entrada(self, e):
        if not (bool(e.text()) and e.text() in "0123456789.,-(" and not e.modifiers() & Qt.ControlModifier):
            return False
        h = self.herramienta
        if h == "circulo_2t":
            return len(self.picks) == 2
        if h == "espiral":
            return self.entrada is not None      # B-689: la caja abierta recibe lo tecleado en el Lienzo
        return bool(self._claves_vivas()) or self._cota_elegida() is not None

    def _cota_elegida(self):
        """B-652: id de la única cota con driving elegida (teclear un número la edita, como Fusion), o None."""
        if self.herramienta != "seleccionar" or self.entrada is not None or len(self.seleccion) != 1:
            return None
        cid = self.seleccion[0]
        cota = self.b.cotas.get(cid)
        return cid if cota is not None and not cota.referencia and cid in self._zonas_cotas else None

    def event(self, e):
        if e.type() == QEvent.WindowDeactivate and getattr(self, "objetos", None) is not None:
            self.objetos.cancelar()
        # Mientras se dibuja, los números son la entrada dinámica (no los atajos de vista 0-3) y
        # Supr / Enter / Esc son del boceto: se reclaman antes de que actúen los atajos de la ventana.
        if e.type() == e.Type.ShortcutOverride and self._previa_texto is not None and self.entrada is not None:
            e.accept()                      # escribiendo en el cuadro de texto: ningún atajo de la ventana
            return True
        if (e.type() == e.Type.KeyPress and e.key() in (Qt.Key_Tab, Qt.Key_Backtab)
                and self._previa_texto is not None and self.entrada is not None):
            self.entrada.campos[1].setFocus()          # Tab: de la escritura en el cuadro a la altura
            self.entrada.campos[1].selectAll()
            return True
        if e.type() == e.Type.ShortcutOverride and (
                self._admite_entrada(e) or e.key() in (Qt.Key_Delete, Qt.Key_Backspace, Qt.Key_Escape,
                                                       Qt.Key_Return, Qt.Key_Enter)
                or e.matches(QKeySequence.SelectAll)
                # Ctrl+Z / Ctrl+Y del boceto: los atiende el lienzo (B-705), no el atajo de la ventana (evita doble).
                or (e.modifiers() & Qt.ControlModifier and e.key() in (Qt.Key_Z, Qt.Key_Y))
                # Espacio (alternar ayudas) y Flecha arriba (bloquear) son del boceto mientras hay una ayuda activa:
                # Espacio es también el atajo de «Boceto sobre la cara» de la ventana
                or (e.key() in (Qt.Key_Space, Qt.Key_Up) and (self.inf_lista or self._inf_bloqueo is not None))):
            e.accept()
            return True
        # Tab / Mayús+Tab pasan de una caja de valor a la otra (no mueven el foco a otro control).
        if e.type() == e.Type.KeyPress and e.key() in (Qt.Key_Tab, Qt.Key_Backtab) and self._claves_vivas():
            n = len(self._claves_vivas())
            atras = e.key() == Qt.Key_Backtab or bool(e.modifiers() & Qt.ShiftModifier)
            self._activo = (self._activo + (-1 if atras else 1)) % n
            self.update()
            return True
        return super().event(e)

    def keyPressEvent(self, e):
        if self._teclado_en_texto(e):
            return
        k = e.key()
        h = self.herramienta
        if k == Qt.Key_Control:
            self._modificadores_raton = e.modifiers()       # Ctrl apaga las ayudas mientras se mantiene
            self._refrescar_cursor()
        # B-689: la caja de la espiral queda abierta tras los 2 clics y el foco puede quedar en el Lienzo;
        # lo tecleado entra en «Vueltas» y Enter la crea (con lo escrito o los valores por defecto, como Fusion).
        if h == "espiral" and self.entrada is not None:
            if k in (Qt.Key_Return, Qt.Key_Enter):
                self.entrada.aceptado.emit([c.text().strip() for c in self.entrada.campos])
                return
            if self._admite_entrada(e):
                self.entrada.campos[0].setFocus()
                self.entrada.campos[0].setText(e.text())
                return
        if k == Qt.Key_Escape:
            if self.visor is not None and self.visor.modo:
                self.visor.set_modo(None)
            else:
                self.cancelar()
        elif e.matches(QKeySequence.Copy) and self.seleccion:
            self.copiar_seleccion()
        elif e.matches(QKeySequence.Paste) and PORTAPAPELES:
            self.pegar()
        elif e.matches(QKeySequence.SelectAll):
            en_curvas = {p for c in self.b.curvas.values() for p in c.puntos()}
            ocultos = self._ocultos()[1]
            self.seleccion = [c.id for c in self.b.curvas.values() if self._visible(c)]
            self.seleccion += [p.id for p in self.b.puntos.values()
                               if p.id > 0 and p.id not in en_curvas and p.id not in ocultos]
            self.cambio.emit()
            self._notificar_seleccion()
            self.update()
        elif (e.modifiers() & Qt.ControlModifier) and k == Qt.Key_Z:
            self.deshacer()
        elif (e.modifiers() & Qt.ControlModifier) and k == Qt.Key_Y:
            self.rehacer()
        elif k == Qt.Key_Space and self.inf_lista:
            self._inf_alt += 1                       # alterna entre las ayudas ambiguas bajo el cursor
            self._refrescar_cursor()
        elif k == Qt.Key_Up and (self.inf_actual is not None or self._inf_bloqueo is not None):
            self._inf_bloqueo, self._inf_bloqueo_clics = (
                (None, 0) if self._inf_bloqueo is not None else (self.inf_actual, len(self.clics)))
            self._refrescar_cursor()
        elif k in (Qt.Key_Delete, Qt.Key_Backspace):
            self.borrar_seleccion()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h in SPLINES and self.clics:
            self._terminar_spline()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h == "simetria":
            self._enter_simetria()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and self._hay_tarjeta_proyeccion():
            self.aceptar_proyeccion()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h in PATRON:
            self.patron.enter()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h in TRANSFORMAR:
            self.transformar.enter()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h in SELECCION and self.fase == "seleccion":
            self._avanzar_seleccion()
        elif k in (Qt.Key_Return, Qt.Key_Enter) and any(c in self._bloqueos for c in self._claves_vivas()):
            self._confirmar_vivo()                   # Enter con valores escritos: crea con esos valores
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h == "desfase" and self.entrada is not None:
            self.entrada.aceptado.emit([c.text().strip() for c in self.entrada.campos])    # Enter fuera de la caja
        elif k in (Qt.Key_Return, Qt.Key_Enter) and h != "seleccionar":
            self.cancelar()
        elif self._admite_entrada(e):
            if self._claves_vivas():
                self._editar_campo_vivo(e.text())
            elif (cid := self._cota_elegida()) is not None:
                self.editar_cota(cid, self._zonas_cotas[cid].center())     # B-652: el número abre la caja de la cota
                if self.entrada is not None:
                    self.entrada.campos[0].setText(e.text())
            else:
                self._entrada_dinamica(e.text())
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Control and self.ajustes_inf["inferencias"]:
            self._modificadores_raton = e.modifiers()       # soltar Ctrl vuelve a encender las ayudas sin mover el ratón
            self._refrescar_cursor()
        super().keyReleaseEvent(e)

    def _refrescar_cursor(self):
        """Recalcula el ajuste del cursor sin que se mueva el ratón (alternar, bloquear, Ctrl)."""
        if self.cursor is not None:
            excluir = self._arrastre if isinstance(self._arrastre, int) else None
            self.cursor = self._ajustar(self._pos_cursor, excluir=excluir, base=self._base_inferencia())[1]
            self.update()

    def _oscuro(self):
        return self.visor is not None and self.visor.config.oscuro()

    def _color_curva(self, c, determinadas, fijos, en_conflicto=frozenset()):
        if c.id == self._eje_simetria and self.herramienta == "simetria":
            return QColor(255, 140, 0), 3.5          # la línea de simetría se distingue de lo elegido (celeste)
        if c.id in self.seleccion or c.id in self.picks:
            return QColor(0, 180, 255), 3.0
        if c.id == self._sobre:
            return QColor(255, 170, 40), 3.0        # lo que se agarraría al hacer clic
        if c.id in en_conflicto or set(c.puntos()) & en_conflicto:
            return CONFLICTO, 2.5
        if c.construccion:                      # tema oscuro de Fusion: gris claro punteado; claro: naranja
            return (QColor(205, 205, 210) if self._oscuro() else QColor(240, 150, 60)), 1.5   # también la proyectada
        if c.proyectada:
            return VIOLETA, 2.0
        if set(c.puntos()) <= fijos:
            return QColor(70, 200, 100), 2.0
        if c.id in determinadas:
            return (QColor(245, 245, 245) if self._oscuro() else QColor(20, 20, 20)), 2.0
        return QColor(90, 160, 255) if self._oscuro() else QColor(25, 90, 200), 2.0

    def _dibujar_capa_curvas(self, p, capa, cuadros):
        """RS-X3: las curvas y los puntos se dibujan en una imagen guardada y después se pegan: el cursor y el hover repintan
        sin volver a trazarlos. La clave es exactamente lo que se dibuja (cada curva con su color, grosor, estilo, polilíneas y
        guías; cada punto con su lugar y sus colores; la cámara y el tamaño), así que cualquier cambio de geometría,
        selección, hover, conflictos, tema o capas visibles cambia algún elemento y rearma la imagen."""
        dpr = self.devicePixelRatioF()
        clave = (self._firma_camara(), self.width(), self.height(), dpr, tuple(capa), tuple(cuadros))
        if clave != self._capa_clave:
            img = QPixmap(max(1, round(self.width() * dpr)), max(1, round(self.height() * dpr)))
            img.setDevicePixelRatio(dpr)
            img.fill(Qt.transparent)
            q = QPainter(img)
            q.setRenderHint(QPainter.Antialiasing)
            for _cid, rgba, ancho, estilo, polis, extra in capa:
                q.setPen(QPen(QColor.fromRgba(rgba), ancho, estilo))
                for poli in polis:
                    self._dibujar_polilinea(q, poli)
                if extra is not None and extra[0] == "marco":
                    q.setPen(QPen(QColor(150, 150, 160), 1, Qt.DotLine))      # marco de control, como Fusion
                    self._dibujar_polilinea(q, list(extra[1]))
                elif extra is not None:
                    self._dibujar_guias_conica(q, *extra[1:])
            for x, y, borde, relleno in cuadros:
                q.setPen(QPen(QColor.fromRgba(borde), 1))
                q.setBrush(QColor.fromRgba(relleno))
                q.drawRect(QRectF(x - 3, y - 3, 6, 6))
            q.end()
            self._capa_clave, self._capa_img = clave, img
        p.drawPixmap(0, 0, self._capa_img)

    def _dibujar_polilinea(self, p, puntos):
        poli = self._poli_px(puntos)
        if poli:
            p.drawPolyline(poli)

    def _ancla(self, ent):
        """Posición (px) donde dibujar textos asociados a una entidad."""
        if ent in self.b.puntos:
            return self.a_px(*self.b.coords(ent))
        c = self.b.curvas[ent]
        if isinstance(c, Linea):
            (x1, y1), (x2, y2) = self.b.coords(c.p1), self.b.coords(c.p2)
            return self.a_px((x1 + x2) / 2, (y1 + y2) / 2)
        if isinstance(c, Texto):
            return self.a_px(*self.b.coords(c.punto))
        prims = self.b.primitivas(ent)
        if not prims:
            return self.a_px(*self.b.coords(c.puntos()[0]))
        prim = prims[0]
        t0, t1, per = dominio(prim)
        t = t0 + (t1 - t0) * (0.125 if per else 0.5)
        return self.a_px(*evaluar_primitiva(prim, t)[0])

    def _fondo_2d(self, p):
        p.fillRect(self.rect(), FONDO_LIENZO)
        s = self.paso_grilla()
        (x0, y1), (x1, y0) = self.a_mm(QPointF(0, 0)), self.a_mm(QPointF(self.width(), self.height()))
        i0, i1 = math.floor(x0 / s), math.ceil(x1 / s)
        j0, j1 = math.floor(y0 / s), math.ceil(y1 / s)
        if (i1 - i0) + (j1 - j0) < 600:
            for i in range(i0, i1 + 1):
                p.setPen(QPen(QColor(215, 218, 225) if i % 5 else QColor(190, 195, 205), 1))
                q = self.a_px(i * s, 0)
                p.drawLine(QPointF(q.x(), 0), QPointF(q.x(), self.height()))
            for j in range(j0, j1 + 1):
                p.setPen(QPen(QColor(215, 218, 225) if j % 5 else QColor(190, 195, 205), 1))
                q = self.a_px(0, j * s)
                p.drawLine(QPointF(0, q.y()), QPointF(self.width(), q.y()))
        o = self.a_px(0, 0)
        p.setPen(QPen(QColor(210, 70, 70), 1.5))
        p.drawLine(QPointF(0, o.y()), QPointF(self.width(), o.y()))
        p.setPen(QPen(QColor(60, 160, 70), 1.5))
        p.drawLine(QPointF(o.x(), 0), QPointF(o.x(), self.height()))

    def _numeros_rejilla(self, p):
        """Números de referencia sobre los ejes del boceto (como la rejilla del boceto de Fusion)."""
        mayor = self.paso_grilla() * self.visor.subdivisiones_rejilla()      # P-197: cada línea mayor
        cu, cv = self.plano.a_uv(self.visor.objetivo)
        p.setFont(temas.qfont_cotas(8))
        p.setPen(QColor(140, 146, 158) if self._oscuro() else QColor(80, 85, 95))     # números tenues, como Fusion
        for i in range(-8, 9):
            for u, v in ((round(cu / mayor) * mayor + i * mayor, 0.0), (0.0, round(cv / mayor) * mayor + i * mayor)):
                valor = u if v == 0.0 and u != 0.0 else v
                if valor == 0.0:
                    continue
                q = self.a_px(u, v)
                if 0 <= q.x() <= self.width() and 0 <= q.y() <= self.height():
                    p.drawText(q + QPointF(4, -4), formato.numero(valor))
