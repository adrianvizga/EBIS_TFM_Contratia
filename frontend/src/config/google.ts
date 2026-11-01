const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

export const googleConfig = {
  clientId: GOOGLE_CLIENT_ID,
  isConfigured: !!GOOGLE_CLIENT_ID,
};

export default googleConfig;
