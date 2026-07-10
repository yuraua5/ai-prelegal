/**
 * Tests for PdfDownloadButton + the preview header integration.
 * The browser-only bits (URL.createObjectURL, anchor click) are mocked.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import * as apiModule from '../lib/api';
import { PdfDownloadButton } from './PdfDownloadButton';

/** Capture every anchor element appended to the body during a click. */
function trackAnchors(): { get: () => HTMLAnchorElement[] } {
  const captured: HTMLAnchorElement[] = [];
  const origAppend = document.body.appendChild.bind(document.body);
  vi.spyOn(document.body, 'appendChild').mockImplementation((node: Node) => {
    if (node instanceof HTMLAnchorElement) {
      captured.push(node);
    }
    return origAppend(node);
  });
  return { get: () => captured };
}

beforeEach(() => {
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: (blob: Blob) => `blob:fake-${blob.size}-${Math.random()}`,
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: () => undefined,
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('PdfDownloadButton', () => {
  it('is disabled when no template is selected', () => {
    render(<PdfDownloadButton filename={null} fieldValues={{}} missing={[]} />);
    expect(screen.getByTestId('pdf-download-button')).toBeDisabled();
  });

  it('is disabled when there are missing fields', () => {
    render(
      <PdfDownloadButton
        filename="Mutual-NDA.md"
        fieldValues={{ 'Party A': 'Acme' }}
        missing={['Purpose']}
      />,
    );
    expect(screen.getByTestId('pdf-download-button')).toBeDisabled();
    expect(screen.getByText(/Fill 1 more field/i)).toBeInTheDocument();
  });

  it('is enabled when a template is selected and no fields are missing', () => {
    render(
      <PdfDownloadButton
        filename="Mutual-NDA.md"
        fieldValues={{ 'Party A': 'Acme' }}
        missing={[]}
      />,
    );
    expect(screen.getByTestId('pdf-download-button')).toBeEnabled();
  });

  it('POSTs to /api/documents/{filename}/pdf and creates a download link', async () => {
    const fetchSpy = vi.spyOn(apiModule, 'downloadPdfDocument').mockResolvedValue({
      blob: new Blob(['%PDF-fake'], { type: 'application/pdf' }),
      downloadName: 'Mutual-NDA.pdf',
    });
    const tracker = trackAnchors();

    render(
      <PdfDownloadButton
        filename="Mutual-NDA.md"
        fieldValues={{ 'Party A': 'Acme', Purpose: 'eval' }}
        missing={[]}
      />,
    );
    const button = screen.getByTestId('pdf-download-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('Mutual-NDA.md', {
        'Party A': 'Acme',
        Purpose: 'eval',
      });
    });

    await waitFor(() => {
      const anchors = tracker.get();
      expect(anchors.length).toBeGreaterThan(0);
    });
    const anchor = tracker.get().find((a) => a.download === 'Mutual-NDA.pdf');
    expect(anchor).toBeDefined();
    expect(anchor?.href).toContain('blob:fake-');
  });

  it('surfaces API errors as an inline message', async () => {
    vi.spyOn(apiModule, 'downloadPdfDocument').mockRejectedValue(new Error('boom'));

    render(<PdfDownloadButton filename="Mutual-NDA.md" fieldValues={{}} missing={[]} />);
    fireEvent.click(screen.getByTestId('pdf-download-button'));

    expect(await screen.findByText(/boom/)).toBeInTheDocument();
  });
});
