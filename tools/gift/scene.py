"""Новогодний подарок для «Книги для тебя» - сцена Blender (Cycles).

Запуск: python3 scene.py <первый кадр> <последний кадр> <папка> [ширина] [сэмплы]
Кадры: 1-48 ожидание (бесшовный цикл), 49-62 удар влево, 63-76 удар вправо, 77-140 раскрытие.
"""
import math, os, random, sys
import bpy, bmesh
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(3)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 24


def mat(name, color, rough=.4, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m, b


def bevel(o, w=.035, seg=4):
    m = o.modifiers.new("b", "BEVEL"); m.width = w; m.segments = seg; m.limit_method = "ANGLE"
    for p in o.data.polygons: p.use_smooth = True


def cube(name, size, loc, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True); o.data.materials.append(m); return o


# ---------- материалы ----------
wrap, wb = mat("wrap", (1, 1, 1), .28, **{"Coat Weight": .55, "Coat Roughness": .12})
tex = wrap.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(os.path.join(HERE, "wrap.png"))
tco = wrap.node_tree.nodes.new("ShaderNodeTexCoord"); mp = wrap.node_tree.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.4, 1.4, 1.4)
wrap.node_tree.links.new(tco.outputs["Object"], mp.inputs["Vector"]); wrap.node_tree.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
tex.projection = "BOX"; tex.projection_blend = .2
wrap.node_tree.links.new(tex.outputs["Color"], wb.inputs["Base Color"])
ribbon, rb = mat("ribbon", (.75, .01, .02), .3, **{"Sheen Weight": .35, "Sheen Roughness": .4, "Coat Weight": .35, "Coat Roughness": .1, "Anisotropic": .6})
rb.inputs["Sheen Tint"].default_value = (1, .55, .55, 1)
inside, ib = mat("inside", (.95, .82, .55), .7)
snow, sb = mat("snow", (.62, .7, .9), .6, **{"Subsurface Weight": .4})
sb.inputs["Subsurface Radius"].default_value = (.4, .5, .8)

# ---------- подарок ----------
W, H, L = 1.5, 1.1, .32
root = bpy.data.objects.new("gift", None); bpy.context.collection.objects.link(root)
def no_top(o):
    bm = bmesh.new(); bm.from_mesh(o.data); top = [f for f in bm.faces if f.normal.z > .9]; bmesh.ops.delete(bm, geom=top, context="FACES"); bm.to_mesh(o.data); bm.free()
body = cube("body", (W, W, H), (0, 0, H / 2), wrap); no_top(body); body.data.materials.append(inside)
so = body.modifiers.new("t", "SOLIDIFY"); so.thickness = .035; so.offset = -1; so.material_offset = 1; so.material_offset_rim = 1
bevel(body, .03); body.parent = root
for i, (sx, sy) in enumerate(((W + .03, .3), (.3, W + .03))):
    r = cube(f"band{i}", (sx, sy, H + .01), (0, 0, H / 2), ribbon); no_top(r); bevel(r, .01, 2); r.parent = root
lid = bpy.data.objects.new("lid", None); bpy.context.collection.objects.link(lid); lid.parent = root; lid.location = (0, 0, H - .06)
lb = cube("lidbox", (W + .12, W + .12, L), (0, 0, L / 2), wrap); bevel(lb, .05); lb.parent = lid
for i, (sx, sy) in enumerate(((W + .15, .31), (.31, W + .15))):
    r = cube(f"lband{i}", (sx, sy, L + .02), (0, 0, L / 2), ribbon); bevel(r, .012, 2); r.parent = lid


def strip(name, pts, side, width, thick=.018):
    """плоская атласная лента вдоль точек; side - направление ширины в каждой точке"""
    bm = bmesh.new(); rows = []
    for p, s in zip(pts, side):
        s = s.normalized() * width / 2; rows.append((bm.verts.new(p - s), bm.verts.new(p + s)))
    for a, b in zip(rows, rows[1:]):
        bm.faces.new((a[0], a[1], b[1], b[0]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.data.materials.append(ribbon)
    m = o.modifiers.new("t", "SOLIDIFY"); m.thickness = thick; m.offset = 0
    m2 = o.modifiers.new("s", "SUBSURF"); m2.levels = 2; m2.render_levels = 2
    for p in me.polygons: p.use_smooth = True
    return o


bow = bpy.data.objects.new("bow", None); bpy.context.collection.objects.link(bow); bow.parent = lid; bow.location = (0, 0, L + .01); bow.scale = (1.3, 1.3, 1.3)
def bow_loop(name, Lx, Hz, az, tilt, raise_, width):
    pts, side = [], []
    n = 72
    for k in range(n + 1):
        t = k / n * 2 * math.pi; u = (1 - math.cos(t)) / 2
        pts.append(Vector((Lx * u, .02 * math.sin(2 * t), Hz * math.sin(t) * u ** .35)))
    for k in range(len(pts)):
        a_, b_ = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
        tan = (b_ - a_).normalized(); nrm = Vector((0, 1, 0)); side.append(nrm - tan * tan.dot(nrm))
    o = strip(name, pts, side, width, .03); o.parent = bow
    o.rotation_euler = (math.radians(tilt), math.radians(-raise_), math.radians(az)); return o
for i, (az, Lx, Hz, tilt, rs) in enumerate(((8, .62, .3, 40, 22), (172, .62, .3, -40, 22), (96, .44, .24, 30, 30), (-84, .44, .24, -30, 30))):
    bow_loop(f"loop{i}", Lx, Hz, az, tilt, rs, .4 if i < 2 else .32)
for s in (-1, 1):
    # хвосты: свисают по крышке
    tp = [Vector((s * .04, 0, .08)), Vector((s * .16, -.3, .03)), Vector((s * .26, -.62, .0)), Vector((s * .32, -.84, -.06)), Vector((s * .36, -.9, -.3)), Vector((s * .4, -.92, -.62))]
    tside = [Vector((1, 0, 0)) for _ in tp]
    tail = strip(f"tail{s}", tp, tside, .27, .022); tail.parent = bow
bpy.ops.mesh.primitive_uv_sphere_add(radius=.16, location=(0, 0, .1)); knot = bpy.context.object; knot.scale = (1.25, .9, .85)
knot.data.materials.append(ribbon); bpy.ops.object.shade_smooth(); knot.parent = bow

# свет внутри коробки (разгорается при открытии)
inner_l = bpy.data.lights.new("inner", "POINT"); inner_l.color = (1, .78, .45); inner_l.energy = 0; inner_l.shadow_soft_size = .4
inner = bpy.data.objects.new("inner", inner_l); bpy.context.collection.objects.link(inner); inner.parent = root; inner.location = (0, 0, H * .7)
glow, gb = mat("glow", (1, .85, .5), .5, **{"Emission Strength": 0})
gb.inputs["Emission Color"].default_value = (1, .78, .4, 1)
gp = cube("glowplane", (W - .08, W - .08, .02), (0, 0, H - .02), glow); gp.parent = root

# луч света из коробки
bpy.ops.mesh.primitive_cone_add(vertices=128, radius1=.65, radius2=1.6, depth=4.2, end_fill_type="NOTHING", location=(0, 0, H + 2.1)); beam = bpy.context.object; bpy.ops.object.shade_smooth(); beam.parent = root
bm_ = bpy.data.materials.new("beam"); bm_.use_nodes = True; nt = bm_.node_tree; nt.nodes.clear()
o_ = nt.nodes.new("ShaderNodeOutputMaterial"); mix = nt.nodes.new("ShaderNodeMixShader"); tr = nt.nodes.new("ShaderNodeBsdfTransparent"); emn = nt.nodes.new("ShaderNodeEmission")
emn.inputs["Color"].default_value = (1, .82, .5, 1); emn.inputs["Strength"].default_value = 4
tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0; ramp.color_ramp.elements[0].color = (.0, 0, 0, 1); ramp.color_ramp.elements[1].position = 1; ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
mapn = nt.nodes.new("ShaderNodeMapRange"); mapn.inputs["From Min"].default_value = 2.1; mapn.inputs["From Max"].default_value = -2.1
amt = nt.nodes.new("ShaderNodeMath"); amt.operation = "MULTIPLY"; amt.inputs[1].default_value = 0
nt.links.new(tc.outputs["Object"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], mapn.inputs["Value"]); nt.links.new(mapn.outputs["Result"], amt.inputs[0])
lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = .5; inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
nt.links.new(lw.outputs["Facing"], inv.inputs[1]); m2_ = nt.nodes.new("ShaderNodeMath"); m2_.operation = "MULTIPLY"; nt.links.new(amt.outputs[0], m2_.inputs[0]); nt.links.new(inv.outputs[0], m2_.inputs[1])
nt.links.new(m2_.outputs[0], mix.inputs["Fac"]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(emn.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], o_.inputs["Surface"])
beam.data.materials.append(bm_); bm_.blend_method = "BLEND" if hasattr(bm_, "blend_method") else None
for f, v in ((77, 0), (84, 0), (88, .22), (100, .13), (140, .1)):
    amt.inputs[1].default_value = v; amt.inputs[1].keyframe_insert("default_value", frame=f)
root.rotation_euler = (0, 0, math.radians(-24))

# ---------- снег и фон ----------
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0)); gr = bpy.context.object; gr.data.materials.append(snow)
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.subdivide(number_cuts=80); bpy.ops.object.mode_set(mode="OBJECT")
tx = bpy.data.textures.new("n", "CLOUDS"); tx.noise_scale = 1.6
d = gr.modifiers.new("d", "DISPLACE"); d.texture = tx; d.strength = .12; d.mid_level = .7
for p in gr.data.polygons: p.use_smooth = True
for x, y, r in ((-1.9, .6, .5), (2.1, 1.0, .45), (-3, 2.5, .8), (3.2, 3, .9)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, -r * .55)); m = bpy.context.object; m.scale.z = .55; m.data.materials.append(snow); bpy.ops.object.shade_smooth()
# гирлянды вдалеке - тёплые огоньки в размытии
cols = [(1, .7, .3), (1, .35, .25), (.4, 1, .55), (.5, .7, 1), (1, .9, .6)]
for i in range(46):
    c = cols[i % len(cols)]
    em, eb = mat(f"bulb{i}", c, .5, **{"Emission Strength": 18})
    eb.inputs["Emission Color"].default_value = (*c, 1)
    x = random.uniform(-7, 7); y = random.uniform(6, 11); z = random.uniform(.5, 6.5)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=.06, location=(x, y, z)); o = bpy.context.object; o.data.materials.append(em)

world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (.012, .02, .06, 1); bg.inputs["Strength"].default_value = 1

# ---------- свет ----------
def area(name, loc, energy, color, size, target=(0, 0, .7)):
    l = bpy.data.lights.new(name, "AREA"); l.energy = energy; l.color = color; l.size = size
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o); o.location = loc
    dvec = Vector(target) - Vector(loc); o.rotation_euler = dvec.to_track_quat("-Z", "Y").to_euler(); return o
kl = bpy.data.lights.new("key", "SPOT"); kl.energy = 2600; kl.color = (1, .87, .72); kl.spot_size = math.radians(34); kl.spot_blend = .8; kl.shadow_soft_size = .9
ko = bpy.data.objects.new("key", kl); bpy.context.collection.objects.link(ko); ko.location = (3.0, -3.6, 5.2); ko.rotation_euler = (Vector((0, 0, .6)) - ko.location).to_track_quat("-Z", "Y").to_euler()
area("rim", (-3.4, 3.2, 3.2), 700, (.55, .7, 1), 2)
area("fill", (-2.6, -4, 1.6), 60, (.7, .8, 1), 3)

# ---------- камера ----------
cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 50; cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 2.2
cam = bpy.data.objects.new("cam", cam_d); bpy.context.collection.objects.link(cam); sc.camera = cam
cam.location = (0, -6.6, 2.6) if not os.environ.get("CLOSE") else (0, -3.2, 2.4); tgt = Vector((0, 0, .95)) if not os.environ.get("CLOSE") else Vector((0, 0, 1.45)); cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_d.dof.focus_distance = (tgt - cam.location).length

# ---------- конфетти ----------
CC = [(.95, .1, .15), (1, .8, .25), (1, 1, 1), (.15, .65, .55), (1, .5, .65), (.45, .8, 1)]
conf = []
for i in range(6):
    m, b = mat(f"conf{i}", CC[i], .35, **{"Metallic": .3})
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -50)); o = bpy.context.object; o.scale = (.05, .08, 1); o.data.materials.append(m); conf.append(o)
coll = bpy.data.collections.new("confetti"); sc.collection.children.link(coll)
for o in conf:
    for c in o.users_collection: c.objects.unlink(o)
    coll.objects.link(o)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, H - .1)); em = bpy.context.object; em.name = "emitter"; em.scale = (.6, .6, 1)
ps = em.modifiers.new("p", "PARTICLE_SYSTEM").particle_system.settings
ps.count = 420; ps.frame_start = 86; ps.frame_end = 90; ps.lifetime = 120; ps.emit_from = "FACE"
ps.normal_factor = 5.5; ps.factor_random = 2.5; ps.render_type = "COLLECTION"; ps.instance_collection = coll; ps.use_collection_pick_random = True
ps.particle_size = 1; ps.size_random = .5; ps.use_rotations = True; ps.rotation_mode = "VEL"; ps.rotation_factor_random = 1; ps.phase_factor_random = 2
ps.angular_velocity_mode = "RAND"; ps.angular_velocity_factor = 12; ps.effector_weights.gravity = .9; ps.drag_factor = .5
em.show_instancer_for_render = False

# ---------- анимация ----------
def key(o, f, loc=None, rot=None, scl=None):
    if loc is not None: o.location = loc; o.keyframe_insert("location", frame=f)
    if rot is not None: o.rotation_euler = [math.radians(a) for a in rot]; o.keyframe_insert("rotation_euler", frame=f)
    if scl is not None: o.scale = scl; o.keyframe_insert("scale", frame=f)

R0 = (0, 0, -24)
rest = dict(loc=(0, 0, 0), rot=R0, scl=(1, 1, 1))
LID0 = (0, 0, H - .06)
# ожидание 1-48: дышит, на 20-30 «кто-то внутри» толкается
for f, s, lz, rz in ((1, 1, 0, 0), (12, 1.012, 0, 0), (20, 1, 0, 0), (22, .97, .0, 0), (25, 1.04, .1, 3), (28, .99, .02, -2), (31, 1.01, 0, 1), (34, 1, 0, 0), (42, 1.01, 0, 0), (48, 1, 0, 0)):
    key(root, f, loc=(0, 0, 0), rot=(0, 0, -24 + rz), scl=(1 / s ** .5, 1 / s ** .5, s)); key(lid, f, loc=(0, 0, LID0[2] + lz), rot=(0, rz * 1.5, 0))
# удары
def hit(f0, sgn):
    seq = ((0, 1, 0, 0, 0), (2, .82, 0, 0, 0), (5, 1.12, .32, 6 * sgn, .25), (8, 1.03, .4, 9 * sgn, .32), (10, .9, 0, 2 * sgn, .05), (12, 1.04, 0, -2 * sgn, 0), (13, 1, 0, 0, 0))
    for df, s, z, tilt, lz in seq:
        key(root, f0 + df, loc=(0, 0, z), rot=(tilt * .4, tilt, -24), scl=(1 / s ** .5, 1 / s ** .5, s)); key(lid, f0 + df, loc=(0, 0, LID0[2] + lz), rot=(0, -tilt * 1.4, 0))
hit(49, 1); hit(63, -1)
# раскрытие 77-140
for df, s, z, tilt in ((0, 1, 0, 0), (4, .8, 0, 0), (7, 1.15, .15, 0), (10, .95, 0, 0), (13, 1, 0, 0)):
    key(root, 77 + df, loc=(0, 0, z), rot=(0, 0, -24), scl=(1 / s ** .5, 1 / s ** .5, s))
key(lid, 77, loc=LID0, rot=(0, 0, 0)); key(lid, 82, loc=(0, 0, LID0[2] + .05), rot=(0, 0, 0))
key(lid, 86, loc=(.6, -.2, 2.6), rot=(-40, 70, 20)); key(lid, 96, loc=(2.6, -.6, 6.5), rot=(-120, 260, 60))
for o, attr, seq in ((inner_l, "energy", ((77, 0), (82, 200), (86, 2600), (92, 1400), (140, 900))),):
    for f, v in seq: setattr(o, attr, v); o.keyframe_insert(attr, frame=f)
for f, v in ((77, 0), (82, 3), (86, 40), (94, 18), (140, 14)):
    gb.inputs["Emission Strength"].default_value = v; gb.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
# в ожидании и ударах свет изнутри чуть-чуть пробивается
for f, v in ((1, 6), (25, 40), (34, 6), (48, 6), (49, 6), (54, 120), (62, 6), (63, 6), (68, 120), (76, 6)):
    inner_l.energy = v; inner_l.keyframe_insert("energy", frame=f)
for a in bpy.data.actions:
    try:
        for fc in a.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = "BEZIER"; kp.easing = "AUTO"
    except Exception: pass

# ---------- рендер ----------
r = sc.render; r.engine = "CYCLES"; sc.cycles.device = "CPU"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
f1, f2, out = int(args[0]), int(args[1]), args[2]
wpx = int(args[3]) if len(args) > 3 else 540; spp = int(args[4]) if len(args) > 4 else 64
r.resolution_x = wpx; r.resolution_y = int(wpx * 16 / 9); r.resolution_percentage = 100
sc.cycles.samples = spp; sc.cycles.use_denoising = True; sc.cycles.max_bounces = 6; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Punchy"; sc.view_settings.exposure = 0
r.film_transparent = False; r.image_settings.file_format = "PNG"
# свечение ярких мест (bloom)
try:
    tree = bpy.data.node_groups.new("comp", "CompositorNodeTree"); sc.compositing_node_group = tree
    rl = tree.nodes.new("CompositorNodeRLayers"); gl = tree.nodes.new("CompositorNodeGlare"); out_n = tree.nodes.new("NodeGroupOutput")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    try: gl.inputs["Type"].default_value = "Bloom"
    except Exception: gl.glare_type = "BLOOM"
    for nm, v in (("Threshold", 1.2), ("Strength", .35), ("Size", .6)):
        try: gl.inputs[nm].default_value = v
        except Exception: pass
    tree.links.new(rl.outputs["Image"], gl.inputs["Image"]); tree.links.new(gl.outputs["Image"], out_n.inputs[0])
except Exception as e:
    print("без bloom:", e, flush=True)
os.makedirs(out, exist_ok=True)
for f in range(f1, f2 + 1):
    sc.frame_set(f); r.filepath = os.path.join(out, f"{f:04d}.png"); bpy.ops.render.render(write_still=True)
    print("кадр", f, flush=True)
