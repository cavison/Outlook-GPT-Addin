include <winged_helmet_v20.scad>
part = "none"; build = "full";
which = 0;
DF = dome_fullness;
function z_of_r(r) = HI * pow(1 - pow(min(1, max(0, r) / RI), DF), 1 / DF);
function top_z(y) = z_of_r(abs(y) / K - W) + W;                    // shell outer height at x = 0
function side_pt(th, z) = surf_pt(th, z);
M = [
  [1, [a_out(100), 0, 100]],                                        // shell seam (right)
  [1, [-a_out(100), 0, 100]],                                       // shell seam (left)
  [2, [a_out(38) + 14, 14, 38]],                                    // wing mount block (right)
  [3, side_pt(95, bb(95) - 3)],                                     // cheek guard snap tongue (right)
  [4, side_pt(180, bb(180) - 3)],                                   // neck plate snap tongue
  [5, side_pt(240, -75)],                                           // cheek guard / neck plate pin (left)
  [6, [0, y_shell(62) - 16, 62]],                                   // front H pegs
  [7, surf_pt(th_back_of(-72, 36), -72)],                           // cheek H pegs (right)
  [8, [0, -70, top_z(-70) + 6]],                                    // crest pegs (front)
  [8, [0, 90, top_z(90) + 6]],                                      // crest pegs (back)
];
for (i = [0:len(M) - 1]) if (i == which) color("red") translate(M[i][1]) sphere(r = 5, $fn = 16);
