import { useEffect } from 'react';
import { FaTimes } from 'react-icons/fa';

interface LegalModalProps {
  type: 'terms' | 'privacy' | null;
  onClose: () => void;
}

export default function LegalModal({ type, onClose }: LegalModalProps) {
  useEffect(() => {
    if (!type) return;
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.body.style.overflow = '';
    };
  }, [type, onClose]);

  if (!type) return null;

  const isTerms = type === 'terms';
  const title = isTerms ? 'Términos de Servicio' : 'Política de Privacidad';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white dark:bg-dark-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-dark-200 dark:border-dark-600">
          <h2 className="text-xl font-bold text-dark-800 dark:text-dark-100">{title}</h2>
          <button
            onClick={onClose}
            className="p-1.5 text-dark-500 hover:text-dark-700 dark:text-dark-400 dark:hover:text-dark-200 hover:bg-dark-100 dark:hover:bg-dark-700 rounded-lg transition-colors"
          >
            <FaTimes className="w-5 h-5" />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5 text-dark-800 dark:text-dark-100">
          {isTerms ? (
            <div className="space-y-6">
              <section>
                <h3 className="text-lg font-semibold mb-2">1. Objeto</h3>
                <p className="text-sm leading-relaxed">ContratIA proporciona herramientas de apoyo para generar y analizar contratos. Sus resultados son informativos y no sustituyen el asesoramiento de un profesional jurídico.</p>
              </section>
              <section>
                <h3 className="text-lg font-semibold mb-2">2. Uso permitido</h3>
                <p className="text-sm leading-relaxed">La persona usuaria debe aportar información legítima, revisar los resultados y no utilizar el servicio para actividades ilícitas o que vulneren derechos de terceros.</p>
              </section>
              <section>
                <h3 className="text-lg font-semibold mb-2">3. Inteligencia artificial</h3>
                <p className="text-sm leading-relaxed">Los resultados pueden contener errores u omisiones. La cobertura se limita a las fuentes expresamente indicadas por la aplicación.</p>
              </section>
              <section>
                <h3 className="text-lg font-semibold mb-2">4. Cuenta y disponibilidad</h3>
                <p className="text-sm leading-relaxed">La persona usuaria es responsable de proteger sus credenciales. El servicio puede cambiar o interrumpirse por mantenimiento o causas técnicas.</p>
              </section>
            </div>
          ) : (
            <div className="space-y-6">
              <section>
                <h3 className="text-lg font-semibold mb-2">1. Datos tratados</h3>
                <p className="text-sm leading-relaxed">Se tratan los datos de cuenta, configuración, documentos y consultas necesarios para prestar el servicio.</p>
              </section>
              <section>
                <h3 className="text-lg font-semibold mb-2">2. Finalidad</h3>
                <p className="text-sm leading-relaxed">Los datos se utilizan para autenticar la cuenta, procesar solicitudes, mantener la seguridad y conservar el historial solicitado.</p>
              </section>
              <section>
                <h3 className="text-lg font-semibold mb-2">3. Proveedores</h3>
                <p className="text-sm leading-relaxed">El procesamiento puede requerir proveedores de infraestructura e inteligencia artificial. Solo se envía la información necesaria para ejecutar cada función.</p>
              </section>
              <section>
                <h3 className="text-lg font-semibold mb-2">4. Derechos y conservación</h3>
                <p className="text-sm leading-relaxed">La configuración permite gestionar preferencias y solicitar la eliminación de la cuenta. Los datos se conservan conforme a la configuración y obligaciones aplicables.</p>
              </section>
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-dark-200 dark:border-dark-600 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 bg-primary-600 hover:bg-primary-700 dark:hover:bg-primary-500 text-white font-semibold rounded-lg transition-colors text-sm"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
