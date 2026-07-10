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
