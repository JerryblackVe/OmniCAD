"""B-858: una reglada no se rechaza porque el análisis no llegó; un cruce comprobado sí."""
import math
from unittest.mock import patch

import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt

from omnicad.nucleo import geometria as geo, revision
from omnicad.nucleo import superficies as sf


def _circulo(radio):
    circulo = gp_Circ(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), radio)
    return BRepBuilderAPI_MakeEdge(circulo).Edge()


def _reglada(radio, distancia, avisos=None):
    return sf.reglada([_circulo(radio)], distancia, tipo="tangente",
                      referencia=geo.Plano("XY"), avisos=avisos)


def test_reglada_sin_analisis_no_rechaza_y_avisa():
    aviso = {"mensaje": "No se revisaron las autointersecciones: plazo agotado."}
    avisos = []
    with patch.object(revision, "_autointersecciones_seguras", return_value=(None, [aviso], False)):
        forma = _reglada(20, -10, avisos)
    assert geo.es_valida(forma) and geo.area(forma) == pytest.approx(300 * math.pi)
    assert avisos == [aviso["mensaje"]]


def test_reglada_con_cruce_comprobado_sigue_rechazando():
    real = revision._autointersecciones_seguras
    completos = []

    def espia(forma, limite, plazo):
        cantidad, problemas, completo = real(forma, limite, plazo)
        completos.append(completo)
        return cantidad, problemas, completo

    with patch.object(revision, "_autointersecciones_seguras", side_effect=espia):
        with pytest.raises(geo.ErrorGeometria, match="La reglada se cruza"):
            _reglada(5, -6)
    assert completos == [True]
