"""B-435: una cantidad enorme debe rechazarse por el tope, sin un error interno."""
from test_b435_cantidad_patron_trayectoria import _caso

from omnicad import api


def test_cantidad_entera_enorme_da_error_de_argumentos_sin_cambiar_el_documento():
    sesion, cuerpo, _ = _caso()
    antes = sesion.doc.a_dict()

    respuesta = api.llamar(sesion, "path_pattern", {
        "bodies": cuerpo, "path_sketch": "Ruta", "count": 10**309, "distance": 30,
    })

    assert not respuesta["ok"], respuesta
    assert sesion.doc.a_dict() == antes
    assert respuesta["error_kind"] == "INVALID_ARGUMENTS", respuesta
    assert "10.000" in respuesta["mensaje"]
