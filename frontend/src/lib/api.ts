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

/**
 * POST /api/documents/{filename}/pdf — returns the PDF as a Blob.
 * The Content-Disposition header from the backend sets a friendly download
 * name; we read it for the frontend-side filename too.
 */
export async function downloadPdfDocument(
  filename: string,
  fields: Record<string, string>,
): Promise<{ blob: Blob; downloadName: string }> {
  const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(filename)}/pdf`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ fields }),
  });
  if (!response.ok) {
    throw new Error(`POST /api/documents/${filename}/pdf failed: ${response.status}`);
  }
  const blob = await response.blob();
  // Parse filename from `attachment; filename="Mutual-NDA.pdf"` header.
  const cd = response.headers.get('content-disposition') ?? '';
  const match = cd.match(/filename="?([^";]+)"?/);
  const downloadName = match?.[1] ?? filename.replace(/\.md$/, '') + '.pdf';
  return { blob, downloadName };
}
