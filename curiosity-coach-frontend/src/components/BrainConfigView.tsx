import React, { useState, useEffect } from 'react';
import { CircularProgress, Button, Alert, Box, Tabs, Tab } from '@mui/material';
import { useChat } from '../context/ChatContext';
import PromptVersionsView from './PromptVersionsView';

// Set this to true to re-enable editing functionality
const ENABLE_CONFIG_EDITING = false;

interface StepConfig {
  name: string;
  enabled: boolean;
  use_conversation_history: boolean;
  is_use_conversation_history_valid: boolean;
  is_allowed_to_change_enabled: boolean;
  // [key: string]: any; // Allow other properties if any, though we primarily care about the above
}

interface BrainConfigFormData {
  steps: StepConfig[];
}

interface BrainConfigViewProps {
  isLoadingBrainConfig: boolean;
  brainConfigSchema: { // Updated to reflect the new structure
    schema?: any; // The JSON schema part
    current_values?: { // The current configuration values
      steps: StepConfig[];
    };
    // Allow other properties from the old structure for graceful degradation if needed, though we focus on new one
    [key: string]: any; 
  } | null;
  brainConfigError: string | null;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`brain-config-tabpanel-${index}`}
      aria-labelledby={`brain-config-tab-${index}`}
      {...other}
      className="py-4"
    >
      {value === index && children}
    </div>
  );
}

const BrainConfigView: React.FC<BrainConfigViewProps> = ({ 
  isLoadingBrainConfig, 
  brainConfigSchema, 
  brainConfigError 
}) => {
  const { 
    updateBrainConfig, 
    isSavingBrainConfig, 
    saveBrainConfigError: contextSaveError
  } = useChat();

  const [formData, setFormData] = useState<BrainConfigFormData>({ steps: [] });
  const [initialFormData, setInitialFormData] = useState<BrainConfigFormData>({ steps: [] });
  const [isDirty, setIsDirty] = useState(false);
  const [localSaveSuccess, setLocalSaveSuccess] = useState<string | null>(null);
  const [localSaveError, setLocalSaveError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  useEffect(() => {
    if (brainConfigSchema && brainConfigSchema.current_values && Array.isArray(brainConfigSchema.current_values.steps)) {
      const initialData = { steps: JSON.parse(JSON.stringify(brainConfigSchema.current_values.steps)) };
      setFormData(initialData);
      setInitialFormData(JSON.parse(JSON.stringify(initialData))); // Deep copy for comparison
      setIsDirty(false);
      setLocalSaveSuccess(null);
      setLocalSaveError(null);
    } else {
      // Reset if schema is not as expected or null
      setFormData({ steps: [] });
      setInitialFormData({ steps: [] });
    }
  }, [brainConfigSchema]);

  useEffect(() => {
    // Deep comparison for isDirty, formData.steps could be undefined initially or if schema is bad
    setIsDirty(JSON.stringify(formData.steps || []) !== JSON.stringify(initialFormData.steps || []));
  }, [formData, initialFormData]);

  useEffect(() => {
    if(contextSaveError) {
        setLocalSaveError(contextSaveError);
        setLocalSaveSuccess(null);
    }
  }, [contextSaveError]);

  const handleStepInputChange = (stepIndex: number, key: string, value: any) => {
    setFormData(prev => {
      const newSteps = prev.steps ? [...prev.steps] : [];
      if (newSteps[stepIndex]) {
        newSteps[stepIndex] = { ...newSteps[stepIndex], [key]: value };
      }
      return { ...prev, steps: newSteps };
    });
    setLocalSaveSuccess(null);
    setLocalSaveError(null);
  };

  const handleSave = async () => {
    setLocalSaveSuccess(null);
    setLocalSaveError(null);
    // Ensure formData (and formData.steps) is what updateBrainConfig expects
    // The backend expects the whole current_values structure or just the part that changed.
    // Assuming updateBrainConfig expects the same structure as current_values for simplicity.
    const configToSave = { steps: formData.steps };
    const success = await updateBrainConfig(configToSave); 
    if (success) {
      setLocalSaveSuccess("Configuration saved successfully!");
      // Update initialFormData to match the saved state
      setInitialFormData(JSON.parse(JSON.stringify(formData)));
      setIsDirty(false);
    }
    // No explicit 'else' needed here as contextSaveError effect handles API errors
  };

  if (isLoadingBrainConfig) {
    return (
      <div className="flex justify-center items-center h-full">
        <CircularProgress />
        <p className="ml-2 text-gray-500">Loading Brain Configuration...</p>
      </div>
    );
  }

  if (brainConfigError) {
    return (
      <div className="flex justify-center items-center h-full p-4">
        <div className="text-center text-red-500 bg-red-100 p-4 rounded shadow w-full max-w-lg">
          <p className="font-semibold text-lg mb-2">Unable to load Brain Configuration</p>
          <p className="mb-3">This may occur if:</p>
          <ul className="list-disc text-left ml-6 mb-4">
            <li>The backend server is not running</li>
            <li>The database hasn't been initialized with configuration</li>
            <li>There's a network connection issue</li>
          </ul>
          <p className="text-sm mb-4 text-gray-600">{brainConfigError}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }
  
  const currentValues = brainConfigSchema?.current_values;
  const stepSchemaDefinition = brainConfigSchema?.schema?.$defs?.StepConfig?.properties;

  if (!currentValues || !Array.isArray(currentValues.steps) || currentValues.steps.length === 0 || !stepSchemaDefinition) {
    return (
      <div className="flex justify-center items-center h-full p-4">
        <p className="text-gray-500">
          {currentValues && Array.isArray(currentValues.steps) && currentValues.steps.length === 0 
            ? "No configuration steps found."
            : "Brain configuration is not available, has an unexpected format, or no steps are defined."}
        </p>
      </div>
    );
  }

  const renderStepsConfig = () => {
    // Simplified view for display only
    if (!ENABLE_CONFIG_EDITING) {
      return (
        <div className="space-y-4">
          {currentValues.steps.map((step, index) => {
            const stepName = step.name || `Step ${index + 1}`;
            
            return (
              <div key={step.name || index} className="p-4 border rounded-md bg-gray-50">
                <h4 className="text-lg font-medium text-gray-800 capitalize">
                  {stepName.replace(/_/g, ' ')}
                </h4>
                
                <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                  <div className="flex items-center">
                    <span className="font-semibold mr-2">Status:</span>
                    <span className={`px-2 py-1 rounded ${step.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {step.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  
                  {step.is_use_conversation_history_valid && (
                    <div className="flex items-center">
                      <span className="font-semibold mr-2">Uses History:</span>
                      <span className={`px-2 py-1 rounded ${step.use_conversation_history ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}`}>
                        {step.use_conversation_history ? 'Yes' : 'No'}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    // Original editable view
    return (
      <>
        {formData.steps && formData.steps.map((step, index) => {
          const stepName = step.name || `Step ${index + 1}`;
          const enabledTitle = stepSchemaDefinition?.enabled?.title || "Enable Step";
          const enabledDescription = stepSchemaDefinition?.enabled?.description;
          const historyTitle = stepSchemaDefinition?.use_conversation_history?.title || "Use Conversation History";
          const historyDescription = stepSchemaDefinition?.use_conversation_history?.description;

          return (
            <div key={step.name || index} className="p-4 border rounded-md hover:shadow-md transition-shadow space-y-3">
              <h4 className="text-lg font-medium text-gray-800 capitalize">
                {stepSchemaDefinition?.name?.title || "Step Name"}: {stepName.replace(/_/g, ' ')}
              </h4>

              {/* Enabled Checkbox */}
              <div className="pl-4">
                <label 
                  htmlFor={`step-${index}-enabled`} 
                  className={`flex items-center ${!step.is_allowed_to_change_enabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}>
                  <input 
                    type="checkbox" 
                    id={`step-${index}-enabled`}
                    checked={!!step.enabled} // Ensure boolean
                    onChange={(e) => handleStepInputChange(index, 'enabled', e.target.checked)}
                    className="mr-3 h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded disabled:opacity-70"
                    disabled={isSavingBrainConfig || !step.is_allowed_to_change_enabled}
                  />
                  <div className="flex-grow">
                    <span className="font-medium text-gray-800">
                      {enabledTitle}
                    </span>
                    {enabledDescription && (
                      <p className="text-sm text-gray-500 mt-1">{enabledDescription}</p>
                    )}
                    {!step.is_allowed_to_change_enabled && (
                      <p className="text-xs text-amber-700 mt-1 italic">
                        (Cannot be disabled as it's essential for the flow)
                      </p>
                    )}
                  </div>
                </label>
              </div>

              {/* Use Conversation History Checkbox */}
              <div className="pl-4">
                <label 
                  htmlFor={`step-${index}-use_conversation_history`} 
                  className={`flex items-center ${!step.is_use_conversation_history_valid ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
                >
                  <input 
                    type="checkbox" 
                    id={`step-${index}-use_conversation_history`}
                    checked={!!step.use_conversation_history} // Ensure boolean
                    onChange={(e) => handleStepInputChange(index, 'use_conversation_history', e.target.checked)}
                    className="mr-3 h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded disabled:opacity-70"
                    disabled={isSavingBrainConfig || !step.is_use_conversation_history_valid}
                  />
                  <div className="flex-grow">
                    <span className="font-medium text-gray-800">
                      {historyTitle}
                    </span>
                    {historyDescription && (
                      <p className="text-sm text-gray-500 mt-1">{historyDescription}</p>
                    )}
                    {!step.is_use_conversation_history_valid && (
                      <p className="text-xs text-amber-700 mt-1 italic">
                          (Not applicable for this step)
                      </p>
                    )}
                  </div>
                </label>
              </div>
            </div>
          );
        })}
        
        {(localSaveError || localSaveSuccess) && (
          <Box mt={2} mb={2}>
            {localSaveSuccess && <Alert severity="success">{localSaveSuccess}</Alert>}
            {localSaveError && <Alert severity="error">Error: {localSaveError}</Alert>}
          </Box>
        )}

        {formData.steps && formData.steps.length > 0 && (
          <div className="mt-6 flex justify-end">
            <Button 
              variant="contained" 
              color="primary" 
              onClick={handleSave}
              disabled={!isDirty || isSavingBrainConfig}
            >
              {isSavingBrainConfig ? <CircularProgress size={24} color="inherit" /> : 'Save Changes'}
            </Button>
          </div>
        )}
      </>
    );
  };

  return (
    <div className="p-6 space-y-6 bg-white shadow rounded-lg m-4">
      <Tabs value={activeTab} onChange={handleTabChange} className="border-b">
        <Tab label="Prompt Versions" id="brain-config-tab-0" aria-controls="brain-config-tabpanel-0" />
      </Tabs>

      <TabPanel value={activeTab} index={0}>
        <PromptVersionsView />
      </TabPanel>
    </div>
  );
};

export default BrainConfigView; 