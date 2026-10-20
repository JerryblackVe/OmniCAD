# -*- coding: utf-8 -*-
"""INSERTAR › Insertar derivación: elegir un proyecto y los objetos que se vinculan a él."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QListWidget, QListWidgetItem, QPushButton

from ...io_archivos import proyecto
from ...timeline.operaciones import ErrorOperacion
from ...timeline.ops_derivacion import OpDerivacion, _abrir_origen
from ..comando import Comando, ErrorComando, Personalizado, Texto
from . import registrar


class InsertarDerivacion(Comando):
    CLAVE, TITULO, ICONO = "insertar_derivacion", "Insertar derivación", "derivar"
    CLASE_OP = OpDerivacion
    AYUDA = ("Vincula cuerpos, bocetos y parámetros de otro proyecto. Al recalcular vuelve a leer el origen; "
             "el archivo debe seguir disponible.")

    def campos(self, ctx):
        return [Texto("archivo", "Proyecto de origen"),
                Personalizado("examinar", "", self._boton_archivo),
                Personalizado("cuerpos", "Cuerpos", lambda p: self._lista(p, "cuerpos"), defecto=[]),
                Personalizado("bocetos", "Bocetos", lambda p: self._lista(p, "bocetos"), defecto=[]),
                Personalizado("parametros", "Parámetros", lambda p: self._lista(p, "parametros"), defecto=[])]

    def _lista(self, panel, clave):
        lista = QListWidget()
        lista.setMaximumHeight(95)
        lista.itemChanged.connect(lambda _item: panel._cambiar(
            clave, [lista.item(i).data(Qt.UserRole) for i in range(lista.count())
                    if lista.item(i).checkState() == Qt.Checked]))
        return lista

    def _boton_archivo(self, panel):
        boton = QPushButton("Elegir proyecto…")

        def elegir():
            ruta, _ = QFileDialog.getOpenFileName(panel, self.TITULO, panel.valores.get("archivo") or "",
                                                 "Proyecto OmniCAD (*.omnicad *.fclone)")
            if ruta:
                panel.set_valor("archivo", ruta)
                self._cargar(panel)
        boton.clicked.connect(elegir)
        return boton

    def preparar_panel(self, panel):
        panel.widgets["archivo"].editingFinished.connect(lambda: self._cargar(panel))
        self._ruta_cargada = panel.valores.get("archivo") or ""
        if self._ruta_cargada:
            self._cargar(panel)

    def _cargar(self, panel):
        ruta = (panel.valores.get("archivo") or "").strip()
        try:
            otro = _abrir_origen(ruta)
        except (ErrorOperacion, OSError, ValueError) as e:
            panel._mostrar(str(e))
            return
        opciones = {
            "cuerpos": [(cid, c.nombre) for cid, c in otro.estado_final.cuerpos.items()],
            "bocetos": [(bid, b.nombre) for bid, b in otro.estado_final.bocetos.items()],
            "parametros": [(p.nombre, p.nombre) for p in otro.parametros],
        }
        for clave, filas in opciones.items():
            elegidos = panel.valores.get(clave, []) if ruta == self._ruta_cargada else []
            lista = panel.widgets[clave]
            lista.blockSignals(True)
            lista.clear()
            for ident, nombre in filas:
                item = QListWidgetItem(f"{nombre} ({ident})" if ident != nombre else nombre, lista)
                item.setData(Qt.UserRole, ident)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if ident in elegidos or nombre in elegidos else Qt.Unchecked)
            lista.blockSignals(False)
            panel._cambiar(clave, [lista.item(i).data(Qt.UserRole) for i in range(lista.count())
                                  if lista.item(i).checkState() == Qt.Checked])
        self._ruta_cargada = ruta

    def construir(self, v, ctx):
        ruta = Path((v.get("archivo") or "").strip()).expanduser()
        if ruta.suffix.lower() not in proyecto.EXTENSIONES or not ruta.is_file():
            raise ErrorComando("Elegí un proyecto de origen .omnicad (o .fclone) existente.")
        if not any(v.get(k) for k in ("cuerpos", "bocetos", "parametros")):
            raise ErrorComando("Elegí al menos un cuerpo, boceto o parámetro del origen.")
        return self.crear_op(OpDerivacion, v, ctx, archivo=str(ruta.resolve()),
                             **{k: list(v.get(k) or []) for k in ("cuerpos", "bocetos", "parametros")})


registrar(InsertarDerivacion)
