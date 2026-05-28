import { useEffect, useRef, useState } from "react";
import {
  aiAction,
  workflowRun,
  type AIAction,
  type WorkflowStepResult,
} from "../../services/api";
import styles from "./AIPanel.module.css";
import { WORKFLOW_TEMPLATES } from "./workflowTemplates";

interface WorkflowTabProps {
  getSelection: () => string;
  onInsertText: (text: string) => void;
  onOpenCorpus?: () => void;
}

const ACTION_LABELS: Record<AIAction, string> = {
  summarize: "Summarize",
  translate: "Translate",
  rewrite: "Rewrite / Polish",
  expand: "Expand",
  explain_term: "Explain Term",
  logic_check: "Logic Check",
  deai: "De-AI",
  research_gap: "Research Gap",
  paper_structure: "Paper Structure",
  citation_check: "Citation Check",
  abstract_draft: "Abstract Draft",
};

export default function WorkflowTab({ getSelection, onInsertText, onOpenCorpus }: WorkflowTabProps) {
  const [selectedTemplateId, setSelectedTemplateId] = useState(WORKFLOW_TEMPLATES[0].id);
  const [workingText, setWorkingText] = useState("");
  const [completedSteps, setCompletedSteps] = useState<WorkflowStepResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [sourceLang, setSourceLang] = useState("en");
  const [targetLang, setTargetLang] = useState("zh");
  const runIdRef = useRef(0);

  const selectedTemplate =
    WORKFLOW_TEMPLATES.find((template) => template.id === selectedTemplateId) ??
    WORKFLOW_TEMPLATES[0];
  const remainingSteps = selectedTemplate.steps.slice(completedSteps.length);
  const nextAction = remainingSteps[0];
  const usesTranslate = selectedTemplate.steps.includes("translate");

  useEffect(() => {
    setCompletedSteps([]);
    setStatusMsg("");
  }, [selectedTemplateId]);

  useEffect(() => {
    return () => {
      runIdRef.current += 1;
    };
  }, []);

  const ensureText = () => {
    if (workingText.trim()) return true;
    setStatusMsg("Please load selected text or paste text before running a workflow.");
    return false;
  };

  const handleLoadSelection = () => {
    if (loading) return;
    const text = getSelection();
    if (!text) {
      setStatusMsg("Please select text in the editor first.");
      return;
    }
    setWorkingText(text);
    setCompletedSteps([]);
    setStatusMsg("");
  };

  const handleRunNext = async () => {
    if (!nextAction || !ensureText()) return;

    const runId = runIdRef.current + 1;
    runIdRef.current = runId;
    setLoading(true);
    setStatusMsg("");
    try {
      const res = await aiAction(
        nextAction,
        workingText,
        undefined,
        sourceLang,
        targetLang,
      );
      if (runId !== runIdRef.current) return;
      const stepResult: WorkflowStepResult = {
        action: nextAction,
        result: res.result,
      };
      const newCompletedCount = completedSteps.length + 1;

      setCompletedSteps((prev) => [...prev, stepResult]);
      setWorkingText(res.result);
      if (newCompletedCount === selectedTemplate.steps.length) {
        setStatusMsg("Workflow completed.");
      }
    } catch (err: unknown) {
      if (runId !== runIdRef.current) return;
      setStatusMsg(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      if (runId === runIdRef.current) {
        setLoading(false);
      }
    }
  };

  const handleRunAll = async () => {
    if (remainingSteps.length === 0 || !ensureText()) return;

    const runId = runIdRef.current + 1;
    runIdRef.current = runId;
    setLoading(true);
    setStatusMsg("");
    try {
      const res = await workflowRun(
        remainingSteps,
        workingText,
        undefined,
        sourceLang,
        targetLang,
      );
      if (runId !== runIdRef.current) return;
      const totalCompletedCount = completedSteps.length + res.steps.length;
      setCompletedSteps((prev) => [...prev, ...res.steps]);
      setWorkingText(res.result);
      if (res.completed) {
        setStatusMsg("Workflow completed.");
      } else {
        setStatusMsg(
          `Workflow stopped after ${totalCompletedCount}/${selectedTemplate.steps.length} steps: ${res.error ?? "Unknown error"}`
        );
      }
    } catch (err: unknown) {
      if (runId !== runIdRef.current) return;
      setStatusMsg(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      if (runId === runIdRef.current) {
        setLoading(false);
      }
    }
  };

  const handleReset = () => {
    if (loading) return;
    setCompletedSteps([]);
    setStatusMsg("");
  };

  return (
    <div className={styles.workflowTab}>
      <div className={styles.workflowSection}>
        <label className={styles.fieldLabel} htmlFor="workflow-template">
          Template
        </label>
        <select
          id="workflow-template"
          value={selectedTemplateId}
          onChange={(e) => setSelectedTemplateId(e.target.value)}
          className={styles.workflowSelect}
          disabled={loading}
        >
          {WORKFLOW_TEMPLATES.map((template) => (
            <option key={template.id} value={template.id}>
              {template.label}
            </option>
          ))}
        </select>
        <div className={styles.templateDescription}>{selectedTemplate.description}</div>
        <div className={styles.workflowSteps}>
          {selectedTemplate.steps.map((step, index) => {
            const stateClass =
              index < completedSteps.length
                ? styles.workflowStepDone
                : index === completedSteps.length
                  ? styles.workflowStepCurrent
                  : styles.workflowStepPending;

            return (
              <div key={`${selectedTemplate.id}-${step}-${index}`} className={`${styles.workflowStep} ${stateClass}`}>
                <span className={styles.workflowStepIndex}>{index + 1}</span>
                <span>{ACTION_LABELS[step]}</span>
              </div>
            );
          })}
        </div>
      </div>

      {usesTranslate && (
        <div className={styles.langRow}>
          <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)} disabled={loading}>
            <option value="en">English</option>
            <option value="zh">Chinese</option>
          </select>
          <span>&rarr;</span>
          <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)} disabled={loading}>
            <option value="zh">Chinese</option>
            <option value="en">English</option>
          </select>
        </div>
      )}

      <div className={styles.workflowControls}>
        <button type="button" onClick={handleLoadSelection} disabled={loading} className={styles.secondaryBtn}>
          Use Selected Text
        </button>
        <button
          type="button"
          onClick={handleRunNext}
          disabled={loading || !nextAction}
          className={styles.runBtn}
        >
          {loading ? "Running..." : nextAction ? `Run Next: ${ACTION_LABELS[nextAction]}` : "Workflow Complete"}
        </button>
        <button
          type="button"
          onClick={handleRunAll}
          disabled={loading || remainingSteps.length === 0}
          className={styles.secondaryBtn}
        >
          {loading ? "Running..." : completedSteps.length > 0 ? "Run Remaining Steps" : "Run Full Workflow"}
        </button>
        <button type="button" onClick={handleReset} disabled={loading} className={styles.secondaryBtn}>
          Reset Steps
        </button>
      </div>

      <div className={styles.workflowSection}>
        <label className={styles.fieldLabel} htmlFor="workflow-text">
          Current Text
        </label>
        <textarea
          id="workflow-text"
          value={workingText}
          onChange={(e) => setWorkingText(e.target.value)}
          className={styles.workflowInput}
          placeholder="Load selected text or paste text here, then run the workflow."
          disabled={loading}
        />
      </div>

      <div className={styles.corpusRow}>
        <span className={styles.corpusHint}>Corpus feeds the AI knowledge base for RAG and workflows.</span>
        <button type="button" onClick={onOpenCorpus} className={styles.corpusBtn}>
          Manage Corpus
        </button>
      </div>

      {statusMsg && <div className={styles.workflowStatus}>{statusMsg}</div>}

      {completedSteps.length > 0 && (
        <div className={styles.workflowHistory}>
          {completedSteps.map((step, index) => (
            <div key={`${step.action}-${index}`} className={styles.workflowHistoryItem}>
              <div className={styles.workflowHistoryHeader}>
                <span>{index + 1}. {ACTION_LABELS[step.action]}</span>
              </div>
              <div className={styles.workflowHistoryOutput}>{step.result}</div>
            </div>
          ))}
        </div>
      )}

      {completedSteps.length > 0 && (
        <div className={styles.resultArea}>
          <div className={styles.resultHeader}>
            <span>Current Result</span>
            <button onClick={() => onInsertText(workingText)} className={styles.insertBtn}>
              Insert into Editor
            </button>
          </div>
          <div className={styles.resultText}>{workingText}</div>
        </div>
      )}
    </div>
  );
}
