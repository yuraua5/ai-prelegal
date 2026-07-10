/**
 * Dropdown over the catalog. Owned by App so it sits above the two panes.
 * Renders three states:
 *   - loading (initial fetch)
 *   - error (initial fetch failed; offers retry)
 *   - ready with N templates
 * Selecting an option sets the chosen filename in app state.
 */

import { useAppActions, useAppState } from '../state/AppContext';

export function TemplatePicker() {
  const { status, error, templates, selectedFilename } = useAppState();
  const { selectTemplate, refreshTemplates } = useAppActions();

  return (
    <div className="picker" data-testid="template-picker">
      <label htmlFor="template-select">Template</label>
      {status === 'loading' && <p className="pane__placeholder">Loading templates…</p>}
      {status === 'error' && (
        <div role="alert">
          <p className="pane__placeholder">Failed to load templates: {error}</p>
          <button type="button" onClick={() => void refreshTemplates()}>
            Retry
          </button>
        </div>
      )}
      {status === 'ready' && (
        <select
          id="template-select"
          value={selectedFilename ?? ''}
          onChange={(e) => selectTemplate(e.target.value)}
          aria-label="Select a template"
        >
          <option value="">— pick a template —</option>
          {templates.map((t) => (
            <option key={t.filename} value={t.filename} title={t.description}>
              {t.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
