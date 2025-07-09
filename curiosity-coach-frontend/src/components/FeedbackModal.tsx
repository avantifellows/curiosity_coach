import React, { useState } from 'react';
import { submitFeedback } from '../services/api';

// Emoji Rating Component
const EmojiRating: React.FC<{
  question: string;
  value: number;
  onChange: (value: number) => void;
}> = ({ question, value, onChange }) => {
  const emojis = ['😠', '😟', '😐', '😊', '🤩'];
  return (
    <div className="mb-6">
      <label className="block text-gray-700 text-sm font-bold mb-2">{question}</label>
      <div className="flex justify-between">
        {emojis.map((emoji, index) => (
          <button
            key={index}
            type="button"
            onClick={() => onChange(index + 1)}
            className={`text-3xl p-2 rounded-full transition-all duration-200 ${
              value === index + 1 ? 'transform scale-125' : 'grayscale hover:grayscale-0'
            }`}
          >
            {emoji}
          </button>
        ))}
      </div>
    </div>
  );
};

// Main Feedback Modal Component
interface FeedbackModalProps {
  open: boolean;
  onClose: () => void;
}

const FeedbackModal: React.FC<FeedbackModalProps> = ({ open, onClose }) => {
  const [formState, setFormState] = useState({
    'How curious do you feel now?': 0,
    'How easy was the application to use?': 0,
    'What surprised you most today?': '',
    'Were you frustrated at any point? What would you change/include?': '',
    'Would you recommend it to someone?': '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showThankYou, setShowThankYou] = useState(false);

  const handleRatingChange = (question: string, value: number) => {
    setFormState(prev => ({ ...prev, [question]: value }));
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormState(prev => ({ ...prev, [name]: value }));
  };
  
  const handleRadioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormState(prev => ({...prev, [name]: value}));
  };

  const isFormComplete = () => {
    return (
      formState['How curious do you feel now?'] > 0 &&
      formState['How easy was the application to use?'] > 0 &&
      formState['Would you recommend it to someone?'] !== ''
    );
  };

  const resetForm = () => {
    setFormState({
      'How curious do you feel now?': 0,
      'How easy was the application to use?': 0,
      'What surprised you most today?': '',
      'Were you frustrated at any point? What would you change/include?': '',
      'Would you recommend it to someone?': '',
    });
    setError('');
    setShowThankYou(false);
  };

  const handleSubmit = async () => {
    if (!isFormComplete()) {
      setError('Please fill out all required fields (ratings and recommendation).');
      return;
    }
    setError('');
    setIsSubmitting(true);
    try {
      await submitFeedback(formState);
      setShowThankYou(true); // Show thank you message on success
    } catch (err: any) {
      setError(err.message || 'Failed to submit feedback.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 z-50 flex justify-center items-center p-4">
      <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-lg max-h-full overflow-y-auto">
        {showThankYou ? (
          <div className="p-8">
            <div className="text-center">
              <div className="text-6xl mb-4">🎉</div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Thank You!</h2>
              <p className="text-gray-600 mb-6">Your feedback helps us improve.</p>
            </div>
            <div className="mt-6 flex justify-center">
              <button onClick={handleClose} className="new-chat-btn w-auto">
                Close
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-800">Share Your Feedback</h2>
              <button onClick={handleClose} className="text-gray-500 hover:text-gray-800 text-3xl">&times;</button>
            </div>

            <form>
                <EmojiRating
                    question="How curious do you feel now?"
                    value={formState['How curious do you feel now?']}
                    onChange={value => handleRatingChange('How curious do you feel now?', value)}
                />
                <EmojiRating
                    question="How easy was the application to use?"
                    value={formState['How easy was the application to use?']}
                    onChange={value => handleRatingChange('How easy was the application to use?', value)}
                />
                
                <div className="mb-6">
                    <label htmlFor="surprised" className="block text-gray-700 text-sm font-bold mb-2">What surprised you most today?</label>
                    <textarea id="surprised" name="What surprised you most today?" value={formState['What surprised you most today?']} onChange={handleTextChange} className="form-textarea w-full" rows={3}></textarea>
                </div>
                
                <div className="mb-6">
                    <label htmlFor="frustrated" className="block text-gray-700 text-sm font-bold mb-2">Were you frustrated at any point? What would you change/include?</label>
                    <textarea id="frustrated" name="Were you frustrated at any point? What would you change/include?" value={formState['Were you frustrated at any point? What would you change/include?']} onChange={handleTextChange} className="form-textarea w-full" rows={3}></textarea>
                </div>
                
                <div className="mb-6">
                    <label className="block text-gray-700 text-sm font-bold mb-2">Would you recommend it to someone?</label>
                    <div className="flex items-center space-x-4">
                        <label className="flex items-center"><input type="radio" name="Would you recommend it to someone?" value="Yes" checked={formState['Would you recommend it to someone?'] === 'Yes'} onChange={handleRadioChange} className="form-radio" /> <span className="ml-2">Yes</span></label>
                        <label className="flex items-center"><input type="radio" name="Would you recommend it to someone?" value="No" checked={formState['Would you recommend it to someone?'] === 'No'} onChange={handleRadioChange} className="form-radio" /> <span className="ml-2">No</span></label>
                        <label className="flex items-center"><input type="radio" name="Would you recommend it to someone?" value="Maybe" checked={formState['Would you recommend it to someone?'] === 'Maybe'} onChange={handleRadioChange} className="form-radio" /> <span className="ml-2">Maybe</span></label>
                    </div>
                </div>

            </form>

            {error && <p className="text-red-500 text-sm my-2">{error}</p>}
            
            <div className="mt-6 flex justify-end">
              <button
                onClick={handleSubmit}
                className="new-chat-btn w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed disabled:scale-100"
                disabled={isSubmitting || !isFormComplete()}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default FeedbackModal; 