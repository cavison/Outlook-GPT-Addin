include <winged_helmet_v20.scad>
part = "none";
color(C_NAVY) { import("out_v13/upper_front.stl"); import("out_v13/upper_back.stl"); import("out_v13/neck.stl"); }
for (m = [0, 1]) mirror([m, 0, 0]) { color(C_NAVY) import("out_v13/guard_navy.stl"); color(C_GOLD) import("out_v13/guard_gold.stl");
    color(C_WHITE) { import("out_v20/cheek_h.stl"); import("out_v20/cheek_rivet.stl"); } }
color("#07090F") import("out_v10/helmet_lining.stl");
color(C_NAVY)  import("out_v14/band_navy.stl");
color(C_GOLD)  import("out_v14/band_gold.stl");
color(C_WHITE) import("out_v14/band_white.stl");
color(C_NAVY)  import("out_v14/h_navy.stl");
color(C_GOLD)  import("out_v14/h_gold.stl");
color(C_WHITE) import("out_v14/h_white.stl");
color(C_GOLD)  import("out_v14/crest_gold.stl");
color(C_WHITE) import("out_v14/crest_white.stl");
