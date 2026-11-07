include <winged_helmet.scad>
part="none";
color("gold") linear_extrude(1) difference(){ translate([-72,-13]) square([144,26]); for(i=[-1:1]) translate([i*48,0]) scroll2d(48, 26, 3); }
