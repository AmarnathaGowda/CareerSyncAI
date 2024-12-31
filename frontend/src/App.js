import React, { useState } from 'react';
import { FileUpload } from './components/FileUpload';
import { ResultsView } from './components/ResultsView';
import { Navbar } from './components/Navbar';

export default function App() {
  const [results, setResults] = useState(null);
  
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="container mx-auto px-4 py-8">
        <FileUpload setResults={setResults} />
        {results && <ResultsView results={results} />}
      </main>
    </div>
  );
}