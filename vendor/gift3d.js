// Новогодний подарок в 3D (three.js): коробка со снежинками, атласный бант, снег, свет изнутри.
// create(el) -> {tap(p), reveal(), destroy(), anchor()}; всё движение - пружины в одном цикле кадров.
import * as T from "./three.module.min.js";

function canvasTex(w, h, draw) {
  const c = document.createElement("canvas"); c.width = w; c.height = h; draw(c.getContext("2d"), w, h);
  const t = new T.CanvasTexture(c); t.colorSpace = T.SRGBColorSpace; t.anisotropy = 4; return t;
}
function flake(g, x, y, r, a) {
  g.save(); g.translate(x, y); g.rotate(a); g.strokeStyle = "rgba(255,255,255,.85)"; g.lineWidth = r * .16; g.lineCap = "round";
  for (let i = 0; i < 6; i++) { g.rotate(Math.PI / 3); g.beginPath(); g.moveTo(0, 0); g.lineTo(0, -r); g.moveTo(0, -r * .55); g.lineTo(r * .25, -r * .78); g.moveTo(0, -r * .55); g.lineTo(-r * .25, -r * .78); g.stroke(); }
  g.restore();
}
function paper(g, w, h, band, cross) {
  const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, "#3C8EE6"); gr.addColorStop(1, "#1C56A6"); g.fillStyle = gr; g.fillRect(0, 0, w, h);
  let k = 0; for (let y = 30; y < h; y += 70) for (let x = (k++ % 2 ? 20 : 55); x < w; x += 70) flake(g, x, y, 13 + (x * y) % 7, (x + y) / 40);
  g.fillStyle = "rgba(255,255,255,.55)"; for (let i = 0; i < 90; i++) { g.beginPath(); g.arc((i * 97) % w, (i * 53) % h, 2.2, 0, 7); g.fill(); }
  const rib = (vert) => {
    const bw = w * .16, gx = vert ? g.createLinearGradient(w / 2 - bw / 2, 0, w / 2 + bw / 2, 0) : g.createLinearGradient(0, h / 2 - bw / 2, 0, h / 2 + bw / 2);
    gx.addColorStop(0, "#9E0F19"); gx.addColorStop(.3, "#E3242E"); gx.addColorStop(.5, "#FF7178"); gx.addColorStop(.7, "#E3242E"); gx.addColorStop(1, "#9E0F19");
    g.fillStyle = gx; vert ? g.fillRect(w / 2 - bw / 2, 0, bw, h) : g.fillRect(0, h / 2 - bw / 2, w, bw);
  };
  if (band) rib(true); if (cross) { rib(true); rib(false); }
}
const spriteTex = () => canvasTex(64, 64, (g) => { const r = g.createRadialGradient(32, 32, 0, 32, 32, 32); r.addColorStop(0, "rgba(255,255,255,1)"); r.addColorStop(.35, "rgba(255,255,255,.75)"); r.addColorStop(1, "rgba(255,255,255,0)"); g.fillStyle = r; g.fillRect(0, 0, 64, 64); });

export function create(el) {
  const W = el.clientWidth || innerWidth, H = el.clientHeight || innerHeight;
  const R = new T.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  R.setPixelRatio(Math.min(devicePixelRatio || 1, 1.75)); R.setSize(W, H); R.toneMapping = T.ACESFilmicToneMapping; R.toneMappingExposure = 1.05;
  R.outputColorSpace = T.SRGBColorSpace; R.shadowMap.enabled = true; R.shadowMap.type = T.PCFSoftShadowMap; el.appendChild(R.domElement);
  const S = new T.Scene(), C = new T.PerspectiveCamera(W / H < .7 ? 33 : 27, W / H, .1, 60);
  const look = new T.Vector3(0, .55, 0); C.position.set(0, 3.6, 11); C.lookAt(look);

  S.add(new T.HemisphereLight(0xbfd6ff, 0x141a33, .9));
  const key = new T.DirectionalLight(0xffe0b5, 2.4); key.position.set(3.5, 6.5, 4); key.castShadow = true; key.shadow.mapSize.set(768, 768);
  Object.assign(key.shadow.camera, { left: -3, right: 3, top: 3, bottom: -3, near: 1, far: 20 }); key.shadow.radius = 6; S.add(key);
  const rim = new T.DirectionalLight(0x86b8ff, 1.6); rim.position.set(-4, 3, -4); S.add(rim);
  const inner = new T.PointLight(0xffc06a, 0, 6, 1.6); inner.position.set(0, 1.25, 0); S.add(inner);

  // снежный пол с мягким краем и сугробы
  const groundT = canvasTex(256, 256, (g) => { const r = g.createRadialGradient(128, 128, 20, 128, 128, 128); g.fillStyle = "#000"; g.fillRect(0, 0, 256, 256); r.addColorStop(0, "#fff"); r.addColorStop(.55, "#ddd"); r.addColorStop(1, "#000"); g.fillStyle = r; g.fillRect(0, 0, 256, 256); });
  const ground = new T.Mesh(new T.CircleGeometry(2.7, 64), new T.MeshStandardMaterial({ color: 0x6f84b3, roughness: .95, alphaMap: groundT, transparent: true }));
  ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; S.add(ground);
  const snowM = new T.MeshStandardMaterial({ color: 0x9db0d6, roughness: .9 });
  [[-1.5, .6, .32], [1.55, -.3, .28], [-.9, -1.2, .22], [1.05, 1.1, .24]].forEach(([x, z, r]) => { const m = new T.Mesh(new T.SphereGeometry(r, 24, 16), snowM); m.scale.y = .38; m.position.set(x, 0, z); m.receiveShadow = true; S.add(m); });

  // коробка: дно и четыре стенки на петлях (раскрываются), крышка с бантом
  const w = 1.5, h = 1.1, d = 1.5, th = .05;
  const side = new T.MeshPhysicalMaterial({ map: canvasTex(512, 512, (g, a, b) => paper(g, a, b, true)), roughness: .38, clearcoat: .7, clearcoatRoughness: .25 });
  const plain = new T.MeshPhysicalMaterial({ map: canvasTex(512, 512, (g, a, b) => paper(g, a, b, false)), roughness: .38, clearcoat: .7, clearcoatRoughness: .25 });
  const topM = new T.MeshPhysicalMaterial({ map: canvasTex(512, 512, (g, a, b) => paper(g, a, b, false, true)), roughness: .35, clearcoat: .8, clearcoatRoughness: .2 });
  const inside = new T.MeshStandardMaterial({ color: 0xf3e2bd, roughness: .8, emissive: 0x3a2a10 });
  const ribbonM = new T.MeshPhysicalMaterial({ color: 0xd61f2b, roughness: .28, clearcoat: 1, clearcoatRoughness: .15 });

  const gift = new T.Group(); S.add(gift);           // точка опоры - низ коробки (для сплющивания)
  const body = new T.Group(); gift.add(body);
  const bottom = new T.Mesh(new T.BoxGeometry(w, th, d), inside); bottom.position.y = th / 2; bottom.receiveShadow = true; body.add(bottom);
  const walls = [];
  const wall = (rotY) => {
    const hinge = new T.Group(); hinge.rotation.y = rotY; body.add(hinge);
    const pivot = new T.Group(); pivot.position.set(0, 0, d / 2); hinge.add(pivot);
    const mats = [plain, plain, plain, plain, side, plain];
    const m = new T.Mesh(new T.BoxGeometry(w + th * 2, h, th), mats); m.position.set(0, h / 2, -th / 2); m.castShadow = true; m.receiveShadow = true; pivot.add(m);
    walls.push(pivot);
  };
  [0, Math.PI / 2, Math.PI, -Math.PI / 2].forEach(wall);

  const lid = new T.Group(); lid.position.y = h; gift.add(lid);
  const lw = w + .14, lh = .34;
  const lidMats = [side, side, topM, plain, side, side];
  const lidBox = new T.Mesh(new T.BoxGeometry(lw, lh, lw), lidMats); lidBox.position.y = lh / 2 - .04; lidBox.castShadow = true; lid.add(lidBox);
  const bow = new T.Group(); bow.position.y = lh - .02; lid.add(bow);
  // атласная лента: плоский прямоугольник, протянутый вдоль петли (как настоящий бант)
  const ribbonShape = new T.Shape(); ribbonShape.moveTo(-.11, -.018); ribbonShape.lineTo(.11, -.018); ribbonShape.lineTo(.11, .018); ribbonShape.lineTo(-.11, .018); ribbonShape.lineTo(-.11, -.018);
  const sweep = (pts, closed) => new T.ExtrudeGeometry(ribbonShape, { steps: 90, bevelEnabled: false, extrudePath: new T.CatmullRomCurve3(pts, closed, "catmullrom", .5) });
  [-1, 1].forEach((s) => {
    const loop = sweep([[0, .08, 0], [s * .22, .38, .04], [s * .55, .52, 0], [s * .72, .36, -.02], [s * .6, .14, 0], [s * .3, .06, .02]].map((q) => new T.Vector3(...q)), true);
    const l = new T.Mesh(loop, ribbonM); l.rotation.y = s * .25; l.castShadow = true; bow.add(l);
    const tail = sweep([[0, .05, .05], [s * .18, .02, .32], [s * .3, -.02, .55], [s * .34, -.2, .66]].map((q) => new T.Vector3(...q)), false);
    const t1 = new T.Mesh(tail, ribbonM); t1.castShadow = true; bow.add(t1);
  });
  const knot = new T.Mesh(new T.SphereGeometry(.13, 24, 16), ribbonM); knot.scale.set(1.2, .9, 1); knot.position.y = .1; knot.castShadow = true; bow.add(knot);

  // снег: три слоя глубины, крупные хлопья ближе к камере
  const snowT = spriteTex(), flakes = [];
  const layer = (n, size, spread, op) => {
    const g = new T.BufferGeometry(), p = new Float32Array(n * 3), v = [];
    for (let i = 0; i < n; i++) { p[i * 3] = (Math.random() - .5) * spread; p[i * 3 + 1] = Math.random() * 7 - .5; p[i * 3 + 2] = (Math.random() - .5) * spread - 1; v.push(.25 + Math.random() * .5, Math.random() * 6.28); }
    g.setAttribute("position", new T.BufferAttribute(p, 3));
    const pts = new T.Points(g, new T.PointsMaterial({ map: snowT, size, transparent: true, opacity: op, depthWrite: false })); S.add(pts); flakes.push({ pts, v, n });
  };
  layer(500, .06, 12, .8); layer(160, .13, 9, .9); layer(40, .3, 6, .55);

  // искры и конфетти
  const sparkT = canvasTex(64, 64, (g) => { const r = g.createRadialGradient(32, 32, 0, 32, 32, 32); r.addColorStop(0, "rgba(255,250,225,1)"); r.addColorStop(.3, "rgba(255,210,120,.9)"); r.addColorStop(1, "rgba(255,170,60,0)"); g.fillStyle = r; g.fillRect(0, 0, 64, 64); });
  const SPN = 160, spG = new T.BufferGeometry(), spP = new Float32Array(SPN * 3).fill(-99), spV = Array.from({ length: SPN }, () => ({ v: new T.Vector3(), l: 0 }));
  spG.setAttribute("position", new T.BufferAttribute(spP, 3));
  const sparks = new T.Points(spG, new T.PointsMaterial({ map: sparkT, size: .16, transparent: true, depthWrite: false, blending: T.AdditiveBlending })); S.add(sparks);
  let spI = 0; const spark = (n, pow) => { for (let i = 0; i < n; i++) { const s = spV[spI]; spP[spI * 3] = (Math.random() - .5) * .8; spP[spI * 3 + 1] = h + .1; spP[spI * 3 + 2] = (Math.random() - .5) * .8; s.v.set((Math.random() - .5) * 3 * pow, (1.5 + Math.random() * 2.5) * pow, (Math.random() - .5) * 3 * pow); s.l = .7 + Math.random() * .5; spI = (spI + 1) % SPN; } };
  const CFN = 260, cf = new T.InstancedMesh(new T.PlaneGeometry(.07, .12), new T.MeshStandardMaterial({ side: T.DoubleSide, roughness: .4, metalness: .35 }), CFN);
  cf.instanceMatrix.setUsage(T.DynamicDrawUsage); const cfS = []; const COL = [0xe3242e, 0xffd36e, 0xffffff, 0x2fa391, 0xff8fa3, 0x7fd3ff];
  for (let i = 0; i < CFN; i++) { cf.setColorAt(i, new T.Color(COL[i % COL.length])); cfS.push({ p: new T.Vector3(0, -99, 0), v: new T.Vector3(), r: new T.Euler(), w: new T.Vector3(), l: 0 }); }
  S.add(cf); const dm = new T.Object3D();

  // лучи света при открытии
  const raysT = canvasTex(512, 512, (g) => { g.translate(256, 256); for (let i = 0; i < 18; i++) { g.rotate(Math.PI * 2 / 18); const gr = g.createLinearGradient(0, 0, 0, -256); gr.addColorStop(0, "rgba(255,225,150,.9)"); gr.addColorStop(1, "rgba(255,200,120,0)"); g.fillStyle = gr; g.beginPath(); g.moveTo(-6, 0); g.lineTo(-26, -256); g.lineTo(26, -256); g.lineTo(6, 0); g.fill(); } });
  const rays = new T.Mesh(new T.PlaneGeometry(9, 9), new T.MeshBasicMaterial({ map: raysT, transparent: true, opacity: 0, depthWrite: false, blending: T.AdditiveBlending }));
  rays.position.set(0, 1.4, -1.2); S.add(rays);

  // пружины
  const st = { y: 0, vy: 0, s: 0, vs: 0, rz: 0, vrz: 0, rx: 0, vrx: 0, ly: 0, vly: 0, lr: 0, vlr: 0 };
  let p = 0, open = false, t0 = performance.now(), last = t0, next = t0 + 800, raf = 0, shake = 0, openT = 0;
  const fly = { v: new T.Vector3(), w: new T.Vector3() };
  const kick = (k) => {
    if (k === 0) { st.vy += 2.2; st.vs -= .9; st.vly += 1.8; }
    else if (k === 1) { st.vrz += (Math.random() < .5 ? -1 : 1) * 4.5; st.vlr += (Math.random() - .5) * 4; }
    else if (k === 2) { st.vs += 1.6; st.vy += 1; st.vly += 2.6; st.vlr += (Math.random() - .5) * 3; }
    else { st.vrx += 3.6; setTimeout(() => (st.vrx -= 6), 90); setTimeout(() => (st.vrx += 4.5), 180); st.vly += 2; }
  };
  const loop = (now) => {
    const dt = Math.min(.033, (now - last) / 1000); last = now; const t = (now - t0) / 1000;
    if (!open && now > next) { kick(Math.floor(Math.random() * 4)); next = now + 700 + Math.random() * 900; }
    const spr = (x, v, k, c) => v + (-k * x - c * v) * dt;
    st.vy = spr(st.y, st.vy, 0, 0) - 22 * dt; st.y += st.vy * dt; if (st.y < 0) { st.y = 0; if (st.vy < -1) { st.vs += -st.vy * .25; st.vy *= -.25; } else st.vy = 0; }
    st.vs = spr(st.s, st.vs, 520, 13); st.s += st.vs * dt; st.vrz = spr(st.rz, st.vrz, 260, 10); st.rz += st.vrz * dt; st.vrx = spr(st.rx, st.vrx, 260, 10); st.rx += st.vrx * dt;
    if (!open) { st.vly = spr(st.ly, st.vly, 0, 0) - 26 * dt; st.ly += st.vly * dt; if (st.ly < 0) { st.ly = 0; st.vly *= -.2; } st.vlr = spr(st.lr, st.vlr, 380, 10); st.lr += st.vlr * dt; }
    const sq = Math.max(-.2, Math.min(.22, st.s));
    if (!open) {
      gift.position.y = st.y; gift.scale.set(1 + sq, 1 - sq, 1 + sq); gift.rotation.set(st.rx * .05, Math.sin(t * .4) * .12 - .35, st.rz * .05);
      lid.position.y = h + st.ly; lid.rotation.set(st.lr * .04, 0, st.lr * .06);
    } else {
      const k = now - openT;
      fly.v.y -= 9.8 * dt; lid.position.addScaledVector(fly.v, dt); lid.rotation.x += fly.w.x * dt; lid.rotation.z += fly.w.z * dt;
      const e = Math.min(1, k / 650), ease = 1 - Math.pow(1 - e, 3) * Math.cos(e * 4) * (1 - e);
      walls.forEach((w2) => (w2.rotation.x = ease * 1.75));
      gift.scale.set(1, 1, 1); gift.position.y = 0;
      rays.material.opacity = Math.min(.85, k / 400 * .85); rays.rotation.z = t * .25; rays.scale.setScalar(.6 + Math.min(1, k / 700) * .6);
      inner.intensity = Math.max(6, 40 - k / 40);
    }
    if (!open) inner.intensity = p * 10 + (Math.sin(t * 6) + 1) * p * 1.5;
    // снег
    for (const f of flakes) { const a = f.pts.geometry.attributes.position.array; for (let i = 0; i < f.n; i++) { a[i * 3 + 1] -= f.v[i * 2] * dt; a[i * 3] += Math.sin(t * .8 + f.v[i * 2 + 1]) * .12 * dt; if (a[i * 3 + 1] < -.2) a[i * 3 + 1] = 6.5; } f.pts.geometry.attributes.position.needsUpdate = true; }
    // искры
    for (let i = 0; i < SPN; i++) { const s = spV[i]; if (s.l <= 0) { spP[i * 3 + 1] = -99; continue; } s.l -= dt; s.v.y -= 4 * dt; spP[i * 3] += s.v.x * dt; spP[i * 3 + 1] += s.v.y * dt; spP[i * 3 + 2] += s.v.z * dt; }
    spG.attributes.position.needsUpdate = true;
    // конфетти
    for (let i = 0; i < CFN; i++) { const c = cfS[i]; if (c.l > 0) { c.l -= dt; c.v.y -= 5.5 * dt; c.v.multiplyScalar(.985); c.p.addScaledVector(c.v, dt); c.r.x += c.w.x * dt; c.r.y += c.w.y * dt; c.r.z += c.w.z * dt; if (c.p.y < .01) { c.p.y = .01; c.v.set(0, 0, 0); c.w.multiplyScalar(.9); } }
      dm.position.copy(c.p); dm.rotation.copy(c.r); dm.scale.setScalar(c.l > 0 ? 1 : 0); dm.updateMatrix(); cf.setMatrixAt(i, dm.matrix); }
    cf.instanceMatrix.needsUpdate = true;
    // камера: лёгкое покачивание и тряска от ударов
    shake *= .9; C.position.set(Math.sin(t * .3) * .35 + (Math.random() - .5) * shake, 3.6 + (Math.random() - .5) * shake, 11); C.lookAt(look);
    R.render(S, C); raf = requestAnimationFrame(loop);
  };
  raf = requestAnimationFrame(loop);
  const onResize = () => { const a = el.clientWidth, b = el.clientHeight; if (!a || !b) return; R.setSize(a, b); C.aspect = a / b; C.updateProjectionMatrix(); };
  addEventListener("resize", onResize);

  return {
    tap(pp) {
      if (open) return; p = pp; next = performance.now() + 900;
      st.vy = Math.min(3, st.vy + 1.8 + p * 1.4); st.vs += 1.2 + p * 1.2; st.vrz += (Math.random() < .5 ? -1 : 1) * (3 + p * 4); st.vrx += (Math.random() - .5) * 4; st.vly = Math.min(3.6, st.vly + 2.4 + p * 3); st.vlr += (Math.random() - .5) * (4 + p * 5);
      shake = .03 + p * .05; spark(5 + Math.round(p * 14), .8 + p);
    },
    reveal() {
      open = true; openT = performance.now(); shake = .14;
      fly.v.set((Math.random() < .5 ? -1 : 1) * (1.2 + Math.random()), 7.5, 1.2); fly.w.set(-6 - Math.random() * 3, 0, (Math.random() - .5) * 8);
      spark(SPN, 2.2);
      for (let i = 0; i < CFN; i++) { const c = cfS[i], a = Math.random() * Math.PI * 2, sp = 1.5 + Math.random() * 3.5; c.p.set((Math.random() - .5) * .6, h, (Math.random() - .5) * .6); c.v.set(Math.cos(a) * sp, 4 + Math.random() * 5, Math.sin(a) * sp * .7 + .8); c.w.set(Math.random() * 12, Math.random() * 12, Math.random() * 12); c.l = 2.5 + Math.random() * 1.5; }
    },
    anchor() { const v = new T.Vector3(0, h * .6, 0).project(C); const r = el.getBoundingClientRect(); return { x: r.left + (v.x + 1) / 2 * r.width, y: r.top + (1 - v.y) / 2 * r.height }; },
    destroy() { cancelAnimationFrame(raf); removeEventListener("resize", onResize); S.traverse((o) => { if (o.geometry) o.geometry.dispose(); }); R.dispose(); R.forceContextLoss && R.forceContextLoss(); el.innerHTML = ""; },
  };
}
