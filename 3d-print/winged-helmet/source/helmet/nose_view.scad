include <winged_helmet_v22.scad>
part = "none";
on = 1;            // nose piece on
style = "over";    // "over" or "stub" (stub = band carries the strap stub, v21 layers clipped at the brow)
hh = 1;            // show the front H
ex = 0;            // pull the nose piece forward / down to show the clip
color(C_NAVY) import("out_v22/shell_nose.stl");
color("#07090F") difference() { layer(-0.6, 0); all_cuts(); cylinder(r = 3, h = BIG, center = true); }
if (style == "over") {
    color(C_WHITE) import("out_v22/bandL_white.stl");
    color(C_GOLD)  import("out_v22/bandL_gold.stl");
    color(C_NAVY)  import("out_v22/bandL_navy.stl");
} else {
    color(C_WHITE) import("out_v22/stub_white.stl");
    color(C_GOLD)  import("out_v22/stub_gold.stl");
    color(C_NAVY)  import("out_v22/stub_navy.stl");
}
if (hh) { color(C_NAVY) import("out_v22/h_navy.stl"); color(C_GOLD) import("out_v22/h_gold.stl"); color(C_WHITE) import("out_v22/h_white.stl"); }
if (on) translate([0, -ex, -ex * 0.6]) {
    color(C_GOLD)  import("out_v22/nose_body.stl");
    translate([0, -ex * 0.6, 0]) color(C_NAVY)  import("out_v22/nose_panel.stl");
    translate([0, -ex * 1.2, 0]) color(C_WHITE) import("out_v22/nose_pin.stl");
}
