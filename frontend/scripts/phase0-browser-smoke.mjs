import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const base = process.env.SMOKE_URL ?? "http://127.0.0.1:4173";
const widths = [320, 360, 390, 430, 768, 1024, 1440];
const checks = ["/", "/learn", "/exams", "/login"];
await mkdir("artifacts/browser", { recursive: true });
const browser = await chromium.launch({headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined});
let failures = 0;
try {
  for (const width of widths) {
    const page = await browser.newPage({ viewport: {width, height: 850}, reducedMotion: "reduce" });
    for (const route of checks) {
      try {
        await page.goto(base + route, {waitUntil: "domcontentloaded", timeout: 20000});
        await page.locator("#root").waitFor();
        await page.waitForTimeout(350);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        if (overflow > 2) throw new Error(`horizontal overflow: ${overflow}px`);
        if (width === 390 && route === "/learn") {
          const more = page.getByRole("button", {name: "More navigation"});
          await more.click();
          await page.getByRole("navigation", {name: "Additional navigation"}).getByRole("link", {name: "Revision"}).waitFor();
          await page.keyboard.press("Escape");
          if (await more.getAttribute("aria-expanded") !== "false") throw new Error("More menu failed Escape close");
        }
        if ([390, 768, 1440].includes(width)) await page.screenshot({path: `artifacts/browser/${width}-${route === "/" ? "home" : route.slice(1)}.png`, fullPage: true});
        console.log(`PASS ${width} ${route}`);
      } catch (error) {
        failures++;
        console.error(`FAIL ${width} ${route}: ${String(error)}`);
      }
    }
    await page.close();
  }
  const page = await browser.newPage({viewport: {width: 390, height: 850}});
  try {
    await page.goto(base + "/mocks", {waitUntil: "domcontentloaded"});
    await page.waitForTimeout(300);
    if (!page.url().includes("/login")) throw new Error("Protected mock route did not redirect unauthenticated visitor");
    console.log("PASS unauthenticated mocks redirect");
  } catch(e) {failures++; console.error("FAIL protected mock redirect: "+e);}
  await page.close();
} finally {
  await browser.close();
}
if (failures) {console.error(`${failures} browser smoke failures`);process.exitCode=1}
