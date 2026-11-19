"""LienzoTextoMixin: métodos del lienzo por tema."""

from .editor_boceto_comun import (
    ANGULO,
    CURVA_TEXTO,
    ErrorBoceto,
    ErrorExpresion,
    QApplication,
    Qt,
    Texto,
    _espaciado_mm,
    _espaciado_porcentaje,
    _fin_palabra,
    _inicio_palabra,
    _numero,
    _palabra_en,
    _validar_opciones_texto,
    copy,
    formato,
    math,
    nombres_usados,
    paradas_cursor,
    primitivas_entidad,
    puntos_primitiva,
)


class LienzoTextoMixin:
    def alternar_eje(self):
        """Tipo de línea «línea central» (eje): alterna lo seleccionado, o lo que se dibuje."""
        curvas = [i for i in self.seleccion if i in self.b.curvas and not isinstance(self.b.curvas[i], Texto)]
        if not curvas:
            self.eje = not self.eje
            if self.eje:
                self.construccion = False
            self.mensaje.emit("Las curvas nuevas son líneas centrales (eje)." if self.eje
                              else "Las curvas nuevas son normales.")
            self._emitir_proyeccion()
            return

        def cambiar():
            nuevo = not all(self.b.curvas[i].eje for i in curvas)
            for i in curvas:
                self.b.curvas[i].eje = nuevo
                if nuevo:
                    self.b.curvas[i].construccion = False
        self.aplicar_cambio(cambiar)

    def editar_texto(self, tid, pos):
        t = self.b.curvas[tid]
        # la paleta parte de lo que ya tiene el texto: aceptar sin tocar nada no le cambia la fuente ni la alineación
        self.opciones.update(fuente=t.fuente, negrita=t.negrita, cursiva=t.cursiva, alineacion=t.alineacion,
                             ancla_v=t.ancla_v, altura_texto=t.altura, **{k: getattr(t, k) for k in CURVA_TEXTO},
                             voltear_h=t.voltear_h, voltear_v=t.voltear_v,
                             espaciado=t.espaciado, interlineado=t.interlineado,
                             **{k: getattr(t, k) for k in Texto.TIPOGRAFIA})
        self.opciones.update(marco_texto=bool(t.marco), pivote_texto=None,
                             parametro_texto=t.parametro_texto, valor_parametro_texto="")

        def aceptar(v):
            t = self.b.curvas[tid]
            v = (list(v) + [""] * 5)[:5]
            altura, ang = self.evaluar(v[1] or "5"), self.evaluar(v[2] or "0", ANGULO)
            espaciado, interlineado = _espaciado_mm(v[3], altura, self.opciones), _numero(v[4] or "1")
            if not v[0].strip():
                raise ErrorBoceto("El texto está vacío.")
            if interlineado <= 0:
                raise ErrorBoceto("El interlineado tiene que ser mayor que cero.")
            _validar_opciones_texto({k: self.opciones[k] for k in Texto.TIPOGRAFIA})
            pivote = self.opciones.get("pivote_texto")
            pivote = self.b.esquina_marco(tid, pivote.removeprefix("corner:")) if pivote else None

            def cambiar():
                texto = v[0].replace("\\n", "\n")
                if t.altura_expr and abs(altura - t.altura) > 1e-9:      # si no, el recálculo vuelve a la altura de antes
                    t.altura_expr = v[1] if nombres_usados(v[1]) else f"{altura:.12g} mm"
                t.texto, t.altura = texto, altura
                if t.marco:
                    self.b.girar_texto(tid, ang, pivote)
                else:
                    t.angulo = ang
                t.fuente, t.negrita, t.cursiva = self.opciones["fuente"], self.opciones["negrita"], self.opciones["cursiva"]
                t.espaciado, t.interlineado = espaciado, interlineado
                t.alineacion, t.ancla_v = self.opciones["alineacion"], self.opciones["ancla_v"]
                t.voltear_h, t.voltear_v = bool(self.opciones["voltear_h"]), bool(self.opciones["voltear_v"])
                for k in CURVA_TEXTO:
                    setattr(t, k, self.opciones[k])
                for k, tipo in Texto.TIPOGRAFIA.items():
                    setattr(t, k, tipo(self.opciones[k]))
                if t.parametro_texto and self.editar_parametro_texto is not None:
                    t.texto = "{" + t.parametro_texto + "}"
            rehacer = self.pila_rehacer[:]
            if not self.aplicar_cambio(cambiar):
                return False
            texto = v[0].replace("\\n", "\n")
            if t.parametro_texto and self.editar_parametro_texto is not None and texto != self.opciones["valor_parametro_texto"]:
                try:
                    self.editar_parametro_texto(t.parametro_texto, texto)
                except ErrorBoceto as e:
                    self._restaurar(self.historial.pop())
                    self.pila_rehacer[:] = rehacer
                    self.resolver()
                    self.mensaje.emit(str(e))
                    return False
            return True
        self._abrir_entrada(["Texto", "Altura", "∠", "Espaciado (%)", "Interlineado"],
                            [t.texto.replace("\n", "\\n"), formato.numero(t.altura), formato.numero(t.angulo, True),
                             _espaciado_porcentaje(t.espaciado, t.altura, self.opciones), formato.numero(t.interlineado)], pos, aceptar)
        # como en Fusion, al editar un texto se ven sus opciones (fuente, negrita, alineación…) en la paleta
        self._paleta_texto = True
        self._previa_texto = {"pos": None, "existente": tid, "extra": {}, "caja": None, "reemplazar": False,
                              "cursor": len(t.texto)}
        self._texto_oculto = tid                 # mientras se escribe se ve la previa en vivo en su lugar
        self._conectar_previa_texto()
        self.texto_en_edicion.emit()
        i = self._indice_en_texto(pos)           # el cursor queda donde se hizo doble clic
        if i is not None:
            self._previa_texto["cursor"] = i
            self._actualizar_cursor()

    def _conectar_previa_texto(self):
        """Cada letra o número que se escribe en la caja redibuja el texto en vivo."""
        for campo in self.entrada.campos:
            campo.textChanged.connect(lambda _t: self.refrescar_previa_texto())
        self.entrada.hacer_movible()
        self.entrada.ocultar_primero()           # el texto se escribe en el cuadro, no en la barra
        d, n = self._previa_texto, len(self._texto_real())
        d.setdefault("cursor", n)
        d.update(ancla=None, col=None, mapa=None, deshacer=[], rehacer=[])
        if d.get("reemplazar") and n:            # el «Texto» de relleno arranca seleccionado: escribir lo reemplaza
            d["cursor"], d["ancla"] = n, 0
        d["cursor"] = min(d["cursor"], n)
        self._caret_on = True
        self._t_caret.start()
        self.setFocus()
        self.mensaje.emit("Escribí el texto directamente en el cuadro. Flechas o clic = mover el cursor; Mayús = "
                          "seleccionar; Enter = línea nueva; Ctrl+Enter o clic afuera = aceptar; Tab = altura y "
                          "demás; Esc = cancelar.")
        self.refrescar_previa_texto()

    def confirmar_texto_pendiente(self):
        """Acepta el texto que está abierto en el cuadro (si hay uno): al salir del boceto, cambiar de herramienta
        o usar el menú radial no se pierde lo escrito."""
        if self._previa_texto is not None and self.entrada is not None:
            self.entrada.aceptado.emit([c.text().strip() for c in self.entrada.campos])

    def _texto_real(self):
        """Lo escrito en el cuadro, con saltos de línea reales (en el campo van como «\\n»)."""
        return self.entrada.campos[0].text().replace("\\n", "\n")

    def _seleccion_texto(self):
        """(desde, hasta) de lo seleccionado en el texto, o None si no hay selección."""
        d = self._previa_texto
        a, c = d["ancla"], d["cursor"]
        return None if a is None or a == c else (min(a, c), max(a, c))

    def _escribir_texto(self, texto, cursor, ancla=None, historial=True):
        """Pone `texto` en el cuadro con el cursor (y la selección) donde se pide; queda para deshacer."""
        d = self._previa_texto
        if historial:
            d["deshacer"].append((self._texto_real(), d["cursor"], d["ancla"]))
            del d["deshacer"][:-200]
            d["rehacer"] = []
        d["cursor"], d["ancla"], d["col"] = cursor, ancla, None
        campo, nuevo = self.entrada.campos[0], texto.replace("\n", "\\n")
        if campo.text() != nuevo:
            campo.setText(nuevo)                 # textChanged vuelve a calcular la vista previa
        else:
            self.refrescar_previa_texto()

    def escribir_contenido_texto(self, texto):
        """B-665: lo escrito en «Contenido» (panel Carácter) pasa al cuadro abierto, con deshacer y el cursor al final."""
        if self._previa_texto is not None and self.entrada is not None:
            real = texto.replace("\\n", "\n")
            self._escribir_texto(real, len(real))

    def _reemplazar_rango(self, desde, hasta, nuevo):
        texto = self._texto_real()
        corrimiento = len(nuevo) - (hasta - desde)
        self.opciones["ajustes_kerning"] = [          # el kerning a mano sigue a sus letras; el de lo borrado se va
            [i + (corrimiento if i > hasta else 0), x] for i, x in self.opciones.get("ajustes_kerning", [])
            if i <= desde or i > hasta]
        self._escribir_texto(texto[:desde] + nuevo + texto[hasta:], desde + len(nuevo))

    def _kerning_en(self, i):
        """mm de kerning a mano entre la letra i - 1 y la i."""
        return next((x for j, x in self.opciones.get("ajustes_kerning", []) if j == i), 0.0)

    def ajustar_kerning_par(self, mm):
        """Kerning a mano entre las dos letras que rodean al cursor (mm; 0 lo quita)."""
        d = self._previa_texto
        if d is None or self.entrada is None or d["cursor"] <= 0:
            return
        i = d["cursor"]
        resto = [[j, x] for j, x in self.opciones.get("ajustes_kerning", []) if j != i]
        self.opciones["ajustes_kerning"] = resto + ([[i, float(mm)]] if abs(mm) > 1e-9 else [])
        self.refrescar_previa_texto()

    def aplicar_opcion_texto(self, clave, valor):
        """Tamaño, interletraje o interlineado desde el panel «Carácter»: quedan en las opciones y, con el cuadro
        abierto, en su barra (que es donde se leen al aceptar)."""
        self.opciones[clave] = float(valor)
        if self._previa_texto is not None and self.entrada is not None:
            campo = {"altura_texto": 1, "espaciado": 3, "interlineado": 4}[clave]
            texto = formato.numero(valor)
            if clave == "espaciado":
                texto = _espaciado_porcentaje(valor, self._previa_texto.get("valores", (self.opciones["altura_texto"],))[0],
                                              self.opciones)
            if self.entrada.campos[campo].text() != texto:
                self.entrada.campos[campo].setText(texto)

    def _insertar_en_texto(self, cadena):
        """Escribe `cadena` en el cursor (si hay selección, la reemplaza)."""
        sel = self._seleccion_texto()
        cur = self._previa_texto["cursor"]
        self._reemplazar_rango(*(sel if sel else (cur, cur)), cadena)

    def _deshacer_texto(self, rehacer=False):
        d = self._previa_texto
        pila, otra = (d["rehacer"], d["deshacer"]) if rehacer else (d["deshacer"], d["rehacer"])
        if pila:
            otra.append((self._texto_real(), d["cursor"], d["ancla"]))
            texto, cursor, ancla = pila.pop()
            self._escribir_texto(texto, cursor, ancla, historial=False)

    def _mover_cursor(self, destino, extender=False, col=None):
        """Lleva el cursor a `destino`; con `extender` (Mayús) deja la selección desde donde estaba."""
        d = self._previa_texto
        if extender:
            if d["ancla"] is None:
                d["ancla"] = d["cursor"]
        else:
            d["ancla"] = None
        d["cursor"], d["col"] = destino, col
        self._caret_on = True
        self._t_caret.start()
        self._actualizar_cursor()
        self.update()

    def _vertical_texto(self, cur, delta):
        """Posición del cursor una línea más arriba (-1) o abajo (+1), en la misma columna; (posición, columna)."""
        d = self._previa_texto
        info = d.get("mapa")
        if not info:
            return (0 if delta < 0 else len(self._texto_real())), None
        k = info["linea_de"][cur] + delta
        if k < 0:
            return 0, None
        if k >= len(info["lineas"]):
            return len(info["paradas"]) - 1, None
        ux, uy = info["dir"]

        def columna(i):
            x, y = info["paradas"][i][0]
            return x * ux + y * uy
        col = d["col"] if d["col"] is not None else columna(cur)
        ini, fin = info["lineas"][k]
        return min(range(ini, fin + 1), key=lambda i: abs(columna(i) - col)), col

    def _teclado_en_texto(self, e):
        """Teclas con el cuadro de texto abierto: editan el texto del lienzo en la posición del cursor. True si las
        atendió."""
        d = self._previa_texto
        if d is None or self.entrada is None:
            return False
        k, mods = e.key(), e.modifiers()
        ctrl, mayus = bool(mods & Qt.ControlModifier), bool(mods & Qt.ShiftModifier)
        if k == Qt.Key_Escape:
            self.cancelar()
            return True
        texto = self._texto_real()
        n = len(texto)
        cur = min(max(d["cursor"], 0), n)
        sel = self._seleccion_texto()
        info = d.get("mapa")
        linea = info["lineas"][info["linea_de"][cur]] if info else (0, n)
        if k in (Qt.Key_Return, Qt.Key_Enter):
            if ctrl:
                self.entrada.aceptado.emit([c.text().strip() for c in self.entrada.campos])
            else:
                self._insertar_en_texto("\n")
        elif k in (Qt.Key_Left, Qt.Key_Right) and mods & Qt.AltModifier and not ctrl:
            paso = 0.02 * max(self.opciones.get("altura_texto", 5.0), 0.1)         # Alt+←/→: kerning del cursor
            self.ajustar_kerning_par(self._kerning_en(cur) + (-paso if k == Qt.Key_Left else paso))
        elif k == Qt.Key_Left:
            if sel and not mayus and not ctrl:
                self._mover_cursor(sel[0])
            else:
                self._mover_cursor(max(_inicio_palabra(texto, cur) if ctrl else cur - 1, 0), mayus)
        elif k == Qt.Key_Right:
            if sel and not mayus and not ctrl:
                self._mover_cursor(sel[1])
            else:
                self._mover_cursor(min(_fin_palabra(texto, cur) if ctrl else cur + 1, n), mayus)
        elif k in (Qt.Key_Up, Qt.Key_Down):
            destino, col = self._vertical_texto(cur, -1 if k == Qt.Key_Up else 1)
            self._mover_cursor(destino, mayus, col)
        elif k == Qt.Key_Home:
            self._mover_cursor(0 if ctrl else linea[0], mayus)
        elif k == Qt.Key_End:
            self._mover_cursor(n if ctrl else linea[1], mayus)
        elif k == Qt.Key_Backspace:
            if sel:
                self._reemplazar_rango(*sel, "")
            elif cur > 0:
                self._reemplazar_rango(_inicio_palabra(texto, cur) if ctrl else cur - 1, cur, "")
        elif k == Qt.Key_Delete:
            if sel:
                self._reemplazar_rango(*sel, "")
            elif cur < n:
                self._reemplazar_rango(cur, _fin_palabra(texto, cur) if ctrl else cur + 1, "")
        elif ctrl and k == Qt.Key_A:
            d["ancla"] = 0
            self._mover_cursor(n, True)
        elif ctrl and k in (Qt.Key_C, Qt.Key_X):
            if sel:
                QApplication.clipboard().setText(texto[sel[0]:sel[1]])
                if k == Qt.Key_X:
                    self._reemplazar_rango(*sel, "")
        elif ctrl and k == Qt.Key_V:
            pegado = QApplication.clipboard().text().replace("\r\n", "\n").replace("\r", "\n")
            pegado = pegado.replace("\t", "    ")
            self._insertar_en_texto("".join(c for c in pegado if c == "\n" or c.isprintable()))
        elif ctrl and k in (Qt.Key_Z, Qt.Key_Y):
            self._deshacer_texto(rehacer=k == Qt.Key_Y or mayus)
        elif e.text() and e.text().isprintable() and (not ctrl or mods & Qt.AltModifier):   # AltGr = Ctrl+Alt
            self._insertar_en_texto(e.text())
        else:
            return False
        return True

    def _indice_en_texto(self, pos):
        """Posición del texto (0..n) más cercana al punto de pantalla `pos`; None si todavía no hay mapa."""
        info = (self._previa_texto or {}).get("mapa")
        if not info:
            return None
        x, y = self.a_mm(self.objetos.posicion_texto(pos))
        mejor, menor = None, None
        for i, (a, b) in enumerate(info["paradas"]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            largo2 = dx * dx + dy * dy
            t = 0.0 if largo2 < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / largo2))
            dist = math.hypot(x - (a[0] + t * dx), y - (a[1] + t * dy))
            if menor is None or dist < menor:
                mejor, menor = i, dist
        return mejor

    def _sobre_texto(self, pos):
        """True si el punto de pantalla cae sobre el texto que se escribe (o su cuadro): ahí el clic mueve el cursor;
        afuera, acepta el texto."""
        d = self._previa_texto
        if d is None or self.entrada is None:
            return False
        info = d.get("mapa")
        x, y = self.a_mm(self.objetos.posicion_texto(pos))
        margen = 6.0 / max(self.px_por_mm(), 1e-6)
        cajas = [c for c in (d.get("caja"), info and info.get("caja")) if c]
        return any(c[0] - margen <= x <= c[2] + margen and c[1] - margen <= y <= c[3] + margen for c in cajas)

    def _clic_en_texto(self, pos, mods):
        """Clic dentro del texto que se escribe: el cursor va ahí; Mayús extiende la selección; arrastrar selecciona."""
        d = self._previa_texto
        i = self._indice_en_texto(pos)
        if i is None:
            return
        if mods & Qt.ShiftModifier:
            if d["ancla"] is None:
                d["ancla"] = d["cursor"]
        else:
            d["ancla"] = i
        d["cursor"], d["col"] = i, None
        self._arrastre_texto = True
        self._pos_clic_texto = pos
        self._caret_on = True
        self._t_caret.start()
        self._actualizar_cursor()
        self.update()

    def _seleccionar_palabra(self, pos):
        i = self._indice_en_texto(pos)
        if i is None:
            return
        d = self._previa_texto
        d["ancla"], d["cursor"] = _palabra_en(self._texto_real(), i)
        d["col"] = None
        self._actualizar_cursor()
        self.update()

    def _actualizar_cursor(self):
        """Pone el cursor y la selección (cuadriláteros) según el mapa del texto y la posición guardada."""
        d = self._previa_texto
        info = d.get("mapa") if d else None
        self._sel_texto = []
        if not info:
            self._caret = None
            return
        paradas, n = info["paradas"], len(info["paradas"]) - 1
        d["cursor"] = cur = min(max(d["cursor"], 0), n)
        self._caret = paradas[cur]
        if d.get("valores"):
            self.texto_valores.emit(*d["valores"], self._kerning_en(cur))
        sel = self._seleccion_texto()
        if sel:
            desde, hasta = sel[0], min(sel[1], n)
            for ini, fin in info["lineas"]:
                a, b = max(desde, ini), min(hasta, fin)
                if a < b:
                    self._sel_texto.append([paradas[a][0], paradas[b][0], paradas[b][1], paradas[a][1]])

    def _texto_en_vivo(self, texto, altura, ang, esp, inter):
        """El Texto con lo escrito y las opciones de la paleta (sin tocar el boceto): de ahí salen los contornos
        de la vista previa y el mapa del cursor."""
        d, o = self._previa_texto, self.opciones
        tipografia = {k: o[k] for k in Texto.TIPOGRAFIA}
        if d["existente"] is not None:
            t = copy.copy(self.b.curvas[d["existente"]])
            if t.marco:
                a, b, c = map(self.b.coords, t.puntos())
                pivote = o.get("pivote_texto")
                px, py = self.b.esquina_marco(t.id, pivote.removeprefix("corner:")) if pivote else a
                giro = math.radians(ang) - math.atan2(b[1] - a[1], b[0] - a[0])
                cos, sin = math.cos(giro), math.sin(giro)
                esquinas = [(px + (x - px) * cos - (y - py) * sin,
                             py + (x - px) * sin + (y - py) * cos) for x, y in (a, b, c)]
                t.punto, t.marco = esquinas[0], esquinas[1:]
            t.texto, t.altura, t.angulo = texto, altura, ang
            t.fuente, t.negrita, t.cursiva = o["fuente"], o["negrita"], o["cursiva"]
            t.espaciado, t.interlineado = esp, inter
            t.alineacion, t.ancla_v = o["alineacion"], o["ancla_v"]
            t.voltear_h, t.voltear_v = bool(o["voltear_h"]), bool(o["voltear_v"])
            for k, v in tipografia.items():
                setattr(t, k, v)
            for k in CURVA_TEXTO:
                setattr(t, k, o[k])
            return t
        extra = {"alineacion": o["alineacion"], "ancla_v": o["ancla_v"], "voltear_h": o["voltear_h"],
                 "voltear_v": o["voltear_v"]} | d["extra"]
        if "camino" in d["extra"]:
            extra |= {k: o[k] for k in CURVA_TEXTO}
        return Texto(0, d["pos"], texto, o["fuente"], altura, ang, o["negrita"], o["cursiva"], espaciado=esp,
                     interlineado=inter, altura_a=True, **extra, **tipografia)

    def _cuadro_texto_previa(self):
        """Esquinas (mm) del cuadro del texto que se escribe: el dibujado con el ratón o el que envuelve las letras,
        girado con el texto (Fusion). [] si no hay."""
        d = self._previa_texto or {}
        ang = d.get("angulo") or 0.0
        caja = d.get("caja")
        if caja:                              # el cuadro gira con el texto alrededor de su esquina de arriba a la izquierda
            x0, y0, x1, y1 = caja
            c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            return [(x0 + (x - x0) * c - (y - y1) * s, y1 + (x - x0) * s + (y - y1) * c)
                    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        if not self._previa_polis:
            return []
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        locales = [(q[0] * c + q[1] * s, -q[0] * s + q[1] * c) for poli in self._previa_polis for q in poli]
        x0, x1 = min(q[0] for q in locales), max(q[0] for q in locales)
        y0, y1 = min(q[1] for q in locales), max(q[1] for q in locales)
        return [(x * c - y * s, x * s + y * c) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]

    def _mapa_cursor(self, t, P, ang):
        """Mapa de posiciones del texto `t` para el cursor: ver `paradas_cursor` (más `dir` y `caja`)."""
        prim_camino = None
        if t.camino is not None and t.camino != t.id and t.camino in self.b.curvas \
                and not isinstance(self.b.curvas[t.camino], Texto):
            base = primitivas_entidad(self.b.curvas[t.camino], P)
            prim_camino = base[0] if base else None
        info = paradas_cursor(t, P(t.punto), prim_camino)
        if info is None:
            return None
        a = math.radians(ang)
        info["dir"] = (math.cos(a), math.sin(a))
        puntos = [q for seg in info["paradas"] for q in seg]
        info["caja"] = (min(q[0] for q in puntos), min(q[1] for q in puntos),
                        max(q[0] for q in puntos), max(q[1] for q in puntos))
        return info

    def _parpadeo(self):
        self._caret_on = not self._caret_on
        self.update()

    def refrescar_previa_texto(self):
        """Recalcula los contornos del texto con lo escrito en la caja y con las opciones de la paleta, y deja el
        cursor y la selección donde van."""
        d, e = self._previa_texto, self.entrada
        if d is None or e is None:
            return
        v = ([c.text() for c in e.campos] + [""] * 5)[:5]
        polis, info = [], None
        self._caret_on = True
        self._t_caret.start()         # al escribir el cursor queda fijo y vuelve a parpadear
        try:
            texto = v[0].replace("\\n", "\n")
            altura, ang = self.evaluar(v[1] or "5"), self.evaluar(v[2] or "0", ANGULO)
            esp, inter = _espaciado_mm(v[3], altura, self.opciones), _numero(v[4] or "1")
            if altura > 0 and inter > 0:
                d["angulo"] = ang                # el cuadro de trazos gira con el texto
                t = self._texto_en_vivo(texto, altura, ang, esp, inter)

                def P(q):
                    return q if isinstance(q, tuple) else self.b.coords(q)
                if texto.strip():
                    polis = [list(puntos_primitiva(prim)) for prim in primitivas_entidad(t, P, curvas=self.b.curvas)]
                info = self._mapa_cursor(t, P, ang)
                if info is not None and polis:      # la caja también cubre las letras (p. ej. los subrayados)
                    xs = [q[0] for poli in polis for q in poli]
                    ys = [q[1] for poli in polis for q in poli]
                    c = info["caja"]
                    info["caja"] = (min(c[0], min(xs)), min(c[1], min(ys)), max(c[2], max(xs)), max(c[3], max(ys)))
        except (ErrorBoceto, ErrorExpresion, ValueError, ZeroDivisionError, KeyError):
            polis, info = [], None          # mientras se escribe un valor a medias, no se dibuja nada
        d["mapa"] = info
        self._previa_polis = polis
        try:                                  # lo de la barra pasa a las opciones (y de ahí al panel)
            alt, inter = self.evaluar(v[1] or "5"), _numero(v[4] or "1")
            esp = _espaciado_mm(v[3], alt, self.opciones)
            if alt > 0 and inter > 0:
                d["valores"] = (alt, esp, inter)
                if not d.get("caja"):
                    self.opciones["altura_texto"] = alt
                self.opciones["espaciado"], self.opciones["interlineado"] = esp, inter
        except (ErrorExpresion, ValueError, ZeroDivisionError, KeyError):
            pass
        self._actualizar_cursor()
        self.update()
