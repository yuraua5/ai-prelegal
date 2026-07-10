import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

import App from './App';
import * as apiModule from './lib/api';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('App', () => {
  it('renders the Prelegal heading', async () => {
    vi.spyOn(apiModule, 'fetchTemplates').mockResolvedValue([]);
    render(<App />);
    expect(screen.getByRole('heading', { name: /prelegal/i })).toBeInTheDocument();
    // Let the provider's initial fetch resolve so no pending state update leaks.
    await waitFor(() => {
      expect(apiModule.fetchTemplates).toHaveBeenCalled();
    });
  });

  it('renders both Form and Preview panes', async () => {
    vi.spyOn(apiModule, 'fetchTemplates').mockResolvedValue([]);
    render(<App />);
    expect(screen.getByRole('region', { name: /document fields/i })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /document preview/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(apiModule.fetchTemplates).toHaveBeenCalled();
    });
  });
});
