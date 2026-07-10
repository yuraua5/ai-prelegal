/**
 * Right pane: live preview of the rendered document. We re-use the backend
 * substitution via the AppContext — the markdown we render here already has
 * user values in place and `<span class="coverpage_link">…</span>` for any
 * missing field.
 *
 * Markdown → React rendering lives in `lib/markdown.ts` so it can be
 * unit-tested in isolation. We never inject raw HTML.
 */

import { Fragment, useMemo } from 'react';
import type { ReactNode } from 'react';

import { useAppState } from '../state/AppContext';
import { parseMarkdown } from '../lib/markdown';
import type { InlineNode, MarkdownBlock } from '../lib/markdown';
import { PdfDownloadButton } from './PdfDownloadButton';

function renderInline(nodes: InlineNode[], keyPrefix: string): ReactNode {
  return nodes.map((node, i) => {
    const key = `${keyPrefix}-${i}`;
    switch (node.kind) {
      case 'text':
        // Strip any leftover unknown <span>…</span> so they don't leak through
        // as raw markup (defensive: backend shouldn't send them, but BAA/DPA
        // include other span classes that the renderer does not handle).
        return <Fragment key={key}>{node.text.replace(/<\/?[^>]+>/g, '')}</Fragment>;
      case 'placeholder':
        return (
          <span className="preview__placeholder" key={key}>
            [missing: {node.name}]
          </span>
        );
      case 'keyterm':
        return (
          <strong className="preview__keyterm" key={key}>
            {node.text}
          </strong>
        );
      case 'header': {
        const cls = node.level === 2 ? 'preview__header-2' : 'preview__header-3';
        return (
          <strong className={cls} key={key}>
            {node.text}
          </strong>
        );
      }
      case 'strong':
        return <strong key={key}>{node.text}</strong>;
      case 'link':
        return (
          <a key={key} href={node.href} target="_blank" rel="noopener noreferrer">
            {node.text}
          </a>
        );
    }
  });
}

function renderBlock(block: MarkdownBlock): ReactNode {
  switch (block.kind) {
    case 'h1':
      return <h1 key={block.key}>{renderInline(block.inline, `${block.key}-h1`)}</h1>;
    case 'h2':
      return <h2 key={block.key}>{renderInline(block.inline, `${block.key}-h2`)}</h2>;
    case 'ol':
      return (
        <ol key={block.key}>
          {block.items.map((it, j) => (
            <li key={`${block.key}-${j}`}>{renderInline(it, `${block.key}-ol-${j}`)}</li>
          ))}
        </ol>
      );
    case 'p':
      return <p key={block.key}>{renderInline(block.inline, `${block.key}-p`)}</p>;
  }
}

export function PreviewPane() {
  const { selectedDetail, previewMarkdown, previewStatus, previewError, fieldValues } =
    useAppState();

  const rendered = useMemo(
    () => parseMarkdown(previewMarkdown).map(renderBlock),
    [previewMarkdown],
  );

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
