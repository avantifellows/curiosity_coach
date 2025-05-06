import React, { useState, useEffect } from 'react';
import { CircularProgress } from '@mui/material';
import { KeyboardArrowDown, KeyboardArrowUp } from '@mui/icons-material';

// Define a type for individual pipeline steps for clarity
export interface PipelineStep {
  name: string;
  enabled: boolean;
  prompt?: string | null;
  raw_result?: any; // Can be complex, so 'any' for now
  result?: string | null;
  main_topic?: string | null;
  related_topics?: string[];
  // Add other potential fields from your pipeline steps here
}

interface PipelineStepsModalProps {
  showModal: boolean;
  onClose: () => void;
  isLoading: boolean;
  error: string | null;
  steps: PipelineStep[];
}

const PipelineStepsModal: React.FC<PipelineStepsModalProps> = ({
  showModal,
  onClose,
  isLoading,
  error,
  steps,
}) => {
  const [collapsedSteps, setCollapsedSteps] = useState<{ [key: number]: boolean }>({});

  useEffect(() => {
    if (showModal && steps) {
      const initialCollapsedState: { [key: number]: boolean } = {};
      steps.forEach((_, index) => {
        initialCollapsedState[index] = true; // Set all steps to collapsed by default
      });
      setCollapsedSteps(initialCollapsedState);
    }
  }, [showModal, steps]); // Re-run when modal is shown or steps change

  if (!showModal) {
    return null;
  }

  const toggleStepCollapse = (index: number) => {
    setCollapsedSteps(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  return (
    <div 
      className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex justify-center items-center z-50"
      onClick={(e) => {
        if (e.target === e.currentTarget) { // Check if the click is on the backdrop itself
          onClose();
        }
      }}
    >
      <div className="relative p-5 border w-11/12 md:w-5/6 lg:w-3/4 shadow-lg rounded-md bg-white">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-lg font-medium text-gray-900">
            {error ? 'Error' : 'Thinking Process Steps'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm p-1.5 ml-auto inline-flex items-center"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span className="sr-only">Close modal</span>
          </button>
        </div>

        {isLoading && !error && <div className="flex justify-center items-center p-4"><CircularProgress /> <p className="ml-2">Loading steps...</p></div>}

        {error && (
          <div className="p-3 bg-red-100 text-red-700 rounded">
            <p><strong>Error:</strong> {error}</p>
          </div>
        )}

        {!isLoading && !error && steps.length > 0 && (
          <div className="mt-2 text-sm text-gray-700 max-h-[calc(100vh-15rem)] overflow-y-auto">
            <ul className="space-y-3">
              {steps.map((step, idx) => (
                <li key={idx} className="p-3 bg-gray-50 rounded-md shadow-sm">
                  <div 
                    className="flex justify-between items-center cursor-pointer py-2"
                    onClick={() => toggleStepCollapse(idx)}
                  >
                    <p className="text-lg font-bold text-gray-900">Step {idx + 1}: {step.name}</p>
                    {collapsedSteps[idx] ? <KeyboardArrowDown /> : <KeyboardArrowUp />}
                  </div>
                  
                  {!collapsedSteps[idx] && (
                    <div className="mt-2 space-y-2">
                      {step.enabled !== undefined && <p><strong className="text-gray-700">Enabled:</strong> {step.enabled ? 'Yes' : 'No'}</p>}
                      {step.main_topic && <p><strong className="text-gray-700">Main Topic:</strong> {step.main_topic}</p>}
                      {step.related_topics && step.related_topics.length > 0 && (
                        <p><strong className="text-gray-700">Related Topics:</strong> {step.related_topics.join(', ')}</p>
                      )}
                      {step.prompt && (
                        <div>
                          <p className="font-medium mt-1"><strong className="text-gray-700">Prompt:</strong></p>
                          <pre className="bg-gray-200 p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap border border-gray-300">{step.prompt}</pre>
                        </div>
                      )}
                      {step.raw_result && (
                        <div>
                          <p className="font-medium mt-1"><strong className="text-gray-700">Raw Result:</strong></p>
                          <pre className="bg-gray-200 p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap border border-gray-300">
                            {typeof step.raw_result === 'object' ? JSON.stringify(step.raw_result, null, 2) : step.raw_result}
                          </pre>
                        </div>
                      )}
                      {step.result && (
                         <div>
                          <p className="font-medium mt-1"><strong className="text-gray-700">Result:</strong></p>
                          <pre className="bg-gray-200 p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap border border-gray-300">{step.result}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
        {!isLoading && !error && steps.length === 0 && (
           <p className="text-gray-500">No pipeline steps available for this message.</p>
        )}
      </div>
    </div>
  );
};

export default PipelineStepsModal; 