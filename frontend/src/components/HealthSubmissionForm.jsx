import React, { useState } from 'react';

export default function HealthSubmissionForm({ astronautList }) {
  const [formData, setFormData] = useState({
    astronaut_id: '',
    heart_rate: 72,
    systolic_bp: 120,
    diastolic_bp: 80,
    body_temperature: 36.8,
    oxygen_saturation: 98,
    sleep_duration: 7.5,
    physical_activity: 30,
    fatigue_level: 3,
  });
  const [status, setStatus] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...formData, source: 'manual', recorded_at: new Date().toISOString() }),
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Validation failed on server');
      }
      setStatus({ type: 'success', message: 'Health reading successfully ingested!' });
    } catch (err) {
      setStatus({ type: 'error', message: err.message });
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg max-w-xl text-slate-100 font-sans">
      <h2 className="text-lg font-bold mb-4">Manual Health Data Ingestion</h2>
      {status && (
        <div className={`p-3 mb-4 rounded text-sm ${status.type === 'success' ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400'}`}>
          {status.message}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-mono uppercase text-slate-400 mb-1">Select Astronaut</label>
          <select 
            className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm"
            value={formData.astronaut_id}
            onChange={(e) => setFormData({...formData, astronaut_id: e.target.value})}
            required
          >
            <option value="">-- Choose Astronaut --</option>
            {astronautList?.map(a => (
              <option key={a.id} value={a.id}>{a.name} ({a.role})</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-mono uppercase text-slate-400 mb-1">Heart Rate (BPM)</label>
            <input 
              type="number" 
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm font-mono"
              value={formData.heart_rate}
              onChange={(e) => setFormData({...formData, heart_rate: parseInt(e.target.value)})}
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-slate-400 mb-1">Blood Oxygen (%)</label>
            <input 
              type="number" 
              step="0.1"
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm font-mono"
              value={formData.oxygen_saturation}
              onChange={(e) => setFormData({...formData, oxygen_saturation: parseFloat(e.target.value)})}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-mono uppercase text-slate-400 mb-1">Sleep Duration (Hours)</label>
            <input 
              type="number" 
              step="0.5"
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm font-mono"
              value={formData.sleep_duration}
              onChange={(e) => setFormData({...formData, sleep_duration: parseFloat(e.target.value)})}
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase text-slate-400 mb-1">Fatigue Level (1-10)</label>
            <input 
              type="number" 
              min="1" max="10"
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm font-mono"
              value={formData.fatigue_level}
              onChange={(e) => setFormData({...formData, fatigue_level: parseInt(e.target.value)})}
            />
          </div>
        </div>

        <button type="submit" className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 font-medium rounded text-sm transition-colors">
          Submit Telemetry Packet
        </button>
      </form>
    </div>
  );
}
