// Single factory: components import only from here.
import * as live from './pramana.js'
import * as mock from './mockClient.js'

const DEMO = String(import.meta.env.VITE_DEMO_MODE ?? 'true').toLowerCase() === 'true'

export const api = DEMO ? mock : live
