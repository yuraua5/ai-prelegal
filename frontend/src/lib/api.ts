/** Thin fetch wrappers for the Prelegal backend. */

const API_BASE = '/api';

export interface TemplateSummary {
  name: string;
  description: string;
  filename: string;
}

export interface TemplateDetail extends TemplateSummary {
  body: string;
  fields: string[];
}

export async function fetchTemplates(): Promise<TemplateSummary[]> {
  const response = await fetch(`${API_BASE}/templates`);
  if (!response.ok) {
    throw new Error(`GET /api/templates failed: ${response.status}`);
  }
  return (await response.json()) as TemplateSummary[];
}

export async function fetchTemplateDetail(filename: string): Promise<TemplateDetail> {
  const response = await fetch(`${API_BASE}/templates/${encodeURIComponent(filename)}`);
  if (!response.ok) {
    throw new Error(`GET /api/templates/${filename} failed: ${response.status}`);
  }
  return (await response.json()) as TemplateDetail;
}

export interface FillResponse {
  filename: string;
  markdown: string;
  missing: string[];
  extras: string[];
  fields: string[];
}

export async function fillDocument(
  filename: string,
  fields: Record<string, string>,
): Promise<FillResponse> {
  const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ fields }),
  });
  if (!response.ok) {
    throw new Error(`POST /api/documents/${filename} failed: ${response.status}`);
  }
  return (await response.json()) as FillResponse;
}
