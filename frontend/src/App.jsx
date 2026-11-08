import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import PatternWorkspace from './components/PatternWorkspace';
import { PATTERNS } from './data/patternsData';

export default function App() {
  const [selectedPatternId, setSelectedPatternId] = useState('p01');
  const [provider, setProvider] = useState('gemini');
  const [temperature, setTemperature] = useState(0.2);
  const [targetFormat, setTargetFormat] = useState('Executive Brief');
  const [inputText, setInputText] = useState(PATTERNS[0].sampleInput || '');
  const [events, setEvents] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [abortController, setAbortController] = useState(null);

  const selectedPattern = PATTERNS.find((p) => p.id === selectedPatternId) || PATTERNS[0];

  const handleSelectPattern = (id) => {
    setSelectedPatternId(id);
    const pat = PATTERNS.find((p) => p.id === id);
    if (pat?.sampleInput) {
      setInputText(pat.sampleInput);
    }
    setEvents([]);
  };

  const handleRun = async () => {
    if (!selectedPattern.endpoint) return;

    setIsRunning(true);
    setEvents([]);

    const controller = new AbortController();
    setAbortController(controller);

    try {
      const response = await fetch(selectedPattern.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          input_text: inputText,
          target_format: targetFormat,
          provider: provider,
          temperature: temperature,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep partial line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.substring(6));
              setEvents((prev) => [...prev, eventData]);
            } catch (err) {
              console.warn('Failed to parse SSE payload:', line);
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setEvents((prev) => [
          ...prev,
          {
            step: 'error',
            node: 'Client Error',
            content: `Connection failed: ${err.message}`,
            status: 'failed',
          },
        ]);
      }
    } finally {
      setIsRunning(false);
      setAbortController(null);
    }
  };

  const handleStop = () => {
    if (abortController) {
      abortController.abort();
      setIsRunning(false);
      setEvents((prev) => [
        ...prev,
        {
          step: 'stopped',
          node: 'Pipeline Aborted',
          content: 'Execution manually cancelled by user.',
          status: 'failed',
        },
      ]);
    }
  };

  const handleReset = () => {
    setEvents([]);
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Sidebar
        patterns={PATTERNS}
        selectedPatternId={selectedPatternId}
        onSelectPattern={handleSelectPattern}
      />
      <PatternWorkspace
        pattern={selectedPattern}
        isRunning={isRunning}
        events={events}
        inputText={inputText}
        setInputText={setInputText}
        targetFormat={targetFormat}
        setTargetFormat={setTargetFormat}
        provider={provider}
        setProvider={setProvider}
        temperature={temperature}
        setTemperature={setTemperature}
        onRun={handleRun}
        onStop={handleStop}
        onReset={handleReset}
      />
    </div>
  );
}

