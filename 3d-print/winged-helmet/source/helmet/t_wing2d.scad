include <winged_helmet.scad>
part="none"; build="full";
for (c=[0:2]) color(c==0?"#1E2A52":c==1?"#F2C12E":"#F4F4EE") for (i=[0:3]) translate([0,0,i]) tier_color2d(i,c);
color("#1E2A52") tab2d();
