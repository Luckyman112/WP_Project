// PostCSS runs after Sass:
//  - postcss-preset-env: polyfills modern CSS (e.g. logical properties, :focus-visible)
//  - autoprefixer:       vendor prefixes based on the browserslist in package.json
//  - cssnano:            minification for production
module.exports = (ctx) => ({
  plugins: [
    require("postcss-preset-env")({ stage: 2, autoprefixer: false }),
    require("autoprefixer"),
    ...(ctx.env === "development" ? [] : [require("cssnano")({ preset: "default" })]),
  ],
});
