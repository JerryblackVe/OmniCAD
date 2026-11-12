"""B-300: el tamaño que propone el diálogo de Rosca no dispara «Sin datos verificados de tolerancia»."""
import pytest

from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import tolerancias as tol
from omnicad.ui.comandos import crear


@pytest.mark.parametrize("familia", [k for k, f in sc.FAMILIAS_ROSCA.items() if not f["conica"]])
def test_el_tamano_inicial_de_cada_familia_tiene_datos_de_tolerancia(familia):
    tamano = crear._tamano_inicial(familia, sc.tamanos_rosca(familia))
    datos = sc.datos_rosca(sc.designaciones_rosca(familia, tamano)[0])
    for interna in (True, False):
        _, aviso = tol.resolver_clase(datos["familia"], datos["diametro"], datos["paso"], "auto", interna)
        assert aviso is None, (familia, tamano, interna, aviso)


def test_el_aviso_sigue_saliendo_cuando_el_tamano_elegido_no_tiene_tabla():
    datos = sc.datos_rosca("GOST ST1.5x0.5")          # B-368: M0.25 ya tiene tabla; las autorroscantes ST no traen clase h14
    _, aviso = tol.resolver_clase(datos["familia"], datos["diametro"], datos["paso"], "auto", False)
    assert aviso and "Sin datos verificados" in aviso
