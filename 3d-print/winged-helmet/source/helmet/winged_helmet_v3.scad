// =====================================================================
//  WINGED VARSITY HELMET  -  parametric, multi-color (AMS / MMU)
// =====================================================================
//  One file makes both sizes:
//    build = "mini"  -> display model sized by OVERALL height
//                       (cheek-guard bottom to wingtip), default 5 in.
//    build = "full"  -> wearable helmet sized from YOUR head measurements.
//
//  Shapes scale up/down, but things that must stay printable do NOT
//  scale: wall thickness, raised-detail height, peg/slot clearance,
//  thinnest line width.  Each size has its own "Print tuning" section.
//
//  HOW TO EXPORT
//    1. Window > Customizer, pick build + part.
//    2. F6 (Render), then File > Export > STL.  One STL per part.
//    3. In the slicer, load the 3 color STLs of a piece together as ONE
//       object with multiple parts (they share the same origin) and
//       assign navy / gold / white filaments.
//
//  Axes: helmet faces -Y (front), +Z up, +X is the wearer's right.
// =====================================================================

/* [What to make] */
// Mini display model, or full-size wearable
build = "mini"; // [mini:Mini display model, full:Full-size wearable]
// Piece to render/export. "assembly" is a color preview only (do not export it).
part = "assembly"; // [assembly:Preview - everything assembled, helmet_navy:Helmet - navy, helmet_gold:Helmet - gold, helmet_white:Helmet - white, wing_right_navy:Right wing - navy, wing_right_gold:Right wing - gold, wing_right_white:Right wing - white, wing_left_navy:Left wing - navy, wing_left_gold:Left wing - gold, wing_left_white:Left wing - white]

/* [Mini model size] */
// Overall height, cheek-guard bottom to wingtip (inches)
mini_overall_height_in = 5; // [2:0.25:12]

/* [Full size - fit to your head] */
// Tape measure around your head, just above eyebrows and ears (mm)
head_circumference = 580; // [500:1:660]
// Head length (front-to-back) / head width (side-to-side). 1.20-1.30 is typical
head_shape_ratio = 1.24; // [1.10:0.01:1.40]
// Eyebrow line to top of head (mm)
brow_to_crown = 120; // [90:1:150]
// Gap left for foam padding at sides/front/back (mm)
side_padding = 12; // [4:1:25]
// Gap left for foam padding on top (mm)
top_padding = 20; // [5:1:35]

/* [Emblem] */
// Big raised letter on the front
front_letter = "H";
// Smaller letter on each cheek guard (leave empty for none)
cheek_letter = "H";
// Any installed font. Liberation fonts ship with OpenSCAD.
letter_font = "Liberation Serif:style=Bold";

/* [Style - full-size millimetres, the mini scales these] */
// 2.0 = egg-round dome, 3.0 = boxier dome
dome_fullness = 2.4; // [2.0:0.1:3.5]
// Cheek/neck guards angle outward this much (also gives nose clearance)
skirt_flare = 10; // [0:1:20]
brow_band_height = 34;
crest_gold_width = 22;
crest_white_width = 6;
front_letter_height = 52;
cheek_letter_height = 30;
cheek_guard_length = 120;
nasal_guard_length = 75;
neck_guard_length = 75;
// How far below the brow line the ear opening starts
ear_notch_depth = 12;
// Gold trim along all edges
edge_trim_width = 5;
// Scroll pattern cut into the gold brow band
band_scrollwork = true;
// Wing size multiplier
wing_size = 1.0; // [0.6:0.05:1.5]
// Wings turned to face forward by this angle (degrees)
wing_yaw = 22; // [0:1:40]
// Wing tops lean outward by this angle (degrees)
wing_splay = 3; // [-10:1:25]
// Wing mount position, + toward the back (full-size mm)
wing_mount_offset = -10;

/* [Print tuning - mini] */
mini_wall = 1.6;
// Height of raised color details
mini_relief = 0.8;
// No printed line narrower than this
mini_min_line = 0.9;
// Wing thickness (bottom feather layer) - also the peg thickness
mini_wing_base = 2.4;
// Extra thickness per feather layer
mini_wing_step = 0.6;
// Peg/slot clearance per side
mini_clearance = 0.2;
mini_socket_wall = 1.4;

/* [Print tuning - full] */
full_wall = 2.4;
full_relief = 1.6;
full_min_line = 1.2;
full_wing_base = 5;
full_wing_step = 1.5;
full_clearance = 0.3;
full_socket_wall = 3;

/* [Quality] */
mini_facets = 120;
full_facets = 200;

/* [Hidden] */
IS_MINI = build == "mini";
BIG = 3000;
EPS = 0.01;

// ---------- colors for the preview ----------
C_NAVY  = "#1E2A52";
C_GOLD  = "#F2C12E";
C_WHITE = "#F4F4EE";

// ---------- head -> full-size interior ----------
_q  = head_shape_ratio;
_hh = pow((_q - 1) / (_q + 1), 2);
head_half_width = head_circumference /
    (PI * (1 + _q) * (1 + 3 * _hh / (10 + sqrt(4 - 3 * _hh))));   // Ramanujan
F_RI = head_half_width + side_padding;                 // interior half-width at brow
K    = (head_half_width * _q + side_padding) / F_RI;    // front/back stretch
F_HI = brow_to_crown + top_padding;                    // interior height above brow

// ---------- printable (non-scaling) values ----------
W      = IS_MINI ? mini_wall        : full_wall;
RL     = IS_MINI ? mini_relief      : full_relief;
MINL   = IS_MINI ? mini_min_line    : full_min_line;
T0     = IS_MINI ? mini_wing_base   : full_wing_base;
TSTEP  = IS_MINI ? mini_wing_step   : full_wing_step;
CLR    = IS_MINI ? mini_clearance   : full_clearance;
SWALL  = IS_MINI ? mini_socket_wall : full_socket_wall;
FN     = IS_MINI ? mini_facets      : full_facets;
$fa = 5;
$fs = IS_MINI ? 0.3 : 0.6;

// ---------- wing design (full-size mm at wing_size = 1) ----------
ARM = [[0, 5], [-12, 72], [28, 130], [92, 166]];   // leading-edge Bezier
SPL = wing_splay;
YAW = wing_yaw;
F_TAB_W = 30;  F_TAB_H = 22;  F_FLOOR = 3;  F_GAP = 2;

function bz(t, ws)  = ws * (pow(1-t,3)*ARM[0] + 3*pow(1-t,2)*t*ARM[1]
                           + 3*(1-t)*t*t*ARM[2] + pow(t,3)*ARM[3]);
function bzd(t)     = 3*pow(1-t,2)*(ARM[1]-ARM[0]) + 6*(1-t)*t*(ARM[2]-ARM[1])
                      + 3*t*t*(ARM[3]-ARM[2]);
function unit(v)    = v / norm(v);
function TT(t)      = unit(bzd(t));
function NN(t)      = [TT(t)[1], -TT(t)[0]];          // trailing-side normal
function arm_hw(t, ws) = ws * (2.5 + 8.5 * pow(1 - t, 0.9));
NA = 40;
function arm_pts(ws) = concat(
    [for (i = [0:NA]) let(t = i/NA) bz(t, ws) - NN(t) * arm_hw(t, ws)],
    [bz(1, ws) + TT(1) * ws * 8],
    [for (i = [NA:-1:0]) let(t = i/NA) bz(t, ws) + NN(t) * arm_hw(t, ws)]);

// ---------- size of the mini ----------
F_VMAX  = max([for (p = arm_pts(wing_size)) p[1]]);
F_DROP  = max(cheek_guard_length * 0.985, nasal_guard_length, neck_guard_length);
SHAPE_H = brow_band_height + F_GAP + (F_TAB_H + F_FLOOR + F_VMAX) * cos(SPL) + F_DROP;
NOUT_ABS = T0 + CLR + SWALL;
ABS_H   = CLR * cos(SPL) + NOUT_ABS * sin(SPL);
S = IS_MINI ? (mini_overall_height_in * 25.4 - ABS_H) / SHAPE_H : 1;

function sc(x) = x * S;
function ln(x) = max(x * S, MINL);

// ---------- scaled dimensions ----------
RI = F_RI * S;
HI = F_HI * S;
BK = RI * K;
BH = sc(brow_band_height);
PIPE = ln(4);
CL = sc(cheek_guard_length);
NL = sc(nasal_guard_length);
NKL = sc(neck_guard_length);
EN = sc(ear_notch_depth);
TRIM = ln(edge_trim_width);
DROP = sc(F_DROP);
ZLOW = -DROP - sc(30);
WS = S * wing_size;

TAB_W = sc(F_TAB_W);
TAB_H = sc(F_TAB_H);
FLOOR = sc(F_FLOOR);
T_TAB = T0;
NIN  = -(CLR + SWALL);
NOUT = T_TAB + CLR + SWALL;
VBOT = -(TAB_H + CLR + FLOOR);
USOCK = TAB_W/2 + CLR + SWALL;

// interior radius (circular frame) at height z
function r_in(z) = z <= 0 ? RI + (-z) * tan(skirt_flare)
                 : RI * pow(max(0, 1 - pow(min(z/HI, 1), dome_fullness)), 1/dome_fullness);
// outer surface x at (y, z) in the final (stretched) frame
function x_out(y, z) = let(a = r_in(z) + W) sqrt(max(0, a*a - pow(y/K, 2)));

// ================= helmet shell profile =================
NP = 72;
function interior_pts() = concat(
    [[0, ZLOW], [RI + (-ZLOW) * tan(skirt_flare), ZLOW]],
    [for (i = [0:NP]) let(p = 90 * i / NP)
        [i == NP ? 0 : RI * pow(cos(p), 2/dome_fullness),
         HI * pow(sin(p), 2/dome_fullness)]]);

module prof(d) {
    intersection() {
        offset(delta = d) polygon(interior_pts());
        translate([0, ZLOW]) square([BIG, BIG]);
    }
}
// solid of revolution between offsets d1 < d2 (0 = inside surface)
module layer(d1, d2) {
    scale([1, K, 1]) rotate_extrude($fn = FN)
        difference() { prof(d2); prof(d1); }
}
module layer_z(d1, d2, z0, z1) {
    scale([1, K, 1]) rotate_extrude($fn = FN)
        intersection() {
            difference() { prof(d2); prof(d1); }
            translate([0, z0]) square([BIG, z1 - z0]);
        }
}
module skin(r)  { layer(W, W + r); }
module cavity() { scale([1, K, 1]) rotate_extrude($fn = FN) prof(0); }
module solid_out() { scale([1, K, 1]) rotate_extrude($fn = FN) prof(W); }

// ================= cut-outs =================
// front view (x, z): face opening, nasal guard left standing
module nasal2d() {
    h = [13, 11, 14, 14];
    polygon(S * [[-h[0], 3], [h[0], 3],
                 [h[1], -0.37*nasal_guard_length], [h[2], -0.77*nasal_guard_length],
                 [h[3], -0.86*nasal_guard_length], [0, -nasal_guard_length],
                 [-h[3], -0.86*nasal_guard_length], [-h[2], -0.77*nasal_guard_length],
                 [-h[1], -0.37*nasal_guard_length]]);
}
module face2d() {
    xs = [0.66, 0.64, 0.57, 0.47, 0.43];
    zs = [0, -0.25, -0.58, -0.88, -3];
    rr = sc(8);
    difference() {
        offset(r = rr) offset(delta = -rr)
            polygon(concat(
                [for (i = [0:4]) [ xs[i] * RI, zs[i] * CL]],
                [for (i = [4:-1:0]) [-xs[i] * RI, zs[i] * CL]]));
        nasal2d();
    }
}
// side view (y, z): bottom edge incl. cheek guards, ear notch, neck guard
module bottom2d() {
    rr = sc(9);
    offset(r = rr) offset(r = -2*rr) offset(r = rr)
        polygon([[-3*BK, -CL], [-0.5*BK, -0.98*CL], [-0.14*BK, -0.86*CL],
                 [-0.04*BK, -0.30*CL], [0.02*BK, -EN], [0.30*BK, -EN],
                 [0.50*BK, -0.9*NKL], [0.70*BK, -NKL], [3*BK, -NKL],
                 [3*BK, -BIG/4], [-3*BK, -BIG/4]]);
}
module face_prism()   { rotate([90, 0, 0]) linear_extrude(BIG) children(); }       // along -Y
module side_prism()   { rotate([90, 0, 90]) linear_extrude(BIG, center = true) children(); } // along X
module face_cut()     { face_prism() face2d(); }
module bottom_cut()   { side_prism() bottom2d(); }
module all_cuts()     { face_cut(); bottom_cut(); }

// ================= wing mount (socket) =================
// local wing frame: u = along wing (toward back), v = up, n = out of wing face
function loc2w(p) = let(
    x = p[2], y = p[0], z = p[1],
    x1 = x*cos(SPL) + z*sin(SPL), z1 = -x*sin(SPL) + z*cos(SPL),
    x2 = x1*cos(YAW) + y*sin(YAW), y2 = -x1*sin(YAW) + y*cos(YAW)) [x2, y2, z1];

ZM = BH + sc(F_GAP) + (TAB_H + CLR + FLOOR) * cos(SPL) + NOUT * sin(SPL);
YM = sc(wing_mount_offset);
_corners = [for (u = [-USOCK, USOCK]) for (v = [VBOT, 0]) loc2w([u, v, NIN])];
XM = max([for (d = _corners) x_out(YM + d[1], ZM + d[2]) - d[0]]);

module wing_frame() {
    translate([XM, YM, ZM]) rotate([0, 0, -YAW]) rotate([0, SPL, 0])
        rotate([90, 0, 90]) children();
}
SOCK_D  = (NOUT - NIN) + sc(14);              // how far the socket's sloped underside reaches in
SOCK_DV = 1.15 * (SOCK_D + NOUT - NIN);       // ... and down
module socket_local() {
    D  = SOCK_D;
    DV = SOCK_DV;
    hull() {
        translate([-USOCK, VBOT, NIN]) cube([2*USOCK, -VBOT, NOUT - NIN]);
        translate([-USOCK, VBOT - DV, NIN - D]) cube([2*USOCK, -VBOT, EPS]);
    }
}
module slot_local() {
    translate([-(TAB_W/2 + CLR), -(TAB_H + CLR), -CLR])
        cube([TAB_W + 2*CLR, BIG, T_TAB + 2*CLR]);
}
module sockets() {
    for (m = [0, 1]) mirror([m, 0, 0])
        difference() {
            wing_frame() socket_local();
            solid_out();
            wing_frame() slot_local();
        }
}
module socket_zone() { for (m = [0, 1]) mirror([m, 0, 0]) wing_frame() socket_local(); }

// ================= raised details =================
module crest_slab(x0, x1) {
    translate([x0, -BIG/2, BH]) cube([x1 - x0, BIG, BIG]);
}
module glyph(txt, h, flip = false) {
    mirror([flip ? 1 : 0, 0])
        resize([0, h], auto = true)
            text(txt, size = 10, font = letter_font, halign = "center", valign = "center");
}
LET_H  = sc(front_letter_height);
LET_Z  = BH + sc(7) + LET_H/2;
LET_OL = ln(2.5);
module front_letter2d()  { translate([0, LET_Z]) glyph(front_letter, LET_H); }
module front_outline2d() { offset(r = LET_OL) front_letter2d(); }

module crest_white() {
    intersection() {
        skin(RL);
        difference() {
            union() {
                crest_slab(sc(crest_gold_width)/2, sc(crest_gold_width)/2 + ln(crest_white_width));
                mirror([1, 0, 0])
                crest_slab(sc(crest_gold_width)/2, sc(crest_gold_width)/2 + ln(crest_white_width));
            }
            face_prism() front_outline2d();
        }
    }
}
module crest_gold() {
    intersection() {
        skin(RL * 1.5);
        difference() {
            crest_slab(-sc(crest_gold_width)/2, sc(crest_gold_width)/2);
            face_prism() front_outline2d();
        }
    }
}
module letter_gold()    { intersection() { skin(RL * 2.5); face_prism() front_letter2d(); } }
module letter_outline() {
    intersection() {
        skin(RL * 1.5);
        face_prism() difference() { front_outline2d(); front_letter2d(); }
    }
}

// --- brow band ---
PLQ = sc(13);           // plaque half-width = nasal top
module band_pipes() {
    layer_z(W, W + RL * 1.5, 0, PIPE);
    layer_z(W, W + RL * 1.5, BH - PIPE, BH);
}
module plaque_cut() {
    translate([0, 0, 0]) face_prism()
        translate([-(PLQ - TRIM), PIPE - EPS]) square([2*(PLQ - TRIM), BH - 2*PIPE + 2*EPS]);
}
// running scroll motif, centred on (0,0): stem + alternating curls
function spiral_pts(c, r0, a0, sweep, shrink, n = 28) =
    [for (i = [0:n]) let(t = i/n, a = a0 + sweep*t, r = r0*(1 - shrink*t))
        c + r * [cos(a), sin(a)]];
module polyline2d(pts, w) {
    for (i = [0:len(pts)-2]) hull() {
        translate(pts[i])   circle(d = w, $fn = 12);
        translate(pts[i+1]) circle(d = w, $fn = 12);
    }
}
module scroll2d(L, hb, lw) {
    a = 0.13 * hb;
    stem = [for (i = [0:24]) let(s = -L/2 + L*i/24) [s, -a * sin(360 * s / L)]];
    r0 = 0.22 * hb;
    c  = [L/4 - 0.02*L, 0.5*hb - lw*1.3 - r0];                 // curl above the trough
    start = [L/4 - 0.30*L, -a * sin(360 * (L/4 - 0.30*L) / L)];
    a0 = atan2(start[1] - c[1], start[0] - c[0]);
    sp = spiral_pts(c, norm(start - c), a0, -300, 0.62);
    union() {
        polyline2d(stem, lw);
        polyline2d(sp, lw);
        translate(sp[len(sp)-1]) circle(d = lw * 1.6, $fn = 16);
        rotate(180) {
            polyline2d(sp, lw);
            translate(sp[len(sp)-1]) circle(d = lw * 1.6, $fn = 16);
        }
    }
}
module band_grooves() {
    hb  = BH - 2*PIPE;
    lw  = ln(3);
    rb  = r_in(BH/2) + W;
    th0 = asin(min(0.9, (PLQ + sc(3)) / rb));
    th1 = 180;
    n   = max(1, round(rb * (th1 - th0) * PI / 180 / (1.9 * hb)));
    dth = (th1 - th0) / n;
    L   = rb * dth * PI / 180;
    sag = L * L / (8 * rb) + 1;
    scale([1, K, 1])
    for (m = [0, 1]) mirror([m, 0, 0])
        for (i = [0:n-1])
            rotate([0, 0, th0 + (i + 0.5) * dth])
                translate([0, -(rb - sag - 5), BH/2]) rotate([90, 0, 0])
                    linear_extrude(sag + 10 + 2*RL) scroll2d(L, hb, lw);
}
module band_gold() {
    difference() {
        layer_z(W, W + RL, PIPE, BH - PIPE);
        plaque_cut();
        if (band_scrollwork) band_grooves();
    }
}

// --- rivets ---
RIV = ln(6);
module front_rivet(z, d) { face_prism() translate([0, z]) circle(d = d); }
module rivets() {
    intersection() {
        skin(RL * 1.5);
        union() {
            for (z = [BH * 0.36, BH * 0.64]) front_rivet(z, ln(4.5));
            for (f = [0.18, 0.42, 0.66]) front_rivet(-f * NL, RIV);
        }
    }
}

// --- edge trim ---
module edge_trim() {
    difference() {
        intersection() {
            skin(RL);
            union() {
                face_prism() intersection() {
                    difference() { offset(delta = TRIM) face2d(); face2d(); }
                    translate([-BIG/2, -BIG]) square([BIG, BIG]);
                }
                side_prism() difference() { offset(delta = TRIM) bottom2d(); bottom2d(); }
            }
        }
        all_cuts();
    }
}

// --- cheek letters ---
module cheek_letters() {
    if (cheek_letter != "") {
        yc = -0.45 * BK;
        zc = -0.5 * CL;
        a  = r_in(zc) + W;
        xs = sqrt(max(0, a*a - pow(yc/K, 2)));
        nv = unit([xs / (a*a), yc / (K*K*a*a)]);
        ang = atan2(nv[1], nv[0]);
        for (m = [0, 1]) mirror([m, 0, 0])
            intersection() {
                skin(RL * 1.5);
                translate([xs - nv[0]*sc(25), yc - nv[1]*sc(25), zc])
                    rotate([0, 0, ang]) rotate([90, 0, 90])
                        linear_extrude(sc(50))
                            glyph(cheek_letter, sc(cheek_letter_height), m == 1);
            }
    }
}

// ================= helmet color bodies =================
module helmet_navy() {
    difference() { layer(0, W); all_cuts(); }
}
module helmet_gold() {
    union() {
        crest_gold();
        letter_gold();
        difference() { band_gold(); socket_zone(); }
        edge_trim();
        sockets();
    }
}
module helmet_white() {
    union() {
        crest_white();
        letter_outline();
        difference() { band_pipes(); socket_zone(); }
        rivets();
        cheek_letters();
    }
}

// ================= wings (printed flat, decorated face up) =================
// ---------------------------------------------------------------------
// Wing: a fan of long curved feathers radiating from the shoulder, with a
// gold leading edge and an eagle head at the shoulder (after the reference
// photo).  Upper feathers sweep up/back to the tip, lower feathers hang
// down beside the cheek guards.  Full-size mm at wing_size = 1.
// ---------------------------------------------------------------------
PIV = [16, 26];                 // shoulder: the point the feathers radiate from
// feather rows, bottom layer first:
// [count, angle_first, angle_last, base radius, length scale, width, curl, [fill, rim, vein]]
// angles in degrees from "straight back" (+u), positive = up.  Colors: 0 navy, 1 gold, 2 white, -1 none.
FAN = [
    [14, 86, -80, 10, 1.00, 27, 0.20, [0, 1, 2]],   // long feathers: navy, gold edge, white streak
    [13, 82, -72, 10, 0.70, 24, 0.18, [1, 0, 2]],   // middle row: gold, navy edge, white streak
    [11, 76, -62,  8, 0.42, 20, 0.14, [0, 1, -1]]   // coverts: navy scallops, gold edge
];
ARM_COL = [1, 0, 2];            // leading edge: gold, navy edge, white stripe
HEAD_C  = [34, 40];             // eagle head centre
HEAD_R  = 15;
NT   = len(FAN) + 3;            // web, feather rows, leading edge, eagle head
RIM  = ln(2.5);
VEIN = ln(2.5);
NF   = 24;
function tier_h(i) = T0 + TSTEP * max(0, i - 1);

// feather length by direction: longest toward the tip, shortest straight back
function fan_len(a) = a >= 0 ? 112 + 42 * pow(a / 86, 2) : 112 + 68 * pow(-a / 80, 1.4);
function fa_ang(r, k)  = r[1] + (r[2] - r[1]) * k / (r[0] - 1);
function fa_dir(r, k)  = let(a = fa_ang(r, k)) [cos(a), sin(a)];
function fa_base(r, k) = WS * (PIV + fa_dir(r, k) * r[3]);
function fa_len(r, k)  = WS * fan_len(fa_ang(r, k)) * r[4];
function fa_wid(r, k)  = WS * r[5];
function perpR(v)      = [v[1], -v[0]];
// curved feather: spine bends clockwise (toward the back / down), pointed tip
function fe_spine(b, d, L, cu, s) = b + d * L * s + perpR(d) * (cu * L * s * s);
function fe_norm(d, L, cu, s)     = let(t = unit(d * L + perpR(d) * (2 * cu * L * s))) [-t[1], t[0]];
function fe_half(w, s)            = w / 2 * pow(max(0, 1 - pow(s, 2.2)), 0.6);
function fe_pts(r, k) = let(b = fa_base(r, k), d = fa_dir(r, k), L = fa_len(r, k), w = fa_wid(r, k), cu = r[6])
    concat([for (i = [0:NF]) let(s = i/NF) fe_spine(b, d, L, cu, s) + fe_norm(d, L, cu, s) * fe_half(w, s)],
           [for (i = [NF:-1:0]) let(s = i/NF) fe_spine(b, d, L, cu, s) - fe_norm(d, L, cu, s) * fe_half(w, s)]);

module feather(r, k) { polygon(fe_pts(r, k)); }
module feather_vein(r, k) {
    b = fa_base(r, k);  d = fa_dir(r, k);  L = fa_len(r, k);  w = fa_wid(r, k);  cu = r[6];
    polyline2d([for (i = [0:12]) let(s = 0.14 + 0.64 * i/12)
        fe_spine(b, d, L, cu, s) + fe_norm(d, L, cu, s) * fe_half(w, s) * 0.2], VEIN);
}
RW = TAB_W/2 + sc(3);
module root_block() {
    rr = WS * 5;
    hull() {
        translate([-RW, 0]) square([2*RW, EPS]);
        translate([-RW + rr, WS*18 - rr]) circle(rr);
        translate([ RW - rr, WS*18 - rr]) circle(rr);
    }
}
module arm2d() { union() { polygon(arm_pts(WS)); root_block(); } }
module arm_vein() { polyline2d([for (i = [0:30]) bz(0.05 + 0.85*i/30, WS)], VEIN); }

// eagle head facing forward, hooked beak
// bird-head profile: round crown tapering back into the neck, hooked beak in front
module skull2d() {
    hull() {
        translate(WS * HEAD_C) circle(r = WS * HEAD_R);
        translate(WS * (HEAD_C + [20, -14])) circle(r = WS * 8);
    }
}
module beak2d() {
    translate(WS * HEAD_C) scale(WS)
        polygon([[-4, 11], [-20, 10], [-31, 4], [-36, -6], [-32, -12], [-28, -5], [-18, -4], [-4, -7]]);
}
module head2d() { skull2d(); beak2d(); }
module eye2d()  { translate(WS * (HEAD_C + [3, 4])) circle(r = max(WS * 3.8, MINL * 0.9)); }
module head_color2d(c) {
    // gold: skull outline, beak body, eye ring;  navy: skull + beak outline;  white: eye
    if (c == 1) union() {
        difference() { skull2d(); offset(delta = -RIM) skull2d(); beak2d(); }
        offset(delta = -RIM * 0.8) beak2d();
        difference() { offset(delta = RIM) eye2d(); eye2d(); beak2d(); }
    }
    if (c == 0) union() {
        difference() { offset(delta = -RIM) skull2d(); beak2d(); offset(delta = RIM) eye2d(); }
        difference() { beak2d(); offset(delta = -RIM * 0.8) beak2d(); }
    }
    if (c == 2) difference() { eye2d(); beak2d(); }
}

// solid web under the long feathers so the wing is one piece
module web2d() {
    r = FAN[0];
    for (k = [0:r[0]-2]) hull() {
        translate(WS * PIV) circle(d = WS * 30);
        translate(fa_base(r, k))     circle(d = fa_wid(r, k));
        translate(fa_base(r, k + 1)) circle(d = fa_wid(r, k + 1));
        translate(fe_spine(fa_base(r, k), fa_dir(r, k), fa_len(r, k), r[6], 0.45)) circle(d = fa_wid(r, k) * 0.7);
        translate(fe_spine(fa_base(r, k+1), fa_dir(r, k+1), fa_len(r, k+1), r[6], 0.45)) circle(d = fa_wid(r, k+1) * 0.7);
    }
}
// tiers: 0 web, 1..len(FAN) feather rows, NT-2 leading edge, NT-1 eagle head
module tier_footprint(i) {
    if (i == 0) web2d();
    else if (i == NT - 2) arm2d();
    else if (i == NT - 1) head2d();
    else for (k = [0:FAN[i-1][0]-1]) feather(FAN[i-1], k);
}
module above(i) { for (j = [i+1:NT-1]) tier_footprint(j); }

// the part of a shape that gets color c, given its [fill, rim, vein] colors
module colored(cols, c) {
    if (cols[1] == c) difference() { children(0); offset(delta = -RIM) children(0); }
    if (cols[0] == c) difference() { offset(delta = -RIM) children(0); if (cols[2] >= 0) children(1); }
    if (cols[2] == c) intersection() { offset(delta = -RIM) children(0); children(1); }
}
// everything in front of the leading edge - feathers may not poke out there
module arm_front2d() {
    polygon(concat(
        [for (i = [0:NA]) let(t = i/NA) bz(t, WS) - NN(t) * arm_hw(t, WS)],
        [bz(1, WS) + TT(1) * WS * 8],
        [bz(1, WS) + TT(1) * WS * 60],
        [for (i = [NA:-1:0]) let(t = i/NA) bz(t, WS) - NN(t) * (arm_hw(t, WS) + WS * 80)]));
}
// keep the wing out of the helmet's socket (the peg goes there)
// (down to where the socket's sloped underside passes the wing's back face)
WCLIP_BOT = VBOT - SOCK_DV * NOUT / (NOUT - NIN + SOCK_D) - sc(4);
module wing_clip() {
    translate([-BIG, WCLIP_BOT]) square([BIG + USOCK + sc(5), -WCLIP_BOT]);
}
module tier_color2d(i, c) {
    difference() {
        if (i == 0) { if (c == 0) web2d(); }
        else if (i == NT - 2) colored(ARM_COL, c) { arm2d(); arm_vein(); }
        else if (i == NT - 1) head_color2d(c);
        else {
            r = FAN[i-1];
            for (k = [0:r[0]-1])
                difference() {
                    colored(r[7], c) { feather(r, k); feather_vein(r, k); }
                    if (k < r[0]-1) for (m = [k+1:r[0]-1]) feather(r, m);
                }
        }
        if (i < NT - 1) above(i);
        if (i < NT - 2) arm_front2d();
        if (i < NT - 1) wing_clip();
    }
}
module tab2d() {
    ch = min(TAB_W, TAB_H) * 0.12;
    polygon([[-TAB_W/2, EPS], [TAB_W/2, EPS], [TAB_W/2, -TAB_H + ch], [TAB_W/2 - ch, -TAB_H],
             [-TAB_W/2 + ch, -TAB_H], [-TAB_W/2, -TAB_H + ch]]);
}
// right wing, lying flat: u = toward back, v = up, decorated face = +Z
// Built as stacked slabs: slab j holds every row at least that tall, so
// same-color areas that touch at a corner get merged instead of leaving a
// non-manifold edge.
module close2d() { offset(delta = -0.01) offset(delta = 0.01) children(); }
module wing_right(c) {
    for (j = [1:NT-1]) {
        z0 = j == 1 ? 0 : tier_h(j - 1);
        translate([0, 0, z0]) linear_extrude(tier_h(j) - z0)
            close2d() {
                for (i = [(j == 1 ? 0 : j):NT-1]) tier_color2d(i, c);
                if (c == 0 && j == 1) tab2d();
            }
    }
}
module wing_left(c) { mirror([1, 0, 0]) wing_right(c); }

// ================= output =================
echo(str("SCALE vs full size: ", S));
echo(str("Helmet interior (L x W x H above brow): ", 2*BK, " x ", 2*RI, " x ", HI, " mm"));
echo(str("Wing socket at x=", XM, " z=", ZM));

if (part == "assembly") {
    color(C_NAVY)  helmet_navy();
    color(C_GOLD)  helmet_gold();
    color(C_WHITE) helmet_white();
    for (m = [0, 1]) mirror([m, 0, 0]) wing_frame() {
        color(C_NAVY)  wing_right(0);
        color(C_GOLD)  wing_right(1);
        color(C_WHITE) wing_right(2);
    }
}
else if (part == "helmet_navy")  helmet_navy();
else if (part == "helmet_gold")  helmet_gold();
else if (part == "helmet_white") helmet_white();
else if (part == "wing_right_navy")  wing_right(0);
else if (part == "wing_right_gold")  wing_right(1);
else if (part == "wing_right_white") wing_right(2);
else if (part == "wing_left_navy")   wing_left(0);
else if (part == "wing_left_gold")   wing_left(1);
else if (part == "wing_left_white")  wing_left(2);
