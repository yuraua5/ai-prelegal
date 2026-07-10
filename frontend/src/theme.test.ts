import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const here = path.dirname(fileURLToPath(import.meta.url));
const cssPath = path.join(here, 'index.css');
const css = fs.readFileSync(cssPath, 'utf-8');

describe('Brand theme', () => {
  it.each([
    ['--color-accent-yellow', '#ecad0a'],
    ['--color-blue-primary', '#209dd7'],
    ['--color-purple-secondary', '#753991'],
    ['--color-dark-navy', '#032147'],
    ['--color-gray-text', '#888888'],
  ])('declares %s as %s', (name, value) => {
    const re = new RegExp(`${name}\\s*:\\s*${value}\\s*;`);
    expect(css).toMatch(re);
  });

  it('uses --color-dark-navy as the page text colour', () => {
    // The :root colour cascades to all text via `color: var(--color-dark-navy)`.
    expect(css).toContain('color: var(--color-dark-navy)');
  });
});
