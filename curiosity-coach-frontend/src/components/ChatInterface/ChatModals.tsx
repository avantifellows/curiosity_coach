import React from 'react';
import PipelineStepsModal, { PipelineStep } from '../PipelineStepsModal';
import MemoryViewModal from '../MemoryViewModal';

interface ChatModalsProps {
  // Pipeline modal props
  showPipelineModal: boolean;
  onClosePipelineModal: () => void;
  isLoadingSteps: boolean;
  pipelineError: string | null;
  pipelineSteps: PipelineStep[];
  
  // Memory modal props
  showMemoryModal: boolean;
  onCloseMemoryModal: () => void;
  isLoadingMemory: boolean;
  memoryError: string | null;
  memoryData: any;
}

const ChatModals: React.FC<ChatModalsProps> = ({
  showPipelineModal,
  onClosePipelineModal,
  isLoadingSteps,
  pipelineError,
  pipelineSteps,
  showMemoryModal,
  onCloseMemoryModal,
  isLoadingMemory,
  memoryError,
  memoryData,
}) => {
  return (
    <>
      {/* Pipeline Steps Modal */}
      <PipelineStepsModal 
        showModal={showPipelineModal}
        onClose={onClosePipelineModal}
        isLoading={isLoadingSteps}
        error={pipelineError}
        steps={pipelineSteps}
      />

      {/* Memory View Modal */}
      <MemoryViewModal
        showModal={showMemoryModal}
        onClose={onCloseMemoryModal}
        isLoading={isLoadingMemory}
        error={memoryError}
        memoryData={memoryData}
      />
    </>
  );
};

export default ChatModals;