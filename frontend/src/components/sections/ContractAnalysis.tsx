import { useState, useEffect, useCallback, type ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FaArrowLeft, FaFileContract, FaExclamationTriangle, FaCheckCircle, FaChevronDown, FaFilePdf, FaMinusCircle, FaRobot, FaSpinner } from 'react-icons/fa';
import { useLanguage } from '../../context/useLanguage';
import { useUser } from '../../context/useUser';
import { useAuthFetch } from '../../hooks/useAuthFetch';
import ClauseRelationsGraph from '../ClauseRelationsGraph';
import type { ClauseRelation } from '../ClauseRelationsGraph';
import { formatDateTime } from '../../utils/formatDate';
import { createContractAnalysisPdf } from './analyzeContract/pdfService';
import { useToast } from '../../context/useToast';

interface AnalysisData {
  filename: string;
  uploadDate: string;
  status: 'completed' | 'analyzing' | 'failed' | 'pending';
  riskLevel: 'high' | 'medium' | 'low';
  riskCount: number;
  positiveCount: number;
  negativeCount: number;
  missingCount: number;
  contractType?: string;
  coverageLevel?: string;
  coverageNotice?: string;
  legalSources?: string[];
  clausesCount?: number;
  pagesCount?: number;
}

interface Clause {
  id: string;
  number: string;
  title: string;
  technicalText: string;
  plainLanguage: string;
  recommendations?: string;
  category: 'risk' | 'positive' | 'neutral';
}

interface RiskFinding {
  title: string;
  severity: string;
}

interface AspectFinding {
  title: string;
}

interface MissingElement {
  title: string;
  severity: string;
}

interface ContractAnalysisData {
  filename: string;
  uploadDate: string;
  status: string;
  riskLevel: string;
  riskCount: number;
  positiveCount: number;
  negativeCount: number;
  missingCount: number;
  contractType?: string;
  coverageLevel?: string;
  coverageNotice?: string;
  legalSources?: string[];
  pagesCount?: number;
  clauses: Clause[];
  riskFindings: RiskFinding[];
  positiveFindings: AspectFinding[];
  negativeFindings: AspectFinding[];
  missingElements: MissingElement[];
  relations: ClauseRelation[];
}

interface ContractAnalysisProps {
  onBack: () => void;
}

interface ExpandableListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => ReactNode;
  maxItems?: number;
  viewMoreText?: string;
  viewLessText?: string;
  buttonClass?: string;
}

function ExpandableList<T>({
  items,
  renderItem,
  maxItems = 5,
  viewMoreText = "Ver más",
  viewLessText = "Ver menos",
  buttonClass = "text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
}: ExpandableListProps<T>) {
  const [expanded, setExpanded] = useState(false);

  if (items.length <= maxItems) {
    return <ul className="space-y-3 sm:space-y-4">{items.map((item, index) => renderItem(item, index))}</ul>;
  }

  const displayedItems = expanded ? items : items.slice(0, maxItems);
  const remainingCount = items.length - maxItems;

  return (
    <div className="flex flex-col">
      <ul className="space-y-3 sm:space-y-4">
        {displayedItems.map((item, index) => renderItem(item, index))}
      </ul>
      <button
        onClick={() => setExpanded(!expanded)}
        className={`mt-4 text-sm font-medium transition-colors flex items-center gap-1 self-start ${buttonClass}`}
      >
        {expanded ? viewLessText : `${viewMoreText} (${remainingCount} más)`}
        <FaChevronDown className={`w-3 h-3 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
      </button>
    </div>
  );
}



export default function ContractAnalysis({ onBack }: ContractAnalysisProps) {
  const { t, language } = useLanguage();
  const { token } = useUser();
  const { showToast } = useToast();
  const authFetch = useAuthFetch();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [expandedClause, setExpandedClause] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalysisData | null>(null);
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [riskFindings, setRiskFindings] = useState<RiskFinding[]>([]);
  const [positiveFindings, setPositiveFindings] = useState<AspectFinding[]>([]);
  const [negativeFindings, setNegativeFindings] = useState<AspectFinding[]>([]);
  const [missingElements, setMissingElements] = useState<MissingElement[]>([]);
  const [relations, setRelations] = useState<ClauseRelation[]>([]);
  const [generatingPDF, setGeneratingPDF] = useState(false);

  const fetchContractAnalysis = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      if (!token) {
        throw new Error('No authentication token found');
      }

      const url = `/api/contracts/${id}/analysis`;

      const response = await authFetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      const data: ContractAnalysisData = await response.json();

      const uniqueRiskFindings = deduplicateFindings(data.riskFindings);
      const uniquePositiveFindings = deduplicateFindings(data.positiveFindings);
      const uniqueNegativeFindings = deduplicateFindings(data.negativeFindings ?? []);
      const uniqueMissingElements = deduplicateFindings(data.missingElements);

      setAnalysisData({
        filename: data.filename,
        uploadDate: data.uploadDate,
        status: data.status as 'completed' | 'analyzing' | 'failed' | 'pending',
        riskLevel: data.riskLevel as 'high' | 'medium' | 'low',
        riskCount: uniqueRiskFindings.length,
        positiveCount: uniquePositiveFindings.length,
        negativeCount: uniqueNegativeFindings.length,
        missingCount: uniqueMissingElements.length,
        contractType: data.contractType || undefined,
        coverageLevel: data.coverageLevel,
        coverageNotice: data.coverageNotice,
        legalSources: data.legalSources,
        clausesCount: data.clauses.length,
        pagesCount: data.pagesCount
      });
      setClauses(data.clauses);
      setRiskFindings(uniqueRiskFindings);
      setPositiveFindings(uniquePositiveFindings);
      setNegativeFindings(uniqueNegativeFindings);
      setMissingElements(uniqueMissingElements);
      setRelations(data.relations);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading analysis');
      console.error('Error fetching contract analysis:', err);
    } finally {
      setLoading(false);
    }
  }, [authFetch, id, token]);

  useEffect(() => {
    if (id) {
      fetchContractAnalysis();
    }
  }, [fetchContractAnalysis, id]);

  const generatePDF = async () => {
    if (!analysisData) return;
    try {
      setGeneratingPDF(true);
      await createContractAnalysisPdf({
        filename: analysisData.filename,
        uploadDate: analysisData.uploadDate,
        status: analysisData.status,
        riskLevel: analysisData.riskLevel,
        riskCount: analysisData.riskCount,
        positiveCount: analysisData.positiveCount,
        negativeCount: analysisData.negativeCount,
        missingCount: analysisData.missingCount,
        contractType: analysisData.contractType,
        coverageLevel: analysisData.coverageLevel,
        coverageNotice: analysisData.coverageNotice,
        legalSources: analysisData.legalSources,
        pagesCount: analysisData.pagesCount,
        language,
        clauses,
        riskFindings,
        positiveFindings,
        negativeFindings,
        missingElements,
        relations,
      });
    } catch (error) {
      console.error('Error generating PDF:', error);
      showToast(t('analysis.pdf.errorMessage'));
    } finally {
      setGeneratingPDF(false);
    }
  };


  const getRiskLevelBadge = (level: string) => {
    switch (level) {
      case 'high':
        return <span className="px-4 py-2 bg-red-200 dark:bg-red-900/60 text-red-900 dark:text-red-100 rounded-full text-sm font-bold">{t('analyze.riskHigh')}</span>;
      case 'medium':
        return <span className="px-4 py-2 bg-amber-200 dark:bg-amber-900/60 text-amber-900 dark:text-amber-100 rounded-full text-sm font-bold">{t('analyze.riskMedium')}</span>;
      case 'low':
        return <span className="px-4 py-2 bg-green-200 dark:bg-green-900/60 text-green-900 dark:text-green-100 rounded-full text-sm font-bold">{t('analyze.riskLow')}</span>;
      default:
        return null;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'risk':
        return <FaExclamationTriangle className="w-4 h-4 text-red-600 dark:text-red-400" />;
      case 'positive':
        return <FaCheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />;
      default:
        return <FaFileContract className="w-4 h-4 text-blue-600 dark:text-blue-400" />;
    }
  };

  const getClauseBorderStyle = (category: string, isExpanded: boolean) => {
    if (!isExpanded) return {};

    switch (category) {
      case 'risk':
        return { borderLeft: '4px solid rgb(239, 68, 68)' };
      case 'positive':
        return { borderLeft: '4px solid rgb(16, 185, 129)' };
      default:
        return { borderLeft: '4px solid rgb(59, 130, 246)' };
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 bg-dark-50 dark:bg-dark-900">
      <div className="max-w-5xl mx-auto">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors mb-6 sm:mb-8 px-2 py-2 -ml-2 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg"
          title={t('analysis.back')}
        >
          <FaArrowLeft className="w-4 h-4 sm:w-5 sm:h-5" />
          <span className="font-semibold text-base sm:text-lg">{t('analysis.back')}</span>
        </button>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
              <p className="mt-4 text-dark-600 dark:text-dark-400">{t('analysis.loading')}</p>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <p className="text-red-800 dark:text-red-300">{error}</p>
          </div>
        )}

        {!loading && !error && analysisData && (
          <>
            <div className="bg-white dark:bg-dark-800 rounded-lg shadow mb-6 sm:mb-8 overflow-hidden">
              <div className="p-5 sm:p-6 border-b border-dark-100 dark:border-dark-700">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className="p-3 bg-primary-100 dark:bg-primary-900 rounded-lg flex-shrink-0">
                      <FaFileContract className="w-6 h-6 sm:w-7 sm:h-7 text-primary-600 dark:text-primary-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-dark-900 dark:text-white break-words">
                        {analysisData.filename}
                      </h1>
                    </div>
                  </div>
                  <button
                    onClick={generatePDF}
                    disabled={generatingPDF}
                    className="flex-shrink-0 px-3 sm:px-4 py-2 border border-primary-300 dark:border-primary-600 text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors text-sm sm:text-base font-medium flex items-center gap-2 whitespace-nowrap h-fit"
                  >
                    {generatingPDF ? <FaSpinner className="w-4 h-4 animate-spin" /> : <FaFilePdf className="w-4 h-4" />}
                    <span>{t('analysis.download')}</span>
                  </button>
                  <button
                    onClick={() => navigate('/dashboard/agent', { state: { analyzedContract: { id: id, filename: analysisData?.filename || '' } } })}
                    className="flex-shrink-0 px-3 sm:px-4 py-2 border border-primary-300 dark:border-primary-600 text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-md transition-colors text-sm sm:text-base font-medium flex items-center gap-2 whitespace-nowrap h-fit"
                    title={t('analysis.consultAgentTitle')}
                  >
                    <FaRobot className="w-4 h-4" />
                    <span className="hidden sm:inline">{t('analysis.agentShort')}</span>
                  </button>
                </div>
              </div>

              <div className="px-5 sm:px-6 py-5 sm:py-6 border-b border-dark-100 dark:border-dark-700">

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 w-full">
                  <div className="bg-dark-50 dark:bg-dark-700 p-3 rounded-lg">
                    <p className="text-xs sm:text-sm font-medium text-dark-600 dark:text-dark-400 mb-1">{t('analysis.contractType')}</p>
                    <p className="text-sm sm:text-base font-semibold text-dark-900 dark:text-white">
                      {analysisData.contractType
                        ? t(`contractType.${analysisData.contractType}`)
                        : t('analysis.notSpecified')}
                    </p>
                  </div>
                  <div className="bg-dark-50 dark:bg-dark-700 p-3 rounded-lg">
                    <p className="text-xs sm:text-sm font-medium text-dark-600 dark:text-dark-400 mb-1">{t('analysis.pages')}</p>
                    <p className="text-sm sm:text-base font-semibold text-dark-900 dark:text-white">
                      {analysisData.pagesCount || 'N/A'}
                    </p>
                  </div>
                  <div className="bg-dark-50 dark:bg-dark-700 p-3 rounded-lg">
                    <p className="text-xs sm:text-sm font-medium text-dark-600 dark:text-dark-400 mb-1">{t('analysis.clausesCount')}</p>
                    <p className="text-sm sm:text-base font-semibold text-dark-900 dark:text-white">
                      {analysisData.clausesCount || 0}
                    </p>
                  </div>
                  <div className="bg-dark-50 dark:bg-dark-700 p-3 rounded-lg">
                    <p className="text-xs sm:text-sm font-medium text-dark-600 dark:text-dark-400 mb-1">{t('analysis.uploadDate')}</p>
                    <p className="text-sm sm:text-base font-semibold text-dark-900 dark:text-white">
                      {formatDateTime(analysisData.uploadDate, language)}
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-5 sm:p-6 bg-dark-50 dark:bg-dark-700">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm sm:text-base font-medium text-dark-700 dark:text-dark-300">
                    {t('analysis.riskLevel')}:
                  </span>
                  {getRiskLevelBadge(analysisData.riskLevel)}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 sm:gap-6 mb-6 sm:mb-8">
              <div className="bg-white dark:bg-dark-800 rounded-lg shadow overflow-hidden">
                <div className="px-5 sm:px-6 py-4 sm:py-5 border-b border-red-300 dark:border-red-700 bg-red-100 dark:bg-red-900/40">
                  <h2 className="text-lg sm:text-xl font-bold text-red-800 dark:text-red-400 flex items-center gap-2 sm:gap-3">
                    <FaExclamationTriangle className="w-5 h-5 sm:w-6 sm:h-6 flex-shrink-0" />
                    <span>{t('analysis.risks')} ({analysisData.riskCount})</span>
                  </h2>
                </div>
                <div className="p-5 sm:p-6">
                  <ExpandableList
                    items={riskFindings}
                    viewMoreText={t('common.viewMore')}
                    viewLessText={t('common.viewLess')}
                    renderItem={(finding, index) => (
                      <li key={index} className="flex gap-3">
                        <span className="text-red-700 dark:text-red-300 font-bold flex-shrink-0 text-lg">•</span>
                        <span className="text-dark-700 dark:text-dark-300 text-sm sm:text-base break-words leading-relaxed">{finding.title}</span>
                      </li>
                    )}
                    buttonClass="text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
                  />
                </div>
              </div>

              <div className="bg-white dark:bg-dark-800 rounded-lg shadow overflow-hidden">
                <div className="px-5 sm:px-6 py-4 sm:py-5 border-b border-amber-400 dark:border-amber-600 bg-amber-100 dark:bg-amber-900/40">
                  <h2 className="text-lg sm:text-xl font-bold text-amber-800 dark:text-amber-400 flex items-center gap-2 sm:gap-3">
                    <FaMinusCircle className="w-5 h-5 sm:w-6 sm:h-6 flex-shrink-0" />
                    <span>{t('analysis.missingElements')} ({analysisData.missingCount})</span>
                  </h2>
                </div>
                <div className="p-5 sm:p-6">
                  <ExpandableList
                    items={missingElements}
                    viewMoreText={t('common.viewMore')}
                    viewLessText={t('common.viewLess')}
                    renderItem={(element, index) => (
                      <li key={index} className="flex gap-3">
                        <span className="text-amber-700 dark:text-amber-300 font-bold flex-shrink-0 text-lg">•</span>
                        <span className="text-dark-700 dark:text-dark-300 text-sm sm:text-base break-words leading-relaxed">{element.title}</span>
                      </li>
                    )}
                    buttonClass="text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300"
                  />
                </div>
              </div>

              <div className="bg-white dark:bg-dark-800 rounded-lg shadow overflow-hidden">
                <div className="px-5 sm:px-6 py-4 sm:py-5 border-b border-green-400 dark:border-green-600 bg-green-100 dark:bg-green-900/40">
                  <h2 className="text-lg sm:text-xl font-bold text-green-800 dark:text-green-400 flex items-center gap-2 sm:gap-3">
                    <FaCheckCircle className="w-5 h-5 sm:w-6 sm:h-6 flex-shrink-0" />
                    <span>{t('analysis.positive')} ({analysisData.positiveCount})</span>
                  </h2>
                </div>
                <div className="p-5 sm:p-6">
                  <ExpandableList
                    items={positiveFindings}
                    viewMoreText={t('common.viewMore')}
                    viewLessText={t('common.viewLess')}
                    renderItem={(finding, index) => (
                      <li key={index} className="flex gap-3">
                        <span className="text-green-700 dark:text-green-300 font-bold flex-shrink-0 text-lg">•</span>
                        <span className="text-dark-700 dark:text-dark-300 text-sm sm:text-base break-words leading-relaxed">{finding.title}</span>
                      </li>
                    )}
                    buttonClass="text-green-600 dark:text-green-400 hover:text-green-700 dark:hover:text-green-300"
                  />
                </div>
              </div>

              {negativeFindings.length > 0 && (
                <div className="bg-white dark:bg-dark-800 rounded-lg shadow overflow-hidden">
                  <div className="px-5 sm:px-6 py-4 sm:py-5 border-b border-orange-400 dark:border-orange-600 bg-orange-100 dark:bg-orange-900/40">
                    <h2 className="text-lg sm:text-xl font-bold text-orange-800 dark:text-orange-400 flex items-center gap-2 sm:gap-3">
                      <FaExclamationTriangle className="w-5 h-5 sm:w-6 sm:h-6 flex-shrink-0" />
                      <span>{t('analysis.negative')} ({analysisData.negativeCount})</span>
                    </h2>
                  </div>
                  <div className="p-5 sm:p-6">
                    <ExpandableList
                      items={negativeFindings}
                      viewMoreText={t('common.viewMore')}
                      viewLessText={t('common.viewLess')}
                      renderItem={(finding, index) => (
                        <li key={index} className="flex gap-3">
                          <span className="text-orange-700 dark:text-orange-300 font-bold flex-shrink-0 text-lg">•</span>
                          <span className="text-dark-700 dark:text-dark-300 text-sm sm:text-base break-words leading-relaxed">{finding.title}</span>
                        </li>
                      )}
                      buttonClass="text-orange-600 dark:text-orange-400 hover:text-orange-700 dark:hover:text-orange-300"
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="bg-white dark:bg-dark-800 rounded-lg shadow overflow-hidden">
              <div className="px-5 sm:px-6 py-4 sm:py-5 border-b border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-700">
                <h2 className="text-lg sm:text-xl font-bold text-dark-900 dark:text-white">{t('analysis.clauses')}</h2>
                <p className="text-dark-500 dark:text-dark-400 text-sm sm:text-base mt-2">{t('analysis.clausesDesc')}</p>
              </div>
              <div className="divide-y divide-dark-100 dark:divide-dark-700">
                {[...clauses].sort((a, b) => {
                  const numA = parseClauseNumber(a.number);
                  const numB = parseClauseNumber(b.number);
                  return numA - numB;
                }).map((clause) => (
                  <div
                    key={clause.id}
                    style={getClauseBorderStyle(clause.category, expandedClause === clause.id)}
                  >
                    <button
                      onClick={() => setExpandedClause(expandedClause === clause.id ? null : clause.id)}
                      className="w-full px-5 sm:px-6 py-4 sm:py-5 hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors text-left"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          {getCategoryIcon(clause.category)}
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-dark-900 dark:text-white text-base sm:text-lg break-words mb-2">
                              {t('analysis.clauseLabel')} {clause.number}: {clause.title}
                            </p>
                            <p className="text-dark-600 dark:text-dark-400 text-sm sm:text-base mt-1 line-clamp-2 break-words leading-relaxed">{clause.technicalText}</p>
                          </div>
                        </div>
                        <FaChevronDown
                          className={`w-5 h-5 sm:w-6 sm:h-6 text-dark-400 dark:text-dark-500 transition-transform duration-200 flex-shrink-0 mt-1 ${expandedClause === clause.id ? 'rotate-180' : ''
                            }`}
                        />
                      </div>
                    </button>

                    {expandedClause === clause.id && (
                      <div className="px-5 sm:px-6 py-4 sm:py-5 bg-dark-50 dark:bg-dark-700 border-t border-dark-100 dark:border-dark-600">
                        <div className="space-y-4">
                          <div className="bg-white dark:bg-dark-800 rounded-lg p-4 sm:p-5">
                            <p className="text-sm sm:text-base font-semibold text-dark-900 dark:text-white mb-3">{t('analysis.explanation')}:</p>
                            <p className="text-dark-700 dark:text-dark-300 text-sm sm:text-base leading-relaxed break-words">{clause.plainLanguage}</p>
                          </div>

                          {clause.category === 'risk' && clause.recommendations && (
                            <div className="bg-white dark:bg-dark-800 border border-amber-400 dark:border-amber-500 rounded-lg p-4 sm:p-5">
                              <p className="text-sm sm:text-base font-semibold text-dark-900 dark:text-white mb-3">{t('analysis.recommendations')}:</p>
                              <p className="text-dark-700 dark:text-dark-300 text-sm sm:text-base leading-relaxed break-words">{clause.recommendations}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {relations.length > 0 ? (
              <div className="bg-white dark:bg-dark-800 rounded-lg shadow overflow-hidden mt-6 sm:mt-8">
                <div className="px-5 sm:px-6 py-4 sm:py-5 border-b border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-700">
                  <h2 className="text-lg sm:text-xl font-bold text-dark-900 dark:text-white">{t('relations.title')}</h2>
                  <p className="text-dark-500 dark:text-dark-400 text-sm sm:text-base mt-3">{t('relations.subtitle')}</p>
                </div>
                <div className="p-5 sm:p-6">
                  <ClauseRelationsGraph relations={relations} />
                </div>
              </div>
            ) : (
              <div className="bg-white dark:bg-dark-800 rounded-lg shadow p-5 sm:p-6 mt-6 sm:mt-8">
                <p className="text-dark-600 dark:text-dark-400 text-center text-sm sm:text-base">
                  {t('relations.noRelations')}
                </p>
              </div>
            )}

            <div className="flex justify-center gap-3 mt-8 sm:mt-10 pb-4 sm:pb-6">
              <button
                onClick={generatePDF}
                disabled={generatingPDF}
                className="inline-flex items-center gap-2 px-6 sm:px-8 py-3 sm:py-3.5 bg-primary-100 dark:bg-primary-900/30 hover:bg-primary-200 dark:hover:bg-primary-900/50 disabled:opacity-50 disabled:cursor-not-allowed text-primary-700 dark:text-primary-300 font-medium rounded-lg transition-colors duration-200 text-sm sm:text-base border border-primary-200 dark:border-primary-800"
              >
                {generatingPDF ? <FaSpinner className="w-4 h-4 animate-spin" /> : <FaFilePdf className="w-4 h-4" />}
                <span>{t('analysis.download')}</span>
              </button>
              <button
                onClick={() => navigate('/dashboard/agent', { state: { analyzedContract: { id: id, filename: analysisData?.filename || '' } } })}
                className="inline-flex items-center gap-2 px-6 sm:px-8 py-3 sm:py-3.5 bg-primary-100 dark:bg-primary-900/30 hover:bg-primary-200 dark:hover:bg-primary-900/50 text-primary-700 dark:text-primary-300 font-medium rounded-lg transition-colors duration-200 text-sm sm:text-base border border-primary-200 dark:border-primary-800"
                title={t('analysis.consultAgentTitle')}
              >
                <FaRobot className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
                <span>{t('analysis.consultAgent')}</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const parseClauseNumber = (numStr: string): number => {
  const num = parseInt(numStr.replace(/\D/g, ''));
  if (!isNaN(num)) return num;

  const lowerStr = numStr.toLowerCase().replace(/\s+/g, ' ').trim();

  const ordinalMap: Record<string, number> = {
    'primera': 1, 'primero': 1, '1º': 1, '1ª': 1,
    'segunda': 2, 'segundo': 2, '2º': 2, '2ª': 2,
    'tercera': 3, 'tercero': 3, '3º': 3, '3ª': 3,
    'cuarta': 4, 'cuarto': 4, '4º': 4, '4ª': 4,
    'quinta': 5, 'quinto': 5, '5º': 5, '5ª': 5,
    'sexta': 6, 'sexto': 6, '6º': 6, '6ª': 6,
    'séptima': 7, 'septima': 7, 'séptimo': 7, 'septimo': 7, '7º': 7, '7ª': 7,
    'octava': 8, 'octavo': 8, '8º': 8, '8ª': 8,
    'novena': 9, 'noveno': 9, '9º': 9, '9ª': 9,
    'décima': 10, 'decima': 10, 'décimo': 10, 'decimo': 10, '10º': 10, '10ª': 10,

    'undécima': 11, 'undecima': 11, 'undécimo': 11, 'undecimo': 11, 'onceava': 11, 'decimo primera': 11, 'décimo primera': 11, 'decimoprimera': 11,
    'duodécima': 12, 'duodecima': 12, 'duodécimo': 12, 'duodecimo': 12, 'doceava': 12, 'decimo segunda': 12, 'décimo segunda': 12, 'decimosegunda': 12,
    'decimotercera': 13, 'decimotercero': 13, 'treceava': 13, 'decimo tercera': 13, 'décimo tercera': 13, 'décimo tercero': 13, 'decimo tercero': 13,
    'decimocuarta': 14, 'decimocuarto': 14, 'catorceava': 14, 'decimo cuarta': 14, 'décimo cuarta': 14,
    'decimoquinta': 15, 'decimoquinto': 15, 'quinceava': 15, 'decimo quinta': 15, 'décimo quinta': 15,
    'decimosexta': 16, 'decimosexto': 16, 'dieciseisava': 16, 'decimo sexta': 16, 'décimo sexta': 16,
    'decimoséptima': 17, 'decimoseptima': 17, 'decimoséptimo': 17, 'decimoseptimo': 17, 'decimo septima': 17, 'décimo séptima': 17,
    'decimoctava': 18, 'decimoctavo': 18, 'dieciochoava': 18, 'decimo octava': 18, 'décimo octava': 18,
    'decimonovena': 19, 'decimonoveno': 19, 'diecinueveava': 19, 'decimo novena': 19, 'décimo novena': 19,

    'vigésima': 20, 'vigesima': 20, 'vigésimo': 20, 'vigesimo': 20, 'veinteava': 20,
    'vigésimo primera': 21, 'vigesimo primera': 21, 'vigesimoprimera': 21,
    'vigésimo segunda': 22, 'vigesimo segunda': 22, 'vigesimosegunda': 22,
    'vigésimo tercera': 23, 'vigesimo tercera': 23, 'vigesimotercera': 23,
    'vigésimo cuarta': 24, 'vigesimo cuarta': 24, 'vigesimocuarta': 24,
    'vigésimo quinta': 25, 'vigesimo quinta': 25, 'vigesimoquinta': 25,
    'vigésimo sexta': 26, 'vigesimo sexta': 26, 'vigesimosexta': 26,
    'vigésimo séptima': 27, 'vigesimo septima': 27, 'vigesimoseptima': 27,
    'vigésimo octava': 28, 'vigesimo octava': 28, 'vigesimooctava': 28,
    'vigésimo novena': 29, 'vigesimo novena': 29, 'vigesimonovena': 29,

    'trigésima': 30, 'trigesima': 30, 'trigésimo': 30, 'trigesimo': 30,
  };

  const sortedKeys = Object.keys(ordinalMap).sort((a, b) => b.length - a.length);

  for (const key of sortedKeys) {
    if (lowerStr.includes(key)) {
      return ordinalMap[key];
    }
  }

  const match = numStr.match(/\d+/);
  if (match) return parseInt(match[0]);

  return 9999;
};

const deduplicateFindings = <T extends { title: string }>(items: T[]): T[] => {
  const seen = new Set<string>();

  const normalizationMap: Record<string, string> = {
    'cumplimiento legal': 'cumplimiento de la ley',
    'cumplimiento normativo': 'cumplimiento de la ley'
  };

  return items.filter(item => {
    let normalizedTitle = item.title.toLowerCase().trim();

    if (normalizationMap[normalizedTitle]) {
      normalizedTitle = normalizationMap[normalizedTitle];
    }

    if (seen.has(normalizedTitle)) {
      return false;
    }
    seen.add(normalizedTitle);
    return true;
  });
};
