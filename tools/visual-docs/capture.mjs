import { createServer } from "node:http";
import { createReadStream, existsSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { dirname, extname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { resolveChromiumPath } from "./browser.mjs";

const toolDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(toolDirectory, "../..");
const learnDirectory = resolve(repositoryRoot, "docs/visual/learn");
const assetsDirectory = resolve(repositoryRoot, "assets");
const [output] = process.argv.slice(2);
const frameRate = 15;
const frameCount = 158;

if (!output) {
  throw new Error("Usage: node capture.mjs <intermediate-webm-output>");
}

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch (error) {
  throw new Error("Playwright is unavailable. Run npm ci in tools/visual-docs before capture.", { cause: error });
}

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml"
};

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { stdio: "inherit" });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) resolvePromise();
      else reject(new Error(`${command} exited with status ${code}`));
    });
  });
}

async function settle(label, operation) {
  let timeout;
  await Promise.race([
    operation,
    new Promise((resolvePromise) => {
      timeout = setTimeout(() => {
        console.warn(`${label} did not complete within five seconds; continuing cleanup.`);
        resolvePromise();
      }, 5000);
    })
  ]);
  clearTimeout(timeout);
}

const server = createServer((request, response) => {
  const pathname = request.url?.split("?")[0] || "/";
  const requestPath = pathname === "/" ? "/index.html" : pathname;
  const filePath = requestPath.startsWith("/assets/")
    ? resolve(repositoryRoot, `.${requestPath}`)
    : resolve(learnDirectory, `.${requestPath}`);
  const permitted = filePath.startsWith(learnDirectory) || filePath.startsWith(assetsDirectory);
  if (!permitted || !existsSync(filePath)) {
    response.writeHead(404);
    response.end("Not found");
    return;
  }
  response.writeHead(200, { "content-type": contentTypes[extname(filePath)] ?? "application/octet-stream" });
  createReadStream(filePath).pipe(response);
});

await new Promise((resolvePromise) => server.listen(0, "127.0.0.1", resolvePromise));
const address = server.address();
if (!address || typeof address === "string") {
  server.close();
  throw new Error("Could not allocate a local server for the Learn demo.");
}

let browser;
try {
  browser = await chromium.launch({ executablePath: await resolveChromiumPath() });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
    reducedMotion: "no-preference"
  });
  const page = await context.newPage();
  await page.goto(`http://127.0.0.1:${address.port}/?capture=1`, { waitUntil: "networkidle" });
  await page.evaluate(() => window.CyberCoreLearn.stop());
  const framesDirectory = resolve(dirname(resolve(output)), "learn-evidence-lifecycle-frames");
  await mkdir(framesDirectory, { recursive: true });
  const startedAt = Date.now();
  for (let index = 0; index < frameCount; index += 1) {
    const elapsed = (index * 1000) / frameRate;
    const nextFrameAt = startedAt + elapsed;
    const wait = nextFrameAt - Date.now();
    if (wait > 0) await page.waitForTimeout(wait);
    await page.evaluate((step) => window.CyberCoreLearn.showStep(step), Math.floor(elapsed / 1200) % 8);
    await page.screenshot({ path: resolve(framesDirectory, `frame-${String(index).padStart(4, "0")}.png`) });
  }
  await settle("Playwright context shutdown", context.close());
  await mkdir(dirname(resolve(output)), { recursive: true });
  await run("ffmpeg", [
    "-y", "-framerate", String(frameRate), "-i", resolve(framesDirectory, "frame-%04d.png"),
    "-an", "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", resolve(output)
  ]);
  console.log(`Captured deterministic Learn demo to ${resolve(output)}`);
} catch (error) {
  throw error;
} finally {
  if (browser) await settle("Playwright browser shutdown", browser.close());
  server.closeAllConnections?.();
  await settle("Local Learn server shutdown", new Promise((resolvePromise) => server.close(resolvePromise)));
}
