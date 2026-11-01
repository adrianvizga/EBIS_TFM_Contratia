import { useState, useEffect, useCallback } from 'react';
import { FaCheckCircle, FaExclamationCircle, FaFile, FaClock, FaRobot, FaFileContract } from 'react-icons/fa';
import { useLanguage } from '../../context/useLanguage';
import { useAuthFetch } from '../../hooks/useAuthFetch';
import { API_ORIGIN } from '../../config/api';

interface Contract {
  id: string;
  filename: string;
  uploadDate: string;
  status: 'completed' | 'analyzing' | 'failed' | 'uploaded';
  riskLevel: 'high' | 'medium' | 'low' | 'none';
  riskCount: number;
  positiveCount: number;
  errorMessage?: string;
}

interface GeneratedContract {
  id: string;
  title: string;
  status: string;
}

const API_BASE = API_ORIGIN;

export default function Dashboard() {
  const { t } = useLanguage();
  const authFetch = useAuthFetch();
  const [analyzedContracts, setAnalyzedContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState([
    { label: t('dashboard.contractsGenerated'), value: '0', color: 'bg-primary-100', textColor: 'text-primary-700', icon: FaFileContract },
    { label: t('dashboard.agentQueries'), value: '0', color: 'bg-purple-100 dark:bg-purple-900/20', textColor: 'text-purple-700 dark:text-purple-400', icon: FaRobot },
    { label: t('dashboard.contractsAnalyzed'), value: '0', color: 'bg-accent-green/10', textColor: 'text-accent-green', icon: FaCheckCircle },
    { label: t('dashboard.pendingTasks'), value: '0', color: 'bg-accent-amber/10', textColor: 'text-accent-amber', icon: FaClock },
  ]);

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);

      const [contractsRes, generatedRes, conversationsRes] = await Promise.all([
        authFetch(`${API_BASE}/api/contracts`),
        authFetch(`${API_BASE}/api/generated-contracts`),
        authFetch(`${API_BASE}/api/agent/conversations`),
      ]);

      let analyzed = 0;
      let analysisPending = 0;
      let contractsData: Contract[] = [];

      if (contractsRes.ok) {
        contractsData = await contractsRes.json();
        analyzed = contractsData.filter(c => c.status === 'completed').length;
        analysisPending = contractsData.filter(c => c.status === 'analyzing' || c.status === 'uploaded').length;
        setAnalyzedContracts(contractsData.slice(0, 5));
      }

      let generatedCount = 0;
      let generationPending = 0;

      if (generatedRes.ok) {
        const generatedData: GeneratedContract[] = await generatedRes.json();
        generatedCount = generatedData.length;
        generationPending = generatedData.filter(c => c.status === 'pending').length;
      }

      let agentQueries = 0;

      if (conversationsRes.ok) {
        const conversationsData = await conversationsRes.json();
        agentQueries = Array.isArray(conversationsData) ? conversationsData.length : 0;
      }

      const totalPending = analysisPending + generationPending;

      setStats([
        { label: t('dashboard.contractsGenerated'), value: generatedCount.toString(), color: 'bg-primary-100 dark:bg-primary-900/20', textColor: 'text-primary-700 dark:text-primary-400', icon: FaFileContract },
        { label: t('dashboard.agentQueries'), value: agentQueries.toString(), color: 'bg-purple-100 dark:bg-purple-900/20', textColor: 'text-purple-700 dark:text-purple-400', icon: FaRobot },
        { label: t('dashboard.contractsAnalyzed'), value: analyzed.toString(), color: 'bg-accent-green/10', textColor: 'text-accent-green', icon: FaCheckCircle },
        { label: t('dashboard.pendingTasks'), value: totalPending.toString(), color: 'bg-accent-amber/10', textColor: 'text-accent-amber', icon: FaClock },
      ]);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [authFetch, t]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full text-sm font-medium">
            <FaCheckCircle className="w-3 h-3" />
            {t('dashboard.completed')}
          </span>
        );
      case 'analyzing':
      case 'uploaded':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
            <div className="w-3 h-3 border-2 border-blue-700 dark:border-blue-300 border-t-transparent rounded-full animate-spin"></div>
            {t('dashboard.inProgress')}
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-full text-sm font-medium">
            <FaExclamationCircle className="w-3 h-3" />
            {t('dashboard.error')}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-sm font-medium">
            <FaClock className="w-3 h-3" />
            {status}
          </span>
        );
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 lg:space-y-8 bg-dark-50 dark:bg-dark-900">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        {stats.map((stat, index) => (
          <div key={index} className="bg-white dark:bg-dark-800 p-4 sm:p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow border border-dark-100 dark:border-dark-700">
            <div className="flex items-center justify-between">
              <p className="text-dark-600 dark:text-dark-400 text-xs sm:text-sm font-medium">{stat.label}</p>
              <stat.icon className={`w-5 h-5 ${stat.textColor} opacity-60`} />
            </div>
            <p className={`text-3xl sm:text-4xl font-bold mt-2 ${stat.textColor}`}>{stat.value}</p>
            <div className={`mt-3 sm:mt-4 h-1 rounded-full ${stat.color}`}></div>
          </div>
        ))}
      </div>

      <div className="bg-white dark:bg-dark-800 rounded-xl shadow-sm overflow-hidden border border-dark-100 dark:border-dark-700">
        <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-700 flex justify-between items-center">
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-dark-900 dark:text-white">{t('dashboard.recentActivity')}</h2>
            <p className="text-dark-500 dark:text-dark-400 text-xs sm:text-sm mt-1">{t('dashboard.recentActivityDesc')}</p>
          </div>
          {loading && <div className="w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>}
        </div>
        <div className="divide-y divide-dark-200 dark:divide-dark-700">
          {!loading && analyzedContracts.length === 0 && (
            <div className="p-8 text-center text-dark-500 dark:text-dark-400">
              {t('dashboard.noActivity')}
            </div>
          )}
          {analyzedContracts.map((contract) => (
            <div key={contract.id} className="px-4 sm:px-6 py-3 sm:py-4 hover:bg-dark-50 dark:hover:bg-dark-700 transition-colors">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
                <div className="flex items-start gap-2 sm:gap-3 flex-1 min-w-0 w-full sm:w-auto">
                  <FaFile className="w-4 h-4 text-dark-400 dark:text-dark-500 flex-shrink-0 mt-1 sm:mt-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-dark-900 dark:text-white text-sm sm:text-base truncate">{contract.filename}</p>
                    <p className="text-xs sm:text-sm text-dark-500 dark:text-dark-400 mt-0.5">{contract.uploadDate}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 w-full sm:w-auto justify-end">
                  {getStatusBadge(contract.status)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
