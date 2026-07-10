/** Right pane: live preview of the rendered document. Wired up in step-09. */

export function PreviewPane() {
  return (
    <section className="pane pane--preview" aria-label="Document preview">
      <h2 className="pane__title">Preview</h2>
      <p className="pane__placeholder">
        Live markdown preview appears here once a template is selected.
      </p>
    </section>
  );
}
