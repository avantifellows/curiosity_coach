import React, { useState, useEffect } from 'react';
import { getPrompts, getPromptVersions } from '../services/api';
import { PromptSimple, PromptVersion } from '../types';

const PromptVersionsView: React.FC = () => {
  const [prompts, setPrompts] = useState<PromptSimple[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch all prompts on component mount
  useEffect(() => {
    const fetchPrompts = async () => {
      try {
        setLoading(true);
        const data = await getPrompts();
        setPrompts(data);
        setLoading(false);
      } catch (err) {
        setError('Failed to load prompts');
        setLoading(false);
      }
    };

    fetchPrompts();
  }, []);

  // Fetch versions when a prompt is selected
  const handlePromptSelect = async (promptId: string) => {
    try {
      setSelectedPrompt(promptId);
      setLoading(true);
      const data = await getPromptVersions(promptId);
      setVersions(data);
      setLoading(false);
    } catch (err) {
      setError(`Failed to load versions for prompt ${promptId}`);
      setLoading(false);
    }
  };

  // Get the active version for display highlighting
  const getActiveVersion = () => {
    if (!selectedPrompt) return null;
    
    const selected = prompts.find(p => p.id.toString() === selectedPrompt);
    return selected?.active_version_number || null;
  };

  // Get the active version number
  const activeVersionNumber = getActiveVersion();

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Prompt Versions</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 p-4 rounded mb-4">
          <p className="font-semibold text-lg mb-2">Unable to load prompts</p>
          <p className="mb-3">This may occur if:</p>
          <ul className="list-disc text-left ml-6 mb-4">
            <li>The backend server is not running</li>
            <li>No prompts have been added to the database yet</li>
            <li>There's a network connection issue</li>
          </ul>
          <p className="text-sm mb-4">{error}</p>
          <button 
            onClick={() => {
              setError(null);
              setLoading(true);
              getPrompts()
                .then(data => {
                  setPrompts(data);
                  setLoading(false);
                })
                .catch(err => {
                  setError('Failed to load prompts');
                  setLoading(false);
                });
            }} 
            className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded"
          >
            Retry
          </button>
        </div>
      )}
      
      <div className="mb-4">
        <label className="block text-gray-700 mb-2">Select Prompt:</label>
        <select 
          className="border rounded py-2 px-3 w-full"
          onChange={(e) => handlePromptSelect(e.target.value)}
          value={selectedPrompt || ''}
          disabled={loading || prompts.length === 0}
        >
          <option value="">
            {loading ? "Loading prompts..." : prompts.length === 0 ? "No prompts available" : "Select a prompt..."}
          </option>
          {prompts.map((prompt) => (
            <option key={prompt.id} value={prompt.id}>
              {prompt.name} {prompt.active_version_number ? `(v${prompt.active_version_number})` : ''}
            </option>
          ))}
        </select>
      </div>

      {loading && !error && (
        <div className="flex justify-center p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      )}

      {selectedPrompt && !loading && (
        <>
          <h3 className="text-xl font-semibold mb-2">
            Versions {activeVersionNumber ? `(Active: v${activeVersionNumber})` : ''}
          </h3>
          
          {versions.length > 0 ? (
            <div className="space-y-4">
              {versions.map((version) => (
                <div 
                  key={version.id} 
                  className={`border p-4 rounded ${version.is_active ? 'border-green-500 bg-green-50' : ''}`}
                >
                  <div className="flex justify-between mb-2">
                    <h4 className="font-bold">
                      Version {version.version_number} 
                      {version.is_active && <span className="ml-2 text-green-600">(Active)</span>}
                    </h4>
                    <span className="text-gray-500 text-sm">
                      Created: {new Date(version.created_at).toLocaleString()}
                    </span>
                  </div>
                  <pre className="bg-gray-100 p-3 rounded overflow-auto text-sm max-h-60">
                    {version.prompt_text}
                  </pre>
                </div>
              ))}
            </div>
          ) : (
            <p>No versions found for this prompt.</p>
          )}
        </>
      )}
    </div>
  );
};

export default PromptVersionsView; 