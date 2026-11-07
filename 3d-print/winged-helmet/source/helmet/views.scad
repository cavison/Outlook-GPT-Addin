include <winged_helmet_v7.scad>
part = "none";
view = "assembled";
WV3 = false;
D = "../pkg/winged_helmet/stl_mini_5in";
module H(c) { import(str(D, "/helmet_", c, ".stl")); }
module Wg(side, c) { import(str(D, "/wing_", side, "_", c, ".stl")); }
module helmet_all() { color(C_NAVY) H("navy"); color(C_GOLD) H("gold"); color(C_WHITE) H("white"); }
module wing_all(side) { color(C_NAVY) Wg(side,"navy"); color(C_GOLD) Wg(side,"gold"); color(C_WHITE) Wg(side,"white"); }
module bed() {   // AD5X 220 x 220 build plate
    color("#C9CCD1") translate([-110, -110, -1.2]) cube([220, 220, 1.2]);
    color("#B4B8BF") for (i = [-100:20:100]) {
        translate([i - 0.2, -110, -0.01]) cube([0.4, 220, 0.02]);
        translate([-110, i - 0.2, -0.01]) cube([220, 0.4, 0.02]);
    }
}
if (view == "assembled") {
    helmet_all();
    for (m = [0, 1]) mirror([m, 0, 0]) wing_frame() wing_all("right");
}
if (view == "plate_helmet") { bed(); translate([0, 0, 43.1]) helmet_all(); }
if (view == "plate_wings") {
    bed();
    translate([-14, -30, 0]) wing_all("left");
    translate([12, -30, 0]) wing_all("right");
}
if (view == "colors") {
    translate([-105, 0, 0]) color(C_NAVY) H("navy");
    color(C_GOLD) H("gold");
    translate([105, 0, 0]) color(C_WHITE) H("white");
}
if (view == "socket") {
    helmet_all();
    for (m = [0, 1]) mirror([m, 0, 0]) wing_frame() translate([0, m == 0 ? 22 : 0, 0]) wing_all("right");
    // arrow: slide the tab straight down into the slot
    wing_frame() color("#D9342B") translate([0, 19, NOUT + 3]) rotate([90, 0, 0]) {
        cylinder(h = 14, d = 1.4, $fn = 24);
        translate([0, 0, 14]) cylinder(h = 4, d1 = 4, d2 = 0, $fn = 24);
    }
}
