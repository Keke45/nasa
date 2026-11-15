import React, { useState, useEffect } from 'react';

export default function App() {
  const [theme, setTheme] = useState('light');
  const [activeNav, setActiveNav] = useState('Dashboard');
  const [telemetry, setTelemetry] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('LIVE');
  const [loading, setLoading] = useState(true);

  // Toggle theme handler
  const toggleTheme = () => setTheme(prev => prev === 'light' ? 'dark' : 'light');

  // Fetch telemetry / health stream loop
  useEffect(() => {
    let isMounted = true;
    const fetchTelemetry = async () => {
      try {
        const res = await fetch('http://localhost:8080/api/telemetry'); // or your health/telemetry endpoint
        if (!res.ok) throw new Error('Failed to fetch telemetry');
        const data = await res.json();
        if (isMounted) {
          setTelemetry(data);
          setConnectionStatus('LIVE');
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          // Fallback mock data or error state so UI remains fully interactive
          setTelemetry({
            heart_rate: 72,
            blood_oxygen: 98,
            body_temp: 37.1,
            fatigue_level: 3
          });
          setConnectionStatus('LIVE - MOCK');
          setLoading(false);
        }
      }
    };
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2000);
    return () => { isMounted = false; clearInterval(interval); };
  }, []);

  // Dynamic theme styling classes
  const isDark = theme === 'dark';
  const bgClass = isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-100 text-slate-800';
  const sidebarClass = isDark ? 'bg-slate-900/80 border-slate-800' : 'bg-white/80 border-slate-200';
  const cardClass = isDark ? 'bg-slate-900/70 border-slate-800 shadow-xl' : 'bg-white/70 border-white shadow-lg';

  return (
    <div className={`min-h-screen flex font-sans transition-colors duration-300 ${bgClass} p-6 gap-6 backdrop-blur-md`}>
      
      {/* LEFT SIDEBAR NAVIGATION */}
      <aside className={`w-64 rounded-2xl border p-6 flex flex-col justify-between ${sidebarClass}`}>
        <div>
          <div className="flex items-center gap-3 mb-10">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white font-bold">A</div>
            <span className="font-bold tracking-wider text-lg">AstroHealth</span>
          </div>

          <nav className="space-y-2">
            {['Dashboard', 'Crew Roster', 'Telemetry', 'Analytics', 'Settings'].map((item) => (
              <button
                key={item}
                onClick={() => setActiveNav(item)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  activeNav === item 
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md shadow-cyan-500/20' 
                    : isDark ? 'text-slate-400 hover:bg-slate-800/50' : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                {item}
              </button>
            ))}
          </nav>
        </div>

        {/* Theme Toggle Button */}
        <button 
          onClick={toggleTheme}
          className={`w-full py-2.5 px-4 rounded-xl text-xs font-semibold border flex items-center justify-center gap-2 transition-all ${
            isDark ? 'border-slate-800 bg-slate-800/40 text-cyan-400' : 'border-slate-200 bg-slate-50 text-blue-600'
          }`}
        >
          {isDark ? '☀️ Switch to Light Mode' : '🌙 Switch to Dark Mode'}
        </button>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 flex flex-col gap-6">
        
        {/* TOP GREETING & PROFILE BAR */}
        <header className={`flex justify-between items-center p-5 rounded-2xl border ${cardClass}`}>
          <div>
            <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Welcome back, Flight Surgeon</p>
            <h1 className="text-2xl font-black tracking-tight">Mission Control Dashboard</h1>
          </div>
          <div className="flex items-center gap-4">
            <span className={`px-3 py-1 rounded-full text-xs font-mono font-bold ${
              connectionStatus.includes('LIVE') ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
            }`}>
              ● {connectionStatus}
            </span>
            <div className="flex items-center gap-3 pl-4 border-l border-slate-300 dark:border-slate-800">
              <div className="w-10 h-10 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-sm">EV</div>
              <div>
                <p className="text-sm font-bold">Dr. Elena Vance</p>
                <p className={`text-[10px] ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>Lead Medical Officer</p>
              </div>
            </div>
          </div>
        </header>

        {/* DASHBOARD GRID CONTENT */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left 2 Columns: Live Telemetry Cards */}
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
            <WidgetCard title="Heart Rate" value={telemetry?.heart_rate || '74'} unit="BPM" status="NOMINAL" isDark={isDark} cardClass={cardClass} baseline="58-74 | Z: +0.12" />
            <WidgetCard title="Blood Oxygen (SpO2)" value={telemetry?.blood_oxygen || '98'} unit="%" status="NOMINAL" isDark={isDark} cardClass={cardClass} baseline="96-99 | Z: -0.05" />
            <WidgetCard title="Core Body Temperature" value={telemetry?.body_temp || '37.1'} unit="°C" status="NOMINAL" isDark={isDark} cardClass={cardClass} baseline="36.5-37.2 | Z: +0.85" />
            <WidgetCard title="Fatigue Level" value={telemetry?.fatigue_level || '3'} unit="/10" status="CAUTION" isDark={isDark} cardClass={cardClass} baseline="Scale 1-10" />
          </div>

          {/* Right Column: Mission Status & Actions */}
          <div className="flex flex-col gap-6">
            <div className={`p-6 rounded-2xl border flex flex-col justify-between ${cardClass}`}>
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider mb-4">Crew Fleet Status</h3>
                <div className="space-y-3">
                  <CrewStatusRow name="Alex (Commander)" status="NOMINAL" color="bg-emerald-500" isDark={isDark} />
                  <CrewStatusRow name="James (Pilot)" status="ATTENTION" color="bg-amber-500" isDark={isDark} />
                  <CrewStatusRow name="Sarah (Specialist)" status="NOMINAL" color="bg-emerald-500" isDark={isDark} />
                </div>
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-gradient-to-br from-cyan-600 to-blue-700 text-white shadow-lg relative overflow-hidden flex flex-col justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase bg-white/20 px-2 py-0.5 rounded backdrop-blur-md">Intelligence Engine</span>
                <h4 className="text-lg font-bold mt-2">Run Next-Gen Baseline Diagnostics</h4>
                <p className="text-xs text-cyan-100 mt-1">Analyze multi-variate trends across sleep debt and heart rate variability.</p>
              </div>
              <button className="mt-4 py-2 px-4 bg-white text-blue-900 font-semibold text-xs rounded-xl hover:bg-cyan-50 transition-colors shadow-md">
                Launch Diagnostic Scan →
              </button>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}

function WidgetCard({ title, value, unit, status, isDark, cardClass, baseline }) {
  const statusColor = status === 'NOMINAL' ? 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20' : 'text-amber-500 bg-amber-500/10 border-amber-500/20';

  return (
    <div className={`p-5 rounded-2xl border flex flex-col justify-between ${cardClass}`}>
      <div className="flex justify-between items-start">
        <span className={`text-xs font-semibold uppercase tracking-wider ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{title}</span>
        <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded-full border ${statusColor}`}>{status}</span>
      </div>
      <div className="flex items-baseline gap-2 my-4">
        <span className="text-4xl font-mono font-extrabold">{value}</span>
        <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>{unit}</span>
      </div>
      <div className={`pt-3 border-t text-[11px] font-mono flex justify-between ${isDark ? 'border-slate-800 text-slate-400' : 'border-slate-100 text-slate-500'}`}>
        <span>Personal Baseline</span>
        <span>{baseline}</span>
      </div>
    </div>
  );
}

function CrewStatusRow({ name, status, color, isDark }) {
  return (
    <div className="flex items-center justify-between text-xs font-medium">
      <span className={isDark ? 'text-slate-300' : 'text-slate-700'}>{name}</span>
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${color}`} />
        <span className="font-mono">{status}</span>
      </div>
    </div>
  );
}
