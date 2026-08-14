import { existsSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { resolveChromiumPath } from "./browser.mjs";

const toolDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(toolDirectory, "../..");
const diagramsDirectory = resolve(repositoryRoot, "docs/visual/diagrams");
const generatedDirectory = resolve(repositoryRoot, "docs/visual/generated");
const mmdc = resolve(toolDirectory, "node_modules/.bin/mmdc");
const config = resolve(toolDirectory, "mermaid-config.json");
const puppeteerConfig = resolve(toolDirectory, "puppeteer-config.json");

const diagrams = [
  "evidence-lifecycle",
  "work-block-lifecycle",
  "security-merge-gate",
  "architecture-overview",
  "public-private-overlay"
];

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { cwd: repositoryRoot, stdio: "inherit" });
    const timeout = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`${command} exceeded the 60-second render timeout`));
    }, 60_000);
    child.on("error", (error) => {
      clearTimeout(timeout);
      reject(error);
    });
    child.on("exit", (code) => {
      clearTimeout(timeout);
      if (code === 0) {
        resolvePromise();
      } else {
        reject(new Error(`${command} exited with status ${code}`));
      }
    });
  });
}

if (!existsSync(mmdc)) {
  throw new Error(
    "Mermaid CLI is not installed. Run npm ci in tools/visual-docs before rendering."
  );
}

const chromiumPath = await resolveChromiumPath();
process.env.PUPPETEER_EXECUTABLE_PATH = chromiumPath;

await mkdir(generatedDirectory, { recursive: true });

for (const name of diagrams) {
  const source = resolve(diagramsDirectory, `${name}.mmd`);
  const output = resolve(generatedDirectory, `${name}.svg`);
  if (!existsSync(source)) {
    throw new Error(`Expected Mermaid source is missing: ${source}`);
  }
  await run(mmdc, ["-i", source, "-o", output, "-c", config, "-p", puppeteerConfig, "-b", "#0b1014"]);
}

console.log(`Rendered ${diagrams.length} Mermaid diagrams into ${generatedDirectory}`);
