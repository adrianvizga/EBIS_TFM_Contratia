
import { FaRocket, FaCrown, FaStar, FaCheck } from 'react-icons/fa';
import { useLanguage } from '../context/useLanguage';

interface UpgradePlanScreenProps {
  feature?: string;
}

export default function UpgradePlanScreen({ feature }: UpgradePlanScreenProps) {
  const { t } = useLanguage();
  const resolvedFeature = feature || t('upgrade.defaultFeature');

  const plans = [
    {
      id: 'plus',
      role: '2',
      name: 'Plus',
      icon: FaCrown,
      color: 'amber',
      features: [
        `10 ${t('upgrade.feature.generatedContracts')}`,
        `10 ${t('upgrade.feature.analyzedContracts')}`,
        `30 ${t('upgrade.feature.aiMods')}`,
        t('upgrade.feature.unlimitedAgent'),
      ],
    },
    {
      id: 'pro',
      role: '3',
      name: 'Pro',
      icon: FaStar,
      color: 'primary',
      features: [
        `30 ${t('upgrade.feature.generatedContracts')}`,
        `25 ${t('upgrade.feature.analyzedContracts')}`,
        `50 ${t('upgrade.feature.aiMods')}`,
        t('upgrade.feature.unlimitedAgent'),
      ],
    },
  ];

  return (
    <div className="flex-1 flex items-center justify-center p-6 bg-dark-50 dark:bg-dark-900">
      <div className="max-w-3xl w-full text-center">
        <div className="mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-400 to-primary-600 rounded-2xl mb-5 shadow-lg">
            <FaRocket className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-dark-900 dark:text-white mb-3">
            {t('upgrade.title')}
          </h2>
          <p className="text-dark-500 dark:text-dark-400 text-base sm:text-lg max-w-lg mx-auto">
            {t('upgrade.description')} {resolvedFeature}{t('upgrade.descriptionSuffix')}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
          {plans.map((plan) => {
            const Icon = plan.icon;
            const isPrimary = plan.id === 'pro';
            return (
              <div
                key={plan.id}
                className={`relative rounded-2xl border-2 p-6 transition-all ${isPrimary
                    ? 'border-primary-500 bg-white dark:bg-dark-800 shadow-xl shadow-primary-100 dark:shadow-primary-900/20'
                    : 'border-dark-200 dark:border-dark-700 bg-white dark:bg-dark-800 shadow-lg'
                  }`}
              >
                {isPrimary && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                    {t('upgrade.recommended')}
                  </span>
                )}
                <div className="flex flex-col items-center mb-5">
                  <div
                    className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 ${isPrimary
                        ? 'bg-primary-100 dark:bg-primary-900/30'
                        : 'bg-amber-100 dark:bg-amber-900/30'
                      }`}
                  >
                    <Icon
                      className={`w-6 h-6 ${isPrimary
                          ? 'text-primary-600 dark:text-primary-400'
                          : 'text-amber-600 dark:text-amber-400'
                        }`}
                    />
                  </div>
                  <h3 className="text-xl font-bold text-dark-900 dark:text-white">{plan.name}</h3>
                </div>
                <ul className="space-y-3 text-left mb-6">
                  {plan.features.map((feat, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-dark-700 dark:text-dark-300">
                      <FaCheck
                        className={`w-4 h-4 mt-0.5 flex-shrink-0 ${isPrimary
                            ? 'text-primary-500 dark:text-primary-400'
                            : 'text-amber-500 dark:text-amber-400'
                          }`}
                      />
                      {feat}
                    </li>
                  ))}
                </ul>
                <button
                  disabled
                  className={`w-full py-2.5 rounded-lg font-semibold text-sm transition-colors cursor-not-allowed opacity-60 ${isPrimary
                      ? 'bg-primary-600 text-white'
                      : 'bg-amber-500 text-white'
                    }`}
                >
                  {t('upgrade.comingSoon')}
                </button>
              </div>
            );
          })}
        </div>

        <p className="text-dark-400 dark:text-dark-500 text-xs">
          {t('upgrade.footer')}
        </p>
      </div>
    </div>
  );
}
