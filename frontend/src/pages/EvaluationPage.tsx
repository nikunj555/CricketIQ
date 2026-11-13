import React, { useState, useEffect } from 'react';
import {
  BrainCircuit,
  Activity,
  CheckCircle2,
  TrendingUp,
  Cpu,
  Layers,
  ShieldAlert,
  BarChart2
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  BarChart,
  Bar,
} from 'recharts';
import { ModelEvaluationReport } from '../types/cricket';
import { api } from '../services/api';
import { ConfusionMatrix } from '../components/ConfusionMatrix';

export const EvaluationPage: React.FC = () => {
  const [report, setReport] = useState<ModelEvaluationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadReport();
  }, []);

  const loadReport = async () => {
    try {
      setLoading(true);
      const rep = await api.getEvaluationReport();
      setReport(rep);
    } catch (err: any) {
      setError(err.message || 'Failed to load model evaluation report');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center space-y-3">
        <Activity className="w-8 h-8 text-[#7FEA35] animate-spin mx-auto" />
        <h3 className="text-sm font-semibold text-[#F5F5F5]">Loading Model Benchmarks...</h3>
      </div>
    );
  }

  if (error || !report || !report.has_empirical_data) {
    const minRequired = report?.min_required_per_shot ?? 8;
    const clipCount = report?.labeled_clips_count ?? 0;
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-[#181B1D] border border-[#303438] flex items-center justify-center mx-auto text-amber-400">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-extrabold text-[#F5F5F5] tracking-tight">
            Classifier Evaluation Requires Empirical Data
          </h2>
          <p className="text-xs text-[#A5A9AD] max-w-lg mx-auto leading-relaxed">
            Classifier evaluation requires at least {minRequired} labelled clips per shot. Current labelled clips: {clipCount}. Run <code className="text-[#7FEA35] bg-[#111315] px-1.5 py-0.5 rounded border border-[#303438]">scripts/evaluate_classifier.py</code> once data is added.
          </p>
        </div>

        <div className="bg-[#181B1D] border border-[#303438] rounded-2xl p-6 text-left max-w-lg mx-auto space-y-4 font-mono text-xs shadow-xl">
          <div className="flex items-center justify-between border-b border-[#303438] pb-3">
            <span className="text-[#A5A9AD]">Empirical Validation Status</span>
            <span className="text-amber-400 font-bold">Unvalidated</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#A5A9AD]">Labelled Clips in Repository:</span>
            <span className="text-[#F5F5F5] font-bold">{clipCount}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#A5A9AD]">Required per Supported Shot:</span>
            <span className="text-[#7FEA35] font-bold">≥ {minRequired} clips (≥ 2 batters)</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[#A5A9AD]">Evaluation Script:</span>
            <span className="text-sky-400">scripts/evaluate_classifier.py</span>
          </div>
        </div>
      </div>
    );
  }

  // Format loss curve data
  const lossData = report.training_loss_history.map((trainLoss, idx) => ({
    epoch: idx + 1,
    trainLoss,
    valLoss: report.val_loss_history[idx] ?? null,
  }));

  // Format feature importance data
  const featData = Object.entries(report.feature_importance).map(([name, val]) => ({
    feature: name,
    importance: Number((val * 100).toFixed(1)),
  }));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-navy-800">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Machine Learning Evaluation & Project Research
            </h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Empirical Benchmarks
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Experimental results from trained BiLSTM temporal sequence model versus baseline classifier on held-out test data (Synthetic Benchmark).
          </p>
        </div>
      </div>

      {/* Model Overview & Metric Banners */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-navy-900/80 p-5 rounded-xl border border-navy-800 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              BiLSTM Test Accuracy
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-navy-800 text-brand-400 border border-brand-500/30">
              Synthetic Benchmark
            </span>
          </div>
          <div className="text-3xl font-extrabold font-mono text-emerald-400">
            {(report.accuracy * 100).toFixed(2)}%
          </div>
          <p className="text-[11px] text-slate-400">
            Baseline: {(report.baseline_comparison.baseline_accuracy * 100).toFixed(2)}% ({'+' + report.baseline_comparison.accuracy_improvement}%)
          </p>
        </div>

        <div className="bg-navy-900/80 p-5 rounded-xl border border-navy-800 space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Macro F1-Score
          </span>
          <div className="text-3xl font-extrabold font-mono text-brand-400">
            {report.macro_f1.toFixed(4)}
          </div>
          <p className="text-[11px] text-slate-400">
            Baseline F1: {report.baseline_comparison.baseline_macro_f1.toFixed(4)} ({'+' + report.baseline_comparison.f1_improvement}%)
          </p>
        </div>

        <div className="bg-navy-900/80 p-5 rounded-xl border border-navy-800 space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Held-out Test Set
          </span>
          <div className="text-3xl font-extrabold font-mono text-white">
            {report.total_test_frames}
          </div>
          <p className="text-[11px] text-slate-400">
            Frames across {report.total_test_sequences} un-leaked sequences
          </p>
        </div>

        <div className="bg-navy-900/80 p-5 rounded-xl border border-navy-800 space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Inference Latency
          </span>
          <div className="text-3xl font-extrabold font-mono text-cricket-sky">
            {report.inference_latency_ms} ms
          </div>
          <p className="text-[11px] text-slate-400">Per 60-frame batting sequence on CPU</p>
        </div>
      </div>

      {/* Model vs Baseline Comparison Card */}
      <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center justify-between">
          <span>Baseline Model vs Deep Learning Temporal Model</span>
          <span className="text-xs font-mono text-brand-400 font-semibold">Scientific Comparison</span>
        </h3>
        <p className="text-xs text-slate-300 leading-relaxed">
          The deep learning model incorporates bidirectional temporal recurrence (BiLSTM), resolving frame-level ambiguity between symmetrical arm and leg positions across stroke phases.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
          <div className="bg-navy-950 p-4 rounded-xl border border-navy-800 space-y-2">
            <span className="text-xs font-mono text-slate-400 uppercase">Baseline Model</span>
            <div className="text-base font-bold text-slate-200">
              {report.baseline_comparison.baseline_model}
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
              <div>
                <span className="text-slate-500">Accuracy: </span>
                <strong className="text-white">{(report.baseline_comparison.baseline_accuracy * 100).toFixed(2)}%</strong>
              </div>
              <div>
                <span className="text-slate-500">Macro F1: </span>
                <strong className="text-white">{report.baseline_comparison.baseline_macro_f1.toFixed(4)}</strong>
              </div>
            </div>
            <p className="text-[11px] text-slate-500">
              Evaluates frames independently without temporal order or past sequence context.
            </p>
          </div>

          <div className="bg-navy-950 p-4 rounded-xl border border-emerald-500/30 space-y-2 relative overflow-hidden">
            <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-mono font-bold">
              +{(report.baseline_comparison.accuracy_improvement).toFixed(1)}% Gain
            </div>
            <span className="text-xs font-mono text-emerald-400 uppercase">Advanced Deep Temporal Model</span>
            <div className="text-base font-bold text-white">
              {report.architecture}
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
              <div>
                <span className="text-slate-400">Accuracy: </span>
                <strong className="text-emerald-400">{(report.baseline_comparison.deep_learning_accuracy * 100).toFixed(2)}%</strong>
              </div>
              <div>
                <span className="text-slate-400">Macro F1: </span>
                <strong className="text-brand-400">{report.baseline_comparison.deep_learning_macro_f1.toFixed(4)}</strong>
              </div>
            </div>
            <p className="text-[11px] text-slate-400">
              Bidirectional LSTM captures lead-up kinematics and trajectory progression.
            </p>
          </div>
        </div>
      </div>

      {/* Confusion Matrix and Per-Class Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Confusion Matrix Heatmap */}
        <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            7x7 Multi-Class Confusion Matrix (Test Split)
          </h3>
          <p className="text-xs text-slate-400">
            Row represents ground-truth cricket phase; column represents model prediction.
          </p>
          <ConfusionMatrix matrix={report.confusion_matrix} classes={report.classes} />
        </div>

        {/* Per-Class Precision / Recall / F1 Table */}
        <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Per-Class Classification Metrics
          </h3>
          <p className="text-xs text-slate-400">
            Independent evaluation per batting action phase on held-out test frames:
          </p>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-navy-800 text-xs font-mono">
              <thead>
                <tr className="text-slate-400 text-[11px]">
                  <th className="py-2 px-2 text-left font-sans">Phase Name</th>
                  <th className="py-2 px-2 text-right">Precision</th>
                  <th className="py-2 px-2 text-right">Recall</th>
                  <th className="py-2 px-2 text-right">F1-Score</th>
                  <th className="py-2 px-2 text-right">Support</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-800/60 font-sans">
                {report.per_class_metrics.map((row, i) => (
                  <tr key={i} className="hover:bg-navy-850">
                    <td className="py-2.5 px-2 font-medium text-white">{row.class_name}</td>
                    <td className="py-2.5 px-2 text-right font-mono text-slate-300">
                      {(row.precision * 100).toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-2 text-right font-mono text-slate-300">
                      {(row.recall * 100).toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-2 text-right font-mono font-bold text-brand-400">
                      {row.f1_score.toFixed(3)}
                    </td>
                    <td className="py-2.5 px-2 text-right font-mono text-slate-400">{row.support}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Training & Validation Loss Learning Curves */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Training & Validation Loss Convergence
          </h3>
          <p className="text-xs text-slate-400">
            CrossEntropyLoss over 28 epochs with AdamW (weight decay 1e-4, gradient clipping):
          </p>

          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lossData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="epoch" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0b1120',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="trainLoss"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  name="Training Loss"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="valLoss"
                  stroke="#22c55e"
                  strokeWidth={2}
                  name="Validation Loss"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Feature Importance Breakdown */}
        <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Kinematic Feature Contribution Weights
          </h3>
          <p className="text-xs text-slate-400">
            Relative importance of input features for phase boundary discrimination:
          </p>

          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={featData.slice(0, 8)} layout="vertical" margin={{ left: 35 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" stroke="#64748b" fontSize={10} tickLine={false} unit="%" />
                <YAxis
                  type="category"
                  dataKey="feature"
                  stroke="#64748b"
                  fontSize={10}
                  tickLine={false}
                  width={90}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0b1120',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="importance" fill="#4ade80" radius={[0, 4, 4, 0]} name="Weight (%)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Dataset & Methodology Transparency Card */}
      <div className="bg-navy-900/80 rounded-2xl border border-navy-800 p-6 space-y-3">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
          Experimental Methodology & Data Integrity Statement
        </h3>
        <p className="text-xs text-slate-300 leading-relaxed">
          <strong>Splitting Strategy: </strong>Group-aware sequence partition (70% train, 15% validation, 15% held-out test).
          Entire video sequences are isolated so that near-duplicate frames from the same stroke cycle never leak across splits.
        </p>
        <p className="text-xs text-slate-400 leading-relaxed">
          <strong>AQA Benchmark Alignment: </strong>Ground-truth phase definitions conform to the GCSE / UJ-AQA-CricketVision / CricTAL
          temporal action specifications (Moodley & van der Haar, IEEE/CVF WACV).
        </p>
      </div>
    </div>
  );
};
