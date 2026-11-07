include <winged_helmet_v23.scad>
part = "none";
echo(BAND = [for (th = [0:1:180]) [th, bb(th), band_top(th)]]);
echo(DOTS = [for (dd = concat(BAND_FRONT_DOTS, BAND_BACK_DOTS)) let(z = bm_map([dd[0], dd[1]])[1], r = dd[2] * FACE_R0 / 2) [dd[0], z, r]]);
echo(MISC = [CHV_Z, CHV_W, CHV_H, CHV_EDGE, K, RI, W, HI, TH_EYE, GUARD_TH_BACK, LUG_Z, CR_FRONT_Z, CR_BACK_Z, CR_W[0], CR_W[1], CR_T[0], CR_T[1]]);
echo(RIV = [th_back_of(sc(RIV_Z), sc(RIV_BACK)), sc(RIV_Z)], CHC = [th_back_of(sc(CH_Z), sc(CH_BACK)), sc(CH_Z)]);
