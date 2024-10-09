const webpack = require('webpack')
const workbox = require('workbox-webpack-plugin')

// Uncomment this, to easily analyze the bundle sizes
// const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

// This is a working configuration for create-react-app 5 + CRACO (c-r-a-config-override) 6.4.4.
// It adds these things which are disabled by default in webpack 5:
// - webpack loader for wasm files

module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      const wasmExtensionRegExp = /\.wasm$/
      webpackConfig.mode = process.env.NODE_ENV ? process.env.NODE_ENV : 'production'
      webpackConfig.experiments = {
        ...(webpackConfig.experiments || {}),
        syncWebAssembly: true,
      }
      webpackConfig.resolve.fallback = {
        buffer: require.resolve('buffer/'),
      }
      webpackConfig.module.rules.forEach((rule) => {
        ;(rule.oneOf || []).forEach((oneOf) => {
          if (oneOf.type === 'asset/resource') {
            oneOf.exclude.push(wasmExtensionRegExp)
          }
        })
      })
      webpackConfig.plugins.push(
        new webpack.ProvidePlugin({
          Buffer: ['buffer', 'Buffer'],
        }),
      )

      // webpackConfig.plugins.push(
      //    new BundleAnalyzerPlugin()
      // )

      if (process.env.NODE_ENV !== 'development')
        webpackConfig.plugins.push(
          new workbox.GenerateSW({
            swDest: './sw.js',
            ignoreURLParametersMatching: [/^utm_/, /^fbclid$/],
          }),
        )

      return webpackConfig
    },
  },
}