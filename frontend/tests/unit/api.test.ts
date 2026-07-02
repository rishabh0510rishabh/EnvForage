//  Unit tests for frontend/src/services/api.ts
 
import { api } from '../../src/services/api'

// Mock global fetch before each test
beforeEach(() => {
	global.fetch = jest.fn() 
}) 

// Reset all mocks after each test to avoid leaking state
afterEach(() => {
	jest.resetAllMocks()
}) 

// api.getProfiles() 
// Source api.ts line 54
// Builds URL with optional os, cuda, tags filters
// Error: "Failed to fetch profiles"
describe('api.getProfiles()', () => {
	it('fetches profiles successfully with no filters', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({
			ok: true,
			json: async () => ({ profiles: [] }),
		})
		const result = await api.getProfiles()
		expect(result).toEqual([])
		expect(fetch).toHaveBeenCalledWith(
			expect.stringContaining('/profiles'),
			expect.any(Object)
		)
	})

	it('appends os filter to URL when provided', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({
			ok: true,
			json: async () => ({ profiles: [] }),
		})
		await api.getProfiles('LINUX')
		expect(fetch).toHaveBeenCalledWith(
			expect.stringContaining('os=LINUX'),
			expect.any(Object)
		)
	})

	it('appends cuda_required filter when cuda is true', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({
			ok: true,
			json: async () => ({ profiles: [] }),
		})
		await api.getProfiles(undefined, true)
		expect(fetch).toHaveBeenCalledWith(
			expect.stringContaining('cuda_required=true'),
			expect.any(Object)
		)
	}) 

	it('throws "Failed to fetch profiles" on non-ok response', async () => {
		// Mock fetch to always return 500 — exhausts all 3 retries in fetchWithRetry
		;(fetch as jest.Mock).mockResolvedValue({ ok: false, status: 400 })
		await expect(api.getProfiles()).rejects.toThrow('Failed to fetch profiles')
	 }, 20000) 
})

// api.getProfile()
// Source api.ts line 73
// Fetches single profile by slug
// Error: "Failed to fetch profile: ${slug}"
describe('api.getProfile()', () => {
	it('calls correct slug URL', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({
			ok: true,
			json: async () => ({ slug: 'pytorch-cu121' }),
		})
		await api.getProfile('pytorch-cu121')
		expect(fetch).toHaveBeenCalledWith(
			expect.stringContaining('/profiles/pytorch-cu121'),
			expect.any(Object)
		)
	})

	it('throws with slug name on error', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({ ok: false, status: 404 })
		await expect(api.getProfile('bad-slug')).rejects.toThrow(
			'Failed to fetch profile: bad-slug'
		)
	})
})

// api.generateScript()
// Source api.ts line 84
// POSTs to /scripts/generate with JSON body
// Error: "Failed to generate script"
describe('api.generateScript()', () => {
	it('POSTs to /scripts/generate with correct headers', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({
			ok: true,
			json: async () => ({}),
		})
		await api.generateScript({
			profile_id: 'test',
			target_os: 'LINUX',
			python_version: '3.11',
			output_formats: ['setup.sh'],
		} as any)
		expect(fetch).toHaveBeenCalledWith(
			expect.stringContaining('/scripts/generate'),
			expect.objectContaining({
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
			})
		)
	})

	it('throws "Failed to generate script" on error', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({ ok: false, status: 500 })
		await expect(api.generateScript({} as any)).rejects.toThrow(
			'Failed to generate script'
		)
	})
})

// api.diagnose()
// Source api.ts line 98
// POSTs to /diagnose, optionally with profile_id query param
// Error: "Failed to analyze diagnostic report"
describe('api.diagnose()', () => {
	it('calls /diagnose endpoint without profile_id', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({
			ok: true,
			json: async () => ({}),
		})
		await api.diagnose({} as any)
		expect(fetch).toHaveBeenCalledWith(
			expect.stringContaining('/diagnose'),
			expect.any(Object)
		)
	})

	it('appends profile_id as query param when provided', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({
			ok: true,
			json: async () => ({}),
		})
		await api.diagnose({} as any, 'profile-123')
		expect(fetch).toHaveBeenCalledWith(
			expect.stringContaining('profile_id=profile-123'),
			expect.any(Object)
		)
	})

	it('throws "Failed to analyze diagnostic report" on error', async () => {
		;(fetch as jest.Mock).mockResolvedValueOnce({ ok: false, status: 500 })
		await expect(api.diagnose({} as any)).rejects.toThrow(
			'Failed to analyze diagnostic report'
		)
	})
})