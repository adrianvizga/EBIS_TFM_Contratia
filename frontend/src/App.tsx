import { lazy, Suspense, useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import ScrollToTop from './components/ScrollToTop';
import ProtectedRoute from './components/ProtectedRoute';
import { useLanguage } from './context/useLanguage';
import { useUser } from './context/useUser';
import './App.css';

const Dashboard = lazy(() => import('./components/sections/Dashboard'));
const ViewGeneratedContract = lazy(() => import('./components/sections/ViewGeneratedContract'));
const EditGeneratedContract = lazy(() => import('./components/sections/EditGeneratedContract'));
const GenerateContract = lazy(() => import('./components/sections/GenerateContract'));
const AnalyzeContract = lazy(() => import('./components/sections/AnalyzeContract'));
const ContractAnalysis = lazy(() => import('./components/sections/ContractAnalysis'));
const Agent = lazy(() => import('./components/sections/Agent'));
const Settings = lazy(() => import('./components/sections/Settings'));
const SignIn = lazy(() => import('./pages/SignIn'));
const SignUp = lazy(() => import('./pages/SignUp'));
const ResetPassword = lazy(() => import('./pages/ResetPassword'));
const LegalDocument = lazy(() => import('./pages/LegalDocument'));

const RouteLoadingFallback = () => (
  <div
    className="flex min-h-64 items-center justify-center bg-dark-50 dark:bg-dark-900"
    role="status"
    aria-live="polite"
  >
    <div className="text-center">
      <div
        className="mx-auto mb-3 h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-500 dark:border-dark-700 dark:border-t-primary-400"
        aria-hidden="true"
      />
      <span className="text-dark-600 dark:text-dark-400">Cargando...</span>
    </div>
  </div>
);

interface Section {
  id: string;
  titleKey: string;
  subtitleKey: string;
}

const sections: Section[] = [
  { id: 'dashboard', titleKey: 'dashboard.title', subtitleKey: 'dashboard.subtitle' },
  { id: 'generate', titleKey: 'generate.title', subtitleKey: 'generate.subtitle' },
  { id: 'analyze', titleKey: 'analyze.title', subtitleKey: 'analyze.subtitle' },
  { id: 'agent', titleKey: 'agent.title', subtitleKey: 'agent.subtitle' },
  { id: 'settings', titleKey: 'settings.title', subtitleKey: 'settings.subtitle' },
];

function App() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const { t } = useLanguage();
  const { isAuthenticated, isLoading } = useUser();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const mainElement = document.querySelector('main');
    if (mainElement) {
      mainElement.scrollTo(0, 0);
    }
  }, [location.pathname]);

  const isAuthRoute = ['/signin', '/signup', '/reset-password', '/terms', '/privacy'].includes(location.pathname);

  const handleSectionChange = (sectionId: string) => {
    const routes: Record<string, string> = {
      dashboard: '/dashboard',
      generate: '/dashboard/generate',
      analyze: '/dashboard/analyze',
      agent: '/dashboard/agent',
      settings: '/dashboard/settings',
    };
    navigate(routes[sectionId] || '/dashboard');
    setIsMobileMenuOpen(false);
  };

  const handleBackFromAnalysis = () => {
    navigate('/dashboard/analyze');
  };

  const getCurrentSection = () => {
    const path = location.pathname;
    if (path.includes('/generate')) return sections[1];
    if (path.includes('/analyze')) return sections[2];
    if (path.includes('/agent')) return sections[3];
    if (path.includes('/settings')) return sections[4];
    return sections[0];
  };

  const currentSection = getCurrentSection();
  const activeSection = currentSection.id;

  if (isAuthRoute) {
    return (
      <Suspense fallback={<RouteLoadingFallback />}>
        <Routes>
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/terms" element={<LegalDocument type="terms" />} />
          <Route path="/privacy" element={<LegalDocument type="privacy" />} />
        </Routes>
      </Suspense>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-dark-50 dark:bg-dark-900">
        <div className="text-center">
          <div className="flex items-center justify-center mb-4">
            <img src="/logo-icon.png" alt="ContratIA" className="w-16 h-16 object-contain animate-pulse" />
          </div>
          <p className="text-dark-600 dark:text-dark-400">Cargando...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/signin" replace />;
  }

  return (
    <div className="flex h-screen bg-dark-50 dark:bg-dark-900">
      <div className={`
        fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 ease-in-out
        lg:relative lg:translate-x-0
        ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <Sidebar activeSection={activeSection} onSectionChange={handleSectionChange} />
      </div>

      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      <div className="flex-1 flex flex-col overflow-hidden w-full">
        <Header
          title={location.pathname.match(/\/analizar\/\d+/) ? t('analysis.title') : t(currentSection.titleKey)}
          subtitle={location.pathname.match(/\/analizar\/\d+/) ? t('analysis.subtitle') : t(currentSection.subtitleKey)}
          onMenuClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        />
        <main className="flex-1 overflow-y-auto bg-dark-50 dark:bg-dark-900">
          <Suspense fallback={<RouteLoadingFallback />}>
            <Routes>
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/dashboard/generate" element={<ProtectedRoute><GenerateContract /></ProtectedRoute>} />
              <Route path="/dashboard/generate/:id" element={<ProtectedRoute><ViewGeneratedContract /></ProtectedRoute>} />
              <Route path="/dashboard/generate/:id/edit" element={<ProtectedRoute><EditGeneratedContract /></ProtectedRoute>} />
              <Route path="/dashboard/analyze" element={<ProtectedRoute><AnalyzeContract /></ProtectedRoute>} />
              <Route path="/dashboard/analyze/:id" element={<ProtectedRoute><ContractAnalysis onBack={handleBackFromAnalysis} /></ProtectedRoute>} />
              <Route path="/dashboard/agent" element={<ProtectedRoute><Agent /></ProtectedRoute>} />
              <Route path="/dashboard/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
              <Route path="/signin" element={<SignIn />} />
              <Route path="/signup" element={<SignUp />} />
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
      <ScrollToTop />
    </div>
  );
}

export default App;
