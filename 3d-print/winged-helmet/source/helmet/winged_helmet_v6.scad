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
brow_band_height = 38;
crest_gold_width = 22;
crest_white_width = 6;
front_letter_height = 74;
cheek_letter_height = 32;
cheek_guard_length = 120;
nasal_guard_length = 46;
neck_guard_length = 75;
// How far below the brow line the ear opening starts
ear_notch_depth = 12;
// Gold trim along all edges
edge_trim_width = 6.5;
// Gold scrollwork on the brow band (traced from the reference photo)
band_scrollwork = true;
// Wing size multiplier
wing_size = 1.0; // [0.6:0.05:1.5]
// Wings turned to face forward by this angle (degrees)
wing_yaw = 35; // [0:1:50]
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
include <eagle_logo.scad>
include <band_motif.scad>
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
// front view (x, z): face opening.  The brow line dips down to meet a short,
// shield-shaped nose guard, is level over the eyes, then turns down the cheek guards.
NHW  = sc(16);                       // nose-guard half width
NLEN = sc(nasal_guard_length);
DIP  = 0.10 * RI;                    // how far the brow line dips at the nose guard
XDIP = 0.32 * RI;                    // brow line is level again from here out
XT   = 0.76 * RI;                    // cheek-guard front edge at the top
function ease(u) = let(v = max(0, min(1, u))) v * v * (3 - 2 * v);
function brow_z(x) = let(ax = abs(x)) ax >= XDIP ? 0 : -DIP * (1 - ease((ax - NHW) / (XDIP - NHW)));
module face2d() {
    rr = sc(8);
    n  = 16;
    right = concat(
        [for (i = [0:n]) let(x = NHW + (XDIP - NHW) * i / n) [x, brow_z(x)]],
        [[XT, 0], [0.74 * RI, -0.25 * CL], [0.62 * RI, -0.6 * CL], [0.52 * RI, -0.9 * CL], [0.48 * RI, -3 * CL]]);
    pts = concat(
        right,
        [for (i = [len(right)-1:-1:0]) [-right[i][0], right[i][1]]],
        [[-NHW * 1.06, -DIP - 0.72 * NLEN], [0, -DIP - NLEN], [NHW * 1.06, -DIP - 0.72 * NLEN]]);
    offset(r = rr) offset(delta = -rr) polygon(pts);
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
BRR = max(sc(3), MINL * 0.6);              // rim bead radius
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
CHEEK_TH  = 63;                          // cheek letter position, degrees from the front
RIVET_TH  = 56;                          // cheek rivet near the top-front corner, degrees from the front
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
                side_stamp(CHEEK_TH, -0.5 * CL) letter2d(cheek_letter, sc(cheek_letter_height), m == 1);
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
module up_feather(i) { polygon(up_pts(i)); }
module up_vein(i)    { polyline2d([for (j = [0:16]) up_spine(i, 0.12 + 0.62 * j/16)], VEIN); }

// ---- lower wing: feathers fanning down from the shoulder, plus shoulder coverts ----
// [count, angle_first, angle_last, base radius, length scale, width, curl, [fill, rim, vein]]
// angles in degrees from "straight back", positive = up
LOW = [
    [7,  8, -84, 10, 1.00, 26, 0.16, [0, 1, 2]],    // long hanging feathers: navy, gold edge, white streak
    [6,  2, -78, 10, 0.68, 24, 0.14, [1, 0, 2]]     // shorter layer: gold, navy edge, white streak
];
COV = [9, 70, -60, 6, 0.36, 18, 0.12, [0, 1, -1]]; // shoulder coverts: navy scallops, gold edge
ARM_COL = [1, 0, 2];            // leading edge: gold, navy edge, white stripe
LOGO_C   = [30, 38];            // eagle-head logo centre (full-size mm)
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

function fan_len(a) = a >= 0 ? 112 : 112 + 68 * pow(-a / 80, 1.4);
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
// ---- eagle-head logo at the shoulder (traced from the supplied artwork, see eagle_logo.scad)
// navy = logo outline and linework, white = head, gold = beak
module logo_at() { translate(WS * LOGO_C) rotate(LOGO_ROT) scale(WS * LOGO_W) children(); }
module logo_white() { offset(delta = -LOGO_PAD) logo_at() logo_set(LOGO_WHITE); }
module logo_gold()  { offset(delta = -LOGO_PAD) logo_at() logo_set(LOGO_GOLD); }
module logo_navy_edge() { offset(r = WS * LOGO_HALO) logo_at() logo_set(LOGO_SIL); }
module head2d() { offset(r = max(WS * LOGO_RING, MINL)) logo_navy_edge(); }
module head_color2d(c) {
    if (c == 0) difference() { logo_navy_edge(); logo_white(); logo_gold(); }
    if (c == 1) union() { logo_gold(); difference() { head2d(); logo_navy_edge(); } }
    if (c == 2) logo_white();
}

// solid web under everything so the wing prints as one piece
module web2d() {
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
