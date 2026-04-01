import React from 'react';
import PromptVersionsView from './PromptVersionsView';

const BrainConfigView: React.FC = () => {
  return (
    <div className="p-2 sm:p-4 lg:p-6 space-y-4 sm:space-y-6 bg-white shadow rounded-lg m-2 sm:m-4">
      <div className="border-b pb-3">
        <h2 className="text-lg font-semibold text-gray-900">Prompt Versions</h2>
      </div>
      <div className="py-1">
        <PromptVersionsView />
      </div>
    </div>
  );
};

export default BrainConfigView;
