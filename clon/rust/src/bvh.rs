//! BVH de triángulos para rayos (RS-R3): el primer triángulo que corta cada rayo, con la misma cuenta (Möller–Trumbore) y
//! los mismos bordes que las referencias numpy (`nucleo/revision.py` › `primer_choque`, `ui/visor3d.py` ›
//! `rayo_triangulos`). Datos puros: un arreglo de triángulos dentro, arreglos de distancias e índices fuera.
//!
//! shortcut: partición por la mediana del eje más largo (no SAH) y hojas de 4; construir 251 k triángulos cuesta ~60 ms
//! y 2000 rayos ~4 ms. Subir a SAH por bins si aparece una malla muy desbalanceada.
use numpy::{PyArray1, PyReadonlyArray2, PyReadonlyArray3, PyUntypedArrayMethods};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

type V = [f64; 3];

const HOJA: usize = 4;
const PILA: usize = 64;

fn resta(a: V, b: V) -> V {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}
fn cruz(a: V, b: V) -> V {
    [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
}
fn punto(a: V, b: V) -> f64 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

struct Nodo {
    lo: V,
    hi: V,
    /// hijos si `n == 0`; si no, la hoja abarca `orden[ini..ini + n]`
    izq: u32,
    der: u32,
    ini: u32,
    n: u32,
}

struct Triangulos {
    p0: Vec<V>,
    e1: Vec<V>,
    e2: Vec<V>,
    /// largo de e1 × e2 (la normal sin normalizar), para el descarte de rayos paralelos
    largo_n: Vec<f64>,
}

/// Cajas y centros de los triángulos, para construir.
struct Cajas {
    lo: Vec<V>,
    hi: Vec<V>,
    centro: Vec<V>,
}

fn construir_nodos(nodos: &mut Vec<Nodo>, orden: &mut [u32], base: usize, cajas: &Cajas) -> u32 {
    let (mut l, mut h) = ([f64::INFINITY; 3], [f64::NEG_INFINITY; 3]);
    let (mut cl, mut ch) = ([f64::INFINITY; 3], [f64::NEG_INFINITY; 3]);
    for &i in orden.iter() {
        let i = i as usize;
        for k in 0..3 {
            l[k] = l[k].min(cajas.lo[i][k]);
            h[k] = h[k].max(cajas.hi[i][k]);
            cl[k] = cl[k].min(cajas.centro[i][k]);
            ch[k] = ch[k].max(cajas.centro[i][k]);
        }
    }
    let id = nodos.len() as u32;
    nodos.push(Nodo { lo: l, hi: h, izq: 0, der: 0, ini: base as u32, n: orden.len() as u32 });
    if orden.len() <= HOJA {
        return id;
    }
    let eje = (1..3).fold(0, |m, k| if ch[k] - cl[k] > ch[m] - cl[m] { k } else { m });
    if ch[eje] - cl[eje] <= 0.0 {
        return id; // todos los centros coinciden (o hay NaN): hoja grande, correcta aunque lenta
    }
    let mitad = orden.len() / 2;
    orden.select_nth_unstable_by(mitad, |&a, &b| cajas.centro[a as usize][eje].total_cmp(&cajas.centro[b as usize][eje]));
    let (a, b) = orden.split_at_mut(mitad);
    let izq = construir_nodos(nodos, a, base, cajas);
    let der = construir_nodos(nodos, b, base + mitad, cajas);
    let nodo = &mut nodos[id as usize];
    nodo.izq = izq;
    nodo.der = der;
    nodo.n = 0;
    id
}

/// ¿El rayo (con su inverso por eje) entra en la caja antes de `tmax`?
fn toca_caja(o: V, inv: V, lo: V, hi: V, tmax: f64) -> bool {
    let (mut t0, mut t1) = (0.0f64, tmax);
    for k in 0..3 {
        if inv[k].is_infinite() {
            // eje paralelo (d = ±0): o está dentro de la losa o el rayo no entra nunca; (lo − o)·∞ daría NaN con o = lo
            if o[k] < lo[k] || o[k] > hi[k] {
                return false;
            }
            continue;
        }
        let (a, b) = ((lo[k] - o[k]) * inv[k], (hi[k] - o[k]) * inv[k]);
        t0 = t0.max(a.min(b));
        t1 = t1.min(a.max(b));
        if t0 > t1 {
            return false;
        }
    }
    true
}

/// Distancias e índices de triángulo de un lote de rayos.
type Choques<'py> = (Bound<'py, PyArray1<f64>>, Bound<'py, PyArray1<i64>>);

#[pyclass(frozen)]
pub struct Bvh {
    nodos: Vec<Nodo>,
    orden: Vec<u32>,
    tri: Triangulos,
}

impl Bvh {
    /// Construye desde T·9 números (a, b, c de cada triángulo).
    fn desde(v: &[f64]) -> Bvh {
        let n = v.len() / 9;
        let mut tri = Triangulos { p0: Vec::with_capacity(n), e1: Vec::with_capacity(n), e2: Vec::with_capacity(n), largo_n: Vec::with_capacity(n) };
        let mut cajas = Cajas { lo: Vec::with_capacity(n), hi: Vec::with_capacity(n), centro: Vec::with_capacity(n) };
        for t in v.as_chunks::<9>().0 {
            let (a, b, c) = ([t[0], t[1], t[2]], [t[3], t[4], t[5]], [t[6], t[7], t[8]]);
            let (e1, e2) = (resta(b, a), resta(c, a));
            let nrm = cruz(e1, e2);
            tri.p0.push(a);
            tri.e1.push(e1);
            tri.e2.push(e2);
            tri.largo_n.push(punto(nrm, nrm).sqrt());
            let lo: V = std::array::from_fn(|k| a[k].min(b[k]).min(c[k]));
            let hi: V = std::array::from_fn(|k| a[k].max(b[k]).max(c[k]));
            cajas.centro.push(std::array::from_fn(|k| (lo[k] + hi[k]) * 0.5));
            // el choque acepta hasta 1e-9 (coordenadas baricéntricas) fuera del triángulo: la caja lo deja pasar
            let borde = punto(e1, e1).max(punto(e2, e2)).max(punto(resta(e2, e1), resta(e2, e1))).sqrt();
            cajas.lo.push(lo.map(|x| x - 4e-9 * borde));
            cajas.hi.push(hi.map(|x| x + 4e-9 * borde));
        }
        let mut orden: Vec<u32> = (0..n as u32).collect();
        let mut nodos = Vec::with_capacity(n / 2 + 1);
        if n > 0 {
            construir_nodos(&mut nodos, &mut orden, 0, &cajas);
        }
        Bvh { nodos, orden, tri }
    }

    /// (t, índice) del primer triángulo con t > `eps`; el de menor índice si empatan. (inf, −1) si ninguno.
    fn primero(&self, o: V, d: V, eps: f64, det_abs: f64, det_rel: f64) -> (f64, i64) {
        let inv = [1.0 / d[0], 1.0 / d[1], 1.0 / d[2]];
        let (mut mejor, mut indice) = (f64::INFINITY, -1i64);
        let mut pila = [0u32; PILA];
        let mut sp = 1;
        while sp > 0 {
            sp -= 1;
            let nodo = &self.nodos[pila[sp] as usize];
            if !toca_caja(o, inv, nodo.lo, nodo.hi, mejor) {
                continue;
            }
            if nodo.n == 0 {
                pila[sp] = nodo.izq;
                pila[sp + 1] = nodo.der;
                sp += 2;
                continue;
            }
            for &i in &self.orden[nodo.ini as usize..(nodo.ini + nodo.n) as usize] {
                let i = i as usize;
                let (e1, e2) = (self.tri.e1[i], self.tri.e2[i]);
                let p = cruz(d, e2);
                let det = punto(e1, p);
                if det.abs() <= det_abs + det_rel * self.tri.largo_n[i] {
                    continue;
                }
                let inv_det = 1.0 / det;
                let tv = resta(o, self.tri.p0[i]);
                let u = punto(tv, p) * inv_det;
                if !(-1e-9..=1.0 + 1e-9).contains(&u) {
                    continue;
                }
                let q = cruz(tv, e1);
                let v = punto(d, q) * inv_det;
                if v < -1e-9 || u + v > 1.0 + 1e-9 {
                    continue;
                }
                let t = punto(e2, q) * inv_det;
                if t > eps && (t < mejor || (t == mejor && (i as i64) < indice)) {
                    mejor = t;
                    indice = i as i64;
                }
            }
        }
        (mejor, indice)
    }
}

#[pymethods]
impl Bvh {
    /// BVH de `tris` (T×3×3, float64 contiguo).
    #[new]
    fn nuevo(py: Python<'_>, tris: PyReadonlyArray3<'_, f64>) -> PyResult<Self> {
        let v = tris.as_slice().map_err(|_| PyValueError::new_err("Los triángulos deben ser un arreglo float64 contiguo."))?;
        if tris.shape()[1..] != [3, 3] {
            return Err(PyValueError::new_err("Los triángulos deben tener forma (T, 3, 3)."));
        }
        if v.len() / 9 >= u32::MAX as usize {
            return Err(PyValueError::new_err("Demasiados triángulos."));
        }
        Ok(py.allow_threads(|| Bvh::desde(v)))
    }

    fn __len__(&self) -> usize {
        self.tri.p0.len()
    }

    /// (t, índice) del primer triángulo que corta cada rayo origen + t·dirección con t > `eps`; (inf, −1) si ninguno.
    /// `direcciones` con una sola fila vale para todos los rayos. Un triángulo se descarta como paralelo si
    /// |e1·(d×e2)| ≤ `det_abs` + `det_rel`·|e1×e2|.
    fn primer_choque<'py>(
        &self,
        py: Python<'py>,
        origenes: PyReadonlyArray2<'py, f64>,
        direcciones: PyReadonlyArray2<'py, f64>,
        eps: f64,
        det_abs: f64,
        det_rel: f64,
    ) -> PyResult<Choques<'py>> {
        let (o, d) = (origenes.as_slice()?, direcciones.as_slice()?);
        let n = o.len() / 3;
        if origenes.shape()[1] != 3 || direcciones.shape()[1] != 3 || (d.len() != 3 && d.len() != o.len()) {
            return Err(PyValueError::new_err("Orígenes y direcciones deben ser N×3 (o una sola dirección)."));
        }
        let salto = if d.len() == 3 { 0 } else { 3 };
        let resultado: Vec<(f64, i64)> = py.allow_threads(|| {
            (0..n)
                .map(|r| {
                    let ro = [o[3 * r], o[3 * r + 1], o[3 * r + 2]];
                    let rd = [d[salto * r], d[salto * r + 1], d[salto * r + 2]];
                    if self.nodos.is_empty() { (f64::INFINITY, -1) } else { self.primero(ro, rd, eps, det_abs, det_rel) }
                })
                .collect()
        });
        let t = PyArray1::from_iter(py, resultado.iter().map(|x| x.0));
        let i = PyArray1::from_iter(py, resultado.iter().map(|x| x.1));
        Ok((t, i))
    }
}

#[cfg(test)]
mod pruebas {
    use super::*;

    fn azar(semilla: &mut u64) -> f64 {
        *semilla = semilla.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        (*semilla >> 11) as f64 / (1u64 << 53) as f64
    }

    fn fuerza_bruta(v: &[f64], o: V, d: V, eps: f64) -> (f64, i64) {
        let (mut mejor, mut indice) = (f64::INFINITY, -1);
        for (i, t) in v.chunks_exact(9).enumerate() {
            let (a, b, c) = ([t[0], t[1], t[2]], [t[3], t[4], t[5]], [t[6], t[7], t[8]]);
            let (e1, e2) = (resta(b, a), resta(c, a));
            let p = cruz(d, e2);
            let det = punto(e1, p);
            if det.abs() <= 1e-12 {
                continue;
            }
            let tv = resta(o, a);
            let u = punto(tv, p) / det;
            let q = cruz(tv, e1);
            let w = punto(d, q) / det;
            let t = punto(e2, q) / det;
            if u >= -1e-9 && w >= -1e-9 && u + w <= 1.0 + 1e-9 && t > eps && t < mejor {
                (mejor, indice) = (t, i as i64);
            }
        }
        (mejor, indice)
    }

    #[test]
    fn igual_a_la_fuerza_bruta() {
        let mut s = 7u64;
        let v: Vec<f64> = (0..300 * 9).map(|_| azar(&mut s) * 10.0).collect();
        let bvh = Bvh::desde(&v);
        assert_eq!(bvh.tri.p0.len(), 300);
        for _ in 0..500 {
            let o = [azar(&mut s) * 14.0 - 2.0, azar(&mut s) * 14.0 - 2.0, azar(&mut s) * 14.0 - 2.0];
            let mut d = [azar(&mut s) - 0.5, azar(&mut s) - 0.5, azar(&mut s) - 0.5];
            let l = punto(d, d).sqrt();
            d = [d[0] / l, d[1] / l, d[2] / l];
            let (t1, i1) = bvh.primero(o, d, 1e-9, 1e-12, 0.0);
            let (t2, i2) = fuerza_bruta(&v, o, d, 1e-9);
            assert_eq!(i1, i2);
            assert!(t1 == t2 || (t1 - t2).abs() < 1e-12);
        }
    }

    #[test]
    fn vacio_y_sin_choque() {
        let vacio = Bvh::desde(&[]);
        assert!(vacio.nodos.is_empty());
        let uno = Bvh::desde(&[0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0]);
        assert_eq!(uno.primero([0.2, 0.2, 5.0], [0.0, 0.0, -1.0], 1e-9, 1e-12, 0.0), (5.0, 0));
        assert_eq!(uno.primero([5.0, 5.0, 5.0], [0.0, 0.0, -1.0], 1e-9, 1e-12, 0.0).1, -1);
        assert_eq!(uno.primero([0.2, 0.2, 5.0], [0.0, 0.0, 1.0], 1e-9, 1e-12, 0.0).1, -1);
        // origen justo en el borde de la caja de un eje paralelo (el vértice (1, 0)): (lo − o)·∞ es NaN
        assert_eq!(uno.primero([1.0, 0.0, 5.0], [0.0, 0.0, -1.0], 1e-9, 1e-12, 0.0), (5.0, 0));
    }
}
