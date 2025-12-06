import React from 'react';

interface CuriosityScoreIndicatorProps {
  score: number;
}

const CuriosityScoreIndicator: React.FC<CuriosityScoreIndicatorProps> = ({ score }) => {
  const safeScore = Number.isFinite(score) ? Math.max(0, Math.min(100, Math.round(score))) : 0;
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (safeScore / 100) * circumference;

  return (
    <div className="fixed top-20 right-4 z-40">
      <div className="bg-white/90 backdrop-blur-sm shadow-lg rounded-xl px-4 py-3 flex flex-col items-center">
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
      </div>
    </div>
  );
};

export default CuriosityScoreIndicator;
