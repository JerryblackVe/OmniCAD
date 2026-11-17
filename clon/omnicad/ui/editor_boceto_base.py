"""LienzoBaseMixin: métodos del lienzo por tema."""

from .editor_boceto_comun import (
    AVISO_BORRADAS,
    Boceto,
    Circulo,
    ErrorBoceto,
    ErrorExpresion,
    Indice,
    LONGITUD,
    MODIFICAN,
    NOMBRES_ENTIDAD,
    PICKS,
    QPointF,
    Qt,
    RADIO_INTERIOR_PX,
    Spline,
    TIPOS_COTA,
    TIPOS_RESTRICCION,
    TOL_INFERENCIA,
    TOL_PUNTO,
    TOL_PX,
    Texto,
    _diff_uso,
    _dist_px,
    _foto_uso,
    _muestras,
    _ru,
    _suelta_aislada,
    _tipo_valor,
    copy,
    inferencias,
    math,
    nombres_usados,
    np,
    primitivas_entidad,
    proyectar_bloqueo,
    re,
    replace,
    resolver,
    restricciones_redundantes,
    time,
)


class LienzoBaseMixin:
    def _camara(self):
        if self.visor is not None:
            self._mvp = self.visor.matriz_mvp()

    def a_px(self, x, y):
        if self.visor is None:
            return QPointF((x - self.centro[0]) * self.escala + self.width() / 2,
                           self.height() / 2 - (y - self.centro[1]) * self.escala)
        if self._mvp is None:
            self._camara()
        q = self.visor.proyectar(self.plano.a_3d(x, y), self._mvp)
        return q if q is not None else QPointF(-1e5, -1e5)

    def a_mm(self, p):
        if self.visor is None:
            return ((p.x() - self.width() / 2) / self.escala + self.centro[0],
                    (self.height() / 2 - p.y()) / self.escala + self.centro[1])
        p3 = self.visor.interseccion_plano(p, self.plano)
        return self.plano.a_uv(p3) if p3 is not None else (self.cursor or (0.0, 0.0))

    def px_por_mm(self):
        return self.visor.px_por_mm() if self.visor is not None else self.escala

    def paso_grilla(self):
        if self.visor is not None:
            return self.visor.paso_rejilla()
        bruto = 14 / self.escala
        e = 10 ** math.floor(math.log10(bruto))
        for m in (1, 2, 5, 10):
            if m * e >= bruto:
                return m * e
        return 10 * e

    def encuadrar(self, ids=None):
        """Centra y acerca la vista al boceto entero, o solo a `ids` (Buscar subrestringidos lleva a la entidad
        elegida)."""
        xs, ys = [], []
        from ..restricciones import objetos
        internos = {p for cid in objetos.indice(self.b) for p in self.b.curvas[cid].puntos()}
        for p in self.b.puntos.values():
            if p.id in internos or (ids is not None and p.id not in ids):
                continue
            xs.append(p.x)
            ys.append(p.y)
        for c in self.b.curvas.values():
            if ids is not None and c.id not in ids:
                continue
            for poli in self._polilineas(c, 16):
                xs += [q[0] for q in poli]
                ys += [q[1] for q in poli]
        if self.visor is not None:
            if xs:
                self.visor.objetivo = self.plano.a_3d((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
                radio = max(max(xs) - min(xs), max(ys) - min(ys), 20) / 2
                self.visor.distancia = radio / math.sin(math.radians(self.visor.fov) / 2) * 1.3
                area = self.parentWidget()
                if self.b.objetos and area is not None and hasattr(area, "reubicar"):
                    area.reubicar()
                    izquierda, derecha = 24., self.width() - 24.
                    for w in area.arriba_izq:
                        if w.isVisible():
                            izquierda = max(izquierda, w.geometry().right() - self.x() + 24)
                    for w in [area.paleta, self.objetos.panel]:
                        if w is not None and w.isVisible():
                            derecha = min(derecha, w.x() - self.x() - 24)
                    alto_util = max(self.height() - 120, 80)
                    ancho_util = max(derecha - izquierda, 80)
                    alto_mm = max((max(xs) - min(xs)) * self.height() / ancho_util,
                                  (max(ys) - min(ys)) * self.height() / alto_util, 20)
                    self.visor.distancia = alto_mm / (2 * math.tan(math.radians(self.visor.fov) / 2)) * 1.3
                    self.visor.desplazar((izquierda + derecha) / 2 - self.width() / 2, 0)
                    self._camara()
                self.visor.update()
            return
        if not xs:
            self.centro, self.escala = [0.0, 0.0], 4.0
        else:
            self.centro = [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2]
            ancho, alto = max(max(xs) - min(xs), 20), max(max(ys) - min(ys), 20)
            self.escala = min(self.width() / (ancho * 1.4), self.height() / (alto * 1.4))
        self.update()

    def _instantanea(self):
        self.historial.append(self.b.a_dict())
        if self._recorte_arrastre is not True:     # los recortes siguientes usan una foto temporal para revertir errores
            del self.historial[:-(200 if len(self.b.puntos) < 3000 else 100)]    # un boceto enorme pesa MB por instantánea

    def _restaurar(self, datos):
        nuevo = Boceto.desde_dict(datos)
        self.b.__dict__.update(nuevo.__dict__)   # se conserva el mismo objeto (lo referencian otros)
        from ..restricciones import objetos
        objetos.invalidar(self.b)
        self.objetos._firma = None
        self._indice_inf = None

    def deshacer(self):
        if not self.historial:
            return
        self.pila_rehacer.append(self.b.a_dict())
        self._restaurar(self.historial.pop())
        self._tras_deshacer()

    def rehacer(self):
        """Ctrl+Y dentro del boceto: vuelve lo último que se deshizo (cualquier cambio nuevo vacía la pila)."""
        if not self.pila_rehacer:
            return
        self.historial.append(self.b.a_dict())
        self._restaurar(self.pila_rehacer.pop())
        self._tras_deshacer()

    def _quitar_proyecciones(self, n):
        """B-256: saca las últimas `n` proyecciones de la Curva de fusión sin dejarlas para rehacer (no se completó)."""
        for _ in range(n):
            self._restaurar(self.historial.pop())
        self._proy_fusion = 0
        self.resolver()
        self._emitir_proyeccion()

    def _tras_deshacer(self):
        self._proy_fusion = 0
        self._recorte_arrastre = None
        elegidos = [i for i in self.objetos.seleccion() if i in self.b.objetos]
        self.objetos.cancelar()
        self.seleccion, self.clics, self.picks, self.picks_xy = elegidos, [], [], []
        self.perfiles_sel = []
        self.inf_actual = self.inferencia = self._inf_inicio = None
        self._reiniciar_vivo()
        self.resolver()
        self._emitir_proyeccion()

    def evaluar(self, expr, tipo=LONGITUD, estricto=False):
        """Evalúa contra el documento. Una cota nombrada al citarla todavía no está en su tabla (entra al terminar el
        boceto): se cita por su valor, y una referencia circular entre ellas es un error de expresión. `estricto`: lo
        que se acaba de teclear; además exige la magnitud del campo."""
        usadas = nombres_usados(expr) & self._nombradas.keys() if isinstance(expr, str) else set()
        for nombre in usadas:
            cota = self.b.cotas.get(self._nombradas[nombre])
            if cota is None:
                continue
            if nombre in self._evaluando:
                raise ErrorExpresion(f"Referencia circular: la cota {nombre} depende de sí misma.")
            self._evaluando.add(nombre)
            try:
                valor = self.evaluar(cota.expresion, _tipo_valor(cota.tipo))
            finally:
                self._evaluando.discard(nombre)
            unidad = "deg" if cota.tipo == "angulo" else "mm"
            expr = re.sub(rf"\b{re.escape(nombre)}\b", f"({valor!r} {unidad})", expr)
        return self._evaluar_doc(expr, tipo, True) if estricto else self._evaluar_doc(expr, tipo)

    def valores_cotas(self):
        return {c.id: self.evaluar(c.expresion, _tipo_valor(c.tipo)) for c in self.b.cotas.values()}

    def resolver(self, arrastrado=None, rapido=False):
        """`rapido` (arrastrar un punto): solo se resuelve la parte de ese punto y sin recontar grados de libertad;
        al soltar se resuelve todo."""
        try:
            self.b.evaluar_patrones(self.evaluar)
            valores = self.valores_cotas()
        except (ErrorExpresion, ErrorBoceto) as e:
            self.mensaje.emit(f"Hay una cota o patrón con expresión inválida: {e}")
            valores = {}
        previo = self.resultado if rapido and arrastrado is not None else None
        self.resultado = resolver(self.b, valores, arrastrado, previo)
        r_uso = _ru.activo
        if r_uso is not None and time.monotonic() - getattr(self, "_uso_solver", 0.0) >= 0.5:
            self._uso_solver = time.monotonic()
            r_uso.emitir("boceto_solver", {"estado": self.resultado.estado, "gdl": self.resultado.gdl})
        self._cache_cortes = {}
        self._indice_inf = None
        if arrastrado is None:
            self._generacion += 1
            self._diagnostico_agotado = False
            self._conflictos = [] if self.resultado.ok else None      # None: se diagnostica en otro hilo al pintar
            self.cambio.emit()
            self._notificar_seleccion()
        self.update()
        return self.resultado

    def _valores_para_diagnostico(self):
        try:
            return self.valores_cotas()
        except ErrorExpresion:
            return {}

    def _sondear_conflictos(self):
        generacion, caja = self._diagnostico
        if not caja.get("listo"):
            self._t_diagnostico.start(40)
            return
        self._diagnostico = None
        if "error" in caja:
            raise caja["error"]
        if generacion != self._generacion:
            if self._conflictos is None:
                self.conflictos_sin_esperar()           # el boceto cambió mientras tanto: diagnosticar el nuevo estado
            return
        self._diagnostico_agotado = caja["res"] is None     # pasó el tope de tiempo: no se sabe cuál vínculo sobra
        self._conflictos = caja["res"] or []
        self.cambio.emit()
        self.update()
        if self._mostrar_conflictos_al_llegar:
            self._mostrar_conflictos_al_llegar = False
            self.mensaje.emit(self.texto_conflictos() or "No hay restricciones ni cotas en conflicto.")

    def geometria_en_conflicto(self, esperar=True):
        """Puntos y curvas que tocan las restricciones/cotas en conflicto (se dibujan en rojo)."""
        vinculos = {**self.b.restricciones, **self.b.cotas}
        ids = self.conflictos if esperar else self.conflictos_sin_esperar()
        return {e for i in ids if i in vinculos for e in vinculos[i].entidades}

    def texto_conflictos(self, esperar=False):
        """Qué choca, en palabras: «cota d3 = 30, horizontal (5)»; vacío si el boceto está bien. Mientras el diagnóstico
        se calcula (otro hilo) todavía no nombra nada; `esperar=True` lo espera."""
        if self.resultado is None or self.resultado.ok:
            return ""
        ids = self.conflictos if esperar else self.conflictos_sin_esperar()
        if self._conflictos is None:
            return ""
        if self._diagnostico_agotado:
            return "Hay restricciones en conflicto; el boceto es grande y no se pudo ver cuál sobra."
        nombres = []
        for i in ids:
            if i in self.b.cotas:
                k = self.b.cotas[i]
                nombres.append(f"cota {k.nombre or TIPOS_COTA[k.tipo].lower()} = {k.expresion}")
            elif i in self.b.restricciones:
                nombres.append(f"{TIPOS_RESTRICCION[self.b.restricciones[i].tipo].lower()} ({i})")
        if not nombres:
            return "No hay un solo vínculo que sobre: hay que quitar o cambiar varios."
        return f"Chocan: {', '.join(nombres)}. Quitá o cambiá uno para resolverlo."

    def mostrar_conflictos(self):
        """F5 «Qué choca»: lista las restricciones y cotas en conflicto (ya pintadas en rojo)."""
        if self.resultado is not None and not self.resultado.ok and not self.conflictos_sin_esperar() \
                and self._conflictos is None:
            self._mostrar_conflictos_al_llegar = True       # el diagnóstico corre en otro hilo: el mensaje sale al llegar
            texto = "Calculando qué choca…"
            self.mensaje.emit(texto)
            return texto
        texto = self.texto_conflictos() or self.texto_redundantes() or "No hay restricciones ni cotas en conflicto."
        self.mensaje.emit(texto)
        self.update()
        return texto

    def texto_redundantes(self):
        """Boceto bien resuelto pero sobre-definido (no hay contradicción): cuáles restricciones y cotas no quitan ningún
        grado de libertad. Las deja elegidas: Supr las borra. Vacío si no sobra ninguna. Se calcula al pedirlo (F5): son
        varios cálculos de rango, demasiados para correrlos en cada cambio."""
        if self.resultado is None or not self.resultado.ok:
            return ""
        sobran = restricciones_redundantes(self.b, self._valores_para_diagnostico())
        if sobran is None:
            return "El boceto tiene demasiadas restricciones y cotas para ver cuáles sobran."
        if not sobran:
            return ""
        nombres = [f"cota {self.b.cotas[i].nombre or TIPOS_COTA[self.b.cotas[i].tipo].lower()}" if i in self.b.cotas
                   else f"{TIPOS_RESTRICCION[self.b.restricciones[i].tipo].lower()} ({i})" for i in sobran]
        self.seleccion = list(sobran)
        self._notificar_seleccion()
        return (f"Sobra (no quita ningún grado de libertad): {', '.join(nombres)}. Quedó elegida: Supr la borra, "
                "y el boceto se mantiene igual.")

    def subrestringidas(self):
        """Buscar subrestringidos (Fusion: Find Under-Constrained): [(id, texto)] de la geometría que todavía se puede
        mover, o sea la que el solver no marca como determinada ni fija. Vacío si está todo restringido o el solver
        no resolvió."""
        r = self.resultado
        if r is None or not r.ok:
            return []
        salida = [(c.id, f"{NOMBRES_ENTIDAD.get(c.tipo, c.tipo)} {c.id}")
                  for c in self.b.curvas.values() if c.id not in r.determinadas]
        salida += [(p.id, f"punto {p.id}") for p in self.b.puntos.values() if p.id not in r.determinadas]
        return salida

    def resaltar(self, ids):
        """Deja elegido `ids` y lleva la vista ahí (una fila de Buscar subrestringidos)."""
        self.seleccion = list(ids)
        self._notificar_seleccion()
        self.encuadrar(ids)
        self.update()

    def borrar_ids(self, ids):
        """Borra `ids` en un solo paso de deshacer (la ✕ de una fila de Buscar subrestringidos)."""
        self.seleccion = list(ids)
        self.borrar_seleccion()
        self.update()

    def aplicar_cambio(self, funcion, operacion=False, anclar=True):
        """Aplica una modificación. Si deja en conflicto un boceto que estaba bien, se deshace sola.
        Lo que crean las herramientas de dibujo toma el tipo de línea elegido (normal / línea central).
        Con `operacion` (empalme, chaflán, recortar…), si se perdieron restricciones o cotas se avisa
        como Fusion."""
        estaba_ok = self.resultado is None or self.resultado.ok
        foto_uso = _foto_uso(self)
        antes = set(self.b.curvas)
        puntos_antes = set(self.b.puntos)
        vinculos = set(self.b.restricciones) | set(self.b.cotas)
        self._instantanea()
        try:
            funcion()
            if self._post_crear is not None:        # cotas de lo escrito en las cajas de valor
                self._post_crear(sorted(set(self.b.curvas) - antes))
            if anclar and self.herramienta not in MODIFICAN:
                self._anclar_al_origen(set(self.b.puntos) - puntos_antes)
        except (ErrorBoceto, ErrorExpresion) as e:
            self._restaurar(self.historial.pop())
            self.mensaje.emit(str(e))
            self.update()
            return False
        if anclar and self.herramienta not in MODIFICAN + ("linea", "texto") and set(self.b.puntos) - puntos_antes:
            self._restringir_clics(set(self.b.puntos) - puntos_antes, set(self.b.curvas) - antes)
        if anclar and self.eje and self.herramienta not in MODIFICAN:
            for cid in set(self.b.curvas) - antes:
                c = self.b.curvas[cid]
                if not c.construccion and not isinstance(c, Texto):
                    c.eje = True
        r = self.resolver()
        if estaba_ok and not r.ok:
            self._restaurar(self.historial.pop())
            self.resolver()
            self.mensaje.emit("Eso entra en conflicto con las restricciones que ya había (sobre-restringe): se deshizo.")
            return False
        self.pila_rehacer.clear()
        self.perfiles_sel = []                     # los índices de perfil dejan de valer al cambiar el boceto
        if foto_uso is not None:
            _diff_uso(self, foto_uso)
        if operacion and not vinculos <= (set(self.b.restricciones) | set(self.b.cotas)):
            self.aviso.emit(AVISO_BORRADAS)
        return True

    def _anclar_al_origen(self, puntos_nuevos):
        """Anclaje compartido con los rectángulos de la API."""
        return self.b.anclar_al_origen(puntos_nuevos)

    def _polilineas(self, c, pasos=64):
        """Polilíneas (u, v) de una curva (un texto da una por contorno). Con caché por primitiva: con miles de
        curvas, muestrear las splines en cada cuadro tardaba ~1 s y trababa el zoom y el paneo."""
        if isinstance(c, Texto) and c.parametro_texto:
            from ..timeline.operaciones import _contenido_texto, texto_con_valores
            valores = self.valores_parametros()
            if c.parametro_texto in valores:
                c = copy.copy(c)
                c.texto = texto_con_valores(_contenido_texto(c, valores), valores)
                from ..restricciones import objetos
                prims = primitivas_entidad(c, self.b.coords, curvas=self.b.curvas)
                return [_muestras(p, pasos) for p in objetos.aplicar_a_primitivas(self.b, c.id, prims)]
        if isinstance(c, Spline) and c.modo == "ajuste" and not self.b.objetos:
            # RS-X3: interpolar una spline de ajuste cuesta ~25 µs y se hacía en cada cuadro; la clave es todo lo que la
            # define (`primitivas_entidad`): sus puntos, grado, cierre y manijas (punta y curvatura)
            P = self.b.coords
            clave = (c.grado, c.cerrada, tuple(P(q) for q in c.pts), tuple((a, P(b), k) for a, b, k in c.manijas))
            hecho = self._cache_splines.get(c.id)
            if hecho is None or hecho[0] != clave:
                hecho = self._cache_splines[c.id] = (clave, self.b.primitivas(c.id))
            return [_muestras(p, pasos) for p in hecho[1]]
        return [_muestras(p, pasos) for p in self.b.primitivas(c.id)]

    def geometria_real(self):
        """`Boceto.geometria()` con el contenido de los textos ligados a un parámetro, no el «{Text}» que guardan."""
        from ..timeline.operaciones import _contenido_texto, texto_con_valores
        valores = self.valores_parametros()
        ligados = [(c, c.texto) for c in self.b.curvas.values() if isinstance(c, Texto) and c.parametro_texto in valores]
        try:
            for c, _texto in ligados:
                try:
                    c.texto = texto_con_valores(_contenido_texto(c, valores), valores)
                except ErrorExpresion:       # un {nombre} que no existe: el paso lo avisa; los demás perfiles siguen
                    pass
            return self.b.geometria()
        finally:
            for c, texto in ligados:
                c.texto = texto

    def _firma_camara(self):
        """Lo que define el paso de coordenadas del boceto a píxeles: si no cambia, lo proyectado sigue valiendo."""
        if self.visor is None:
            return (self.escala, self.centro[0], self.centro[1], self.width(), self.height())
        if self._mvp is None:
            self._camara()
        return (self._mvp.tobytes(), self.visor.width(), self.visor.height())

    def _poli_px(self, puntos):
        # Con la cámara quieta (repintar por el hover, una selección…) se reusa lo proyectado. Solo se guardan las
        # tuplas (las muestras cacheadas de `_muestras`, que no cambian); la entrada retiene la tupla: su id no se recicla.
        firma = self._firma_camara()
        if firma != getattr(self, "_firma_px", None):
            self._firma_px, self._cache_px = firma, {}
        hecho = self._cache_px.get(id(puntos))
        if hecho is not None and hecho[0] is puntos:
            return hecho[1]
        if self.visor is None:               # boceto 2D: la cuenta de a_px en línea (se hace miles de veces)
            s, cx, cy = self.escala, self.centro[0], self.centro[1]
            w2, h2 = self.width() / 2, self.height() / 2
            poli = [QPointF((x - cx) * s + w2, h2 - (y - cy) * s) for x, y in puntos]
        else:
            x, y = self._uv_px(np.asarray(puntos, dtype=float).reshape(-1, 2))
            poli = [QPointF(a, b) for a, b in zip(x.tolist(), y.tolist(), strict=True)]
        if isinstance(puntos, tuple):
            if len(self._cache_px) > 20000:
                self._cache_px.clear()
            self._cache_px[id(puntos)] = (puntos, poli)
        return poli

    def _visible(self, c):
        return not ((c.construccion and not self.mostrar["construccion"])
                    or (c.proyectada and not self.mostrar["proyectadas"]) or c.id in self.copias_en_edicion
                    or self.b.objetos and _suelta_aislada(self.b, c.id)
                    or self.b.props_curvas.get(c.id, {}).get("visible", True) is False)     # H-69: curva oculta

    def _ocultos(self):
        """(curvas, puntos) que no se ven —construcción o proyectadas apagadas, o las copias de un patrón que se
        edita (BOC-60)—: tampoco se pueden capturar."""
        if self.mostrar["construccion"] and self.mostrar["proyectadas"] and not self.copias_en_edicion and not self.b.objetos \
                and not self.b.props_curvas:
            return frozenset(), frozenset()
        curvas = {c.id: c for c in self.b.curvas.values() if not self._visible(c)}
        vistos = {p for c in self.b.curvas.values() if c.id not in curvas for p in c.puntos()}
        ocultos = {p for c in curvas.values() for p in c.puntos()}
        ocultos |= {p.id for p in self.b.puntos.values() if p.proyectado and not self.mostrar["proyectadas"]}
        ocultos |= {i for i in self.copias_en_edicion if i in self.b.puntos}
        ocultos.discard(Boceto.ORIGEN)  # la referencia del origen se sigue dibujando con esas capas apagadas
        if self.b.objetos:
            from ..restricciones import objetos
            internos = {p for cid in objetos.indice(self.b) for p in self.b.curvas[cid].puntos()}
            return frozenset(curvas), frozenset(ocultos - vistos | internos)
        return frozenset(curvas), frozenset(ocultos - vistos)

    def _clave_geometria(self):
        """Cambia cada vez que se resuelve el boceto o crece: las cachés de ayudas de dibujo se rearman solas."""
        return id(self.resultado), len(self.b.puntos), len(self.b.curvas)

    def _puntos_en_px(self):
        """(ids, x, y): todos los puntos del boceto en píxeles con un solo producto de matrices (un `a_px` por punto
        costaba 20 ms por movimiento del ratón con 3000 líneas)."""
        clave = self._clave_geometria()
        if self._puntos_np is None or self._puntos_np[0] != clave:
            xy = np.array([(p.x, p.y) for p in self.b.puntos.values()], dtype=float).reshape(-1, 2)
            # se guarda también el resultado: mientras viva, su id no lo puede reusar otro (la clave lo usa)
            self._puntos_np = (clave, np.array(list(self.b.puntos), dtype=int), xy, self.resultado)
        _, ids, uv, _resultado = self._puntos_np
        return (ids, *self._uv_px(uv))

    def _uv_px(self, uv):
        """(x, y) en píxeles de un array (n, 2) de coordenadas del boceto, en bloque: como `a_px` con un solo producto de
        matrices (punto a punto: 5 µs por punto). Lo que queda detrás de la cámara va a -1e5."""
        if self.visor is None:
            return ((uv[:, 0] - self.centro[0]) * self.escala + self.width() / 2,
                    self.height() / 2 - (uv[:, 1] - self.centro[1]) * self.escala)
        if self._mvp is None:
            self._camara()
        pl = self.plano
        c = np.hstack([pl.origen + uv[:, :1] * pl.u + uv[:, 1:] * pl.v, np.ones((len(uv), 1))]) @ self._mvp.T
        w = c[:, 3]
        delante = w > 1e-9
        w = np.where(delante, w, 1.0)
        return (np.where(delante, (c[:, 0] / w + 1) / 2 * self.visor.width(), -1e5),
                np.where(delante, (1 - c[:, 1] / w) / 2 * self.visor.height(), -1e5))

    def _segmentos_uv(self):
        """(ids de curva, a, b): los segmentos de las polilíneas de todas las curvas menos los textos, en coordenadas del
        boceto, con caché por geometría (RS-X3: el hover los mide todos juntos con numpy)."""
        clave = self._clave_geometria()
        if getattr(self, "_segs_uv", None) is None or self._segs_uv[0] != clave:
            ids, a, b = [np.zeros(0, int)], [np.zeros((0, 2))], [np.zeros((0, 2))]
            for c in self.b.curvas.values():
                if isinstance(c, Texto):
                    continue
                for poli in self._polilineas(c, 48):
                    q = np.asarray(poli, dtype=float).reshape(-1, 2)
                    ids.append(np.full(max(len(q) - 1, 0), c.id))
                    a.append(q[:-1])
                    b.append(q[1:])
            self._segs_uv = (clave, np.concatenate(ids), np.concatenate(a), np.concatenate(b), self.resultado)  # ver _puntos_np
        return self._segs_uv[1:4]

    def _punto_cercano(self, pos, excluir=None, radio_px=TOL_PUNTO):
        ids, x, y = self._puntos_en_px()
        if not len(ids):
            return None
        d = np.hypot(x - pos.x(), y - pos.y())
        if excluir is not None:
            d[ids == excluir] = np.inf
        ocultos = self._ocultos()[1]
        if ocultos:
            d[np.isin(ids, list(ocultos))] = np.inf
        i = int(np.argmin(d))
        return int(ids[i]) if d[i] < radio_px else None

    def _curva_cercana(self, pos, radio_px=6.0, tipos=None, interior=False):
        mejor, dmin = None, radio_px
        validas = [c for c in self.b.curvas.values() if self._visible(c) and not (tipos and c.tipo not in tipos)]
        if self.b.objetos and tipos != ("texto",):
            from ..restricciones import objetos
            dentro = objetos.indice(self.b)
            validas = [c for c in validas if isinstance(c, Texto) or c.id not in dentro]
        ids, a, b = self._segmentos_uv()        # RS-X3: la distancia a todos los segmentos de una vez (no los textos)
        if len(ids):
            (ax, ay), (bx, by) = self._uv_px(a), self._uv_px(b)
            dx, dy, px, py = bx - ax, by - ay, pos.x(), pos.y()
            L2 = np.maximum(dx * dx + dy * dy, 1e-18)
            t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
            d = np.hypot(px - ax - t * dx, py - ay - t * dy)
            d[~np.isin(ids, [c.id for c in validas if not isinstance(c, Texto)])] = np.inf
            i = int(np.argmin(d))
            if d[i] < dmin:
                mejor, dmin = int(ids[i]), float(d[i])
        for c in validas:
            if interior and isinstance(c, Circulo) and radio_px * 0.8 < dmin:
                # círculo chico (un agujero): también se agarra desde adentro, cediendo ante lo que esté más cerca
                centro = self.a_px(*self.b.coords(c.centro))
                r_px = self.b.radio(c.id) * self.px_por_mm()
                if r_px <= RADIO_INTERIOR_PX and math.hypot(pos.x() - centro.x(), pos.y() - centro.y()) <= r_px:
                    mejor, dmin = c.id, radio_px * 0.8
            if not isinstance(c, Texto):
                continue
            xs, ys = [], []
            for poli in self._polilineas(c, 48):
                px = self._poli_px(poli)
                d = min(_dist_px(pos, a, b) for a, b in zip(px, px[1:], strict=False))
                if d < dmin:
                    mejor, dmin = c.id, d
                xs += [q.x() for q in px]
                ys += [q.y() for q in px]
            if xs and min(xs) - radio_px <= pos.x() <= max(xs) + radio_px                     and min(ys) - radio_px <= pos.y() <= max(ys) + radio_px and radio_px * 0.9 < dmin:
                mejor, dmin = c.id, radio_px * 0.9      # dentro de la caja del texto: cede ante lo que esté más cerca
            if xs and min(xs) <= pos.x() <= max(xs) and min(ys) <= pos.y() <= max(ys):
                # clic sobre la tinta de una letra: el texto gana (B-187), aunque la curva de abajo cruce la letra
                cruces = 0
                for poli in self._polilineas(c, 48):
                    px = self._poli_px(poli)
                    for a, b in zip(px, px[1:], strict=False):
                        if (a.y() > pos.y()) != (b.y() > pos.y()) and pos.x() < a.x() + (pos.y() - a.y()) * (b.x() - a.x()) / (b.y() - a.y()):
                            cruces += 1
                if cruces % 2 == 1:
                    mejor, dmin = c.id, -1.0

        return mejor

    def entidad_en(self, pos):
        if self.herramienta == "seleccionar":
            if self.objetos.modo_perfiles:
                return None
            oid = self.objetos.en(pos)
            if oid is not None:
                return oid
        # El origen se dibuja aunque todavía no lo haya citado ninguna restricción o cota.
        origen = self.a_px(0, 0)
        if math.hypot(pos.x() - origen.x(), pos.y() - origen.y()) < TOL_PUNTO:
            self.b.asegurar_referencias([Boceto.ORIGEN])
        pid = self._punto_cercano(pos)
        return pid if pid is not None else self._curva_cercana(pos, interior=True)

    def _plano_perfiles(self):
        from ..nucleo import geometria as geo
        return self.plano if self.plano is not None else geo.Plano("XY")

    def _perfiles(self):
        """Perfiles del boceto en el orden de `detectar_boceto` (el mismo índice que `profile` en la API). Con caché por
        geometría en el núcleo: repetir la consulta sin cambios no vuelve a partir caras."""
        from ..nucleo.perfiles import detectar_boceto
        try:
            return detectar_boceto(self.b, self._plano_perfiles(), self.geometria_real())
        except Exception:  # noqa: BLE001 — un boceto a medio dibujar no debe romper la selección
            return []

    def perfil_en(self, pos):
        """Índice del perfil (región cerrada) bajo `pos`, o None. Si hay varios (una letra sobre un disco), el más chico."""
        from .manipuladores import punto_en_cara
        p3 = self._plano_perfiles().a_3d(*self.a_mm(pos))
        dentro = [(p.area, i) for i, p in enumerate(self._perfiles()) if punto_en_cara(p.cara, p3, 1e-7)]
        return min(dentro)[1] if dentro else None

    def perfiles_seleccionados(self):
        """Perfiles elegidos con clic en el editor (objetos `Perfil` del núcleo: cara, área, centroide, firma)."""
        todos = self._perfiles()
        return [todos[i] for i in self.perfiles_sel if i < len(todos)]

    def _clic_perfil(self, pos):
        if self.herramienta != "seleccionar":
            return
        if self.b.objetos and not self.objetos.modo_perfiles and any(
                camino.boundingRect().contains(pos) for camino, _borde in self.objetos._datos().values()):
            return  # el vacío entre trazos de un recurso no cambia implícitamente a selección CAD
        i = self.perfil_en(pos)
        if i is None:
            return
        if i in self.perfiles_sel:            # con Ctrl o Mayús, un segundo clic lo quita
            self.perfiles_sel.remove(i)
        else:
            self.perfiles_sel.append(i)
        self._notificar_seleccion()
        self.update()

    def _base_inferencia(self):
        """Desde dónde se mide el segmento en curso (la última pulsación), o None si la herramienta no tiene base."""
        return self.clics[-1][1] if self.clics and self.herramienta not in ("circulo_3p",) else None

    def _inferir(self, xy, base, excluidos, previa):
        """Ayudas bajo el cursor según los ajustes. Con una bloqueada (Flecha arriba), el cursor sigue su guía."""
        a = self.ajustes_inf
        if self._inf_bloqueo is not None and len(self.clics) != self._inf_bloqueo_clics:
            self._inf_bloqueo = None
        if self._inf_bloqueo is not None:
            self.inf_lista = [proyectar_bloqueo(self._inf_bloqueo, xy)]
            return self.inf_lista[0]
        if self._indice_inf is None or self._indice_inf.b is not self.b or self._indice_clave != self._clave_geometria():
            self._indice_inf, self._indice_clave = Indice(self.b, self._indice_inf), self._clave_geometria()
        # Paralela/perpendicular/colineal e igual mueven el punto sobre un rayo desde la base: valen para el segmento de
        # una Línea (BOC-48: también el de la línea de punto medio y el primer lado del rectángulo 3p, donde no
        # deforman nada). Igual compara el largo con otras líneas, o el radio de un círculo o arco con centro.
        # (BOC-33) Con la base en el centro de un círculo o arco, el cursor fija el radio.
        h, n = self.herramienta, len(self.clics)
        centro = h in ("circulo", "arco_centro") and n == 1
        quitar = []
        if not (h == "linea" or (h in ("linea_medio", "rectangulo_3p") and n == 1)):
            quitar.append("paralela")
        if not (h == "linea" or centro):
            quitar.append("igual")
        tipos = tuple(t for t in a["tipos"] if t not in quitar)
        # Alternar con Espacio elige una de las ambiguas: sin histéresis, o la activa volvería siempre al primer lugar.
        lista = inferencias(self.b, xy, a["sensibilidad_px"] / self.px_por_mm(), base=base, excluir=excluidos,
                            coincidente=bool(self._modificadores_raton & Qt.ShiftModifier),
                            angulo_tol=TOL_INFERENCIA, previa=None if self._inf_alt else previa, tipos=tipos,
                            indice=self._indice_inf, extra=[c[1] for c in self.clics[:-1]], centro=centro)
        claves = [i.clave() for i in lista]
        if claves != self._inf_claves:
            self._inf_alt, self._inf_claves = 0, claves
        self.inf_lista = lista
        return lista[self._inf_alt % len(lista)] if lista else None

    def _ajustar(self, pos, excluir=None, base=None):
        """Punto existente y origen primero; después ajustes a objetos, alineaciones, H/V y rejilla."""
        previa = self.inf_actual
        self.inf_actual = self.inferencia = None
        self.inf_lista = []
        pid = self._punto_cercano(pos, excluir)
        if pid is not None:
            xy = self.b.coords(pid)
            if (self.herramienta == "linea" and base is not None and self.ajustes_inf["inferencias"]
                    and self.ajustes_inf["restricciones_auto"]
                    and not self._modificadores_raton & Qt.ControlModifier):
                # B-539: al cerrar en un punto que ya existe, Fusion también pone la perpendicular (o la paralela)
                excluidos = [*self._ocultos()[0], self._ultima_linea]
                self._inferir(xy, base, excluidos, previa)
                self.inf_actual = next((replace(i, restriccion=i.restriccion[:2]) for i in self.inf_lista
                                        if i.tipo in ("perpendicular", "paralela")), None)
                self.inf_lista = [self.inf_actual] if self.inf_actual else []
            return pid, xy
        o = self.a_px(0.0, 0.0)
        if math.hypot(o.x() - pos.x(), o.y() - pos.y()) < TOL_PX:
            return None, (0.0, 0.0)                     # el origen del boceto también engancha
        x, y = self.a_mm(pos)
        excluidos = [excluir] if excluir is not None else []
        excluidos += self._ocultos()[0]
        if self.herramienta == "linea" and self.clics and self._ultima_linea is not None:
            excluidos.append(self._ultima_linea)
        # Ctrl mantenido apaga las ayudas un momento (como Fusion); en Seleccionar solo ayudan al arrastrar; al elegir
        # geometría o el eje (Simetría, Empalme…) no hay punto que ajustar, solo qué tocar.
        ayuda = (self.ajustes_inf["inferencias"] and not self._modificadores_raton & Qt.ControlModifier
                 and self.fase not in ("seleccion", "eje") and self.herramienta not in PICKS
                 and (self.herramienta != "seleccionar" or self._arrastre is not None))
        if ayuda:
            self.inf_actual = self._inferir((x, y), base, excluidos, previa)
        if self.inf_actual is not None:
            if not self.ajustes_inf["restricciones_auto"]:
                self.inf_actual = replace(self.inf_actual, restriccion=None)
            elif self.inf_actual.restriccion in (("horizontal",), ("vertical",)):
                self.inferencia = self.inf_actual.tipo
            return None, self.inf_actual.xy
        if self.ajustar_grilla:
            s = self.paso_grilla()
            x, y = round(x / s) * s, round(y / s) * s
        return None, (x, y)
