include <winged_helmet_v2.scad>
part="none"; build="full";
echo(fe_pts(TIERS[0], 3));
for (k=[0:TIERS[0][0]-1]) feather(TIERS[0], k);
