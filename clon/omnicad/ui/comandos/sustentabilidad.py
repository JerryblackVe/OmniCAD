# -*- coding: utf-8 -*-
"""INSPECCIONAR › Sustainability Insights: el panel local de `nucleo/sustentabilidad.py`, con sus dos pestañas."""
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QWidget

from ...nucleo import geometria as geo
from ...nucleo import sustentabilidad as su
from ...timeline.operaciones import propiedades_cuerpo
from ...timeline.parametros import ESCALAR
from ..comando import Comando, ErrorComando, Expresion, Info, Opciones, OpcionesVivas, Personalizado, Seleccion, Texto
from . import registrar

_PESTANA = "Materiales personalizados"
_CLAVES = {"abs": "ABS", "asa": "ASA", "aluminio": "Aluminio", "cobre": "Cobre", "nylon": "Nylon", "ptfe": "PTFE", "pvc": "PVC",
           "policarbonato": "Policarbonato", "polietileno": "Polietileno", "polipropileno": "Polipropileno",
           "inoxidable": "Acero inoxidable", "acero": "Acero", "titanio": "Titanio"}
_NOTA = "Estimación local: masa × kg de CO₂e por kg del material. No cuenta la fabricación de la pieza ni usa internet."


class Sustentabilidad(Comando):
    CLAVE, TITULO, ICONO = "sustentabilidad", "Sustainability Insights", "sustentabilidad"
    AYUDA = "Estima el CO₂ de un cuerpo por su material, con el cálculo y la fuente a la vista. No usa internet."
    SIN_OP, TEXTO_ACEPTAR = True, "Cerrar"
    PESTANA_PRINCIPAL = "Percepciones"
    panel = None
    aviso = ""

    def campos(self, ctx):
        return [Seleccion("cuerpo", "Seleccionar cuerpo", {"cuerpo"}, minimo=0),
                Info("manufactura", "Tipo de manufactura", self._manufactura),
                Info("material_cuerpo", "Material del cuerpo", self._material_cuerpo),
                Opciones("material", "Material más cercano", {"": "Seleccione…", **_CLAVES, "personalizado": su.PERSONALIZADO}),
                OpcionesVivas("propio", "Material propio", self._propios, visible_si=lambda v: v.get("material") == "personalizado"),
                Opciones("sobrescritura", "Sobrescritura de volumen del stock",
                         {"no": "Sin sobrescritura", "manual": "Valores manuales", "cuerpo": "Seleccionar un cuerpo"}),
                Expresion("stock_volumen", "Volumen del stock", "1000", tipo=ESCALAR, ayuda="En mm³.",
                          visible_si=lambda v: v.get("sobrescritura") == "manual"),
                Seleccion("stock_cuerpo", "Cuerpo del stock", {"cuerpo"}, minimo=0, visible_si=lambda v: v.get("sobrescritura") == "cuerpo"),
                Opciones("region", "Región de manufactura", {"": "Seleccione…", **{r: r for r in su.REGIONES}}),
                OpcionesVivas("pais", "País de manufactura", lambda v: {p: p for p in su.REGIONES.get(v.get("region"), ())} or {"": "—"}),
                Info("resultado", "", self._resultado),
                Texto("nombre", "Nombre del material", pestana=_PESTANA),
                Expresion("co2", "CO2 por kg", "1.00", tipo=ESCALAR, pestana=_PESTANA),
                Expresion("densidad", "Densidad g/cm³", "1.00", tipo=ESCALAR, pestana=_PESTANA),
                Opciones("parecido", "Material más parecido", {"": "Ninguno", **_CLAVES}, pestana=_PESTANA),
                Info("info_material", "", lambda v, ctx: self.aviso or "Un factor propio se guarda en esta PC y sirve para todos los documentos.", pestana=_PESTANA),
                Personalizado("crear", "", self._boton_crear, pestana=_PESTANA),
                Personalizado("archivos", "", self._botones_archivo, ancho_completo=True, pestana=_PESTANA),
                OpcionesVivas("lista", "Materiales personalizados", self._propios, pestana=_PESTANA),
                Info("info_lista", "", self._info_lista, pestana=_PESTANA)]

    def _propios(self, v):
        return {n: n for n in su.materiales_propios()} or {"": "Sin materiales propios"}

    def preparar_panel(self, panel):
        self.panel = panel
        panel.boton_cancelar.hide()              # nada que descartar: Cerrar y Cancelar harían lo mismo
        panel.widgets["pais"].setEnabled(False)

    def al_cambiar(self, panel, clave):
        if clave == "region":
            panel.widgets["pais"].setEnabled(bool(panel.valores.get("region")))

    def _cuerpo(self, v, ctx):
        h = v.get("cuerpo") or []
        return ctx.estado.cuerpos[h[0]["ref"]["cuerpo"]] if h else None

    def _fisico(self, c, ctx):
        return propiedades_cuerpo(ctx.doc.propiedades, c).get("material") or getattr(c, "material", None)

    def _manufactura(self, v, ctx):
        c = self._cuerpo(v, ctx)
        return su.tipo_manufactura(c) if c else "Seleccione un cuerpo…"

    def _material_cuerpo(self, v, ctx):
        c = self._cuerpo(v, ctx)
        return (self._fisico(c, ctx) or "Sin material físico") if c else "No hay cuerpo seleccionado"

    def _material(self, v, c, ctx):
        elegido = v.get("material")
        if elegido == "personalizado":
            return v.get("propio") or ""
        return _CLAVES.get(elegido) or su.material_cercano(self._fisico(c, ctx))

    def _volumen(self, v, c, ctx):
        modo = v.get("sobrescritura")
        if modo == "manual":
            return ctx.evaluar(v.get("stock_volumen") or "0", ESCALAR)
        h = v.get("stock_cuerpo") or []
        c = ctx.estado.cuerpos[h[0]["ref"]["cuerpo"]] if modo == "cuerpo" and h else c
        if getattr(c, "tipo", "solido") != "solido":
            raise geo.ErrorGeometria(f"«{c.nombre}» no es un sólido: no tiene volumen para estimar.")
        return geo.volumen(c.forma)

    def _resultado(self, v, ctx):
        c = self._cuerpo(v, ctx)
        if c is None:
            return _NOTA
        material = self._material(v, c, ctx)
        if not material:
            return "Elegí el material más cercano para estimar."
        try:
            e = su.estimar(self._volumen(v, c, ctx), material)
        except Exception as ex:  # noqa: BLE001 — un valor a medio escribir o un material sin factor se muestran, no rompen el panel
            return str(ex)
        lugar = " · ".join(x for x in (v.get("region"), v.get("pais")) if x)
        return (f"Estimación: {e['co2_kg']:.3f} kg CO₂e\n{e['masa_kg']:.4f} kg × {e['co2_por_kg']:g} kg CO₂e/kg ({material})\n"
                f"Fuente: {e['fuente']}" + (f"\n{lugar}: la región todavía no cambia el cálculo." if lugar else ""))

    def _info_lista(self, v, ctx):
        n = v.get("lista")
        if not n or n not in su.materiales_propios():
            return ""
        d = su.materiales_propios()[n]
        return f"{d['co2']:g} kg CO₂e/kg · {d['densidad']:g} g/cm³" + (f" · parecido a {d['parecido']}" if d.get("parecido") else "")

    def _boton_crear(self, panel):
        b = QPushButton("Crear material")
        b.clicked.connect(lambda: self._crear(panel))
        return b

    def _botones_archivo(self, panel):
        caja = QWidget()
        fila = QHBoxLayout(caja)
        fila.setContentsMargins(0, 0, 0, 0)
        for texto, accion in (("Importar materiales", self._importar), ("Exportar materiales", self._exportar)):
            b = QPushButton(texto)
            b.clicked.connect(accion)
            fila.addWidget(b)
        return caja

    def _crear(self, panel):
        v, ctx = panel.valores, panel.ctx
        try:
            nombre = su.definir_material(v.get("nombre") or "", ctx.evaluar(v.get("co2") or "0", ESCALAR),
                                         ctx.evaluar(v.get("densidad") or "0", ESCALAR), _CLAVES.get(v.get("parecido"), ""))
        except (geo.ErrorGeometria, ErrorComando, ValueError) as e:
            self.aviso = str(e)
            panel._programar()
            return
        self.aviso = ""
        panel.set_valor("lista", nombre)
        panel.set_valor("nombre", "")

    def quitar_material_propio(self, nombre):
        su.borrar_material(nombre)
        self.panel._actualizar_visibles()

    def _importar(self):
        ruta, _f = QFileDialog.getOpenFileName(self.panel, "Importar materiales", "", "Materiales (*.json)")
        if ruta:
            try:
                importados, salteados = su.importar_materiales(ruta)
            except (geo.ErrorGeometria, OSError) as e:
                QMessageBox.warning(self.panel, self.TITULO, str(e))
                return
            self.panel._actualizar_visibles()
            QMessageBox.information(self.panel, self.TITULO, f"Importados: {len(importados)}. Salteados: {len(salteados)}.")

    def _exportar(self):
        ruta, _f = QFileDialog.getSaveFileName(self.panel, "Exportar materiales", "materiales.json", "Materiales (*.json)")
        if ruta:
            try:
                su.exportar_materiales(ruta)
            except OSError as e:
                QMessageBox.warning(self.panel, self.TITULO, str(e))

    def aplicar(self, v, ctx):
        return None


registrar(Sustentabilidad)
