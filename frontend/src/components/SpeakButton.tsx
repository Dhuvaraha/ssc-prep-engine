import { useState } from "react";

type Props = {
  text: string;
  label?: string;
};

export default function SpeakButton({ text, label = "Read aloud" }: Props) {
  const [speaking, setSpeaking] = useState(false);

  function toggle() {
    if (!("speechSynthesis" in window)) return;

    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  }

  return (
    <button className={speaking ? "speakButton speaking" : "speakButton"} onClick={toggle}>
      {speaking ? "■ Stop" : "🔊 " + label}
    </button>
  );
}
