//! Cálculos puros del render local; Python conserva la escena y OpenCascade.
use numpy::{PyArray1, PyReadonlyArray1, PyReadonlyArray2, PyReadwriteArray1};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

mod perfiles;

#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn rasterizar(
    py: Python<'_>,
    sx: PyReadonlyArray2<'_, f64>,
    sy: PyReadonlyArray2<'_, f64>,
    sz: PyReadonlyArray2<'_, f64>,
    orden: PyReadonlyArray1<'_, i64>,
    ancho: usize,
    alto: usize,
    mut profundidad: PyReadwriteArray1<'_, f64>,
    mut ids: PyReadwriteArray1<'_, i64>,
    base: i64,
) -> PyResult<()> {
    let x = sx.as_array();
    let y = sy.as_array();
    let z = sz.as_array();
    let orden = orden.as_slice()?;
    let profundidad = profundidad.as_slice_mut()?;
    let ids = ids.as_slice_mut()?;
    if ancho == 0
        || alto == 0
        || ancho.checked_mul(alto) != Some(profundidad.len())
        || ids.len() != profundidad.len()
        || x.ncols() != 3
        || y.dim() != x.dim()
        || z.dim() != x.dim()
        || orden.iter().any(|&i| i < 0 || i as usize >= x.nrows())
        || base.checked_add(x.nrows() as i64).is_none()
    {
        return Err(PyValueError::new_err(
            "Dimensiones inválidas para rasterizar.",
        ));
    }
    py.allow_threads(|| {
        for &indice in orden {
            let i = indice as usize;
            let (ax, bx, cx) = (x[[i, 0]], x[[i, 1]], x[[i, 2]]);
            let (ay, by, cy) = (y[[i, 0]], y[[i, 1]], y[[i, 2]]);
            let area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay);
            let x0 = ((ax.min(bx).min(cx) - 0.5).ceil().max(0.0) as usize).min(ancho - 1);
            let x1 = ((ax.max(bx).max(cx) - 0.5).floor() as isize).min(ancho as isize - 1);
            let y0 = ((ay.min(by).min(cy) - 0.5).ceil().max(0.0) as usize).min(alto - 1);
            let y1 = ((ay.max(by).max(cy) - 0.5).floor() as isize).min(alto as isize - 1);
            if x1 < x0 as isize || y1 < y0 as isize {
                continue;
            }
            for fila in y0..=y1 as usize {
                let py = fila as f64 + 0.5;
                for columna in x0..=x1 as usize {
                    let px = columna as f64 + 0.5;
                    let la = ((bx - px) * (cy - py) - (by - py) * (cx - px)) / area;
                    let lb = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) / area;
                    let lc = 1.0 - la - lb;
                    if la >= -1e-7 && lb >= -1e-7 && lc >= -1e-7 {
                        let d = la * z[[i, 0]] + lb * z[[i, 1]] + lc * z[[i, 2]];
                        let pixel = fila * ancho + columna;
                        if d < profundidad[pixel] {
                            profundidad[pixel] = d;
                            ids[pixel] = indice + base;
                        }
                    }
                }
            }
        }
    });
    Ok(())
}

#[pyfunction]
fn visibilidad<'py>(
    py: Python<'py>,
    coordenadas: PyReadonlyArray2<'_, f64>,
    mapa: PyReadonlyArray2<'_, f64>,
    disco: PyReadonlyArray2<'_, f64>,
    radio: f64,
    sesgo: f64,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let c = coordenadas.as_array();
    let z = mapa.as_array();
    let d = disco.as_array();
    if c.ncols() != 3
        || z.nrows() == 0
        || z.nrows() != z.ncols()
        || d.ncols() != 2
        || d.nrows() == 0
    {
        return Err(PyValueError::new_err(
            "Dimensiones inválidas del mapa de sombras.",
        ));
    }
    let n = z.nrows();
    let salida = py.allow_threads(|| {
        (0..c.nrows())
            .map(|i| {
                let (sx, sy, sz) = (c[[i, 0]], c[[i, 1]], c[[i, 2]]);
                if sx < 0.0 || sy < 0.0 || sx >= n as f64 || sy >= n as f64 {
                    return 1.0;
                }
                let mut luz = 0;
                for j in 0..d.nrows() {
                    let x = ((sx + d[[j, 0]] * radio).floor().max(0.0) as usize).min(n - 1);
                    let y = ((sy + d[[j, 1]] * radio).floor().max(0.0) as usize).min(n - 1);
                    luz += usize::from(sz <= z[[y, x]] + sesgo * (1.0 + radio * 0.15));
                }
                luz as f64 / d.nrows() as f64
            })
            .collect::<Vec<_>>()
    });
    Ok(PyArray1::from_vec(py, salida))
}

#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn oclusion<'py>(
    py: Python<'py>,
    posiciones: PyReadonlyArray2<'_, f64>,
    normales: PyReadonlyArray2<'_, f64>,
    profundidad: PyReadonlyArray1<'_, f64>,
    proyeccion: PyReadonlyArray2<'_, f64>,
    direcciones: PyReadonlyArray2<'_, f64>,
    escalas: PyReadonlyArray1<'_, f64>,
    ancho: usize,
    alto: usize,
    radio: f64,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let p = posiciones.as_array();
    let n = normales.as_array();
    let z = profundidad.as_slice()?;
    let m = proyeccion.as_array();
    let d = direcciones.as_array();
    let e = escalas.as_slice()?;
    if p.ncols() != 3
        || n.dim() != p.dim()
        || m.dim() != (4, 4)
        || d.ncols() != 3
        || d.nrows() != e.len()
        || e.is_empty()
        || ancho.checked_mul(alto) != Some(z.len())
    {
        return Err(PyValueError::new_err(
            "Dimensiones inválidas para la oclusión ambiental.",
        ));
    }
    let salida = py.allow_threads(|| {
        (0..p.nrows())
            .map(|i| {
                let giro =
                    ((i as u64 * 2654435761) % 4096) as f64 / 4096.0 * 2.0 * std::f64::consts::PI;
                let (s, c) = giro.sin_cos();
                let mut ocl = 0.0;
                for j in 0..e.len() {
                    let mut dd = [
                        c * d[[j, 0]] - s * d[[j, 1]],
                        s * d[[j, 0]] + c * d[[j, 1]],
                        d[[j, 2]],
                    ];
                    if dd[0] * n[[i, 0]] + dd[1] * n[[i, 1]] + dd[2] * n[[i, 2]] < 0.0 {
                        dd.iter_mut().for_each(|v| *v = -*v);
                    }
                    let q = [
                        p[[i, 0]] + dd[0] * radio * e[j],
                        p[[i, 1]] + dd[1] * radio * e[j],
                        p[[i, 2]] + dd[2] * radio * e[j],
                        1.0,
                    ];
                    let h: [f64; 4] =
                        std::array::from_fn(|k| (0..4).map(|v| q[v] * m[[k, v]]).sum());
                    let w = if h[3].abs() < 1e-12 { 1e-12 } else { h[3] };
                    let x = ((h[0] / w + 1.0) * 0.5 * ancho as f64).floor() as isize;
                    let y = ((1.0 - h[1] / w) * 0.5 * alto as f64).floor() as isize;
                    if x >= 0 && y >= 0 && x < ancho as isize && y < alto as isize {
                        let zq = z[y as usize * ancho + x as usize];
                        if zq.is_finite() && zq > q[2] + radio * 0.02 {
                            let t = (radio / (zq - p[[i, 2]]).abs().max(1e-9)).clamp(0.0, 1.0);
                            ocl += t * t * (3.0 - 2.0 * t);
                        }
                    }
                }
                (1.0 - ocl / e.len() as f64 * 1.1).clamp(0.25, 1.0)
            })
            .collect::<Vec<_>>()
    });
    Ok(PyArray1::from_vec(py, salida))
}

#[pymodule]
fn _rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rasterizar, m)?)?;
    m.add_function(wrap_pyfunction!(visibilidad, m)?)?;
    m.add_function(wrap_pyfunction!(oclusion, m)?)?;
    m.add_function(wrap_pyfunction!(perfiles::arreglo_planar, m)?)?;
    Ok(())
}
