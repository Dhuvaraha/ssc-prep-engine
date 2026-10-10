import { useEffect, useMemo, useState } from "react";

type Props = {
  title: string;
  context?: string;
  explanation?: string | null;
  fastMethod?: string | null;
  commonTrap?: string | null;
  standardMethod?: string | null;
  examples?: string[];
  correctAnswer?: string | null;
  selectedAnswer?: string | null;
  onNext?: () => void;
  onHintUsed?: () => void;
  onAsk?: (prompt: string) => Promise<string>;
  defaultOpen?: boolean;
  lead?: string | null;
  hintSteps?: string[];
};

function speak(text: string) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = Number(localStorage.getItem("ssc_voice_rate") ?? "0.94");
  utterance.lang = "en-IN";
  window.speechSynthesis.speak(utterance);
}

export default function TeacherCoach({
  title,
  context = "",
  explanation,
  fastMethod,
  commonTrap,
  standardMethod,
  examples = [],
  correctAnswer,
  selectedAnswer,
  onNext,
  onHintUsed,
  onAsk,
  defaultOpen = false,
  lead,
  hintSteps = [],
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [input, setInput] = useState("");
  const [answer, setAnswer] = useState(
    lead || "Ask for a hint, explanation, shortcut, common trap, or why an answer is wrong."
  );
  const [listening, setListening] = useState(false);
  const [exampleIndex, setExampleIndex] = useState(0);
  const [hintIndex, setHintIndex] = useState(0);

  useEffect(() => {
    if (lead) setAnswer(lead);
    setHintIndex(0);
  }, [lead, title]);

  const quickPrompts = useMemo(() => {
    const tanglish = localStorage.getItem("ssc_preferred_language") === "tanglish";
    return tanglish
      ? ["Hint kudu", "Simple ah explain pannu", "Inoru example", "Rendu method compare pannu", "Shortcut kaatu", "Common trap", "En answer en wrong?", "Inoru question", "Repeat", "Stop"]
      : ["Give me a hint", "Explain simply", "Another example", "Compare methods", "Show shortcut", "Common trap", "Why was I wrong?", "One more like this", "Repeat", "Stop"];
  }, []);

  async function respond(raw: string) {
    const q = raw.trim().toLowerCase();
    if (!q) return;

    if (onAsk && q !== "stop") {
      try { setAnswer(await onAsk(raw)); }
      catch { setAnswer("Teaching is unavailable. Finish any active assessment and retry."); }
      return;
    }
    let next = "";
    if (q === "stop" || q.includes("stop speaking")) {
      window.speechSynthesis?.cancel();
      next = "Voice stopped.";
    } else if (q === "repeat" || q.includes("repeat that")) {
      next = answer;
      speak(answer);
    } else if (q.includes("one more like this") || q.includes("inoru question") || q.includes("another question")) {
      next = onNext
        ? "Okay. Moving to the next question in this same practice flow."
        : "Open the quick check or guided practice to solve another question using this same skill.";
      onNext?.();
    } else if (q.includes("next")) {
      next = "Moving to the next question.";
      onNext?.();
    } else if (q.includes("another example") || q.includes("one more example") || q.includes("inoru example")) {
      if (examples.length) {
        const picked = examples[exampleIndex % examples.length];
        setExampleIndex((value) => value + 1);
        next = "Example: " + picked;
      } else {
        next = "This screen does not have another verified worked example attached. Use the quick check for a fresh application of the same rule.";
      }
    } else if ((q.includes("compare") && q.includes("method")) || q.includes("rendu method")) {
      next = "Standard method: " + (standardMethod || context || "apply the full rule step by step") +
        ". Fast method: " + (fastMethod || "use elimination only after the governing rule is clear") + ".";
    } else if (q.includes("hint")) {
      onHintUsed?.();
      if (hintSteps.length) {
        const picked = hintSteps[Math.min(hintIndex, hintSteps.length - 1)];
        next = "Hint " + (Math.min(hintIndex, hintSteps.length - 1) + 1) + ": " + picked;
        setHintIndex((value) => Math.min(value + 1, hintSteps.length - 1));
      } else {
        next = fastMethod
          ? "Hint: first identify the pattern or rule. " + fastMethod
          : "Hint: identify what the question is testing, eliminate impossible options, then solve only the remaining choices.";
      }
    } else if (q.includes("shortcut") || q.includes("fast")) {
      next = fastMethod || "Use the smallest reliable method: identify the rule, eliminate impossible options, then calculate only what is necessary.";
    } else if (q.includes("trap") || q.includes("mistake")) {
      next = commonTrap || "Common trap: rushing into the options before identifying the exact rule or changing the method midway.";
    } else if (q.includes("wrong") || q.includes("why") || q.includes("en wrong")) {
      if (correctAnswer) {
        next = selectedAnswer
          ? "You chose " + selectedAnswer + ", while the correct answer is " + correctAnswer + ". " + (explanation || "Re-check the governing rule and compare both options.")
          : "The correct answer is " + correctAnswer + ". " + (explanation || "Apply the governing rule step by step.");
      } else {
        next = explanation || "Re-check the governing rule, the exact wording, and the option that preserves it.";
      }
    } else if (q.includes("explain") || q.includes("simple") || q.includes("teach") || q.includes("explain pannu")) {
      next = explanation || context || "Focus on the core rule for " + title + ", then apply it once before trying the shortcut.";
    } else if (q.includes("read")) {
      next = context || explanation || title;
    } else {
      next = "For " + title + ", ask me: “give me a hint”, “explain simply”, “show shortcut”, “another example”, “compare methods”, “common trap”, “why was I wrong?”, or “next”.";
    }
    setAnswer(next);
    if (localStorage.getItem("ssc_auto_speak") === "true") speak(next);
  }

  function startListening() {
    const w = window as typeof window & {
      SpeechRecognition?: new () => {
        lang: string;
        interimResults: boolean;
        onresult: (event: any) => void;
        onend: () => void;
        onerror: () => void;
        start: () => void;
      };
      webkitSpeechRecognition?: new () => any;
    };
    const Recognition = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!Recognition) {
      setAnswer("Voice input is not supported in this browser. You can type the same question below.");
      return;
    }
    const recognition = new Recognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.onresult = (event: any) => {
      const transcript = String(event.results?.[0]?.[0]?.transcript ?? "");
      setInput(transcript);
      respond(transcript);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    setListening(true);
    recognition.start();
  }

  return (
    <section className="teacherCoach">
      <button className="teacherCoachToggle" onClick={() => setOpen((value) => !value)}>
        <span>◉</span>
        <div>
          <strong>Teacher Coach</strong>
          <small>Explain • hint • method • trap</small>
        </div>
        <b>{open ? "−" : "+"}</b>
      </button>

      {open && (
        <div className="teacherCoachBody">
          <p className="teacherAnswer">{answer}</p>
          <div className="teacherQuickPrompts">
            {quickPrompts.map((prompt) => (
              <button key={prompt} onClick={() => { setInput(prompt); respond(prompt); }}>{prompt}</button>
            ))}
          </div>
          <div className="teacherInputRow">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") respond(input);
              }}
              placeholder="Ask the teacher..."
            />
            <button className={listening ? "teacherMic listening" : "teacherMic"} onClick={startListening} aria-label="Voice question">
              {listening ? "●" : "🎙"}
            </button>
            <button onClick={() => respond(input)}>Ask</button>
          </div>
          <button className="teacherSpeak" onClick={() => speak(answer)}>🔊 Read teacher answer</button>
        </div>
      )}
    </section>
  );
}
