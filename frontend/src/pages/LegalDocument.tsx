interface LegalDocumentProps { type: 'terms' | 'privacy' }

export default function LegalDocument({ type }: LegalDocumentProps) {
  const terms = type === 'terms';
  return (
    <main className="min-h-screen bg-dark-50 dark:bg-dark-900 px-4 py-10 text-dark-800 dark:text-dark-100">
      <article className="mx-auto max-w-3xl rounded-2xl bg-white dark:bg-dark-800 p-6 sm:p-10 shadow-lg">
        <h1 className="text-3xl font-bold mb-4">{terms ? 'Términos de Servicio' : 'Política de Privacidad'}</h1>
        {terms ? (
          <div className="space-y-6">
            <section><h2 className="text-xl font-semibold mb-2">1. Objeto</h2><p>ContratIA proporciona herramientas de apoyo para generar y analizar contratos. Sus resultados son informativos y no sustituyen el asesoramiento de un profesional jurídico.</p></section>
            <section><h2 className="text-xl font-semibold mb-2">2. Uso permitido</h2><p>La persona usuaria debe aportar información legítima, revisar los resultados y no utilizar el servicio para actividades ilícitas o que vulneren derechos de terceros.</p></section>
            <section><h2 className="text-xl font-semibold mb-2">3. Inteligencia artificial</h2><p>Los resultados pueden contener errores u omisiones. La cobertura se limita a las fuentes expresamente indicadas por la aplicación.</p></section>
            <section><h2 className="text-xl font-semibold mb-2">4. Cuenta y disponibilidad</h2><p>La persona usuaria es responsable de proteger sus credenciales. El servicio puede cambiar o interrumpirse por mantenimiento o causas técnicas.</p></section>
          </div>
        ) : (
          <div className="space-y-6">
            <section><h2 className="text-xl font-semibold mb-2">1. Datos tratados</h2><p>Se tratan los datos de cuenta, configuración, documentos y consultas necesarios para prestar el servicio.</p></section>
            <section><h2 className="text-xl font-semibold mb-2">2. Finalidad</h2><p>Los datos se utilizan para autenticar la cuenta, procesar solicitudes, mantener la seguridad y conservar el historial solicitado.</p></section>
            <section><h2 className="text-xl font-semibold mb-2">3. Proveedores</h2><p>El procesamiento puede requerir proveedores de infraestructura e inteligencia artificial. Solo se envía la información necesaria para ejecutar cada función.</p></section>
            <section><h2 className="text-xl font-semibold mb-2">4. Derechos y conservación</h2><p>La configuración permite gestionar preferencias y solicitar la eliminación de la cuenta. Los datos se conservan conforme a la configuración y obligaciones aplicables.</p></section>
          </div>
        )}
      </article>
    </main>
  );
}
