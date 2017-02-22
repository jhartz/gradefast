var path = require("path");
var webpack = require("webpack");

module.exports = {
    module: {
        loaders: [
            {
                test: /\.jsx?$/,
                exclude: /node_modules/,
                loader: "babel-loader",
                query: {
                    presets: ["es2015", "react"]
                }
            }
        ]
    },
    entry: "./gradefast/gradebook/static/js/index.js",
    output: {
        filename: "bundle.js",
        path: path.resolve(__dirname, "gradefast/gradebook/static/dist/")
    },
    devtool: "#source-map"
};
