"""B-563: Tangente entre una línea con los 2 extremos sobre un círculo (proyectado) y ese círculo: una cuerda no puede ser
tangente; el solver la aceptaba y la línea colapsaba a 0,013 mm. Ahora se rechaza con un aviso de un renglón."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from omnicad.restricciones import Boceto  # noqa: E402
from omnicad.restricciones.boceto import ErrorBoceto  # noqa: E402
from omnicad.timeline.parametros import TablaParametros  # noqa: E402

AVISO = "Tangente: la línea tiene los 2 extremos sobre la curva; soltá uno."


def _cuerda():
    b = Boceto()
    c = b.agregar_circulo((95, 40), 10)
    b.curvas[c].proyectada = True
    l = b.agregar_linea((81, 34), (109, 49))
    b.agregar_restriccion("coincidente", [b.curvas[l].p1, c])
    b.agregar_restriccion("coincidente", [b.curvas[l].p2, c])
    return b, c, l


@pytest.mark.parametrize("orden", [0, 1])
def test_la_cuerda_se_rechaza_en_los_dos_ordenes(orden):
    b, c, l = _cuerda()
    with pytest.raises(ErrorBoceto, match="2 extremos"):
        b.agregar_restriccion("tangente", [l, c] if orden == 0 else [c, l])
    assert not any(r.tipo == "tangente" for r in b.restricciones.values())


def test_con_un_extremo_suelto_se_puede():
    b, c, l = _cuerda()
    b.eliminar(next(k for k, r in b.restricciones.items() if r.entidades == [b.curvas[l].p2, c]))
    b.agregar_restriccion("tangente", [l, c])


def test_en_la_ventana_avisa_y_no_toca_la_linea():
    from omnicad.ui import editor_boceto
    QApplication.instance() or QApplication([])
    b, c, l = _cuerda()
    lz = editor_boceto.Lienzo(b, TablaParametros().evaluar)
    lz.resolver()
    largo = lz.b.medir_cota("distancia", [l])
    mensajes = []
    lz.mensaje.connect(mensajes.append)
    assert not lz.aplicar_restriccion("tangente", [l, c])
    assert AVISO in mensajes[-1]
    assert lz.b.medir_cota("distancia", [l]) == pytest.approx(largo)
    lz.close()
