"""P-201: un hilo de OpenBLAS para las cuentas chicas del solver, y al salir los que había."""
from omnicad import hilos_blas


def test_un_hilo_baja_a_uno_y_devuelve_los_de_antes_anidado():
    libs = hilos_blas._bibliotecas()
    assert libs, "numpy y scipy traen su OpenBLAS en numpy.libs y scipy.libs"
    antes = [leer() for _p, leer in libs]
    with hilos_blas.un_hilo():
        with hilos_blas.un_hilo():
            assert [leer() for _p, leer in libs] == [1] * len(libs)
        assert [leer() for _p, leer in libs] == [1] * len(libs)      # el de afuera sigue en uno
    assert [leer() for _p, leer in libs] == antes


def test_un_hilo_sin_openblas_o_si_falla_no_rompe(monkeypatch):
    monkeypatch.setitem(hilos_blas._estado, "libs", [])
    with hilos_blas.un_hilo():
        pass

    def falla(*_a):
        raise OSError("sin símbolo")
    monkeypatch.setitem(hilos_blas._estado, "libs", [(falla, lambda: 8)])
    with hilos_blas.un_hilo():
        pass
    assert hilos_blas._estado["profundidad"] == 0
