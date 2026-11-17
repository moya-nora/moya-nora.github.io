"""Книга встаёт на полку - сцена Blender (Cycles) для анимации в приложении.

Видео - полка с книгами при тёплом свете: соседи расступаются, в щель садится книга (её рисует приложение
поверх видео - с настоящей обложкой), в момент посадки - тёплая вспышка и золотая пыль.
Запуск: python3 scene.py <первый кадр> <последний кадр> <папка> [ширина] [сэмплы]
Кадры 1-84 (30 в секунду): 1-12 свет, 10-28 соседи расступаются, 36 посадка, дальше всё успокаивается.
Рядом пишет gap.json - где на кадре щель (доли кадра), по ней приложение ставит книгу.
"""
import json, math, os, random, sys
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

random.seed(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30
F_END = 84
sc.frame_start, sc.frame_end = 1, F_END


def mat(name, color, rough=.5, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m, b


def bump(m, scale=60, strength=.08, detail=6):
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    bu = nt.nodes.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = strength
    nt.links.new(n.outputs["Fac"], bu.inputs["Height"]); nt.links.new(bu.outputs["Normal"], b.inputs["Normal"])


def box(name, size, loc, m, bev=.02, seg=3, origin_bottom=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0)); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if origin_bottom:
        for v in o.data.vertices: v.co.z += size[2] / 2
    o.location = loc
    if bev:
        md = o.modifiers.new("b", "BEVEL"); md.width = bev; md.segments = seg; md.limit_method = "ANGLE"
    for p in o.data.polygons: p.use_smooth = True
    if isinstance(m, list):
        for mm in m: o.data.materials.append(mm)
    else:
        o.data.materials.append(m)
    return o


# ---------- материалы ----------
wall, wb = mat("wall", (.032, .026, .03), .92); bump(wall, 9, .12)
walnut, nb = mat("walnut", (.11, .055, .028), .42, **{"Coat Weight": .35, "Coat Roughness": .18})
nt = walnut.node_tree; wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 3.2; wv.inputs["Distortion"].default_value = 9; wv.inputs["Detail"].default_value = 4
wv.bands_direction = "X"
ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (.06, .028, .014, 1); ramp.color_ramp.elements[1].color = (.15, .08, .04, 1)
nt.links.new(wv.outputs["Fac"], ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"], nb.inputs["Base Color"])
brass, _ = mat("brass", (.83, .6, .3), .24, **{"Metallic": 1})
foil, _ = mat("foil", (.86, .64, .34), .2, **{"Metallic": 1})
pages, _ = mat("pages", (.15, .12, .085), .85); bump(pages, 220, .25, 2)
CLOTH = [(.075, .01, .015), (.008, .032, .022), (.009, .015, .042), (.13, .07, .018), (.01, .009, .012), (.038, .01, .034), (.085, .026, .01), (.006, .028, .032), (.2, .16, .11)]
cloth = []
for i, c in enumerate(CLOTH):
    m, b = mat(f"cloth{i}", c, .62, **{"Sheen Weight": .18, "Sheen Roughness": .3, "Coat Weight": .12, "Coat Roughness": .4}); bump(m, 300, .14, 4); cloth.append(m)
leather = []
for i, c in enumerate(CLOTH):
    m, b = mat(f"lab{i}", tuple(x * .45 for x in c), .55, **{"Coat Weight": .3, "Coat Roughness": .3}); bump(m, 90, .1, 3); leather.append(m)

# ---------- стена и полка ----------
box("wall", (14, .2, 14), (0, 1.05, 3), wall, 0)
SH_D = 2.1
box("shelf", (9, SH_D, .26), (0, .0, -.13), walnut, .03)
box("trim", (9, .03, .05), (0, -SH_D / 2 - .012, -.04), brass, .01, 2)
box("shelf_up", (9, SH_D, .26), (0, .0, 5.6), walnut, .03)  # верхняя полка - едва видна в темноте наверху

# ---------- книги ----------
G = .34   # толщина новой книги = ширина щели
BH = 2.4  # её высота
books = []
def make_book(x_center, w, h, ci, side, lean=0):
    d = 1.5 + random.uniform(-.06, .06)
    y = -SH_D / 2 + d / 2 + .08 + random.uniform(0, .04)
    root = bpy.data.objects.new("bk", None); bpy.context.collection.objects.link(root)
    root.location = (x_center, y, 0)
    b = box("bookbody", (w, d, h), (0, 0, 0), [cloth[ci], pages], .045, 4, origin_bottom=True); b.parent = root
    for p in b.data.polygons:
        if p.normal.z > .9: p.material_index = 1
    # обрез страниц сверху - чуть утоплен между крышками
    pg = box("pg", (w - .05, d - .06, .02), (0, .02, h - .004), pages, .004, 1); pg.parent = root
    # корешок: две пары тонких золотых линий и тёмная наклейка с рамкой под названием
    fy = -d / 2 - .003
    for z in (h * .07, h * .085, h * .905, h * .92):
        f = box("band", (w * .8, .004, .006), (0, fy, z), foil, 0); f.parent = root
    # «буквы» названия: несколько коротких золотых штрихов, как тиснение издалека
    z0 = h * random.uniform(.62, .72)
    for k in range(random.choice((2, 3, 3, 4))):
        ww = w * random.uniform(.28, .62)
        f = box("txt", (ww, .004, .012), (0, fy, z0 - k * .055), foil, 0); f.parent = root
    if random.random() < .5:
        f = box("orn", (w * .16, .004, w * .16), (0, fy, h * .3), foil, 0); f.parent = root; f.rotation_euler = (0, math.radians(45), 0)
    root["side"] = side; root["lean"] = lean
    books.append(root); return root

# слева и справа от щели - по 7 книг, плотно
def row(side):
    x = 0.0; n = 0
    while n < 11:
        w = random.choice((.26, .3, .34, .38, .42, .48)); h = random.uniform(2.05, 2.75)
        if n == 0: h = random.uniform(2.35, 2.6)
        ci = random.randrange(len(CLOTH))
        cx = side * (x + w / 2 + .004)
        make_book(cx, w, h, ci, side)
        x += w + .008; n += 1
row(-1); row(1)
# крайние книги чуть завалены (живая полка)
for side in (-1, 1):
    L = [b for b in books if b["side"] == side]; L.sort(key=lambda o: abs(o.location.x))
    L[-1].rotation_euler = (0, math.radians(-side * 9), 0); L[-1].location.x += side * .12

# ---------- пыль в луче ----------
dust_m, db = mat("dust", (1, .85, .6), .5, **{"Emission Strength": 1.6}); db.inputs["Emission Color"].default_value = (1, .82, .55, 1)
motes = []
for i in range(22):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=random.uniform(.005, .011), subdivisions=1, location=(random.uniform(-1.8, 1.8), random.uniform(-2.2, -1.2), random.uniform(1.2, 4.4)))
    o = bpy.context.object; o.data.materials.append(dust_m); motes.append((o, o.location.copy(), random.uniform(0, 6.28), random.uniform(.2, .5)))

# ---------- золотая пыль при посадке ----------
spark_m, sb = mat("spark", (1, .8, .45), .4, **{"Emission Strength": 22}); sb.inputs["Emission Color"].default_value = (1, .76, .42, 1)
sparks = []
F_LAND = 36
for i in range(80):
    top = random.random() < .7
    p0 = Vector((random.uniform(-G / 2, G / 2), -.62, BH + random.uniform(-.05, .05) if top else random.uniform(.05, BH)))
    ang = random.uniform(math.radians(20), math.radians(160)) if top else random.choice((math.pi * random.uniform(-.15, .15), math.pi * random.uniform(.85, 1.15)))
    sp = random.uniform(1.6, 4.2) if top else random.uniform(.8, 2.4)
    v = Vector((math.cos(ang) * sp, -random.uniform(.4, 1.6), math.sin(ang) * sp * (1 if top else .5)))
    bpy.ops.mesh.primitive_ico_sphere_add(radius=random.uniform(.012, .03), subdivisions=1, location=(0, 0, -20))
    o = bpy.context.object; o.data.materials.append(spark_m)
    sparks.append((o, p0, v, random.uniform(.5, 1.1)))

# ---------- свет ----------
def light(kind, name, loc, target, energy, color, **kw):
    l = bpy.data.lights.new(name, kind); l.energy = energy; l.color = color
    for k, v in kw.items(): setattr(l, k, v)
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler(); return o, l
key_o, key_l = light("SPOT", "key", (-.4, -3.2, 7.4), (0, .9, 1.4), 12000, (1, .76, .5), spot_size=math.radians(36), spot_blend=1, shadow_soft_size=.45)
light("AREA", "fill", (3.5, -9, 2.2), (0, 0, 1.2), 70, (.75, .82, 1), size=4)
light("AREA", "bounce", (0, -3, -1.5), (0, 0, .5), 60, (1, .7, .45), size=3)
glow_o, glow_l = light("POINT", "glow", (0, -.2, 1.5), (0, -1, 1.5), 0, (1, .74, .4), shadow_soft_size=.3)
glow2_o, glow2_l = light("POINT", "glow2", (0, -1.2, 2.5), (0, -2, 2.5), 0, (1, .8, .5), shadow_soft_size=.2)

world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (.004, .004, .007, 1); bg.inputs["Strength"].default_value = 1

# ---------- камера ----------
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 85; cam_d.sensor_fit = "VERTICAL"; cam_d.sensor_height = 36
cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 3.2
cam = bpy.data.objects.new("cam", cam_d); bpy.context.collection.objects.link(cam); sc.camera = cam
TGT = Vector((0, 0, .72))
def cam_at(f, dist, dz=0, sx=0, sz=0):
    cam.location = Vector((sx, -dist, 3.6 + dz + sz)); cam.rotation_euler = (TGT + Vector((sx, 0, sz)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
cam_d.dof.focus_distance = 20.5

# ---------- анимация ----------
def ease(t): return t * t * (3 - 2 * t)
def out_back(t, s=1.4): t -= 1; return t * t * ((s + 1) * t + s) + 1
base = {b.name: (b.location.copy(), b.rotation_euler.copy()) for b in books}
def books_at(f):
    # 10-28 расступаются (с запасом), 34-38 смыкаются на книге, лёгкая отдача
    if f < 10: off = 0
    elif f <= 28: off = (G / 2 + .07) * out_back((f - 10) / 18, .9)
    elif f < 34: off = G / 2 + .07
    elif f <= 38: off = G / 2 + .07 - .07 * ease((f - 34) / 4)
    else:
        t = (f - 38) / 10; off = G / 2 + (.018 * math.sin(t * math.pi * 2) * math.exp(-t * 3) if t < 1.5 else 0)
    # соседи у щели наклоняются наружу, пока она открыта
    if f < 10: lean = 0
    elif f <= 26: lean = 4.5 * ease((f - 10) / 16)
    elif f < 34: lean = 4.5
    elif f <= 38: lean = 4.5 * (1 - ease((f - 34) / 4))
    else:
        t = (f - 38) / 12; lean = -1.2 * math.sin(t * math.pi) * math.exp(-t * 2) if t < 1 else 0
    return off, lean
for f in range(1, F_END + 1):
    off, lean = books_at(f)
    for b in books:
        loc0, rot0 = base[b.name]; s = b["side"]; near = abs(loc0.x) < .6
        b.location = (loc0.x + s * off, loc0.y, loc0.z)
        b.rotation_euler = (rot0.x, rot0.y + (math.radians(-s * lean) if near else 0), rot0.z)
        b.keyframe_insert("location", frame=f); b.keyframe_insert("rotation_euler", frame=f)
    # пыль медленно плывёт
    for o, p, ph, sp in motes:
        o.location = p + Vector((math.sin(f / 30 * sp + ph) * .12, 0, f / 30 * .05 * sp + math.cos(f / 25 + ph) * .05)); o.keyframe_insert("location", frame=f)
    # искры
    for o, p0, v, life in sparks:
        t = (f - F_LAND) / 30
        if t < 0 or t > life:
            o.location = (0, 0, -20); o.scale = (1, 1, 1)
        else:
            drag = (1 - math.exp(-2.4 * t)) / 2.4
            o.location = p0 + v * drag + Vector((0, 0, -1.2 * t * t))
            k = 1 - t / life; o.scale = (k, k, k)
        o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f)
    # камера: медленный наезд + толчок при посадке
    shake = 0
    if F_LAND <= f <= F_LAND + 6: shake = .025 * math.sin((f - F_LAND) * 2.4) * (1 - (f - F_LAND) / 6)
    cam_at(f, 21.5 - .6 * ease(min(1, (f - 1) / (F_END - 1))), sz=shake)
for f, v in ((1, 0), (F_LAND - 2, 0), (F_LAND, 260), (F_LAND + 3, 170), (F_LAND + 20, 40), (F_END, 22)):
    glow_l.energy = v; glow_l.keyframe_insert("energy", frame=f)
for f, v in ((1, 0), (F_LAND - 1, 0), (F_LAND + 1, 90), (F_LAND + 10, 10), (F_LAND + 18, 0)):
    glow2_l.energy = v; glow2_l.keyframe_insert("energy", frame=f)
for f, v in ((1, 8000), (12, 12000), (F_LAND, 12000), (F_LAND + 2, 14000), (F_LAND + 14, 12000)):
    key_l.energy = v; key_l.keyframe_insert("energy", frame=f)
for a in bpy.data.actions:
    try:
        for fc in a.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = "LINEAR"
    except Exception: pass

# ---------- где щель на кадре ----------
def gap_rect(f):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    pts = [Vector((x, -SH_D / 2 + .08 + .02, z)) for x in (-G / 2, G / 2) for z in (0, BH)]
    pr = [world_to_camera_view(sc, cam, p) for p in pts]
    xs = [p.x for p in pr]; ys = [1 - p.y for p in pr]
    return [round(min(xs), 5), round(min(ys), 5), round(max(xs), 5), round(max(ys), 5)]

# ---------- рендер ----------
r = sc.render; r.engine = "CYCLES"; sc.cycles.device = "CPU"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
f1, f2, out = int(args[0]), int(args[1]), args[2]
wpx = int(args[3]) if len(args) > 3 else 540; spp = int(args[4]) if len(args) > 4 else 48
r.resolution_x = wpx; r.resolution_y = int(wpx * 16 / 9); r.resolution_percentage = 100
sc.cycles.samples = spp; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 5; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"; sc.view_settings.exposure = .55
r.image_settings.file_format = "PNG"
try:
    tree = bpy.data.node_groups.new("comp", "CompositorNodeTree"); sc.compositing_node_group = tree
    rl = tree.nodes.new("CompositorNodeRLayers"); gl = tree.nodes.new("CompositorNodeGlare"); out_n = tree.nodes.new("NodeGroupOutput")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    try: gl.inputs["Type"].default_value = "Bloom"
    except Exception: gl.glare_type = "BLOOM"
    for nm, v in (("Threshold", 1.0), ("Strength", .45), ("Size", .7)):
        try: gl.inputs[nm].default_value = v
        except Exception: pass
    tree.links.new(rl.outputs["Image"], gl.inputs["Image"]); tree.links.new(gl.outputs["Image"], out_n.inputs[0])
except Exception as e:
    print("без bloom:", e, flush=True)
os.makedirs(out, exist_ok=True)
if os.environ.get("GAP"):
    json.dump({"fps": 30, "frames": F_END, "land": F_LAND, "gap": [gap_rect(f) for f in range(1, F_END + 1)]}, open(os.path.join(out, "gap.json"), "w"))
    print("gap.json", flush=True); sys.exit(0)
for f in range(f1, f2 + 1):
    sc.frame_set(f); r.filepath = os.path.join(out, f"{f:04d}.png"); bpy.ops.render.render(write_still=True)
    print("кадр", f, flush=True)
