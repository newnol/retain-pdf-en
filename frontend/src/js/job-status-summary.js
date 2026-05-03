function numberOrNull(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function firstNonEmpty(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function stageKeyOf(payload) {
  return firstNonEmpty(payload.current_stage, payload.stage, payload.runtime?.current_stage).toLowerCase();
}

function stageCountsText(payload, stageKey = stageKeyOf(payload)) {
  const current = numberOrNull(payload.progress_current ?? payload.progress?.current);
  const total = numberOrNull(payload.progress_total ?? payload.progress?.total);
  if (current === null || total === null || total <= 0) {
    return "";
  }
  if (stageKey.includes("translat")) {
    return `Completed batch ${current}/${total} of translation`;
  }
  if (stageKey.includes("ocr") || stageKey.includes("parse")) {
    return `Completed page ${current}/${total} of OCR`;
  }
  if (stageKey.includes("render")) {
    return `Completed page ${current}/${total} of rendering`;
  }
  return `Progress ${current}/${total}`;
}

export function summarizeStageLabel(payload) {
  const stageKey = stageKeyOf(payload);
  if (payload.status === "succeeded") {
    return "Processing Complete";
  }
  if (payload.status === "failed") {
    return "Processing Failed";
  }
  if (payload.status === "canceled") {
    return "Task Canceled";
  }
  if (stageKey.includes("queue")) {
    return "Queued";
  }
  if (stageKey.includes("ocr") || stageKey.includes("parse")) {
    return "OCR In Progress";
  }
  if (stageKey.includes("translat")) {
    return "Translating";
  }
  if (stageKey.includes("normaliz")) {
    return "Normalizing";
  }
  if (stageKey.includes("render")) {
    return "Rendering";
  }
  if (stageKey.includes("sav")) {
    return "Saving";
  }
  if (stageKey.includes("finish")) {
    return payload.status === "running" ? "Processing" : "Processing Complete";
  }
  if (payload.status === "queued") {
    return "Queued";
  }
  if (payload.status === "running") {
    return "Processing";
  }
  return "Waiting";
}

export function summarizeStageDetail(payload) {
  const detail = firstNonEmpty(
    payload.failure?.summary,
    payload.stage_detail,
  );
  const stageLabel = summarizeStageLabel(payload);
  const countsText = stageCountsText(payload);
  if (detail) {
    if (detail === stageLabel) {
      return countsText || detail;
    }
    return countsText && !detail.includes(`${payload.progress_current ?? ""}/${payload.progress_total ?? ""}`)
      ? `${detail} · ${countsText}`
      : detail;
  }
  if (countsText) {
    return countsText;
  }
  const currentStage = firstNonEmpty(
    payload.runtime?.current_stage,
    payload.current_stage,
  );
  if (currentStage && currentStage !== stageLabel) {
    return `${stageLabel} · ${currentStage}`;
  }
  return stageLabel || "-";
}
