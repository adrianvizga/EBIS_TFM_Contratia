declare global {
  interface GoogleCredentialResponse {
    credential?: string;
    select_by?: string;
    clientId?: string;
  }

  interface GoogleInitializeConfig {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
    itp_support?: boolean;
  }

  interface GoogleButtonOptions {
    type?: 'standard' | 'icon';
    size?: 'large' | 'medium' | 'small';
    text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
    locale?: string;
    theme?: 'outline' | 'filled_blue' | 'filled_black';
  }

  interface GoogleAccountsId {
    initialize: (config: GoogleInitializeConfig) => void;
    renderButton: (element: HTMLElement, options: GoogleButtonOptions) => void;
    cancel: () => void;
  }

  interface GoogleAccounts {
    id: GoogleAccountsId;
  }

  interface Window {
    google?: {
      accounts: GoogleAccounts;
    };
  }
}

export {};
