include <winged_helmet.scad>
part = "none";
module W(d) { color(C_NAVY) import(str(d,"/wing_right_navy.stl")); color(C_GOLD) import(str(d,"/wing_right_gold.stl")); color(C_WHITE) import(str(d,"/wing_right_white.stl")); }
W("out_mini");
translate([70, 0, 0]) W("out_v2");
