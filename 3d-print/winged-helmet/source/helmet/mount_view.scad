// right side: shell, band, mount block, and the wing lifted off to show the key and socket
lift = 45;
color("#1E2A52") import("out_v23/print/shell_front_navy.stl");
color("#1E2A52") import("out_v23/print/shell_back_navy.stl");
for (f = ["band_white_F","band_white_R","band_white_B"]) color("#F4F4EE") import(str("out_v23/print/", f, ".stl"));
for (f = ["band_gold_F","band_gold_R","band_gold_BR"]) color("#F2C12E") import(str("out_v23/print/", f, ".stl"));
for (f = ["band_navy_F","band_navy_R","band_navy_BR"]) color("#1E2A52") import(str("out_v23/print/", f, ".stl"));
color("#3B5BA9") import("out_v23/print/wing_mount_R_navy.stl");
translate([0, 0, lift]) {
    color("#1E2A52") import("out_v23/view/wingR_navy.stl");
    color("#F2C12E") import("out_v23/view/wingR_gold.stl");
    color("#F4F4EE") import("out_v23/view/wingR_white.stl");
}
