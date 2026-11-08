import React from 'react';
import { CATEGORIES } from '../data/patternsData';
import { 
  GitBranch, 
  Brain, 
  Wrench, 
  Users, 
  Sparkles, 
  CheckCircle2, 
  CircleDashed 
} from 'lucide-react';

const categoryIcons = {
  Workflows: GitBranch,
  Reasoning: Brain,
  Capabilities: Wrench,
  'Multi-Agent': Users,
};

export default function Sidebar({ patterns, selectedPatternId, onSelectPattern }) {
  return (
    <aside className="w-80 bg-slate-900/90 border-r border-slate-800 flex flex-col h-screen select-none shrink-0 backdrop-blur-md">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-500 text-white shadow-lg shadow-indigo-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-wide text-white uppercase">Agent Patterns</h1>
            <p className="text-xs text-slate-400">20 Design Patterns Lab</p>
          </div>
        </div>
        <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
          20/20
        </span>
      </div>

      {/* Pattern Navigation List */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-5">
        {CATEGORIES.map((category) => {
          const Icon = categoryIcons[category] || Sparkles;
          const categoryPatterns = patterns.filter((p) => p.category === category);

          return (
            <div key={category} className="space-y-1.5">
              <div className="flex items-center space-x-2 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                <Icon className="w-3.5 h-3.5 text-cyan-400" />
                <span>{category}</span>
                <span className="text-slate-600">({categoryPatterns.length})</span>
              </div>

              <div className="space-y-1">
                {categoryPatterns.map((pat) => {
                  const isSelected = pat.id === selectedPatternId;
                  const isImplemented = !!pat.endpoint;

                  return (
                    <button
                      key={pat.id}
                      onClick={() => onSelectPattern(pat.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center justify-between group ${
                        isSelected
                          ? 'bg-gradient-to-r from-cyan-500/20 to-indigo-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm'
                          : 'text-slate-300 hover:bg-slate-800/60 hover:text-white border border-transparent'
                      }`}
                    >
                      <div className="flex items-center space-x-2.5 truncate">
                        <span className={`font-mono text-[11px] px-1.5 py-0.5 rounded ${
                          isSelected ? 'bg-cyan-500/30 text-cyan-200' : 'bg-slate-800 text-slate-400 group-hover:text-slate-300'
                        }`}>
                          {pat.num}
                        </span>
                        <span className="truncate">{pat.name}</span>
                      </div>

                      <div className="flex items-center space-x-1.5 shrink-0 pl-2">
                        {isImplemented ? (
                          <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                            <CheckCircle2 className="w-3 h-3" />
                            Ready
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] text-slate-500 font-mono">
                            <CircleDashed className="w-3 h-3" />
                            Next
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950/40 text-[11px] text-slate-400 flex items-center justify-between font-mono">
        <span>FastAPI + React</span>
        <span className="text-emerald-400 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Backend Live
        </span>
      </div>
    </aside>
  );
}

