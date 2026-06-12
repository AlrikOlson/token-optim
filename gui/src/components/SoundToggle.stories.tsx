import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";
import { SoundToggle } from "./SoundToggle";

const meta = {
  title: "Patterns/Office/SoundToggle",
  component: SoundToggle,
  parameters: {
    docs: {
      description: {
        component:
          "Saga Act IV — The Office Speaks. Synthesized Web Audio (no samples): the stamp " +
          "thunk on a verdict, a paper shuffle on card flight, the heavier seal press, a " +
          "typewriter tick as the docket advances. The values-never-lie rule extends to ears: " +
          "a sound fires only from a real domain event, never decoratively. Strictly opt-in — " +
          "OFF by default, this visible toggle persists the choice, reduced-motion silences " +
          "everything, and the client-facing deliverable surfaces are structurally incapable " +
          "of sound (they may not import the module; test-enforced). Toggling ON plays the " +
          "stamp once — the click is the autoplay-policy gesture and the preview.",
      },
    },
  },
} satisfies Meta<typeof SoundToggle>;
export default meta;

type Story = StoryObj<typeof meta>;

export const OptIn: Story = {
  args: { persistent: false },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const toggle = canvas.getByTestId("sound-toggle");
    // off by default, accessible state, flips on click
    await expect(toggle).toHaveAttribute("aria-pressed", "false");
    await expect(toggle).toHaveTextContent(/off/i);
    await userEvent.click(toggle);
    await expect(toggle).toHaveAttribute("aria-pressed", "true");
    await expect(toggle).toHaveTextContent(/on/i);
    // leave the catalog quiet for the next story
    await userEvent.click(toggle);
    await expect(toggle).toHaveAttribute("aria-pressed", "false");
  },
};
