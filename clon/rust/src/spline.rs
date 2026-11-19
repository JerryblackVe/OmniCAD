//! Geometría de B-splines del boceto (B-111, R5 chica): tangente y curvatura en los extremos de una spline de ajuste.
//! Misma cuenta, en el mismo orden, que `restricciones/boceto.py` (`interpolar_spline`, `_de_boor`, `evaluar_bspline`):
//! el solver la pide miles de veces por jacobiano y en Python cada una cuesta ~100 µs.
use numpy::PyReadonlyArray2;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Índice del tramo [u_k, u_k+1) que contiene t (fuera del dominio, el tramo extremo).
fn tramo(nudos: &[f64], p: usize, n: usize, t: f64) -> usize {
    if t >= nudos[n + 1] {
        let mut k = n;
        while k > p && nudos[k] >= nudos[n + 1] {
            k -= 1;
        }
        return k;
    }
    // bisect_right - 1
    let k = nudos.partition_point(|&u| u <= t).saturating_sub(1);
    k.max(p).min(n)
}

fn de_boor(ctrl: &[[f64; 3]], nudos: &[f64], p: usize, t: f64) -> [f64; 3] {
    let n = ctrl.len() - 1;
    let k = tramo(nudos, p, n, t);
    let mut d: Vec<[f64; 3]> = (0..=p).map(|j| ctrl[j + k - p]).collect();
    for r in 1..=p {
        for j in (r..=p).rev() {
            let i = j + k - p;
            let den = nudos[i + p - r + 1] - nudos[i];
            let a = if den != 0.0 { (t - nudos[i]) / den } else { 0.0 };
            let (anterior, actual) = (d[j - 1], d[j]);
            d[j] = std::array::from_fn(|c| (1.0 - a) * anterior[c] + a * actual[c]);
        }
    }
    d[p]
}

fn ctrl_derivada(ctrl: &[[f64; 3]], nudos: &[f64], p: usize) -> (Vec<[f64; 3]>, Vec<f64>, usize) {
    let q = (0..ctrl.len() - 1)
        .map(|i| {
            let den = nudos[i + p + 1] - nudos[i + 1];
            let f = if den != 0.0 { p as f64 / den } else { 0.0 };
            std::array::from_fn(|c| f * (ctrl[i + 1][c] - ctrl[i][c]))
        })
        .collect();
    (q, nudos[1..nudos.len() - 1].to_vec(), p - 1)
}

/// (C', C'') de una B-spline no racional en t (los pesos valen 1, como en el camino de Python).
fn derivadas(polos: &[[f64; 2]], nudos: &[f64], grado: usize, t: f64) -> ([f64; 2], [f64; 2]) {
    let mut c: Vec<[f64; 3]> = polos.iter().map(|q| [q[0], q[1], 1.0]).collect();
    let (mut k, mut q) = (nudos.to_vec(), grado as isize);
    let mut hs: Vec<[f64; 3]> = Vec::with_capacity(3);
    for orden in 0..3 {
        hs.push(if q >= 0 && !c.is_empty() {
            de_boor(&c, &k, q as usize, t)
        } else {
            [0.0; 3]
        });
        if orden < 2 {
            if q <= 0 || c.len() < 2 {
                c.clear();
                q = -1;
            } else {
                let (nc, nk, nq) = ctrl_derivada(&c, &k, q as usize);
                c = nc;
                k = nk;
                q = nq as isize;
            }
        }
    }
    let (a, a1, a2) = (hs[0], hs[1], hs[2]);
    let ws = if a[2] != 0.0 { a[2] } else { 1e-300 };
    let c0 = [a[0] / ws, a[1] / ws];
    let c1 = [(a1[0] - a1[2] * c0[0]) / ws, (a1[1] - a1[2] * c0[1]) / ws];
    let c2 = [
        (a2[0] - 2.0 * a1[2] * c1[0] - a2[2] * c0[0]) / ws,
        (a2[1] - 2.0 * a1[2] * c1[1] - a2[2] * c0[1]) / ws,
    ];
    (c1, c2)
}

/// N_{k-p..k,p}(t) (algoritmo A2.2 de Piegl y Tiller).
fn funciones_base(nudos: &[f64], p: usize, t: f64, k: usize) -> Vec<f64> {
    let mut n = vec![0.0; p + 1];
    n[0] = 1.0;
    let (mut izq, mut der) = (vec![0.0; p + 1], vec![0.0; p + 1]);
    for j in 1..=p {
        izq[j] = t - nudos[k + 1 - j];
        der[j] = nudos[k + j] - t;
        let mut salvado = 0.0;
        for r in 0..j {
            let den = der[r + 1] + izq[j - r];
            let temp = if den != 0.0 { n[r] / den } else { 0.0 };
            n[r] = salvado + der[r + 1] * temp;
            salvado = izq[j - r] * temp;
        }
        n[j] = salvado;
    }
    n
}

/// Parámetro 0-1 de cada punto de ajuste (largo de cuerda acumulado).
fn parametros_cuerda(q: &[[f64; 2]]) -> Vec<f64> {
    let m = q.len() - 1;
    let mut cuerdas: Vec<f64> = (1..=m)
        .map(|i| (q[i][0] - q[i - 1][0]).hypot(q[i][1] - q[i - 1][1]))
        .collect();
    let mut total: f64 = cuerdas.iter().sum();
    if total < 1e-12 {
        cuerdas = vec![1.0; m];
        total = m as f64;
    }
    let piso = total * 1e-9;
    cuerdas.iter_mut().for_each(|c| *c = c.max(piso));
    let total: f64 = cuerdas.iter().sum();
    let mut ub = vec![0.0];
    for c in cuerdas {
        ub.push(ub[ub.len() - 1] + c / total);
    }
    *ub.last_mut().unwrap() = 1.0;
    ub
}

/// Resuelve A·X = B (2 columnas) por eliminación con pivoteo parcial; None si A es singular.
fn resolver(mut a: Vec<Vec<f64>>, mut b: Vec<[f64; 2]>) -> Option<Vec<[f64; 2]>> {
    let n = a.len();
    for col in 0..n {
        let mut piv = col;
        for f in col + 1..n {
            if a[f][col].abs() > a[piv][col].abs() {
                piv = f;
            }
        }
        if a[piv][col] == 0.0 {
            return None;
        }
        a.swap(col, piv);
        b.swap(col, piv);
        for f in col + 1..n {
            let m = a[f][col] / a[col][col];
            if m != 0.0 {
                for c in col..n {
                    a[f][c] -= m * a[col][c];
                }
                b[f][0] -= m * b[col][0];
                b[f][1] -= m * b[col][1];
            }
        }
    }
    for f in (0..n).rev() {
        for c in f + 1..n {
            let (x, y) = (b[c][0], b[c][1]);
            b[f][0] -= a[f][c] * x;
            b[f][1] -= a[f][c] * y;
        }
        b[f][0] /= a[f][f];
        b[f][1] /= a[f][f];
    }
    Some(b)
}

/// Spline de ajuste ABIERTA (sin manijas) por los puntos `pts` (m+1 × 2): devuelve (C', C'') al inicio y (C', C'') al
/// final, respecto del parámetro 0-1: (d1x, d1y, d2x, d2y, d1x, d1y, d2x, d2y). Error si el sistema es singular (Python
/// resuelve entonces por mínimos cuadrados).
#[pyfunction]
pub fn spline_extremos(
    pts: PyReadonlyArray2<'_, f64>,
    grado: usize,
) -> PyResult<(f64, f64, f64, f64, f64, f64, f64, f64)> {
    let a = pts.as_array();
    if a.ncols() != 2 || a.nrows() < 2 || grado < 1 {
        return Err(PyValueError::new_err("Una spline necesita 2+ puntos (m×2) y grado ≥ 1."));
    }
    let q: Vec<[f64; 2]> = (0..a.nrows()).map(|i| [a[[i, 0]], a[[i, 1]]]).collect();
    let m = q.len() - 1;
    let ub = parametros_cuerda(&q);
    let (n, p) = (m, grado.min(m));
    let mut nudos = vec![0.0; p + 1];
    nudos.extend((1..=n - p).map(|j| ub[j..j + p].iter().sum::<f64>() / p as f64));
    nudos.extend(vec![1.0; p + 1]);
    let mut matriz = vec![vec![0.0; n + 1]; n + 1];
    for (fila, &u) in ub.iter().enumerate() {
        let k = tramo(&nudos, p, n, u);
        for (j, v) in funciones_base(&nudos, p, u, k).into_iter().enumerate() {
            matriz[fila][k - p + j] = v;
        }
    }
    let polos = resolver(matriz, q).ok_or_else(|| PyValueError::new_err("Sistema singular."))?;
    let (t0, t1) = (nudos[p], nudos[nudos.len() - p - 1]);
    let (a1, a2) = derivadas(&polos, &nudos, p, t0);
    let (b1, b2) = derivadas(&polos, &nudos, p, t1);
    Ok((a1[0], a1[1], a2[0], a2[1], b1[0], b1[1], b2[0], b2[1]))
}

/// Derivada d-ésima de N_{k-p..k,p}(t) (como `_base_derivada` de `boceto_geometria.py`).
fn base_derivada(nudos: &[f64], p: usize, t: f64, k: usize, d: usize) -> Vec<f64> {
    if d == 0 {
        return funciones_base(nudos, p, t, k);
    }
    if d > p {
        return vec![0.0; p + 1];
    }
    let mut baja = vec![0.0];
    baja.extend(base_derivada(nudos, p - 1, t, k, d - 1));
    baja.push(0.0);
    (0..=p)
        .map(|j| {
            let i = k - p + j;
            let (d1, d2) = (nudos[i + p] - nudos[i], nudos[i + p + 1] - nudos[i + 1]);
            let a = if d1 != 0.0 { baja[j] / d1 } else { 0.0 };
            let b = if d2 != 0.0 { baja[j + 1] / d2 } else { 0.0 };
            p as f64 * (a - b)
        })
        .collect()
}

/// Gauss-Legendre de 6 puntos (exacta para |C^(k)|² de una quíntica), como `np.polynomial.legendre.leggauss(6)`.
const GAUSS: [(f64, f64); 6] = [
    (-0.932_469_514_203_152_1, 0.171_324_492_379_170_3),
    (-0.661_209_386_466_264_5, 0.360_761_573_048_138_6),
    (-0.238_619_186_083_196_9, 0.467_913_934_572_691),
    (0.238_619_186_083_196_9, 0.467_913_934_572_691),
    (0.661_209_386_466_264_5, 0.360_761_573_048_138_6),
    (0.932_469_514_203_152_1, 0.171_324_492_379_170_3),
];
const PESOS_ENERGIA: [f64; 4] = [0.0, 1.0, 0.039_062_497_620_798_24, 0.008];

thread_local! {
    /// (nudos, 2H) por cantidad de segmentos: solo dependen de m (como el `lru_cache` de Python).
    static ENERGIA: std::cell::RefCell<std::collections::HashMap<usize, (Vec<f64>, Vec<Vec<f64>>)>> = Default::default();
}

/// (nudos uniformes con 5 tramos por segmento, 2H = gradiente de Σ w_k ∫|C^(k)|²), como `_energia_quintica`.
fn energia_quintica(m: usize) -> (Vec<f64>, Vec<Vec<f64>>) {
    let (p, tramos) = (5usize, 5 * m);
    let mut nudos = vec![0.0; p];
    nudos.extend((0..tramos).map(|j| j as f64 / tramos as f64));
    nudos.extend(vec![1.0; p + 1]);
    let n = nudos.len() - p - 1;
    let mut h = vec![vec![0.0; n]; n];
    for s in 0..tramos {
        let (a0, a1) = (nudos[p + s], nudos[p + s + 1]);
        for &(x, w) in &GAUSS {
            let (u, jac) = (0.5 * (a0 + a1 + (a1 - a0) * x), 0.5 * (a1 - a0) * w);
            for orden in 1..=3 {
                let b = base_derivada(&nudos, p, u, p + s, orden);
                for i in 0..=p {
                    for j in 0..=p {
                        h[s + i][s + j] += 2.0 * PESOS_ENERGIA[orden] * jac * b[i] * b[j];
                    }
                }
            }
        }
    }
    (nudos, h)
}

/// SOLVER-FUSION: como `spline_extremos`, para la spline de ajuste quíntica de Fusion (B-463, `_quintica_fusion` de
/// `boceto_geometria.py`, método de BauhausCM10.dll): abierta y sin manijas. Nombre aparte: un módulo viejo no la trae y el
/// solver cae a Python (con `spline_extremos(pts, 5)` haría una spline de interpolación de otro grado, sin avisar).
/// Resuelve denso: el solver la usa solo hasta `PUNTOS_QUINTICA_RUST` puntos; con más, rige la dispersa de Python.
#[pyfunction]
pub fn spline_quintica_extremos(pts: PyReadonlyArray2<'_, f64>) -> PyResult<(f64, f64, f64, f64, f64, f64, f64, f64)> {
    let a = pts.as_array();
    if a.ncols() != 2 || a.nrows() < 2 {
        return Err(PyValueError::new_err("Una spline necesita 2+ puntos (m×2)."));
    }
    let q: Vec<[f64; 2]> = (0..a.nrows()).map(|i| [a[[i, 0]], a[[i, 1]]]).collect();
    let (m, p) = (q.len() - 1, 5usize);
    // parámetros centrípetos regularizados (`parametros_cuerda(Q, 5)`)
    let mut cuerdas: Vec<f64> = (1..=m)
        .map(|i| ((q[i][0] - q[i - 1][0]).hypot(q[i][1] - q[i - 1][1]) / 10.0 + 1.1 / (5 * m) as f64).sqrt())
        .collect();
    let mut total: f64 = cuerdas.iter().sum();
    if total < 1e-12 {
        cuerdas = vec![1.0; m];
        total = m as f64;
    }
    let piso = total * 1e-9;
    cuerdas.iter_mut().for_each(|c| *c = c.max(piso));
    let total: f64 = cuerdas.iter().sum();
    let mut ub = vec![0.0];
    for c in &cuerdas {
        ub.push(ub[ub.len() - 1] + c / total);
    }
    *ub.last_mut().unwrap() = 1.0;
    let (nudos, h2) = ENERGIA.with(|c| c.borrow_mut().entry(m).or_insert_with(|| energia_quintica(m)).clone());
    let n = nudos.len() - p - 1;
    let filas = m + 1;
    let tam = n + filas;
    let mut k_mat = vec![vec![0.0; tam]; tam];
    for (fila, h) in k_mat.iter_mut().zip(&h2) {
        fila[..n].copy_from_slice(h);
    }
    let h_max = h2.iter().flatten().fold(0.0f64, |acc, v| acc.max(v.abs()));
    let mut d = vec![[0.0; 2]; tam];
    for (fila, (&u, punto)) in ub.iter().zip(&q).enumerate() {
        let k = tramo(&nudos, p, n - 1, u);
        let base = funciones_base(&nudos, p, u, k);
        let escala = h_max / base.iter().fold(0.0f64, |acc, v| acc.max(v.abs()));
        for (j, v) in base.into_iter().enumerate() {
            k_mat[n + fila][k - p + j] = v * escala;
            k_mat[k - p + j][n + fila] = v * escala;
        }
        d[n + fila] = [punto[0] * escala, punto[1] * escala];
    }
    let sol = resolver(k_mat, d).ok_or_else(|| PyValueError::new_err("Sistema singular."))?;
    let polos = &sol[..n];
    let (a1, a2) = derivadas(polos, &nudos, p, 0.0);
    let (b1, b2) = derivadas(polos, &nudos, p, 1.0);
    Ok((a1[0], a1[1], a2[0], a2[1], b1[0], b1[1], b2[0], b2[1]))
}
