"""B-552: una sección tangente no deja el visor vacío sin aviso."""
from types import SimpleNamespace

import pytest

from omnicad.nucleo import geometria as geo
from omnicad.ui.comando import ErrorComando
from omnicad.ui.comandos.inspeccionar import Seccion


def test_seccion_en_base_avisa_y_conserva_cuerpo():
    forma = geo.caja(10, 10, 10)
    estado = SimpleNamespace(cuerpos={"c": SimpleNamespace(forma=forma)})
    visor = SimpleNamespace(set_capa=lambda *_: None)
    ventana = SimpleNamespace(visor=visor, propiedades_analisis=lambda _: {})
    guardados = []
    ctx = SimpleNamespace(estado=estado, ventana=ventana,
                          evaluar=lambda valor, *_: float(valor.split()[0]),
                          doc=SimpleNamespace(agregar_analisis=lambda *args: guardados.append(args)))
    valores = {"plano": [{"ref": {"tipo": "plano", "id": "XY"}}],
               "desfase": "0 mm", "angulo": "0 deg", "invertir": False,
               "color_modo": "personalizado", "rayado": False}
    comando = Seccion()
    with pytest.raises(ErrorComando, match="El plano no corta el cuerpo"):
        comando.mostrar(valores, ctx)
    assert not visor.cortes
    with pytest.raises(ErrorComando, match="El plano no corta el cuerpo"):
        comando.aplicar(valores, ctx)
    assert not guardados

    valores["desfase"] = "5 mm"
    comando.mostrar(valores, ctx)
    assert len(visor.cortes) == 1
    comando.aplicar(valores, ctx)
    assert len(guardados) == 1
