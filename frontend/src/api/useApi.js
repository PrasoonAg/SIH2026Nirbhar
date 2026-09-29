import { useSyncExternalStore } from 'react'
import { api } from './client.js'
import { subscribe, getVersion } from './mockStore.js'

export function useApi() {
  const version = useSyncExternalStore(subscribe, getVersion, getVersion)
  return { api, version }
}
