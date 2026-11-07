include <winged_helmet_v21.scad>
part = "none";
ex = 0;            // pull the layers apart along the view direction (front: -y)
color(C_NAVY) import("out_v21/shell.stl");
color("#07090F") difference() { layer(-0.6, 0); all_cuts(); cylinder(r = 3, h = BIG, center = true); }
translate([0, -ex * 1, 0]) color(C_WHITE) import("out_v21/bandL_white.stl");
translate([0, -ex * 2, 0]) color(C_GOLD)  import("out_v21/bandL_gold.stl");
translate([0, -ex * 3, 0]) color(C_NAVY)  import("out_v21/bandL_navy_disp.stl");
