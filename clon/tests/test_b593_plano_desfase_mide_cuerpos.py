"""B-593: un plano de desfase sobre XY (Redimensionar: Predeterminado) se mide por los cuerpos, no por la cámara."""
from omnicad import api


def _llamar(sesion, herramienta, **argumentos):
    respuesta = api.llamar(sesion, herramienta, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def test_plano_desfase_cubre_un_cuerpo_lejos_del_origen():
    sesion = api.Sesion()
    cuerpo = _llamar(sesion, "create_box", length=20, width=30, height=40, anchor="corner")["bodies_created"][0]["id"]
    _llamar(sesion, "move_body", body=cuerpo, translate=[500, -300, 0])
    plano = _llamar(sesion, "create_construction_plane", type="offset", references=["XY"], distance=20)["plane"]["id"]
    estado = sesion.doc.estado_final
    u0, v0, u1, v1 = estado.medidas[plano]["limites"]
    assert u0 < 500 and v0 < -300 and u1 > 520 and v1 > -270            # envuelve la caja movida, con margen
    assert u1 - u0 < 60 and v1 - v0 < 80                                # y no se dispara
