import { FormPane } from './components/FormPane';
import { PreviewPane } from './components/PreviewPane';
import { TemplatePicker } from './components/TemplatePicker';
import { AppProvider } from './state/AppContext';

function App() {
  return (
    <AppProvider>
      <div className="app">
        <header className="app__header">
          <h1>Prelegal</h1>
          <p className="app__tagline">Draft legal agreements from CommonPaper templates.</p>
          <TemplatePicker />
        </header>
        <main className="app__main">
          <FormPane />
          <PreviewPane />
        </main>
      </div>
    </AppProvider>
  );
}

export default App;
