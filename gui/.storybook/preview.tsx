import type { Decorator, Preview } from "@storybook/react-vite";
import "../src/fonts";
import "../src/tokens.css";
import { InkBleedDefs } from "../src/components/InkBleedDefs";

/** Light/dark via the same [data-theme] attribute the app uses — stories
 * exercise the real token system, not a Storybook-only theme. */
const withTheme: Decorator = (Story, context) => {
  const theme = (context.globals.theme as string) ?? "light";
  document.documentElement.dataset.theme = theme;
  document.body.style.background = "var(--paper)";
  document.body.style.color = "var(--ink)";
  document.body.style.fontFamily = "var(--font-body)";
  return (
    <>
      <InkBleedDefs />
      <Story />
    </>
  );
};

const preview: Preview = {
  globalTypes: {
    theme: {
      description: "Token theme",
      toolbar: {
        title: "Theme",
        items: ["light", "dark"],
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: { theme: "light" },
  decorators: [withTheme],
  // every component meta gets a generated docs page; descriptions live on the meta
  tags: ["autodocs"],
  parameters: {
    // axe violations FAIL the story test — accessibility is a gate, not a report
    a11y: { test: "error" },
    options: {
      // catalog order: the law first, then the objects it governs
      storySort: {
        order: ["Foundations", "Objects", "Patterns", "Screens"],
      },
    },
  },
};

export default preview;
