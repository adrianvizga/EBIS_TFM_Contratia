import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FaArrowLeft, FaEdit, FaTrash, FaFileContract, FaUser, FaSpinner, FaChartPie, FaRobot } from 'react-icons/fa';
import DownloadDropdown from '../DownloadDropdown';
import { generatedContractsService, type GeneratedContract } from '../../services/generatedContracts';
import ConfirmDeleteModal from '../ConfirmDeleteModal';
import { useNotifications } from '../../context/useNotifications';
import { useLanguage } from '../../context/useLanguage';
import { formatDate } from '../../utils/formatDate';
import { useUsage } from '../../hooks/useUsage';
import { useContractTypes } from '../../hooks/useContractTypes';
import UsageBadge from '../UsageBadge';
import { useToast } from '../../context/useToast';

export default function ViewGeneratedContract() {
    const navigate = useNavigate();
    const { id } = useParams();
    const { refreshNotifications } = useNotifications();
    const { t, language } = useLanguage();
    const { usage, remainingAnalyses, refresh: refreshUsage } = useUsage();
    const { getLabel: contractTypeLabel } = useContractTypes();
    const [contract, setContract] = useState<GeneratedContract | null>(null);
    const [loading, setLoading] = useState(true);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [analyzeModalOpen, setAnalyzeModalOpen] = useState(false);
    const [sendingToAnalysis, setSendingToAnalysis] = useState(false);
    const [retrying, setRetrying] = useState(false);
    const { showToast } = useToast();
    const contractStatus = contract?.status;

    useEffect(() => {
        if (id) {
            loadContract(id);
        }
    }, [id]);

    useEffect(() => {
        if (!id || !contractStatus || !['pending', 'processing'].includes(contractStatus)) return;
        const timer = window.setInterval(async () => {
            try {
                setContract(await generatedContractsService.getById(id));
            } catch {
                showToast('No se pudo actualizar el estado de la generación.');
            }
        }, 3000);
        return () => window.clearInterval(timer);
    }, [id, contractStatus]);

    const handleRetry = async () => {
        if (!contract) return;
        setRetrying(true);
        try {
            setContract(await generatedContractsService.retry(contract.id));
        } catch (error) {
            showToast(error instanceof Error ? error.message : 'No se pudo reintentar.');
        } finally {
            setRetrying(false);
        }
    };

    const loadContract = async (contractId: string) => {
        try {
            setLoading(true);
            const data = await generatedContractsService.getById(contractId);
            setContract(data);
        } catch (error) {
            console.error('Error loading contract:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteClick = () => {
        setDeleteModalOpen(true);
    };

    const handleDeleteConfirm = async () => {
        if (!contract) return;
        setDeleting(true);
        try {
            await generatedContractsService.delete(contract.id);
            navigate('/dashboard/generate');
        } catch (error) {
            console.error('Error deleting contract:', error);
        } finally {
            setDeleting(false);
        }
    };

    const handleDeleteCancel = () => {
        setDeleteModalOpen(false);
    };

    const handleAnalyzeClick = () => {
        setAnalyzeModalOpen(true);
    };

    const handleAnalyzeConfirm = async () => {
        if (!contract) return;
        setSendingToAnalysis(true);
        try {
            await generatedContractsService.sendToAnalysis(contract.id);
            setAnalyzeModalOpen(false);
            refreshNotifications();
            refreshUsage();
            navigate('/dashboard/analyze');
        } catch (error) {
            console.error('Error sending contract to analysis:', error);
            refreshNotifications();
        } finally {
            setSendingToAnalysis(false);
        }
    };

    const handleAnalyzeCancel = () => {
        setAnalyzeModalOpen(false);
    };

    const isHeading = (text: string) => {
        const t = text.trim();
        return t.length > 0 && t === t.toUpperCase() && !t.endsWith('.');
    };

    const handleDownloadPDF = async () => {
        if (!contract) return;
        const { default: jsPDF } = await import('jspdf');
        const doc = new jsPDF();
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 20;
        const contentWidth = pageWidth - (margin * 2);
        let yPosition = margin;

        const checkPage = (needed: number) => {
            if (yPosition + needed > pageHeight - margin) {
                doc.addPage();
                yPosition = margin;
            }
        };

        const paragraphs = contract.current_content.trim().split(/\n\n+/);

        for (let i = 0; i < paragraphs.length; i++) {
            const text = paragraphs[i].trim();
            if (!text) continue;

            if (isHeading(text)) {
                if (i > 0) yPosition += 7;
                // mantiene encabezado y al menos una línea de cuerpo juntos en la misma página
                checkPage(22);
                doc.setFontSize(11);
                doc.setFont('helvetica', 'bold');
                doc.setTextColor(0);
                const lines = doc.splitTextToSize(text, contentWidth);
                lines.forEach((line: string) => {
                    checkPage(6);
                    doc.text(line, margin, yPosition);
                    yPosition += 5.5;
                });
                yPosition += 2;
            } else {
                doc.setFontSize(10.5);
                doc.setFont('times', 'roman');
                doc.setTextColor(0);
                const lines = doc.splitTextToSize(text, contentWidth);
                lines.forEach((line: string) => {
                    checkPage(5.5);
                    doc.text(line, margin, yPosition);
                    yPosition += 5;
                });
                yPosition += 2.5;
            }
        }

        const pageCount = doc.getNumberOfPages();
        for (let i = 1; i <= pageCount; i++) {
            doc.setPage(i);
            doc.setFontSize(8.5);
            doc.setTextColor(160);
            doc.text(`${i} / ${pageCount}`, pageWidth / 2, pageHeight - 8, { align: 'center' });
        }

        doc.save(`${contract.title}.pdf`);
    };

    const handleDownloadDOCX = async () => {
        if (!contract) return;
        const { Document, Packer, Paragraph, TextRun, AlignmentType } = await import('docx');
        const children: InstanceType<typeof Paragraph>[] = [];

        const paragraphs = contract.current_content.trim().split(/\n\n+/);

        for (const para of paragraphs) {
            const text = para.trim();
            if (!text) continue;

            if (isHeading(text)) {
                children.push(
                    new Paragraph({
                        children: [new TextRun({ text, bold: true, size: 22, font: 'Arial' })],
                        spacing: { before: 480, after: 80, line: 240 },
                        alignment: AlignmentType.LEFT,
                        keepNext: true,
                    }),
                );
            } else {
                children.push(
                    new Paragraph({
                        children: [new TextRun({ text, size: 21, font: 'Times New Roman' })],
                        spacing: { before: 0, after: 100, line: 264 },
                        alignment: AlignmentType.JUSTIFIED,
                    }),
                );
            }
        }

        const doc = new Document({
            sections: [{
                properties: { page: { margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
                children,
            }],
        });
        const blob = await Packer.toBlob(doc);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${contract.title}.docx`;
        a.click();
        URL.revokeObjectURL(url);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full bg-dark-50 dark:bg-dark-900">
                <FaSpinner className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        );
    }

    if (!contract) {
        return (
            <div className="flex flex-col items-center justify-center h-full bg-dark-50 dark:bg-dark-900 text-dark-500">
                <p className="mb-4">{t('view.contractNotFound')}</p>
                <button
                    onClick={() => navigate('/dashboard/generate')}
                    className="text-primary-600 hover:text-primary-700"
                >
                    {t('view.backToList')}
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-dark-50 dark:bg-dark-900">
            {/* Cabecera */}
            <div className="bg-white dark:bg-dark-800 border-b border-dark-200 dark:border-dark-700 px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate('/dashboard/generate')}
                        className="p-2 rounded-full hover:bg-dark-100 dark:hover:bg-dark-700 text-dark-600 dark:text-dark-300 transition-colors"
                    >
                        <FaArrowLeft />
                    </button>
                    <div>
                        <h1 className="text-xl font-bold text-dark-900 dark:text-white flex items-center gap-2">
                            <FaFileContract className="text-primary-500" />
                            {contract.title}
                        </h1>
                        <p className="text-sm text-dark-500 dark:text-dark-400 mt-1">
                            {t('view.generatedOn')} {formatDate(contract.created_at, language)} • {contractTypeLabel(contract.contract_type)}
                        </p>
                    </div>
                </div>

                <div className="flex gap-2">
                    {contract.status === 'completed' ? (
                        <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full text-sm font-medium">
                            {t('view.completed')}
                        </span>
                    ) : contract.status === 'pending' || contract.status === 'processing' ? (
                        <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
                            <div className="w-3 h-3 border-2 border-blue-700 dark:border-blue-300 border-t-transparent rounded-full animate-spin"></div>
                            {t('view.generating')}
                        </span>
                    ) : contract.status === 'error' ? (
                        <span className="inline-flex items-center gap-1 px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-full text-sm font-medium">
                            {t('view.error')}
                        </span>
                    ) : (
                        <span className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-sm font-medium">
                            {contract.status}
                        </span>
                    )}
                    {contract.status === 'error' && (
                        <button onClick={handleRetry} disabled={retrying} className="px-3 py-1 rounded-lg bg-primary-600 text-sm text-white disabled:opacity-50">
                            {retrying ? 'Reintentando…' : 'Reintentar generación'}
                        </button>
                    )}
                    <button
                        onClick={() => navigate('/dashboard/agent', { state: { generatedContract: { id: contract.id, title: contract.title } } })}
                        className="p-2 text-dark-600 dark:text-dark-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-950 rounded-lg transition-colors"
                        title={t('view.consultAgent')}
                    >
                        <FaRobot className="w-4 h-4" />
                    </button>
                    <button
                        onClick={handleAnalyzeClick}
                        disabled={contract.status !== 'completed' || !contract.current_content}
                        className="p-2 text-dark-600 dark:text-dark-400 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
                        title={t('view.sendToAnalysis')}
                    >
                        <FaChartPie className="w-4 h-4" />
                    </button>
                    <DownloadDropdown
                        onDownloadPDF={handleDownloadPDF}
                        onDownloadDOCX={handleDownloadDOCX}
                        disabled={contract.status !== 'completed' || !contract.current_content}
                        variant="icon"
                    />
                    <button
                        onClick={() => navigate(`/dashboard/generate/${contract.id}/edit`)}
                        disabled={contract.status !== 'completed' || !contract.current_content}
                        className="p-2 text-dark-600 dark:text-dark-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-950 rounded-lg transition-colors"
                        title={t('view.edit')}
                    >
                        <FaEdit className="w-4 h-4" />
                    </button>
                    <button
                        onClick={handleDeleteClick}
                        className="p-2 text-dark-600 dark:text-dark-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                        title={t('view.delete')}
                    >
                        <FaTrash className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Contenido */}
            <div className="flex-1 overflow-hidden">
                <div className="h-full flex flex-col lg:flex-row">

                    {/* Documento */}
                    <div className="flex-1 overflow-y-auto p-6 lg:p-10">
                        {contract.error_message && (
                            <div className="max-w-4xl mx-auto mb-4 rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
                                <p role="alert">{contract.error_message}</p>
                            </div>
                        )}
                        <div className="max-w-4xl mx-auto bg-white dark:bg-dark-800 shadow-lg rounded-xl min-h-[800px] p-12 border border-dark-100 dark:border-dark-700">
                            <pre className="whitespace-pre-wrap font-serif text-dark-900 dark:text-dark-200 text-lg leading-relaxed">
                                {contract.current_content}
                            </pre>
                        </div>
                    </div>

                    {/* Panel lateral */}
                    <div className="w-full lg:w-80 bg-white dark:bg-dark-800 border-l border-dark-200 dark:border-dark-700 p-6 overflow-y-auto shadow-xl z-10 flex flex-col">
                        <h3 className="text-lg font-bold text-dark-900 dark:text-white mb-6">{t('view.contractDetails')}</h3>

                        <div className="space-y-6">
                            {contract.contract_details?.parties && (
                                <div>
                                    <h4 className="text-sm font-medium text-dark-500 dark:text-dark-400 uppercase tracking-wider mb-2">{t('view.parties')}</h4>
                                    <div className="space-y-3">
                                        <div className="flex items-start gap-3">
                                            <div className="bg-primary-100 dark:bg-primary-900/30 p-2 rounded-lg text-primary-600 dark:text-primary-400">
                                                <FaUser className="w-4 h-4" />
                                            </div>
                                            <div>
                                                <p className="text-xs text-dark-500 dark:text-dark-400">{t('view.partyA')}</p>
                                                <p className="text-sm font-medium text-dark-900 dark:text-white">{contract.contract_details.parties.partyA || t('view.notSpecified')}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3">
                                            <div className="bg-primary-100 dark:bg-primary-900/30 p-2 rounded-lg text-primary-600 dark:text-primary-400">
                                                <FaUser className="w-4 h-4" />
                                            </div>
                                            <div>
                                                <p className="text-xs text-dark-500 dark:text-dark-400">{t('view.partyB')}</p>
                                                <p className="text-sm font-medium text-dark-900 dark:text-white">{contract.contract_details.parties.partyB || t('view.notSpecified')}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div>
                                <h4 className="text-sm font-medium text-dark-500 dark:text-dark-400 uppercase tracking-wider mb-2">{t('view.information')}</h4>
                                <div className="text-sm space-y-2">
                                    <div className="flex justify-between">
                                        <span className="text-dark-600 dark:text-dark-400">{t('view.created')}</span>
                                        <span className="text-dark-900 dark:text-white font-medium">{formatDate(contract.created_at, language)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-dark-600 dark:text-dark-400">{t('view.lastEdit')}</span>
                                        <span className="text-dark-900 dark:text-white font-medium">{formatDate(contract.updated_at, language)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="mt-auto pt-6 border-t border-dark-100 dark:border-dark-700">
                            <p className="text-xs text-dark-400 dark:text-dark-500 leading-relaxed">
                                Borrador generado por IA. Requiere revisión profesional antes de su firma. La cobertura se limita a las fuentes legales indicadas para este tipo contractual.
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            <ConfirmDeleteModal
                isOpen={deleteModalOpen}
                contractName={contract.title}
                onConfirm={handleDeleteConfirm}
                onCancel={handleDeleteCancel}
                isLoading={deleting}
                title={t('view.deleteTitle')}
                description={t('view.deleteDescription')}
                warningItems={[
                    t('view.deleteWarning1'),
                    t('view.deleteWarning2'),
                    t('view.deleteWarning3')
                ]}
                confirmNote={t('view.deleteConfirm')}
            />

            {/* Modal de confirmación para enviar al análisis */}
            {analyzeModalOpen && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-dark-800 rounded-xl shadow-2xl max-w-md w-full overflow-hidden">
                        <div className="px-6 py-4 border-b border-dark-200 dark:border-dark-700 bg-amber-50 dark:bg-amber-950 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <FaChartPie className="w-6 h-6 text-amber-600 dark:text-amber-400" />
                                <h2 className="text-lg font-bold text-amber-900 dark:text-amber-300">{t('view.analyzeModalTitle')}</h2>
                            </div>
                            <button
                                type="button"
                                onClick={handleAnalyzeCancel}
                                className="text-dark-400 dark:text-dark-500 hover:text-dark-600 dark:hover:text-dark-400 transition-colors"
                                title={t('view.close')}
                            >
                                <span className="text-xl">&times;</span>
                            </button>
                        </div>

                        <div className="px-6 py-6">
                            <p className="text-dark-900 dark:text-white font-semibold mb-4">
                                {t('view.analyzeModalQuestion')}
                            </p>
                            <p className="text-dark-700 dark:text-dark-300 text-sm mb-4">
                                <strong>{t('view.analyzeModalContract')}</strong> {contract.title}
                            </p>
                            <div className="bg-amber-50 dark:bg-amber-950 border-l-4 border-l-amber-500 p-4 rounded mb-6">
                                <p className="text-sm text-dark-900 dark:text-amber-300 mb-2">
                                    <strong>{t('view.analyzeModalInfo')}</strong>
                                </p>
                                <ul className="text-sm text-dark-700 dark:text-dark-300 space-y-2">
                                    <li>• {t('view.analyzeModalBullet1')}</li>
                                    <li>• {t('view.analyzeModalBullet2')}</li>
                                    <li>• {t('view.analyzeModalBullet3')}</li>
                                </ul>
                            </div>

                            {usage && usage.contracts_analyzed_limit !== null && (
                                <div className="mb-4">
                                    <UsageBadge
                                        used={usage.contracts_analyzed}
                                        limit={usage.contracts_analyzed_limit}
                                        label={t('view.analyzeUsageLabel')}
                                    />
                                </div>
                            )}
                        </div>

                        <div className="px-6 py-4 border-t border-dark-200 dark:border-dark-700 bg-dark-50 dark:bg-dark-700 flex gap-3 justify-end">
                            <button
                                type="button"
                                onClick={handleAnalyzeCancel}
                                disabled={sendingToAnalysis}
                                className="px-4 py-2 border border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                            >
                                {t('view.cancel')}
                            </button>
                            <button
                                type="button"
                                onClick={handleAnalyzeConfirm}
                                disabled={sendingToAnalysis || (remainingAnalyses !== null && remainingAnalyses <= 0)}
                                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 dark:hover:bg-amber-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                            >
                                {remainingAnalyses !== null && remainingAnalyses <= 0 ? t('view.limitReached') : sendingToAnalysis ? t('view.sending') : t('view.sendToAnalysis')}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
