"""B-704: el test del hover (rsx3) no depende de lo que dejó una prueba anterior: con otro Lienzo visible sin cerrar
(lo que queda cuando una prueba falla antes de su `lz.close()`), sigue pasando."""
import test_rsx3_hover_boceto as rsx3


def test_el_hover_resiste_un_lienzo_visible_sin_cerrar():
    fantasma = rsx3._lienzo(500)
    fantasma.show()
    try:
        rsx3.test_rsx3_el_hover_resalta_con_mas_de_400_curvas()
    finally:
        fantasma.close()
