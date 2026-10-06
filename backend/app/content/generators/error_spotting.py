from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedQuestion:
    pattern_type: str
    subtopic: str
    difficulty: int
    expected_time_seconds: int
    question_text: str
    options: tuple[str, str, str, str]
    correct_option: int
    explanation: str
    fast_method: str


def _make(
    *,
    pattern: str,
    subtopic: str,
    difficulty: int,
    seconds: int,
    parts: tuple[str, str, str],
    correct_option: int,
    explanation: str,
    fast_method: str,
) -> GeneratedQuestion:
    options = (*parts, "No error")
    return GeneratedQuestion(
        pattern_type=pattern,
        subtopic=subtopic,
        difficulty=difficulty,
        expected_time_seconds=seconds,
        question_text=(
            "Identify the part containing the error: "
            + " / ".join(parts)
            + '. If there is no error, choose "No error".'
        ),
        options=options,
        correct_option=correct_option,
        explanation=explanation,
        fast_method=fast_method,
    )


def build_error_spotting_bank() -> list[GeneratedQuestion]:
    bank: list[GeneratedQuestion] = []

    groups: list[tuple[str, str, int, str, list[tuple[tuple[str, str, str], int, str]]]] = [
        (
            "subject-verb-agreement",
            "Subject–verb agreement",
            40,
            "Find the head subject and ignore intervening phrases before checking the verb.",
            [
                (("The list of items", "are on the table", "near the window."), 2, "The head subject is 'list', so use 'is on the table'."),
                (("Each of the players", "have received", "a certificate."), 2, "'Each' is singular; use 'has received'."),
                (("The teacher, along with the students,", "is preparing", "for the exhibition."), 4, "The main subject is singular 'teacher'; the sentence is correct."),
                (("Neither of the answers", "seem", "correct to me."), 2, "Use 'seems' with singular 'neither'."),
                (("The quality of these products", "has improved", "significantly this year."), 4, "The head subject 'quality' is singular; the sentence is correct."),
                (("One of my friends", "live", "in Chennai."), 2, "The subject is 'one'; use 'lives'."),
                (("The committee members", "were divided", "in their opinions."), 4, "'Members' is plural and correctly takes 'were'."),
                (("Mathematics", "are", "my favourite subject."), 2, "The school subject 'Mathematics' is singular; use 'is'."),
                (("The bouquet of roses", "smell", "wonderful."), 2, "The head noun 'bouquet' is singular; use 'smells'."),
                (("Both the manager and the assistant", "has approved", "the request."), 2, "'Both...and' creates a plural subject; use 'have approved'."),
            ],
        ),
        (
            "tense-conditionals",
            "Tense and conditionals",
            45,
            "Use time markers and event order before choosing the tense.",
            [
                (("If it rains tomorrow", "we will stay", "at home."), 4, "This first conditional is correct."),
                (("If I will see him", "I will tell him", "the news."), 1, "Use simple present in the if-clause: 'If I see him'."),
                (("She has completed the report", "yesterday", "before leaving office."), 1, "With 'yesterday', use simple past: 'She completed'."),
                (("By the time the train arrived", "we waited", "for nearly an hour."), 2, "Use 'we had been waiting' for the earlier continuing past action."),
                (("He has lived here", "since 2019", "and still works nearby."), 4, "Present perfect with 'since 2019' is correct."),
                (("When I reached the station", "the train already left", "the platform."), 2, "Use 'had already left' for the earlier past event."),
                (("She did not attended", "the meeting", "last Monday."), 1, "After 'did not', use the base form 'attend'."),
                (("I have known her", "for five years", "now."), 4, "Present perfect with 'for five years' is correct."),
                (("If he had studied harder", "he would have passed", "the examination."), 4, "This third conditional is correct."),
                (("They were discussing the plan", "when the lights", "had gone out."), 3, "Use simple past 'went out' for the interrupting event."),
            ],
        ),
        (
            "articles-determiners",
            "Articles and determiners",
            45,
            "Check sound for a/an, specificity for the, and countability for quantity words.",
            [
                (("He bought", "an university textbook", "yesterday."), 2, "Use 'a university textbook' because 'university' begins with /juː/."),
                (("She is", "a honest officer", "in this department."), 2, "Use 'an honest officer' because the h is silent."),
                (("There is", "very little information", "available online."), 4, "The sentence is correct; 'information' is uncountable."),
                (("We saw", "the sun rise", "above the hills."), 4, "The definite article with the unique sun is correct."),
                (("He gave me", "an useful suggestion", "before the interview."), 2, "Use 'a useful suggestion' because 'useful' begins with /juː/."),
                (("Only a few students", "understood", "the final question."), 4, "'A few' is correct with countable plural 'students'."),
                (("She has", "much books", "on modern history."), 2, "Use 'many books' with a countable plural noun."),
                (("This is", "best solution", "to the problem."), 2, "Use 'the best solution'."),
                (("He waited for", "a hour", "outside the office."), 2, "Use 'an hour' because h is silent."),
                (("Less candidates", "appeared this year", "than last year."), 1, "Use 'fewer candidates' for a countable plural noun."),
            ],
        ),
        (
            "noun-countability-number",
            "Noun number and countability",
            45,
            "Classify the noun as countable or uncountable before checking plural and determiner use.",
            [
                (("It is not advisable", "to carry heavy luggages", "on a short journey."), 2, "Use uncountable 'luggage', not 'luggages'."),
                (("The office bought", "new furnitures", "for the conference room."), 2, "Use uncountable 'furniture'."),
                (("She gave me", "several useful pieces of advice", "before the interview."), 4, "'Pieces of advice' is correct."),
                (("The police", "is investigating", "the case."), 2, "Use plural verb 'are investigating' with 'police'."),
                (("These equipments", "are used", "in the laboratory."), 1, "Use 'This equipment' or 'These pieces of equipment'."),
                (("Five hundred rupees", "is enough", "for the ticket."), 4, "A sum of money viewed as one amount can take a singular verb."),
                (("He has", "many informations", "about the project."), 2, "Use 'much information' or 'a lot of information'."),
                (("The child has", "two tooths", "missing."), 2, "The plural of 'tooth' is 'teeth'."),
                (("We admired", "the beautiful sceneries", "during the journey."), 2, "Use uncountable 'scenery'."),
                (("She bought", "two loaves of bread", "from the bakery."), 4, "'Two loaves of bread' is correct."),
            ],
        ),
        (
            "pronoun-case-agreement",
            "Pronoun case and agreement",
            50,
            "Identify whether the pronoun is acting as subject, object, possessive or reflexive.",
            [
                (("Between you and I", "this plan seems", "too risky."), 1, "After 'between', use objective 'me': 'between you and me'."),
                (("Each student must bring", "his or her ID card", "to the examination hall."), 4, "The pronoun reference is consistent."),
                (("The teacher asked Rahul and I", "to stay back", "after class."), 1, "The pronoun is an object; use 'Rahul and me'."),
                (("This is the boy", "whom I believe", "won the prize."), 2, "Use 'who' because the relative pronoun is the subject of 'won'."),
                (("The manager himself", "checked the documents", "before signing them."), 4, "The reflexive is correctly used for emphasis."),
                (("She blamed", "herself", "for the mistake."), 4, "The reflexive is correct because subject and object refer to the same person."),
                (("Me and my sister", "visited the museum", "on Sunday."), 1, "Use subject form: 'My sister and I'."),
                (("The prize was shared", "between Ravi and he", "equally."), 2, "Use object form 'him' after 'between'."),
                (("One should", "keep one's promises", "whenever possible."), 4, "The pronoun reference is consistent."),
                (("The person to who", "I sent the letter", "replied yesterday."), 1, "After 'to', use objective relative pronoun 'whom'."),
            ],
        ),
        (
            "prepositions-collocations",
            "Prepositions and collocations",
            45,
            "Treat common adjective/verb + preposition combinations as fixed chunks.",
            [
                (("Arun is very good", "with solving puzzles", "under time pressure."), 2, "Use 'good at solving puzzles'."),
                (("She is interested", "in learning French", "this year."), 4, "'Interested in' is correct."),
                (("He insisted", "to paying the bill", "himself."), 2, "Use 'insisted on paying'."),
                (("The result depends", "on how carefully", "you read the question."), 4, "'Depend on' is correct."),
                (("He is capable", "to solve this problem", "without help."), 2, "Use 'capable of solving'."),
                (("She is married", "with a doctor", "from Delhi."), 2, "Use 'married to a doctor'."),
                (("The manager complied", "to the new rules", "immediately."), 2, "Use 'complied with the new rules'."),
                (("They congratulated him", "for his success", "in the examination."), 2, "Use 'congratulated him on his success'."),
                (("The child was afraid", "of the dark", "at night."), 4, "'Afraid of' is correct."),
                (("This book is different", "than the one", "I read last week."), 2, "In standard SSC usage, use 'different from'."),
            ],
        ),
        (
            "adjective-adverb-comparison",
            "Adjective, adverb and comparison",
            45,
            "Ask what the modifier describes; then check the comparison structure.",
            [
                (("She spoke", "concise during the briefing", "to save time."), 2, "Use adverb 'concisely' to modify 'spoke'."),
                (("She completed the task", "quick", "despite the pressure."), 2, "Use adverb 'quickly'."),
                (("This road is", "more narrower", "than the old one."), 2, "Avoid a double comparative; use 'narrower'."),
                (("He is", "senior than me", "in the department."), 2, "Use 'senior to me'."),
                (("The child looked", "happy", "after the result."), 4, "After a linking verb, adjective 'happy' is correct."),
                (("She sings", "beautifully", "at every concert."), 4, "The adverb correctly modifies 'sings'."),
                (("Of the two proposals", "this one is the best", "for our budget."), 2, "For two, use comparative 'better'."),
                (("The weather became", "suddenly cold", "in the evening."), 4, "The construction is grammatical."),
                (("He performed", "bad", "in the final round."), 2, "Use adverb 'badly'."),
                (("This is", "the most tallest building", "in the town."), 2, "Avoid double superlative; use 'the tallest building'."),
            ],
        ),
        (
            "verb-forms-modals",
            "Verb forms, gerunds and infinitives",
            50,
            "Find the governing auxiliary or verb and apply its required complement form.",
            [
                (("She did not went", "to the office", "yesterday."), 1, "After 'did not', use base form 'go'."),
                (("He can sings", "very well", "in public."), 1, "A modal takes the base form: 'can sing'."),
                (("She enjoys", "to read novels", "before bed."), 2, "Use gerund after 'enjoy': 'enjoys reading'."),
                (("They decided", "going by train", "instead of flying."), 2, "Use infinitive after 'decide': 'decided to go'."),
                (("Please avoid", "to make noise", "inside the library."), 2, "Use gerund after 'avoid': 'avoid making'."),
                (("He wants", "to improve his English", "before the exam."), 4, "'Want to improve' is correct."),
                (("You had better", "to leave now", "before it gets late."), 2, "Use bare infinitive: 'had better leave'."),
                (("The delay made me", "to wait outside", "for two hours."), 2, "Use bare infinitive after active 'make': 'made me wait'."),
                (("I am looking forward", "to meet you", "next week."), 2, "Use gerund after prepositional 'to': 'to meeting you'."),
                (("She let him", "use her laptop", "for an hour."), 4, "'Let + object + base verb' is correct."),
            ],
        ),
        (
            "parallelism-conjunctions",
            "Parallelism and conjunctions",
            55,
            "Check paired conjunctions and ensure coordinated items have matching grammatical forms.",
            [
                (("She likes reading", "swimming", "and to cycle."), 3, "Keep the list parallel: reading, swimming and cycling."),
                (("She is both intelligent", "as well as hardworking", "in her work."), 2, "Use the pair 'both...and'."),
                (("Neither Ravi", "or Mohan", "was available."), 2, "Use 'neither...nor'."),
                (("You can either call me", "and send an email", "before noon."), 2, "Use 'either...or'."),
                (("The job requires accuracy", "patience", "and working quickly."), 3, "Keep all coordinated items in parallel form."),
                (("He not only completed the report", "but also presented it", "to the board."), 4, "The paired structure is balanced."),
                (("She wants to learn", "how to code, how to design", "and managing projects."), 3, "Use parallel 'how to manage projects'."),
                (("The lecture was", "both informative and engaging", "for the students."), 4, "The two adjectives are correctly paired."),
                (("They will either", "travel by train", "nor take a bus."), 3, "Use 'either...or', not 'either...nor'."),
                (("He is", "neither careless nor lazy", "at work."), 4, "The sentence is correct."),
            ],
        ),
        (
            "standard-usage-phrases",
            "Standard usage and fixed expressions",
            55,
            "Learn frequent SSC corrections as complete usage chunks, not isolated words.",
            [
                (("On weekends", "I prefer reading", "than watching television."), 3, "Use 'prefer reading to watching television'."),
                (("I do not think", "I can cope up", "with this workload."), 2, "Standard usage is 'cope with'."),
                (("We discussed about the proposal", "for an hour", "before voting."), 1, "Use 'discussed the proposal'."),
                (("He returned back", "home late", "after the meeting."), 1, "'Return' already means come/go back; omit 'back'."),
                (("She entered into the room", "quietly", "during the lecture."), 1, "For physical entry, use 'entered the room'."),
                (("He resembles with his father", "in appearance", "and manner."), 1, "Use transitive 'resembles his father'."),
                (("We reached to the station", "before noon", "without difficulty."), 1, "Use 'reached the station'."),
                (("She has been absent", "from work", "since Monday."), 4, "'Absent from' is correct."),
                (("The teacher asked", "us to write down", "the answer carefully."), 4, "'Ask + object + infinitive' is correct."),
                (("He is accustomed", "to waking up early", "every day."), 4, "'Be accustomed to' correctly takes a gerund."),
            ],
        ),
    ]

    for pattern, subtopic, seconds, fast_method, cases in groups:
        for index, (parts, correct_option, explanation) in enumerate(cases):
            difficulty = 1 if index < 3 else 2 if index < 7 else 3
            bank.append(_make(
                pattern=pattern,
                subtopic=subtopic,
                difficulty=difficulty,
                seconds=seconds,
                parts=parts,
                correct_option=correct_option,
                explanation=explanation,
                fast_method=fast_method,
            ))

    if len(bank) != 100:
        raise AssertionError(f"Expected 100 questions, got {len(bank)}")
    return bank
