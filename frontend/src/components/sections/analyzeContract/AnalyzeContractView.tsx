import { FaCloudUploadAlt, FaExclamationCircle, FaFile, FaFilePdf, FaTrash, FaExclamationTriangle, FaSpinner } from 'react-icons/fa';
import ConfirmDeleteModal from '../../ConfirmDeleteModal';
import ErrorModal from '../../ErrorModal';
import UsageBadge from '../../UsageBadge';
import type { AnalyzeContractController } from './useAnalyzeContractController';
import { formatDateLong, formatDateTime } from '../../../utils/formatDate';
import { ContractRiskBadge, ContractStatusBadge } from './ContractBadges';

export function AnalyzeContractView(props: AnalyzeContractController) {
  const {
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
  } = props;
  return (
    <div className="p-4 sm:p-6 lg:p-8 bg-dark-50 dark:bg-dark-900">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white dark:bg-dark-800 rounded-xl shadow-sm p-4 sm:p-6 lg:p-8 mb-6 lg:mb-8 border border-dark-100 dark:border-dark-700">
          <div className="flex items-start justify-between mb-2 flex-wrap gap-3">
            <div>
              <h2 className="text-xl sm:text-2xl font-bold text-dark-900 dark:text-white mb-2">{t('analyze.upload')}</h2>
              <p className="text-dark-500 dark:text-dark-400 text-sm sm:text-base mb-4 sm:mb-6">{t('analyze.uploadDesc')}</p>
            </div>
            {usage && usage.contracts_analyzed_limit !== null && (
              <div className="w-48">
                <UsageBadge
                  used={usage.contracts_analyzed}
                  limit={usage.contracts_analyzed_limit}
                  label={t('analyze.analysisThisMonth')}
                />
                {remainingAnalyses !== null && remainingAnalyses <= 0 && usage.analysis_reset_date && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-2 text-center">
                    {t('analyze.resetDate')} {formatDateLong(usage.analysis_reset_date, language)}
                  </p>
                )}
              </div>
            )}
          </div>

          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-6 sm:p-8 lg:p-12 text-center transition-all cursor-pointer ${isDragging
              ? 'border-primary-500 bg-primary-50 dark:border-primary-600 dark:bg-dark-700'
              : 'border-primary-300 bg-primary-50 dark:border-primary-700 dark:bg-dark-700 hover:border-primary-500 dark:hover:border-primary-600'
              }`}
          >
            <div className="flex flex-col items-center">
              <FaCloudUploadAlt className={`w-12 h-12 sm:w-16 sm:h-16 mb-3 sm:mb-4 transition-colors ${isDragging ? 'text-primary-700 dark:text-primary-500' : 'text-primary-600 dark:text-primary-400'}`} />
              <p className={`text-base sm:text-lg font-medium mb-2 ${isDragging ? 'text-dark-900 dark:text-white' : 'text-dark-900 dark:text-white'}`}>
                {isDragging ? t('analyze.dropHere') : t('analyze.dragHere')}
              </p>
              <p className="text-dark-500 dark:text-dark-400 text-xs sm:text-sm mb-3 sm:mb-4">{t('analyze.or')}</p>
              <label className="inline-block">
                <span className="bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white font-medium py-2 px-4 sm:px-6 rounded-lg transition-colors cursor-pointer text-sm sm:text-base">
                  {t('analyze.uploadButton')}
                </span>
                <input
                  type="file"
                  onChange={handleFileInput}
                  accept=".pdf,.docx,.txt"
                  className="hidden"
                />
              </label>
              <p className="text-dark-400 dark:text-dark-500 text-xs mt-4">{t('analyze.supportedFormats')}</p>
            </div>
          </div>
          {uploadError && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20 px-4 py-3 text-sm text-red-700 dark:text-red-300">
              <FaExclamationCircle className="mt-0.5 shrink-0 w-4 h-4" />
              <span>{uploadError}</span>
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-dark-800 rounded-xl shadow-sm overflow-hidden border border-dark-100 dark:border-dark-700">
          <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-700">
            <h3 className="text-lg sm:text-xl font-bold text-dark-900 dark:text-white">{t('analyze.recentAnalysis')}</h3>
            <p className="text-dark-500 dark:text-dark-400 text-xs sm:text-sm mt-1">{analyzedContracts.length} {t('analyze.contractsInHistory')}</p>
          </div>

          {analyzedContracts.length > 0 && (
            <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-dark-200 dark:border-dark-700 bg-dark-50 dark:bg-dark-800 space-y-3">
              <input
                type="text"
                placeholder={t('analyze.searchPlaceholder')}
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-4 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 dark:placeholder-dark-500 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-primary-600 transition-all"
              />

              <div className="flex flex-col sm:flex-row gap-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 flex-1 w-full">
                  <div>
                    <label className="block text-xs font-medium text-dark-600 dark:text-dark-400 mb-1">
                      {t('analyze.filterStatus')}
                    </label>
                    <select
                      value={filterStatus}
                      onChange={(e) => {
                        setFilterStatus(e.target.value);
                        setCurrentPage(1);
                      }}
                      className="w-full px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-primary-600 transition-all"
                    >
                      <option value="all">{t('analyze.filterAll')}</option>
                      <option value="completed">{t('analyze.filterCompleted')}</option>
                      <option value="analyzing">{t('analyze.filterProcessing')}</option>
                      <option value="pending">{t('analyze.filterPending')}</option>
                      <option value="error">{t('analyze.filterError')}</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-dark-600 dark:text-dark-400 mb-1">
                      {t('analyze.filterRiskLevel')}
                    </label>
                    <select
                      value={filterRiskLevel}
                      onChange={(e) => {
                        setFilterRiskLevel(e.target.value);
                        setCurrentPage(1);
                      }}
                      className="w-full px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-primary-600 transition-all"
                    >
                      <option value="all">{t('analyze.filterAll')}</option>
                      <option value="high">{t('analyze.filterHigh')}</option>
                      <option value="medium">{t('analyze.filterMedium')}</option>
                      <option value="low">{t('analyze.filterLow')}</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-dark-600 dark:text-dark-400 mb-1">
                      {t('analyze.filterDateFrom')}
                    </label>
                    <input
                      type="date"
                      value={filterDateFrom}
                      onChange={(e) => {
                        setFilterDateFrom(e.target.value);
                        setCurrentPage(1);
                      }}
                      className="w-full px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-primary-600 transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-dark-600 dark:text-dark-400 mb-1">
                      {t('analyze.filterDateTo')}
                    </label>
                    <input
                      type="date"
                      value={filterDateTo}
                      onChange={(e) => {
                        setFilterDateTo(e.target.value);
                        setCurrentPage(1);
                      }}
                      className="w-full px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:focus:ring-primary-600 transition-all"
                    />
                  </div>
                </div>

                <div className="flex items-end w-full sm:w-auto">
                  <button
                    onClick={() => {
                      setSearchTerm('');
                      setFilterStatus('all');
                      setFilterRiskLevel('all');
                      setFilterDateFrom('');
                      setFilterDateTo('');
                      setCurrentPage(1);
                    }}
                    disabled={filterStatus === 'all' && filterRiskLevel === 'all' && !filterDateFrom && !filterDateTo && !searchTerm}
                    className="w-full sm:w-auto px-4 py-2.5 bg-dark-200 dark:bg-dark-700 text-dark-700 dark:text-dark-300 hover:bg-dark-300 dark:hover:bg-dark-600 rounded-lg transition-colors text-sm font-medium whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed h-10"
                    title={t('analyze.clearFiltersTitle')}
                  >
                    {t('analyze.clearFilters')}
                  </button>
                </div>
              </div>
            </div>
          )}

          {loading ? (
            <div className="px-4 sm:px-6 py-8 sm:py-12 text-center">
              <FaSpinner className="w-10 h-10 sm:w-12 sm:h-12 mx-auto text-primary-600 dark:text-primary-400 mb-3 sm:mb-4 animate-spin" />
              <p className="text-dark-500 dark:text-dark-400 text-sm sm:text-base">{t('analyze.loadingContracts')}</p>
            </div>
          ) : error ? (
            <div className="px-4 sm:px-6 py-8 sm:py-12 text-center">
              <FaExclamationCircle className="w-10 h-10 sm:w-12 sm:h-12 mx-auto text-red-600 dark:text-red-400 mb-3 sm:mb-4" />
              <p className="text-red-600 dark:text-red-400 text-sm sm:text-base font-medium">{t('analyze.errorLoadingContracts')}</p>
              <p className="text-dark-500 dark:text-dark-400 text-xs sm:text-sm mt-2">{error}</p>
              <button
                onClick={fetchContracts}
                className="mt-4 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
              >
                {t('analyze.retry')}
              </button>
            </div>
          ) : analyzedContracts.length === 0 ? (
            <div className="px-4 sm:px-6 py-8 sm:py-12 text-center">
              <FaFile className="w-10 h-10 sm:w-12 sm:h-12 mx-auto text-dark-300 dark:text-dark-600 mb-3 sm:mb-4" />
              <p className="text-dark-500 dark:text-dark-400 text-sm sm:text-base">{t('analyze.noContracts')}</p>
              <p className="text-dark-400 dark:text-dark-500 text-xs sm:text-sm mt-2">{t('analyze.uploadFirst')}</p>
            </div>
          ) : (
            <>
              {(() => {
                if (filteredContracts.length === 0) {
                  return (
                    <div className="px-4 sm:px-6 py-8 sm:py-12 text-center">
                      <FaFile className="w-10 h-10 sm:w-12 sm:h-12 mx-auto text-dark-300 dark:text-dark-600 mb-3 sm:mb-4" />
                      <p className="text-dark-500 dark:text-dark-400 text-sm sm:text-base">{t('analyze.noResults')}</p>
                      <p className="text-dark-400 dark:text-dark-500 text-xs sm:text-sm mt-2">{t('analyze.adjustFilters')}</p>
                    </div>
                  );
                }

                return (
                  <>
                    <div className="hidden md:block overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-700">
                            <th className="px-6 py-3 text-left text-sm font-semibold text-dark-900 dark:text-white">{t('analyze.filename')}</th>
                            <th className="px-2 py-3 text-left text-sm font-semibold text-dark-900 dark:text-white">{t('analyze.type')}</th>
                            <th className="px-6 py-3 text-left text-sm font-semibold text-dark-900 dark:text-white">{t('analyze.uploadDate')}</th>
                            <th className="px-6 py-3 text-left text-sm font-semibold text-dark-900 dark:text-white">{t('analyze.status')}</th>
                            <th className="px-6 py-3 text-left text-sm font-semibold text-dark-900 dark:text-white">{t('analyze.riskLevel')}</th>
                            <th className="px-6 py-3 text-right text-sm font-semibold text-dark-900 dark:text-white">{t('analyze.actions')}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-dark-100 dark:divide-dark-700">
                          {currentContracts.map(contract => (
                            <tr
                              key={contract.id}
                              onClick={() => contract.status === 'completed' && navigate(`/dashboard/analyze/${contract.id}`)}
                              className={`transition-colors ${contract.status === 'completed' ? 'hover:bg-dark-50 dark:hover:bg-dark-700 cursor-pointer' : 'hover:bg-dark-50 dark:hover:bg-dark-700'}`}
                            >
                              <td className="px-6 py-4 max-w-xs">
                                <div
                                  className="flex items-center gap-3"
                                  title={contract.filename}
                                >
                                  <FaFile className="w-4 h-4 text-dark-400 dark:text-dark-500 flex-shrink-0" />
                                  <span className="font-medium text-dark-900 dark:text-white truncate">
                                    {getFilenameParts(contract.filename).displayName}
                                  </span>
                                </div>
                              </td>
                              <td className="px-2 py-4 text-dark-700 dark:text-dark-300 text-sm">
                                {getFilenameParts(contract.filename).extension}
                              </td>
                              <td className="px-6 py-4 text-dark-700 dark:text-dark-300">{formatDateTime(contract.uploadDate, language)}</td>
                              <td className="px-6 py-4">
                                <ContractStatusBadge status={contract.status} t={t} />
                              </td>
                              <td className="px-6 py-4">
                                <ContractRiskBadge level={contract.riskLevel} status={contract.status} t={t} />
                              </td>
                              <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                                <div className="flex gap-2 justify-end">
                                  {contract.status === 'error' && (
                                    <button
                                      onClick={() => showError(contract)}
                                      className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors cursor-pointer"
                                      title={t('analyze.viewError')}
                                    >
                                      <FaExclamationTriangle className="w-4 h-4" />
                                    </button>
                                  )}
                                  <button
                                    onClick={() => generatePDF(contract.id)}
                                    disabled={contract.status !== 'completed' || generatingPDFs.has(contract.id)}
                                    title="Descargar PDF"
                                    className={`p-2 rounded-lg transition-colors ${contract.status === 'completed' && !generatingPDFs.has(contract.id) ? 'text-dark-600 dark:text-dark-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 cursor-pointer' : 'text-dark-300 dark:text-dark-600 cursor-not-allowed opacity-50'}`}
                                  >
                                    {generatingPDFs.has(contract.id) ? <FaSpinner className="w-4 h-4 animate-spin" /> : <FaFilePdf className="w-4 h-4" />}
                                  </button>
                                  <button
                                    onClick={() => deleteContract(contract.id)}
                                    className="p-2 text-dark-600 dark:text-dark-400 hover:bg-red-50 dark:hover:bg-red-950 hover:text-red-600 dark:hover:text-red-400 rounded-lg transition-colors cursor-pointer"
                                    title={t('analyze.delete')}
                                  >
                                    <FaTrash className="w-4 h-4" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="md:hidden divide-y divide-dark-200 dark:divide-dark-700">
                      {currentContracts.map(contract => (
                        <div
                          key={contract.id}
                          onClick={() => contract.status === 'completed' && navigate(`/dashboard/analyze/${contract.id}`)}
                          className={`p-4 transition-colors ${contract.status === 'completed' ? 'hover:bg-dark-50 dark:hover:bg-dark-700 cursor-pointer' : 'hover:bg-dark-50 dark:hover:bg-dark-700'}`}
                        >
                          <div className="space-y-3">
                            <div
                              className="flex items-start gap-2"
                              title={contract.filename}
                            >
                              <FaFile className="w-4 h-4 text-dark-400 dark:text-dark-500 flex-shrink-0 mt-0.5" />
                              <span className="font-medium text-dark-900 dark:text-white text-sm flex-1">
                                {getFilenameParts(contract.filename, 35).displayName}
                              </span>
                              <span className="text-dark-700 dark:text-dark-300 text-sm">
                                {getFilenameParts(contract.filename, 35).extension}
                              </span>
                            </div>

                            <div className="flex items-center justify-between gap-2 flex-wrap">
                              <span className="text-xs text-dark-500 dark:text-dark-400">{formatDateTime(contract.uploadDate, language)}</span>
                              <ContractStatusBadge status={contract.status} t={t} />
                            </div>

                            <div>
                              <ContractRiskBadge level={contract.riskLevel} status={contract.status} t={t} />
                            </div>

                            <div className="flex gap-2 pt-2 border-t border-dark-100 dark:border-dark-700" onClick={(e) => e.stopPropagation()}>
                              {contract.status === 'error' && (
                                <button
                                  onClick={() => showError(contract)}
                                  className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors"
                                  title={t('analyze.viewError')}
                                >
                                  <FaExclamationTriangle className="w-4 h-4" />
                                </button>
                              )}
                              <button
                                onClick={() => generatePDF(contract.id)}
                                disabled={contract.status !== 'completed' || generatingPDFs.has(contract.id)}
                                className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${contract.status === 'completed' && !generatingPDFs.has(contract.id) ? 'bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900' : 'bg-dark-100 dark:bg-dark-700 text-dark-400 dark:text-dark-500 cursor-not-allowed'}`}
                              >
                                {generatingPDFs.has(contract.id) ? <FaSpinner className="w-4 h-4 animate-spin" /> : <FaFilePdf className="w-4 h-4" />}
                                <span>{t('analyze.download')}</span>
                              </button>
                              <button
                                onClick={() => deleteContract(contract.id)}
                                className="p-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-colors"
                              >
                                <FaTrash className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {totalPages > 1 && (
                      <div className="px-4 sm:px-6 py-4 border-t border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-700 flex items-center justify-center gap-2">
                        <button
                          onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                          disabled={currentPage === 1}
                          className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 hover:bg-dark-50 dark:hover:bg-dark-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                        >
                          ←
                        </button>

                        <div className="flex gap-1">
                          {(() => {
                            const pageNumbers = [];
                            const maxVisible = 5;
                            let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
                            const endPage = Math.min(totalPages, startPage + maxVisible - 1);

                            if (endPage - startPage + 1 < maxVisible) {
                              startPage = Math.max(1, endPage - maxVisible + 1);
                            }

                            if (startPage > 1) {
                              pageNumbers.push(
                                <button
                                  key={1}
                                  onClick={() => setCurrentPage(1)}
                                  className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors text-sm font-medium"
                                >
                                  1
                                </button>
                              );
                              if (startPage > 2) {
                                pageNumbers.push(
                                  <span key="dots1" className="px-2 py-2 text-dark-400 dark:text-dark-500">...</span>
                                );
                              }
                            }

                            for (let i = startPage; i <= endPage; i++) {
                              pageNumbers.push(
                                <button
                                  key={i}
                                  onClick={() => setCurrentPage(i)}
                                  className={`px-3 py-2 rounded-lg border transition-colors text-sm font-medium ${currentPage === i
                                    ? 'bg-primary-600 dark:bg-primary-600 border-primary-600 text-white'
                                    : 'border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 hover:bg-dark-50 dark:hover:bg-dark-700'
                                    }`}
                                >
                                  {i}
                                </button>
                              );
                            }

                            if (endPage < totalPages) {
                              if (endPage < totalPages - 1) {
                                pageNumbers.push(
                                  <span key="dots2" className="px-2 py-2 text-dark-400 dark:text-dark-500">...</span>
                                );
                              }
                              pageNumbers.push(
                                <button
                                  key={totalPages}
                                  onClick={() => setCurrentPage(totalPages)}
                                  className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors text-sm font-medium"
                                >
                                  {totalPages}
                                </button>
                              );
                            }

                            return pageNumbers;
                          })()}
                        </div>

                        <button
                          onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                          disabled={currentPage === totalPages}
                          className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-300 hover:bg-dark-50 dark:hover:bg-dark-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                        >
                          →
                        </button>
                      </div>
                    )}
                  </>
                );
              })()}
            </>
          )}
        </div>
      </div>

      {contractToDelete && (
        <ConfirmDeleteModal
          isOpen={deleteModalOpen}
          contractName={contractToDelete.filename}
          onConfirm={confirmDelete}
          onCancel={cancelDelete}
        />
      )}

      {/* Modal de error */}
      {contractWithError && (
        <ErrorModal
          isOpen={errorModalOpen}
          errorMessage={contractWithError.errorMessage || 'Error desconocido'}
          filename={contractWithError.filename}
          onClose={closeErrorModal}
          onRetry={retryAnalysis}
        />
      )}
    </div>
  );;
}
