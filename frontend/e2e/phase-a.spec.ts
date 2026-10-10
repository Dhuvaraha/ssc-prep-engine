import { test, expect } from "@playwright/test";

const api = "http://127.0.0.1:8811/api/v1";
test("SEC-06 real browser: scoped lesson, no persistent cache, logout/back and account switch", async ({page, request}) => {
  const a = await request.post(api+"/auth/login", {data:{email:"browser-a@example.com",password:"Synthetic-test-only-123!"}});
  const tokenA = (await a.json()).access_token;
  const b = await request.post(api+"/auth/login", {data:{email:"browser-b@example.com",password:"Synthetic-test-only-123!"}});
  const tokenB = (await b.json()).access_token;
  await page.goto("/login");
  await page.evaluate((token) => {
    localStorage.setItem("ssc_prep_token",token);
    sessionStorage.setItem("ssc_topic_package_v3_1",JSON.stringify({value:{secret:"LEGACY_SENTINEL"},expires_at:Date.now()+100000}));
  }, tokenA);
  const loaded = page.waitForResponse(r=>r.url().endsWith("/learn/topics/1/package"));
  await page.goto("/learn/topic/1");
  expect((await loaded).headers()["cache-control"]).toBe("private, no-store");
  await expect(page.locator("body")).toContainText("SYNTHETIC_ACCOUNT_A_ONLY");
  expect(await page.evaluate(()=>JSON.stringify({...sessionStorage}))).not.toContain("SYNTHETIC");
  expect(await page.evaluate(()=>sessionStorage.getItem("ssc_topic_package_v3_1"))).toBeNull();
  await page.goto("/settings");
  await page.getByRole("button", {name:"Log out",exact:true}).click();
  await expect(page).toHaveURL(/login/);
  await expect(page.locator("body")).not.toContainText("SYNTHETIC_ACCOUNT_A_ONLY");
  await page.goBack();
  await expect(page.locator("body")).not.toContainText("SYNTHETIC_ACCOUNT_A_ONLY");
  await page.evaluate(token=>{
    localStorage.setItem("ssc_prep_token",token);
    window.dispatchEvent(new StorageEvent("storage",{key:"ssc_prep_token"}));
  },tokenB);
  const denied = page.waitForResponse(r=>r.url().endsWith("/learn/topics/1/package"));
  await page.goto("/learn/topic/1");
  expect((await denied).status()).toBe(404);
  await expect(page.locator("body")).not.toContainText("SYNTHETIC_ACCOUNT_A_ONLY");
});

test("SEC-06 stale in-flight package cannot render after logout", async ({page, request}) => {
  const a = await request.post(api+"/auth/login", {data:{email:"browser-a@example.com",password:"Synthetic-test-only-123!"}});
  const token = (await a.json()).access_token;
  await page.goto("/login");
  await page.evaluate(token=>localStorage.setItem("ssc_prep_token",token),token);
  let release!:()=>void;
  let captured!:()=>void;
  const seen = new Promise<void>(resolve=>{captured=resolve;});
  const wait = new Promise<void>(resolve=>{release=resolve;});
  await page.route("**/learn/topics/1/package",async route=>{
    const response = await route.fetch();
    captured();
    await wait;
    await route.fulfill({response});
  });
  await page.goto("/learn/topic/1");
  await seen;
  await page.evaluate(()=>{
    localStorage.removeItem("ssc_prep_token");
    window.dispatchEvent(new StorageEvent("storage",{key:"ssc_prep_token"}));
  });
  release();
  await expect(page).toHaveURL(/login/);
  await expect(page.locator("body")).not.toContainText("SYNTHETIC_ACCOUNT_A_ONLY");
});

test("authorized practice and diagnostic remain usable with explicit grants", async ({page, request}) => {
  const login = await request.post(api+"/auth/login", {data:{email:"browser-a@example.com",password:"Synthetic-test-only-123!"}});
  const token = (await login.json()).access_token;
  const headers = {Authorization:"Bearer "+token};
  const precheck = await request.get(api+"/practice/questions?topic_id=1&mode=guided&limit=3",{headers});
  expect(precheck.status()).toBe(200);
  await page.goto("/login");
  await page.evaluate(token=>localStorage.setItem("ssc_prep_token",token),token);
  const practiceLoaded = page.waitForResponse(r=>r.url().includes("/practice/questions?"));
  await page.goto("/practice?topic_id=1&mode=guided&limit=3");
  expect((await practiceLoaded).status()).toBe(200);
  await page.locator(".practiceOption").first().click();
  await page.getByRole("button",{name:"Sure",exact:true}).click();
  const submitted = page.waitForResponse(r=>r.url().endsWith("/practice/submit"));
  await page.getByRole("button",{name:"Check answer",exact:true}).click();
  expect((await submitted).status()).toBe(200);
  await expect(page.locator("body")).toContainText("SYNTHETIC_ANSWER");
  const diagnostic = await request.post(api+"/mocks/start",{headers,data:{mode:"diagnostic"}});
  expect(diagnostic.status()).toBe(200);
  const assessment = await diagnostic.json();
  expect(assessment.questions).toHaveLength(40);
  expect(JSON.stringify(assessment)).not.toContain("SYNTHETIC_ANSWER");
  expect((await request.get(api+"/learn/topics/1/package",{headers})).status()).toBe(409);
  const finished = await request.post(api+`/mocks/${assessment.attempt_id}/submit`,{headers});
  expect(finished.status()).toBe(200);
  expect((await finished.json()).total_questions).toBe(40);
  expect((await request.get(api+"/diagnostics/baseline",{headers})).status()).toBe(200);
  await page.goto("/mocks");
  await page.getByRole("button",{name:/Quick Sprint/}).click();
  const started = page.waitForResponse(r=>r.url().endsWith("/mocks/start"));
  await page.getByRole("button",{name:"Start test",exact:true}).click();
  const mini = await (await started).json();
  expect(mini.questions).toHaveLength(4);
  await expect(page.locator("body")).toContainText("Synthetic");
  // Cleanly terminate the synthetic attempt; no production rows exist here.
  expect((await request.post(api+`/mocks/${mini.attempt_id}/submit`,{headers})).status()).toBe(200);
});
