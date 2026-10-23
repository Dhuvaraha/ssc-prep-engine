import { test, expect } from "@playwright/test";

const api = "http://127.0.0.1:8811/api/v1";
test("reviewed correction uses independent editor UI and publication gate", async ({page, request}) => {
  const tokens = [];
  for (const email of ["editor-a@example.com", "editor-b@example.com"]) {
    const login = await request.post(api+"/auth/login", {data:{email,password:"Synthetic-test-only-123!"}});
    expect(login.status()).toBe(200);
    tokens.push((await login.json()).access_token);
  }
  const headers={Authorization:"Bearer "+tokens[0]};
  const listed=await request.get(api+"/review/questions?status=verified",{headers});
  const question=(await listed.json())[0];
  const created=await request.post(api+`/review/questions/${question.id}/revisions`,{headers,data:{
    expected_digest:question.revision_digest,reason:"Synthetic browser correction",
    changes:{verification_status:"verified",review_notes:"Browser evidence",explanation:question.explanation+" Reviewed correction."},
  }});
  expect(created.status()).toBe(200);
  const id=(await created.json()).candidate_id;
  await page.goto("/login");
  await page.evaluate(token=>localStorage.setItem("ssc_prep_token",token),tokens[1]);
  await page.goto("/review?candidate="+id);
  await page.getByRole("button",{name:"Open candidate"}).click();
  await expect(page.getByRole("table")).toContainText("Reviewed correction.");
  const publish=page.getByRole("button",{name:"Publish reviewed correction"});
  await expect(publish).toBeDisabled();
  for (const checkbox of await page.getByRole("checkbox").all()) await checkbox.check();
  await page.getByLabel("Review evidence reference").fill("Independent synthetic browser check");
  await page.getByRole("button",{name:"Record independent review"}).click();
  await expect(page.getByRole("status")).toContainText("Independent review recorded");
  await expect(publish).toBeEnabled();
  await publish.click();
  await expect(page.getByRole("status")).toContainText("Reviewed correction published.");
  await expect(publish).toBeDisabled();
});
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
  test.setTimeout(90000); // Includes independent review of ten synthetic payloads.
  const editors: string[] = [];
  for (const email of ["editor-a@example.com", "editor-b@example.com"]) {
    const response = await request.post(api+"/auth/login", {data:{email,password:"Synthetic-test-only-123!"}});
    editors.push((await response.json()).access_token);
  }
  const author = {Authorization:"Bearer "+editors[0]};
  const reviewer = {Authorization:"Bearer "+editors[1]};
  const listed = await request.get(api+"/review/questions?status=verified", {headers:author});
  for (const question of (await listed.json()).filter((q: {topic_id:number})=>q.topic_id===1)) {
    const draft = await request.post(api+`/review/questions/${question.id}/supplements`, {headers:author,data:{
      coaching:{standard_method:"SYNTHETIC_VERSIONED_METHOD: add one to the given whole number."},
      source_ids:["browser-original"],contributors:[{kind:"lesson",resource_id:1}],
      option_insights:[{position:2,insight_type:"misconception",knowledge_text:"SYNTHETIC_VERSIONED_TRAP",source_reference:"Synthetic author check"}],
    }});
    expect(draft.status()).toBe(200);
    const id = (await draft.json()).supplement_id;
    const evidence = {answer_verified:true,all_options_checked:true,instruction_reviewed:true,visual_reviewed:true,reference:"Synthetic independent review"};
    expect((await request.post(api+`/review/supplements/${id}/review`, {headers:author,data:evidence})).status()).toBe(409);
    expect((await request.post(api+`/review/supplements/${id}/review`, {headers:reviewer,data:evidence})).status()).toBe(200);
    expect((await request.get(api+`/review/supplements/${id}`)).status()).toBe(401);
  }
  const login = await request.post(api+"/auth/login", {data:{email:"browser-a@example.com",password:"Synthetic-test-only-123!"}});
  const token = (await login.json()).access_token;
  const headers = {Authorization:"Bearer "+token};
  const precheck = await request.get(api+"/practice/questions?topic_id=1&mode=guided&limit=3",{headers});
  expect(precheck.status()).toBe(200);
  expect(JSON.stringify(await precheck.json())).not.toContain("SYNTHETIC_VERSIONED_METHOD");
  await page.goto("/login");
  await page.evaluate(token=>localStorage.setItem("ssc_prep_token",token),token);
  const practiceLoaded = page.waitForResponse(r=>r.url().includes("/practice/questions?"));
  await page.goto("/practice?topic_id=1&mode=guided&limit=3");
  expect((await practiceLoaded).status()).toBe(200);
  await expect(page.locator("body")).toContainText("Source year: 2026");
  await expect(page.locator("body")).not.toContainText("PYQ 2026");
  await page.locator(".practiceOption").first().click();
  await page.getByRole("button",{name:"Sure",exact:true}).click();
  const submitted = page.waitForResponse(r=>r.url().endsWith("/practice/submit"));
  await page.getByRole("button",{name:"Check answer",exact:true}).click();
  expect((await submitted).status()).toBe(200);
  await expect(page.locator("body")).toContainText("SYNTHETIC_ANSWER");
  await expect(page.locator("body")).toContainText("SYNTHETIC_VERSIONED_METHOD");
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
