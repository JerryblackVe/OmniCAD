"""B-427: la simetría avisa si crea una copia coincidente con el cuerpo original."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo


@pytest.mark.parametrize("z,combinar,avisa", [
    (-5, False, True),
    (10, False, False),
    (-4, False, False),
    (-4.9999, False, False),
    (-5, True, False),
])
def test_simetria_xy_avisa_solo_si_la_copia_coincide(z, combinar, avisa):
    sesion = api.Sesion()
    creado = api.llamar(sesion, "create_box", {
        "length": 30, "width": 20, "height": 10, "z": z, "name": "Bloque",
    })
    assert creado["ok"], creado

    resultado = api.llamar(sesion, "mirror", {
        "bodies": "Bloque", "plane": "XY", "combine": combinar,
    })
    assert resultado["ok"], resultado
    if avisa:
        assert any("Bloque" in a and "coincide" in a and "original" in a for a in resultado["avisos"]), resultado
    else:
        assert not resultado["avisos"], resultado
    assert sesion.doc.resultados[-1].estado == ("aviso" if avisa else "ok")

    cuerpos = list(sesion.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == (1 if combinar else 2)
    assert all(geo.es_valida(c.forma) for c in cuerpos)
    assert all(geo.volumen_exacto(c.forma) == pytest.approx(6000) for c in cuerpos)
    assert geo.centro_masa(sesion.cuerpo("Bloque").forma)[2] == pytest.approx(z + 5)
    if not combinar:
        copia = sesion.cuerpo("Bloque (copia)").forma
        assert geo.centro_masa(copia)[2] == pytest.approx(-z - 5)
        minimo, maximo = geo.caja_envolvente(copia)
        assert minimo == pytest.approx((-15, -10, -z - 10))
        assert maximo == pytest.approx((15, 10, -z))
