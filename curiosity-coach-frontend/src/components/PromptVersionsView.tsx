import React, { useState, useEffect } from 'react';
import { getPrompts, getPromptVersions } from '../services/api';
import { Prompt, PromptSimple, PromptVersion } from '../types';

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

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Prompt Versions</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      <div className="mb-4">
        <label className="block text-gray-700 mb-2">Select Prompt:</label>
        <select 
          className="border rounded py-2 px-3 w-full"
          onChange={(e) => handlePromptSelect(e.target.value)}
          value={selectedPrompt || ''}
        >
          <option value="">Select a prompt...</option>
          {prompts.map((prompt) => (
            <option key={prompt.id} value={prompt.id}>
              {prompt.name} {prompt.active_version_number ? `(v${prompt.active_version_number})` : ''}
            </option>
          ))}
        </select>
      </div>

      {selectedPrompt && (
        <>
          <h3 className="text-xl font-semibold mb-2">Versions</h3>
          {loading ? (
            <p>Loading versions...</p>
          ) : versions.length > 0 ? (
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