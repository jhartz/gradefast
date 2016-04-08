module.exports = function (grunt) {
    var ALL_TASKS = ["browserify", "extract_sourcemap", "uglify"];

    grunt.initConfig({
        pkg: grunt.file.readJSON("package.json"),

        /*
        babel: {
            options: {
                sourceMap: true,
                presets: ["es2015", "react"]
            },

            dist: {
                files: [
                    {
                        expand: true,
                        src: ["jsx/*.js"],
                        dest: "build/"
                    }
                ]
            }
        },
        */

        browserify: {
            options: {
                browserifyOptions: {
                    debug: true  // for source maps
                },
                transform: [["babelify", {presets: ["es2015", "react"]}]]
            },

            dist: {
                files: [
                    {
                        src: "../jsx/index.jsx",
                        dest: "bundle.js"
                    }
                ]
            }
        },

        extract_sourcemap: {
            dist: {
                files: [
                    {
                        src: "bundle.js",
                        dest: "."
                    }
                ]
            }
        },

        uglify: {
            options: {
                sourceMap: true,
                sourceMapIncludeSources: true,
                sourceMapIn: "bundle.js.map",
                banner: '/* GradeFast gradebook - <%= grunt.template.today("yyyy-mm-dd") %> */\n'
            },

            dist: {
                files: [
                    {
                        src: "bundle.js",
                        dest: "bundle.min.js"
                    }
                ]
            }
        },

        watch: {
            js: {
                files: ["../jsx/*.js", "../jsx/*.jsx"],
                tasks: ALL_TASKS
            }
        }
    });

    //grunt.loadNpmTasks("grunt-babel");
    grunt.loadNpmTasks("grunt-browserify");
    grunt.loadNpmTasks("grunt-extract-sourcemap");
    grunt.loadNpmTasks("grunt-contrib-uglify");
    grunt.loadNpmTasks("grunt-contrib-watch");

    grunt.file.setBase("gradefast/gradebook/static/build/");

    grunt.registerTask("default", ALL_TASKS);
    grunt.registerTask("watchme", ALL_TASKS.concat("watch"));
};
