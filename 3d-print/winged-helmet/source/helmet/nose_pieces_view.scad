// the nose piece's three parts laid out: body (front), body (back, showing the tongue and snap bumps), navy panel, white pin
C_NAVY = "#1E2A52"; C_GOLD = "#F2C12E"; C_WHITE = "#F4F4EE";
cy = 133; cz = -13;
module at(x, rz) translate([x, 0, 0]) rotate([0, 0, rz]) translate([0, cy, -cz]) children();
at(-70, -30) color(C_GOLD)  import("out_v22/nose_body.stl");
at(-5, 150)  color(C_GOLD)  import("out_v22/nose_body.stl");   // back side
at(45, -25)  color(C_NAVY)  import("out_v22/nose_panel.stl");
at(85, -35)  color(C_WHITE) import("out_v22/nose_pin.stl");
