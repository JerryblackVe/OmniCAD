"""P-197: rejilla de la barra de navegación (Bloqueo y Parámetros de rejilla), como Fusion."""
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from omnicad.nucleo import geometria as g
from omnicad.ui import visor3d


def _visor(px_por_mm, **config):
    cfg = SimpleNamespace(**{"rejilla_fija": None, "rejilla_bloqueada": False, "paso_bloqueado": None, **config})
    v = SimpleNamespace(config=cfg, px_por_mm=lambda: px_por_mm[0])
    v.paso_rejilla = lambda: visor3d.Visor3D.paso_rejilla(v)
    v.subdivisiones_rejilla = lambda: visor3d.Visor3D.subdivisiones_rejilla(v)
    return v


def test_bloqueo_de_rejilla_al_reabrir_sigue_bloqueado():
    """Bloqueada en las preferencias (al reabrir no hay paso guardado): el paso del primer uso no cambia con el zoom.
    Antes el menú la mostraba bloqueada y el paso seguía al zoom (5 → 100 mm)."""
    zoom = [3.0]
    v = _visor(zoom, rejilla_bloqueada=True)
    paso = v.paso_rejilla()
    zoom[0] = 0.05
    assert v.paso_rejilla() == paso
    v.config.rejilla_bloqueada = False
    assert v.paso_rejilla() > paso                      # desbloqueada vuelve a seguir al zoom


def test_rejilla_fija_marca_las_mayores_en_el_espaciado_elegido():
    """Parámetros de rejilla › Fija, 10 mm con 4 subdivisiones: paso 2,5 y las líneas mayores cada 10 mm (antes cada 5
    pasos: 12,5 mm)."""
    v = _visor([3.0], rejilla_fija=(10.0, 4))
    paso, cada = v.paso_rejilla(), v.subdivisiones_rejilla()
    assert (paso, cada) == (2.5, 4)
    vert, col = visor3d.lineas_rejilla(g.Plano("XY"), paso, (0.0, 0.0), (0.5, 0.5, 0.5), False, n=10, cada=cada)
    u, alfa = vert[0::4, 0], col[0::4, 3]               # una línea de u fija cada 4 vértices
    assert np.allclose(sorted({round(float(x), 6) for x, a in zip(u, alfa, strict=True) if a > 0.3}), [-20, -10, 0, 10, 20])
    assert _visor([3.0]).subdivisiones_rejilla() == 5   # adaptativa: cada 5, como siempre
