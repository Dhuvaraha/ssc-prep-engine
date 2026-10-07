# Phase 2 — Product Functionality Readiness

Status: **COMPLETE for implementation**

Phase 2 converts the Phase 1 content corpus into one connected learner workflow:

**Today → Learn → Practice → Tests → Analyse → Revise → Re-plan**

Final browser/device/deployment validation is deliberately reserved for Phase 3.

## Completion gates

### App shell and hierarchy
- Persistent desktop sidebar
- Mobile bottom navigation
- Context header, universal back action and breadcrumb context
- Subject/topic hierarchy visible in Learn, Lesson and Practice
- Global offline notice and render error boundary
- Responsive layouts for learner pages

### Learner profile
- Display name and email
- Active SSC CGL exam target and daily study time
- Preparation stats: streak, practice attempts, readiness and mastery
- Preferred coach style (English or Tanglish prompts)
- Voice rate and auto-speak preferences
- Password change, mock history, JSON backup and logout

### Learn
- Searchable and priority-filtered topic library
- Structured topic lessons, pattern archetypes and shortcuts
- Read-aloud
- 3-question quick check
- Guided practice and focused topic-test handoff
- Contextual Teacher Coach with explain, hint, shortcut, trap, another example, method comparison, why-wrong, repeat, stop and next-question intents

### Practice
Implemented modes:
- Adaptive
- Guided
- Topic drill
- PYQ
- Mixed syllabus
- Weak-topic drill
- Revision drill
- Speed drill
- Difficulty ladder
- Timed practice

Answer review includes:
- selected vs correct answer
- explanation and fastest safe method
- actual vs target time
- confidence calibration
- mistake classification
- bookmark
- manual/additive revision scheduling
- mastery update and automatic wrong/slow/guess revision scheduling
- contextual Teacher Coach
- end-of-set accuracy and speed summary

### Tests / mock simulator
- Mini mock
- Sectional test
- Full 100-question SSC CGL Tier-I mock
- Focused topic test
- Configured positive and negative marking
- Countdown timer and autosubmit
- Question palette
- Clear response
- Mark for review
- Autosave on answer/navigation
- Resume-safe in-progress attempt
- Explicit discard flow
- Result accuracy and attempt rate
- Section score/accuracy/time breakdown
- Easy marks missed and slow-question counts
- Weak question-pattern summary
- Expandable question-by-question explanation review

### Revision
- Due wrong/slow/guess/low-confidence queue
- Manually added questions
- Bookmarks
- Spaced-repetition flashcards
- Reason filters and review grading

### Analytics
- Readiness
- Practice accuracy
- Speed score
- Topic mastery
- Study streak
- 14-day practice trend
- Weak-topic map with direct repair action
- Subject performance
- Error taxonomy and recoverable marks
- Confidence calibration and overconfident errors
- Recommended next actions
- Recent mock performance

### Adaptive planner
Each task shows:
- activity type
- subject/topic context
- minutes/questions target
- why the task was selected
- expected outcome
- direct Open action

Plan selection reacts to weakness, revision due, priority and days remaining.

## Automated verification

- Backend/frontend CI is green on the completed Phase 2 tree.
- Dedicated Phase 2 tests cover the expanded practice-mode selector and focused topic mock generation.
- Existing smoke, mock-engine, planner, auth/content and frontend build checks remain in CI.

## Phase boundary

Phase 2 is complete as an **implemented product workflow**.

Phase 3 remains responsible for:
- live deployed end-to-end flows with real user accounts
- desktop/tablet/mobile browser matrix
- production CORS/auth/cold-start checks
- visual/UI defect sweep
- performance and accessibility pass
- live voice-browser compatibility
- final content spot-check and release sign-off

Do not call the whole product production-released until Phase 3 passes.
