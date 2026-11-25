import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");
const port = Number.parseInt(process.env.PORT || "3000", 10);

const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".webp", "image/webp"],
  [".ico", "image/x-icon"],
  [".woff2", "font/woff2"],
  [".txt", "text/plain; charset=utf-8"],
  [".webmanifest", "application/manifest+json"],
]);

function send(res, status, message) {
  res.writeHead(status, {
    "Content-Type": "text/plain; charset=utf-8",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
  });
  res.end(message);
}

const server = createServer(async (req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    send(res, 405, "Method not allowed");
    return;
  }

  try {
    const requestUrl = new URL(req.url || "/", "http://localhost");
    let pathname;
    try {
      pathname = decodeURIComponent(requestUrl.pathname);
    } catch {
      send(res, 400, "Invalid URL path");
      return;
    }

    if (pathname.includes("\0")) {
      send(res, 400, "Invalid URL path");
      return;
    }

    const candidate = path.resolve(root, "." + pathname);
    if (candidate !== root && !candidate.startsWith(root + path.sep)) {
      send(res, 400, "Invalid URL path");
      return;
    }

    let target = candidate;
    let fileInfo;
    try {
      fileInfo = await stat(target);
      if (!fileInfo.isFile()) throw new Error("Not a file");
    } catch {
      if (path.extname(pathname)) {
        send(res, 404, "Not found");
        return;
      }
      target = path.join(root, "index.html");
      try {
        fileInfo = await stat(target);
        if (!fileInfo.isFile()) throw new Error("Build output not found");
      } catch {
        send(res, 503, "Frontend build output is unavailable");
        return;
      }
    }

    const body = await readFile(target);
    const extension = path.extname(target).toLowerCase();
    const isHtml = extension === ".html";
    res.writeHead(200, {
      "Content-Type": contentTypes.get(extension) || "application/octet-stream",
      "Content-Length": body.byteLength,
      "X-Content-Type-Options": "nosniff",
      "X-Frame-Options": "DENY",
      "Referrer-Policy": "strict-origin-when-cross-origin",
      "Cache-Control": isHtml ? "no-cache" : "public, max-age=31536000, immutable",
    });
    res.end(req.method === "HEAD" ? undefined : body);
  } catch {
    send(res, 500, "Internal server error");
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`RuangKampus frontend listening on 0.0.0.0:${port}`);
});

server.on("error", (error) => {
  console.error("Frontend server failed to start:", error.message);
  process.exitCode = 1;
});
