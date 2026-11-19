"""B-658: al soltar, la resolución completa de un boceto con Curvatura quedaba en 2,9e-6 mm (apenas sobre TOLERANCIA) y el
Lienzo decía «Restricciones en conflicto». Estado real capturado en la ventana justo antes de esa resolución
(spline y arco con Curvatura, tras arrastrar el extremo de la spline)."""
import json

from omnicad.restricciones.boceto import Boceto
from omnicad.restricciones.solver import TOLERANCIA, resolver

ESTADO = '{"siguiente_id": 9, "puntos": [{"id": 1, "x": 59.99990680325433, "y": 39.99988496618507}, {"id": 2, "x": 14.95715680701231, "y": 25.005040149397168}, {"id": 3, "x": 59.999905908034584, "y": 39.99988379346312}, {"id": 6, "x": 26.466017597580436, "y": 65.6012922041037}, {"id": 7, "x": 68.5787192917526, "y": 63.05686862070172}], "curvas": [{"tipo": "spline", "id": 4, "modo": "ajuste", "grado": 3, "cerrada": false, "pesos": null, "nudos": null, "construccion": false, "puntos": [2, 3, 1]}, {"tipo": "arco", "id": 5, "centro": 6, "inicio": 1, "fin": 7, "construccion": false}], "restricciones": [{"id": 8, "tipo": "curvatura", "entidades": [4, 5], "datos": {}}], "cotas": []}'


def test_resolver_al_soltar_no_da_conflicto_falso_con_curvatura():
    b = Boceto.desde_dict(json.loads(ESTADO))
    r = resolver(b, {})
    assert r.ok, r.descripcion()
    assert r.residuo_max < TOLERANCIA
