import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TopicRule:
    topic_slug: str
    patterns: tuple[str, ...]


RULES: dict[str, tuple[TopicRule, ...]] = {
    "reasoning": (
        TopicRule("coding-decoding", ("code language", "coded as", "written as", "coding")),
        TopicRule("number-series", ("number series", "missing number", "next number", "series?")),
        TopicRule("letter-series", ("letter-cluster", "letter series", "letters that")),
        TopicRule("dictionary-order", ("dictionary order", "english dictionary")),
        TopicRule("syllogism", ("statements:", "conclusions:", "logically follow")),
        TopicRule("mirror-and-water-images", ("mirror image", "water image", "mirror is placed")),
        TopicRule("paper-folding-and-cutting", ("paper is folded", "paper folding", "when unfolded")),
        TopicRule("dice-and-cubes", ("dice", "cube", "opposite face")),
        TopicRule("venn-diagrams", ("venn diagram", "set of classes", "relationship among")),
        TopicRule("mathematical-operations-and-sign-interchange", ("signs should be interchanged", "mathematical signs", "replace the * signs", "interchanging")),
        TopicRule("blood-relations", ("brother", "sister", "mother", "father", "son", "daughter", "blood relation")),
        TopicRule("direction-sense", ("north", "south", "east", "west", "direction")),
        TopicRule("analogy", ("related to the third", "same way as", "analogy")),
        TopicRule("classification-and-odd-one-out", ("odd one out", "does not belong", "different from the other")),
        TopicRule("figure-series", ("figure series", "figure that will come next")),
        TopicRule("embedded-figures", ("embedded", "hidden figure")),
        TopicRule("counting-figures", ("number of triangles", "number of squares", "count the")),
    ),
    "quant": (
        TopicRule("percentage", ("percentage", "%", "percent")),
        TopicRule("ratio-and-proportion", ("ratio", "proportion")),
        TopicRule("average", ("average", "mean")),
        TopicRule("profit-loss-and-discount", ("profit", "loss", "discount", "cost price", "selling price")),
        TopicRule("simple-interest", ("simple interest",)),
        TopicRule("compound-interest", ("compound interest",)),
        TopicRule("time-and-work", ("complete a work", "work in", "efficiency", "days to complete")),
        TopicRule("pipes-and-cisterns", ("pipe", "cistern", "tank")),
        TopicRule("time-speed-and-distance", ("speed", "distance", "km/h", "m/s")),
        TopicRule("trains", ("train", "platform")),
        TopicRule("boats-and-streams", ("boat", "stream", "upstream", "downstream")),
        TopicRule("mixture-and-alligation", ("mixture", "alligation")),
        TopicRule("algebra", ("equation", "polynomial", "x²", "x^2")),
        TopicRule("geometry", ("triangle", "circle", "angle", "chord", "radius")),
        TopicRule("mensuration", ("area", "volume", "surface area", "perimeter")),
        TopicRule("trigonometry", ("sin ", "cos ", "tan ", "trigonometric")),
        TopicRule("data-interpretation", ("histogram", "bar graph", "pie chart", "table below", "graph")),
        TopicRule("number-system", ("divisible", "remainder", "prime number", "number system")),
        TopicRule("lcm-and-hcf", ("lcm", "hcf", "greatest common", "least common")),
        TopicRule("simplification", ("simplified value", "simplify")),
    ),
    "english": (
        TopicRule("error-spotting", ("contains the error", "grammatical error", "identify the segment")),
        TopicRule("sentence-improvement", ("substitute the underlined", "no substitution", "no improvement")),
        TopicRule("synonyms-and-antonyms", ("synonym", "antonym")),
        TopicRule("one-word-substitution", ("one-word substitute", "one word substitute")),
        TopicRule("idioms-and-phrases", ("meaning of the idiom", "idiom")),
        TopicRule("spelling", ("incorrectly spelt", "correctly spelt", "spelling")),
        TopicRule("fill-in-the-blanks", ("fill in the blank", "fill in the blanks")),
        TopicRule("cloze-test", ("cloze", "passage", "blank no.")),
        TopicRule("active-and-passive-voice", ("active voice", "passive voice")),
        TopicRule("direct-and-indirect-speech", ("direct speech", "indirect speech", "reported speech")),
        TopicRule("para-jumbles", ("jumbled order", "correct order", "meaningful and coherent paragraph")),
        TopicRule("reading-comprehension", ("read the passage", "according to the passage")),
        TopicRule("vocabulary", ("meaning of the word", "most appropriate word")),
    ),
    "general-awareness": (
        TopicRule("history", ("empire", "dynasty", "movement", "revolt", "ancient", "medieval", "freedom struggle")),
        TopicRule("geography", ("river", "ocean", "mountain", "plateau", "soil", "latitude", "continent")),
        TopicRule("indian-polity", ("article", "constitution", "parliament", "rajya sabha", "lok sabha", "president")),
        TopicRule("economics", ("inflation", "gdp", "economy", "budget", "repo rate")),
        TopicRule("physics", ("physics", "force", "current", "voltage", "law", "light", "sound")),
        TopicRule("chemistry", ("chemical", "acid", "base", "element", "compound", "rust")),
        TopicRule("biology", ("cell", "organ", "disease", "vitamin", "plant", "human body")),
        TopicRule("environment", ("environment", "pollution", "biodiversity", "ozone", "wildlife")),
        TopicRule("art-and-culture", ("festival", "dance", "music", "temple", "painting")),
        TopicRule("awards-and-honours", ("award", "prize", "honour")),
        TopicRule("books-and-authors", ("author", "book", "written by")),
        TopicRule("important-days", ("day is observed", "week was observed", "international day", "world day")),
        TopicRule("sports", ("tournament", "championship", "player", "medal", "sports")),
        TopicRule("current-affairs", ("2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026")),
    ),
}


def suggest_topic(subject_slug: str, text: str) -> tuple[str | None, float]:
    normalized = re.sub(r"\s+", " ", text).lower()
    best_slug: str | None = None
    best_hits = 0

    for rule in RULES.get(subject_slug, ()):
        hits = sum(1 for pattern in rule.patterns if pattern in normalized)
        if hits > best_hits:
            best_slug = rule.topic_slug
            best_hits = hits

    if best_hits == 0:
        return None, 0.0

    confidence = min(0.95, 0.55 + (best_hits - 1) * 0.15)
    return best_slug, confidence
