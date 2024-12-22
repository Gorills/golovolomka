"use strict";

import gulp from "gulp";

const requireDir = require("require-dir"),
    paths = {
        views: {
            src: [
                "./#src/templates/theme/default/**/*.html",
                "./#src/templates/theme/default/pages/*.html"
            ],
            dist: "./main/core/theme/default/views/",
            watch: [
                "./#src/templates/theme/default/**/*.html",
                "./#src/templates/theme/default/pages/*.html"
            ]
        },
        styles: {
            src: "./#src/scss/theme/default/style.{scss,sass}",
            dist: "./main/core/theme/default/css/",
            watch: [
                "./#src/scss/theme/default/**/*.{scss,sass}",
                "./#src/scss/theme/default/**/*.{scss,sass}"
            ]
        },
        scripts: {
            src: "./#src/js/theme/default/app.js",
            dist: "./main/core/theme/default/js/",
            watch: [
                "./#src/js/theme/default/**/*.js",
                "./#src/js/theme/default/**/*.js"
            ]
        },
        images: {
            src: [
                "./#src/images/theme/default/**/*.{jpg,jpeg,png,gif,tiff,svg}",
                "!./#src/images/theme/default/fav/*.{jpg,jpeg,png,gif,tiff}"
            ],
            dist: "./main/core/theme/default/images/",
            watch: "./#src/images/theme/default/**/*.{jpg,jpeg,png,gif,svg,tiff}"
        },
        sprites: {
            src: "./#src/images/theme/default/sprites/*.svg",
            dist: "./main/core/theme/default/images/sprites/",
            watch: "./#src/images/theme/default/sprites/*.svg"
        },
        fonts: {
            src: "./#src/fonts/theme/default/**/*.{woff,woff2,ttf,otf}",
            dist: "./main/core/theme/default/fonts/",
            watch: "./#src/fonts/theme/default/**/*.{woff,woff2,ttf,otf}"
        },
        favicons: {
            src: "./#src/img/theme/default/fav/*.{jpg,jpeg,png,gif}",
            dist: "./main/core/img/fav/",
        },
        gzip: {
            src: "./#src/.htaccess",
            dist: "./main/core/"
        },
        // admin
        adminviews: {
            src: [
                "./#src/templates/admin/**/*.html",
                "./#src/templates/admin/pages/*.html"
            ],
            dist: "./main/core/admin/views/",
            watch: [
                "./#src/templates/admin/**/*.html",
                "./#src/templates/admin/pages/*.html"
            ]
        },
        adminstyles: {
            src: "./#src/scss/admin/style.{scss,sass}",
            dist: "./main/core/admin/css/",
            watch: [
                "./#src/scss/admin/**/*.{scss,sass}",
                "./#src/scss/admin/**/*.{scss,sass}"
            ]
        },
        adminscripts: {
            src: "./#src/js/admin/app.js",
            dist: "./main/core/admin/js/",
            watch: [
                "./#src/js/admin/**/*.js",
                "./#src/js/admin/**/*.js"
            ]
        },
        adminimages: {
            src: [
                "./#src/images/admin/**/*.{jpg,jpeg,png,gif,tiff,svg}",
                "!./#src/images/admin/fav/*.{jpg,jpeg,png,gif,tiff}"
            ],
            dist: "./main/core/admin/images/",
            watch: "./#src/images/admin/**/*.{jpg,jpeg,png,gif,svg,tiff}"
        },
        adminsprites: {
            src: "./#src/images/admin/sprites/*.svg",
            dist: "./main/core/admin/images/sprites/",
            watch: "./#src/images/admin/sprites/*.svg"
        },
        adminfonts: {
            src: "./#src/fonts/admin/**/*.{woff,woff2,ttf}",
            dist: "./main/core/admin/fonts/",
            watch: "./#src/fonts/admin/**/*.{woff,woff2,ttf}"
        },
        adminfavicons: {
            src: "./#src/img/admin/fav/*.{jpg,jpeg,png,gif}",
            dist: "./main/core/img/fav/",
        }
    };

requireDir("./gulp-tasks/");

export { paths };

export const development = gulp.series("clean", "adminclean",
    gulp.parallel([
        "views", 
        "styles", 
        "scripts", 
        "images", 
        "webp", 
        "sprites", 
        "fonts", 
        "favicons",
        "adminviews", 
        "adminstyles", 
        "adminscripts", 
        "adminimages", 
        "adminwebp", 
        "adminsprites", 
        "adminfonts", 
        "adminfavicons"
    
    ]),
    gulp.parallel("serve"));

export const prod = gulp.series("clean", "adminclean",
    gulp.parallel([
        "views", 
        "styles", 
        "scripts", 
        "images", 
        "webp", 
        "sprites", 
        "fonts", 
        "favicons", 
        "gzip",
        "adminviews", 
        "adminstyles", 
        "adminscripts", 
        "adminimages", 
        "adminwebp", 
        "adminsprites", 
        "adminfonts", 
        "adminfavicons",
    ]));

export default development;