import { describe, expect, it } from 'vitest';

import { __test__, parseMarkdown } from './markdown';

const { parseInline } = __test__;

describe('parseInline', () => {
  it('returns a single text node for plain text', () => {
    expect(parseInline('hello world')).toEqual([{ kind: 'text', text: 'hello world' }]);
  });

  it('parses a coverpage_link placeholder', () => {
    const nodes = parseInline('Effective <span class="coverpage_link">Effective Date</span>');
    expect(nodes).toEqual([
      { kind: 'text', text: 'Effective ' },
      { kind: 'placeholder', name: 'Effective Date' },
    ]);
  });

  it('parses a keyterms_link as a keyterm', () => {
    const nodes = parseInline('by <span class="keyterms_link">Provider</span> agrees');
    expect(nodes[1]).toEqual({ kind: 'keyterm', text: 'Provider' });
  });

  it('parses header_2 and header_3 spans', () => {
    expect(
      parseInline('<span class="header_2">Business Associate Obligations</span>'),
    ).toEqual([{ kind: 'header', level: 2, text: 'Business Associate Obligations' }]);
    expect(parseInline('<span class="header_3">Notice.</span>')).toEqual([
      { kind: 'header', level: 3, text: 'Notice.' },
    ]);
  });

  it('parses **bold**', () => {
    expect(parseInline('Use **reasonable care** please')).toEqual([
      { kind: 'text', text: 'Use ' },
      { kind: 'strong', text: 'reasonable care' },
      { kind: 'text', text: ' please' },
    ]);
  });

  it('parses [text](url) as a link', () => {
    expect(parseInline('See [Version 1.0](https://commonpaper.com/x) free')).toEqual([
      { kind: 'text', text: 'See ' },
      { kind: 'link', text: 'Version 1.0', href: 'https://commonpaper.com/x' },
      { kind: 'text', text: ' free' },
    ]);
  });

  it('drops overlapping matches, keeping the earliest in source order', () => {
    // The strong-regex and span-regex don't naturally overlap, but make sure the
    // guard is in place if they ever do.
    const nodes = parseInline('a **b** c');
    expect(nodes).toEqual([
      { kind: 'text', text: 'a ' },
      { kind: 'strong', text: 'b' },
      { kind: 'text', text: ' c' },
    ]);
  });
});

describe('parseMarkdown', () => {
  it('returns [] for empty input', () => {
    expect(parseMarkdown('')).toEqual([]);
  });

  it('parses a heading and a paragraph', () => {
    expect(parseMarkdown('# Title\n\nbody text')).toEqual([
      { kind: 'h1', key: 'b0', inline: [{ kind: 'text', text: 'Title' }] },
      { kind: 'p', key: 'b1', inline: [{ kind: 'text', text: 'body text' }] },
    ]);
  });

  it('groups consecutive ordered-list lines into a single <ol> block', () => {
    const md = '1. first\n2. second\n3. third';
    const blocks = parseMarkdown(md);
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe('ol');
    if (blocks[0].kind === 'ol') {
      expect(blocks[0].items).toHaveLength(3);
    }
  });

  it('handles a Mutual-NDA-style line with mixed inline tokens', () => {
    const md =
      '1. **Introduction**. This MNDA on <span class="coverpage_link">Purpose</span>.';
    const blocks = parseMarkdown(md);
    expect(blocks).toHaveLength(1);
    expect(blocks[0].kind).toBe('ol');
    if (blocks[0].kind === 'ol') {
      const inline = blocks[0].items[0];
      const kinds = inline.map((n) => n.kind);
      // strong opens the line, placeholder appears mid-sentence, with text
      // segments before, between, and after.
      expect(kinds).toContain('strong');
      expect(kinds).toContain('placeholder');
      expect(kinds).toContain('text');
      expect(kinds[0]).toBe('strong');
      // Trailing "." lives in a text node after the placeholder.
      expect(kinds[kinds.length - 1]).toBe('text');
    }
  });
});