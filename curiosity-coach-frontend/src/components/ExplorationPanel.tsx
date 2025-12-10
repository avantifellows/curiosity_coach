import React from 'react';

interface ExplorationPanelProps {
  isOpen: boolean;
  onClose: () => void;
  directions: string[];
  prompt?: string; // kept for compatibility, not rendered
}

const ExplorationPanel: React.FC<ExplorationPanelProps> = ({ isOpen, onClose, directions }) => {
  if (!isOpen) return null;

  const visibleDirections = (directions || []).slice(0, 3);

  return (
    <div
      className="
        fixed left-4 top-4 z-40
        bg-white border border-gray-200 shadow-xl rounded-lg
        w-[300px] sm:w-[340px] md:w-[380px]
      "
      role="dialog"
      aria-label="Exploration directions"
    >
      <div className="p-3 sm:p-4 border-b bg-gray-50 flex items-center justify-between rounded-t-lg">
        <h3 className="text-base sm:text-lg font-bold text-gray-900">Exploration directions</h3>
        <button
          onClick={onClose}
          className="text-gray-600 hover:text-gray-800 text-xs sm:text-sm border border-gray-300 px-2 py-1 rounded"
          aria-label="Collapse exploration panel"
          title="Collapse"
        >
          Collapse
        </button>
      </div>

      <div className="p-3 sm:p-4">
        {visibleDirections.length === 0 ? (
          <p className="text-sm text-gray-500">No exploration directions available.</p>
        ) : (
          <ul className="list-disc list-inside space-y-1">
            {visibleDirections.map((d, i) => (
              <li key={i} className="text-sm text-gray-800">
                {d}
              </li>
            ))}
          </ul>
        )}

        {directions.length > 3 && (
          <p className="mt-2 text-xs text-gray-500">{directions.length - 3} more not shown</p>
        )}
      </div>
    </div>
  );
};

export default ExplorationPanel;