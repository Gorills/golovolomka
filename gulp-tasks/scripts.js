"use strict";

import { paths } from "../gulpfile.babel";
import webpack from "webpack";
import webpackStream from "webpack-stream";
import gulp from "gulp";
import gulpif from "gulp-if";
import rename from "gulp-rename";
import browsersync from "browser-sync";
import debug from "gulp-debug";
import yargs from "yargs";

const webpackConfig = require("../webpack.config.js"),
    argv = yargs.argv,
    production = !!argv.production;

webpackConfig.mode = production ? "production" : "development";
webpackConfig.devtool = production ? false : "source-map";

gulp.task("scripts", () => {
    return gulp.src(paths.scripts.src)
        
        
		.pipe(gulp.dest(paths.scripts.dist))

		.pipe(gulp.dest(paths.scripts.dist))
		.pipe(browsersync.stream());
});

gulp.task("adminscripts", () => {
    return gulp.src(paths.adminscripts.src)
    .pipe(gulp.dest(paths.adminscripts.dist))

    .pipe(gulp.dest(paths.adminscripts.dist))
    .pipe(browsersync.stream());
});