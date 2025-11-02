import React from 'react';
import { createPortal } from 'react-dom';
import { CircularProgress } from '@mui/material';

interface MemoryViewModalProps {
  showModal: boolean;
  onClose: () => void;
  isLoading: boolean;
  error: string | null;
  memoryData: any; // The conversation memory data
}

const MemoryViewModal: React.FC<MemoryViewModalProps> = ({
  showModal,
  onClose,
  isLoading,
  error,
  memoryData,
}) => {
  if (!showModal) {
    return null;
  }

  const memoryJson = memoryData ? JSON.stringify(memoryData, null, 2) : "No memory data available.";

  return createPortal(
    <div 
      className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex justify-center items-start sm:items-center z-50 p-2 sm:p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="relative border w-full max-w-4xl shadow-lg rounded-md bg-white mt-4 sm:mt-0 max-h-[90vh] sm:max-h-[85vh] flex flex-col">
        <div className="flex justify-between items-center p-4 sm:p-5 border-b border-gray-200 flex-shrink-0">
          <h3 className="text-lg sm:text-xl font-medium text-gray-900">
            {error ? 'Error' : 'AI-Generated Conversation Memory'}
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
              <p className="ml-2 text-sm sm:text-base">Loading memory...</p>
            </div>
          )}

          {error && (
            <div className="p-3 sm:p-4 bg-red-100 text-red-700 rounded">
              <p className="text-sm sm:text-base"><strong>Error:</strong> {error}</p>
            </div>
          )}

          {!isLoading && !error && (
            <div className="text-sm sm:text-base text-gray-700">
                <pre className="bg-gray-100 p-3 sm:p-4 rounded text-xs sm:text-sm overflow-x-auto whitespace-pre-wrap border border-gray-200 max-w-full">
                  {memoryJson}
                </pre>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default MemoryViewModal; 