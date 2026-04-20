"use strict";

import gulp from "gulp";
import del from "del";

gulp.task("clean", () => {
    return del(["./main/core/theme/default/*"]);
});

gulp.task("adminclean", () => {
    return del(["./main/core/admin/*"]);
});