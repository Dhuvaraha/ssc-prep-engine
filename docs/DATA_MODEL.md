# Data model draft

## Main entities

- User
- Exam
- ExamStage
- Subject
- Topic
- Lesson
- Question
- QuestionOption
- QuestionSource
- PracticeSession
- QuestionAttempt
- Test
- TestSection
- TestAttempt
- TopicMastery
- RevisionItem
- Flashcard
- Bookmark
- DailyPlan
- StudyTask

## Question fields

- id
- exam_id
- subject_id
- topic_id
- subtopic
- pattern_type
- question_type
- question_text
- question_image_url
- options
- correct_option
- explanation
- fast_method
- difficulty
- estimated_time_seconds
- year
- shift
- source_type
- source_reference
- visibility
- verification_status

## Attempt fields

- user_id
- question_id
- selected_option
- outcome
- time_seconds
- confidence
- used_hint
- changed_answer
- mistake_type
- attempted_at

## Source types

- official
- licensed
- user_private
- original
- generated

## Verification statuses

- raw
- parsed
- review_required
- verified
