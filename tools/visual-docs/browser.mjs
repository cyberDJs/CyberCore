import { existsSync } from "node:fs";
import { chromium } from "playwright";

const fallbackPaths = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser"
];

export async function resolveChromiumPath() {
  const candidates = [chromium.executablePath(), ...fallbackPaths].filter(existsSync);
  const failures = [];

  for (const executablePath of candidates) {
    try {
      const browser = await chromium.launch({ executablePath });
      await browser.close();
      return executablePath;
    } catch (error) {
      failures.push(`${executablePath}: ${String(error).split("\n")[0]}`);
    }
  }

  throw new Error(
    "No usable local Chromium was found for Playwright. Install Playwright Chromium with "
      + "npx playwright install chromium, or set up a supported local Chromium executable. "
      + failures.join(" | ")
  );
}
