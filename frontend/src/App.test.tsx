import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders the Prelegal heading', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /prelegal/i })).toBeInTheDocument();
  });

  it('renders both Form and Preview panes', () => {
    render(<App />);
    expect(screen.getByRole('region', { name: /document fields/i })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /document preview/i })).toBeInTheDocument();
  });
});
