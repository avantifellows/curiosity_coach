import React from 'react';

interface CuriosityScoreIndicatorProps {
  score: number;
  tip?: string;
}

const DEFAULT_TIPS = [
  "Respond to what the coach just said.",
  "Try asking the coach a cool follow-up!",
  "Challenge the coach with a smart question!"
];

const CuriosityScoreIndicator: React.FC<CuriosityScoreIndicatorProps> = ({ score, tip }) => {
  const safeScore = Number.isFinite(score) ? Math.max(0, Math.min(100, Math.round(score))) : 0;
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (safeScore / 100) * circumference;
  
  // Use provided tip, or fall back to a stable random default tip (memoized so it doesn't change on re-renders)
  const defaultTip = React.useMemo(() => {
    return DEFAULT_TIPS[Math.floor(Math.random() * DEFAULT_TIPS.length)];
  }, []);
  
  const displayTip = tip || defaultTip;

  return (
    <div className="fixed right-4 top-20 z-40 hidden xl:block">
      <div className="flex w-60 flex-col items-center rounded-2xl border border-violet-200 bg-white/95 px-5 py-4 shadow-sm">
        <div className="relative">
          <svg width={72} height={72} role="img" aria-label={`Curiosity score ${safeScore} out of 100`}>
            <circle
              cx={36}
              cy={36}
              r={radius}
              stroke="#E5E7EB"
              strokeWidth={8}
              fill="none"
            />
            <circle
              cx={36}
              cy={36}
              r={radius}
              stroke="#7C3AED"
              strokeWidth={8}
              fill="none"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-[stroke-dashoffset] duration-500 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-semibold text-slate-900">{safeScore}</span>
          </div>
        </div>
        <span className="mt-2 text-xs font-medium uppercase tracking-wide text-slate-500">Curiosity score</span>
        <div className="mt-3 w-full text-left space-y-1.5">
          <p className="text-xs font-semibold uppercase tracking-wide text-violet-700">Try this</p>
          <p className="text-sm leading-snug text-slate-700">{displayTip}</p>
        </div>
      </div>
    </div>
  );
};

export default CuriosityScoreIndicator;
