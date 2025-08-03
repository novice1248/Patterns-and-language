import React from 'react';
import axios from 'axios';
import './App.css';

// バックエンドからのレスポンスの型を定義
interface PatternResult {
  pattern: string;
  count: number;
  example: string;
}

interface AnalysisResponse {
  token_patterns: PatternResult[];
  generalized_patterns: PatternResult[];
}

function App() {
  const [urls, setUrls] = React.useState<string>('https://www3.nhk.or.jp/nhkworld/en/news/20250731_08/\nhttps://www3.nhk.or.jp/nhkworld/en/news/20250730_80/');
  const [results, setResults] = React.useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string>('');

  const handleAnalyze = async () => {
    // 改行で区切られたURLを配列に変換
    const urlList = urls.split('\n').filter(url => url.trim() !== '');
    if (urlList.length === 0) {
      setError('Please enter at least one URL to analyze.');
      return;
    }

    setLoading(true);
    setError('');
    setResults(null);

    try {
      // バックエンドのAPI (http://localhost:8000/analyze) を呼び出す
      const response = await axios.post<AnalysisResponse>('http://localhost:8000/analyze', {
        urls: urlList,
      });
      setResults(response.data);
    } catch (err) {
      console.error(err);
      setError('An error occurred during analysis. Please check the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>WebPagePatternAnalysisTool</h1>
        <div className="container">
          <p>Enter each URL you want to analyze on a new line.</p>
          <textarea
            value={urls}
            onChange={(e) => setUrls(e.target.value)}
            rows={5}
            placeholder="https://example.com/page1&#10;https://example.com/page2"
          />
          <button onClick={handleAnalyze} disabled={loading}>
            {loading ? 'Analysing...' : 'run analysis'}
          </button>
          
          {error && <p className="error">{error}</p>}

          {results && (
            <div className="results-container">
              <div className="result-column">
                <h2>Token Pattern TOP20</h2>
                <ul>
                  {results.token_patterns.map((item, index) => (
                    <li key={index}>
                      <strong>{item.pattern}</strong> (x{item.count})
                    </li>
                  ))}
                </ul>
              </div>
              <div className="result-column">
                <h2>PhasePattern TOP20</h2>
                <ul>
                  {results.generalized_patterns.map((item, index) => (
                    <li key={index}>
                      <strong>{item.pattern}</strong> (x{item.count})
                      <p className="example">ex: "{item.example}"</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </header>
    </div>
  );
}

export default App;