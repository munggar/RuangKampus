import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const frontendRoot = fileURLToPath(new URL("..", import.meta.url));
const run = (script, args, env = process.env) => {
  const result = spawnSync(process.execPath, [script, ...args], {
    cwd: frontendRoot,
    env,
    stdio: "inherit",
    windowsHide: true,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
};

run("node_modules/typescript/bin/tsc", ["--noEmit"]);
run("node_modules/vite/bin/vite.js", ["build"], { ...process.env, VITE_API_BASE_URL: "/api/v1" });
