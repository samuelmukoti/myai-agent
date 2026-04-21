import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

const dir = process.env.HERMES_HOME ?? join(homedir(), '.hermes')
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
