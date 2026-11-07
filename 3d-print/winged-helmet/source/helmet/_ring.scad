include <winged_helmet_v11.scad>
part = "none"; build = "full";
th = ths_ring();
band_zone([for (a = th) band_bot(a)], [for (a = th) band_top(a)]);
