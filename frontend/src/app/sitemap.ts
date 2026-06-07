import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  let rawBase = process.env.NEXT_PUBLIC_BASE_URL?.trim() || ''

  if (process.env.NODE_ENV === 'production' && (!rawBase || rawBase.includes('localhost'))) {
    console.error('ERROR: NEXT_PUBLIC_BASE_URL is not set or is localhost in production build.')
  }

  if (!rawBase) rawBase = 'http://localhost:3000'
  if (rawBase.endsWith('/')) rawBase = rawBase.slice(0, -1)
  if (!rawBase.startsWith('http')) rawBase = `https://${rawBase}`

  const baseUrl = rawBase

  return [
    {
      url: baseUrl,
      changeFrequency: 'yearly',
      priority: 1,
    },
    {
      url: `${baseUrl}/coming-soon`,
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/diagnose`,
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/generate`,
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/profiles`,
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/troubleshoot`,
      changeFrequency: 'monthly',
      priority: 0.8,
    }
  ]
}
