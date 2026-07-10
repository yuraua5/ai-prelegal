/**
 * Minimal, safe markdown → React-node renderer used by PreviewPane.
 *
 * We do NOT use dangerouslySetInnerHTML. Instead we walk the text line by line
 * and produce a tree of React elements. The output is intentionally a tree
 * (`MarkdownBlock[]`), not raw HTML, so it composes naturally with the rest
 * of the UI and stays XSS-safe even when user values flow back through.
 *
 * Supported CommonPaper-flavored markdown:
 *   - `# Heading` / `## Heading`              → <h1> / <h2>
 *   - `1. item` … (consecutive numbered lines) → <ol><li>…</li></ol>
 *   - `<span class="coverpage_link">Name</span>`   → placeholder chip
 *   - `<span class="keyterms_link">Term</span>`    → <strong class="keyterm">
 *   - `<span class="header_2|header_3">…</span>`   → <strong class="headerN">
 *   - `**bold**`                                 → <strong>
 *   - `[text](https://url)`                      → <a target="_blank">
 *   - Blank lines separate paragraphs
 */

export type MarkdownBlock =
  | { kind: 'h1'; key: string; inline: InlineNode[] }
  | { kind: 'h2'; key: string; inline: InlineNode[] }
  | { kind: 'ol'; key: string; items: InlineNode[][] }
  | { kind: 'p'; key: string; inline: InlineNode[] };

export type InlineNode =
  | { kind: 'text'; text: string }
  | { kind: 'placeholder'; name: string }
  | { kind: 'keyterm'; text: string }
  | { kind: 'header'; level: 2 | 3; text: string }
  | { kind: 'strong'; text: string }
  | { kind: 'link'; text: string; href: string };

const SPAN_RE = /<span\s+class="(coverpage_link|keyterms_link|header_2|header_3)"\s*>([^<]*)<\/span>/gi;
const STRONG_RE = /\*\*([^*]+)\*\*/g;
const LINK_RE = /\[([^\]]+)\]\(([^)\s]+)\)/g;

function parseInline(text: string): InlineNode[] {
  const out: InlineNode[] = [];

  // Tokenise by walking through all matches of any of our patterns, in source order.
  type Hit = { start: number; end: number; node: InlineNode };
  const hits: Hit[] = [];

  for (const m of text.matchAll(SPAN_RE)) {
    const start = m.index ?? 0;
    const cls = m[1].toLowerCase();
    const inner = m[2];
    hits.push({
      start,
      end: start + m[0].length,
      node:
        cls === 'coverpage_link'
          ? { kind: 'placeholder', name: inner.trim() }
          : cls === 'keyterms_link'
            ? { kind: 'keyterm', text: inner }
            : cls === 'header_2'
              ? { kind: 'header', level: 2, text: inner }
              : { kind: 'header', level: 3, text: inner },
    });
  }
  for (const m of text.matchAll(STRONG_RE)) {
    const start = m.index ?? 0;
    hits.push({ start, end: start + m[0].length, node: { kind: 'strong', text: m[1] } });
  }
  for (const m of text.matchAll(LINK_RE)) {
    const start = m.index ?? 0;
    hits.push({
      start,
      end: start + m[0].length,
      node: { kind: 'link', text: m[1], href: m[2] },
    });
  }

  hits.sort((a, b) => a.start - b.start);

  // Drop overlapping hits (keep the first one we encounter).
  const filtered: Hit[] = [];
  let cursor = 0;
  for (const h of hits) {
    if (h.start < cursor) continue;
    filtered.push(h);
    cursor = h.end;
  }

  let last = 0;
  for (const h of filtered) {
    if (h.start > last) {
      out.push({ kind: 'text', text: text.slice(last, h.start) });
    }
    out.push(h.node);
    last = h.end;
  }
  if (last < text.length) {
    out.push({ kind: 'text', text: text.slice(last) });
  }
  return out;
}

export function parseMarkdown(md: string): MarkdownBlock[] {
  if (!md) return [];
  const lines = md.split('\n');
  const blocks: MarkdownBlock[] = [];

  let i = 0;
  let keyCounter = 0;
  const nextKey = () => `b${keyCounter++}`;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith('## ')) {
      blocks.push({ kind: 'h2', key: nextKey(), inline: parseInline(line.slice(3)) });
      i += 1;
      continue;
    }
    if (line.startsWith('# ')) {
      blocks.push({ kind: 'h1', key: nextKey(), inline: parseInline(line.slice(2)) });
      i += 1;
      continue;
    }
    if (/^\d+\.\s/.test(line)) {
      const items: InlineNode[][] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(parseInline(lines[i].replace(/^\d+\.\s/, '')));
        i += 1;
      }
      blocks.push({ kind: 'ol', key: nextKey(), items });
      continue;
    }
    if (line.trim() === '') {
      i += 1;
      continue;
    }

    // Paragraph: contiguous non-blank, non-heading, non-list lines.
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
    blocks.push({ kind: 'p', key: nextKey(), inline: parseInline(para.join(' ')) });
  }

  return blocks;
}

// React import is local to the consumer; this file only exports data so the
// parser can be unit-tested without pulling in the DOM.
export const __test__ = { parseInline, SPAN_RE, STRONG_RE, LINK_RE };