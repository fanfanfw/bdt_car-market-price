/* global SwaggerUIBundle */
(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function showError(message) {
    var el = byId("swagger-ui-error");
    if (!el) return;
    el.textContent = message;
    el.style.display = "block";
  }

  function hideLoading() {
    var el = byId("swagger-ui-loading");
    if (el) el.style.display = "none";
  }

  function loadCss(urls, index) {
    index = index || 0;
    if (index >= urls.length) return;
    var href = urls[index];
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.onerror = function () {
      loadCss(urls, index + 1);
    };
    document.head.appendChild(link);
  }

  function loadScript(urls, index, done) {
    if (index >= urls.length) return done(new Error("All scripts failed"));
    var src = urls[index];
    var script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = function () {
      done(null);
    };
    script.onerror = function () {
      loadScript(urls, index + 1, done);
    };
    document.head.appendChild(script);
  }

  function initSwagger(openapiUrl) {
    if (typeof SwaggerUIBundle === "undefined") {
      showError(
        "Swagger UI failed to load (SwaggerUIBundle missing). If your domain has a strict Content-Security-Policy, host swagger-ui assets locally and allow only 'self'."
      );
      return;
    }

    hideLoading();
    SwaggerUIBundle({
      url: openapiUrl,
      dom_id: "#swagger-ui",
      deepLinking: true,
      presets: [SwaggerUIBundle.presets.apis],
      layout: "BaseLayout",
      persistAuthorization: true,
    });
  }

  function runOnce() {
    if (runOnce._didRun) return;
    runOnce._didRun = true;

    var root = byId("swagger-ui");
    if (!root) return;

    var openapiUrl = root.dataset.openapiUrl || "/api/docs/openapi.json";
    var staticPrefix = root.dataset.staticPrefix || "/static/";
    if (staticPrefix.slice(-1) !== "/") staticPrefix += "/";

    // Prefer local assets (works in offline networks and with strict CSP),
    // then fall back to public CDNs.
    var cssUrls = [
      staticPrefix + "swagger-ui-dist/swagger-ui.css",
      "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
      "https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
      "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.19.0/swagger-ui.css",
    ];

    var jsUrls = [
      staticPrefix + "swagger-ui-dist/swagger-ui-bundle.js",
      "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
      "https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
      "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.19.0/swagger-ui-bundle.js",
    ];

    loadCss(cssUrls);
    loadScript(jsUrls, 0, function (err) {
      if (err) {
        showError(
          "Swagger UI scripts could not be loaded. If your domain blocks external scripts, install swagger-ui-dist (npm) and run collectstatic so assets are served from /static/."
        );
        return;
      }
      initSwagger(openapiUrl);
    });
  }

  // Cloudflare Rocket Loader can execute scripts after DOMContentLoaded.
  // Run immediately when possible, and fall back to both DOMContentLoaded + load.
  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", runOnce);
    window.addEventListener("load", runOnce);
  } else {
    runOnce();
  }
})();
