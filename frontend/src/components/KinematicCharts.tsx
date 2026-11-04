import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { FrameMetric } from '../types/cricket';

interface KinematicChartsProps {
  timeSeries: FrameMetric[];
  currentFrame?: number;
  onSelectFrame?: (frame: number) => void;
}

export const KinematicCharts: React.FC<KinematicChartsProps> = ({
  timeSeries,
  currentFrame = 0,
  onSelectFrame,
}) => {
  const [activeMetric, setActiveMetric] = useState<'knee' | 'elbow' | 'extension' | 'torso' | 'head' | 'stance' | 'weight'>('knee');

  if (!timeSeries || timeSeries.length === 0) {
    return <div className="p-4 text-slate-400 text-xs">No time series kinematic data.</div>;
  }

  const chartData = timeSeries.map((m) => ({
    frame: m.frame_index,
    time: m.timestamp_sec,
    leadKnee: m.lead_knee_angle ?? null,
    rearKnee: m.rear_knee_angle ?? null,
    leadElbow: m.lead_elbow_angle ?? null,
    rearElbow: m.rear_elbow_angle ?? null,
    armExtension: m.lead_arm_extension ? Number((m.lead_arm_extension * 100).toFixed(1)) : null,
    torsoLean: m.torso_inclination ?? null,
    headDisp: m.head_displacement ? Number((m.head_displacement * 10).toFixed(2)) : null,
    stanceWidth: m.stance_width_norm ?? null,
    weightDist: m.weight_distribution_proxy ? Number((m.weight_distribution_proxy * 100).toFixed(1)) : null,
    phase: m.phase,
  }));

  const metricConfigs = {
    knee: {
      title: 'Lead Knee Flexion Angle',
      unit: 'degrees (°)',
      yKey: 'leadKnee',
      color: '#22c55e',
      yDomain: [90, 185],
      benchmark: 125,
      benchmarkLabel: 'MCC Cover Drive Target (125°)',
      desc: 'Interior angle formed between hip, knee, and ankle. 180° = fully straight leg, 115°–135° = balanced front foot drive bend.',
    },
    elbow: {
      title: 'Lead Elbow Flexion Angle',
      unit: 'degrees (°)',
      yKey: 'leadElbow',
      color: '#34d399',
      yDomain: [70, 180],
      benchmark: 145,
      benchmarkLabel: 'High Elbow Benchmark (135°–160°)',
      desc: 'Angle formed between shoulder, elbow, and wrist. Maintaining a high lead elbow provides blade control through the line of the ball.',
    },
    extension: {
      title: 'Lead Arm Reach Extension',
      unit: '% full arm length',
      yKey: 'armExtension',
      color: '#06b6d4',
      yDomain: [50, 105],
      benchmark: 90,
      benchmarkLabel: 'Optimal Impact Reach (~90%)',
      desc: 'Distance from lead shoulder to lead wrist divided by total arm segment length. Measures straight-line arm extension into the shot.',
    },
    torso: {
      title: 'Torso Forward Lean Angle',
      unit: 'degrees from vertical (°)',
      yKey: 'torsoLean',
      color: '#38bdf8',
      yDomain: [0, 50],
      benchmark: 25,
      benchmarkLabel: 'Optimal Drive Lean (20°–30°)',
      desc: 'Angular deviation of the spine line (mid-hip to mid-shoulder) relative to the image-plane vertical axis.',
    },
    head: {
      title: 'Head Displacement Trajectory',
      unit: 'normalized units (x10)',
      yKey: 'headDisp',
      color: '#eab308',
      yDomain: [0, 8],
      benchmark: 2.2,
      benchmarkLabel: 'Stability Threshold',
      desc: 'Head landmark displacement relative to pelvis anchor, scaled by torso length to account for camera distance.',
    },
    stance: {
      title: 'Normalized Stance Width Ratio',
      unit: 'torso length ratio',
      yKey: 'stanceWidth',
      color: '#a855f7',
      yDomain: [0.5, 2.8],
      benchmark: 1.5,
      benchmarkLabel: 'Standard Front Stride (~1.5x)',
      desc: 'Inter-ankle distance divided by torso height. Measures base foundation stability during stride.',
    },
    weight: {
      title: 'Front-Foot Weight Distribution Proxy',
      unit: '% weight on front foot',
      yKey: 'weightDist',
      color: '#f43f5e',
      yDomain: [10, 100],
      benchmark: 75,
      benchmarkLabel: 'Front-Foot Drive Target (70%–85%)',
      desc: 'Estimated center-of-mass coronal projection between feet base of support. Values > 60% indicate positive forward weight transfer.',
    },
  };

  const curr = metricConfigs[activeMetric];

  return (
    <div className="bg-navy-900/80 rounded-xl border border-navy-800 p-4 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
            <span>Biomechanical Kinematic Curves</span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-brand-500/10 text-brand-400 border border-brand-500/20">
              TimeSeries
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">{curr.desc}</p>
        </div>

        {/* Tab switcher */}
        <div className="flex flex-wrap gap-1 bg-navy-950 p-1 rounded-lg border border-navy-800 self-start">
          <button
            onClick={() => setActiveMetric('knee')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-all ${
              activeMetric === 'knee' ? 'bg-brand-500 text-navy-950 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Lead Knee
          </button>
          <button
            onClick={() => setActiveMetric('elbow')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-all ${
              activeMetric === 'elbow' ? 'bg-emerald-500 text-navy-950 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Lead Elbow
          </button>
          <button
            onClick={() => setActiveMetric('extension')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-all ${
              activeMetric === 'extension' ? 'bg-cyan-500 text-navy-950 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Arm Reach
          </button>
          <button
            onClick={() => setActiveMetric('torso')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-all ${
              activeMetric === 'torso' ? 'bg-sky-500 text-navy-950 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Torso Lean
          </button>
          <button
            onClick={() => setActiveMetric('head')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-all ${
              activeMetric === 'head' ? 'bg-yellow-500 text-navy-950 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Head Stability
          </button>
          <button
            onClick={() => setActiveMetric('stance')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-all ${
              activeMetric === 'stance' ? 'bg-purple-500 text-navy-950 font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Stance Width
          </button>
          <button
            onClick={() => setActiveMetric('weight')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-all ${
              activeMetric === 'weight' ? 'bg-rose-500 text-white font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Weight Transfer
          </button>
        </div>
      </div>

      {/* Chart container */}
      <div className="h-64 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            onClick={(e: any) => {
              if (e && e.activePayload && e.activePayload.length > 0) {
                const f = e.activePayload[0].payload.frame;
                if (onSelectFrame && typeof f === 'number') onSelectFrame(f);
              }
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="frame"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              tickFormatter={(v) => `F${v}`}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              domain={curr.yDomain as any}
              tickLine={false}
              unit={
                activeMetric === 'knee' || activeMetric === 'elbow' || activeMetric === 'torso'
                  ? '°'
                  : activeMetric === 'extension' || activeMetric === 'weight'
                  ? '%'
                  : ''
              }
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0b1120',
                borderColor: '#334155',
                borderRadius: '8px',
                fontSize: '12px',
                color: '#f8fafc',
              }}
              formatter={(val: any) => [`${val} ${curr.unit}`, curr.title]}
              labelFormatter={(label: any) => `Frame ${label} (${(Number(label) / 30).toFixed(2)}s)`}
            />
            <ReferenceLine
              y={curr.benchmark}
              stroke="#ef4444"
              strokeDasharray="4 4"
              label={{
                value: curr.benchmarkLabel,
                fill: '#ef4444',
                fontSize: 10,
                position: 'insideBottomRight',
              }}
            />
            {currentFrame >= 0 && (
              <ReferenceLine
                x={currentFrame}
                stroke="#ffffff"
                strokeWidth={2}
                label={{
                  value: 'Current Frame',
                  fill: '#ffffff',
                  fontSize: 10,
                  position: 'top',
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey={curr.yKey}
              stroke={curr.color}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, fill: curr.color, stroke: '#ffffff' }}
              name={curr.title}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-navy-800">
        <span className="flex items-center space-x-1.5">
          <span className="w-2.5 h-0.5 bg-rose-500 inline-block" />
          <span>Dashed line: Reference technical standard</span>
        </span>
        <span>Click anywhere on chart to jump video scrubber</span>
      </div>
    </div>
  );
};
