import React, { useState, useEffect } from 'react';
import { CircularProgress, Tabs, Tab } from '@mui/material';
import { useChat } from '../context/ChatContext';
import PromptVersionsView from './PromptVersionsView';

interface StepConfig {
  name: string;
  enabled: boolean;
  use_conversation_history: boolean;
  is_use_conversation_history_valid: boolean;
  is_allowed_to_change_enabled: boolean;
  // [key: string]: any; // Allow other properties if any, though we primarily care about the above
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
  const { fetchBrainConfigSchema } = useChat();

  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  useEffect(() => {
    if (brainConfigSchema === null && !isLoadingBrainConfig && !brainConfigError) {
      fetchBrainConfigSchema();
    }
  }, [brainConfigSchema, isLoadingBrainConfig, brainConfigError, fetchBrainConfigSchema]);

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