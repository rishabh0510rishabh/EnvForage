import type { Config } from 'jest'
import nextJest from 'next/jest'

const createJestConfig = nextJest({ dir: './' })

const config: Config = {
  testEnvironment: 'jsdom',
  testMatch: ['**/tests/unit/**/*.test.{ts,tsx}'], 
}

export default createJestConfig(config) 