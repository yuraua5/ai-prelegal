/**
 * Triggers a PDF download by POSTing the current field values to
 * /api/documents/{filename}/pdf, wrapping the response Blob in a
 * synthetic anchor click, and revoking the object URL once the
 * browser has had a moment to start the download.
 *
 * Disabled when:
 *   - no template is selected
 *   - there are missing fields (we'd be downloading an unfinished document)
 *   - a download is already in flight
 */

import { useState } from 'react';

import { downloadPdfDocument } from '../lib/api';

interface Props {
  filename: string | null;
  fieldValues: Record<string, string>;
  missing: string[];
}

export function PdfDownloadButton({ filename, fieldValues, missing }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const disabled = !filename || missing.length > 0 || busy;

  async function handleClick() {
    if (!filename || disabled) return;
    setBusy(true);
    setError(null);
    try {
      const { blob, downloadName } = await downloadPdfDocument(filename, fieldValues);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = downloadName;
      a.rel = 'noopener';
      // Some browsers require the anchor to be in the DOM.
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Defer revoke so the browser has time to fetch the blob.
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PDF download failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pdf-download">
      <button
        type="button"
        className="pdf-download__button"
        onClick={() => void handleClick()}
        disabled={disabled}
        data-testid="pdf-download-button"
      >
        {busy ? 'Preparing PDF…' : 'Download PDF'}
      </button>
      {missing.length > 0 && filename && (
        <p className="pdf-download__hint">
          Fill {missing.length} more field{missing.length === 1 ? '' : 's'} to enable download.
        </p>
      )}
      {error && (
        <p className="pdf-download__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
