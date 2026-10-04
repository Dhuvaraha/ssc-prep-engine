# Product architecture

## Goal

A reusable SSC preparation engine that can support CGL first and JE next.

## Learning loop

1. Target an exam
2. Run a diagnostic
3. Generate a daily plan
4. Learn concise concepts
5. Practise by topic/pattern
6. Run timed and exam-mode tests
7. Analyse accuracy, attempts, speed and error type
8. Schedule revision
9. Regenerate the plan

## Core bounded contexts

- **Content**: exams, subjects, topics, lessons, questions and sources
- **Learning**: mastery, recommendations and diagnostics
- **Practice**: practice sessions, responses and timers
- **Testing**: sectional/full mock configuration and attempts
- **Analytics**: accuracy, attempt rate, speed, score leakage and readiness
- **Revision**: wrong/slow/guessed/bookmarked queues and spaced repetition
- **Planning**: exam date, available study time and daily tasks

## Design rules

- Core scoring must be deterministic.
- AI is optional and cannot be a hard dependency.
- Every question has source and visibility metadata.
- Image-based questions are first-class content.
- Exam rules are data-driven rather than hard-coded into the UI.
- Recent PYQs can receive greater recommendation weight than older material.
