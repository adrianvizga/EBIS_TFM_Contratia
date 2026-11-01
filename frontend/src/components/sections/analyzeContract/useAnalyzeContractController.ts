import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../../context/useLanguage';
import { useNotifications } from '../../../context/useNotifications';
import { useUser } from '../../../context/useUser';
import { useAuthFetch } from '../../../hooks/useAuthFetch';
import { useUsage } from '../../../hooks/useUsage';
import type { AnalyzedContract } from './types';
import { applyStreamEvent, filterContracts, getFilenameParts, ITEMS_PER_PAGE, paginateContracts } from './transformations';
import { createContractAnalysisPdf } from './pdfService';
import {
  createNotification,
  createTokenNotification,
  deleteContractRequest,
  getContractAnalysis,
  listContracts,
  retryContractAnalysis,
  streamContractEvents,
  uploadContract,
} from './api';

export function useAnalyzeContractController() {
  const { t, language } = useLanguage();
  const { refreshNotifications } = useNotifications();
  const { token } = useUser();
  const authFetch = useAuthFetch();
  const navigate = useNavigate();
  const { usage, remainingAnalyses, refresh: refreshUsage } = useUsage();
  const [isDragging, setIsDragging] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [contractToDelete, setContractToDelete] = useState<AnalyzedContract | null>(null);
  const [errorModalOpen, setErrorModalOpen] = useState(false);
  const [contractWithError, setContractWithError] = useState<AnalyzedContract | null>(null);
  const [analyzedContracts, setAnalyzedContracts] = useState<AnalyzedContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [generatingPDFs, setGeneratingPDFs] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRiskLevel, setFilterRiskLevel] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterDateFrom, setFilterDateFrom] = useState<string>('');
  const [filterDateTo, setFilterDateTo] = useState<string>('');
  const itemsPerPage = ITEMS_PER_PAGE;

  const fetchContracts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      if (!token) {
        throw new Error('No authentication token found');
      }

      const data = await listContracts(authFetch);
      setAnalyzedContracts(data);
    } catch (err) {
      console.error('Error fetching contracts:', err);
      setError(err instanceof Error ? err.message : 'Error al cargar contratos');
    } finally {
      setLoading(false);
    }
  }, [authFetch, token]);

  useEffect(() => {
    fetchContracts();
  }, [fetchContracts]);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    const connect = async () => {
      let delay = 1000;
      while (!controller.signal.aborted) {
        try {
          await streamContractEvents(
            token,
            data => setAnalyzedContracts(previous => applyStreamEvent(previous, data)),
            controller.signal,
          );
          delay = 1000;
        } catch (streamError) {
          if (controller.signal.aborted) return;
          console.error('SSE connection error:', streamError);
        }
        await new Promise(resolve => setTimeout(resolve, delay));
        delay = Math.min(delay * 2, 30_000);
      }
    };
    void connect();
    return () => controller.abort();
  }, [token]);

  const generatePDF = async (contractId: string) => {
    setGeneratingPDFs(previous => new Set([...previous, contractId]));
    try {
      if (!token) throw new Error('No authentication token found');
      const data = await getContractAnalysis(contractId, token);
      await createContractAnalysisPdf({ ...data, language });
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Error al generar el PDF. Por favor intenta de nuevo.');
    } finally {
      setGeneratingPDFs(previous => {
        const next = new Set(previous);
        next.delete(contractId);
        return next;
      });
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const uploadFiles = async (files: FileList) => {
    if (!token) {
      console.error('No authentication token found');
      return;
    }

    if (remainingAnalyses !== null && remainingAnalyses <= 0) {
      alert(t('analyze.limitReached'));
      return;
    }

    if (files.length > 1) {
      console.error(t('analyze.errorUpload'));
      return;
    }

    setUploadError(null);

    const file = files[0];
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!['.pdf', '.docx', '.txt'].includes(ext)) {
      setUploadError(t('analyze.errorInvalidType'));
      setTimeout(() => setUploadError(null), 6000);
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setUploadError(t('analyze.errorFileTooLarge'));
      setTimeout(() => setUploadError(null), 6000);
      return;
    }
    if (file.size === 0) {
      setUploadError(t('analyze.errorFileEmpty'));
      setTimeout(() => setUploadError(null), 6000);
      return;
    }

    try {
      setLoading(true);

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        await uploadContract(authFetch, file);
        await fetchContracts();
      }

      if (token) {
        try {
          const notifResponse = await createNotification(authFetch, {
              title: t('analyze.notifFileUploaded'),
              message: t('analyze.notifFileUploadedMsg'),
              notification_type: 'success',
              related_entity_type: 'contract',
          });
          if (notifResponse.ok) refreshNotifications();
        } catch (notifErr) {
          console.error('Error creating notification:', notifErr);
        }
      }

      refreshUsage();
    } catch (err) {
      console.error('Error uploading files:', err);
      const raw = err instanceof Error ? err.message : '';
      let errorMessage: string;
      if (raw.includes('not allowed') || raw.includes('File type')) {
        errorMessage = t('analyze.errorInvalidType');
      } else if (raw.includes('too large') || raw.includes('File too large')) {
        errorMessage = t('analyze.errorFileTooLarge');
      } else if (raw.includes('empty')) {
        errorMessage = t('analyze.errorFileEmpty');
      } else if (raw.includes('too many pages') || raw.includes('Maximum allowed')) {
        errorMessage = t('analyze.errorTooManyPages');
      } else if (raw.includes('not a valid') || raw.includes('not valid')) {
        errorMessage = t('analyze.errorInvalidContent');
      } else {
        errorMessage = t('analyze.errorUpload');
      }
      setUploadError(errorMessage);
      setTimeout(() => setUploadError(null), 6000);
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      uploadFiles(e.dataTransfer.files);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      uploadFiles(e.target.files);
      e.target.value = '';
    }
  };

  const deleteContract = (id: string) => {
    const contract = analyzedContracts.find(c => c.id === id);
    if (contract) {
      setContractToDelete(contract);
      setDeleteModalOpen(true);
    }
  };

  const confirmDelete = async () => {
    if (contractToDelete) {
      if (!token) {
        console.error('No authentication token found');
        return;
      }

      try {
        await deleteContractRequest(contractToDelete.id, token);

        setAnalyzedContracts(analyzedContracts.filter(contract => contract.id !== contractToDelete.id));
        setDeleteModalOpen(false);
        setContractToDelete(null);

        if (token) {
          try {
            await createTokenNotification(token, {
                title: 'Contrato eliminado',
                message: 'El contrato ha sido eliminado correctamente',
                notification_type: 'success',
                related_entity_type: 'contract',
                related_entity_id: contractToDelete.id,
            });
            refreshNotifications();
          } catch (notifErr) {
            console.error('Error creating notification:', notifErr);
          }
        }
      } catch (err) {
        console.error('Error deleting contract:', err);

        if (token) {
          try {
            await createTokenNotification(token, {
                title: 'Error al eliminar contrato',
                message: 'No se pudo eliminar el contrato. Por favor intenta de nuevo.',
                notification_type: 'error',
                related_entity_type: 'contract',
            });
            refreshNotifications();
          } catch (notifErr) {
            console.error('Error creating notification:', notifErr);
          }
        }
        setDeleteModalOpen(false);
        setContractToDelete(null);
      }
    }
  };

  const cancelDelete = () => {
    setDeleteModalOpen(false);
    setContractToDelete(null);
  };

  const showError = (contract: AnalyzedContract) => {
    setContractWithError(contract);
    setErrorModalOpen(true);
  };

  const closeErrorModal = () => {
    setErrorModalOpen(false);
    setContractWithError(null);
  };

  const retryAnalysis = async () => {
    if (contractWithError) {
      try {
        await retryContractAnalysis(authFetch, contractWithError.id);
        setAnalyzedContracts(previous => previous.map(contract =>
          contract.id === contractWithError.id
            ? { ...contract, status: 'pending' as const, errorMessage: undefined }
            : contract
        ));
        closeErrorModal();
      } catch (retryError) {
        console.error('Error retrying analysis:', retryError);
        setError(retryError instanceof Error ? retryError.message : 'No se pudo reintentar el análisis');
      }
    }
  };

  const filteredContracts = filterContracts(analyzedContracts, {
    searchTerm,
    status: filterStatus,
    riskLevel: filterRiskLevel,
    dateFrom: filterDateFrom,
    dateTo: filterDateTo,
  });
  const { contracts: currentContracts, totalPages } = paginateContracts(filteredContracts, currentPage, itemsPerPage);

  return {
    t,
    language,
    isDragging,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileInput,
    usage,
    remainingAnalyses,
    loading,
    error,
    fetchContracts,
    analyzedContracts,
    filteredContracts,
    currentContracts,
    totalPages,
    searchTerm,
    setSearchTerm,
    filterRiskLevel,
    setFilterRiskLevel,
    filterStatus,
    setFilterStatus,
    filterDateFrom,
    setFilterDateFrom,
    filterDateTo,
    setFilterDateTo,
    currentPage,
    setCurrentPage,
    navigate,
    getFilenameParts,
    generatePDF,
    generatingPDFs,
    uploadError,
    deleteContract,
    showError,
    contractToDelete,
    deleteModalOpen,
    confirmDelete,
    cancelDelete,
    contractWithError,
    errorModalOpen,
    closeErrorModal,
    retryAnalysis
  };
}

export type AnalyzeContractController = ReturnType<typeof useAnalyzeContractController>;
