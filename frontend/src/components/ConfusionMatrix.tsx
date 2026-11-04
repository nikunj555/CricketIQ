import React from 'react';

interface ConfusionMatrixProps {
  matrix: number[][];
  classes: string[];
}

export const ConfusionMatrix: React.FC<ConfusionMatrixProps> = ({ matrix, classes }) => {
  if (!matrix || matrix.length === 0 || !classes || classes.length === 0) {
    return <div className="text-slate-400 text-xs">No confusion matrix data.</div>;
  }

  // Find max value in diagonal / matrix for relative normalization
  let maxVal = 1;
  matrix.forEach((row) => {
    row.forEach((v) => {
      if (v > maxVal) maxVal = v;
    });
  });

  return (
    <div className="overflow-x-auto">
      <div className="inline-block min-w-full align-middle">
        <table className="min-w-full divide-y divide-navy-800 text-center font-mono text-xs">
          <thead>
            <tr>
              <th className="py-2 px-3 text-left font-sans text-slate-400 font-medium">True \ Pred</th>
              {classes.map((c, i) => (
                <th key={i} className="py-2 px-2 text-slate-300 font-medium whitespace-nowrap" title={c}>
                  {c.split('/')[0].slice(0, 7)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-navy-800/60">
            {matrix.map((row, rIdx) => {
              const rowSum = row.reduce((a, b) => a + b, 0);
              return (
                <tr key={rIdx} className="hover:bg-navy-900/60 transition-colors">
                  <td className="py-2 px-3 text-left font-sans text-slate-300 font-medium whitespace-nowrap">
                    {classes[rIdx].split('/')[0]}
                  </td>
                  {row.map((cell, cIdx) => {
                    const isDiagonal = rIdx === cIdx;
                    const intensity = Math.min(1, cell / maxVal);
                    // Green gradient for diagonal (correct), red for misclassification
                    const bgColor = isDiagonal
                      ? `rgba(34, 197, 94, ${0.15 + intensity * 0.7})`
                      : cell > 0
                      ? `rgba(239, 68, 68, ${0.15 + (cell / (rowSum || 1)) * 0.5})`
                      : 'transparent';

                    return (
                      <td
                        key={cIdx}
                        style={{ backgroundColor: bgColor }}
                        className={`py-2 px-2 transition-all ${
                          isDiagonal ? 'font-bold text-white' : cell > 0 ? 'text-rose-300' : 'text-slate-600'
                        }`}
                        title={`True: ${classes[rIdx]} | Pred: ${classes[cIdx]} = ${cell} frames`}
                      >
                        {cell}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-3">
        <span className="flex items-center space-x-2">
          <span className="w-3 h-3 bg-brand-500/80 rounded-sm" />
          <span>Diagonal = Correct Predictions</span>
        </span>
        <span className="flex items-center space-x-2">
          <span className="w-3 h-3 bg-rose-500/60 rounded-sm" />
          <span>Off-Diagonal = Classification Confusions</span>
        </span>
      </div>
    </div>
  );
};
