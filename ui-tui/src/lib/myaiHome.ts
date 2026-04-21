import { existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

/**
 * Resolve the MyAIOne home directory (default: ~/.myai).
 *
 * Resolution order mirrors the Python `get_myai_home()` so TUI and backend
 * agree on a single path:
 *   1. $MYAI_HOME env var
 *   2. $HERMES_HOME env var (back-compat)
 *   3. ~/.myai if it exists
 *   4. ~/.hermes if it exists (legacy install — Python side handles migration)
 *   5. ~/.myai as the new-install default
 */
export function getMyaiHome(): string {
  const fromEnv = process.env.MYAI_HOME?.trim() || process.env.HERMES_HOME?.trim()
  if (fromEnv) {
    return fromEnv
  }
  const home = homedir()
  const newHome = join(home, '.myai')
  if (existsSync(newHome)) {
    return newHome
  }
  const legacyHome = join(home, '.hermes')
  if (existsSync(legacyHome)) {
    return legacyHome
  }
  return newHome
}
