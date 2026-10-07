# SSC Prep Engine — Product Completion Plan v2

## Why v2 exists
The current app proves that the frontend, FastAPI backend, database, auth, planner, practice, mock, analytics and revision plumbing can be connected. It is not yet a finished preparation product. The new plan is outcome-gated: a phase is complete only when a student can use the feature end-to-end with real content.

## Product goal
A private SSC preparation system that behaves like a structured teacher:
**Learn → Guided practice → Timed practice → Mock → Analyse → Revise → Re-plan.**

The immediate target is SSC CGL Tier I. The architecture remains reusable for SSC JE.

## Canonical product hierarchy
Exam
→ Subject
→ Domain
→ Topic
→ Subtopic
→ Question archetype
→ Lesson
→ Solved examples
→ Practice sets
→ Tests
→ Revision

Every user-facing page must show where the learner is in this hierarchy.

---

# Phase 1 — Content Intelligence & Curriculum

## Goal
Build the real learning corpus before polishing secondary product features.

## Source layers
1. Official SSC syllabus/pattern — canonical scope and exam rules.
2. User-private PYQ PDFs — private trend/archetype/solution analysis.
3. Original practice bank — newly written questions inspired by the skill/pattern, not copied from proprietary publications.
4. Current affairs — verified, dated, source-tagged facts.

## Topic package definition
Every topic must contain:
- beginner concept explanation
- prerequisite knowledge
- formulas/rules
- normal method
- shortest safe method / shortcut
- decision rule: how to recognise the question type
- 3+ solved examples (easy, exam, hard)
- common traps and distractor logic
- question archetypes
- timed target
- revision flashcards
- linked practice sets

## Question archetype definition
Each archetype stores:
- skill tested
- recognition cues
- canonical solving method
- shortcut method
- typical trap
- expected time
- easy / medium / hard construction rules
- PYQ evidence tags
- generator/variant constraints

## Bank targets
Launch-quality floor:
- Priority-5 topic: 100+ original variants
- Priority-4 topic: 60+ original variants
- Priority-3 topic: 40+ original variants
- plus private PYQs separately

With the current 66-topic CGL taxonomy this produces roughly 4,500+ original practice questions before adding private PYQs.

## Content QA gates
A question is usable only when:
- one unambiguous correct answer exists
- all options are plausible
- solution reproduces the answer
- shortcut is valid, not a gimmick
- difficulty label is justified
- expected solve time exists
- topic/subtopic/archetype tags are valid
- visual assets are present when required
- source/licensing/visibility metadata is correct

## Definition of done
Phase 1 is complete only when every CGL topic has a full topic package and the bank meets the question targets above. No empty Learn cards.

---

# Phase 2 — Study Experience & Information Architecture

## Goal
Make the product feel like a professional study application rather than separate pages.

## App shell
- persistent desktop sidebar
- compact mobile bottom/tab navigation
- global breadcrumb
- universal Back action
- page title + context header
- profile/avatar menu
- consistent content width and spacing
- loading, empty, error and offline states

## Main navigation
Today
Learn
Practice
Tests
Revision
Analytics
Profile

Admin/content-review tools are hidden from the normal learner navigation.

## Profile
- name/email
- active exam target
- exam date
- daily study hours
- preferred language
- voice settings
- current streak
- total practice attempts
- mock history
- backup/export
- logout

## Study plan UX
Each task must display:
- subject
- topic/subtopic
- activity type
- exact target (minutes/questions)
- why it was selected
- expected outcome
- direct Open action

## Definition of done
A student can enter any deep page and always knows: where am I, what am I learning, how do I go back, and what is next.

**Status: COMPLETE — 2026-10-07**

Closure includes persistent desktop navigation, compact mobile navigation, profile access, global loading/error/offline feedback, explicit exam and study settings, subject/topic hierarchy on deep study pages, and planner tasks with exact targets, selection reason, expected outcome and direct actions.

---

# Phase 3 — Teacher-Quality Learn Mode

## Goal
Teach from zero, then transition immediately into practice.

## Lesson flow
1. What you are learning
2. Why SSC asks it
3. Core concept
4. Formula/rule
5. Recognition cues
6. Standard method
7. Shortcut method
8. Easy worked example
9. Exam-level worked example
10. Hard variation
11. Common mistakes
12. 3-question quick check
13. Start guided practice

## Teacher controls
- Explain simpler
- Show another example
- Show shortcut
- Why is this wrong?
- Compare two methods
- Read aloud
- Ask teacher

## Definition of done
A beginner can learn a topic without leaving the app and can pass the topic quick-check before practice.

---

# Phase 4 — Practice & Question Intelligence

## Modes
- Guided practice
- Topic drill
- Mixed topic drill
- Speed drill
- Weak-topic drill
- Revision drill
- PYQ practice
- Difficulty ladder

## Question review
After answering, show:
- correct answer
- step-by-step method
- fastest safe method
- why the selected option was wrong
- trap type
- expected time vs actual time
- confidence calibration
- bookmark
- add to revision

## Difficulty generation
For each archetype:
- easy: direct recognition / clean numbers
- medium: one transformation or hidden cue
- hard: multi-step, reverse question, close distractors or heavier calculation

## Definition of done
The same skill can be practised repeatedly without seeing only trivial clones.

---

# Phase 5 — Exam Simulator

## Goal
Replicate the current SSC CGL Tier-I behaviour closely.

- 100 questions
- 4 sections × 25
- 200 marks
- negative marking
- sectional timing where applicable
- question palette
- save & next
- mark for review
- clear response
- section transition behaviour
- autosave
- autosubmit
- resume-safe state
- full / sectional / topic tests

## Result review
- score
- attempted/correct/wrong/skipped
- section score
- question-by-question review
- time spent
- easy marks missed
- guessed answers
- weak archetypes

## Definition of done
A full mock can be taken from start to submission without any dead action or missing question.

---

# Phase 6 — Analytics, Revision & Adaptive Planner

## Analytics
- score trend
- accuracy trend
- speed trend
- subject/topic/archetype mastery
- error taxonomy
- time leakage
- guess rate
- confidence calibration
- first-pass vs second-pass performance
- mock trend
- potential marks recoverable

## Revision
Queues:
- wrong
- slow
- guessed
- low confidence
- bookmarked
- formulas
- GK facts
- due by spaced repetition

## Planner
Selection priority:
exam importance × frequency × weakness × revision due × days-left urgency.

Every task shows **why this task is here**.

## Definition of done
After practice, the system changes what the learner is asked to study next.

---

# Phase 7 — Voice Teacher, Profile, Accessibility & Release QA

## Voice Teacher
Voice is not a page reader. It is a contextual tutor with access to:
- current topic
- current lesson block
- current question
- selected answer
- solution
- user mastery and recent mistakes

Supported intents:
- explain this
- explain simpler
- give me a hint
- give me the shortcut
- why is option B wrong?
- ask me one more like this
- repeat
- next question
- stop

Start with browser speech recognition + speech synthesis and deterministic lesson/question context. Optional LLM tutoring can be added later without making the core product dependent on paid AI.

## Release QA gate
Before calling the product complete:
- register/login/logout/profile passes
- all navigation/back/breadcrumb flows pass
- every topic opens real content
- practice works for every topic
- full mock completes
- revision queue is generated
- analytics update after attempts
- planner links to exact tasks
- voice controls work on supported browsers
- desktop/tablet/mobile smoke tests pass
- no blank screens or silent failures

---

# Execution order

1. Content taxonomy + archetype system
2. High-priority CGL content packages
3. Original question-bank expansion
4. Private PYQ ingestion and tagging
5. App shell + profile + hierarchy
6. Learn mode redesign
7. Practice redesign
8. Mock simulator alignment
9. Analytics/revision/planner refinement
10. Voice teacher + final QA

## Rule for all future status updates
Never mark a phase complete because code files exist. Mark it complete only when the learner-facing workflow is usable end-to-end with real content.
