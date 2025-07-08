import React, { useState } from 'react';
import { submitFeedback } from '../services/api';

interface FeedbackModalProps {
  open: boolean;
  onClose: () => void;
}

const FeedbackModal: React.FC<FeedbackModalProps> = ({ open, onClose }) => {
  const [thumbsUp, setThumbsUp] = useState<boolean | null>(null);
  const [feedbackText, setFeedbackText] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (thumbsUp === null) {
      setError('Please select thumbs up or thumbs down.');
      return;
    }
    setError('');
    setIsSubmitting(true);
    try {
      await submitFeedback(thumbsUp, feedbackText);
      handleClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit feedback.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setThumbsUp(null);
    setFeedbackText('');
    setError('');
    onClose();
  };

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-center">
      <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Give Feedback</h2>
          <button onClick={handleClose} className="text-gray-500 hover:text-gray-800">&times;</button>
        </div>
        
        <p className="mb-4">Liked it? Let us know!</p>
        
        <div className="flex justify-center items-center space-x-8 mb-6">
          <button
            onClick={() => setThumbsUp(true)}
            className={`text-4xl p-3 border rounded-full transition-all duration-200 flex items-center justify-center
              ${
                thumbsUp === true
                  ? 'scale-110 border-blue-500 bg-blue-100' // Selected state
                  : 'grayscale hover:grayscale-0 hover:scale-110 border-gray-300' // Unselected state
              }`}
          >
            👍
          </button>
          <button
            onClick={() => setThumbsUp(false)}
            className={`text-4xl p-3 border rounded-full transition-all duration-200 flex items-center justify-center
              ${
                thumbsUp === false
                  ? 'scale-110 border-red-500 bg-red-100' // Selected state
                  : 'grayscale hover:grayscale-0 hover:scale-110 border-gray-300' // Unselected state
              }`}
          >
            👎
          </button>
        </div>
        
        <textarea
          className="w-full p-2 border rounded-md"
          rows={4}
          placeholder="Tell us more... (optional)"
          value={feedbackText}
          onChange={(e) => setFeedbackText(e.target.value)}
        />
        
        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        
        <div className="mt-6 flex justify-end">
          <button
            onClick={handleSubmit}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded transition-colors duration-200 disabled:bg-blue-300 disabled:cursor-not-allowed"
            disabled={isSubmitting || thumbsUp === null}
          >
            {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FeedbackModal; 