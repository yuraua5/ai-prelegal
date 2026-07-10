/**
 * FormPane + PreviewPane tests. We mock /api/templates and /api/documents
 * to exercise the dynamic form behaviour end-to-end via AppProvider.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useEffect } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { AppProvider, useAppActions } from '../state/AppContext';
import * as apiModule from '../lib/api';
import type { TemplateDetail, TemplateSummary } from '../lib/api';
import { FormPane } from './FormPane';
import { PreviewPane } from './PreviewPane';

const SAMPLE: TemplateSummary[] = [
  { name: 'Mutual NDA', description: 'Confidentiality', filename: 'Mutual-NDA.md' },
];

const SAMPLE_DETAIL: TemplateDetail = {
  name: 'Mutual NDA',
  description: 'Confidentiality',
  filename: 'Mutual-NDA.md',
  body: '# Mutual NDA\n\nFor <span class="coverpage_link">Party A</span>, purpose: <span class="coverpage_link">Purpose</span>.',
  fields: ['Party A', 'Purpose'],
};

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

beforeEach(() => {
  vi.spyOn(apiModule, 'fetchTemplates').mockResolvedValue(SAMPLE);
  vi.spyOn(apiModule, 'fetchTemplateDetail').mockResolvedValue(SAMPLE_DETAIL);
});

/** A tiny helper component that fires the action to select a template.
 *  This avoids spinning up TemplatePicker for each test.
 */
function SelectOnMount({ filename }: { filename: string }) {
  const { selectTemplate } = useAppActions();
  useEffect(() => {
    selectTemplate(filename);
  }, [selectTemplate, filename]);
  return null;
}

describe('FormPane', () => {
  it('shows a placeholder until a template is picked', () => {
    render(
      <AppProvider>
        <FormPane />
      </AppProvider>,
    );
    expect(screen.getByText(/pick a template above/i)).toBeInTheDocument();
  });

  it('renders one input per template field after selection', async () => {
    const { container } = render(
      <AppProvider>
        <SelectOnMount filename="Mutual-NDA.md" />
        <FormPane />
      </AppProvider>,
    );

    // The label text includes " (missing)" so we can't use getByLabelText
    // reliably — instead match the inputs via data-field-name.
    await waitFor(() => {
      const inputs = container.querySelectorAll<HTMLInputElement>('input[data-field-name]');
      expect(inputs).toHaveLength(2);
      const names = Array.from(inputs).map((el) => el.dataset.fieldName);
      expect(names).toEqual(['Party A', 'Purpose']);
    });
  });

  it('marks every input as missing before the user types anything', async () => {
    const { container } = render(
      <AppProvider>
        <SelectOnMount filename="Mutual-NDA.md" />
        <FormPane />
      </AppProvider>,
    );

    await waitFor(() => {
      const inputs = container.querySelectorAll<HTMLInputElement>('input[data-field-name]');
      expect(inputs).toHaveLength(2);
      for (const input of inputs) {
        expect(input.getAttribute('aria-invalid')).toBe('true');
      }
    });
  });

  it('typing into an input lifts its missing flag (mocked backend)', async () => {
    const user = userEvent.setup();
    const fill = vi.spyOn(apiModule, 'fillDocument').mockResolvedValue({
      filename: 'Mutual-NDA.md',
      markdown: '# Mutual NDA\n\nFor Acme, purpose: <span class="coverpage_link">Purpose</span>.',
      missing: ['Purpose'],
      extras: [],
      fields: ['Party A', 'Purpose'],
    });

    const { container } = render(
      <AppProvider>
        <SelectOnMount filename="Mutual-NDA.md" />
        <FormPane />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(
        container.querySelector<HTMLInputElement>('input[data-field-name="Party A"]'),
      ).not.toBeNull();
    });

    const partyA = container.querySelector<HTMLInputElement>(
      'input[data-field-name="Party A"]',
    ) as HTMLInputElement;
    await user.type(partyA, 'Acme');

    await waitFor(() => {
      expect(fill).toHaveBeenCalledWith(
        'Mutual-NDA.md',
        expect.objectContaining({ 'Party A': 'Acme' }),
      );
    });

    // The preview update is debounced 300ms; waitFor handles that.
    await waitFor(() => {
      const filled = container.querySelector<HTMLInputElement>('input[data-field-name="Party A"]');
      const stillMissing = container.querySelector<HTMLInputElement>(
        'input[data-field-name="Purpose"]',
      );
      expect(filled?.getAttribute('aria-invalid')).toBe('false');
      expect(stillMissing?.getAttribute('aria-invalid')).toBe('true');
    });
  });
});

describe('FormPane — Cover Page templates', () => {
  it('shows a "Cover Page workflow not supported" notice when fields is empty', async () => {
    vi.spyOn(apiModule, 'fetchTemplateDetail').mockResolvedValueOnce({
      name: 'BAA',
      description: 'HIPAA Business Associate Agreement',
      filename: 'BAA.md',
      body: '# BAA\n\nBody only document.',
      fields: [],
    });

    const { container } = render(
      <AppProvider>
        <SelectOnMount filename="BAA.md" />
        <FormPane />
      </AppProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('no-fields-notice')).toBeInTheDocument();
    });
    expect(screen.getByText(/cover page workflow/i)).toBeInTheDocument();
    // No inputs should be rendered.
    expect(container.querySelectorAll('input[data-field-name]')).toHaveLength(0);
  });
});

describe('PreviewPane', () => {
  it('renders selected template body and highlights missing placeholders', async () => {
    const user = userEvent.setup();
    // fillDocument returns a populated backend response for the "Acme" value
    // but leaves Purpose still showing as a missing placeholder.
    const fill = vi
      .spyOn(apiModule, 'fillDocument')
      .mockResolvedValueOnce({
        filename: 'Mutual-NDA.md',
        markdown: '# Mutual NDA\n\nFor Acme, purpose: <span class="coverpage_link">Purpose</span>.',
        missing: ['Purpose'],
        extras: [],
        fields: ['Party A', 'Purpose'],
      })
      // subsequent debounces (if any) — return the same.
      .mockResolvedValue({
        filename: 'Mutual-NDA.md',
        markdown: '# Mutual NDA\n\nFor Acme, purpose: <span class="coverpage_link">Purpose</span>.',
        missing: ['Purpose'],
        extras: [],
        fields: ['Party A', 'Purpose'],
      });

    const { container } = render(
      <AppProvider>
        <SelectOnMount filename="Mutual-NDA.md" />
        <FormPane />
        <PreviewPane />
      </AppProvider>,
    );

    // Wait for the input to appear, then type to trigger the debounced fill.
    await waitFor(() => {
      expect(
        container.querySelector<HTMLInputElement>('input[data-field-name="Party A"]'),
      ).not.toBeNull();
    });
    const partyA = container.querySelector<HTMLInputElement>(
      'input[data-field-name="Party A"]',
    ) as HTMLInputElement;
    await user.type(partyA, 'Acme');

    // Wait for fillDocument to be called and the preview to render the result.
    await waitFor(
      () => {
        expect(fill).toHaveBeenCalled();
      },
      { timeout: 1500 },
    );
    await waitFor(
      () => {
        expect(screen.getByTestId('preview')).toHaveTextContent(/acme/i);
      },
      { timeout: 1500 },
    );
    expect(screen.getByTestId('preview')).toHaveTextContent(/\[missing: Purpose\]/);
  });

  it('renders **bold**, [link](url), and <span class="keyterms_link"> in the preview', async () => {
    vi.spyOn(apiModule, 'fetchTemplateDetail').mockResolvedValueOnce({
      name: 'Mutual NDA',
      description: '',
      filename: 'Mutual-NDA.md',
      body: '1. **Introduction**. See [Version 1.0](https://commonpaper.com/x). The <span class="keyterms_link">Disclosing Party</span> agrees.',
      fields: [],
    });
    vi.spyOn(apiModule, 'fillDocument').mockResolvedValue({
      filename: 'Mutual-NDA.md',
      markdown:
        '1. **Introduction**. See [Version 1.0](https://commonpaper.com/x). The <span class="keyterms_link">Disclosing Party</span> agrees.',
      missing: [],
      extras: [],
      fields: [],
    });

    render(
      <AppProvider>
        <SelectOnMount filename="Mutual-NDA.md" />
        <PreviewPane />
      </AppProvider>,
    );

    const preview = await waitFor(() => screen.getByTestId('preview'));
    expect(preview.querySelector('strong')).not.toBeNull();
    expect(preview.querySelector('a')?.getAttribute('href')).toBe('https://commonpaper.com/x');
    expect(preview.querySelector('.preview__keyterm')).not.toBeNull();
  });
});
