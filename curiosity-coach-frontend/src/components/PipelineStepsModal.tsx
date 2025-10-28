import React, { useState, useEffect } from 'react';
import { CircularProgress } from '@mui/material';
import { KeyboardArrowDown, KeyboardArrowUp } from '@mui/icons-material';

// Define a type for individual pipeline steps for clarity
export interface PipelineStep {
  name: string;
  enabled: boolean;
  prompt?: string | null;
  prompt_template?: string | null;  // Original template with placeholders
  formatted_prompt?: string | null;  // What actually went to the LLM
  raw_result?: any; // Can be complex, so 'any' for now
  result?: string | null;
  main_topic?: string | null;
  related_topics?: string[];
  prompt_name?: string | null;
  prompt_version?: number | null;
  // Add chat controller specific fields
  original_response?: string | null;
  controlled_response?: string | null;
  core_theme?: string | null;
  chat_controller_applied?: boolean;
  // Add core theme extraction specific fields
  extraction_successful?: boolean;
  // Add exploration directions specific fields
  directions?: string[];
  evaluation_successful?: boolean;
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
      className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex justify-center items-start sm:items-center z-50 p-2 sm:p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) { // Check if the click is on the backdrop itself
          onClose();
        }
      }}
    >
      <div className="relative border w-full max-w-4xl shadow-lg rounded-md bg-white mt-4 sm:mt-0 max-h-[90vh] sm:max-h-[85vh] flex flex-col">
        <div className="flex justify-between items-center p-4 sm:p-5 border-b border-gray-200 flex-shrink-0">
          <h3 className="text-lg sm:text-xl font-medium text-gray-900">
            {error ? 'Error' : 'Thinking Process Steps'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm p-2 sm:p-1.5 ml-auto inline-flex items-center touch-manipulation"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span className="sr-only">Close modal</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 sm:p-5">
          {isLoading && !error && (
            <div className="flex justify-center items-center p-4">
              <CircularProgress /> 
              <p className="ml-2 text-sm sm:text-base">Loading steps...</p>
            </div>
          )}

          {error && (
            <div className="p-3 sm:p-4 bg-red-100 text-red-700 rounded">
              <p className="text-sm sm:text-base"><strong>Error:</strong> {error}</p>
            </div>
          )}

          {!isLoading && !error && steps.length > 0 && (
            <div className="text-sm sm:text-base text-gray-700">
              <ul className="space-y-3 sm:space-y-4">
                {steps.map((step, idx) => (
                  <li key={idx} className="p-3 sm:p-4 bg-gray-50 rounded-md shadow-sm">
                    <div 
                      className="flex justify-between items-center cursor-pointer py-2 touch-manipulation"
                      onClick={() => toggleStepCollapse(idx)}
                    >
                      <div className="min-w-0 flex-1 pr-2">
                        <p className="text-base sm:text-lg font-bold text-gray-900 break-words">
                          Step {idx + 1}: {step.prompt_name || step.name}
                        </p>
                        {step.prompt_name && step.prompt_version && (
                          <p className="text-sm text-gray-600 break-words">
                            Version {step.prompt_version}
                          </p>
                        )}
                      </div>
                      <div className="flex-shrink-0">
                        {collapsedSteps[idx] ? <KeyboardArrowDown /> : <KeyboardArrowUp />}
                      </div>
                    </div>
                    
                    {!collapsedSteps[idx] && (
                      <div className="mt-2 space-y-2 sm:space-y-3">
                        {step.enabled !== undefined && (
                          <p className="text-sm sm:text-base">
                            <strong className="text-gray-700">Enabled:</strong> {step.enabled ? 'Yes' : 'No'}
                          </p>
                        )}
                        {step.main_topic && (
                          <p className="text-sm sm:text-base break-words">
                            <strong className="text-gray-700">Main Topic:</strong> {step.main_topic}
                          </p>
                        )}
                        {step.related_topics && step.related_topics.length > 0 && (
                          <p className="text-sm sm:text-base break-words">
                            <strong className="text-gray-700">Related Topics:</strong> {step.related_topics.join(', ')}
                          </p>
                        )}
                        
                        {/* Core Theme Extraction Handling */}
                        {step.name === 'core_theme_extraction' && (
                          <div className="space-y-3">
                            <div className="bg-purple-50 p-3 rounded border-l-4 border-purple-400">
                              <p className="font-medium text-purple-800">Core Theme Extraction</p>
                              <p className="text-sm text-purple-600">
                                {step.extraction_successful ? 
                                  `Extracted Theme: ${step.core_theme}` : 
                                  'No core theme could be extracted'
                                }
                              </p>
                            </div>
                            
                            {step.prompt && (
                              <div>
                                <p className="font-medium mt-1 text-sm sm:text-base">
                                  <strong className="text-gray-700">Prompt Used:</strong>
                                </p>
                                <pre className="bg-gray-200 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-gray-300 max-w-full">{step.prompt}</pre>
                              </div>
                            )}
                            
                            {step.result && (
                              <div>
                                <p className="font-medium mt-1 text-sm sm:text-base">
                                  <strong className="text-gray-700">Extracted Theme:</strong>
                                </p>
                                <pre className="bg-purple-100 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-purple-300 max-w-full">{step.result}</pre>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {/* Chat Controller Handling */}
                        {step.name === 'chat_controller' && step.chat_controller_applied && (
                          <div className="space-y-3">
                            <div className="bg-blue-50 p-3 rounded border-l-4 border-blue-400">
                              <p className="font-medium text-blue-800">Chat Controller Applied</p>
                              <p className="text-sm text-blue-600">Core Theme: {step.core_theme}</p>
                            </div>
                            
                            {step.original_response && (
                              <div>
                                <p className="font-medium mt-1 text-sm sm:text-base">
                                  <strong className="text-gray-700">Original Response:</strong>
                                </p>
                                <pre className="bg-gray-100 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-gray-300 max-w-full">{step.original_response}</pre>
                              </div>
                            )}
                            
                            {step.controlled_response && (
                              <div>
                                <p className="font-medium mt-1 text-sm sm:text-base">
                                  <strong className="text-gray-700">Controlled Response:</strong>
                                </p>
                                <pre className="bg-green-100 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-green-300 max-w-full">{step.controlled_response}</pre>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {/* Exploration Directions Evaluation Handling */}
                        {step.name === 'exploration_directions_evaluation' && step.directions && step.directions.length > 0 && (
                          <div className="space-y-3">
                            <div className="bg-amber-50 p-3 rounded border-l-4 border-amber-400">
                              <p className="font-medium text-amber-800">Exploration Directions</p>
                              <p className="text-sm text-amber-600">
                                {step.evaluation_successful ? 
                                  `${step.directions.length} exploration direction${step.directions.length !== 1 ? 's' : ''} identified` : 
                                  'Failed to identify exploration directions'
                                }
                              </p>
                            </div>
                            
                            {step.core_theme && (
                              <div>
                                <p className="font-medium mt-1 text-sm sm:text-base">
                                  <strong className="text-gray-700">Core Theme:</strong>
                                </p>
                                <p className="bg-purple-50 p-2 rounded text-sm border border-purple-200">{step.core_theme}</p>
                              </div>
                            )}
                            
                            {step.directions && step.directions.length > 0 && (
                              <div>
                                <p className="font-medium mt-1 text-sm sm:text-base">
                                  <strong className="text-gray-700">Possible Exploration Directions:</strong>
                                </p>
                                <ul className="list-disc list-inside space-y-1 bg-amber-50 p-3 rounded border border-amber-200">
                                  {step.directions.map((direction, directionIdx) => (
                                    <li key={directionIdx} className="text-sm text-gray-800">{direction}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            
                            {step.prompt && (
                              <div>
                                <p className="font-medium mt-1 text-sm sm:text-base">
                                  <strong className="text-gray-700">Prompt Used:</strong>
                                </p>
                                <pre className="bg-gray-200 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-gray-300 max-w-full">{step.prompt}</pre>
                              </div>
                            )}
                          </div>
                        )}
                        
                        {step.prompt_template && (
                          <div>
                            <p className="font-medium mt-1 text-sm sm:text-base">
                              <strong className="text-gray-700">Prompt Template (with placeholders):</strong>
                            </p>
                            <pre className="bg-gray-200 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-gray-300 max-w-full">{step.prompt_template}</pre>
                          </div>
                        )}
                        {step.formatted_prompt && (
                          <div>
                            <p className="font-medium mt-1 text-sm sm:text-base">
                              <strong className="text-green-700">Formatted Prompt (sent to AI model):</strong>
                            </p>
                            <pre className="bg-green-50 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-green-300 max-w-full">{step.formatted_prompt}</pre>
                          </div>
                        )}
                        {step.prompt && !step.formatted_prompt && !step.name.startsWith('exploration') && (
                          <div>
                            <p className="font-medium mt-1 text-sm sm:text-base">
                              <strong className="text-gray-700">Prompt:</strong>
                            </p>
                            <pre className="bg-gray-200 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-gray-300 max-w-full">{step.prompt}</pre>
                          </div>
                        )}
                        {step.raw_result && (
                          <div>
                            <p className="font-medium mt-1 text-sm sm:text-base">
                              <strong className="text-gray-700">Raw Result:</strong>
                            </p>
                            <pre className="bg-gray-200 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-gray-300 max-w-full">
                              {typeof step.raw_result === 'object' ? JSON.stringify(step.raw_result, null, 2) : step.raw_result}
                            </pre>
                          </div>
                        )}
                        {step.result && (
                           <div>
                            <p className="font-medium mt-1 text-sm sm:text-base">
                              <strong className="text-gray-700">Result:</strong>
                            </p>
                            <pre className="bg-gray-200 p-2 sm:p-3 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-gray-300 max-w-full">{step.result}</pre>
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
             <p className="text-gray-500 text-center p-4 text-sm sm:text-base">No pipeline steps available for this message.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default PipelineStepsModal;