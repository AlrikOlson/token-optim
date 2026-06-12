import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  _resetSoundForTests,
  playSound,
  restoreSoundPreference,
  setSoundEnabled,
  SOUND_KEY,
  soundEnabled,
} from "./sound";

afterEach(() => {
  _resetSoundForTests();
  localStorage.removeItem(SOUND_KEY);
  vi.unstubAllGlobals();
});

describe("the office speaks — engine discipline (gui-10)", () => {
  it("is OFF by default", () => {
    expect(soundEnabled()).toBe(false);
  });

  it("persists the preference only when asked to", () => {
    setSoundEnabled(true, true);
    expect(localStorage.getItem(SOUND_KEY)).toBe("true");
    _resetSoundForTests();
    restoreSoundPreference();
    expect(soundEnabled()).toBe(true);

    localStorage.removeItem(SOUND_KEY);
    setSoundEnabled(true, false); // story/test mode: session only
    expect(localStorage.getItem(SOUND_KEY)).toBeNull();
  });

  it("never constructs an AudioContext while disabled", () => {
    const Ctor = vi.fn();
    vi.stubGlobal("AudioContext", Ctor);
    playSound("stamp");
    expect(Ctor).not.toHaveBeenCalled();
  });

  it("reduced motion silences the office even when enabled", () => {
    const Ctor = vi.fn();
    vi.stubGlobal("AudioContext", Ctor);
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockReturnValue({ matches: true }),
    );
    setSoundEnabled(true, false);
    playSound("seal");
    expect(Ctor).not.toHaveBeenCalled();
  });

  it("no-ops without Web Audio (jsdom) instead of throwing", () => {
    setSoundEnabled(true, false);
    expect(() => playSound("stamp")).not.toThrow();
    expect(() => playSound("shuffle")).not.toThrow();
    expect(() => playSound("seal")).not.toThrow();
    expect(() => playSound("tick")).not.toThrow();
  });
});

describe("deliverable silence — the register gate for ears", () => {
  // The client-facing surfaces must be structurally incapable of sound:
  // they may not import sound.ts, same rule as the voice.ts register gate.
  const SILENT_FILES = [
    "components/ReportPreview.tsx",
    "components/QBRPack.tsx",
    "components/CaveatBlock.tsx",
    "components/BrandChip.tsx",
    "screens/SealedArchive.tsx",
    "screens/QBRView.tsx",
    "screens/SealFlow.tsx",
  ];

  it("deliverable contexts never import the sound module", () => {
    for (const rel of SILENT_FILES) {
      const text = readFileSync(join(process.cwd(), "src", rel), "utf8");
      expect(text, rel).not.toMatch(/from\s+["'][./]*\.\.?\/?sound["']/);
      expect(text, rel).not.toContain("playSound");
    }
  });

  it("every playSound call site lives in an event handler file (App or a screen with the toggle)", () => {
    // sweep all source files: the only modules allowed to call playSound
    // are App.tsx (domain event handlers) and SoundToggle (the opt-in click)
    const allowed = new Set(["App.tsx", "components/SoundToggle.tsx", "sound.ts", "sound.test.ts"]);
    const offenders: string[] = [];
    const walk = (dir: string): void => {
      for (const name of readdirSync(dir)) {
        const p = join(dir, name);
        if (statSync(p).isDirectory()) {
          walk(p);
          continue;
        }
        if (!/\.tsx?$/.test(p) || /\.stories\.tsx$/.test(p)) continue;
        const rel = p.replace(join(process.cwd(), "src") + "/", "");
        if (allowed.has(rel)) continue;
        if (readFileSync(p, "utf8").includes("playSound")) offenders.push(rel);
      }
    };
    walk(join(process.cwd(), "src"));
    expect(offenders).toEqual([]);
  });
});
