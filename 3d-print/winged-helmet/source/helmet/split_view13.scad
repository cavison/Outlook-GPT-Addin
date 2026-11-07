// exploded / assembled views of the printable pieces (full size)
include <winged_helmet_v13.scad>
part = "none";
mode = "exploded";      // exploded | assembled_A | assembled_B | guard_out | guard_in
EX = mode == "exploded";
module band_half(side) {   // band pieces, cut at the front/back seam for the view
    intersection() {
        union() {
            color(C_NAVY)  import("out_v12/band_navy.stl");
            color(C_GOLD)  import("out_v12/band_gold.stl");
            color(C_WHITE) import("out_v12/band_white.stl");
        }
        if (side < 0) translate([-500, -1000, -500]) cube([1000, 1000, 1000]);
        else          translate([-500, 0, -500]) cube([1000, 1000, 1000]);
    }
}
module guard(m) {
    mirror([m, 0, 0]) {
        color(C_NAVY) import("out_v13/guard_navy.stl");
        color(C_GOLD) import("out_v13/guard_gold.stl");
    }
}
if (mode == "guard_out" || mode == "guard_in") guard(0);
else {
    color(C_NAVY) import("out_v13/upper_front.stl");
    band_half(-1);
    translate(EX ? [0, 70, 0] : [0, 0, 0]) { color(C_NAVY) import("out_v13/upper_back.stl"); band_half(1); }
    translate(EX ? [80, -5, -50] : [0, 0, 0]) guard(0);
    translate(EX ? [-80, -5, -50] : [0, 0, 0]) guard(1);
    if (mode != "assembled_B") translate(EX ? [0, 120, -70] : [0, 0, 0]) color(C_NAVY) import("out_v13/neck.stl");
}
