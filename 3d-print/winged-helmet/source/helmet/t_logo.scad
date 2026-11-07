include <eagle_logo.scad>
s = 100;
color("#1E2A52") linear_extrude(1) scale(s) difference() { logo_set(LOGO_SIL); logo_set(LOGO_WHITE); logo_set(LOGO_GOLD); }
color("#F4F4EE") linear_extrude(1.2) scale(s) logo_set(LOGO_WHITE);
color("#F2C12E") linear_extrude(1.2) scale(s) logo_set(LOGO_GOLD);
