import { useState } from "react";
import { playSound, setSoundEnabled, soundEnabled } from "../sound";

/** The visible sound switch (gui-10): office sounds are OFF by default and
 * only ever opt-in. `persistent` follows the App's discipline — preference
 * survives reload in the real app, stays session-only under an explicit
 * initial state so stories and tests are deterministic. Toggling ON plays
 * the stamp once: the click IS the user gesture the autoplay policy wants,
 * and the user hears exactly what they enabled. */
export function SoundToggle({ persistent = true }: { persistent?: boolean }) {
  const [on, setOn] = useState(soundEnabled);
  return (
    <button
      aria-pressed={on}
      data-testid="sound-toggle"
      onClick={() => {
        const next = !on;
        setSoundEnabled(next, persistent);
        setOn(next);
        if (next) playSound("stamp");
      }}
    >
      Sound: {on ? "on" : "off"}
    </button>
  );
}
