# -*- coding: utf-8 -*-
"""
Pieza de calibración de holguras como paso del timeline (el núcleo está en `nucleo/calibracion.py`): una placa con
agujeros de holgura creciente y el peine de pernos con que se prueban, para imprimirlos y averiguar qué
`print_clearance` pedirle a la impresora. Crea dos cuerpos nuevos.
"""
from ..nucleo import calibracion as cal
from ..nucleo import geometria as geo
from .operaciones import ErrorOperacion, Operacion, registrar_operacion


class OpCalibracionHolguras(Operacion):
    """Pieza de calibración de holguras: placa con `cantidad` agujeros de Ø diametro + 2·holgura (la holgura radial
    sube de `holgura_inicial` en `paso`), con su valor grabado, y el peine de pernos de Ø diametro. Dos cuerpos."""
    TIPO, ETIQUETA, ICONO = "calibracion_holguras", "Calibración de holguras", "◎"
    PARAMS = {"diametro": "5 mm", "holgura_inicial": "0.1 mm", "paso": "0.1 mm", "cantidad": 5, "espesor": "3 mm",
              "etiquetas": True}
    EXPRESIONES = ("diametro", "holgura_inicial", "paso", "espesor")

    def ejecutar(self, estado, ctx):
        v = {k: ctx.evaluar(self.p[k]) for k in self.EXPRESIONES}
        try:
            r = cal.pieza_calibracion_holguras(v["diametro"], v["holgura_inicial"], v["paso"], self.entero("cantidad"),
                                               v["espesor"], bool(self.p.get("etiquetas")))
        except geo.ErrorGeometria as e:
            raise ErrorOperacion(str(e)) from e
        estado.nuevo_cuerpo(self.id, r["placa"], "solido", nombre="Placa de calibración")
        estado.nuevo_cuerpo(self.id, r["peine"], "solido", nombre="Peine de calibración")


registrar_operacion(OpCalibracionHolguras)
