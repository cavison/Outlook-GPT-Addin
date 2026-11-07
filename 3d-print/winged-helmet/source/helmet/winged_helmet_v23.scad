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
head_circumference = 579; // [500:1:660]   (hat size 7 1/4)
// Head length (front-to-back) / head width (side-to-side). 1.20-1.30 is typical
head_shape_ratio = 1.24; // [1.10:0.01:1.40]
// Eyebrow line to top of head (mm)
brow_to_crown = 120; // [90:1:150]
// Gap left for foam padding at sides/front/back (mm)
side_padding = 23; // [4:1:30]
// Gap left for foam padding at the front and back (mm)
fb_padding = 28; // [4:1:40]
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
dome_fullness = 2.2; // [2.0:0.1:3.5]
// Angle of the skirt below the brow (cheek guards and back). Negative = the guards
// lean in toward the chin, as in the reference pictures
skirt_flare = -4; // [-10:1:20]
brow_band_height = 47;
crest_gold_width = 22;
crest_white_width = 6;
front_letter_height = 74;
cheek_letter_height = 28;
// The face opening (eyes, nose guard, cheek-guard edges) is traced from the front
// reference picture: see face_trace.scad.  It scales with the helmet.
// The back of the helmet ends this far down, as a fraction of the cheek-guard depth
back_edge_depth = 0.87; // [0.5:0.01:1]
// Gold trim along all edges
edge_trim_width = 6.5;
// Gold scrollwork on the brow band (traced from the reference photo)
band_scrollwork = true;
// Wing size multiplier
wing_size = 1.8; // [0.8:0.05:3.0]
// Wings turned to face forward by this angle (degrees)
wing_yaw = 35; // [0:1:60]
// Wing tops lean outward by this angle (degrees)
wing_splay = -4; // [-15:1:25]
// Wing mount position, + toward the back (full-size mm)
wing_mount_offset = -25;
// How far the wings lean back from upright (degrees)
wing_sweep = 16; // [0:1:60]
// Height of the top of the wing peg, relative to the brow line (full-size mm; negative = below)
wing_mount_height = -52;

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
include <eagle_logo.scad>
include <band_motif.scad>
include <face_trace.scad>
include <band_path.scad>
include <wing_outline.scad>
include <wing_geom.scad>
include <wing_mid.scad>
include <wing_pegs.scad>
include <band_motif4.scad>
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
K    = (head_half_width * _q + fb_padding) / F_RI;      // front/back stretch
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
F_TAB_W = 30;  F_TAB_H = 18;  F_FLOOR = 3;  F_GAP = 2;

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
SW = wing_sweep;
F_VMAX  = max([for (p = arm_pts(wing_size)) -p[0] * sin(SW) + p[1] * cos(SW)]);   // wing tip height above the peg
// the face trace is in fractions of the band half-width (shell outer radius + 2 %)
F_CL    = -FACE_HALF[len(FACE_HALF) - 1][1] * (F_RI + full_wall) * 1.02;
F_DROP  = F_CL * 0.985;
SHAPE_H = wing_mount_height + F_VMAX * cos(SPL) + F_DROP;
NOUT_ABS = T0 + CLR + SWALL;
ABS_H   = SPL < 0 ? (T0 + TSTEP * 5) * sin(-SPL) : 0;
S = IS_MINI ? (mini_overall_height_in * 25.4 - ABS_H) / SHAPE_H : 1;

function sc(x) = x * S;
function ln(x) = max(x * S, MINL);

// ---------- scaled dimensions ----------
RI = F_RI * S;
HI = F_HI * S;
BK = RI * K;
BH = sc(brow_band_height);
PIPE = ln(4);
FACE_R0 = (RI + W) * 1.02;                       // the trace's unit length
CL = -FACE_HALF[len(FACE_HALF) - 1][1] * FACE_R0;  // cheek guards: brow to tip
NL = -FACE_HALF[0][1] * FACE_R0;                   // nose guard: brow to tip
NKL = back_edge_depth * CL;                        // back of the helmet
EN = sc(12);
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
// Face opening, traced from the straight-on front picture (face_trace.scad) and
// cut straight through from the front.  The brow is level over each eye and
// curves down into the nose guard; each cheek guard drops from a rounded outer
// corner, steps in, and runs down and in toward the chin to a point.
NHW  = FACE_NOSE_HW * FACE_R0;       // nose-guard half width at the top
NLEN = NL;
DIP  = -FACE_BROW[0][1] * FACE_R0;   // how far the brow dips where it meets the nose guard
XDIP = FACE_BROW[len(FACE_BROW) - 1][0] * FACE_R0;   // outer eye corner
function brow_z(x) = lookup(abs(x) / FACE_R0, FACE_BROW) * FACE_R0;
module face2d() {
    half = [for (p = FACE_HALF) p * FACE_R0];
    tip  = half[len(half) - 1];
    pts  = concat(half, [[tip[0], -3 * CL], [-tip[0], -3 * CL]],
                  [for (i = [len(half) - 1:-1:1]) [-half[i][0], half[i][1]]]);
    polygon(pts);
}
// side view (y, z): bottom edge
module bottom2d() {
    // the guards' tips are lowest; the edge rises gently past the ears and runs level round the back
    rr = sc(20);
    offset(r = rr) offset(delta = -rr)
        polygon([[-3*BK, -CL], [-0.70*BK, -CL], [0, -0.92*CL], [0.35*BK, -NKL], [3*BK, -NKL],
                 [3*BK, -BIG/4], [-3*BK, -BIG/4]]);
}
module face_prism()   { rotate([90, 0, 0]) linear_extrude(BIG) children(); }       // along -Y
module side_prism()   { rotate([90, 0, 90]) linear_extrude(BIG, center = true) children(); } // along X
module face_cut()     { face_prism() face2d(); }
module bottom_cut()   { side_prism() bottom2d(); }
module all_cuts()     { face_cut(); bottom_cut(); nose_cut(); }
// the nose guard is its own snap-on piece: the shell stops at the brow line between the eyes
module nose_cut()     { face_prism() translate([-NHW - 0.01, -BIG]) square([2 * NHW + 0.02, BIG - DIP]); }

// ================= wing mount (socket) =================
// local wing frame: u = along wing (toward back), v = up, n = out of wing face
function loc2w(p) = let(
    x = p[2], y = p[0], z = p[1],
    x1 = x*cos(SPL) + z*sin(SPL), z1 = -x*sin(SPL) + z*cos(SPL),
    x2 = x1*cos(YAW) + y*sin(YAW), y2 = -x1*sin(YAW) + y*cos(YAW)) [x2, y2, z1];

ZM = sc(wing_mount_height);
YM = sc(wing_mount_offset);
_corners = [for (u = [-USOCK, USOCK]) for (v = [VBOT, 0]) loc2w([u, v, NIN])];
XM = max([for (d = _corners) x_out(YM + d[1], ZM + d[2]) - d[0]]);

module wing_frame() {
    translate([XM, YM, ZM]) rotate([0, 0, -YAW]) rotate([0, SPL, 0])
        rotate([90, 0, 90]) children();
}
SOCK_D  = (NOUT - NIN) + sc(14);              // how far the socket's sloped underside reaches in
SOCK_DV = 1.15 * (SOCK_D + NOUT - NIN);       // ... and down
// g grows the block slightly (used to keep other details a hair away from it)
module socket_local(g = 0) {
    D  = SOCK_D;
    DV = SOCK_DV;
    hull() {
        translate([-USOCK - g, VBOT - g, NIN - g]) cube([2*USOCK + 2*g, -VBOT + 2*g, NOUT - NIN + 2*g]);
        translate([-USOCK - g, VBOT - DV - g, NIN - D - g]) cube([2*USOCK + 2*g, -VBOT + 2*g, EPS]);
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
// band details stop 0.05 mm short of the socket so the two never share an edge
module socket_zone() { for (m = [0, 1]) mirror([m, 0, 0]) wing_frame() socket_local(0.05); }

// ================= raised details =================
module polyline2d(pts, w) {
    for (i = [0:len(pts)-2]) hull() {
        translate(pts[i])   circle(d = w, $fn = 12);
        translate(pts[i+1]) circle(d = w, $fn = 12);
    }
}
module crest_slab(x0, x1) {
    translate([x0, -BIG/2, BH + BRR * 1.1]) cube([x1 - x0, BIG, BIG]);
}
module glyph(txt, h, flip = false) {
    mirror([flip ? 1 : 0, 0])
        resize([0, h], auto = true)
            text(txt, size = 10, font = letter_font, halign = "center", valign = "center");
}
// collegiate block "H" (unit box, centred): wide stems, slab serifs, narrow counters
module block_H() {
    bo = 0.035; si = 0.42; bi = 0.335; sh = 0.21; c0 = 0.40; c1 = 0.60;
    translate([-0.5, -0.5]) offset(r = 0.012) offset(delta = -0.012) union() {
        for (m = [0, 1]) translate([m, 0]) mirror([m, 0]) {
            translate([bo, 0]) square([bi - bo, 1]);
            square([si, sh]);
            translate([0, 1 - sh]) square([si, sh]);
        }
        translate([bi, c0]) square([1 - 2 * bi, c1 - c0]);
    }
}
// "H" uses the block letter above; any other letter falls back to letter_font
module letter2d(txt, h, flip = false) {
    if (txt == "H") mirror([flip ? 1 : 0, 0]) scale(h) block_H();
    else glyph(txt, h, flip);
}

// --- front letter: navy outline, white outline, gold face, stacked like a varsity patch ---
LET_H  = sc(front_letter_height);
LET_Z  = BH * 0.62 + LET_H / 2;            // bottom of the letter sits over the top of the band
LET_OW = max(sc(3.2), MINL);
LET_ON = max(sc(4.2), MINL);
LR_N = RL * 2.6;  LR_W = RL * 3.4;  LR_G = RL * 4.2;
module front_letter2d() { translate([0, LET_Z]) letter2d(front_letter, LET_H); }
module front_white2d()  { offset(r = LET_OW) front_letter2d(); }
module front_navy2d()   { offset(r = LET_ON) front_white2d(); }
// the letter's whole footprint with its counters filled: nothing else shows through the letter
module front_cover2d()  { offset(r = -0.2 * LET_H) offset(r = 0.2 * LET_H) front_navy2d(); }
module letter_navy()  { intersection() { layer(W * 0.5, W + LR_N); face_prism() difference() { front_navy2d(); front_white2d(); } } }
module letter_white() { intersection() { skin(LR_W); face_prism() difference() { front_white2d(); front_letter2d(); } } }
module letter_gold()  { intersection() { skin(LR_G); face_prism() front_letter2d(); } }

module crest_white() {
    intersection() {
        skin(RL * 1.2);
        difference() {
            union() {
                crest_slab(sc(crest_gold_width)/2, sc(crest_gold_width)/2 + ln(crest_white_width));
                mirror([1, 0, 0])
                crest_slab(sc(crest_gold_width)/2, sc(crest_gold_width)/2 + ln(crest_white_width));
            }
            face_prism() front_cover2d();
        }
    }
}
module crest_gold() {
    intersection() {
        skin(RL * 2.0);
        difference() {
            crest_slab(-sc(crest_gold_width)/2, sc(crest_gold_width)/2);
            face_prism() front_cover2d();
        }
    }
}

// --- brow band: navy, rounded white rims, gold scrollwork, white pearls ---
BRR = max(sc(4.2), MINL * 0.6);            // rim bead radius
module bead_ring(z) {
    scale([1, K, 1]) rotate_extrude($fn = FN) translate([r_in(z) + W, z]) circle(r = BRR, $fn = 24);
}
// strip above the brow line where it dips to the nose guard (the bottom rim follows it)
module dip_strip2d() {
    intersection() {
        difference() { offset(r = BRR * 1.1) face2d(); face2d(); }
        translate([-(XDIP + sc(2)), -DIP - sc(0.5)]) square([2 * (XDIP + sc(2)), DIP + sc(0.5) + 2 * BRR]);
        difference() { translate([-BIG/2, -BIG/2]) square(BIG); translate([-NHW, -BIG/2]) square([2 * NHW, BIG]); }
    }
}
module band_rims() {
    difference() {
        union() {
            bead_ring(BH);
            difference() {
                bead_ring(0);
                translate([-XDIP - sc(1), -BIG, -BIG]) cube([2 * (XDIP + sc(1)), BIG, BIG + BRR + 1]);
            }
            intersection() { skin(BRR); face_prism() dip_strip2d(); }
        }
        solid_out();
        face_prism() front_cover2d();
        all_cuts();
        socket_zone();
    }
}

// scrollwork: traced points are [angle, t]; t is mapped onto the band height,
// following the dip at the front, and wrapped around the band in thin slices
RB    = r_in(BH / 2) + W;
M_T0  = BH - BRR * 1.3;
M_START = asin(min(0.95, (NHW + sc(2)) / RB)) + 1.5;
function m_zb(th, front) = (front ? brow_z(RB * sin(th)) : 0) + BRR * 1.3;
function m_th(phi) = M_START + (phi - 16.5);
function m_map(p, front) = let(th = m_th(p[0]), zb = m_zb(th, front)) [th, zb + (1 - p[1]) * (M_T0 - zb)];
module motif_set2d(set, front) {
    pts   = [for (poly = set) for (p = poly) m_map(p, front)];
    start = [for (i = [0:len(set)-1]) i == 0 ? 0 : len([for (j = [0:i-1]) each set[j]])];
    polygon(pts, [for (i = [0:len(set)-1]) [for (k = [0:len(set[i])-1]) start[i] + k]]);
}
M_DA = 3;
module motif_relief(set, relief, front) {
    lo = m_th(16.5) - 1;  hi = m_th(78) + 1;
    n  = ceil((hi - lo) / M_DA);
    scale([1, K, 1]) intersection() {
        rotate_extrude($fn = FN) difference() { prof(W + relief); prof(W); }
        union() for (k = [0:n-1]) let(a = lo + (k + 0.5) * M_DA)
            rotate([0, 0, a]) translate([0, -(RB - sc(12)), 0]) rotate([90, 0, 0])
                linear_extrude(sc(24)) scale([PI / 180 * RB, 1]) translate([-a, 0])
                    intersection() {
                        motif_set2d(set, front);
                        translate([a - M_DA / 2 - 0.15, -BIG]) square([M_DA + 0.3, 2 * BIG]);
                    }
    }
}
module motif_all(set, relief) {
    if (band_scrollwork) difference() {
        union() {
            for (mx = [0, 1]) mirror([mx, 0, 0]) {
                motif_relief(set, relief, true);
                mirror([0, 1, 0]) motif_relief(set, relief, false);
            }
        }
        face_prism() front_cover2d();
        socket_zone();
    }
}

// keystone: the nose guard's gold trim carries on up the band to the letter, with a gold point under it
module keystone2d() {
    difference() {
        union() {
            difference() {
                translate([-NHW, -DIP - 1]) square([2 * NHW, LET_Z + 1 + DIP]);
                translate([-(NHW - TRIM), -DIP - 2]) square([2 * (NHW - TRIM), BIG]);
            }
            yb = LET_Z - LET_H / 2 - LET_ON;
            polygon([[-NHW + TRIM, yb], [NHW - TRIM, yb], [0, yb - 0.9 * NHW]]);
        }
        front_cover2d();
    }
}
module keystone() { intersection() { skin(RL * 1.6); face_prism() keystone2d(); } }

// --- rivets ---
RIV = ln(6);
module front_rivet(z, d) { face_prism() translate([0, z]) circle(d = d); }
// stamp a 2D shape onto the side of the helmet, square to the surface
module side_stamp(th, z) {
    scale([1, K, 1]) rotate([0, 0, th]) translate([0, -(r_in(z) + W - sc(8)), z]) rotate([90, 0, 0])
        linear_extrude(sc(16)) children();
}
CHEEK_TH  = 55;                          // cheek letter position, degrees from the front
RIVET_TH  = 63;                          // cheek rivet near the top-front corner, degrees from the front
module rivets_gold() {
    intersection() {
        skin(RL * 1.8);
        union() {
            front_rivet(BH * 0.18, RIV);
            front_rivet(-DIP - 0.62 * NLEN, RIV);
        }
    }
}
module rivets_white() {
    intersection() {
        skin(RL * 1.8);
        union() {
            front_rivet(-DIP - 0.30 * NLEN, RIV);
            for (m = [0, 1]) mirror([m, 0, 0]) side_stamp(RIVET_TH, -0.10 * CL) circle(d = RIV);
        }
    }
}

// --- edge trim (gold): cheek-guard fronts, nose guard, bottom edges ---
module edge_trim() {
    difference() {
        intersection() {
            skin(RL * 1.6);
            union() {
                face_prism() difference() {
                    intersection() {
                        difference() { offset(delta = TRIM) face2d(); face2d(); }
                        translate([-BIG/2, -BIG - BRR * 1.05]) square([BIG, BIG]);
                    }
                    // the white rim covers the dip above the eyes
                    for (m = [0, 1]) mirror([m, 0]) translate([NHW, -DIP - BRR]) square([XDIP + sc(2) - NHW, BIG]);
                }
                side_prism() difference() { offset(delta = TRIM) bottom2d(); bottom2d(); }
            }
        }
        all_cuts();
    }
}

// --- cheek letters (white) ---
module cheek_letters() {
    if (cheek_letter != "")
        intersection() {
            skin(RL * 1.6);
            for (m = [0, 1]) mirror([m, 0, 0])
                side_stamp(CHEEK_TH, -0.72 * CL) letter2d(cheek_letter, sc(cheek_letter_height), m == 1);
        }
}

// ================= helmet color bodies =================
module helmet_navy() {
    union() {
        difference() { layer(0, W); all_cuts(); }
        letter_navy();
    }
}
module helmet_gold() {
    union() {
        crest_gold();
        letter_gold();
        motif_all(MOTIF_GOLD, RL * 1.4);
        keystone();
        rivets_gold();
        edge_trim();
        sockets();
    }
}
module helmet_white() {
    union() {
        crest_white();
        letter_white();
        band_rims();
        motif_all(MOTIF_WHITE, RL * 1.8);
        rivets_white();
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
PIV = [16, 26];                 // shoulder: the lower feathers radiate from here
// ---- upper wing: long stripes running parallel to the gold leading edge ----
UPN  = 6;                       // number of stripes
UPSP = 11;                      // stripe spacing
UPW  = 17;                      // stripe width (wider than spacing, so they overlap)
UPTS = 0.04;                    // where along the leading edge they start
// stripe colors [fill, rim, vein], outermost (next to the leading edge) first
UPCOL = [[2, 1, -1], [0, 1, 2], [1, 0, -1], [0, 1, 2], [2, 1, -1], [0, 1, -1]];
function up_te(i)      = 1.0 - 0.085 * i;                      // inner stripes end earlier
function up_t(i, s)    = UPTS + (up_te(i) - UPTS) * s;
function up_off(i, s)  = WS * (UPSP * (i + 0.5) + (5 + 3 * i) * s * s);   // flare out at the tip
function up_spine(i, s) = let(t = up_t(i, s)) bz(t, WS) + NN(t) * (arm_hw(t, WS) + up_off(i, s));
function up_w(s)       = WS * UPW / 2 * min(1, pow(max(0, (1 - s) / 0.3), 0.7));
function up_pts(i) = let(n = 40) concat(
    [for (j = [0:n]) let(s = j/n, t = up_t(i, s)) up_spine(i, s) - NN(t) * up_w(s)],
    [for (j = [n:-1:0]) let(s = j/n, t = up_t(i, s)) up_spine(i, s) + NN(t) * up_w(s)]);
module up_feather(i) { rotate(-SW) polygon(up_pts(i)); }
module up_vein(i)    { rotate(-SW) polyline2d([for (j = [0:16]) up_spine(i, 0.12 + 0.62 * j/16)], VEIN); }

// ---- lower wing: feathers fanning down from the shoulder, plus shoulder coverts ----
// [count, angle_first, angle_last, base radius, length scale, width, curl, [fill, rim, vein]]
// angles in degrees from "straight back", positive = up
LOW = [
    [7,  8, -84, 10, 1.00, 26, 0.16, [0, 1, 2]],    // long hanging feathers: navy, gold edge, white streak
    [6,  2, -78, 10, 0.68, 24, 0.14, [1, 0, 2]]     // shorter layer: gold, navy edge, white streak
];
COV = [9, 70, -60, 6, 0.36, 18, 0.12, [0, 1, -1]]; // shoulder coverts: navy scallops, gold edge
ARM_COL = [1, 0, 2];            // leading edge: gold, navy edge, white stripe
LOGO_C   = [8, 44];             // eagle-head logo centre, relative to the top of the peg (full-size mm)
LOGO_W   = 100;                 // logo width (full-size mm)
LOGO_HALO = 1.5;                // extra navy border around the logo (full-size mm)
LOGO_RING = 2.5;                // gold outer ring, like a varsity patch (full-size mm)
LOGO_ROT = 0;                   // logo rotation, degrees
LOGO_PAD = IS_MINI ? 0.2 : 0;   // thickens the logo's navy lines so they print at small sizes
NT   = 7;                       // web, long lower, stripes, short lower, coverts, leading edge, head
RIM  = ln(2.5);
VEIN = ln(2.5);
NF   = 24;
function tier_h(i) = T0 + TSTEP * max(0, i - 1);

function fan_len(a) = a >= 0 ? 112 : (62 + 40 * pow(-a / 80, 1.4)) / wing_size;
function fa_ang(r, k)  = r[1] + (r[2] - r[1]) * k / (r[0] - 1);
function fa_dir(r, k)  = let(a = fa_ang(r, k)) [cos(a), sin(a)];
function fa_base(r, k) = WS * (PIV + fa_dir(r, k) * r[3]);
function fa_len(r, k)  = WS * fan_len(min(fa_ang(r, k), 0)) * r[4];
function fa_wid(r, k)  = WS * r[5];
function perpR(v)      = [v[1], -v[0]];
function fe_spine(b, d, L, cu, s) = b + d * L * s + perpR(d) * (cu * L * s * s);
function fe_norm(d, L, cu, s)     = let(t = unit(d * L + perpR(d) * (2 * cu * L * s))) [-t[1], t[0]];
function fe_half(w, s)            = w / 2 * pow(max(0, 1 - pow(s, 2.2)), 0.6);
function fe_pts(r, k) = let(b = fa_base(r, k), d = fa_dir(r, k), L = fa_len(r, k), w = fa_wid(r, k), cu = r[6])
    concat([for (i = [0:NF]) let(s = i/NF) fe_spine(b, d, L, cu, s) + fe_norm(d, L, cu, s) * fe_half(w, s)],
           [for (i = [NF:-1:0]) let(s = i/NF) fe_spine(b, d, L, cu, s) - fe_norm(d, L, cu, s) * fe_half(w, s)]);
module feather(r, k) { rotate(-SW) polygon(fe_pts(r, k)); }
module feather_vein(r, k) {
    b = fa_base(r, k);  d = fa_dir(r, k);  L = fa_len(r, k);  w = fa_wid(r, k);  cu = r[6];
    rotate(-SW) polyline2d([for (i = [0:12]) let(s = 0.14 + 0.64 * i/12)
        fe_spine(b, d, L, cu, s) + fe_norm(d, L, cu, s) * fe_half(w, s) * 0.2], VEIN);
}
RW = TAB_W/2 + sc(3);
module root_block() {
    rr = S * 5;
    hull() {
        translate([-RW, 0]) square([2*RW, EPS]);
        translate([-RW + rr, S*18 - rr]) circle(rr);
        translate([ RW - rr, S*18 - rr]) circle(rr);
    }
}
module arm2d() { union() { rotate(-SW) polygon(arm_pts(WS)); root_block(); } }
module arm_vein() { rotate(-SW) polyline2d([for (i = [0:30]) bz(0.05 + 0.85*i/30, WS)], VEIN); }

// eagle head facing forward, hooked beak
// ---- eagle-head logo at the shoulder (traced from the supplied artwork, see eagle_logo.scad)
// navy = logo outline and linework, white = head, gold = beak
module logo_at() { translate(S * LOGO_C) rotate(LOGO_ROT) scale(S * LOGO_W) children(); }
module logo_white() { offset(delta = -LOGO_PAD) logo_at() logo_set(LOGO_WHITE); }
module logo_gold()  { offset(delta = -LOGO_PAD) logo_at() logo_set(LOGO_GOLD); }
module logo_navy_edge() { offset(r = S * LOGO_HALO) logo_at() logo_set(LOGO_SIL); }
module head2d() { offset(r = max(S * LOGO_RING, MINL)) logo_navy_edge(); }
module head_color2d(c) {
    if (c == 0) difference() { logo_navy_edge(); logo_white(); logo_gold(); }
    if (c == 1) union() { logo_gold(); difference() { head2d(); logo_navy_edge(); } }
    if (c == 2) logo_white();
}

// solid web under everything so the wing prints as one piece
module web2d() { rotate(-SW) web2d_raw(); }
module web2d_raw() {
    r = LOW[0];
    for (k = [0:r[0]-2]) hull() {
        translate(WS * PIV) circle(d = WS * 30);
        translate(fa_base(r, k))     circle(d = fa_wid(r, k));
        translate(fa_base(r, k + 1)) circle(d = fa_wid(r, k + 1));
        translate(fe_spine(fa_base(r, k), fa_dir(r, k), fa_len(r, k), r[6], 0.45)) circle(d = fa_wid(r, k) * 0.7);
        translate(fe_spine(fa_base(r, k+1), fa_dir(r, k+1), fa_len(r, k+1), r[6], 0.45)) circle(d = fa_wid(r, k+1) * 0.7);
    }
    i = UPN - 1;  n = 12;
    for (j = [0:n-1]) hull() {
        translate(bz(up_t(i, j/n), WS))     circle(d = WS * 6);
        translate(bz(up_t(i, (j+1)/n), WS)) circle(d = WS * 6);
        translate(up_spine(i, j/n))         circle(d = WS * 6);
        translate(up_spine(i, (j+1)/n))     circle(d = WS * 6);
    }
    hull() { translate(WS * PIV) circle(d = WS * 30); translate(up_spine(UPN - 1, 0)) circle(d = WS * 10); }
}
// tiers, bottom to top: 0 web, 1 long lower feathers, 2 stripes, 3 short lower feathers,
// 4 shoulder coverts, 5 leading edge, 6 eagle head
module tier_footprint(i) {
    if (i == 0) web2d();
    else if (i == 1) for (k = [0:LOW[0][0]-1]) feather(LOW[0], k);
    else if (i == 2) for (j = [0:UPN-1]) up_feather(j);
    else if (i == 3) for (k = [0:LOW[1][0]-1]) feather(LOW[1], k);
    else if (i == 4) for (k = [0:COV[0]-1]) feather(COV, k);
    else if (i == 5) arm2d();
    else head2d();
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
    rotate(-SW) polygon(concat(
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
module fan_row_color2d(r, c) {
    for (k = [0:r[0]-1])
        difference() {
            colored(r[7], c) { feather(r, k); feather_vein(r, k); }
            if (k < r[0]-1) for (m = [k+1:r[0]-1]) feather(r, m);
        }
}
module tier_color2d(i, c) {
    difference() {
        if (i == 0) { if (c == 0) web2d(); }
        else if (i == 1) fan_row_color2d(LOW[0], c);
        else if (i == 2)                       // inner stripes underneath, outer ones on top
            for (j = [UPN-1:-1:0])
                difference() {
                    colored(UPCOL[j], c) { up_feather(j); up_vein(j); }
                    if (j > 0) for (m = [0:j-1]) up_feather(m);
                }
        else if (i == 3) fan_row_color2d(LOW[1], c);
        else if (i == 4) fan_row_color2d(COV, c);
        else if (i == 5) colored(ARM_COL, c) { arm2d(); arm_vein(); }
        else head_color2d(c);
        if (i < NT - 1) above(i);
        if (i < NT - 2) arm_front2d();
        wing_clip();
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

// ================= brow band and nose-guard strap (from the new pictures) =================
// The band runs level across the front with its bottom rim on the brow line,
// drops behind the wings and dips into a gold V at the back.  Heights are tables
// round the helmet (band_path.scad); the scrollwork is traced (band_motif2.scad).
// Full-size relief above the shell, mm (the mini scales these, with a printable floor)
function rel(x) = max(sc(x), 0.2);
B_BASE  = rel(3.0);     // navy band and strap
B_SCRL  = rel(3.9);     // gold scrollwork
B_RIM   = rel(4.3);     // white rims
B_DOT   = rel(4.5);     // white dots in the scrollwork
B_EDGE  = rel(4.3);     // gold strap border, gold V at the back
B_RIV   = rel(5.0);     // strap rivets
RIM_TW  = sc(5.0);      // top rim width
RIM_BW  = sc(5.7);      // bottom rim width
A0      = RI + W;       // outer radius at the brow line
TH_EYE  = asin(min(1, FACE_BROW[len(FACE_BROW) - 1][0] * FACE_R0 / A0));
function band_top(th) = lookup(abs(th), BAND_TOP_V) * FACE_R0;
function band_bot(th) = abs(th) <= TH_EYE ? brow_z(A0 * sin(abs(th)))
                                          : lookup(abs(th), BAND_BOT_V) * FACE_R0;
function fld_top(th) = band_top(th) - RIM_TW;
function fld_bot(th) = band_bot(th) + RIM_BW;
// a closed ring of material between two heights that vary round the helmet,
// from radius r1 to r2 (circular frame; scale by K afterwards)
B_DTH = 2;
module ring_between(lo, hi, r1, r2) {      // lo, hi: lists of heights at th = -180, -178, ... 178
    n = len(lo);
    pts = [for (i = [0:n-1]) let(th = -180 + B_DTH * i, c = cos(th), s_ = sin(th))
             each [[r1 * s_, -r1 * c, lo[i]], [r2 * s_, -r2 * c, lo[i]],
                   [r2 * s_, -r2 * c, hi[i]], [r1 * s_, -r1 * c, hi[i]]]];
    faces = [for (i = [0:n-1]) let(j = (i + 1) % n) for (k = [0:3]) let(k2 = (k + 1) % 4)
             each [[4*i + k, 4*j + k2, 4*j + k], [4*i + k, 4*i + k2, 4*j + k2]]];
    polyhedron(pts, faces, convexity = 6);
}
function ths_ring() = [for (i = [0:360/B_DTH - 1]) -180 + B_DTH * i];
module band_zone(lo, hi) { scale([1, K, 1]) ring_between(lo, hi, RI * 0.6, RI * 1.4); }
module band_layer(t) { layer(W - 0.01, W + t); }

// scrollwork: [angle, t] -> [angle, z] between the rims, wrapped round in thin slices
function bm_map(p) = let(th = p[0]) [th, fld_top(th) - p[1] * (fld_top(th) - fld_bot(th))];
module bm_set2d(set) {
    pts   = [for (poly = set) for (p = poly) bm_map(p)];
    start = [for (i = [0:len(set)-1]) i == 0 ? 0 : len([for (j = [0:i-1]) each set[j]])];
    polygon(pts, [for (i = [0:len(set)-1]) [for (k = [0:len(set[i])-1]) start[i] + k]]);
}
BM_DA = 3;
module bm_relief(set, t, lo, hi) {
    n = ceil((hi - lo) / BM_DA);
    scale([1, K, 1]) intersection() {
        rotate_extrude($fn = FN) difference() { prof(W + t); prof(W - 0.01); }
        union() for (k = [0:n-1]) let(a = lo + (k + 0.5) * BM_DA,
                                       rb = r_in((fld_top(a) + fld_bot(a)) / 2) + W)
            rotate([0, 0, a]) translate([0, -(rb - sc(14)), 0]) rotate([90, 0, 0])
                linear_extrude(sc(28)) scale([PI / 180 * rb, 1]) translate([-a, 0])
                    intersection() {
                        bm_set2d(set);
                        translate([a - BM_DA / 2 - 0.15, -BIG]) square([BM_DA + 0.3, 2 * BIG]);
                    }
    }
}
module bm_both(set, t, lo, hi) { for (m = [0, 1]) mirror([m, 0, 0]) bm_relief(set, t, lo, hi); }

// white dots: true circles, pushed out radially through the band
module band_dot(dd) {
    th = dd[0]; z = bm_map([th, dd[1]])[1]; r = dd[2] * FACE_R0 / 2;
    rb = r_in(z) + W;
    scale([1, K, 1]) intersection() {
        rotate_extrude($fn = FN) difference() { prof(W + B_DOT); prof(W - 0.01); }
        rotate([0, 0, th]) translate([0, -(rb - sc(14)), z]) rotate([90, 0, 0]) cylinder(r = r, h = sc(28), $fn = 48);
    }
}

// gold V at the back centre (arc length from the centre line, height), full-size mm
CHV_W = 35; CHV_H = 60; CHV_NOTCH = 12; CHV_EDGE = 6;
function chv_side(t) = let(p0 = [CHV_W, 0], p1 = [CHV_W * 0.62, -CHV_H * 0.62], p2 = [0, -CHV_H])
    pow(1 - t, 2) * p0 + 2 * (1 - t) * t * p1 + t * t * p2;
module chevron2d() {
    right = [for (i = [0:16]) chv_side(i / 16)];
    scale(S) polygon(concat([[0, -CHV_NOTCH]], right, [for (i = [15:-1:1]) [-right[i][0], right[i][1]]], [[-CHV_W, 0]]));
}
CHV_Z = band_top(160) + sc(2);           // top corners of the V
module chevron_solid(inner) {           // wrapped onto the back like the scrollwork (one slab is enough here)
    rb = r_in(CHV_Z - sc(30)) + W;
    scale([1, K, 1]) intersection() {
        rotate_extrude($fn = FN) difference() { prof(W + (inner ? B_BASE + 0.05 : B_EDGE)); prof(W - 0.01); }
        rotate([0, 0, 180]) translate([0, -(rb - sc(14)), CHV_Z]) rotate([90, 0, 0]) linear_extrude(sc(28))
            if (inner) offset(delta = -sc(CHV_EDGE)) chevron2d();
            else difference() { chevron2d(); offset(delta = -sc(CHV_EDGE)) chevron2d(); }
    }
}
module chevron_zone() { scale([1, K, 1]) rotate([0, 0, 180]) translate([0, -BIG / 2, CHV_Z]) rotate([90, 0, 0]) linear_extrude(BIG, center = true) chevron2d(); }

// nose-guard strap (front view): the nose guard's outline carried on up the band to under the H
STRAP_TOP = 0.22;                         // top of the strap above the brow line (x band half-width)
STRAP_BORDER = sc(5.7);
function strap_half() = let(i0 = [for (i = [1:len(FACE_HALF) - 1]) if (FACE_HALF[i][0] > FACE_NOSE_HW + 0.02) i][0])
    concat([for (i = [0:i0 - 1]) FACE_HALF[i] * FACE_R0], [[FACE_NOSE_HW * FACE_R0, STRAP_TOP * FACE_R0], [0, STRAP_TOP * FACE_R0]]);
module strap2d() { h = strap_half(); polygon(concat(h, [for (i = [len(h) - 2:-1:1]) [-h[i][0], h[i][1]]])); }
module strap_inner2d() {          // the navy middle: no border along the top edge
    h = strap_half(); top = STRAP_TOP * FACE_R0;
    intersection() {
        strap2d();
        offset(delta = -STRAP_BORDER) polygon(concat([for (i = [0:len(h) - 3]) h[i]], [[h[len(h) - 2][0], top + sc(30)], [-h[len(h) - 2][0], top + sc(30)]],
                                                      [for (i = [len(h) - 3:-1:1]) [-h[i][0], h[i][1]]]));
    }
}
module strap_chevron2d() {        // gold point under the H
    w = FACE_NOSE_HW * FACE_R0 - STRAP_BORDER + 0.01; zt = STRAP_TOP * FACE_R0 + 0.01;
    polygon([[-w, zt], [w, zt], [0, zt - sc(12)]]);
}
RIVETS = [[0.011, 8.6, 1], [-0.166, 7.8, 2], [-0.342, 8.6, 1]];   // [height (x band half-width), diameter mm, 1 gold / 2 white]
module strap_part(c) {
    if (c == 0) intersection() { band_layer(B_BASE); face_prism() strap2d(); }
    if (c == 1) intersection() { band_layer(B_EDGE); face_prism() union() {
        difference() { strap2d(); strap_inner2d(); }
        strap_chevron2d(); } }
    for (r = RIVETS) if (r[2] == c) intersection() { band_layer(B_RIV); face_prism() translate([0, r[0] * FACE_R0]) circle(d = sc(r[1]), $fn = 32); }
}
module strap_zone() { face_prism() strap2d(); }

module band_part(c) {         // c: 0 navy, 1 gold, 2 white
    th = ths_ring();
    difference() {
        union() {
            if (c == 0) intersection() { band_layer(B_BASE); band_zone([for (a = th) band_bot(a)], [for (a = th) band_top(a)]); }
            if (c == 2) intersection() { band_layer(B_RIM); band_zone([for (a = th) fld_top(a)], [for (a = th) band_top(a)]); }
            if (c == 2) intersection() { band_layer(B_RIM); band_zone([for (a = th) band_bot(a)], [for (a = th) fld_bot(a)]); }
            if (c == 1) { bm_both(BAND_FRONT_GOLD, B_SCRL, 9, 71); bm_both(BAND_BACK_GOLD, B_SCRL, 107, 167); }
            if (c == 2) for (dd = concat(BAND_FRONT_DOTS, BAND_BACK_DOTS)) for (m = [0, 1]) mirror([m, 0, 0]) band_dot(dd);
            if (c == 1) chevron_solid(false);
        }
        strap_zone();
        h_zone(); crest_zone();
        if (c != 1) chevron_zone();
        if (c == 1) difference() { chevron_zone(); chevron_solid(false); }   // keep the scrollwork out of the V
        all_cuts();
    }
    if (c == 0) chevron_solid(true);
    strap_part(c);
}

// ================= printable pieces: upper helmet, cheek guards, neck guard =================
// The cheek guards are their own pieces: each is the navy plate inside its gold border,
// from the eye opening back past the ear (120 deg round, from the back picture), hanging
// from under the band.  A tongue along its top slides up inside the helmet and snaps in.
// The neck guard is the plain navy part under the band at the back.
// The upper helmet (dome, band zone, nose guard) is split front / back through the ears.
GUARD_TH_FRONT = 12;     // forward of this is the nose guard
GUARD_TH_BACK  = 120;    // cheek guard back edge
GUARD_BORDER   = sc(5.7);
GUARD_TONGUE   = sc(12); // how far the tongue reaches up inside the helmet
SPLIT_Y        = 0;      // front / back seam of the upper helmet
function bb(th) = band_bot(th > 180 ? 360 - th : th);
// open sector of material between two heights that vary round the helmet (circular frame)
module sector_between(th0, th1, lo, hi, r1, r2) {
    n = len(lo);
    dth = (th1 - th0) / (n - 1);
    pts = [for (i = [0:n-1]) let(th = th0 + dth * i, c = cos(th), s_ = sin(th))
             each [[r1 * s_, -r1 * c, lo[i]], [r2 * s_, -r2 * c, lo[i]],
                   [r2 * s_, -r2 * c, hi[i]], [r1 * s_, -r1 * c, hi[i]]]];
    side = [for (i = [0:n-2]) let(j = i + 1) for (k = [0:3]) let(k2 = (k + 1) % 4)
             each [[4*i + k, 4*j + k2, 4*j + k], [4*i + k, 4*i + k2, 4*j + k2]]];
    caps = [[0, 2, 1], [0, 3, 2], [4*(n-1), 4*(n-1) + 1, 4*(n-1) + 2], [4*(n-1), 4*(n-1) + 2, 4*(n-1) + 3]];
    polyhedron(pts, concat(side, caps), convexity = 4);
}
function th_list(th0, th1, step = 2) = let(n = max(1, ceil(abs(th1 - th0) / step))) [for (i = [0:n]) th0 + (th1 - th0) * i / n];
// below the band bottom, between two angles.  In front of the outer eye corner the band bottom is
// the top of the eye opening, so the zone stops 3 mm lower there: the brow strip stays with the upper helmet.
function zone_top(a) = bb(a) - (a < TH_EYE || a > 360 - TH_EYE ? sc(3) : 0);
module zone(th0, th1) {
    ths = th_list(th0, th1);
    scale([1, K, 1]) sector_between(th0, th1, [for (a = ths) -BIG / 8], [for (a = ths) zone_top(a)], RI * 0.5, RI * 1.5);
}
module guard_zone()  { for (m = [0, 1]) mirror([m, 0, 0]) zone(GUARD_TH_FRONT, GUARD_TH_BACK); }
module neck_zone()   { zone(GUARD_TH_BACK, 360 - GUARD_TH_BACK); }
module shell_solid() { difference() { layer(0, W); all_cuts(); } }

// cheek guard outline unrolled flat: s = arc length round the helmet (mm at GR_REF), z = height
GR_REF = RI + W;
function a_at(z) = r_in(z) + W;
function s_of(th) = th * PI / 180 * GR_REF;
I_CORNER = [for (i = [0:len(FACE_HALF) - 1]) if (FACE_HALF[i][0] == FACE_BROW[len(FACE_BROW) - 1][0]) i][0];
BOT_EDGE = [[-3 * BK, -CL], [-0.70 * BK, -CL], [0, -0.92 * CL], [0.35 * BK, -NKL], [3 * BK, -NKL]];
function z_bottom(th) = lookup(-K * a_at(-CL) * cos(th), BOT_EDGE);
function th_front(p) = let(z = p[1] * FACE_R0, x = p[0] * FACE_R0) asin(min(1, x / a_at(z)));
module guard_outline_sz() {
    front = [for (i = [len(FACE_HALF) - 1:-1:I_CORNER]) [s_of(th_front(FACE_HALF[i])), FACE_HALF[i][1] * FACE_R0]];
    th_tip = th_front(FACE_HALF[len(FACE_HALF) - 1]);
    bottom = [for (a = th_list(th_tip, GUARD_TH_BACK)) [s_of(a), z_bottom(a)]];
    top = [for (a = th_list(GUARD_TH_BACK, th_front(FACE_HALF[I_CORNER]))) [s_of(a), bb(a)]];
    polygon(concat([for (i = [len(front) - 1:-1:0]) front[i]], bottom, top));
}
module guard_border_sz() { difference() { guard_outline_sz(); offset(delta = -GUARD_BORDER) guard_outline_sz(); } }
// wrap a flat (s, z) drawing onto the outside of the helmet, between two angles, raised by t
module wrap_sz(th0, th1, t) {
    n = ceil((th1 - th0) / BM_DA);
    scale([1, K, 1]) intersection() {
        rotate_extrude($fn = FN) difference() { prof(W + t); prof(W - 0.01); }
        union() for (k = [0:n-1]) let(a = th0 + (k + 0.5) * BM_DA, rb = a_at(-CL / 2))
            rotate([0, 0, a]) translate([0, -(rb - sc(16)), 0]) rotate([90, 0, 0])
                linear_extrude(sc(32)) scale([PI / 180 * rb, 1]) translate([-a, 0])
                    intersection() {
                        scale([180 / (PI * GR_REF), 1]) children();
                        translate([a - BM_DA / 2 - 0.15, -BIG]) square([BM_DA + 0.3, 2 * BIG]);
                    }
    }
}
// pieces
module upper_piece(side) {     // side: -1 front, +1 back
    difference() {
        union() { shell_solid(); seam_rib(side); }
        guard_zone(); neck_zone();
        if (side < 0) nose_bump_holes();
        if (side < 0) translate([-BIG / 2, SPLIT_Y, -BIG / 2]) cube(BIG);
        else          translate([-BIG / 2, SPLIT_Y - BIG, -BIG / 2]) cube(BIG);
    }
}
// a tongue that runs up inside the upper shell from a lower piece's top edge, CON_C clear of the shell
// (below the edge it merges into the piece's own wall)
CON_C = 0.2;
module tongue(th0, th1) {
    ths = th_list(th0, th1);
    difference() {
        intersection() {
            difference() { layer(-W - CON_C, 0.01); all_cuts(); }
            scale([1, K, 1]) sector_between(th0, th1, [for (a = ths) bb(a) - W], [for (a = ths) bb(a) + GUARD_TONGUE], RI * 0.5, RI * 1.5);
        }
        intersection() {
            layer(-CON_C, W + 1);
            scale([1, K, 1]) sector_between(th0 - 1, th1 + 1, [for (a = th_list(th0 - 1, th1 + 1)) bb(a) - 0.01], [for (a = th_list(th0 - 1, th1 + 1)) bb(a) + GUARD_TONGUE + 1], RI * 0.5, RI * 1.5);
        }
    }
}
module guard_tongue() { tongue(TH_EYE + 6, GUARD_TH_BACK - 4); }
module neck_tongue()  { tongue(GUARD_TH_BACK + 4, 360 - GUARD_TH_BACK - 4); }
// cheek guard to neck plate: a lug inside the guard's back edge with a vertical hole, and a lug on the
// neck plate that reaches under it with a peg pointing up (both pieces slide up into place)
LUG_Z = -95; LUG_H = 8; LUG_T = 6; LUG_TH = 6;
module pie(th0, th1) {      // wedge between two angles, kept clear of the axis (inner layers also wrap the axis)
    a = th_list(th0, th1, 1); r0 = RI * 0.5;
    scale([1, K, 1]) linear_extrude(BIG, center = true)
        polygon(concat([for (t = a) [r0 * sin(t), -r0 * cos(t)]], [for (i = [len(a) - 1:-1:0]) [300 * sin(a[i]), -300 * cos(a[i])]]));
}
function lug_pt(th, z) = let(r = r_in(z) - LUG_T / 2) [r * sin(th), -K * r * cos(th)];
LUG_THC = GUARD_TH_BACK - LUG_TH / 2 - 0.5;
module guard_lug() {
    difference() {
        intersection() { layer_z(-LUG_T, 0.01, LUG_Z, LUG_Z + LUG_H); pie(GUARD_TH_BACK - LUG_TH - 0.5, GUARD_TH_BACK - 0.01); }
        translate(concat(lug_pt(LUG_THC, LUG_Z), [LUG_Z - 1])) cylinder(d = 3.2, h = LUG_H + 2, $fn = 24);
    }
}
module neck_lug() {
    union() {
        intersection() { layer_z(-LUG_T, -CON_C, LUG_Z - LUG_H, LUG_Z - CON_C); pie(GUARD_TH_BACK - LUG_TH - 0.5, GUARD_TH_BACK + LUG_TH); }
        intersection() { layer_z(-LUG_T, 0.01, LUG_Z - LUG_H, LUG_Z - CON_C); pie(GUARD_TH_BACK + 0.01, GUARD_TH_BACK + LUG_TH); }
        translate(concat(lug_pt(LUG_THC, LUG_Z), [LUG_Z - CON_C - 0.01])) { cylinder(d = 3, h = LUG_H - 1.2, $fn = 24); translate([0, 0, LUG_H - 1.2]) cylinder(d1 = 3, d2 = 2.2, h = 0.6, $fn = 24); }
    }
}
// seam ribs: thick strips inside each upper half along the front / back seam; dowel pins sit half in each
RIB_T = 6; RIB_HW = 9;
RIB_Z0 = max([for (a = [80:1:100]) bb(a)]) + GUARD_TONGUE + 1.5;   // start above the cheek guards' tongues (all along the rib's width)
module seam_rib(side) {
    difference() {
        intersection() { layer(-RIB_T, 0.01); translate([-BIG / 2, side < 0 ? SPLIT_Y - RIB_HW : SPLIT_Y, RIB_Z0]) cube([BIG, RIB_HW, BIG]); }
        all_cuts();
        scale([1, K, 1]) translate([0, 0, ZLOW - 1]) cylinder(r = RIB_T + 0.5, h = HI - RIB_T - 0.5 - ZLOW);   // inner layers also wrap the axis (stretched like the shell)
    }
}
// pocket in the cheek guard for the separate white cheek H
module cheek_h_pocket() {
    th = th_back_of(sc(CH_Z), sc(CH_BACK));
    intersection() {
        layer(W - 1.0, W + 1);
        on_surface(th, sc(CH_Z)) translate([0, 0, -sc(30)]) linear_extrude(sc(60)) offset(delta = 0.15) cheek_h2d();
    }
}
module guard_piece(c) {        // right-hand cheek guard (mirror for the left); c: 0 navy, 1 gold
    if (c == 0) difference() { union() { intersection() { shell_solid(); zone(GUARD_TH_FRONT, GUARD_TH_BACK); } guard_tongue(); guard_lug(); } cheek_h_pocket(); }
    if (c == 1) wrap_sz(GUARD_TH_FRONT, GUARD_TH_BACK + 3, B_EDGE) guard_border_sz();
}
module neck_piece() { union() { intersection() { shell_solid(); neck_zone(); } neck_tongue(); neck_lug(); mirror([1, 0, 0]) neck_lug(); } }

// ================= crest stripe and front H (from the new pictures) =================
// Crest: a stepped stripe over the top, from the band's V at the back to behind the H.
// White base (widest), gold layer on it, narrower raised gold rib down the middle.
CR_W  = [41, 31, 19];          // widths, full-size mm: white, gold layer, gold rib
CR_T  = [2.5, 4.0, 8.5];       // height above the shell, full-size mm
// Front H: a raised badge.  Gold letter on a white outline on a navy backing; the face is
// flat and leans back, so the badge stands off the dome more at its top (as in the side picture).
// Letter in band half-widths (u sideways, v up from the brow line), measured from the front picture.
H_OUT_S = 0.316; H_OUT_L = 0.263; H_IN_S = 0.051; H_IN_L = 0.1015;
H_TOP = 0.877; H_BOT = 0.262; H_BAR = [0.523, 0.653];
H_PTS = [[H_IN_S, H_TOP], [H_OUT_S, H_TOP], [H_OUT_S, 0.776], [H_OUT_L, 0.742], [H_OUT_L, 0.394], [H_OUT_S, 0.362],
         [H_OUT_S, H_BOT], [H_IN_S, H_BOT], [H_IN_S, 0.370], [H_IN_L, 0.400], [H_IN_L, H_BAR[0]],
         [-H_IN_L, H_BAR[0]], [-H_IN_L, 0.400], [-H_IN_S, 0.370], [-H_IN_S, H_BOT], [-H_OUT_S, H_BOT], [-H_OUT_S, 0.362],
         [-H_OUT_L, 0.394], [-H_OUT_L, 0.742], [-H_OUT_S, 0.776], [-H_OUT_S, H_TOP], [-H_IN_S, H_TOP], [-H_IN_S, 0.782],
         [-H_IN_L, 0.750], [-H_IN_L, H_BAR[1]], [H_IN_L, H_BAR[1]], [H_IN_L, 0.750], [H_IN_S, 0.782]];
H_WHITE_W = 2.0;  H_NAVY_W = 3.0;          // outline widths, full-size mm
H_T_GOLD = 1.6;   H_T_WHITE = 1.6;          // layer thicknesses, full-size mm
H_STAND_BOT = 7.7; H_STAND_TOP = 17;        // face stand-off from the shell at the bottom / top, full-size mm
H_ROUND = 1.5;
module h_gold2d()  { rr = sc(H_ROUND); offset(r = rr) offset(r = -2 * rr) offset(r = rr) scale(FACE_R0) polygon(H_PTS); }
module h_white2d() { offset(r = max(sc(H_WHITE_W), MINL)) h_gold2d(); }
module h_navy2d()  { offset(r = -sc(8)) offset(r = sc(8)) offset(r = max(sc(H_NAVY_W), MINL)) h_white2d(); }   // counters filled
HZ_B = H_BOT * FACE_R0 - sc(H_WHITE_W + H_NAVY_W);
HZ_T = H_TOP * FACE_R0 + sc(H_WHITE_W + H_NAVY_W);
function y_shell(z) = -K * (r_in(z) + W);
HY_B = y_shell(HZ_B) - sc(H_STAND_BOT);
H_ALPHA = atan(((y_shell(HZ_T) - sc(H_STAND_TOP)) - HY_B) / (HZ_T - HZ_B));   // lean back
// slab between depths d0..d1 behind the H face (measured square to the face)
module h_slab(d0, d1) { translate([0, HY_B, HZ_B]) rotate([-H_ALPHA, 0, 0]) translate([-BIG / 2, d0, -BIG / 2]) cube([BIG, d1 - d0, BIG]); }
module h_part(c) {            // 0 navy backing, 1 gold letter, 2 white outline
    tg = rel(H_T_GOLD); tw = rel(H_T_WHITE);
    if (c == 1) intersection() { face_prism() h_gold2d();  h_slab(0, tg); }
    if (c == 2) intersection() { face_prism() h_white2d(); h_slab(tg, tg + tw); }
    if (c == 0) difference() { intersection() { face_prism() h_navy2d(); h_slab(tg + tw, sc(80)); } solid_out(); }
}
module h_zone() { intersection() { face_prism() offset(r = sc(0.4)) h_navy2d(); h_slab(-1, sc(80)); } }

// crest: drawn in the side section (y, z) of the shell, square to its surface, then given its width
module section2d() { scale([K, 1]) union() { prof(W); mirror([1, 0]) prof(W); } }
CR_FRONT_Z = HZ_T - sc(14);                     // front end, tucked behind the H
CR_BACK_Z  = band_top(180) - RIM_TW * 0.5;      // white and gold layer end on the band's top rim
CR_RIB_Z   = CHV_Z - sc(CHV_NOTCH) - sc(2);     // the rib carries on down into the V
module cr_clip(zb) { union() { translate([0, zb]) square([BIG, BIG]); translate([-BIG, CR_FRONT_Z]) square([BIG, BIG]); } }
module cr_band2d(t, zb) { intersection() { difference() { offset(r = t) section2d(); offset(r = -sc(8)) section2d(); } cr_clip(zb); } }
module cr_tier(i) {
    zb = i == 2 ? CR_RIB_Z : CR_BACK_Z;
    difference() {
        rotate([90, 0, 90]) linear_extrude(sc(CR_W[i]), center = true) cr_band2d(sc(CR_T[i]), zb);
        solid_out();
        h_zone();
    }
}
// The crest is two single-colour parts, so neither needs filament swaps: a white base strip
// (full width, on the shell) and a gold top (gold layer + rib) that seats on it.  Each is cut in
// two to fit the bed; the joints are staggered (white at CR_CUT_WHITE, gold at CR_CUT_GOLD,
// shell seam at SPLIT_Y) so no two line up.
CR_CUT_WHITE = -45;   // full-size mm along y
CR_CUT_GOLD  = 45;
module crest_part(c) {        // 1 gold top, 2 white base
    if (c == 2) cr_tier(0);
    if (c == 1) difference() { union() { cr_tier(1); cr_tier(2); } rotate([90, 0, 90]) linear_extrude(sc(CR_W[0]) + 1, center = true) cr_band2d(sc(CR_T[0]), CR_RIB_Z - sc(20)); }
}
module crest_piece(c, side) { // side -1 front, +1 back
    cut = sc(c == 2 ? CR_CUT_WHITE : CR_CUT_GOLD);
    intersection() { crest_part(c); translate([-BIG / 2, side < 0 ? cut - BIG : cut, -BIG / 2]) cube(BIG); }
}
module crest_zone() { rotate([90, 0, 90]) linear_extrude(sc(CR_W[0]) + sc(0.4), center = true) cr_band2d(sc(12), CR_RIB_Z); }

// ================= wings (from the new pictures) =================
// Outline traced from the side picture.  The lower feathers hang straight down just outside
// the cheek guard; above the shoulder hinge the wing leans outward by WG_LEAN.
WG_X     = 110;    // inner face of the wing's lower part, full-size mm from the centre
WG_T     = 6;      // wing plate thickness (full size)
WG_HINGE = 40;     // hinge height above the brow line (full size)
WG_LEAN  = 25;     // outward lean of the upper wing, degrees
WG_YAW   = 0;      // wing turned so its back edge sits further out (degrees): shows its face from the front
WG_PIVOT = 10;     // front-back position of the shoulder, full-size mm
module wing_outline2d() { scale(S) polygon(WING_OUTLINE); }
// upper part is stretched so that, once leaned, it looks the same as in the side picture
module wing_upper2d() { translate([0, sc(WG_HINGE)]) scale([1, 1 / cos(WG_LEAN)]) translate([0, -sc(WG_HINGE)])
    intersection() { wing_outline2d(); translate([-BIG / 2, sc(WG_HINGE)]) square(BIG); } }
module wing_lower2d() { intersection() { wing_outline2d(); translate([-BIG / 2, sc(WG_HINGE) - BIG]) square(BIG); } }
// 2D (u, v) drawn in the plane x = 0, u along +y, v along +z
module in_side_plane() { rotate([90, 0, 90]) children(); }
module wing_flat(t) {     // right wing (+x), plate of thickness t
    translate([sc(WG_X), sc(WG_PIVOT), 0]) rotate([0, 0, -WG_YAW]) translate([0, -sc(WG_PIVOT), 0]) {
        in_side_plane() linear_extrude(t) wing_lower2d();
        translate([0, 0, sc(WG_HINGE)]) rotate([0, WG_LEAN, 0]) translate([0, 0, -sc(WG_HINGE)])
            in_side_plane() linear_extrude(t) wing_upper2d();
    }
}

// ================= gold-tipped wing, layered like a real wing =================
// Navy wing plate; long and hanging feathers on it (navy, gold tips, white shafts); two rows of
// scallop feathers stepped up over their bases; the eagle medallion on top.  The wing is flat
// (each piece prints flat, decorated face up), leaned out slightly and turned to face forward.
WP_T  = 2.5;                                  // plate thickness of each half (full size)
WP_M  = 4.0;                                  // white middle layer (core) thickness, full size
WP_H  = [2.0, 3.4, 4.8, 5.6, 6.6];             // heights above the plate: L1, L2, L3, medallion, logo
// the wing's back face carries the same feather design (mirrored), so the plate's centre sits
// further out by the back decoration's height
TWO_SIDED = true;
WP_X  = (RI + W) - 14.6 + (TWO_SIDED ? WP_H[4] + WP_T + WP_M / 2 : 0);   // wing centre plane
WP_LEAN = 4;  WP_YAW = 15;  WP_PIVOT_Y = -60;
WP_ZB = -135;                                 // lean pivots about the wing's bottom edge
function wh(i) = max(sc(WP_H[i]), 0.2 * (i + 1));
function wt() = max(sc(WP_T), 1.0);
function wm() = max(sc(WP_M), 1.2);
module wp_place() {
    translate([sc(WP_X), sc(WP_PIVOT_Y), 0]) rotate([0, 0, -WP_YAW]) translate([0, -sc(WP_PIVOT_Y), 0])
        translate([0, 0, sc(WP_ZB)]) rotate([0, WP_LEAN, 0]) translate([0, 0, -sc(WP_ZB)])
            in_side_plane() children();
}
module wp_layer(z0, z1) { translate([0, 0, z0]) linear_extrude(z1 - z0) scale(S) children(); }
module wp_logo(set) { translate(WG_MED_C + WG_LOGO_OFF) scale(WG_LOGO_W) logo_set(set); }
module wp_logo_halo() { offset(r = 1.5) wp_logo(LOGO_SIL); }
// front face decoration on the plate (w = 0..t), back face = the same decoration mirrored through
// the plate's back face, so both faces line up feather for feather
// w = 0 is the wing's centre plane: white core, then a front half and a mirrored back half.
// The core has pegs on both faces that snap into blind holes in each half (2 per wing piece).
function peg_d()   = max(sc(5), 2.0);
function peg_len() = (wt() + wh(0)) * 0.7;
module core_pegs(clr = 0) {
    for (p = WG_PEGS) translate(concat(p * S, [-0.01])) cylinder(d = peg_d() + 2 * clr, h = peg_len() + clr, $fn = 32);
}
module wing_core() {
    translate([0, 0, -wm() / 2]) linear_extrude(wm()) scale(S) wg_set(WG_MID);
    for (m = [0, 1]) mirror([0, 0, m]) translate([0, 0, wm() / 2 - 0.02]) core_pegs();
}
module wing_half(c, back = false) { difference() { wing_face(c, back); core_pegs(CLR); } }
module wing_layers(c, ex = 0) {
    if (c == 2) wing_core();
    translate([0, 0, wm() / 2 - 0.01 + ex]) wing_half(c);
    if (TWO_SIDED) mirror([0, 0, 1]) translate([0, 0, wm() / 2 - 0.01 + ex]) wing_half(c, back = true);
}
module wing_face(c, back = false) {         // flat, in (u, v, out-of-plate) coordinates
    t = wt();
    if (c == 0) {
        wp_layer(0, wt()) wg_set(WG_PLATE);
        wp_layer(t - 0.01, t + wh(0)) wg_set(WG_L1_NAVY);
        wp_layer(t - 0.01, t + wh(2)) wg_set(WG_L3_NAVY);
        wp_layer(t - 0.01, t + wh(3)) translate(WG_MED_C) circle(r = WG_MED_R - WG_MED_RING, $fn = 96);
        wp_layer(t + wh(3) - 0.01, t + wh(4)) difference() { wp_logo_halo(); wp_logo(LOGO_WHITE); wp_logo(LOGO_GOLD); }
    }
    if (c == 1) {
        wp_layer(t - 0.01, t + wh(0)) wg_set(WG_L1_GOLD);
        wp_layer(t - 0.01, t + wh(1)) wg_set(WG_L2_GOLD);
        wp_layer(t - 0.01, t + wh(2)) wg_set(WG_L3_GOLD);
        wp_layer(t - 0.01, t + wh(3)) translate(WG_MED_C) difference() { circle(r = WG_MED_R, $fn = 96); circle(r = WG_MED_R - WG_MED_RING, $fn = 96); }
        wp_layer(t + wh(3) - 0.01, t + wh(4)) wp_logo(LOGO_GOLD);
    }
    if (c == 2) {
        wp_layer(t - 0.01, t + wh(0)) wg_set(WG_L1_WHITE);
        wp_layer(t - 0.01, t + wh(1)) wg_set(WG_L2_WHITE);
        wp_layer(t + wh(3) - 0.01, t + wh(4)) wp_logo(LOGO_WHITE);
    }
}
module wing_r(c) { wp_place() wing_layers(c); }

// ================= cheek H and rivet (from the new pictures) =================
// White block H on each cheek guard (same letter as the front H), tilted back to follow the
// guard, and a white rivet near the guard's top-front corner.  Positions are measured as distance
// round the guard from its front edge, and height below the brow line (full-size mm).
CH_H     = 30;    CH_TILT = 15;   CH_BACK = 36;  CH_Z = -72;   CH_RELIEF = 2.0;
RIV_D    = 7;     RIV_BACK = 26;  RIV_Z = -24;   RIV_RELIEF = 2.0;
function a_out(z) = r_in(z) + W;
// guard front edge angle at height z (from the face trace)
function guard_front_th(z) = let(zz = max(z, -CL + 1), pts = [for (i = [I_CORNER:len(FACE_HALF) - 1]) [FACE_HALF[i][1] * FACE_R0, FACE_HALF[i][0] * FACE_R0]],
                                  srt = [for (i = [len(pts) - 1:-1:0]) pts[i]], x = lookup(zz, srt)) asin(min(1, x / a_out(zz)));
// point and frame on the outer surface at angle th, height z (final, stretched frame)
function surf_pt(th, z) = [a_out(z) * sin(th), -K * a_out(z) * cos(th), z];
function surf_n(th) = let(n = [sin(th), -cos(th) / K]) n / norm(n);
module on_surface(th, z) {
    p = surf_pt(th, z); n = surf_n(th); t = [-n[1], n[0]];   // t: along the surface toward the back
    multmatrix([[t[0], 0, n[0], p[0]], [t[1], 0, n[1], p[1]], [0, 1, 0, p[2]], [0, 0, 0, 1]]) children();
}
function th_back_of(z, dist) = guard_front_th(z) + dist / a_out(z) * 180 / PI;
module cheek_h2d() { rotate(-CH_TILT) scale(sc(CH_H) / ((H_TOP - H_BOT) * FACE_R0)) translate([0, -(H_TOP + H_BOT) / 2 * FACE_R0]) h_gold2d(); }
module cheek_h(depth_below = 0) {            // right side; raised CH_RELIEF above the guard
    th = th_back_of(sc(CH_Z), sc(CH_BACK));
    intersection() {
        layer(W - depth_below, W + rel(CH_RELIEF));
        on_surface(th, sc(CH_Z)) translate([0, 0, -sc(30)]) linear_extrude(sc(60)) cheek_h2d();
    }
}
module cheek_rivet() {
    th = th_back_of(sc(RIV_Z), sc(RIV_BACK));
    on_surface(th, sc(RIV_Z)) translate([0, 0, -1]) scale([1, 1, (rel(RIV_RELIEF) + 1) / (sc(RIV_D) / 2)]) sphere(d = sc(RIV_D), $fn = 32);
}

// ================= layered band: three single-colour layers, no colour swaps =================
// White base, gold middle, navy top.  The navy layer has openings where the gold scrollwork,
// strap border and back V show; the gold layer has openings where the white rims and dots show.
BL_T = [1.2, 1.0, 1.0];                   // layer thicknesses (full size): white, gold, navy
function bl_z(i) = i == 0 ? 0 : BL_T[0] + (i > 1 ? BL_T[1] : 0) + (i > 2 ? BL_T[2] : 0);
module bl_slab(i) { layer(W + bl_z(i) - (i == 0 ? 0.01 : 0), W + bl_z(i + 1)); }
NOSE_STYLE = "over";     // "over": the nose strap lies on a complete band; "stub": the band carries the strap down to the brow
module band_area() {
    th = ths_ring();
    difference() {
        union() { band_zone([for (a = th) band_bot(a)], [for (a = th) band_top(a)]); if (NOSE_STYLE == "stub") strap_zone(); chevron_zone(); }
        h_zone(); crest_zone(); face_cut();
    }
}
module white_show() {    // strap and V cross over the rims; the strap's white rivet goes back in afterwards
    difference() { white_show_raw(); if (NOSE_STYLE == "stub") strap_zone(); chevron_zone(); }
    if (NOSE_STYLE == "stub") for (r = RIVETS) if (r[2] == 2) face_prism() translate([0, r[0] * FACE_R0]) circle(d = sc(r[1]), $fn = 32);
}
// gold strap border and point as one clean outline (strap minus its navy middle), so it stays a closed solid
module strap_gold2d() {
    w = FACE_NOSE_HW * FACE_R0 - STRAP_BORDER; zt = STRAP_TOP * FACE_R0; dz = sc(12); e = sc(2);
    difference() { strap2d(); difference() { strap_inner2d();
        polygon([[0, zt - dz], [w + e, zt], [w + e, zt + sc(10)], [-w - e, zt + sc(10)], [-w - e, zt]]); } }   // point overlaps the border, no pinch
}
module white_show_raw() {
    th = ths_ring();
    band_zone([for (a = th) fld_top(a)], [for (a = th) band_top(a) + 1]);
    band_zone([for (a = th) band_bot(a) - 1], [for (a = th) fld_bot(a)]);
    for (dd = concat(BAND_FRONT_DOTS, BAND_BACK_DOTS)) for (m = [0, 1]) mirror([m, 0, 0]) {
        z = bm_map([dd[0], dd[1]])[1]; r = dd[2] * FACE_R0 / 2; rb = r_in(z) + W;
        scale([1, K, 1]) rotate([0, 0, dd[0]]) translate([0, -(rb - sc(20)), z]) rotate([90, 0, 0]) cylinder(r = r, h = sc(40), $fn = 48);
    }
}
module gold_show() {
    bm_both(BAND_FRONT_GOLD, 10, 9, 71); bm_both(BAND_BACK_GOLD, 10, 107, 167);
    rb = r_in(CHV_Z - sc(30)) + W;
    scale([1, K, 1]) rotate([0, 0, 180]) translate([0, -(rb - sc(20)), CHV_Z]) rotate([90, 0, 0]) linear_extrude(sc(40))
        difference() { chevron2d(); offset(delta = -sc(CHV_EDGE)) chevron2d(); }
    if (NOSE_STYLE == "stub") face_prism() strap_gold2d();
    if (NOSE_STYLE == "stub") for (r = RIVETS) if (r[2] == 1) face_prism() translate([0, r[0] * FACE_R0]) circle(d = sc(r[1]), $fn = 32);
}
// ================= detachable nose piece =================
// One clip that slides up over the brow edge: the strap plate lies on the band outside, a tongue
// runs up inside the shell, and two bumps on the tongue click into holes in the shell (hidden
// under the band).  Below the brow the nose bar leans 10 deg forward for nose room.
// Gold body (border and the two gold rivets), a navy panel set into it, a white rivet pin.
BL_TOT    = BL_T[0] + BL_T[1] + BL_T[2];
NOSE_GAP  = 0.2;                 // clearance to the band and the shell
NOSE_PT   = 2.6;                 // strap plate thickness on the band
NOSE_TILT = 10;                  // forward lean of the bar below the brow
NOSE_TT   = 2.5;                 // tongue thickness
NOSE_UD   = 5;                   // depth of the clip's U below the brow edge
NOSE_TOP_T = 16;                 // tongue reaches this high inside (z, mm)
NOSE_THW  = 12;                  // tongue half width
NOSE_TAPER = 7; NOSE_TAPER_N = 10;   // the clip's back tapers into the bar over this height
NOSE_BUMP = [[-7, 8], [7, 8]];   // snap bumps (x, z)
BUMP_R = 1.6; BUMP_H = 0.8; BUMP_HOLE = 3.6;
PANEL_T   = 1.2;                 // navy panel thickness (flush with the gold face)
PANEL_CLR = 0.15;
RIV_SHANK = 4; RIV_HEAD = 1.0;   // white rivet pin: shank diameter, head height
N_OUT  = W + BL_TOT + NOSE_GAP + NOSE_PT;      // outer face of the strap (offset from the inner surface)
N_EDGE = -DIP - NOSE_GAP;                      // top of the clip's U (just under the shell edge)
N_HINGE = N_EDGE - NOSE_UD;                    // the bar leans forward below this height
module nose_shear() {          // lean everything below the hinge forward, keep everything above
    intersection() { children(); translate([-BIG / 2, -BIG / 2, N_HINGE]) cube(BIG); }
    translate([0, 0, N_HINGE]) multmatrix([[1, 0, 0, 0], [0, 1, tan(NOSE_TILT), 0], [0, 0, 1, 0]]) translate([0, 0, -N_HINGE])
        intersection() { children(); translate([-BIG / 2, -BIG / 2, N_HINGE - BIG]) cube(BIG); }
}
module nose_clip_h() { offset(r = sc(1.0)) h_navy2d(); }
module above2d(z) { translate([-BIG / 2, z]) square(BIG); }
module below2d(z) { translate([-BIG / 2, z - BIG]) square(BIG); }
module nose_navy2d() { difference() { strap2d(); strap_gold2d(); nose_clip_h(); } }
module nose_rivet2d(r, extra = 0) { translate([0, r[0] * FACE_R0]) circle(d = sc(r[1]) + extra, $fn = 40); }
module nose_body_raw() {
    difference() {
        union() {
            intersection() { layer(W + BL_TOT + NOSE_GAP, N_OUT); face_prism() difference() { intersection() { strap2d(); above2d(N_EDGE); } nose_clip_h(); } }
            intersection() { layer(-NOSE_GAP - NOSE_TT, N_OUT); face_prism() intersection() { strap2d(); above2d(N_HINGE - 0.01); below2d(N_EDGE); } }
            intersection() { layer(0, N_OUT); face_prism() intersection() { strap2d(); below2d(N_HINGE); } }
            // taper the back of the clip into the bar (no hard step under the brow)
            for (k = [0:NOSE_TAPER_N - 1]) let(t = (k + 1) / (NOSE_TAPER_N + 1))
                intersection() { layer_z(-(NOSE_GAP + NOSE_TT) * (1 - t), N_OUT, N_HINGE - NOSE_TAPER * (k + 1) / NOSE_TAPER_N, N_HINGE + 0.01);
                                 face_prism() strap2d(); }
            intersection() { layer(-NOSE_GAP - NOSE_TT, -NOSE_GAP); face_prism() translate([-NOSE_THW, N_EDGE - 1]) square([2 * NOSE_THW, NOSE_TOP_T - N_EDGE + 1]); }
        }
        intersection() { layer(N_OUT - PANEL_T, N_OUT + 1); face_prism() offset(delta = PANEL_CLR) nose_navy2d(); }
        for (r = RIVETS) if (r[2] == 2) intersection() { layer(N_OUT - PANEL_T - 4, N_OUT + 1); face_prism() nose_rivet2d(r, -sc(r[1]) + RIV_SHANK + 0.25); }
    }
    // gold rivet heads stand up through the navy panel
    for (r = RIVETS) if (r[2] == 1) intersection() { layer(N_OUT - PANEL_T - 0.1, N_OUT + RIV_HEAD); face_prism() nose_rivet2d(r); }
}
module nose_bumps() {
    for (b = NOSE_BUMP) let(r = r_in(b[1]) - NOSE_GAP, y = -K * sqrt(r * r - b[0] * b[0]))   // on the tongue's face
        intersection() {
            translate([b[0], y, b[1]]) sphere(r = BUMP_R, $fn = 32);
            translate([b[0] - BUMP_R, y - BUMP_H - NOSE_GAP, b[1] - BUMP_R]) cube([2 * BUMP_R, BUMP_H + NOSE_GAP + 1, 2 * BUMP_R]);
        }
}
module nose_bump_holes() { for (b = NOSE_BUMP) face_prism() translate(b) circle(d = BUMP_HOLE, $fn = 32); }
module nose_body() { intersection() { union() { nose_shear() nose_body_raw(); nose_bumps(); } translate([-BIG / 2, -BIG, -BIG / 2]) cube([BIG, BIG - RI * 0.5, BIG]); } }   // front only (inner layers also wrap the axis)
module nose_panel() {
    nose_shear() difference() {
        intersection() { layer(N_OUT - PANEL_T, N_OUT); face_prism() nose_navy2d(); }
        for (r = RIVETS) intersection() { layer(N_OUT - PANEL_T - 1, N_OUT + 1); face_prism() nose_rivet2d(r, r[2] == 1 ? 0.3 : -sc(r[1]) + RIV_SHANK + 0.3); }
    }
}
module nose_pin() {
    r = [for (q = RIVETS) if (q[2] == 2) q][0];
    nose_shear() union() {
        intersection() { layer(N_OUT, N_OUT + RIV_HEAD); face_prism() nose_rivet2d(r); }
        intersection() { layer(N_OUT - PANEL_T - 3.8, N_OUT + 0.01); face_prism() translate([0, r[0] * FACE_R0]) circle(d = RIV_SHANK, $fn = 32); }
    }
}

module band_layer_part(c) {          // 2 white base, 1 gold middle, 0 navy top
    if (c == 2) intersection() { bl_slab(0); band_area(); }
    if (c == 1) difference() { intersection() { bl_slab(1); band_area(); } white_show(); chevron_zone(); }
    if (c == 0) difference() { intersection() { bl_slab(2); band_area(); } white_show(); gold_show(); chevron_zone(); }
}
// the back V as two inserts the full height of the gold and navy layers, sitting on the white base
module chevron_prism(inset) { scale([1, K, 1]) rotate([0, 0, 180]) translate([0, -BIG / 2, CHV_Z]) rotate([90, 0, 0]) linear_extrude(BIG, center = true)
                                 if (inset) offset(delta = -sc(CHV_EDGE)) chevron2d(); else chevron2d(); }
module band_v_part(c) {              // 1 gold outline, 0 navy middle
    difference() {
        intersection() { layer(W + bl_z(1), W + bl_z(3)); if (c == 1) difference() { chevron_prism(false); chevron_prism(true); } else chevron_prism(true); }
        crest_zone(); all_cuts();
    }
}

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
else if (part == "shell") difference() { layer(0, W); all_cuts(); }
else if (part == "h_navy")  h_part(0);
else if (part == "h_gold")  h_part(1);
else if (part == "h_white") h_part(2);
else if (part == "crest_gold")  crest_part(1);
else if (part == "crest_white") crest_part(2);
else if (part == "crest_white_front") crest_piece(2, -1);
else if (part == "crest_white_back")  crest_piece(2, 1);
else if (part == "crest_gold_front")  crest_piece(1, -1);
else if (part == "crest_gold_back")   crest_piece(1, 1);
else if (part == "hc_preview") { color(C_NAVY) shell_solid(); color(C_NAVY) h_part(0); color(C_GOLD) h_part(1); color(C_WHITE) h_part(2); color(C_GOLD) crest_part(1); color(C_WHITE) crest_part(2); }
else if (part == "wing_flat_r") wing_flat(sc(WG_T));
else if (part == "wingB_navy")  wing_r(0);
else if (part == "wingB_gold")  wing_r(1);
else if (part == "wingB_white") wing_r(2);
else if (part == "wing_exploded") rotate([-62, 0, 0]) { color(C_NAVY) wing_layers(0, sc(90)); color(C_GOLD) wing_layers(1, sc(90)); color(C_WHITE) wing_layers(2, sc(90)); }
else if (part == "wingB_flat_preview") { color(C_NAVY) wing_layers(0); color(C_GOLD) wing_layers(1); color(C_WHITE) wing_layers(2); }
else if (part == "cheek_h")      cheek_h(rel(0.8));
else if (part == "cheek_rivet")  cheek_rivet();
else if (part == "nose_body")  nose_body();
else if (part == "nose_panel") nose_panel();
else if (part == "nose_pin")   nose_pin();
else if (part == "shell_nose") difference() { layer(0, W); all_cuts(); nose_bump_holes(); }
else if (part == "solid_out") solid_out();
else if (part == "bandV_gold") band_v_part(1);
else if (part == "bandV_navy") band_v_part(0);
else if (part == "neck_tongue_only") neck_tongue();
else if (part == "bandL_white") band_layer_part(2);
else if (part == "bandL_gold")  band_layer_part(1);
else if (part == "bandL_navy")  band_layer_part(0);
else if (part == "upper_front") upper_piece(-1);
else if (part == "upper_back")  upper_piece(1);
else if (part == "guard_navy")  guard_piece(0);
else if (part == "guard_gold")  guard_piece(1);
else if (part == "neck")        neck_piece();
else if (part == "split_preview") { color(C_NAVY) upper_piece(-1); color("#3B4F8C") upper_piece(1); color("#6A7FB8") guard_piece(0); color(C_GOLD) guard_piece(1); color("#9AA7CF") neck_piece(); }
else if (part == "band_navy")  band_part(0);
else if (part == "band_gold")  band_part(1);
else if (part == "band_white") band_part(2);
else if (part == "band_preview") { color(C_NAVY) difference() { layer(0, W); all_cuts(); } color(C_NAVY) band_part(0); color(C_GOLD) band_part(1); color(C_WHITE) band_part(2); }
// display aid only: a thin dark lining so the opening reads like the shadowed inside in the photo
else if (part == "shell_lining") difference() { layer(-0.6, 0); all_cuts(); cylinder(r = 3, h = BIG, center = true); }
else if (part == "helmet_navy")  helmet_navy();
else if (part == "helmet_gold")  helmet_gold();
else if (part == "helmet_white") helmet_white();
else if (part == "wing_right_navy")  wing_right(0);
else if (part == "wing_right_gold")  wing_right(1);
else if (part == "wing_right_white") wing_right(2);
else if (part == "wing_left_navy")   wing_left(0);
else if (part == "wing_left_gold")   wing_left(1);
else if (part == "wing_left_white")  wing_left(2);
