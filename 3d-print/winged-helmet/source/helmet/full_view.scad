// the whole helmet built from the print pieces, both wings and their mounts
include <conn_explode_view.scad>
C_N = "#1E2A52"; C_G = "#F2C12E"; C_W = "#F4F4EE";
for (m = [0, 1]) mirror([m, 0, 0]) {
    color(C_N) import("out_v23/view/wingR_navy.stl");
    color(C_G) import("out_v23/view/wingR_gold.stl");
    color(C_W) import("out_v23/view/wingR_white.stl");
}
