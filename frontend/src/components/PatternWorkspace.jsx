import React from 'react';
import { 
  Play, 
  Square, 
  Terminal, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Layers, 
  Cpu, 
  ArrowRight,
  Info
} from 'lucide-react';

export default function PatternWorkspace({
  pattern,
  isRunning,
  events,
  inputText,
  setInputText,
  targetFormat,
  setTargetFormat,
  provider,
  setProvider,
  temperature,
  setTemperature,
  onRun,
  onStop,
  onReset
}) {
  const isImplemented = !!pattern.endpoint;

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-slate-950">
      {/* Top Header Bar */}
      <header className="px-6 py-4 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <span className="font-mono text-sm px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 font-bold">
            Pattern {pattern.num}
          </span>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-lg font-bold text-white tracking-tight">{pattern.name}</h2>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono border border-slate-700">
                {pattern.framework}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{pattern.tagline}</p>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 bg-slate-800/80 px-2.5 py-1.5 rounded-lg border border-slate-700 text-xs">
            <span className="text-slate-400">Provider:</span>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              disabled={isRunning}
              className="bg-transparent text-white font-medium focus:outline-none cursor-pointer"
            >
              <option value="gemini" className="bg-slate-900">Google Gemini</option>
              <option value="openai" className="bg-slate-900">OpenAI</option>
              <option value="anthropic" className="bg-slate-900">Anthropic Claude</option>
              <option value="ollama" className="bg-slate-900">Local Ollama</option>
            </select>
          </div>

          {isImplemented && (
            <button
              onClick={isRunning ? onStop : onRun}
              className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 transition-all shadow-md ${
                isRunning
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 hover:bg-rose-500/30'
                  : 'bg-gradient-to-r from-cyan-500 to-indigo-600 text-white hover:from-cyan-400 hover:to-indigo-500 shadow-cyan-500/20'
              }`}
            >
              {isRunning ? (
                <>
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Stop Pipeline</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Execute Pattern</span>
                </>
              )}
            </button>
          )}
        </div>
      </header>

      {/* Main Workspace Body: Split Left (Input/Docs) & Right (Trace/Output) */}
      <div className="flex-1 grid grid-cols-12 overflow-hidden">
        {/* Left Column: Input Controls & Pattern Deep-Dive */}
        <div className="col-span-5 border-r border-slate-800/80 p-5 overflow-y-auto space-y-5 bg-slate-900/30">
          {/* Pattern Architecture Flow Card */}
          <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3">
            <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300 uppercase tracking-wider">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span>Architecture Flow</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800/80 font-mono text-xs text-cyan-300 flex items-center justify-center text-center shadow-inner">
              {pattern.flowDiagram}
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              {pattern.description}
            </p>
          </div>

          {/* Input Configuration */}
          {isImplemented ? (
            <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                  Input Payload
                </label>
                <button
                  onClick={() => setInputText(pattern.sampleInput || '')}
                  disabled={isRunning}
                  className="text-[11px] text-cyan-400 hover:text-cyan-300 underline font-mono"
                >
                  Load Sample
                </button>
              </div>

              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                disabled={isRunning}
                rows={5}
                className="w-full bg-slate-950 text-slate-200 text-xs rounded-lg p-3 border border-slate-800 focus:border-cyan-500 focus:outline-none font-mono resize-none leading-relaxed"
                placeholder="Enter text to process..."
              />

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-[11px] font-medium text-slate-400 block mb-1">Target Format</label>
                  <select
                    value={targetFormat}
                    onChange={(e) => setTargetFormat(e.target.value)}
                    disabled={isRunning}
                    className="w-full bg-slate-950 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 border border-slate-800 focus:border-cyan-500 focus:outline-none"
                  >
                    <option value="Executive Brief">Executive Brief</option>
                    <option value="Action Items List">Action Items List</option>
                    <option value="Risk Assessment">Risk Assessment</option>
                    <option value="JSON Specification">JSON Specification</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-medium text-slate-400 block mb-1">
                    Temperature: <span className="font-mono text-cyan-400">{temperature}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    disabled={isRunning}
                    className="w-full accent-cyan-500 cursor-pointer mt-1"
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 text-center space-y-2">
              <Info className="w-8 h-8 text-cyan-400 mx-auto opacity-70" />
              <h4 className="text-sm font-semibold text-white">Pattern in Roadmap</h4>
              <p className="text-xs text-slate-400">
                Pattern {pattern.num} will be plugged into this interactive testbed in sequential order.
              </p>
            </div>
          )}

          {/* Trade-offs & Analysis */}
          <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3 text-xs">
            <h4 className="font-semibold text-slate-300 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-amber-400" />
              Trade-offs & Implementation Notes
            </h4>
            <div className="space-y-2">
              <div>
                <span className="font-medium text-emerald-400 block mb-1">Pros:</span>
                <ul className="list-disc list-inside space-y-0.5 text-slate-300 pl-1">
                  {pattern.pros?.map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              </div>
              <div className="pt-1">
                <span className="font-medium text-rose-400 block mb-1">Cons / Gotchas:</span>
                <ul className="list-disc list-inside space-y-0.5 text-slate-400 pl-1">
                  {pattern.cons?.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Live Event Trace & Execution Stream */}
        <div className="col-span-7 flex flex-col h-full bg-slate-950 overflow-hidden">
          {/* Stream Header */}
          <div className="px-5 py-3 border-b border-slate-800/80 flex items-center justify-between shrink-0 bg-slate-900/40">
            <div className="flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
                Execution Stream (SSE)
              </span>
              {isRunning && (
                <span className="flex items-center gap-1 text-[10px] text-cyan-400 font-mono bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
                  Active Step
                </span>
              )}
            </div>
            {events.length > 0 && (
              <button
                onClick={onReset}
                disabled={isRunning}
                className="text-[11px] text-slate-400 hover:text-slate-200 font-mono"
              >
                Clear Log
              </button>
            )}
          </div>

          {/* Trace Event Log List */}
          <div className="flex-1 overflow-y-auto p-5 space-y-3 font-sans">
            {events.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-600 text-xs space-y-2">
                <Terminal className="w-8 h-8 opacity-40" />
                <p>Click "Execute Pattern" to watch the step-by-step agent trace.</p>
              </div>
            ) : (
              events.map((evt, idx) => {
                const isGatePassed = evt.step === 'gate_passed';
                const isGateFailed = evt.step === 'gate_failed';
                const isError = evt.step === 'error' || evt.status === 'failed';
                const isComplete = evt.step === 'completed';

                return (
                  <div
                    key={idx}
                    className={`p-3.5 rounded-xl border transition-all ${
                      isGatePassed
                        ? 'bg-emerald-950/20 border-emerald-500/30'
                        : isGateFailed
                        ? 'bg-rose-950/20 border-rose-500/30'
                        : isError
                        ? 'bg-rose-950/30 border-rose-500/40 text-rose-200'
                        : isComplete
                        ? 'bg-cyan-950/20 border-cyan-500/40 shadow-lg shadow-cyan-950/50'
                        : 'bg-slate-900/60 border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2">
                        {isGatePassed ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : isGateFailed || isError ? (
                          <XCircle className="w-4 h-4 text-rose-400" />
                        ) : (
                          <div className="w-2 h-2 rounded-full bg-cyan-400" />
                        )}
                        <span className="font-semibold text-xs text-white">
                          {evt.node}
                        </span>
                        <span className="font-mono text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-800/80">
                          {evt.step}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">
                        #{idx + 1}
                      </span>
                    </div>

                    <div className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed font-sans pl-4 border-l border-slate-800">
                      {evt.content}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

