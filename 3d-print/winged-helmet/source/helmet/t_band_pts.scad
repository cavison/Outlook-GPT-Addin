include <winged_helmet_v22.scad>
part = "none";
pts = [for (th = [40:2:140]) for (f = [0, 0.25, 0.5, 0.75, 1]) let(z = band_bot(th) + f * (band_top(th) - band_bot(th)), a = r_in(z) + W + 3.2)
       [th, f, a * sin(th), -K * a * cos(th), z]];
echo(BANDPTS = pts);
echo(MEDC = WG_MED_C, WPX = WP_X);
