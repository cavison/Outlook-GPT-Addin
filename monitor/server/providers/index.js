import { config } from '../config.js';
import { MockProvider } from './mock.js';
import { PowerAutomateProvider } from './powerAutomate.js';
import { GraphProvider } from './graph.js';
import { PortfolioProvider } from './portfolio.js';
import { FlowFleetProvider } from './flowFleet.js';
import { EstateProvider } from './estate.js';

/**
 * Build the active provider list. Adding a new system means writing one class
 * with `fetch()` and `execute()` and adding it here — nothing downstream, and
 * nothing in the renderer, needs to know it exists.
 */
export function buildProviders() {
  const providers = [];
  if (config.providers.mock) providers.push(new MockProvider());
  if (config.providers.powerAutomate) providers.push(new PowerAutomateProvider());
  if (config.providers.graph) providers.push(new GraphProvider());
  if (config.providers.portfolio) providers.push(new PortfolioProvider());
  if (config.providers.estate) providers.push(new EstateProvider());
  if (config.providers.flowFleet) providers.push(new FlowFleetProvider());
  return providers;
}
