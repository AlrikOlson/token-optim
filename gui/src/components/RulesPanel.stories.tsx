import type { Meta, StoryObj } from "@storybook/react-vite";
import { RulesPanel } from "./RulesPanel";

const meta = {
  title: "Objects/SeatRecommendation/RulesPanel",
  component: RulesPanel,
  parameters: {
    docs: {
      description: {
        component:
          "The stated rules, on the record. Renders `RULES_SPEC.stated` from " +
          "`rules-spec.json` — the generated single source (gui-1b) that the " +
          "suggestion engine itself decides with and that the Python report " +
          "prints under \"How verdicts are decided\". The panel therefore " +
          "cannot state a rule the engine doesn't apply: values-never-lie, " +
          "extended to policy prose. Progressive disclosure (gui-14): closed " +
          "it's one quiet line under the Hearing masthead. Design-law note: " +
          "no VerdictStamp in here — stamps render true verdict values only.",
      },
    },
  },
} satisfies Meta<typeof RulesPanel>;
export default meta;

type Story = StoryObj<typeof meta>;

export const Closed: Story = {};

export const Open: Story = { args: { defaultOpen: true } };
