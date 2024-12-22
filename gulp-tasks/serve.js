"use strict";

import { paths } from "../gulpfile.babel";
import gulp from "gulp";
import browsersync from "browser-sync";

gulp.task("serve", () => {
    browsersync.init({
		notify: false,
        port: 3000,
        proxy: 'localhost:8000'
	});

    gulp.watch(paths.views.watch, gulp.parallel("views"));
    gulp.watch(paths.styles.watch, gulp.parallel("styles"));
    gulp.watch(paths.scripts.watch, gulp.parallel("scripts"));
    gulp.watch(paths.sprites.watch, gulp.parallel("sprites"));
    gulp.watch(paths.images.watch, gulp.parallel("images"));
    gulp.watch(paths.fonts.watch, gulp.parallel("fonts"));


    gulp.watch(paths.adminviews.watch, gulp.parallel("adminviews"));
    gulp.watch(paths.adminstyles.watch, gulp.parallel("adminstyles"));
    gulp.watch(paths.adminscripts.watch, gulp.parallel("adminscripts"));
    gulp.watch(paths.adminsprites.watch, gulp.parallel("adminsprites"));
    gulp.watch(paths.adminimages.watch, gulp.parallel("adminimages"));
    gulp.watch(paths.adminfonts.watch, gulp.parallel("adminfonts"));
});