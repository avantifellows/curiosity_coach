import React from 'react';
import { Code } from '@mui/icons-material';

interface DebugInfoProps {
  visitNumber: number | null;
  promptVersionId?: number;
  curiosityScore?: number;
}

const DebugInfo: React.FC<DebugInfoProps> = ({ visitNumber, promptVersionId, curiosityScore }) => {
  // Derive prompt purpose from visit number
  const getPromptPurpose = (visit: number | null): string => {
    if (visit === null) return 'Unknown';
    if (visit === 1) return 'visit_1 (First Time User)';
    if (visit === 2) return 'visit_2 (Second Visit)';
    if (visit === 3) return 'visit_3 (Third Visit)';
    return 'steady_state (4+ Visits)';
  };

  if (visitNumber === null) return null;

  const formattedScore = typeof curiosityScore === 'number'
    ? Math.max(0, Math.min(100, Math.round(curiosityScore)))
    : null;

  return (
    <div className="fixed top-20 right-4 z-50 bg-black bg-opacity-80 text-white p-3 rounded-lg shadow-lg text-xs font-mono max-w-xs backdrop-blur-sm">
      <div className="flex items-center gap-2 mb-2 border-b border-gray-600 pb-2">
        <Code fontSize="small" />
        <span className="font-bold">Debug Info</span>
      </div>
      
      <div className="space-y-1">
        <div className="flex justify-between">
          <span className="text-gray-400">Visit Number:</span>
          <span className="font-bold text-green-400">{visitNumber}</span>
        </div>
        
        <div className="flex flex-col">
          <span className="text-gray-400">Prompt Purpose:</span>
          <span className="font-bold text-blue-400 mt-1">{getPromptPurpose(visitNumber)}</span>
        </div>
        
        {promptVersionId && (
          <div className="flex justify-between pt-1 border-t border-gray-700 mt-1">
            <span className="text-gray-400">Prompt Version ID:</span>
            <span className="font-bold text-purple-400">{promptVersionId}</span>
          </div>
        )}

        {formattedScore !== null && (
          <div className="flex justify-between pt-1 border-t border-gray-700 mt-1">
            <span className="text-gray-400">Curiosity Score:</span>
            <span className="font-bold text-yellow-300">{formattedScore}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default DebugInfo;
