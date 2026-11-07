// analysis view: navy shell + magenta lining, previewed straight from the model (no STL)
// plus two marker dots on the brow line (red at 45 deg, green at 90 deg) used to line up with the photo
include <MODEL>
part = "none";
build = "full";
color(C_NAVY) difference() { layer(0, W); all_cuts(); }
color("#FF00FF") difference() { layer(-0.6, 0); all_cuts(); }
A0 = r_in(0) + W + 1;
color("#FF0000") translate([A0 * sin(45), -K * A0 * cos(45), 0]) sphere(r = 2.2, $fn = 24);
color("#00FF00") translate([A0 * sin(90), -K * A0 * cos(90), 0]) sphere(r = 2.2, $fn = 24);
color("#0000FF") translate([0, -K * (r_in(10) + W + 1), 10]) sphere(r = 2.2, $fn = 24);
