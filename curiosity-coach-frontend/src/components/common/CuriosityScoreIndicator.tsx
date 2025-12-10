import React from 'react';

interface CuriosityScoreIndicatorProps {
  score: number;
}

const CuriosityScoreIndicator: React.FC<CuriosityScoreIndicatorProps> = ({ score }) => {
  const safeScore = Number.isFinite(score) ? Math.max(0, Math.min(100, Math.round(score))) : 0;
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (safeScore / 100) * circumference;
  const tips = [
    "Add one more detail by responding to questions!",
    "Ask a follow-up or toss in a fresh idea!",
  ];

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
          {tips.map((tip, index) => (
            <p key={index} className="text-sm text-gray-700 leading-snug">
              {index + 1}. {tip}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CuriosityScoreIndicator;
