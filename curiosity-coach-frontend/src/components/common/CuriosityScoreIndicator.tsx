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
    <div className="fixed top-20 right-4 z-40">
      <div className="bg-white/90 backdrop-blur-sm shadow-lg rounded-xl px-5 py-4 flex flex-col items-center w-60">
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
              stroke="#8B5CF6"
              strokeWidth={8}
              fill="none"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-[stroke-dashoffset] duration-500 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-semibold text-gray-800">{safeScore}</span>
          </div>
        </div>
        <span className="mt-2 text-xs font-medium text-gray-600 tracking-wide uppercase">Score</span>
        <div className="mt-3 w-full text-left space-y-1.5">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Try this</p>
          <p className="text-sm text-gray-700 leading-snug">{displayTip}</p>
        </div>
      </div>
    </div>
  );
};

export default CuriosityScoreIndicator;
