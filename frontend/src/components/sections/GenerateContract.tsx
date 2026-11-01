import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaFileContract, FaMagic, FaBalanceScale, FaLanguage, FaGlobe, FaEye, FaEdit, FaTrash, FaCheckCircle, FaClock, FaExclamationCircle } from 'react-icons/fa';
import { generatedContractsService, type GeneratedContract } from '../../services/generatedContracts';
import { useContractTypes } from '../../hooks/useContractTypes';
import ConfirmDeleteModal from '../ConfirmDeleteModal';
import { useNotifications } from '../../context/useNotifications';
import { useLanguage } from '../../context/useLanguage';
import { formatDateLong, formatDate } from '../../utils/formatDate';
import { useUsage } from '../../hooks/useUsage';
import UsageBadge from '../UsageBadge';
import { useToast } from '../../context/useToast';

export default function GenerateContract() {
  const { t, language } = useLanguage();
  const navigate = useNavigate();
  const { refreshNotifications } = useNotifications();
  const { usage, remainingGenerations, refresh: refreshUsage } = useUsage();
  const { showToast } = useToast();
  const [contractType, setContractType] = useState('');
  const { contractTypes, getLabel: contractTypeLabel } = useContractTypes();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  const [contracts, setContracts] = useState<GeneratedContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [contractToDelete, setContractToDelete] = useState<GeneratedContract | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadContracts = useCallback(async () => {
    try {
      const data = await generatedContractsService.getAll();
      setContracts(data);
    } catch (error) {
      console.error('Error loading contracts:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadContracts();
  }, [loadContracts]);

  useEffect(() => {
    const generatingContracts = contracts.filter(c => c.status === 'pending' || c.status === 'processing');
    if (generatingContracts.length === 0) return;

    const interval = setInterval(async () => {
      let updated = false;
      const updatedContracts = [...contracts];

      for (const contract of generatingContracts) {
        try {
          const freshData = await generatedContractsService.getById(contract.id);
          if (freshData.status !== 'pending') {
            const index = updatedContracts.findIndex(c => c.id === contract.id);
            if (index !== -1) {
              updatedContracts[index] = freshData;
              updated = true;
            }
          }
        } catch (e) {
          console.error("Error polling contract", contract.id, e);
        }
      }

      if (updated) {
        setContracts(updatedContracts);
        refreshNotifications();
      }

    }, 4000);

    return () => clearInterval(interval);
  }, [contracts, refreshNotifications]);

  const handleDeleteClick = (contract: GeneratedContract) => {
    setContractToDelete(contract);
    setDeleteModalOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!contractToDelete) return;
    setDeleting(true);
    try {
      await generatedContractsService.delete(contractToDelete.id);
      setContracts(contracts.filter(c => c.id !== contractToDelete.id));
      setDeleteModalOpen(false);
      setContractToDelete(null);
    } catch (error) {
      console.error('Error deleting contract:', error);
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteModalOpen(false);
    setContractToDelete(null);
  };

  const [tone, setTone] = useState('Legal Formal');
  const [partyA, setPartyA] = useState('');
  const [partyB, setPartyB] = useState('');

  const handleCreate = async () => {
    if (!contractType || !title) return;

    setCreating(true);
    try {
      const newContract = await generatedContractsService.create({
        title,
        contract_type: contractType,
        tone,
        contract_details: {
          parties: {
            partyA,
            partyB
          },
          description
        }
      });

      setContracts([newContract, ...contracts]);

      refreshNotifications();
      refreshUsage();

      setTitle('');
      setDescription('');
      setPartyA('');
      setPartyB('');
      setContractType('');
      setTone('Legal Formal');


    } catch (error: unknown) {
      console.error('Error creating contract:', error);
      const message = error instanceof Error ? error.message : 'Error al crear el contrato. Por favor, asegúrate de que el servidor está funcionando y los datos son correctos.';
      showToast(message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 bg-dark-50 dark:bg-dark-900 min-h-full">
      <div className="max-w-6xl mx-auto">

        {usage && usage.contracts_generated_limit !== null && (
          <div className="mb-6 bg-white dark:bg-dark-800 rounded-xl shadow-sm p-4 border border-dark-100 dark:border-dark-700">
            <UsageBadge
              used={usage.contracts_generated}
              limit={usage.contracts_generated_limit}
              label={t('generate.monthlyCount')}
            />
            {remainingGenerations !== null && remainingGenerations <= 0 && usage.generation_reset_date && (
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-2 text-center">
                {t('generate.resetDate')} {formatDateLong(usage.generation_reset_date, language)}
              </p>
            )}
          </div>
        )}


        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
          <div className="lg:col-span-2 space-y-6">

            <div className="bg-white dark:bg-dark-800 rounded-xl shadow-lg p-6 border border-dark-100 dark:border-dark-700">
              <h3 className="text-xl font-semibold text-dark-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400 w-8 h-8 rounded-full flex items-center justify-center text-sm">1</span>
                {t('generate.contractTypeLabel')}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {contractTypes.map((type) => {
                  const TypeIcon = type.id === 'prestacion_servicios' ? FaFileContract : FaBalanceScale;
                  return (
                  <div
                    key={type.id}
                    onClick={() => setContractType(type.id)}
                    className={`cursor-pointer p-4 rounded-lg border-2 transition-all flex items-center gap-3 ${contractType === type.id
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                      : 'border-dark-200 dark:border-dark-700 hover:border-primary-300 dark:hover:border-primary-700'
                      }`}
                  >
                    <TypeIcon className={`w-6 h-6 shrink-0 ${contractType === type.id ? 'text-primary-600 dark:text-primary-400' : 'text-dark-400'}`} />
                    <span className={`font-medium ${contractType === type.id ? 'text-primary-900 dark:text-primary-300' : 'text-dark-700 dark:text-dark-300'}`}>{type.label}</span>
                  </div>
                )})}
              </div>
            </div>

            <div className="bg-white dark:bg-dark-800 rounded-xl shadow-lg p-6 border border-dark-100 dark:border-dark-700">
              <h3 className="text-xl font-semibold text-dark-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400 w-8 h-8 rounded-full flex items-center justify-center text-sm">2</span>
                {t('generate.basicInfo')}
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                    {t('generate.contractTitle')}
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    placeholder={t('generate.contractTitlePlaceholder')}
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                    {t('generate.descriptionContext')}
                  </label>
                  <textarea
                    rows={4}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all resize-none"
                    placeholder={t('generate.descriptionPlaceholder')}
                  ></textarea>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-dark-800 rounded-xl shadow-lg p-6 border border-dark-100 dark:border-dark-700">
              <h3 className="text-xl font-semibold text-dark-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-400 w-8 h-8 rounded-full flex items-center justify-center text-sm">3</span>
                {t('generate.involvedParties')}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                    {t('generate.partyA')}
                  </label>
                  <input
                    type="text"
                    value={partyA}
                    onChange={(e) => setPartyA(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    placeholder={t('generate.partyPlaceholder')}
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-dark-700 dark:text-dark-300 mb-2">
                    {t('generate.partyB')}
                  </label>
                  <input
                    type="text"
                    value={partyB}
                    onChange={(e) => setPartyB(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    placeholder={t('generate.partyPlaceholder')}
                  />
                </div>
              </div>
            </div>

            <button
              onClick={handleCreate}
              disabled={!contractType || !title || creating || (remainingGenerations !== null && remainingGenerations <= 0)}
              className="w-full py-4 bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-700 hover:to-primary-600 text-white rounded-xl shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5 font-bold text-lg flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-lg"
            >
              <FaMagic className={creating ? "animate-spin" : ""} />
              {creating ? t('generate.generating') : (remainingGenerations !== null && remainingGenerations <= 0) ? t('generate.limitReached') : t('generate.generateDraft')}
            </button>

          </div>

          <div className="lg:col-span-1 space-y-6">

            <div className="bg-white dark:bg-dark-800 rounded-xl shadow-lg p-6 border border-dark-100 dark:border-dark-700 sticky top-6">
              <h3 className="text-lg font-bold text-dark-900 dark:text-white mb-4">{t('generate.configuration')}</h3>

              <div className="space-y-4">
                <div>
                  <label className="flex items-center gap-2 text-sm font-medium text-dark-700 dark:text-dark-300 mb-2">
                    <FaGlobe className="text-dark-400" /> {t('generate.jurisdiction')}
                  </label>
                  <select disabled className="w-full px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-dark-50 dark:bg-dark-900 text-dark-500 dark:text-dark-400 cursor-not-allowed">
                    <option>{t('generate.jurisdictionSpain')}</option>
                  </select>
                </div>

                <div>
                  <label className="flex items-center gap-2 text-sm font-medium text-dark-700 dark:text-dark-300 mb-2">
                    <FaLanguage className="text-dark-400" /> {t('generate.language')}
                  </label>
                  <select disabled className="w-full px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-dark-50 dark:bg-dark-900 text-dark-500 dark:text-dark-400 cursor-not-allowed">
                    <option>{t('generate.languageSpanish')}</option>
                  </select>
                </div>

                <div>
                  <label className="text-sm font-medium text-dark-700 dark:text-dark-300 mb-2 block">
                    {t('generate.tone')}
                  </label>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-700 text-dark-900 dark:text-white focus:ring-2 focus:ring-primary-500 outline-none"
                  >
                    <option value="Legal Formal">{t('generate.legalFormal')}</option>
                    <option value="Lenguaje claro">{t('generate.clearLanguage')}</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-16">
          <h3 className="text-2xl font-bold text-dark-900 dark:text-white mb-6 flex items-center gap-2">
            <FaFileContract className="text-dark-400" />
            {t('generate.myContracts')}
          </h3>

          <div className="bg-white dark:bg-dark-800 rounded-xl shadow-lg border border-dark-100 dark:border-dark-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-dark-50 dark:bg-dark-900/50 border-b border-dark-100 dark:border-dark-700">
                    <th className="px-6 py-4 text-xs font-semibold text-dark-500 dark:text-dark-400 uppercase tracking-wider">{t('generate.tableTitle')}</th>
                    <th className="px-6 py-4 text-xs font-semibold text-dark-500 dark:text-dark-400 uppercase tracking-wider">{t('generate.tableType')}</th>
                    <th className="px-6 py-4 text-xs font-semibold text-dark-500 dark:text-dark-400 uppercase tracking-wider">{t('generate.tableDate')}</th>
                    <th className="px-6 py-4 text-xs font-semibold text-dark-500 dark:text-dark-400 uppercase tracking-wider">{t('generate.tableStatus')}</th>
                    <th className="px-6 py-4 text-right text-xs font-semibold text-dark-500 dark:text-dark-400 uppercase tracking-wider">{t('generate.tableActions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-100 dark:divide-dark-700">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-dark-500">{t('generate.loadingContracts')}</td>
                    </tr>
                  ) : contracts.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-dark-500">{t('generate.noContracts')}</td>
                    </tr>
                  ) : (
                    contracts.map((contract) => (
                      <tr key={contract.id} className="hover:bg-dark-50 dark:hover:bg-dark-700/50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg text-primary-600 dark:text-primary-400">
                              <FaFileContract />
                            </div>
                            <span className="font-medium text-dark-900 dark:text-white">{contract.title}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-dark-600 dark:text-dark-300 text-sm">{contractTypeLabel(contract.contract_type)}</td>
                        <td className="px-6 py-4 text-dark-600 dark:text-dark-300 text-sm">
                          {formatDate(contract.created_at, language)}
                        </td>
                        <td className="px-6 py-4">
                          {contract.status === 'completed' ? (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-full text-xs font-medium">
                              <FaCheckCircle className="w-3 h-3" />
                              {t('generate.completed')}
                            </span>
                          ) : contract.status === 'pending' || contract.status === 'processing' ? (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full text-xs font-medium">
                              <div className="w-3 h-3 border-2 border-blue-700 dark:border-blue-300 border-t-transparent rounded-full animate-spin"></div>
                              {t('generate.pending')}
                            </span>
                          ) : contract.status === 'error' ? (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-full text-xs font-medium">
                              <FaExclamationCircle className="w-3 h-3" />
                              {t('generate.error')}
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-xs font-medium">
                              <FaClock className="w-3 h-3" />
                              {contract.status}
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {contract.status !== 'pending' && contract.status !== 'processing' && (
                              <>
                                <button
                                  onClick={() => navigate(`/dashboard/generate/${contract.id}`)}
                                  className="p-2 text-dark-600 dark:text-dark-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-950 rounded-lg transition-colors"
                                  title={t('generate.viewDetails')}
                                >
                                  <FaEye className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => navigate(`/dashboard/generate/${contract.id}/edit`)}
                                  className="p-2 text-dark-600 dark:text-dark-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-950 rounded-lg transition-colors"
                                  title={t('generate.edit')}
                                >
                                  <FaEdit className="w-4 h-4" />
                                </button>
                              </>
                            )}
                            {contract.status !== 'pending' && contract.status !== 'processing' && (
                              <button
                                onClick={() => handleDeleteClick(contract)}
                                className="p-2 text-dark-600 dark:text-dark-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                title={t('generate.delete')}
                              >
                                <FaTrash className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )))}
                </tbody>
              </table>
            </div>

            <div className="md:hidden divide-y divide-dark-100 dark:divide-dark-700">
              {loading ? (
                <div className="p-6 text-center text-dark-500">{t('generate.loadingContracts')}</div>
              ) : contracts.map((contract) => (
                <div key={contract.id} className="p-4 space-y-3">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary-50 dark:bg-primary-900/20 rounded-lg text-primary-600 dark:text-primary-400">
                        <FaFileContract />
                      </div>
                      <div>
                        <h4 className="font-medium text-dark-900 dark:text-white">{contract.title}</h4>
                        <span className="text-xs text-dark-500 dark:text-dark-400">{contractTypeLabel(contract.contract_type)}</span>
                      </div>
                    </div>
                    {contract.status === 'completed' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded-full text-xs font-medium">
                        <FaCheckCircle className="w-3 h-3" />
                        {t('generate.completed')}
                      </span>
                    ) : contract.status === 'pending' || contract.status === 'processing' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full text-xs font-medium">
                        <div className="w-3 h-3 border-2 border-blue-700 dark:border-blue-300 border-t-transparent rounded-full animate-spin"></div>
                        {t('generate.pending')}
                      </span>
                    ) : contract.status === 'error' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded-full text-xs font-medium">
                        <FaExclamationCircle className="w-3 h-3" />
                        {t('generate.error')}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-xs font-medium">
                        <FaClock className="w-3 h-3" />
                        {contract.status}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between pt-2">
                    <span className="text-sm text-dark-500 dark:text-dark-400">
                      {formatDate(contract.created_at, language)}
                    </span>
                    <div className="flex items-center gap-1">
                      {contract.status !== 'pending' && contract.status !== 'processing' && (
                        <>
                          <button
                            onClick={() => navigate(`/dashboard/generate/${contract.id}`)}
                            className="p-2 text-dark-600 dark:text-dark-400 hover:text-primary-600 dark:hover:text-primary-400 bg-dark-50 dark:bg-dark-700 rounded-lg"
                          >
                            <FaEye />
                          </button>
                          <button
                            onClick={() => navigate(`/dashboard/generate/${contract.id}/edit`)}
                            className="p-2 text-dark-600 dark:text-dark-400 hover:text-primary-600 dark:hover:text-primary-400 bg-dark-50 dark:bg-dark-700 rounded-lg"
                          >
                            <FaEdit />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <ConfirmDeleteModal
        isOpen={deleteModalOpen}
        contractName={contractToDelete?.title || ''}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        isLoading={deleting}
        title={t('generate.deleteTitle')}
        description={t('generate.deleteDescription')}
        warningItems={[
          t('generate.deleteWarning1'),
          t('generate.deleteWarning2'),
          t('generate.deleteWarning3')
        ]}
        confirmNote={t('generate.deleteConfirm')}
      />
    </div>
  );
}
