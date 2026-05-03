import { $ } from "../../dom.js";
import {
  getRecentJobsState,
  resetRecentJobsPagination,
  setRecentJobsDate,
  setRecentJobsHasMore,
  setRecentJobsItems,
  setRecentJobsOffset,
} from "./state.js";
import {
  renderRecentJobsEmpty,
  renderRecentJobsError,
  renderRecentJobsList,
  renderRecentJobsLoading,
  setRecentJobsLoadMoreLoading,
} from "./view.js";

function padDatePart(value) {
  return `${value}`.padStart(2, "0");
}

function formatDateKey(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return "";
  }
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`;
}

function recentJobDateKey(value) {
  const raw = `${value || ""}`.trim();
  if (!raw) {
    return "";
  }
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  return formatDateKey(parsed);
}

function setDialogOpen(open) {
  const dialog = $("query-dialog");
  if (!dialog) {
    return;
  }
  if (open) {
    dialog.showModal();
  } else {
    dialog.close();
  }
  $("open-query-btn")?.setAttribute("aria-expanded", open ? "true" : "false");
}

function dedupeRecentJobs(items) {
  const seen = new Set();
  const result = [];
  for (const item of Array.isArray(items) ? items : []) {
    const jobId = `${item?.job_id || ""}`.trim();
    if (!jobId || seen.has(jobId)) {
      continue;
    }
    seen.add(jobId);
    result.push(item);
  }
  return result;
}

function isPrimaryRecentJob(item) {
  const workflow = `${item?.workflow || item?.job_type || ""}`.trim();
  const jobId = `${item?.job_id || ""}`.trim();
  if (workflow === "ocr") {
    return false;
  }
  if (jobId.endsWith("-ocr")) {
    return false;
  }
  return true;
}

async function collectRecentJobsPage(fetchJobList, apiPrefix, startOffset, selectedDate, pageSize) {
  const fetchLimit = Math.max(pageSize, 20);
  const collected = [];
  let latestInvocationSummary = null;
  let nextOffset = startOffset;
  let hasMore = true;

  while (collected.length < pageSize) {
    const payload = await fetchJobList(apiPrefix, { limit: fetchLimit, offset: nextOffset });
    latestInvocationSummary = payload?.invocation_summary || latestInvocationSummary;
    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (items.length === 0) {
      hasMore = false;
      break;
    }

    let consumed = 0;
    for (const item of items) {
      consumed += 1;
      if (!isPrimaryRecentJob(item)) {
        continue;
      }
      const dateKey = recentJobDateKey(item.updated_at || item.created_at);
      if (!dateKey) {
        continue;
      }
      if (selectedDate) {
        if (dateKey > selectedDate) {
          continue;
        }
        if (dateKey < selectedDate) {
          hasMore = false;
          break;
        }
      }
      collected.push(item);
      if (collected.length >= pageSize) {
        break;
      }
    }

    nextOffset += consumed;

    if (!hasMore || collected.length >= pageSize) {
      break;
    }
    if (items.length < fetchLimit) {
      hasMore = false;
      break;
    }
  }

  return {
    collected,
    hasMore,
    latestInvocationSummary,
    nextOffset,
  };
}

export function mountRecentJobsFeature({ fetchJobList, apiPrefix, startPolling }) {
  async function loadRecentJobs({ reset = false } = {}) {
    const list = $("recent-jobs-list");
    const empty = $("recent-jobs-empty");
    const loadMoreButton = $("load-more-jobs-btn");
    if (!list || !empty || !loadMoreButton) {
      return;
    }
    if (reset) {
      resetRecentJobsPagination();
      renderRecentJobsLoading();
    } else {
      setRecentJobsLoadMoreLoading();
    }

    try {
      const { date, offset, items: previousItems } = getRecentJobsState();
      const selectedDate = `${date || ""}`.trim();
      const pageSize = 5;
      const {
        collected,
        hasMore,
        latestInvocationSummary,
        nextOffset,
      } = await collectRecentJobsPage(
        fetchJobList,
        apiPrefix,
        reset ? 0 : offset,
        selectedDate,
        pageSize,
      );

      if (reset && collected.length === 0) {
        setRecentJobsItems([]);
        setRecentJobsHasMore(false);
        renderRecentJobsEmpty(selectedDate ? "No jobs for selected date" : "No recent jobs", latestInvocationSummary);
        return;
      }
      if (!reset && collected.length === 0) {
        setRecentJobsHasMore(false);
        renderRecentJobsError("", { reset: false });
        return;
      }

      const nextItems = dedupeRecentJobs(reset ? collected : [...previousItems, ...collected]);
      setRecentJobsOffset(nextOffset);
      setRecentJobsHasMore(hasMore);
      setRecentJobsItems(nextItems);
      renderRecentJobsList({
        items: nextItems,
        allItems: nextItems,
        invocationSummary: latestInvocationSummary,
        reset,
        hasMore,
        onSelect(jobId) {
          if (!jobId) {
            return;
          }
          closeRecentJobsDialog();
          startPolling(jobId);
        },
      });
    } catch (err) {
      if (!reset) {
        setRecentJobsHasMore(false);
      }
      renderRecentJobsError(err.message || "Failed to load recent jobs", { reset });
    }
  }

  function openRecentJobsDialog() {
    if ($("recent-jobs-date")) {
      $("recent-jobs-date").value = getRecentJobsState().date;
    }
    loadRecentJobs({ reset: true });
    setDialogOpen(true);
  }

  function closeRecentJobsDialog() {
    setDialogOpen(false);
  }

  $("open-query-btn")?.addEventListener("click", openRecentJobsDialog);
  $("refresh-jobs-btn")?.addEventListener("click", () => loadRecentJobs({ reset: true }));
  $("load-more-jobs-btn")?.addEventListener("click", () => loadRecentJobs({ reset: false }));
  $("recent-jobs-date")?.addEventListener("change", (event) => {
    const target = event.currentTarget;
    if (target instanceof HTMLInputElement) {
      setRecentJobsDate(target.value || "");
      loadRecentJobs({ reset: true });
    }
  });

  return {
    openRecentJobsDialog,
    closeRecentJobsDialog,
    loadRecentJobs,
  };
}
