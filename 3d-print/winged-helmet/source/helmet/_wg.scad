include <winged_helmet_v16.scad>
part = "none"; build = "full";
color(C_NAVY) import("out_v13/upper_front.stl");
color(C_NAVY) import("out_v13/upper_back.stl");
color(C_GOLD) for (m = [0, 1]) mirror([m, 0, 0]) wing_flat(sc(WG_T));
