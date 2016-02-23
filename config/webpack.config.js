var path = require('path')
var webpack = require('webpack')
var BundleTracker = require('webpack-bundle-tracker')
var ExtractText = require('extract-text-webpack-plugin')

// paths are absolute to the root of the project, where we run `npm` commands
var root = './muckrock/'

module.exports = {
    devtool: 'source-map',
    context: __dirname,
    entry: path.resolve(root + 'assets/js/index'),
    output: {
        path: path.resolve(root + 'assets/bundles/'),
        filename: '[name].js',
    },
    module: {
        loaders: [
            {
                test: /\.jsx?$/,
                exclude: /node_modules/,
                loader: 'babel-loader',
                query: {
                    presets: ['es2015', 'react'],
                }
            },
            {
                test: /\.scss?$/,
                loader: ExtractText.extract('style-loader', 'css-loader!sass-loader'),
            },
        ],
    },
    plugins: [
        new BundleTracker({filename: './muckrock/webpack-stats.json'}),
        new ExtractText('[name].css'),
    ],
    resolve: {
        moduleDirectories: ['node_modules'],
        extensions: ['', '.js', '.jsx']
    },
}