import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  let rawBase = process.env.NEXT_PUBLIC_BASE_URL?.trim() || ''

  if (process.env.NODE_ENV === 'production' && (!rawBase || rawBase.includes('localhost'))) {
    console.error('ERROR: NEXT_PUBLIC_BASE_URL is not set or is localhost in production build.')
  }

  if (!rawBase) rawBase = 'http://localhost:3000'
  if (rawBase.endsWith('/')) rawBase = rawBase.slice(0, -1)
  if (!rawBase.startsWith('http')) rawBase = `https://${rawBase}`

  const baseUrlNormalized = rawBase

  return {
    rules: {
      userAgent: '*',
      allow: '/',
    },
    sitemap: `${baseUrlNormalized}/sitemap.xml`,
  }
}
