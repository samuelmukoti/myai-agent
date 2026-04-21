import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import { getMyaiHome } from './myaiHome.js'

const dir = getMyaiHome()
const stateDir = join(dir, 'state')
const flagFile = join(stateDir, 'first_run_seen')

export function isFirstRun(): boolean {
  return !existsSync(flagFile)
}

export function markFirstRunSeen(): void {
  try {
    if (!existsSync(stateDir)) {
      mkdirSync(stateDir, { recursive: true })
    }
    writeFileSync(flagFile, new Date().toISOString() + '\n')
  } catch {
    void 0
  }
}
