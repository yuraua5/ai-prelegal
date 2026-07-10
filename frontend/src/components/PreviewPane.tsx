/**
 * Right pane: live preview of the rendered document. We re-use the backend
 * substitution via the AppContext — the markdown we render here already has
 * user values in place and `<span class="coverpage_link">…</span>` for any
 * missing field. We do NOT use dangerouslySetInnerHTML; instead we walk
 * the markdown line by line into safe React nodes.
 */

import { useMemo } from 'react';

import { useAppState } from '../state/AppContext';
import { PdfDownloadButton } from './PdfDownloadButton';

const SPAN_RE = /<span\s+class="coverpage_link"\s*>([^<]+)<\/span>/gi;

interface InlineSegment {
  kind: 'text' | 'placeholder';
  text: string;
}

function splitInline(line: string): InlineSegment[] {
  const out: InlineSegment[] = [];
  let last = 0;
  for (const match of line.matchAll(SPAN_RE)) {
    const start = match.index ?? 0;
    if (start > last) {
      out.push({ kind: 'text', text: line.slice(last, start) });
    }
    out.push({ kind: 'placeholder', text: match[1].trim() });
    last = start + match[0].length;
  }
  if (last < line.length) {
    out.push({ kind: 'text', text: line.slice(last) });
  }
  return out;
}

function renderInline(line: string, key: string): React.ReactNode {
  const segments = splitInline(line);
  return segments.map((seg, i) => {
    if (seg.kind === 'placeholder') {
      return (
        <span className="preview__placeholder" key={`${key}-p-${i}`}>
          [missing: {seg.text}]
        </span>
      );
    }
    return <span key={`${key}-t-${i}`}>{seg.text}</span>;
  });
}

function renderMarkdown(md: string): React.ReactNode {
  if (!md) return null;
  const lines = md.split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith('## ')) {
      blocks.push(<h2 key={`h2-${i}`}>{renderInline(line.slice(3), `${i}-h2`)}</h2>);
      i += 1;
    } else if (line.startsWith('# ')) {
      blocks.push(<h1 key={`h1-${i}`}>{renderInline(line.slice(2), `${i}-h1`)}</h1>);
      i += 1;
    } else if (/^\d+\.\s/.test(line)) {
      // ordered list — collect until blank line or non-list line
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s/, ''));
        i += 1;
      }
      blocks.push(
        <ol key={`ol-${i}`}>
          {items.map((it, j) => (
            <li key={`ol-${i}-${j}`}>{renderInline(it, `${i}-ol-${j}`)}</li>
          ))}
        </ol>,
      );
    } else if (line.trim() === '') {
      i += 1;
    } else {
      // paragraph — group contiguous non-blank, non-heading, non-list lines
      const para: string[] = [];
      while (
        i < lines.length &&
        lines[i].trim() !== '' &&
        !lines[i].startsWith('# ') &&
        !lines[i].startsWith('## ') &&
        !/^\d+\.\s/.test(lines[i])
      ) {
        para.push(lines[i]);
        i += 1;
      }
      blocks.push(<p key={`p-${i}`}>{renderInline(para.join(' '), `${i}-p`)}</p>);
    }
  }
  return blocks;
}

export function PreviewPane() {
  const { selectedDetail, previewMarkdown, previewStatus, previewError, fieldValues } =
    useAppState();

  const rendered = useMemo(() => renderMarkdown(previewMarkdown), [previewMarkdown]);

  // Recompute missing-fields from the live preview so the download button
  // stays in sync without an extra round-trip to /api/documents.
  const missing = useMemo<string[]>(() => {
    if (!previewMarkdown) return [];
    const seen = new Set<string>();
    const out: string[] = [];
    const re = /<span\s+class="coverpage_link"\s*>([^<]+)<\/span>/gi;
    let m: RegExpExecArray | null;
    while ((m = re.exec(previewMarkdown)) !== null) {
      const name = m[1].trim();
      if (!seen.has(name)) {
        seen.add(name);
        out.push(name);
      }
    }
    return out;
  }, [previewMarkdown]);

  if (!selectedDetail) {
    return (
      <section className="pane pane--preview" aria-label="Document preview">
        <h2 className="pane__title">Preview</h2>
        <p className="pane__placeholder">Select a template to see a preview.</p>
      </section>
    );
  }

  return (
    <section className="pane pane--preview" aria-label="Document preview">
      <div className="preview__header">
        <h2 className="pane__title">Preview</h2>
        <PdfDownloadButton
          filename={selectedDetail.filename}
          fieldValues={fieldValues}
          missing={missing}
        />
      </div>
      {previewStatus === 'loading' && (
        <p className="pane__placeholder" aria-live="polite">
          Updating…
        </p>
      )}
      {previewStatus === 'error' && (
        <p className="pane__placeholder" role="status">
          Preview unavailable ({previewError}); showing local fallback.
        </p>
      )}
      <article className="preview" data-testid="preview">
        {rendered}
      </article>
    </section>
  );
}
