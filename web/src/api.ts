export type FilterTag = {
  field: string;
  value: string;
};

export type AskFilters = {
  source: string;
  tags: FilterTag[];
};

export type AskBody = {
  text: string;
  session?: string;
  filters?: AskFilters;
};

export type Citation = {
  id: string;
  source: string;
  pages: number[];
  snippet: string;
};

export type GenerationResult = {
  answer: string;
  citations: Citation[];
  tags: FilterTag[];
};

function isFilterTag(value: unknown): value is FilterTag {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const row = value as Record<string, unknown>;
  return typeof row.field === "string" && row.field !== "" && typeof row.value === "string" && row.value !== "";
}

function isCitation(value: unknown): value is Citation {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const row = value as Record<string, unknown>;
  return (
    typeof row.id === "string" &&
    typeof row.source === "string" &&
    Array.isArray(row.pages) &&
    row.pages.every((page) => typeof page === "number") &&
    typeof row.snippet === "string"
  );
}

function isGenerationResult(value: unknown): value is GenerationResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const row = value as Record<string, unknown>;
  if (typeof row.answer !== "string" || !Array.isArray(row.citations)) {
    return false;
  }
  if (!row.citations.every(isCitation)) {
    return false;
  }
  if (!("tags" in row) || row.tags === undefined) {
    return true;
  }
  return Array.isArray(row.tags) && row.tags.every(isFilterTag);
}

function formatValidationRow(value: unknown): string {
  if (typeof value !== "object" || value === null) {
    return "";
  }
  const row = value as Record<string, unknown>;
  const message = typeof row.msg === "string" ? row.msg : "";
  if (message === "") {
    return "";
  }
  const location = Array.isArray(row.loc)
    ? row.loc.filter((part) => typeof part === "string" || typeof part === "number").join(".")
    : "";
  return location === "" ? message : `${location}: ${message}`;
}

function readDetail(value: unknown, status: number): string {
  if (typeof value !== "object" || value === null) {
    return `请求失败（HTTP ${status}）`;
  }
  const row = value as Record<string, unknown>;
  if (typeof row.detail === "string" && row.detail !== "") {
    return row.detail;
  }
  // FastAPI 的 422 校验错误把 detail 写成 list：只认 string 会把字段级诊断吞成「请求失败」
  if (Array.isArray(row.detail)) {
    const messages = row.detail.map(formatValidationRow).filter((line) => line !== "");
    if (messages.length > 0) {
      return messages.join("；");
    }
  }
  return `请求失败（HTTP ${status}）`;
}

export async function askQuestion(body: AskBody): Promise<GenerationResult> {
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let raw: unknown;
  try {
    raw = await response.json();
  } catch {
    throw new Error("响应不是 JSON");
  }
  if (!response.ok) {
    throw new Error(readDetail(raw, response.status));
  }
  if (!isGenerationResult(raw)) {
    throw new Error("响应不是生成结果");
  }
  const row = raw as GenerationResult & { tags?: FilterTag[] };
  const result: GenerationResult = {
    answer: row.answer,
    citations: row.citations,
    tags: Array.isArray(row.tags) ? row.tags : [],
  };
  return result;
}
