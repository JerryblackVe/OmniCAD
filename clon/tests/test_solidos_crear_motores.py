"""La ruta histórica de Crear sigue despachando después de separar los temas."""
import os
import subprocess
import sys


def test_crear_con_omnikernel_y_cambio_a_opencascade():
    # Proceso limpio: los demás tests ya cargaron OpenCascade durante la colección.
    codigo = """
import sys
from omnicad.nucleo import motor, solidos_crear as sc

if motor.version_omnikernel() is not None:
    assert sc.datos_rosca('M6')['paso'] == 1
    assert sc.transformacion_escala(2).diagonal().tolist() == [2, 2, 2, 1]
assert not any(n.split('.')[0] in ('OCP', 'PySide6') for n in sys.modules)
with motor.fijar_motor('opencascade'):
    assert sc.datos_rosca('M6')['paso'] == 1
    escala = sc.transformacion_escala(2)
    assert isinstance(escala, sc.gp_Trsf)
    assert escala.ScaleFactor() == 2
"""
    subprocess.run([sys.executable, "-c", codigo], check=True, env=dict(os.environ, OMNICAD_MOTOR="omnikernel"))
