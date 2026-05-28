import type { AIAction } from "../../services/api";

export interface WorkflowTemplate {
  id: string;
  label: string;
  description: string;
  steps: AIAction[];
}

export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  {
    id: "translate-polish",
    label: "Translate & Polish",
    description: "Translate first, then polish the academic tone and remove formulaic phrasing.",
    steps: ["translate", "rewrite", "deai"],
  },
  {
    id: "expand-refine",
    label: "Expand & Refine",
    description: "Turn notes into full prose, polish the writing, then tighten the logic.",
    steps: ["expand", "rewrite", "logic_check"],
  },
  {
    id: "full-review",
    label: "Full Review",
    description: "Check logic, flag weak citation support, then rewrite the text into a cleaner draft.",
    steps: ["logic_check", "citation_check", "rewrite"],
  },
  {
    id: "research-analysis",
    label: "Research Analysis",
    description: "Summarize the material, identify gaps, and turn them into a paper structure.",
    steps: ["summarize", "research_gap", "paper_structure"],
  },
  {
    id: "draft-abstract",
    label: "Draft Abstract",
    description: "Condense a long passage into a structured abstract and smooth out the wording.",
    steps: ["summarize", "abstract_draft", "deai"],
  },
  {
    id: "humanize-ai-text",
    label: "Humanize AI Text",
    description: "Reduce AI-style phrasing first, then polish the final tone.",
    steps: ["deai", "rewrite"],
  },
  {
    id: "deep-expansion",
    label: "Deep Expansion",
    description: "Go from short notes to a fuller draft, then polish, humanize, and logic-check it.",
    steps: ["expand", "rewrite", "deai", "logic_check"],
  },
];
