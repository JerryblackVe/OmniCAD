"""LienzoRestriccionesMixin: métodos del lienzo por tema."""

from .editor_boceto_comun import (
    ErrorBoceto,
    PORTAPAPELES,
    RESTRICCIONES_HERRAMIENTA,
    TIPOS_COTA,
    TIPOS_RESTRICCION,
    _registro_uso,
    _tipo_valor,
    acomodar_segunda,
    acomodar_tangente,
    aviso_tangencias_fuera,
    grados_de_libertad,
    resolver,
    restriccion_quita_grados,
    separar_nombre,
    validar_valor_cota,
)


def QMenu(*args, **kwargs):
    from . import editor_boceto
    return editor_boceto.QMenu(*args, **kwargs)


class LienzoRestriccionesMixin:
    def _menu_restriccion(self, rid):
        """Clic derecho en el símbolo de una restricción (Fusion): elegir la geometría que restringe o borrarla."""
        r = self.b.restricciones[rid]
        m = QMenu(self)
        m.addAction("Seleccionar la geometría restringida", lambda: self._elegir_entidades(r.entidades))
        otros = self.b.tipos_compatibles(rid)
        if otros:                     # una restricción no tiene valores que editar: se cambia por otra sobre lo mismo
            sub = m.addMenu("Cambiar por")
            for tipo in otros:
                sub.addAction(TIPOS_RESTRICCION[tipo], lambda t=tipo: self.reemplazar_restriccion(rid, t))
        m.addSeparator()
        m.addAction(f"Borrar restricción {TIPOS_RESTRICCION[r.tipo].lower()}", lambda: self.borrar_restriccion(rid))
        return m

    def _elegir_entidades(self, ids):
        self.seleccion = [i for i in ids if i in self.b.puntos or i in self.b.curvas]
        self._notificar_seleccion()
        self.update()

    def reemplazar_restriccion(self, rid, tipo):
        """Cambia una restricción por otra sobre las mismas entidades, en un solo paso; si choca con las demás, no cambia."""
        r = self.b.restricciones.get(rid)
        if r is None:
            return False
        antes = TIPOS_RESTRICCION[r.tipo].lower()
        if self.resultado is None or self.resultado.ok:       # BOC-53: una restricción que sobra se rechaza, como en Agregar
            copia = self.b.copia()
            try:
                copia.reemplazar_restriccion(rid, tipo)
                valores = self.valores_cotas()
                sobra = resolver(copia, valores).ok and not restriccion_quita_grados(copia, rid, valores)
            except ErrorBoceto:
                sobra = False                                # no aplica: lo dice `aplicar_cambio`
            if sobra:
                self.mensaje.emit(f"«{TIPOS_RESTRICCION[tipo]}» no quita ningún grado de libertad: el boceto ya la cumple "
                                  "por otras restricciones o cotas. No se cambió.")
                return False
        def cambiar():
            if tipo == "perpendicular":
                self.b.girar_a_perpendicular(*r.entidades)       # B-586: sin esto el solver deformaba la spline
            self.b.reemplazar_restriccion(rid, tipo)
            if tipo == "tangente":
                acomodar_tangente(self.b, r.entidades, self._valores_para_diagnostico())
        if not self.aplicar_cambio(cambiar):
            return False
        self.mensaje.emit(f"Restricción cambiada: {antes} → {TIPOS_RESTRICCION[tipo].lower()}.")
        return True

    def borrar_restriccion(self, rid):
        """Quita una restricción sola: la geometría y las demás restricciones quedan como estaban."""
        r = self.b.restricciones.get(rid)
        if r is None:
            return False
        self.seleccion = [i for i in self.seleccion if i != rid]
        if not self.aplicar_cambio(lambda: self.b.eliminar(rid)):
            return False
        self.mensaje.emit(f"Restricción borrada: {TIPOS_RESTRICCION[r.tipo].lower()}.")
        self._notificar_seleccion()
        return True

    def editar_cota(self, cid, pos):
        cota = self.b.cotas[cid]
        if cota.referencia:
            self.mensaje.emit("Es una cota de referencia: mide la geometría. Mayús + doble clic la vuelve driving.")
            return

        def aceptar(v):
            nombre, texto = separar_nombre(v[0])
            self._comprobar_nombre_cota(nombre, cota)
            validar_valor_cota(cota.tipo, self.evaluar(texto, _tipo_valor(cota.tipo), estricto=True))

            def cambiar():
                cota.expresion = texto
                _registro_uso("boceto_cota", {"accion": "editada", "tipo": cota.tipo, "valor": texto})
                if nombre:
                    cota.nombre, self._nombradas[nombre] = nombre, cota.id
            self.aplicar_cambio(cambiar)
        self._abrir_entrada([TIPOS_COTA[cota.tipo]], [cota.expresion], pos, aceptar)
        self._cota_editada = cid             # mientras se edita, la caja con borde reemplaza al texto
        zona = self._zonas_cotas.get(cid)
        if zona is not None:
            self.entrada.move(int(zona.left()) - 4, int(zona.top()) - 4)

    def aplicar_restriccion(self, tipo, ents):
        """Aplica una restricción a las entidades, en el orden en que se eligieron. Devuelve True si quedó."""
        grupos = None
        if tipo == "horizontal_vertical":
            lineas = [i for i in ents if self.b.tipo_de(i) == "linea"]
            if lineas:                    # cada línea elegida queda horizontal o vertical, la que le queda más cerca
                grupos = [[i] for i in lineas]
            elif len(ents) == 2 and all(self.b.tipo_de(i) == "punto" for i in ents):
                grupos = [list(ents)]
            else:
                self.mensaje.emit("Horizontal/Vertical: elegí una o más líneas, o dos puntos.")
                return False
            tipos = []
            for g in grupos:
                (x1, y1), (x2, y2) = (self.b._extremos_linea(g[0]) if len(g) == 1
                                      else (self.b.coords(g[0]), self.b.coords(g[1])))
                tipos.append("horizontal" if abs(x2 - x1) >= abs(y2 - y1) else "vertical")
            tipo = tipos[0]
            ents = grupos[0]
        elif tipo == "simetrica" and len(ents) == 3 and self.b.tipo_de(ents[-1]) != "linea":
            self.mensaje.emit("Simetría: elegí los dos elementos y después el eje (una línea).")
            return False
        elif tipo == "fijo":
            existente = [r.id for r in self.b.restricciones.values() if r.tipo == "fijo" and set(r.entidades) == set(ents)]
            if existente:
                return self.aplicar_cambio(lambda: self.b.eliminar(existente[0]))
        elif tipo == "poligono":
            if len(ents) == 1:            # un clic en un lado: se toma la cadena cerrada de líneas
                cadena, cerrada = self.b.cadena(ents[0])
                if not cerrada or any(self.b.tipo_de(k) != "linea" for k, _ in cadena):
                    self.mensaje.emit("Polígono: hacé clic en un lado de una cadena cerrada de líneas.")
                    return False
                ents = [k for k, _ in cadena]
        pedidos = [(tipo, ents)] if grupos is None else list(zip(tipos, grupos, strict=True))
        # los GDL de ANTES se cuentan ahora (no con `self.resultado`, que puede estar viejo si el boceto se tocó directo)
        gdl = (grados_de_libertad(self.b, self._valores_para_diagnostico())
               if self.resultado is not None and self.resultado.ok else None)

        def agregar():
            for t, e in pedidos:
                if t == "tangente":
                    self.b.deslizar_a_tangente(*e)
                elif t == "perpendicular":
                    self.b.girar_a_perpendicular(*e)           # B-586: línea–spline, como Fusion
                self.b.agregar_restriccion(t, e)
                if t in ("tangente", "curvatura"):
                    acomodar_tangente(self.b, e, self._valores_para_diagnostico())
                elif t in ("concentrica", "punto_medio", "igual"):
                    acomodar_segunda(self.b, e[0], self._valores_para_diagnostico())
        ok = self.aplicar_cambio(agregar)
        if ok and tipo != "fijo" and gdl is not None and self.resultado.gdl >= gdl:    # no quitó ningún GDL: sobra
            self._restaurar(self.historial.pop())
            self.resolver()
            self.mensaje.emit(f"{TIPOS_RESTRICCION.get(tipo, tipo)} no se agregó: el boceto ya la cumple por otras "
                              "restricciones o cotas (sobre-definiría).")
            return False
        if ok:
            fuera = self.b.tangencias_fuera_del_arco() if tipo == "tangente" else []
            self.mensaje.emit(aviso_tangencias_fuera() if fuera else f"Restricción agregada: {TIPOS_RESTRICCION.get(tipo, tipo)}.")
        return ok

    def _restriccion_con_seleccion(self):
        tipo, n = RESTRICCIONES_HERRAMIENTA[self.herramienta]
        ents = [i for i in self.seleccion if i in self.b.puntos or i in self.b.curvas]
        listo = (len(ents) == n
                 or (tipo == "horizontal_vertical" and (len(ents) == 2 or all(self.b.tipo_de(i) == "linea" for i in ents)))
                 or (tipo == "fijo" and len(ents) >= 1) or (tipo == "poligono" and len(ents) >= 3))
        if ents and listo:
            self.aplicar_restriccion(tipo, ents)
            self.seleccion = []
            self.update()
            return True
        return False

    def _clic_restriccion(self, pos):
        ent = self.entidad_en(pos)
        if ent is None:
            return
        tipo, n = RESTRICCIONES_HERRAMIENTA[self.herramienta]
        if ent in self.picks:
            return
        self.picks.append(ent)
        if tipo == "horizontal_vertical":
            if self.b.tipo_de(self.picks[0]) == "linea" or len(self.picks) == 2:
                self.aplicar_restriccion(tipo, list(self.picks))
                self.picks = []
        elif len(self.picks) >= n:
            self.aplicar_restriccion(tipo, list(self.picks))
            self.picks = []
        self.update()

    def borrar_seleccion(self):
        ids = [i for i in self.seleccion if i in self.b.puntos or i in self.b.curvas
               or i in self.b.restricciones or i in self.b.cotas or i in self.b.objetos]
        fijas = [i for i in ids if i <= 0]      # B-241: un recuadro que toma el origen o un eje no frena el resto
        ids = [i for i in ids if i > 0]
        if fijas:
            self.mensaje.emit("El origen y los ejes del boceto son referencias fijas: no se borran."
                              + (" Se borró el resto de la selección." if ids else ""))
        if not ids:
            return

        def borrar():
            for i in ids:
                if i in self.b.objetos:
                    from ..restricciones import objetos
                    if self.b.objetos[i]["bloqueado"]:
                        raise ErrorBoceto("Desbloqueá el objeto antes de borrarlo.")
                    for cid in objetos.curvas(self.b, [i]):
                        self.b.eliminar(cid)
                    continue
                if i in self.b.puntos or i in self.b.curvas or i in self.b.restricciones or i in self.b.cotas:
                    self.b.eliminar(i)
        self.aplicar_cambio(borrar)
        self.seleccion = []
        self._notificar_seleccion()

    def copiar_seleccion(self):
        """Ctrl+C: guarda la selección (con una copia del boceto) para pegarla en este u otro boceto."""
        ids = [i for i in self.seleccion if i > 0 and (i in self.b.puntos or i in self.b.curvas)]
        if ids:
            PORTAPAPELES.update(boceto=self.b.copia(), ids=ids)
            self.mensaje.emit(f"{len(ids)} elemento(s) copiado(s): Ctrl+V los pega.")

    def pegar(self):
        """Ctrl+V: pega lo copiado en el mismo lugar, como geometría normal, y lo deja seleccionado."""
        nuevos = []
        origen, ids = PORTAPAPELES["boceto"], PORTAPAPELES["ids"]
        if self.aplicar_cambio(lambda: nuevos.extend(self.b.pegar_de(origen, ids)), operacion=True, anclar=False):
            self.seleccion = nuevos
            self._notificar_seleccion()
            self.update()

    def alternar_construccion(self):
        curvas = [i for i in self.seleccion if i in self.b.curvas]
        if not curvas:
            self.construccion = not self.construccion
            if self.construccion:
                self.eje = False
            self.mensaje.emit("Las curvas nuevas son de construcción." if self.construccion
                              else "Las curvas nuevas son normales.")
            self._emitir_proyeccion()
            return

        def cambiar():
            for i in curvas:
                self.b.curvas[i].construccion = not self.b.curvas[i].construccion
                if self.b.curvas[i].construccion:
                    self.b.curvas[i].eje = False
        self.aplicar_cambio(cambiar)
