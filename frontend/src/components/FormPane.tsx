/** Left pane: form to fill template fields, one input per placeholder. */

import { useEffect, useMemo } from 'react';

import { useAppActions, useAppState } from '../state/AppContext';

export function FormPane() {
  const { selectedDetail, detailStatus, fieldValues, previewMarkdown } = useAppState();
  const { setFieldValue } = useAppActions();

  // Re-derive the missing list from the live preview every render.
  // The preview contains `<span class="coverpage_link">…</span>` for any
  // placeholder the user hasn't filled in yet.
  const missingNames = useMemo(() => {
    if (!previewMarkdown) return new Set<string>();
    const found = new Set<string>();
    const re = /<span\s+class="coverpage_link"\s*>([^<]+)<\/span>/gi;
    let m: RegExpExecArray | null;
    while ((m = re.exec(previewMarkdown)) !== null) {
      found.add(m[1].trim());
    }
    return found;
  }, [previewMarkdown]);

  // Keep fieldValues in sync with the loaded template (no stale keys after a
  // template switch).
  useEffect(() => {
    if (!selectedDetail) return;
  }, [selectedDetail]);

  if (!selectedDetail) {
    return (
      <section className="pane pane--form" aria-label="Document fields">
        <h2 className="pane__title">Fields</h2>
        <p className="pane__placeholder">
          {detailStatus === 'loading'
            ? 'Loading fields…'
            : detailStatus === 'error'
              ? 'Could not load fields.'
              : 'Pick a template above to start.'}
        </p>
      </section>
    );
  }

  return (
    <section className="pane pane--form" aria-label="Document fields">
      <h2 className="pane__title">Fields</h2>
      <form className="form" onSubmit={(e) => e.preventDefault()}>
        {selectedDetail.fields.map((name) => {
          const isMissing = missingNames.has(name);
          const id = `field-${name.replace(/\W+/g, '-').toLowerCase()}`;
          return (
            <div className="form__row" key={name}>
              <label htmlFor={id}>
                {name}
                {isMissing && <span className="form__missing"> (missing)</span>}
              </label>
              <input
                id={id}
                type="text"
                value={fieldValues[name] ?? ''}
                onChange={(e) => setFieldValue(name, e.target.value)}
                aria-invalid={isMissing}
                data-missing={isMissing ? 'true' : 'false'}
                data-field-name={name}
              />
            </div>
          );
        })}
      </form>
    </section>
  );
}
