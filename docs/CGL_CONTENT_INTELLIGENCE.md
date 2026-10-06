# SSC CGL Content Intelligence — Phase 1 Working Matrix

> Purpose: turn the private PYQ corpus into a curriculum + archetype map, then create original practice variants. Private PDF text/images are never committed to this public repository.

## 1. 2026 exam contract

The current product must model SSC CGL 2026 Tier-I as:
- 4 subjects: General Intelligence & Reasoning, General Awareness, Quantitative Aptitude, English Comprehension
- 25 questions / 50 marks per subject
- 100 questions / 200 marks total
- 1 hour total with a 15-minute sectional timer for each subject
- 0.50 negative marking per wrong answer

Source of truth: SSC CGL 2026 official notice, section 13.8 and 13.10.

## 2. Private corpus analysed

Local analysis currently covers 20 unique CGL PDF sources spanning 2010–2024, plus the 2025 candidate-response compilation as a separate visual-source case.

Automated extraction found:
- 30,516 question-like text blocks in the 2010–2024 local corpus
- 16,527 blocks with explicit answer markers in older/solution-style documents
- 3,529 parsed questions from the 2023 compilation for topic-pattern analysis
- 3,766 parsed questions from the 2024 candidate-response compilation for topic-pattern analysis
- 23,822 text questions usable in the current topic/archetype analysis pass
- 2,275 question blocks with obvious visual/diagram cues in the first parser pass

The 2025 candidate-response PDF is heavily raster/image based: the text layer frequently contains only Q.No / section metadata while the actual question is visible in the page image. It therefore needs the visual extraction path, not a text-only parser.

Important: counts below are **heuristic lower-bound pattern hits**, not official SSC weightage. A large unclassified bucket remains because many questions need semantic or visual review.

## 3. Observed pattern signal

### Reasoning

| Topic / pattern | Heuristic hits |
|---|---:|
| Number Series | 777 |
| Analogy | 623 |
| Coding-Decoding | 415 |
| Blood Relations | 351 |
| Mathematical Operations / Sign Interchange | 278 |
| Syllogism | 249 |
| Ranking & Order | 214 |
| Classification / Odd One Out | 210 |
| Mirror / Water Images | 202 |
| Embedded Figures | 135 |
| Letter Series | 109 |
| Counting Figures | 90 |
| Paper Folding & Cutting | 74 |
| Direction Sense | 70 |
| Venn Diagrams | 69 |
| Figure Series | 38 |
| Dice & Cubes | 34 |

Strong recurring solution families observed in the private corpus include:
- first-difference / increasing-difference / alternating number-series logic
- relationship transfer for analogies
- alphabet shift / position / common-code deduction
- common-face dice logic
- left-right reflection rules for mirror images
- reverse-unfold logic for paper folding
- minimum-commitment Venn logic for syllogism
- systematic size-wise counting for figures

### Quantitative Aptitude

| Topic / pattern | Heuristic hits |
|---|---:|
| Geometry | 630 |
| Percentage | 505 |
| Ratio & Proportion | 306 |
| Profit, Loss & Discount | 296 |
| Number System | 213 |
| Mensuration | 212 |
| Time, Speed & Distance | 207 |
| Data Interpretation | 173 |
| Average | 168 |
| Time & Work | 141 |
| Algebra | 101 |
| Trigonometry | 96 |
| Simplification | 88 |
| Simple Interest | 88 |
| Compound Interest | 66 |
| Pipes & Cisterns | 51 |
| LCM & HCF | 30 |
| Mixture & Alligation | 22 |
| Trains | 21 |
| Boats & Streams | 14 |

Recurring solution families include:
- base selection and fraction equivalents for percentage
- CP/SP/MP base discipline for profit/loss/discount
- rate model / LCM work units for time & work
- relative speed + unit conversion
- geometry theorem recognition before calculation
- formula selection + unit discipline in mensuration
- chart/table read-first, calculate-second for DI

### English

| Topic / pattern | Heuristic hits |
|---|---:|
| Synonyms & Antonyms | 827 |
| Sentence Improvement | 522 |
| Error Spotting | 391 |
| Idioms & Phrases | 353 |
| Spelling | 322 |
| Fill in the Blanks | 268 |
| One Word Substitution | 268 |
| Para Jumbles | 261 |
| Active / Passive Voice | 245 |
| Direct / Indirect Speech | 40 |
| Vocabulary / phrasal verbs | 26 |
| Cloze Test | 15 |

The low cloze/RC counts are parser artefacts: passage questions often do not repeat the same keyword in every item.

Recurring solution families include:
- head-subject → finite-verb checks
- auxiliary + base-form rules
- fixed adjective/preposition and verb/preposition usage
- tense/time-marker constraints
- context + root + tone for vocabulary
- mandatory pair / pronoun reference / chronology for para jumbles
- sentence-type-first conversion for narration
- tense-preserving object→subject transformation for passive voice

### General Awareness

| Topic / pattern | Heuristic hits |
|---|---:|
| Chemistry | 483 |
| Indian Polity | 391 |
| Art & Culture | 382 |
| Geography | 336 |
| Awards & Honours | 249 |
| History | 234 |
| Sports | 207 |
| Static GK | 206 |
| Biology | 179 |
| Economics | 164 |
| Physics | 134 |
| Books & Authors | 130 |
| Current Affairs | 112 |
| Environment | 78 |
| Important Days | 15 |

GA needs fact verification rather than pattern-only generation. Current-affairs items must be dated and source-tagged.

## 4. Official-syllabus coverage gaps to add

The current product taxonomy must explicitly cover the official 2026 syllabus concepts that are not yet strong first-class content nodes:
- Reasoning: similarities/differences, spatial orientation/visualisation, problem solving, critical thinking, drawing inferences, word building, trends, indexing, address matching, date/city matching, centre-code/roll-number classification, emotional intelligence, social intelligence
- Quant: square roots, partnership business, graphs of linear equations, frequency polygon
- English: current Tier-I notice is broad, so detailed grammar/vocabulary/comprehension subtopics should be driven by PYQ evidence
- GA: keep official broad scope but break lessons into memory clusters rather than one giant factual list

Do not expose an empty topic in the learner UI. Add a topic/subtopic only after it has a real lesson package and practice set.

## 5. Content package contract

Every topic must eventually contain:
1. prerequisite
2. recognition cues
3. core concept
4. formula / rule
5. standard method
6. safest shortcut
7. easy worked example
8. exam-level worked example
9. hard variation
10. common traps / distractor logic
11. quick recall
12. question archetypes
13. guided practice set
14. timed practice set
15. revision cards

## 6. Question-bank target

Per topic:
- Priority 5: 100+ original variants
- Priority 4: 60+ original variants
- Priority 3: 40+ original variants

Difficulty mix for generated/original practice:
- 30% easy: direct recognition / clean arithmetic
- 50% medium: one hidden cue or transformation
- 20% hard: multi-step, reverse wording, close distractors, heavier calculation

Private PYQs remain a separate source layer and are not counted as original variants.

## 7. First implementation batch

Completed in the live database:
- Percentage: expanded to 105 verified questions total
- Number Series: expanded to 105 verified questions total
- both topics now have richer recognition/method/example/trap lesson blocks
- detailed archetype definitions added for direct %, reverse %, successive %, percentage comparison, constant difference, increasing difference, multiplication, alternating and interleaved series

Next content batches should prioritise:
1. Analogy
2. Coding-Decoding
3. Geometry
4. Ratio & Proportion
5. Profit, Loss & Discount
6. Error Spotting
7. Sentence Improvement
8. Synonyms & Antonyms
9. Indian Polity
10. Chemistry / Biology / Geography

## 8. QA rule

A phase is not complete because a generator produced N rows.

A question is publishable only when:
- exactly one option is correct
- solution reproduces the answer
- distractors are plausible
- shortcut is valid
- difficulty is sensible
- expected time is present
- topic/archetype tags are correct
- any required visual asset exists
- source/visibility metadata is correct
