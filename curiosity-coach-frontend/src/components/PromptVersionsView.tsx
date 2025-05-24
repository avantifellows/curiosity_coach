import React, { useState, useEffect } from 'react';
import { CircularProgress } from '@mui/material';
import {
  getPrompts,
  getPromptVersions,
  createPromptVersion,
  setActivePromptVersion
} from '../services/api';
import { PromptSimple, PromptVersion } from '../types';

const PromptVersionsView: React.FC = () => {
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeVersionId, setActiveVersionId] = useState<number | null>(null);
  
  // Editor state
  const [editedPromptText, setEditedPromptText] = useState<string>('');
  const [saving, setSaving] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load the simplified_conversation prompt on component mount
  useEffect(() => {
    const loadPrompt = async () => {
      try {
        setLoading(true);
        // Get all prompts first to find the simplified_conversation prompt
        const prompts = await getPrompts();
        const simplifiedPrompt = prompts.find((p: PromptSimple) => p.name === 'simplified_conversation');
        
        if (!simplifiedPrompt) {
          setError('Could not find the "simplified_conversation" prompt');
          setLoading(false);
          return;
        }
        
        // Set the selected prompt ID
        setSelectedPromptId(simplifiedPrompt.id.toString());
        
        // Load versions for the prompt
        const promptVersions = await getPromptVersions(simplifiedPrompt.id);
        setVersions(promptVersions);
        
        // Find active version
        const activeVersion = promptVersions.find((v: PromptVersion) => v.is_active);
        if (activeVersion) {
          setActiveVersionId(activeVersion.id);
          setEditedPromptText(activeVersion.prompt_text);
        } else if (promptVersions.length > 0) {
          // If no active version, use the latest one
          const latestVersion = promptVersions.sort((a: PromptVersion, b: PromptVersion) => 
            b.version_number - a.version_number
          )[0];
          setEditedPromptText(latestVersion.prompt_text);
        }
        
        setLoading(false);
      } catch (err) {
        setError('Failed to load the simplified_conversation prompt');
        setLoading(false);
      }
    };

    loadPrompt();
  }, []);

  // Handle saving a new version
  const handleSaveNewVersion = async () => {
    if (!selectedPromptId || !editedPromptText.trim()) {
      setSaveError('Prompt text cannot be empty');
      return;
    }

    try {
      setSaving(true);
      setSaveError(null);
      setSuccessMessage(null);
      
      // Create a new version
      const newVersion = await createPromptVersion(selectedPromptId, editedPromptText);
      console.log("New version created:", newVersion);
      
      // Set the new version as active
      await setActivePromptVersion(selectedPromptId, newVersion.id);
      
      // Refresh the versions list
      const updatedVersions = await getPromptVersions(selectedPromptId);
      setVersions(updatedVersions);
      
      // Make sure to update the active version ID in state
      setActiveVersionId(newVersion.id);
      
      setSuccessMessage(`New version ${newVersion.version_number} created and set as active`);
      setSaving(false);
    } catch (err) {
      setSaveError('Failed to save new version');
      setSaving(false);
    }
  };

  // Handle setting a version as active
  const handleSetActiveVersion = async (versionId: number) => {
    if (!selectedPromptId) return;
    
    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);
      
      await setActivePromptVersion(selectedPromptId, versionId);
      
      // Update the versions list
      const updatedVersions = await getPromptVersions(selectedPromptId);
      setVersions(updatedVersions);
      
      // Update the active version
      const newActiveVersion = updatedVersions.find((v: PromptVersion) => v.id === versionId);
      if (newActiveVersion) {
        setActiveVersionId(versionId); // Set this explicitly to the selected version ID
        setEditedPromptText(newActiveVersion.prompt_text);
      }
      
      setSuccessMessage(`Version ${newActiveVersion?.version_number} set as active`);
      setLoading(false);
    } catch (err) {
      setError('Failed to set version as active');
      setLoading(false);
    }
  };

  return (
    <div className="p-2 sm:p-4 max-w-full">
      <h2 className="text-xl font-bold mb-4">Simplified Conversation Prompt Editor</h2>
      
      {/* Error message */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 p-3 sm:p-4 rounded mb-4">
          <p className="font-bold text-sm sm:text-base">Error: {error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="mt-2 bg-red-500 hover:bg-red-600 text-white font-semibold py-1 px-3 rounded text-sm"
          >
            Retry
          </button>
        </div>
      )}
      
      {/* Success message */}
      {successMessage && (
        <div className="bg-green-100 border border-green-400 text-green-700 p-3 sm:p-4 rounded mb-4">
          <p className="font-bold text-sm sm:text-base">{successMessage}</p>
          <button 
            onClick={() => setSuccessMessage(null)} 
            className="mt-2 bg-green-500 hover:bg-green-600 text-white font-semibold py-1 px-3 rounded text-sm"
          >
            Dismiss
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center p-4">
          <CircularProgress size={24} />
          <span className="ml-2 text-sm sm:text-base">Loading...</span>
        </div>
      ) : (
        <>
          {/* Version selector */}
          <div className="mb-4">
            <label className="block text-gray-700 mb-2 font-medium text-sm sm:text-base">Version:</label>
            <select
              className="border rounded py-2 px-3 w-full text-sm sm:text-base"
              onChange={(e) => {
                const versionId = parseInt(e.target.value);
                const selectedVersion = versions.find((v: PromptVersion) => v.id === versionId);
                if (selectedVersion) {
                  setEditedPromptText(selectedVersion.prompt_text);
                  // If not already active, set as active
                  if (!selectedVersion.is_active) {
                    handleSetActiveVersion(versionId);
                  } else {
                    setActiveVersionId(versionId);
                  }
                }
              }}
              value={activeVersionId || ''}
              disabled={loading || saving || versions.length === 0}
            >
              <option value="">Select a version</option>
              {versions.map((version) => (
                <option key={version.id} value={version.id}>
                  Version {version.version_number} {version.is_active ? '(Active)' : ''}
                </option>
              ))}
            </select>
          </div>
          
          {/* Code editor */}
          <div className="mb-4">
            <label className="block text-gray-700 mb-2 font-medium text-sm sm:text-base">Prompt Text:</label>
            <textarea
              className="border rounded py-2 px-3 w-full h-64 sm:h-80 resize-none font-mono text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              value={editedPromptText}
              onChange={(e) => setEditedPromptText(e.target.value)}
              placeholder="Enter prompt text here..."
              disabled={saving}
            />
          </div>
          
          {/* Save error message */}
          {saveError && (
            <div className="bg-red-100 border border-red-400 text-red-700 p-3 sm:p-4 rounded mb-4">
              <p className="font-bold text-sm sm:text-base">Save Error: {saveError}</p>
            </div>
          )}
          
          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-3 sm:gap-0 sm:space-x-4">
            <button
              onClick={handleSaveNewVersion}
              disabled={saving || !editedPromptText.trim()}
              className="flex-1 sm:flex-none bg-indigo-500 hover:bg-indigo-600 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded text-sm sm:text-base disabled:cursor-not-allowed"
            >
              {saving ? (
                <div className="flex items-center justify-center">
                  <CircularProgress size={16} color="inherit" className="mr-2" />
                  Saving...
                </div>
              ) : (
                'Save as New Version'
              )}
            </button>
            
            <button
              onClick={() => {
                if (activeVersionId) {
                  const activeVersion = versions.find((v: PromptVersion) => v.id === activeVersionId);
                  if (activeVersion) {
                    setEditedPromptText(activeVersion.prompt_text);
                  }
                }
              }}
              disabled={saving}
              className="flex-1 sm:flex-none bg-gray-500 hover:bg-gray-600 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded text-sm sm:text-base disabled:cursor-not-allowed"
            >
              Reset to Active Version
            </button>
          </div>
          
          {/* Version history */}
          {versions.length > 0 && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold mb-3 text-sm sm:text-lg">Version History:</h3>
              <div className="space-y-2">
                {versions
                  .sort((a: PromptVersion, b: PromptVersion) => b.version_number - a.version_number)
                  .map((version) => (
                    <div
                      key={version.id}
                      className={`border rounded p-3 ${
                        version.is_active ? 'border-green-500 bg-green-50' : 'border-gray-300'
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center">
                        <div className="mb-2 sm:mb-0">
                          <span className="font-medium text-sm sm:text-base">
                            Version {version.version_number}
                          </span>
                          {version.is_active && (
                            <span className="ml-2 bg-green-500 text-white px-2 py-1 rounded text-xs">
                              Active
                            </span>
                          )}
                        </div>
                        <div className="text-xs sm:text-sm text-gray-500">
                          Created: {new Date(version.created_at).toLocaleString()}
                        </div>
                      </div>
                      {!version.is_active && (
                        <button
                          onClick={() => handleSetActiveVersion(version.id)}
                          disabled={loading || saving}
                          className="mt-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white font-semibold py-1 px-3 rounded text-xs sm:text-sm disabled:cursor-not-allowed"
                        >
                          Set as Active
                        </button>
                      )}
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default PromptVersionsView; 