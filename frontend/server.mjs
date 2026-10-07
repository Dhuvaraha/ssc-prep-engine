import { createReadStream, statSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, extname, join, normalize, sep } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, "dist");
const indexFile = join(dist, "index.html");
const port = Number(process.env.PORT ?? "4173");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function commonHeaders() {
  return {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), geolocation=()",
  };
}

function sendFile(request, response, filePath) {
  const extension = extname(filePath).toLowerCase();
  const cacheControl = filePath.includes(`${sep}assets${sep}`)
    ? "public, max-age=31536000, immutable"
    : "no-cache";

  response.writeHead(200, {
    ...commonHeaders(),
    "Content-Type": contentTypes[extension] ?? "application/octet-stream",
    "Cache-Control": cacheControl,
  });

  if (request.method === "HEAD") {
    response.end();
    return;
  }

  const stream = createReadStream(filePath);
  stream.on("error", () => {
    if (!response.headersSent) response.writeHead(500, commonHeaders());
    response.end();
  });
  stream.pipe(response);
}

const server = createServer((request, response) => {
  const method = request.method ?? "GET";
  if (method !== "GET" && method !== "HEAD") {
    response.writeHead(405, {...commonHeaders(), Allow: "GET, HEAD"});
    response.end();
    return;
  }

  let url;
  try {
    url = new URL(request.url ?? "/", "http://localhost");
  } catch {
    response.writeHead(400, commonHeaders());
    response.end();
    return;
  }

  if (url.pathname === "/__health") {
    response.writeHead(200, {
      ...commonHeaders(),
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    });
    if (method === "HEAD") {
      response.end();
    } else {
      response.end(JSON.stringify({status: "ok"}));
    }
    return;
  }

  let pathname;
  try {
    pathname = decodeURIComponent(url.pathname);
  } catch {
    response.writeHead(400, commonHeaders());
    response.end();
    return;
  }

  const relative = pathname.replace(/^\/+/, "");
  const candidate = normalize(join(dist, relative || "index.html"));
  if (candidate !== indexFile && !candidate.startsWith(dist + sep)) {
    response.writeHead(403, commonHeaders());
    response.end();
    return;
  }

  let target = candidate;
  try {
    const stats = statSync(target);
    if (stats.isDirectory()) target = join(target, "index.html");
    if (!statSync(target).isFile()) throw new Error("not a file");
    sendFile(request, response, target);
    return;
  } catch {
    // React Router owns extensionless routes. Missing asset-like requests stay 404.
    if (extname(pathname)) {
      response.writeHead(404, commonHeaders());
      response.end();
      return;
    }
  }

  try {
    if (!statSync(indexFile).isFile()) throw new Error("missing index");
    sendFile(request, response, indexFile);
  } catch {
    response.writeHead(503, {
      ...commonHeaders(),
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
    });
    response.end("Frontend build is unavailable.");
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`SSC Prep Engine web listening on ${port}`);
});
