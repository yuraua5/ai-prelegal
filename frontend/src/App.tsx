import { FormPane } from './components/FormPane';
import { PreviewPane } from './components/PreviewPane';

function App() {
  return (
    <div className="app">
      <header className="app__header">
        <h1>Prelegal</h1>
        <p className="app__tagline">Draft legal agreements from CommonPaper templates.</p>
      </header>
      <main className="app__main">
        <FormPane />
        <PreviewPane />
      </main>
    </div>
  );
}

export default App;
