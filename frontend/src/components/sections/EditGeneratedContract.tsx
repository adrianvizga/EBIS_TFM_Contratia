import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FaArrowLeft, FaSave, FaFileContract, FaSpinner, FaMagic, FaHistory, FaUndo } from 'react-icons/fa';
import { generatedContractsService, type GeneratedContract, type ContractVersion } from '../../services/generatedContracts';
import { useNotifications } from '../../context/useNotifications';
import { useLanguage } from '../../context/useLanguage';
import { formatDate, formatTime } from '../../utils/formatDate';
import { useUsage } from '../../hooks/useUsage';
import { useContractTypes } from '../../hooks/useContractTypes';
import UsageBadge from '../UsageBadge';
import { useToast } from '../../context/useToast';

export default function EditGeneratedContract() {
    const navigate = useNavigate();
    const { id } = useParams();
    const { refreshNotifications } = useNotifications();
    const { t, language } = useLanguage();
    const { usage, refresh: refreshUsage, getAiModsRemaining } = useUsage();
    const { getLabel: contractTypeLabel } = useContractTypes();

    const aiModsRemaining = id ? getAiModsRemaining(id) : null;

    const [contract, setContract] = useState<GeneratedContract | null>(null);
    const [content, setContent] = useState('');
    const [originalContent, setOriginalContent] = useState('');
    const [loading, setLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const { showToast } = useToast();

    const hasChanges = content !== originalContent;

    const [aiPrompt, setAiPrompt] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);

    const [versions, setVersions] = useState<ContractVersion[]>([]);
    const [activeTab, setActiveTab] = useState<'ai' | 'history'>('ai');

    const loadContractData = useCallback(async (contractId: string) => {
        try {
            if (!contract) setLoading(true);

            const [contractData, versionsData] = await Promise.all([
                generatedContractsService.getById(contractId),
                generatedContractsService.getVersions(contractId)
            ]);

            setContract(contractData);

            if (contractData.status === 'pending' || contractData.status === 'processing') {
                setTimeout(() => loadContractData(contractId), 3000);
            } else {
                if (!content) {
                    setContent(contractData.current_content);
                    setOriginalContent(contractData.current_content);
                }
                setVersions(versionsData);
            }

        } catch (error) {
            console.error('Error loading contract data:', error);
        } finally {
            setLoading(false);
        }
    }, [content, contract]);

    useEffect(() => {
        if (id) {
            loadContractData(id);
        }
    }, [id, loadContractData]);

    const handleSave = async () => {
        if (!id) return;
        setIsSaving(true);
        try {
            const updated = await generatedContractsService.update(id, content, 'Manual', t('edit.manualSave'));

            const versionsData = await generatedContractsService.getVersions(id);
            setVersions(versionsData);
            setContract(updated);
            setOriginalContent(content);
        } catch (error) {
            console.error('Error saving contract:', error);
            const msg = error instanceof Error ? error.message : String(error);
            showToast(`${t('edit.saveError')} ${msg}`);
        } finally {
            setIsSaving(false);
        }
    };

    const handleAIRequest = async () => {
        if (!aiPrompt.trim() || !id) return;

        setIsGenerating(true);
        try {
            const updated = await generatedContractsService.generateModification(id, aiPrompt);

            setContent(updated.current_content);
            setOriginalContent(updated.current_content);
            setContract(updated);

            const versionsData = await generatedContractsService.getVersions(id);
            setVersions(versionsData);

            refreshNotifications();
            refreshUsage();
            setAiPrompt('');
        } catch (error) {
            console.error('Error generating with AI:', error);
            const msg = error instanceof Error ? error.message : String(error);
            showToast(`${t('edit.aiError')} ${msg}`);
            refreshNotifications();
        } finally {
            setIsGenerating(false);
        }
    };

    const restoreVersion = async (version: ContractVersion) => {
        if (!id) return;
        if (window.confirm(t('edit.restoreConfirm'))) {
            try {
                const updated = await generatedContractsService.update(
                    id,
                    version.content,
                    'Manual',
                    `${t('edit.restoredTo')} ${version.version_number || 'anterior'}`
                );
                setContent(updated.current_content);
                setOriginalContent(updated.current_content);
                setContract(updated);
                const versionsData = await generatedContractsService.getVersions(id);
                setVersions(versionsData);
            } catch (error) {
                console.error('Error restoring version:', error);
                showToast(t('edit.restoreError'));
            }
        }
    };

    const getSuggestions = () => {
        const type = contract?.contract_type || '';
        if (type.toLowerCase().includes('arrendamiento') || type.toLowerCase().includes('alquiler')) {
            return [
                t('edit.suggestNoPets'),
                t('edit.suggestRentReview'),
                t('edit.suggestEarlyTermination')
            ];
        } else if (type.toLowerCase().includes('servicios')) {
            return [
                t('edit.suggestConfidentiality'),
                t('edit.suggestLiability'),
                t('edit.suggestIP')
            ];
        }
        return [
            t('edit.suggestFormalTone'),
            t('edit.suggestSummarize'),
            t('edit.suggestDataProtection')
        ];
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-dark-50 dark:bg-dark-900">
                <FaSpinner className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        );
    }

    if (!contract) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-dark-50 dark:bg-dark-900 text-dark-500">
                <p className="mb-4">{t('edit.contractNotFound')}</p>
                <button
                    onClick={() => navigate('/dashboard/generate')}
                    className="text-primary-600 hover:text-primary-700"
                >
                    {t('edit.backToList')}
                </button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-dark-50 dark:bg-dark-900 flex flex-col">
            <header className="bg-white dark:bg-dark-800 border-b border-dark-200 dark:border-dark-700 h-16 flex items-center justify-between px-6 sticky top-0 z-40">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate('/dashboard/generate')}
                        className="p-2 mr-2 text-dark-500 hover:bg-dark-100 dark:hover:bg-dark-700 rounded-lg transition-colors"
                    >
                        <FaArrowLeft />
                    </button>
                    <div>
                        <h1 className="text-lg font-bold text-dark-900 dark:text-white flex items-center gap-2">
                            <FaFileContract className="text-primary-500" />
                            {contract.title}
                        </h1>
                        <p className="text-xs text-dark-500 dark:text-dark-400">
                            {t('edit.editingDraft')} • {contractTypeLabel(contract.contract_type)}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {hasChanges && (
                        <span className="text-sm text-dark-500 dark:text-dark-400">
                            {isSaving ? t('edit.saving') : t('edit.unsavedChanges')}
                        </span>
                    )}
                    <button
                        onClick={handleSave}
                        disabled={isSaving || !hasChanges || isGenerating}
                        className="flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isSaving ? <FaSpinner className="animate-spin" /> : <FaSave />}
                        {t('edit.saveChanges')}
                    </button>
                </div>
            </header>
            <div className="flex-1 flex overflow-hidden">

                <div className="flex-1 p-8 overflow-y-auto">
                    <div className="relative max-w-4xl mx-auto bg-white dark:bg-dark-800 shadow-lg rounded-xl min-h-[800px] p-8 md:p-12 border border-dark-100 dark:border-dark-700">
                        {isGenerating && (
                            <div className="absolute inset-0 bg-white/60 dark:bg-dark-800/60 backdrop-blur-sm rounded-xl z-10 flex flex-col items-center justify-center gap-3">
                                <FaSpinner className="animate-spin text-3xl text-purple-600" />
                                <p className="text-sm font-medium text-purple-700 dark:text-purple-400">{t('edit.aiModifying')}</p>
                            </div>
                        )}
                        <textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            disabled={isGenerating}
                            className={`w-full h-full min-h-[700px] resize-none outline-none bg-transparent text-dark-900 dark:text-dark-100 font-mono text-base leading-relaxed ${isGenerating ? 'opacity-50 cursor-not-allowed' : ''}`}
                            placeholder={t('edit.editorPlaceholder')}
                        />
                    </div>
                </div>

                <div className="w-96 bg-white dark:bg-dark-800 border-l border-dark-200 dark:border-dark-700 flex flex-col shadow-xl z-20">

                    <div className="flex border-b border-dark-200 dark:border-dark-700">
                        <button
                            onClick={() => setActiveTab('ai')}
                            className={`flex-1 py-4 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${activeTab === 'ai'
                                ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400 bg-primary-50/50 dark:bg-primary-900/10'
                                : 'text-dark-500 dark:text-dark-400 hover:text-dark-700 dark:hover:text-dark-300'
                                }`}
                        >
                            <FaMagic /> {t('edit.aiAssistant')}
                        </button>
                        <button
                            onClick={() => setActiveTab('history')}
                            className={`flex-1 py-4 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${activeTab === 'history'
                                ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400 bg-primary-50/50 dark:bg-primary-900/10'
                                : 'text-dark-500 dark:text-dark-400 hover:text-dark-700 dark:hover:text-dark-300'
                                }`}
                        >
                            <FaHistory /> {t('edit.history')}
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-6">

                        {activeTab === 'ai' ? (
                            <div className="space-y-6">
                                <div className="bg-primary-50 dark:bg-primary-900/20 rounded-lg p-4 border border-primary-100 dark:border-primary-800/30">
                                    <h3 className="font-semibold text-primary-900 dark:text-primary-300 mb-2 flex items-center gap-2">
                                        <FaMagic className="text-primary-500" />
                                        {t('edit.aiCopilot')}
                                    </h3>
                                    <p className="text-sm text-primary-800 dark:text-primary-400">
                                        {t('edit.aiCopilotDesc')}
                                    </p>
                                </div>

                                {usage && usage.ai_modifications_per_contract_limit !== null && aiModsRemaining !== null && (
                                    <div className="mb-2">
                                        <UsageBadge
                                            used={usage.ai_modifications_per_contract_limit - aiModsRemaining}
                                            limit={usage.ai_modifications_per_contract_limit}
                                            label={t('edit.aiModsLabel')}
                                        />
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-dark-700 dark:text-dark-300">
                                        {t('edit.aiRequestLabel')}
                                    </label>
                                    <textarea
                                        value={aiPrompt}
                                        onChange={(e) => setAiPrompt(e.target.value)}
                                        className="w-full h-32 px-4 py-3 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm resize-none"
                                        placeholder={t('edit.aiRequestPlaceholder')}
                                    />
                                    <div className="text-xs text-dark-500">
                                        <span>{t('edit.beSpecific')}</span>
                                    </div>
                                </div>

                                <button
                                    onClick={handleAIRequest}
                                    disabled={!aiPrompt.trim() || isGenerating || (aiModsRemaining !== null && aiModsRemaining <= 0)}
                                    className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-lg shadow-md hover:shadow-lg transition-all font-medium flex items-center justify-center gap-2 disabled:opacity-50 disabled:shadow-none"
                                >
                                    {isGenerating ? (
                                        <>
                                            <FaSpinner className="animate-spin" /> {t('edit.generating')}
                                        </>
                                    ) : (
                                        <>
                                            <FaMagic /> {t('edit.generateChanges')}
                                        </>
                                    )}
                                </button>

                                <div className="pt-4 border-t border-dark-200 dark:border-dark-700">
                                    <h4 className="text-xs font-semibold text-dark-500 uppercase tracking-wider mb-3">{t('edit.quickSuggestions')}</h4>
                                    <div className="space-y-2">
                                        {getSuggestions().map((suggestion, index) => (
                                            <button
                                                key={index}
                                                onClick={() => setAiPrompt(suggestion)}
                                                className="w-full text-left p-3 rounded-lg bg-dark-50 dark:bg-dark-700/50 hover:bg-white dark:hover:bg-dark-700 border border-transparent hover:border-dark-200 dark:hover:border-dark-600 transition-all text-sm text-dark-700 dark:text-dark-300"
                                            >
                                                {suggestion}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {versions.map((version, index) => (
                                    <div key={version.id} className="bg-dark-50 dark:bg-dark-700/50 rounded-lg p-4 border border-dark-100 dark:border-dark-600">
                                        <div className="flex justify-between items-start mb-2">
                                            <div className="flex items-center gap-2">
                                                <div className={`p-1.5 rounded-full ${version.change_type === 'IA'
                                                    ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400'
                                                    : version.change_type === 'Inicial'
                                                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                                        : 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
                                                    }`}>
                                                    {version.change_type === 'IA' ? <FaMagic className="w-3 h-3" /> : <FaSave className="w-3 h-3" />}
                                                </div>
                                                <span className="font-medium text-sm text-dark-900 dark:text-white">v{version.version_number ?? (versions.length - index)}</span>
                                            </div>
                                            <span className="text-xs text-dark-500 dark:text-dark-400">
                                                {formatTime(version.created_at, language)}
                                            </span>
                                        </div>

                                        <p className="text-xs text-dark-600 dark:text-dark-300 mb-3 line-clamp-2">
                                            {version.change_description || t('edit.noDescription')}
                                        </p>

                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-dark-400">
                                                {formatDate(version.created_at, language)}
                                            </span>

                                            {index !== 0 && (
                                                <button
                                                    onClick={() => restoreVersion(version)}
                                                    className="flex items-center gap-1 text-primary-600 dark:text-primary-400 hover:underline"
                                                >
                                                    <FaUndo className="w-3 h-3" /> {t('edit.restore')}
                                                </button>
                                            )}
                                            {index === 0 && (
                                                <span className="text-green-600 dark:text-green-400 font-medium">{t('edit.current')}</span>
                                            )}
                                        </div>
                                    </div>
                                ))}

                                {versions.length === 0 && (
                                    <div className="text-center py-8 text-dark-500">
                                        {t('edit.noHistory')}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
