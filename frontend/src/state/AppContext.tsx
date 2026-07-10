/**
 * Top-level app state: list of templates, currently selected filename, and
 * the detail (body + fields) for the selected template.
 *
 * Intentionally tiny — Redux/zustand would be overkill for one dropdown and
 * one form. Step-09 will add `fieldValues` here without restructuring.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { fetchTemplateDetail, fetchTemplates } from '../lib/api';
import type { TemplateDetail, TemplateSummary } from '../lib/api';

export type Status = 'idle' | 'loading' | 'ready' | 'error';

export interface AppState {
  status: Status;
  error: string | null;
  templates: TemplateSummary[];
  selectedFilename: string | null;
  selectedDetail: TemplateDetail | null;
  detailStatus: Status;
  detailError: string | null;
}

export interface AppActions {
  selectTemplate(filename: string): void;
  refreshTemplates(): Promise<void>;
}

const AppStateCtx = createContext<AppState | null>(null);
const AppActionsCtx = createContext<AppActions | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [selectedFilename, setSelectedFilename] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<TemplateDetail | null>(null);
  const [detailStatus, setDetailStatus] = useState<Status>('idle');
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadTemplates = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const list = await fetchTemplates();
      setTemplates(list);
      setStatus('ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'unknown error');
      setStatus('error');
    }
  }, []);

  // Load on mount exactly once.
  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  // Fetch detail whenever the selection changes.
  useEffect(() => {
    if (!selectedFilename) {
      setSelectedDetail(null);
      setDetailStatus('idle');
      return;
    }
    let cancelled = false;
    setDetailStatus('loading');
    setDetailError(null);
    fetchTemplateDetail(selectedFilename)
      .then((detail) => {
        if (cancelled) return;
        setSelectedDetail(detail);
        setDetailStatus('ready');
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setDetailError(err instanceof Error ? err.message : 'unknown error');
        setDetailStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [selectedFilename]);

  const selectTemplate = useCallback((filename: string) => {
    setSelectedFilename(filename || null);
  }, []);

  const state = useMemo<AppState>(
    () => ({
      status,
      error,
      templates,
      selectedFilename,
      selectedDetail,
      detailStatus,
      detailError,
    }),
    [status, error, templates, selectedFilename, selectedDetail, detailStatus, detailError],
  );
  const actions = useMemo<AppActions>(
    () => ({ selectTemplate, refreshTemplates: loadTemplates }),
    [selectTemplate, loadTemplates],
  );

  return (
    <AppStateCtx.Provider value={state}>
      <AppActionsCtx.Provider value={actions}>{children}</AppActionsCtx.Provider>
    </AppStateCtx.Provider>
  );
}

export function useAppState(): AppState {
  const ctx = useContext(AppStateCtx);
  if (ctx === null) {
    throw new Error('useAppState must be used inside <AppProvider>');
  }
  return ctx;
}

export function useAppActions(): AppActions {
  const ctx = useContext(AppActionsCtx);
  if (ctx === null) {
    throw new Error('useAppActions must be used inside <AppProvider>');
  }
  return ctx;
}
