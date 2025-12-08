import React from 'react';

interface AnalysisLoadingProps {
  message?: string;
  videoPath?: string;
}

const AnalysisLoading: React.FC<AnalysisLoadingProps> = ({ 
  message = "The deep analysis takes a minute or 2...",
  videoPath = "/analysis-loading.mp4"
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="max-w-md w-full space-y-6">
        {/* Video Container */}
        <div className="relative w-full aspect-video rounded-lg overflow-hidden bg-slate-100 shadow-lg">
          <video
            autoPlay
            loop
            muted
            playsInline
            className="w-full h-full object-cover"
          >
            <source src={videoPath} type="video/mp4" />
            {/* Fallback if video doesn't load */}
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent"></div>
            </div>
          </video>
        </div>
        
        {/* Message Text */}
        <div className="text-center">
          <p className="text-lg font-medium text-slate-700 animate-pulse">
            {message}
          </p>
        </div>
      </div>
    </div>
  );
};

export default AnalysisLoading;

