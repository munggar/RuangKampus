import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const previewUrl = "http://127.0.0.1:4174/login";
const frontendRoot = fileURLToPath(new URL("..", import.meta.url));
const previewScript = fileURLToPath(new URL("../node_modules/vite/bin/vite.js", import.meta.url));

export default async function globalSetup() {
  const preview = spawn(process.execPath, [
    previewScript,
    "preview",
    "--host", "127.0.0.1",
    "--port", "4174",
    "--strictPort",
    "--bypass-lock",
  ], {
    cwd: frontendRoot,
    env: process.env,
    stdio: "ignore",
    windowsHide: true,
  });

  let exitInfo = null;
  preview.once("exit", (code, signal) => { exitInfo = { code, signal }; });

  try {
    const deadline = Date.now() + 60_000;
    while (Date.now() < deadline) {
      if (exitInfo) throw new Error(`Vite preview exited during startup (code ${exitInfo.code}, signal ${exitInfo.signal}).`);
      try {
        const response = await fetch(previewUrl);
        if (response.ok) break;
      } catch {
        // Preview is still starting.
      }
      await delay(200);
    }
    if (Date.now() >= deadline) throw new Error("Vite preview did not become ready within 60 seconds.");
  } catch (error) {
    if (preview.pid && !exitInfo) {
      if (process.platform === "win32") spawnSync("taskkill", ["/pid", String(preview.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      else preview.kill("SIGTERM");
    }
    throw error;
  }

  return async function globalTeardown() {
    if (exitInfo || !preview.pid) return;
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/pid", String(preview.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    } else {
      preview.kill("SIGTERM");
    }
    await Promise.race([
      new Promise((resolve) => preview.once("exit", resolve)),
      delay(5_000),
    ]);
    if (!exitInfo && preview.pid) {
      if (process.platform === "win32") spawnSync("taskkill", ["/pid", String(preview.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      else preview.kill("SIGKILL");
    }
  };
}
