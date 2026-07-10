/**
 * Top-level app state: list of templates, currently selected filename, the
 * detail (body + fields), the user's field values, and the live preview.
 *
 * Preview is debounced (300ms) to avoid hammering POST /api/documents on
 * every keystroke. fillDocument failures fall back to client-side
 * substitution so the preview never goes blank mid-typing.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';

import { fetchTemplateDetail, fetchTemplates, fillDocument } from '../lib/api';
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
  fieldValues: Record<string, string>;
  previewMarkdown: string;
  previewStatus: Status;
  previewError: string | null;
}

export interface AppActions {
  selectTemplate(filename: string): void;
  setFieldValue(name: string, value: string): void;
  refreshTemplates(): Promise<void>;
}

const AppStateCtx = createContext<AppState | null>(null);
const AppActionsCtx = createContext<AppActions | null>(null);

const PREVIEW_DEBOUNCE_MS = 300;

/** Client-side substitution that mirrors the backend fill engine (regex-based,
 * leaves unknown placeholders intact). Used as a fallback when the network is
 * unavailable or the backend is slow, so the preview stays responsive.
 */
function localSubstitute(body: string, values: Record<string, string>): string {
  return body.replace(
    /<span\s+class="coverpage_link"\s*>([^<]+)<\/span>/gi,
    (_match, name: string) => {
      const key = name.trim();
      const v = values[key];
      return v && v.length > 0 ? v : _match;
    },
  );
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [selectedFilename, setSelectedFilename] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<TemplateDetail | null>(null);
  const [detailStatus, setDetailStatus] = useState<Status>('idle');
  const [detailError, setDetailError] = useState<string | null>(null);

  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [previewMarkdown, setPreviewMarkdown] = useState<string>('');
  const [previewStatus, setPreviewStatus] = useState<Status>('idle');
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Cancel pending debounced fetches on unmount / template change.
  const previewSeq = useRef(0);

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

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  // Fetch detail whenever the selection changes; reset field state.
  useEffect(() => {
    if (!selectedFilename) {
      setSelectedDetail(null);
      setDetailStatus('idle');
      setFieldValues({});
      setPreviewMarkdown('');
      setPreviewStatus('idle');
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
        // Pre-seed values from the detail body so initial render shows spans
        // — the user has to type over them. Empty seed so preview is "empty".
        setFieldValues({});
        setPreviewMarkdown(detail.body);
        setPreviewStatus('ready');
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

  const setFieldValue = useCallback((name: string, value: string) => {
    setFieldValues((prev) => ({ ...prev, [name]: value }));
  }, []);

  // Debounced live preview. Hit /api/documents, fall back to local substitute.
  useEffect(() => {
    if (!selectedDetail) return;
    const seq = ++previewSeq.current;
    const handle = setTimeout(() => {
      setPreviewStatus('loading');
      fillDocument(selectedDetail.filename, fieldValues)
        .then((res) => {
          if (seq !== previewSeq.current) return;
          setPreviewMarkdown(res.markdown);
          setPreviewStatus('ready');
          setPreviewError(null);
        })
        .catch((err: unknown) => {
          if (seq !== previewSeq.current) return;
          // Fall back to local substitution so the preview still updates.
          setPreviewMarkdown(localSubstitute(selectedDetail.body, fieldValues));
          setPreviewStatus('error');
          setPreviewError(err instanceof Error ? err.message : 'preview unavailable');
        });
    }, PREVIEW_DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [fieldValues, selectedDetail]);

  const state = useMemo<AppState>(
    () => ({
      status,
      error,
      templates,
      selectedFilename,
      selectedDetail,
      detailStatus,
      detailError,
      fieldValues,
      previewMarkdown,
      previewStatus,
      previewError,
    }),
    [
      status,
      error,
      templates,
      selectedFilename,
      selectedDetail,
      detailStatus,
      detailError,
      fieldValues,
      previewMarkdown,
      previewStatus,
      previewError,
    ],
  );
  const actions = useMemo<AppActions>(
    () => ({ selectTemplate, setFieldValue, refreshTemplates: loadTemplates }),
    [selectTemplate, setFieldValue, loadTemplates],
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
