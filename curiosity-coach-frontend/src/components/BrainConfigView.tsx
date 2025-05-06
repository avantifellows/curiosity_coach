import React, { useState, useEffect, useCallback } from 'react';
import { CircularProgress, Button, Alert, Box } from '@mui/material';
import { useChat } from '../context/ChatContext';

interface BrainConfigViewProps {
  isLoadingBrainConfig: boolean;
  brainConfigSchema: any | null;
  brainConfigError: string | null;
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

  const [formData, setFormData] = useState<Record<string, any>>({});
  const [initialFormData, setInitialFormData] = useState<Record<string, any>>({});
  const [isDirty, setIsDirty] = useState(false);
  const [localSaveSuccess, setLocalSaveSuccess] = useState<string | null>(null);
  const [localSaveError, setLocalSaveError] = useState<string | null>(null);

  const getInitialDataFromSchema = useCallback((schema: any, currentValues: any) => {
    const initialData: Record<string, any> = {};
    if (schema && schema.properties) {
      Object.entries(schema.properties).forEach(([key, prop]: [string, any]) => {
        // Use current values from API if available, otherwise use schema default
        initialData[key] = currentValues && key in currentValues 
          ? currentValues[key] 
          : prop.default;
      });
    }
    return initialData;
  }, []);

  useEffect(() => {
    if (brainConfigSchema) {
      // Extract the schema and current values from the updated API response
      const schema = brainConfigSchema.schema || brainConfigSchema;
      const currentValues = brainConfigSchema.current_values || {};
      
      const initialData = getInitialDataFromSchema(schema, currentValues);
      setFormData(initialData);
      setInitialFormData(initialData); 
      setIsDirty(false);
      setLocalSaveSuccess(null);
      setLocalSaveError(null);
    }
  }, [brainConfigSchema, getInitialDataFromSchema]);

  useEffect(() => {
    setIsDirty(JSON.stringify(formData) !== JSON.stringify(initialFormData));
  }, [formData, initialFormData]);

  useEffect(() => {
    if(contextSaveError) {
        setLocalSaveError(contextSaveError);
        setLocalSaveSuccess(null);
    }
  }, [contextSaveError]);

  const handleInputChange = (key: string, value: any) => {
    setFormData(prev => ({ ...prev, [key]: value }));
    setLocalSaveSuccess(null);
    setLocalSaveError(null);
  };

  const handleSave = async () => {
    setLocalSaveSuccess(null);
    setLocalSaveError(null);
    const success = await updateBrainConfig(formData);
    if (success) {
      setLocalSaveSuccess("Configuration saved successfully!");
      setInitialFormData(formData);
      setIsDirty(false);
    } else {
    }
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
        <div className="text-center text-red-500 bg-red-100 p-3 rounded shadow">
          <p className="font-semibold">Error loading Brain Configuration:</p>
          <p>{brainConfigError}</p>
        </div>
      </div>
    );
  }
  
  // Extract schema from the response
  const schema = brainConfigSchema?.schema || brainConfigSchema;
  
  if (!brainConfigSchema || !schema || !schema.properties) {
    return (
      <div className="flex justify-center items-center h-full">
        <p className="text-gray-500">Brain configuration schema is not available or has an unexpected format.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 bg-white shadow rounded-lg m-4">
      <h3 className="text-xl font-semibold text-gray-700 border-b pb-2">Brain Configuration Settings</h3>
      {Object.entries(schema.properties).map(([key, prop]: [string, any]) => {
        let isBooleanProperty = prop.type === 'boolean';
        if (!isBooleanProperty && Array.isArray(prop.anyOf)) {
          isBooleanProperty = prop.anyOf.some((t: any) => t.type === 'boolean');
        }

        if (isBooleanProperty) {
          return (
            <div key={key} className="p-4 border rounded-md hover:shadow-md transition-shadow">
              <label htmlFor={key} className="flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  id={key} 
                  name={key} 
                  checked={formData[key] === undefined ? (prop.default === undefined ? false : prop.default) : formData[key]}
                  onChange={(e) => handleInputChange(key, e.target.checked)}
                  className="mr-3 h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded disabled:opacity-70"
                  disabled={isSavingBrainConfig}
                />
                <div className="flex-grow">
                  <span className="font-medium text-gray-800 capitalize">
                    {prop.title || key.replace(/_/g, ' ')}
                  </span>
                  {prop.description && (
                    <p className="text-sm text-gray-500 mt-1">{prop.description}</p>
                  )}
                </div>
              </label>
            </div>
          );
        }
        return (
            <div key={key} className="p-4 border rounded-md">
                <p className="font-medium text-gray-800 capitalize">{prop.title || key.replace(/_/g, ' ')}</p>
                <p className="text-sm text-gray-500 mt-1">Unsupported property type: {prop.type || (prop.anyOf ? 'anyOf structure not fully supported for non-boolean' : 'unknown')}</p>
            </div>
        );
      })}
      {Object.keys(schema.properties).length === 0 && (
        <p className="text-gray-500">No configuration properties found in the schema.</p>
      )}

      {(localSaveError || localSaveSuccess) && (
        <Box mt={2} mb={2}>
          {localSaveSuccess && <Alert severity="success">{localSaveSuccess}</Alert>}
          {localSaveError && <Alert severity="error">Error: {localSaveError}</Alert>}
        </Box>
      )}

      {Object.keys(schema.properties).length > 0 && (
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
    </div>
  );
};

export default BrainConfigView; 