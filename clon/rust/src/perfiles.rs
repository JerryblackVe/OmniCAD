//! Arreglo planar de las curvas de un boceto (BOC-28): intersecciones, grafo, lazos y caras.
//!
//! Python entrega las curvas (líneas, círculos, arcos y B-splines) y recibe, por cara, su área, centroide, las
//! curvas de su borde y los ciclos de tramos (curva, t0, t1) con los que arma la cara exacta en OpenCascade.
//! Ante cualquier cosa que no pueda certificar (tangentes en un cruce, curvas superpuestas, autocruces) devuelve
//! `Err` y Python usa el camino de referencia (`BRepAlgoAPI_Splitter`).
use numpy::ndarray::Array2;
use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::f64::consts::PI;

type P2 = [f64; 2];
const TAU: f64 = 2.0 * PI;
const SAGITA: f64 = 2e-4;
const AREA_MIN: f64 = 1e-10;
const GRADO_MAX: usize = 15;

fn hyp(a: P2) -> f64 {
    a[0].hypot(a[1])
}
fn dist(a: P2, b: P2) -> f64 {
    (a[0] - b[0]).hypot(a[1] - b[1])
}
fn cruz(a: P2, b: P2) -> f64 {
    a[0] * b[1] - a[1] * b[0]
}

struct Spl {
    p: usize,
    n: usize,
    ctrl: Vec<[f64; 3]>,
    knots: Vec<f64>,
}

impl Spl {
    fn tramo(&self, t: f64) -> usize {
        let (mut lo, mut hi) = (self.p, self.n);
        while hi - lo > 1 {
            let m = (lo + hi) / 2;
            if self.knots[m] <= t {
                lo = m;
            } else {
                hi = m;
            }
        }
        lo
    }

    fn eval(&self, t: f64) -> P2 {
        let p = self.p;
        let k = self.tramo(t);
        let mut d = [[0.0f64; 3]; GRADO_MAX + 1];
        d[..=p].copy_from_slice(&self.ctrl[k - p..=k]);
        for r in 1..=p {
            for j in (r..=p).rev() {
                let i = k - p + j;
                let den = self.knots[i + p + 1 - r] - self.knots[i];
                let a = if den.abs() < 1e-300 { 0.0 } else { (t - self.knots[i]) / den };
                let previo = d[j - 1];
                for (x, y) in d[j].iter_mut().zip(previo) {
                    *x = (1.0 - a) * y + a * *x;
                }
            }
        }
        [d[p][0] / d[p][2], d[p][1] / d[p][2]]
    }
}

enum Geo {
    Linea(P2, P2),
    Circ(P2, f64),
    Spl(Spl),
}

struct Curva {
    g: Geo,
    t0: f64,
    t1: f64,
}

impl Curva {
    fn pt(&self, t: f64) -> P2 {
        match &self.g {
            Geo::Linea(p, d) => [p[0] + t * d[0], p[1] + t * d[1]],
            Geo::Circ(c, r) => [c[0] + r * t.cos(), c[1] + r * t.sin()],
            Geo::Spl(s) => s.eval(t),
        }
    }

    fn der(&self, t: f64) -> P2 {
        match &self.g {
            Geo::Linea(_, d) => *d,
            Geo::Circ(_, r) => [-r * t.sin(), r * t.cos()],
            Geo::Spl(s) => {
                let h = 1e-6 * (self.t1 - self.t0);
                let (a, b) = ((t - h).max(self.t0), (t + h).min(self.t1));
                let (pa, pb) = (s.eval(a), s.eval(b));
                [(pb[0] - pa[0]) / (b - a), (pb[1] - pa[1]) / (b - a)]
            }
        }
    }

    /// Parámetros de corte de la poligonal que aproxima la curva (también extremos de integración exacta).
    fn trozos(&self) -> Vec<f64> {
        match &self.g {
            Geo::Linea(..) => vec![0.0, 1.0],
            Geo::Circ(_, r) => {
                let paso = 2.0 * (1.0 - (SAGITA / r).min(0.9)).acos();
                let n = (((self.t1 - self.t0) / paso).ceil() as usize).max(1);
                (0..=n).map(|i| self.t0 + (self.t1 - self.t0) * i as f64 / n as f64).collect()
            }
            Geo::Spl(s) => {
                let mut cortes = vec![self.t0];
                for k in s.p..s.n {
                    let (a, b) = (s.knots[k].max(self.t0), s.knots[k + 1].min(self.t1));
                    if b > a + 1e-14 {
                        for i in 0..4 {
                            self.biseccion(a + (b - a) * i as f64 / 4.0, a + (b - a) * (i + 1) as f64 / 4.0, 0, &mut cortes);
                        }
                    }
                }
                cortes
            }
        }
    }

    fn biseccion(&self, a: f64, b: f64, nivel: u32, cortes: &mut Vec<f64>) {
        let m = 0.5 * (a + b);
        let (pa, pb, pm) = (self.pt(a), self.pt(b), self.pt(m));
        let desvio = dist(pm, [0.5 * (pa[0] + pb[0]), 0.5 * (pa[1] + pb[1])]);
        if desvio > SAGITA && nivel < 14 {
            self.biseccion(a, m, nivel + 1, cortes);
            self.biseccion(m, b, nivel + 1, cortes);
        } else {
            cortes.push(b);
        }
    }
}

struct Cuerda {
    c: usize,
    i: usize,
    a: f64,
    b: f64,
    pa: P2,
    pb: P2,
    caja: [f64; 4],
}

/// Raíz de `A(ta) = B(tb)`. `Err` si el cruce es tangente (no se puede certificar); `Ok(None)` si no converge.
fn newton2(a: &Curva, b: &Curva, mut ta: f64, mut tb: f64) -> Result<Option<(f64, f64)>, String> {
    for _ in 0..40 {
        let (pa, pb) = (a.pt(ta), b.pt(tb));
        let f = [pa[0] - pb[0], pa[1] - pb[1]];
        let (da, db) = (a.der(ta), b.der(tb));
        let det = -da[0] * db[1] + db[0] * da[1];
        let escala = hyp(da) * hyp(db);
        if det.abs() < 1e-7 * escala {
            return if hyp(f) < 1e-6 { Err("cruce tangente".into()) } else { Ok(None) };
        }
        let (rx, ry) = (-f[0], -f[1]);
        let dta = (-rx * db[1] + db[0] * ry) / det;
        let dtb = (da[0] * ry - da[1] * rx) / det;
        ta = (ta + dta).clamp(a.t0, a.t1);
        tb = (tb + dtb).clamp(b.t0, b.t1);
        if dta.abs() * hyp(da) + dtb.abs() * hyp(db) < 1e-12 {
            let r = dist(a.pt(ta), b.pt(tb));
            return Ok(if r < 1e-9 { Some((ta, tb)) } else { None });
        }
    }
    Ok(None)
}

/// Parámetro de `c` más cercano a `q` (Gauss-Newton 1D) y su distancia.
fn proyectar(c: &Curva, q: P2, ini: f64) -> (f64, f64) {
    let mut t = ini.clamp(c.t0, c.t1);
    for _ in 0..50 {
        let (p, d) = (c.pt(t), c.der(t));
        let n2 = d[0] * d[0] + d[1] * d[1];
        if n2 < 1e-300 {
            break;
        }
        let dt = -((p[0] - q[0]) * d[0] + (p[1] - q[1]) * d[1]) / n2;
        t = (t + dt).clamp(c.t0, c.t1);
        if dt.abs() * n2.sqrt() < 1e-13 {
            break;
        }
    }
    (t, dist(c.pt(t), q))
}

const GL8X: [f64; 4] = [0.1834346424956498, 0.525_532_409_916_329, 0.7966664774136267, 0.9602898564975363];
const GL8W: [f64; 4] = [0.362_683_783_378_362, 0.3137066458778873, 0.2223810344533745, 0.1012285362903763];

/// (área, ∫(x-ox) dA, ∫(y-oy) dA) del tramo [t0, t1] recorrido hacia adelante (Green sobre el borde). Los momentos
/// van respecto de `o`, un punto de la cara: respecto del origen, una cara chica y lejana pierde dígitos.
fn integrar(c: &Curva, t0: f64, t1: f64, o: P2) -> [f64; 3] {
    let mut cortes = vec![t0];
    match &c.g {
        Geo::Linea(..) => cortes.push(t1),
        Geo::Circ(..) => {
            let n = (((t1 - t0).abs() / (PI / 4.0)).ceil() as usize).max(1);
            cortes.extend((1..=n).map(|i| t0 + (t1 - t0) * i as f64 / n as f64));
        }
        Geo::Spl(s) => {
            for k in s.p..s.n {
                for i in 1..4 {
                    let t = s.knots[k] + (s.knots[k + 1] - s.knots[k]) * i as f64 / 4.0;
                    if t > t0 && t < t1 {
                        cortes.push(t);
                    }
                }
                let t = s.knots[k + 1];
                if t > t0 && t < t1 {
                    cortes.push(t);
                }
            }
            cortes.push(t1);
            cortes.sort_by(|a, b| a.total_cmp(b));
            cortes.dedup_by(|a, b| (*a - *b).abs() < 1e-15);
        }
    }
    let mut r = [0.0; 3];
    for w in cortes.windows(2) {
        let (a, b) = (w[0], w[1]);
        let (m, h) = (0.5 * (a + b), 0.5 * (b - a));
        for (x, peso) in GL8X.iter().zip(GL8W.iter()) {
            for s in [-1.0, 1.0] {
                let t = m + s * x * h;
                let (p, d) = (c.pt(t), c.der(t));
                let (x, y, k) = (p[0] - o[0], p[1] - o[1], peso * h);
                r[0] += 0.5 * (x * d[1] - y * d[0]) * k;
                r[1] += 0.5 * x * x * d[1] * k;
                r[2] -= 0.5 * y * y * d[0] * k;
            }
        }
    }
    r
}

/// Caja envolvente exacta [xmin, ymin, xmax, ymax] del tramo [t0, t1]: extremos, ejes del círculo y extremos de los
/// B-splines (refinados por sección áurea alrededor de la mejor muestra de la poligonal).
fn caja_pieza(c: &Curva, t0: f64, t1: f64) -> [f64; 4] {
    let mut b = [f64::MAX, f64::MAX, f64::MIN, f64::MIN];
    let mut sumar = |p: P2| {
        b = [b[0].min(p[0]), b[1].min(p[1]), b[2].max(p[0]), b[3].max(p[1])];
    };
    sumar(c.pt(t0));
    sumar(c.pt(t1));
    match &c.g {
        Geo::Linea(..) => {}
        Geo::Circ(..) => {
            let mut k = (t0 / (PI / 2.0)).ceil();
            while k * PI / 2.0 < t1 {
                sumar(c.pt(k * PI / 2.0));
                k += 1.0;
            }
        }
        Geo::Spl(_) => {
            let mut ts = vec![t0];
            ts.extend(c.trozos().into_iter().filter(|&t| t > t0 && t < t1));
            ts.push(t1);
            let pts: Vec<P2> = ts.iter().map(|&t| c.pt(t)).collect();
            for eje in 0..2 {
                for signo in [1.0, -1.0] {
                    let k = (0..pts.len()).max_by(|&i, &j| (signo * pts[i][eje]).total_cmp(&(signo * pts[j][eje]))).unwrap();
                    let (mut a, mut z) = (ts[k.saturating_sub(1)], ts[(k + 1).min(ts.len() - 1)]);
                    for _ in 0..60 {
                        let (m1, m2) = (a + 0.381_966 * (z - a), a + 0.618_034 * (z - a));
                        if signo * c.pt(m1)[eje] < signo * c.pt(m2)[eje] {
                            a = m1;
                        } else {
                            z = m2;
                        }
                    }
                    sumar(c.pt(0.5 * (a + z)));
                }
            }
        }
    }
    b
}

struct Pieza {
    c: usize,
    t0: f64,
    t1: f64,
    va: usize,
    vb: usize,
}

fn buscar(uf: &mut [usize], mut i: usize) -> usize {
    while uf[i] != i {
        uf[i] = uf[uf[i]];
        i = uf[i];
    }
    i
}

fn unir(uf: &mut [usize], a: usize, b: usize) {
    let (ra, rb) = (buscar(uf, a), buscar(uf, b));
    if ra != rb {
        uf[ra.max(rb)] = ra.min(rb);
    }
}

struct Salida {
    verts: Vec<P2>,
    piezas: Vec<Pieza>,
    area: Vec<f64>,
    cen: Vec<P2>,
    caja: Vec<[f64; 4]>,
    firma_ptr: Vec<i64>,
    firma: Vec<i64>,
    ciclo_ptr: Vec<i64>,
    semi_ptr: Vec<i64>,
    semi: Vec<i64>,
}

/// Ciclos simples de un lazo (secuencia de semiaristas). Los pares de ida y vuelta por la misma pieza
/// (colgantes e istmos) se descartan.
fn ciclos(lazo: &[usize], dest: impl Fn(usize) -> usize, origen: impl Fn(usize) -> usize, area_h: &[f64]) -> Vec<(Vec<usize>, f64)> {
    let mut salida = Vec::new();
    let mut camino: Vec<usize> = Vec::new();
    let mut vertices: Vec<usize> = vec![origen(lazo[0])];
    for &h in lazo {
        camino.push(h);
        let v = dest(h);
        if let Some(pos) = vertices.iter().rposition(|&x| x == v) {
            let ciclo: Vec<usize> = camino.split_off(pos);
            vertices.truncate(pos + 1);
            if !(ciclo.len() == 2 && ciclo[0] ^ 1 == ciclo[1]) {
                let a = ciclo.iter().map(|&x| area_h[x]).sum();
                salida.push((ciclo, a));
            }
        } else {
            vertices.push(v);
        }
    }
    salida
}

/// `gap` es la tolerancia del Splitter de referencia: los vértices se funden mucho más justo (1e-8) para que las áreas
/// salgan exactas, y un extremo libre a menos de `gap` de otra curva (que el Splitter cerraría) se delega al respaldo.
fn calcular(curvas: &[Curva], gap: f64) -> Result<Salida, String> {
    let tol = gap.min(1e-8);
    let n = curvas.len();
    let extremos: Vec<(P2, P2)> = curvas.iter().map(|c| (c.pt(c.t0), c.pt(c.t1))).collect();

    // --- cuerdas
    let mut cuerdas: Vec<Cuerda> = Vec::new();
    let mut ncuerdas = vec![0usize; n];
    for (k, c) in curvas.iter().enumerate() {
        let cortes = c.trozos();
        ncuerdas[k] = cortes.len() - 1;
        for (i, w) in cortes.windows(2).enumerate() {
            let (pa, pb) = (c.pt(w[0]), c.pt(w[1]));
            cuerdas.push(Cuerda {
                c: k,
                i,
                a: w[0],
                b: w[1],
                pa,
                pb,
                caja: [pa[0].min(pb[0]), pa[1].min(pb[1]), pa[0].max(pb[0]), pa[1].max(pb[1])],
            });
        }
    }
    // círculos repetidos: las cuerdas de dos copias no son colineales y el cruce no se vería
    let mut vistos: HashMap<(i64, i64, i64), usize> = HashMap::new();
    for (k, c) in curvas.iter().enumerate() {
        if let Geo::Circ(ce, r) = c.g {
            let clave = ((ce[0] / tol).round() as i64, (ce[1] / tol).round() as i64, (r / tol).round() as i64);
            if let Some(&otro) = vistos.get(&clave) {
                if otro != k {
                    return Err("círculos superpuestos".into());
                }
            }
            vistos.insert(clave, k);
        }
    }

    // --- eventos: (curva, t, punto)
    let mut ev: Vec<(usize, f64, P2)> = Vec::new();
    for (k, c) in curvas.iter().enumerate() {
        ev.push((k, c.t0, extremos[k].0));
        ev.push((k, c.t1, extremos[k].1));
    }
    let mut orden: Vec<usize> = (0..cuerdas.len()).collect();
    orden.sort_by(|&a, &b| cuerdas[a].caja[0].total_cmp(&cuerdas[b].caja[0]));
    let cerca = 4.0 * SAGITA;
    let holgura = tol + 2.0 * SAGITA; // la curva real se aparta de su cuerda hasta SAGITA
    for ii in 0..orden.len() {
        let ca = &cuerdas[orden[ii]];
        for &j in &orden[ii + 1..] {
            let cb = &cuerdas[j];
            if cb.caja[0] > ca.caja[2] + holgura {
                break;
            }
            if cb.caja[1] > ca.caja[3] + holgura || cb.caja[3] < ca.caja[1] - holgura {
                continue;
            }
            let (a, b) = (&curvas[ca.c], &curvas[cb.c]);
            let d1 = [ca.pb[0] - ca.pa[0], ca.pb[1] - ca.pa[1]];
            let d2 = [cb.pb[0] - cb.pa[0], cb.pb[1] - cb.pa[1]];
            let (l1, l2) = (hyp(d1), hyp(d2));
            if l1 < 1e-12 || l2 < 1e-12 {
                continue;
            }
            let misma = ca.c == cb.c;
            if misma {
                let (i, j2) = (ca.i.min(cb.i), ca.i.max(cb.i));
                if j2 - i <= 1 || (j2 - i == ncuerdas[ca.c] - 1 && a.t1 - a.t0 > TAU - 1e-9) {
                    continue;
                }
            }
            let cr = cruz(d1, d2);
            let qp = [cb.pa[0] - ca.pa[0], cb.pa[1] - ca.pa[1]];
            if cr.abs() <= 1e-9 * l1 * l2 {
                // paralelas: solo preocupan si son la misma recta y se solapan
                if cruz(qp, d1).abs() / l1 <= tol {
                    let (s0, s1) = ((qp[0] * d1[0] + qp[1] * d1[1]) / l1, ((cb.pb[0] - ca.pa[0]) * d1[0] + (cb.pb[1] - ca.pa[1]) * d1[1]) / l1);
                    if s0.min(s1).max(0.0) + tol < s0.max(s1).min(l1) {
                        return Err("curvas superpuestas".into());
                    }
                }
                continue;
            }
            let s = cruz(qp, d2) / cr;
            let u = cruz(qp, d1) / cr;
            // la curva real se aparta de su cuerda hasta SAGITA: se amplía el margen por eso (y por el ángulo del cruce)
            let (sa, sb) = (if matches!(a.g, Geo::Linea(..)) { 0.0 } else { SAGITA }, if matches!(b.g, Geo::Linea(..)) { 0.0 } else { SAGITA });
            let (ms, mu) = if sa + sb == 0.0 { (tol / l1, tol / l2) } else { (((tol + 2.0 * sb) * l2 / cr.abs()).min(1.0), ((tol + 2.0 * sa) * l1 / cr.abs()).min(1.0)) };
            if s < -ms || s > 1.0 + ms || u < -mu || u > 1.0 + mu {
                continue;
            }
            if misma {
                return Err("curva que se corta a sí misma".into());
            }
            let g = [ca.pa[0] + s.clamp(0.0, 1.0) * d1[0], ca.pa[1] + s.clamp(0.0, 1.0) * d1[1]];
            let ta0 = ca.a + s.clamp(0.0, 1.0) * (ca.b - ca.a);
            let tb0 = cb.a + u.clamp(0.0, 1.0) * (cb.b - cb.a);
            let (ea, eb) = (extremos[ca.c], extremos[cb.c]);
            let cerca_a = if dist(g, ea.0) <= cerca { Some((a.t0, ea.0)) } else if dist(g, ea.1) <= cerca { Some((a.t1, ea.1)) } else { None };
            let cerca_b = if dist(g, eb.0) <= cerca { Some((b.t0, eb.0)) } else if dist(g, eb.1) <= cerca { Some((b.t1, eb.1)) } else { None };
            if let (Some((ta, pa)), Some((tb, pb))) = (cerca_a, cerca_b) {
                if dist(pa, pb) <= 2.0 * tol {
                    ev.push((ca.c, ta, pa));
                    ev.push((cb.c, tb, pb));
                    continue;
                }
            }
            if let Some((ta, pa)) = cerca_a {
                let (tb, d) = proyectar(b, pa, tb0);
                if d <= 2.0 * tol {
                    ev.push((ca.c, ta, pa));
                    ev.push((cb.c, tb, pa));
                    continue;
                }
            }
            if let Some((tb, pb)) = cerca_b {
                let (ta, d) = proyectar(a, pb, ta0);
                if d <= 2.0 * tol {
                    ev.push((cb.c, tb, pb));
                    ev.push((ca.c, ta, pb));
                    continue;
                }
            }
            let (ta, tb) = if matches!((&a.g, &b.g), (Geo::Linea(..), Geo::Linea(..))) {
                (ta0, tb0)
            } else {
                match newton2(a, b, ta0, tb0)? {
                    Some(r) => r,
                    None => continue,
                }
            };
            let p = a.pt(ta);
            let fuera = |c: &Curva, t: f64| {
                let h = hyp(c.der(t)).max(1e-300);
                ((t - c.t0).min(0.0).abs().max((t - c.t1).max(0.0)) * h) > tol
            };
            if fuera(a, ta) || fuera(b, tb) {
                continue;
            }
            ev.push((ca.c, ta, p));
            ev.push((cb.c, tb, p));
        }
    }

    // --- vértices: se funden los eventos a menos de `tol`
    let mut uf: Vec<usize> = (0..ev.len()).collect();
    let mut celdas: HashMap<(i64, i64), Vec<usize>> = HashMap::new();
    let celda = tol.max(1e-9);
    for (i, e) in ev.iter().enumerate() {
        let (cx, cy) = ((e.2[0] / celda).floor() as i64, (e.2[1] / celda).floor() as i64);
        for dx in -1..=1 {
            for dy in -1..=1 {
                if let Some(v) = celdas.get(&(cx + dx, cy + dy)) {
                    for &j in v {
                        if dist(ev[j].2, e.2) <= tol {
                            unir(&mut uf, i, j);
                        }
                    }
                }
            }
        }
        celdas.entry((cx, cy)).or_default().push(i);
    }
    let mut vid = vec![usize::MAX; ev.len()];
    let mut raiz_a_vertice: HashMap<usize, usize> = HashMap::new();
    let mut verts: Vec<P2> = Vec::new();
    for i in 0..ev.len() {
        let r = buscar(&mut uf, i);
        let v = *raiz_a_vertice.entry(r).or_insert_with(|| {
            verts.push(ev[i].2);
            verts.len() - 1
        });
        vid[i] = v;
    }

    // --- piezas
    let mut por_curva: Vec<Vec<usize>> = vec![Vec::new(); n];
    for (i, e) in ev.iter().enumerate() {
        por_curva[e.0].push(i);
    }
    let mut piezas: Vec<Pieza> = Vec::new();
    for (k, idx) in por_curva.iter_mut().enumerate() {
        idx.sort_by(|&a, &b| ev[a].1.total_cmp(&ev[b].1));
        for w in idx.windows(2) {
            let (a, b) = (w[0], w[1]);
            if ev[b].1 <= ev[a].1 {
                continue;
            }
            let (va, vb) = (vid[a], vid[b]);
            if va == vb && dist(curvas[k].pt(0.5 * (ev[a].1 + ev[b].1)), verts[va]) <= 2.0 * tol {
                continue;
            }
            piezas.push(Pieza { c: k, t0: ev[a].1, t1: ev[b].1, va, vb });
        }
    }
    let np = piezas.len();
    let origen = |h: usize| if h & 1 == 0 { piezas[h >> 1].va } else { piezas[h >> 1].vb };
    let destino = |h: usize| origen(h ^ 1);

    // --- orden angular de las semiaristas en cada vértice
    let mut clave: Vec<(f64, f64)> = Vec::with_capacity(2 * np);
    for h in 0..2 * np {
        let pz = &piezas[h >> 1];
        let c = &curvas[pz.c];
        let (d, t_sec) = if h & 1 == 0 {
            (c.der(pz.t0), pz.t0 + 0.1 * (pz.t1 - pz.t0))
        } else {
            let d = c.der(pz.t1);
            ([-d[0], -d[1]], pz.t1 - 0.1 * (pz.t1 - pz.t0))
        };
        let o = verts[origen(h)];
        let q = c.pt(t_sec);
        let sec = [q[0] - o[0], q[1] - o[1]];
        let d = if hyp(d) < 1e-12 { sec } else { d };
        clave.push((d[1].atan2(d[0]), sec[1].atan2(sec[0])));
    }
    let mut ady: Vec<Vec<usize>> = vec![Vec::new(); verts.len()];
    for h in 0..2 * np {
        ady[origen(h)].push(h);
    }
    let mut pos = vec![0usize; 2 * np];
    for lista in ady.iter_mut() {
        lista.sort_by(|&a, &b| {
            let (ka, kb) = (clave[a], clave[b]);
            if (ka.0 - kb.0).abs() > 1e-9 { ka.0.total_cmp(&kb.0) } else { ka.1.total_cmp(&kb.1) }
        });
        for (i, &h) in lista.iter().enumerate() {
            pos[h] = i;
        }
        for w in lista.windows(2) {
            let (ka, kb) = (clave[w[0]], clave[w[1]]);
            if (ka.0 - kb.0).abs() < 1e-12 && (ka.1 - kb.1).abs() < 1e-12 && piezas[w[0] >> 1].c != piezas[w[1] >> 1].c {
                return Err("curvas tangentes superpuestas".into());
            }
        }
    }
    for (v, lista) in ady.iter().enumerate() {
        if lista.len() != 1 {
            continue;
        }
        let (p, propia, margen) = (verts[v], piezas[lista[0] >> 1].c, gap + SAGITA);
        for c in cuerdas.iter().filter(|c| c.c != propia) {
            if p[0] < c.caja[0] - margen || p[0] > c.caja[2] + margen || p[1] < c.caja[1] - margen || p[1] > c.caja[3] + margen {
                continue;
            }
            let d = [c.pb[0] - c.pa[0], c.pb[1] - c.pa[1]];
            let l2 = d[0] * d[0] + d[1] * d[1];
            let t = if l2 > 0.0 { (((p[0] - c.pa[0]) * d[0] + (p[1] - c.pa[1]) * d[1]) / l2).clamp(0.0, 1.0) } else { 0.0 };
            let mut dd = dist(p, [c.pa[0] + t * d[0], c.pa[1] + t * d[1]]);
            if dd > margen {
                continue;
            }
            if !matches!(curvas[c.c].g, Geo::Linea(..)) {
                dd = proyectar(&curvas[c.c], p, 0.5 * (c.a + c.b)).1;
            }
            if dd > 2.0 * tol && dd <= gap {
                return Err("extremo libre casi unido a otra curva".into());
            }
        }
    }
    let siguiente = |h: usize| {
        let v = destino(h);
        let t = h ^ 1;
        let l = &ady[v];
        l[(pos[t] + l.len() - 1) % l.len()]
    };

    // --- lazos
    let mut lazo_de = vec![usize::MAX; 2 * np];
    let mut lazos: Vec<Vec<usize>> = Vec::new();
    for h0 in 0..2 * np {
        if lazo_de[h0] != usize::MAX {
            continue;
        }
        let mut l = Vec::new();
        let mut h = h0;
        loop {
            lazo_de[h] = lazos.len();
            l.push(h);
            h = siguiente(h);
            if h == h0 {
                break;
            }
            if l.len() > 2 * np {
                return Err("lazo que no cierra".into());
            }
        }
        lazos.push(l);
    }
    let nl = lazos.len();
    // --- integrales por semiarista, respecto del primer vértice de su lazo
    let ref_l: Vec<P2> = lazos.iter().map(|l| verts[origen(l[0])]).collect();
    let mom_h: Vec<[f64; 3]> = (0..2 * np)
        .map(|h| {
            let pz = &piezas[h >> 1];
            let m = integrar(&curvas[pz.c], pz.t0, pz.t1, ref_l[lazo_de[h]]);
            let signo = if h & 1 == 0 { 1.0 } else { -1.0 };
            [signo * m[0], signo * m[1], signo * m[2]]
        })
        .collect();
    let area_h: Vec<f64> = mom_h.iter().map(|m| m[0]).collect();
    let mom_l: Vec<[f64; 3]> = lazos
        .iter()
        .map(|l| {
            let mut m = [0.0; 3];
            for &h in l {
                for k in 0..3 {
                    m[k] += mom_h[h][k];
                }
            }
            m
        })
        .collect();

    // --- componentes conexas
    let mut ufv: Vec<usize> = (0..verts.len()).collect();
    for pz in &piezas {
        unir(&mut ufv, pz.va, pz.vb);
    }
    let comp_de_lazo: Vec<usize> = lazos.iter().map(|l| buscar(&mut ufv, origen(l[0]))).collect();
    // lazo exterior de cada componente (el de menor área) y si tiene ciclos propios
    let mut exterior: HashMap<usize, usize> = HashMap::new();
    for l in 0..nl {
        let e = exterior.entry(comp_de_lazo[l]).or_insert(l);
        if mom_l[l][0] < mom_l[*e][0] {
            *e = l;
        }
    }
    let es_cara: Vec<bool> = (0..nl).map(|l| mom_l[l][0] > AREA_MIN).collect();
    let caras_l: Vec<usize> = (0..nl).filter(|&l| es_cara[l]).collect();

    // --- a qué cara pertenece cada componente suelta (hueco o árbol dentro de una región)
    let mut huecos: HashMap<usize, Vec<usize>> = HashMap::new(); // cara -> lazos exteriores de componentes con ciclos
    let mut arboles: HashMap<usize, Vec<usize>> = HashMap::new(); // cara -> componentes sin ciclos
    if exterior.len() > 1 {
        let poligono = |l: usize| -> Vec<P2> {
            let mut pts = Vec::new();
            for &h in &lazos[l] {
                let pz = &piezas[h >> 1];
                let c = &curvas[pz.c];
                let mut ts: Vec<f64> = c.trozos().into_iter().filter(|&t| t > pz.t0 && t < pz.t1).collect();
                ts.insert(0, pz.t0);
                ts.push(pz.t1);
                if h & 1 == 1 {
                    ts.reverse();
                }
                pts.extend(ts[..ts.len() - 1].iter().map(|&t| c.pt(t)));
            }
            pts
        };
        let polis: Vec<(Vec<P2>, [f64; 4])> = caras_l
            .iter()
            .map(|&l| {
                let p = poligono(l);
                let caja = p.iter().fold([f64::MAX, f64::MAX, f64::MIN, f64::MIN], |b, q| [b[0].min(q[0]), b[1].min(q[1]), b[2].max(q[0]), b[3].max(q[1])]);
                (p, caja)
            })
            .collect();
        let mut sueltas: Vec<(usize, usize)> = exterior.iter().map(|(&c, &e)| (c, e)).collect();
        sueltas.sort_unstable();
        for (comp, ext) in sueltas {
            let q = verts[origen(lazos[ext][0])];
            let mut mejor: Option<usize> = None;
            for (i, &l) in caras_l.iter().enumerate() {
                if comp_de_lazo[l] == comp {
                    continue;
                }
                let (p, caja) = &polis[i];
                if q[0] < caja[0] || q[0] > caja[2] || q[1] < caja[1] || q[1] > caja[3] {
                    continue;
                }
                if mejor.is_some_and(|m| mom_l[m][0] <= mom_l[l][0]) {
                    continue;
                }
                let mut dentro = false;
                let mut j = p.len() - 1;
                for i2 in 0..p.len() {
                    if (p[i2][1] > q[1]) != (p[j][1] > q[1]) && q[0] < (p[j][0] - p[i2][0]) * (q[1] - p[i2][1]) / (p[j][1] - p[i2][1]) + p[i2][0] {
                        dentro = !dentro;
                    }
                    j = i2;
                }
                if dentro {
                    mejor = Some(l);
                }
            }
            if let Some(l) = mejor {
                if mom_l[ext][0] < -AREA_MIN {
                    huecos.entry(l).or_default().push(ext);
                } else {
                    arboles.entry(l).or_default().push(comp);
                }
            }
        }
    }

    // --- caras
    let cajas: Vec<[f64; 4]> = piezas.iter().map(|pz| caja_pieza(&curvas[pz.c], pz.t0, pz.t1)).collect();
    let mut sal = Salida { verts, piezas: Vec::new(), area: Vec::new(), cen: Vec::new(), caja: Vec::new(), firma_ptr: vec![0], firma: Vec::new(), ciclo_ptr: vec![0], semi_ptr: vec![0], semi: Vec::new() };
    let mut curvas_de_comp: HashMap<usize, Vec<i64>> = HashMap::new();
    for pz in &piezas {
        curvas_de_comp.entry(buscar(&mut ufv, pz.va)).or_default().push(pz.c as i64);
    }
    for &l in &caras_l {
        let mut m = mom_l[l];
        let mut curvas_cara: Vec<i64> = lazos[l].iter().map(|&h| piezas[h >> 1].c as i64).collect();
        let mut cics: Vec<(Vec<usize>, f64)> = ciclos(&lazos[l], destino, origen, &area_h);
        cics.sort_by(|a, b| b.1.total_cmp(&a.1));
        if let Some(hs) = huecos.get(&l) {
            for &ext in hs {
                let e = mom_l[ext];
                m[0] += e[0];
                m[1] += e[1] + e[0] * (ref_l[ext][0] - ref_l[l][0]);
                m[2] += e[2] + e[0] * (ref_l[ext][1] - ref_l[l][1]);
                curvas_cara.extend(lazos[ext].iter().map(|&h| piezas[h >> 1].c as i64));
                cics.extend(ciclos(&lazos[ext], destino, origen, &area_h));
            }
        }
        if let Some(cs) = arboles.get(&l) {
            for &comp in cs {
                curvas_cara.extend(&curvas_de_comp[&comp]);
            }
        }
        if cics.is_empty() || cics[0].1 <= 0.0 {
            return Err("cara sin contorno".into());
        }
        curvas_cara.sort_unstable();
        curvas_cara.dedup();
        sal.area.push(m[0]);
        sal.cen.push([ref_l[l][0] + m[1] / m[0], ref_l[l][1] + m[2] / m[0]]);
        sal.caja.push(lazos[l].iter().fold([f64::MAX, f64::MAX, f64::MIN, f64::MIN], |b, &h| {
            let c = cajas[h >> 1];
            [b[0].min(c[0]), b[1].min(c[1]), b[2].max(c[2]), b[3].max(c[3])]
        }));
        sal.firma.extend(curvas_cara);
        sal.firma_ptr.push(sal.firma.len() as i64);
        for (c, _a) in cics {
            sal.semi.extend(c.into_iter().map(|h| h as i64));
            sal.semi_ptr.push(sal.semi.len() as i64);
        }
        sal.ciclo_ptr.push(sal.semi_ptr.len() as i64 - 1);
    }
    sal.piezas = piezas;
    Ok(sal)
}

fn a_curva(tipo: i64, par: &[f64], info: &[i64], polos: &[f64], pesos: &[f64], nudos: &[f64]) -> Result<Curva, String> {
    Ok(match tipo {
        0 => Curva { g: Geo::Linea([par[0], par[1]], [par[2] - par[0], par[3] - par[1]]), t0: 0.0, t1: 1.0 },
        1 => Curva { g: Geo::Circ([par[0], par[1]], par[2]), t0: 0.0, t1: TAU },
        2 => Curva { g: Geo::Circ([par[0], par[1]], par[2]), t0: par[3], t1: par[4] },
        3 => {
            let (p, off, m, offk) = (info[0] as usize, info[1] as usize, info[2] as usize, info[3] as usize);
            if !(1..=GRADO_MAX).contains(&p) || m < p + 1 {
                return Err("spline inválida".into());
            }
            let knots = nudos[offk..offk + m + p + 1].to_vec();
            if knots.windows(2).any(|w| w[1] < w[0]) || knots[m] <= knots[p] {
                return Err("nudos inválidos".into());
            }
            let ctrl = (0..m).map(|i| [polos[2 * (off + i)] * pesos[off + i], polos[2 * (off + i) + 1] * pesos[off + i], pesos[off + i]]).collect();
            let (t0, t1) = (knots[p], knots[m]);
            Curva { g: Geo::Spl(Spl { p, n: m, ctrl, knots }), t0, t1 }
        }
        _ => return Err("tipo de curva no soportado".into()),
    })
}

type Retorno<'py> = (
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray2<i64>>,
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray1<i64>>,
    Bound<'py, PyArray1<i64>>,
    Bound<'py, PyArray1<i64>>,
    Bound<'py, PyArray1<i64>>,
    Bound<'py, PyArray1<i64>>,
    Bound<'py, PyArray2<f64>>,
);

/// Arreglo planar de las curvas de un boceto. Devuelve (vértices, piezas (curva, va, vb), piezas t, áreas, centroides,
/// firma_ptr, firma, ciclo_ptr, semi_ptr, semiaristas, cajas). Una semiarista `h` es la pieza `h >> 1`, hacia adelante si `h` es par.
#[pyfunction]
#[pyo3(signature = (tipos, params, info, polos, pesos, nudos, tolerancia))]
#[allow(clippy::too_many_arguments)]
pub fn arreglo_planar<'py>(
    py: Python<'py>,
    tipos: PyReadonlyArray1<'py, i64>,
    params: PyReadonlyArray2<'py, f64>,
    info: PyReadonlyArray2<'py, i64>,
    polos: PyReadonlyArray2<'py, f64>,
    pesos: PyReadonlyArray1<'py, f64>,
    nudos: PyReadonlyArray1<'py, f64>,
    tolerancia: f64,
) -> PyResult<Retorno<'py>> {
    let (tipos, params, info) = (tipos.as_array(), params.as_array(), info.as_array());
    let (polos, pesos, nudos) = (polos.as_slice()?, pesos.as_slice()?, nudos.as_slice()?);
    if params.ncols() != 6 || info.ncols() != 4 || params.nrows() != tipos.len() || info.nrows() != tipos.len() || !(1e-9..=1e-2).contains(&tolerancia) {
        return Err(PyValueError::new_err("dimensiones inválidas"));
    }
    let curvas: Result<Vec<Curva>, String> = (0..tipos.len())
        .map(|i| {
            let (par, inf) = (params.row(i).to_vec(), info.row(i).to_vec());
            if inf[0] > 0 && (inf[1] < 0 || (inf[1] + inf[2]) as usize * 2 > polos.len() || (inf[1] + inf[2]) as usize > pesos.len() || (inf[3] + inf[2] + inf[0] + 1) as usize > nudos.len()) {
                return Err("índices de spline fuera de rango".to_string());
            }
            a_curva(tipos[i], &par, &inf, polos, pesos, nudos)
        })
        .collect();
    let curvas = curvas.map_err(PyValueError::new_err)?;
    let s = py.allow_threads(|| calcular(&curvas, tolerancia)).map_err(PyValueError::new_err)?;
    let nv = s.verts.len();
    let verts = Array2::from_shape_vec((nv, 2), s.verts.iter().flatten().copied().collect()).unwrap();
    let np = s.piezas.len();
    let pz_i = Array2::from_shape_vec((np, 3), s.piezas.iter().flat_map(|p| [p.c as i64, p.va as i64, p.vb as i64]).collect()).unwrap();
    let pz_t = Array2::from_shape_vec((np, 2), s.piezas.iter().flat_map(|p| [p.t0, p.t1]).collect()).unwrap();
    let nf = s.area.len();
    let cen = Array2::from_shape_vec((nf, 2), s.cen.iter().flatten().copied().collect()).unwrap();
    let caja = Array2::from_shape_vec((nf, 4), s.caja.iter().flatten().copied().collect()).unwrap();
    Ok((
        verts.into_pyarray(py),
        pz_i.into_pyarray(py),
        pz_t.into_pyarray(py),
        s.area.into_pyarray(py),
        cen.into_pyarray(py),
        s.firma_ptr.into_pyarray(py),
        s.firma.into_pyarray(py),
        s.ciclo_ptr.into_pyarray(py),
        s.semi_ptr.into_pyarray(py),
        s.semi.into_pyarray(py),
        caja.into_pyarray(py),
    ))
}

#[cfg(test)]
mod pruebas {
    use super::*;

    fn linea(a: P2, b: P2) -> Curva {
        Curva { g: Geo::Linea(a, [b[0] - a[0], b[1] - a[1]]), t0: 0.0, t1: 1.0 }
    }

    #[test]
    fn cuadrado_con_diagonal_da_dos_caras() {
        let c = vec![linea([0., 0.], [1., 0.]), linea([1., 0.], [1., 1.]), linea([1., 1.], [0., 1.]), linea([0., 1.], [0., 0.]), linea([0., 0.], [1., 1.])];
        let s = calcular(&c, 1e-4).unwrap();
        assert_eq!(s.area.len(), 2);
        assert!((s.area.iter().sum::<f64>() - 1.0).abs() < 1e-12);
    }

    #[test]
    fn circulo_dentro_de_cuadrado_da_anillo_y_disco() {
        let mut c: Vec<Curva> = vec![linea([-2., -2.], [2., -2.]), linea([2., -2.], [2., 2.]), linea([2., 2.], [-2., 2.]), linea([-2., 2.], [-2., -2.])];
        c.push(Curva { g: Geo::Circ([0., 0.], 1.0), t0: 0.0, t1: TAU });
        let s = calcular(&c, 1e-4).unwrap();
        let mut a = s.area.clone();
        a.sort_by(|x, y| x.total_cmp(y));
        assert!((a[0] - PI).abs() < 1e-9 && (a[1] - (16.0 - PI)).abs() < 1e-9, "{a:?}");
    }

    #[test]
    fn circulo_cortado_por_recta() {
        let c = vec![Curva { g: Geo::Circ([0., 0.], 10.0), t0: 0.0, t1: TAU }, linea([-20., 4.], [20., 4.])];
        let s = calcular(&c, 1e-4).unwrap();
        assert_eq!(s.area.len(), 2);
        assert!((s.area.iter().sum::<f64>() - PI * 100.0).abs() < 1e-8);
    }
}
