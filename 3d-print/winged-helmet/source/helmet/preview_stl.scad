include <winged_helmet.scad>
part = "none";
dir = "out_mini";
color(C_NAVY)  import(str(dir, "/helmet_navy.stl"));
color(C_GOLD)  import(str(dir, "/helmet_gold.stl"));
color(C_WHITE) import(str(dir, "/helmet_white.stl"));
for (m = [0, 1]) mirror([m, 0, 0]) wing_frame() {
    color(C_NAVY)  import(str(dir, "/wing_right_navy.stl"));
    color(C_GOLD)  import(str(dir, "/wing_right_gold.stl"));
    color(C_WHITE) import(str(dir, "/wing_right_white.stl"));
}
