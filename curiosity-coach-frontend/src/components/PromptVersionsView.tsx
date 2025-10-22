import React, { useState, useEffect, useRef } from 'react';
import { CircularProgress, Chip, Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, MenuItem, Select, FormControl, InputLabel, FormHelperText } from '@mui/material';
import {
  getPrompts,
  getPromptVersions,
  createPromptVersion,
  setActivePromptVersion,
  setProductionPromptVersion,
  unsetProductionPromptVersion,
  createPrompt,
  updatePrompt
} from '../services/api';
import { PromptSimple, PromptVersion } from '../types';
import { PlaceholderSelector } from './PlaceholderSelector';

interface PromptFormData {
  name: string;
  description: string;
  prompt_purpose: string | null;
}

const PromptVersionsView: React.FC = () => {
  const [prompts, setPrompts] = useState<PromptSimple[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptSimple | null>(null);
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeVersionId, setActiveVersionId] = useState<number | null>(null);
  
  // Editor state
  const [editedPromptText, setEditedPromptText] = useState<string>('');
  const [saving, setSaving] = useState<boolean>(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Create/Edit prompt dialog state
  const [showPromptDialog, setShowPromptDialog] = useState<boolean>(false);
  const [promptFormData, setPromptFormData] = useState<PromptFormData>({
    name: '',
    description: '',
    prompt_purpose: null
  });
  const [editingPromptId, setEditingPromptId] = useState<number | null>(null);

  // Load all prompts on component mount
  useEffect(() => {
    loadPrompts();
  }, []);

  // Debug: Log whenever activeVersionId changes
  useEffect(() => {
    console.log(`[StateUpdate] activeVersionId changed to: ${activeVersionId}`);
  }, [activeVersionId]);

  // Debug: Log whenever versions array changes
  useEffect(() => {
    console.log(`[StateUpdate] versions array updated, length: ${versions.length}`);
  }, [versions]);

  const loadPrompts = async () => {
    try {
      setLoading(true);
      const promptsData = await getPrompts();
      setPrompts(promptsData);
      
      // Auto-select simplified_conversation prompt if available
      const simplifiedPrompt = promptsData.find((p: PromptSimple) => p.name === 'simplified_conversation');
      if (simplifiedPrompt) {
        await selectPrompt(simplifiedPrompt);
      }
      
      setLoading(false);
    } catch (err) {
      setError('Failed to load prompts');
      setLoading(false);
    }
  };

  const selectPrompt = async (prompt: PromptSimple) => {
    try {
      setLoading(true);
      setSelectedPrompt(prompt);
      
      // Load versions for the prompt
      const promptVersions = await getPromptVersions(prompt.id);
      console.log(`[SelectPrompt] Loaded ${promptVersions.length} versions for prompt ${prompt.name}:`);
      console.log(`[SelectPrompt] Versions array:`, promptVersions);
      
      // Log each version's details
      promptVersions.forEach((v: PromptVersion, index: number) => {
        console.log(`[SelectPrompt] Version ${index}: id=${v.id}, version_number=${v.version_number}, is_active=${v.is_active}, is_production=${v.is_production}`);
      });
      
      setVersions(promptVersions);
      
      // Find active version
      const activeVersion = promptVersions.find((v: PromptVersion) => v.is_active);
      if (activeVersion) {
        console.log(`[SelectPrompt] Found active version, setting activeVersionId to ${activeVersion.id} (v${activeVersion.version_number})`);
        setActiveVersionId(activeVersion.id);
        setEditedPromptText(activeVersion.prompt_text);
      } else if (promptVersions.length > 0) {
        // If no active version, use the latest one
        const latestVersion = promptVersions.sort((a: PromptVersion, b: PromptVersion) => 
          b.version_number - a.version_number
        )[0];
        console.log(`[SelectPrompt] No active version found, using latest version ${latestVersion.id} (v${latestVersion.version_number})`);
        setActiveVersionId(latestVersion.id);
        setEditedPromptText(latestVersion.prompt_text);
      } else {
        console.log(`[SelectPrompt] No versions found at all!`);
      }
      
      console.log(`[SelectPrompt] Final state - activeVersionId: ${activeVersionId}`);
      
      setLoading(false);
    } catch (err) {
      console.error(`[SelectPrompt] Error loading versions for prompt ${prompt.name}:`, err);
      setError(`Failed to load versions for prompt ${prompt.name}`);
      setLoading(false);
    }
  };

  // Handle saving a new version
  const handleSaveNewVersion = async () => {
    if (!selectedPrompt || !editedPromptText.trim()) {
      setSaveError('Prompt text cannot be empty');
      return;
    }

    try {
      setSaving(true);
      setSaveError(null);
      setSuccessMessage(null);
      
      // Create a new version
      const newVersion = await createPromptVersion(selectedPrompt.id, editedPromptText);
      
      // Set the new version as active
      await setActivePromptVersion(selectedPrompt.id, newVersion.id);
      
      // Refresh the versions list
      const updatedVersions = await getPromptVersions(selectedPrompt.id);
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
    if (!selectedPrompt) return;
    
    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);
      
      await setActivePromptVersion(selectedPrompt.id, versionId);
      
      // Update the versions list
      const updatedVersions = await getPromptVersions(selectedPrompt.id);
      setVersions(updatedVersions);
      
      // Update the active version
      const newActiveVersion = updatedVersions.find((v: PromptVersion) => v.id === versionId);
      if (newActiveVersion) {
        setActiveVersionId(versionId);
        setEditedPromptText(newActiveVersion.prompt_text);
      }
      
      setSuccessMessage(`Version ${newActiveVersion?.version_number} set as active`);
      setLoading(false);
    } catch (err) {
      setError('Failed to set version as active');
      setLoading(false);
    }
  };

  // Handle setting a version as production
  const handleSetProductionVersion = async (version: PromptVersion) => {
    if (!selectedPrompt) return;
    
    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);
      
      await setProductionPromptVersion(selectedPrompt.id, version.version_number);
      
      // Update the versions list
      const updatedVersions = await getPromptVersions(selectedPrompt.id);
      setVersions(updatedVersions);
      
      setSuccessMessage(`Version ${version.version_number} set as PRODUCTION`);
      setLoading(false);
    } catch (err) {
      setError('Failed to set version as production');
      setLoading(false);
    }
  };

  // Handle unsetting production flag
  const handleUnsetProductionVersion = async (version: PromptVersion) => {
    if (!selectedPrompt) return;
    
    try {
      setLoading(true);
      setError(null);
      setSuccessMessage(null);
      
      await unsetProductionPromptVersion(selectedPrompt.id, version.version_number);
      
      // Update the versions list
      const updatedVersions = await getPromptVersions(selectedPrompt.id);
      setVersions(updatedVersions);
      
      setSuccessMessage(`Version ${version.version_number} removed from PRODUCTION`);
      setLoading(false);
    } catch (err) {
      setError('Failed to unset production version');
      setLoading(false);
    }
  };

  // Handle opening create prompt dialog
  const handleOpenCreateDialog = () => {
    setPromptFormData({
      name: '',
      description: '',
      prompt_purpose: null
    });
    setEditingPromptId(null);
    setShowPromptDialog(true);
  };

  // Handle opening edit prompt dialog
  const handleOpenEditDialog = (prompt: PromptSimple) => {
    setPromptFormData({
      name: prompt.name,
      description: prompt.description || '',
      prompt_purpose: prompt.prompt_purpose
    });
    setEditingPromptId(prompt.id);
    setShowPromptDialog(true);
  };

  // Handle saving prompt (create or update)
  const handleSavePrompt = async () => {
    if (!promptFormData.name.trim()) {
      setSaveError('Prompt name cannot be empty');
      return;
    }

    try {
      setSaving(true);
      setSaveError(null);
      
      if (editingPromptId) {
        // Update existing prompt
        await updatePrompt(
          editingPromptId,
          promptFormData.name,
          promptFormData.description,
          promptFormData.prompt_purpose
        );
        setSuccessMessage('Prompt updated successfully');
      } else {
        // Create new prompt
        await createPrompt(
          promptFormData.name,
          promptFormData.description,
          promptFormData.prompt_purpose
        );
        setSuccessMessage('Prompt created successfully');
      }
      
      // Reload prompts
      await loadPrompts();
      setShowPromptDialog(false);
      setSaving(false);
    } catch (err) {
      setSaveError(editingPromptId ? 'Failed to update prompt' : 'Failed to create prompt');
      setSaving(false);
    }
  };

  // Get purpose label
  const getPurposeLabel = (purpose: string | null): string => {
    if (!purpose) return 'General';
    switch (purpose) {
      case 'visit_1': return 'Visit 1';
      case 'visit_2': return 'Visit 2';
      case 'visit_3': return 'Visit 3';
      case 'steady_state': return 'Steady State';
      case 'general': return 'General';
      default: return purpose;
    }
  };

  // Get purpose chip color
  const getPurposeColor = (purpose: string | null): 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info' | 'default' => {
    if (!purpose) return 'default';
    switch (purpose) {
      case 'visit_1': return 'info';
      case 'visit_2': return 'primary';
      case 'visit_3': return 'secondary';
      case 'steady_state': return 'success';
      case 'general': return 'default';
      default: return 'default';
    }
  };

  // Handle inserting placeholder at cursor position
  const handlePlaceholderInsert = (placeholder: string) => {
    const textarea = textareaRef.current;
    if (!textarea) {
      // Fallback: append to end
      setEditedPromptText(prev => prev + ' ' + placeholder);
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = editedPromptText;

    // Insert placeholder at cursor position
    const newText = text.substring(0, start) + placeholder + text.substring(end);
    setEditedPromptText(newText);

    // Set cursor position after inserted placeholder
    setTimeout(() => {
      textarea.focus();
      textarea.selectionStart = textarea.selectionEnd = start + placeholder.length;
    }, 0);
  };

  return (
    <div className="p-2 sm:p-4 max-w-full">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Prompt Management</h2>
        <button
          onClick={handleOpenCreateDialog}
          className="bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-4 rounded text-sm"
        >
          + Create New Prompt
        </button>
      </div>
      
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

      {loading && !selectedPrompt ? (
        <div className="flex justify-center p-4">
          <CircularProgress size={24} />
          <span className="ml-2 text-sm sm:text-base">Loading prompts...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Prompt list */}
          <div className="lg:col-span-1 border rounded p-4">
            <h3 className="text-lg font-semibold mb-3">Prompts</h3>
            <div className="space-y-2">
              {prompts.map((prompt) => (
                <div
                  key={prompt.id}
                  className={`border rounded p-3 cursor-pointer transition-colors ${
                    selectedPrompt?.id === prompt.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-300 hover:border-blue-300 hover:bg-gray-50'
                  }`}
                  onClick={() => selectPrompt(prompt)}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="font-medium text-sm">{prompt.name}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenEditDialog(prompt);
                      }}
                      className="text-blue-500 hover:text-blue-700 text-xs"
                    >
                      Edit
                    </button>
                  </div>
                  {prompt.description && (
                    <p className="text-xs text-gray-600 mb-2">{prompt.description}</p>
                  )}
                  <Chip
                    label={getPurposeLabel(prompt.prompt_purpose)}
                    color={getPurposeColor(prompt.prompt_purpose)}
                    size="small"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Prompt editor */}
          <div className="lg:col-span-2">
            {selectedPrompt ? (
              <>
                <div className="mb-4 flex justify-between items-center">
                  <div>
                    <h3 className="text-lg font-semibold">{selectedPrompt.name}</h3>
                    {selectedPrompt.description && (
                      <p className="text-sm text-gray-600">{selectedPrompt.description}</p>
                    )}
                  </div>
                  <Chip
                    label={getPurposeLabel(selectedPrompt.prompt_purpose)}
                    color={getPurposeColor(selectedPrompt.prompt_purpose)}
                    size="small"
                  />
                </div>

                {/* Version selector */}
                <div className="mb-4">
                  <label className="block text-gray-700 mb-2 font-medium text-sm sm:text-base">Version:</label>
                  <select
                    className="border rounded py-2 px-3 w-full text-sm sm:text-base"
                    onChange={(e) => {
                      console.log(`[VersionDropdown] onChange triggered, selected value: ${e.target.value}`);
                      const versionId = parseInt(e.target.value);
                      const selectedVersion = versions.find((v: PromptVersion) => v.id === versionId);
                      console.log(`[VersionDropdown] Found selected version:`, selectedVersion);
                      if (selectedVersion) {
                        setEditedPromptText(selectedVersion.prompt_text);
                        // If not already active, set as active
                        if (!selectedVersion.is_active) {
                          console.log(`[VersionDropdown] Version ${versionId} is not active, setting as active`);
                          handleSetActiveVersion(versionId);
                        } else {
                          console.log(`[VersionDropdown] Version ${versionId} is already active, just updating state`);
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
                        Version {version.version_number} {version.is_active ? '(Active)' : ''} {version.is_production ? '(PRODUCTION)' : ''}
                      </option>
                    ))}
                  </select>
                  {/* Debug info */}
                  <div className="text-xs text-gray-500 mt-1">
                    Debug: activeVersionId = {activeVersionId || 'null'}, versions.length = {versions.length}, 
                    disabled = {String(loading || saving || versions.length === 0)}
                  </div>
                </div>
                
                {/* Code editor */}
                <div className="mb-4">
                  <label className="block text-gray-700 mb-2 font-medium text-sm sm:text-base">Prompt Text:</label>
                  <textarea
                    ref={textareaRef}
                    className="border rounded py-2 px-3 w-full h-64 sm:h-80 resize-none font-mono text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    value={editedPromptText}
                    onChange={(e) => setEditedPromptText(e.target.value)}
                    placeholder="Enter prompt text here..."
                    disabled={saving}
                  />
                </div>

                {/* Placeholder Selector */}
                <div className="mb-4 border rounded p-4 bg-gray-50">
                  <h4 className="text-sm font-semibold mb-3 text-gray-700">Insert Placeholder:</h4>
                  <PlaceholderSelector
                    onPlaceholderSelect={handlePlaceholderInsert}
                    className="text-sm"
                  />
                  <p className="text-xs text-gray-500 mt-3">
                    <strong>Tip:</strong> Position your cursor in the text area above where you want to insert the placeholder, then click "Use This Placeholder".
                  </p>
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
                    <h3 className="text-sm sm:text-lg font-semibold mb-3">Version History:</h3>
                    <div className="space-y-2">
                      {versions
                        .sort((a: PromptVersion, b: PromptVersion) => b.version_number - a.version_number)
                        .map((version) => (
                          <div
                            key={version.id}
                            className={`border rounded p-3 ${
                              version.is_production ? 'border-blue-500 bg-blue-50' :
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
                                {version.is_production && (
                                  <span className="ml-2 bg-blue-600 text-white px-2 py-1 rounded text-xs font-semibold">
                                    PRODUCTION
                                  </span>
                                )}
                              </div>
                              <div className="text-xs sm:text-sm text-gray-500">
                                Created: {new Date(version.created_at).toLocaleString()}
                              </div>
                            </div>
                            <div className="flex flex-wrap gap-2 mt-2">
                              {!version.is_active && (
                                <button
                                  onClick={() => handleSetActiveVersion(version.id)}
                                  disabled={loading || saving}
                                  className="bg-green-500 hover:bg-green-600 disabled:bg-gray-400 text-white font-semibold py-1 px-3 rounded text-xs sm:text-sm disabled:cursor-not-allowed"
                                >
                                  Set as Active
                                </button>
                              )}
                              {!version.is_production && (
                                <button
                                  onClick={() => handleSetProductionVersion(version)}
                                  disabled={loading || saving}
                                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-1 px-3 rounded text-xs sm:text-sm disabled:cursor-not-allowed"
                                >
                                  Set as Production
                                </button>
                              )}
                              {version.is_production && (
                                <button
                                  onClick={() => handleUnsetProductionVersion(version)}
                                  disabled={loading || saving}
                                  className="bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white font-semibold py-1 px-3 rounded text-xs sm:text-sm disabled:cursor-not-allowed"
                                >
                                  Unset Production
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="flex justify-center items-center h-full text-gray-500">
                <p>Select a prompt to view and edit versions</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create/Edit Prompt Dialog */}
      <Dialog open={showPromptDialog} onClose={() => setShowPromptDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingPromptId ? 'Edit Prompt' : 'Create New Prompt'}</DialogTitle>
        <DialogContent>
          <TextField
            label="Prompt Name"
            fullWidth
            margin="normal"
            value={promptFormData.name}
            onChange={(e) => setPromptFormData({ ...promptFormData, name: e.target.value })}
            required
            helperText="Unique identifier for this prompt"
          />
          
          <TextField
            label="Description"
            fullWidth
            margin="normal"
            multiline
            rows={2}
            value={promptFormData.description}
            onChange={(e) => setPromptFormData({ ...promptFormData, description: e.target.value })}
            helperText="Optional description of what this prompt does"
          />
          
          <FormControl fullWidth margin="normal">
            <InputLabel>Prompt Purpose</InputLabel>
            <Select
              value={promptFormData.prompt_purpose || ''}
              onChange={(e) => setPromptFormData({ ...promptFormData, prompt_purpose: e.target.value || null })}
            >
              <MenuItem value="">None (General)</MenuItem>
              <MenuItem value="visit_1">Visit 1 - First Time User</MenuItem>
              <MenuItem value="visit_2">Visit 2 - Second Visit</MenuItem>
              <MenuItem value="visit_3">Visit 3 - Third Visit</MenuItem>
              <MenuItem value="steady_state">Steady State - 4+ Visits</MenuItem>
              <MenuItem value="general">General Purpose</MenuItem>
            </Select>
            <FormHelperText>
              Select the visit type this prompt should be used for. Leave empty for general prompts.
            </FormHelperText>
          </FormControl>
          
          {saveError && (
            <div className="bg-red-100 border border-red-400 text-red-700 p-3 rounded mt-4">
              <p className="text-sm">{saveError}</p>
            </div>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowPromptDialog(false)} disabled={saving}>
            Cancel
          </Button>
          <Button 
            onClick={handleSavePrompt} 
            color="primary" 
            variant="contained"
            disabled={saving || !promptFormData.name.trim()}
          >
            {saving ? 'Saving...' : (editingPromptId ? 'Update' : 'Create')}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default PromptVersionsView;
