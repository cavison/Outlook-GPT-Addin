ex = 0;
module p(n, c) { color(c) import(str("out_v23/view/", ex ? "fit_x_" : "fit_", n, ".stl")); }
p("front", "#2E3E78"); p("back", "#2E3E78"); p("side_R", "#F2C12E"); p("side_L", "#F2C12E");
