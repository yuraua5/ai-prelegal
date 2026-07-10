/**
 * TemplatePicker integration tests. We don't use MSW (extra dep); we mock
 * the `../lib/api` module directly via vi.mock. That's enough for these three
 * states and keeps the test self-contained.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import * as apiModule from '../lib/api';
import type { TemplateDetail, TemplateSummary } from '../lib/api';
import { AppProvider } from '../state/AppContext';
import { TemplatePicker } from './TemplatePicker';

const SAMPLE: TemplateSummary[] = [
  { name: 'Mutual NDA', description: 'Confidentiality', filename: 'Mutual-NDA.md' },
  { name: 'BAA', description: 'HIPAA', filename: 'BAA.md' },
];

const SAMPLE_DETAIL: TemplateDetail = {
  ...SAMPLE[0],
  body: '# Mutual NDA\nhello',
  fields: ['Purpose'],
};

afterEach(() => {
  vi.restoreAllMocks();
  vi.unmock('../lib/api');
});

function renderPicker() {
  return render(
    <AppProvider>
      <TemplatePicker />
    </AppProvider>,
  );
}

describe('TemplatePicker', () => {
  it('shows a loading state initially', () => {
    vi.spyOn(apiModule, 'fetchTemplates').mockReturnValue(new Promise(() => {}));
    renderPicker();
    expect(screen.getByText(/loading templates/i)).toBeInTheDocument();
  });

  it('renders an error state with retry button on fetch failure', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiModule, 'fetchTemplates').mockRejectedValueOnce(new Error('boom'));
    renderPicker();

    expect(await screen.findByText(/failed to load templates/i)).toBeInTheDocument();
    const retry = screen.getByRole('button', { name: /retry/i });
    await user.click(retry); // exercise the retry handler — must not throw
  });

  it('populates the dropdown once templates load and selecting one updates state', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiModule, 'fetchTemplates').mockResolvedValue(SAMPLE);
    const fetchDetail = vi.spyOn(apiModule, 'fetchTemplateDetail').mockResolvedValue(SAMPLE_DETAIL);

    renderPicker();

    const select = await screen.findByLabelText(/select a template/i);
    expect(select).toBeInTheDocument();

    await waitFor(() => {
      expect(select.querySelectorAll('option')).toHaveLength(SAMPLE.length + 1);
    });

    await user.selectOptions(select, 'Mutual-NDA.md');
    expect(fetchDetail).toHaveBeenCalledWith('Mutual-NDA.md');
  });

  it('forwards template descriptions as option titles', async () => {
    vi.spyOn(apiModule, 'fetchTemplates').mockResolvedValue(SAMPLE);

    renderPicker();
    const select = await screen.findByLabelText(/select a template/i);
    await waitFor(() => expect(select.querySelectorAll('option')).toHaveLength(SAMPLE.length + 1));

    const mNda = select.querySelector('option[value="Mutual-NDA.md"]') as HTMLOptionElement | null;
    expect(mNda).not.toBeNull();
    expect(mNda).toHaveTextContent(/mutual nda/i);
    expect(mNda?.title).toBe('Confidentiality');
  });
});

describe('AppProvider + App shell integration', () => {
  beforeEach(() => {
    vi.spyOn(apiModule, 'fetchTemplates').mockResolvedValue(SAMPLE);
    vi.spyOn(apiModule, 'fetchTemplateDetail').mockResolvedValue(SAMPLE_DETAIL);
  });

  it('renders both panes while templates load', async () => {
    const { default: App } = await import('../App');
    render(<App />);
    expect(screen.getByRole('region', { name: /document fields/i })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /document preview/i })).toBeInTheDocument();

    // wait for fetchTemplates to resolve so we don't leak unresolved promises
    await waitFor(() => expect(screen.getByLabelText(/select a template/i)).toBeInTheDocument());
  });
});
