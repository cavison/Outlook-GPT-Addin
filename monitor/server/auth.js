import fs from 'node:fs';
import { PublicClientApplication } from '@azure/msal-node';
import { config, dataPath } from './config.js';

// Device-code flow. For a single-user local tool this is the right trade: no
// client secret sitting on your laptop, no redirect URI to register, and the
// refresh token lives in one file you can delete to sign out.

const CACHE_FILE = dataPath('msal-cache.json');

const cachePlugin = {
  beforeCacheAccess: async (ctx) => {
    if (fs.existsSync(CACHE_FILE)) {
      ctx.tokenCache.deserialize(fs.readFileSync(CACHE_FILE, 'utf8'));
    }
  },
  afterCacheAccess: async (ctx) => {
    if (ctx.cacheHasChanged) {
      fs.writeFileSync(CACHE_FILE, ctx.tokenCache.serialize(), { mode: 0o600 });
    }
  },
};

// Scope sets per API. Power Automate's management API is a separate resource
// from Graph, so tokens are acquired independently.
export const SCOPES = {
  powerAutomate: [
    'https://service.flow.microsoft.com/Flows.Read.All',
    'https://service.flow.microsoft.com/Flows.Manage.All',
  ],
  graph: [
    'https://graph.microsoft.com/User.Read',
    'https://graph.microsoft.com/Mail.Read',
    'https://graph.microsoft.com/MailboxSettings.Read',
    'https://graph.microsoft.com/Calendars.Read',
  ],
};

class AuthManager {
  constructor() {
    this.pca = null;
    // Surfaced to the UI so the sign-in code appears in the app, not only in a
    // terminal you may not be looking at.
    this.pendingDeviceCode = null;
    this.lastError = null;
  }

  get configured() {
    return Boolean(config.azure.clientId);
  }

  client() {
    if (!this.configured) {
      throw new Error(
        'AZURE_CLIENT_ID is not set. Copy .env.example to .env and register an app first.',
      );
    }
    this.pca ??= new PublicClientApplication({
      auth: {
        clientId: config.azure.clientId,
        authority: `https://login.microsoftonline.com/${config.azure.tenantId}`,
      },
      cache: { cachePlugin },
    });
    return this.pca;
  }

  async account() {
    const accounts = await this.client().getTokenCache().getAllAccounts();
    return accounts[0] ?? null;
  }

  /**
   * Get an access token for one resource. Tries silent first; only falls back
   * to device code when there is no usable refresh token.
   */
  async token(scopeKey, { interactive = true } = {}) {
    const scopes = SCOPES[scopeKey];
    if (!scopes) throw new Error(`Unknown scope set "${scopeKey}"`);

    const account = await this.account();
    if (account) {
      try {
        const result = await this.client().acquireTokenSilent({ account, scopes });
        return result.accessToken;
      } catch {
        // Fall through to interactive — silent failure here usually means the
        // refresh token aged out or consent changed.
      }
    }

    if (!interactive) return null;

    const result = await this.client().acquireTokenByDeviceCode({
      scopes,
      deviceCodeCallback: (response) => {
        this.pendingDeviceCode = {
          message: response.message,
          userCode: response.userCode,
          verificationUri: response.verificationUri,
          expiresAt: Date.now() + response.expiresIn * 1000,
        };
        console.log(`\n[auth] ${response.message}\n`);
      },
    });
    this.pendingDeviceCode = null;
    return result.accessToken;
  }

  async status() {
    if (!this.configured) {
      return { configured: false, signedIn: false, reason: 'AZURE_CLIENT_ID not set' };
    }
    const account = await this.account();
    return {
      configured: true,
      signedIn: Boolean(account),
      username: account?.username ?? null,
      pendingDeviceCode: this.pendingDeviceCode,
      lastError: this.lastError,
    };
  }

  signOut() {
    if (fs.existsSync(CACHE_FILE)) fs.unlinkSync(CACHE_FILE);
    this.pca = null;
  }
}

export const auth = new AuthManager();
