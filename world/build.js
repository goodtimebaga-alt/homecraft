import { createMultiplayer } from './multiplayer.js';
import { buildIsland } from '@engine/world/terrain.js';
import { buildForest } from '@engine/world/landscape.js';
import { ISLAND, TREES } from './layout.js';

export function build({ grid, layer }) {
  buildIsland(grid, ISLAND, { surfaceAt: () => 'grass', corner: 10, wobble: 0 });
  return { forest: buildForest(grid, layer, TREES) };
}

// Optional presence for this world. The website still works without the service.
export function setup({ stage, player, avatar, config }) {
  if (!config.multiplayer?.enabled) return {};
  let multiplayer;
  try { multiplayer = createMultiplayer({ stage, player, avatar }); }
  catch (error) { console.warn('Multiplayer unavailable', error); }
  return { update(dt) {
    try { multiplayer?.update(dt); }
    catch (error) { console.warn('Multiplayer paused', error); multiplayer = null; }
  } };
}
