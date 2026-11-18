"""B-631: aísla la única unión del caso de fuzz otra-1589."""
import pytest
from test_b39_fuzz import fuzz


@pytest.mark.xfail(strict=True, reason="B-631")
def test_b_631_unir_placa_y_esfera_no_deja_fallos_graves():
    nombre, herramientas, fallos = fuzz.correr_caso("otra", 1589, ligero=True)
    assert not fuzz.graves(fallos), f"{fuzz.descripcion(nombre, herramientas)}\n{fallos}"
