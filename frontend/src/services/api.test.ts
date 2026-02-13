/**
 * Tests for services/api.ts
 * Mocks axios to verify correct HTTP calls.
 */
import { vi, type Mock } from 'vitest'
import axios from 'axios'

// Use var so the mock factory (hoisted above let/const) can access it
var interceptorFn: ((config: any) => any) | undefined

vi.mock('axios', () => {
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn((fn: any) => {
          interceptorFn = fn
        }),
      },
      response: { use: vi.fn() },
    },
  }
  return {
    default: {
      create: vi.fn(() => mockInstance),
      __mockInstance: mockInstance,
    },
  }
})

// Get the mock instance that api.ts will use
const mockAxios = (axios as any).__mockInstance as {
  get: Mock
  post: Mock
  put: Mock
  delete: Mock
}

// Import after mocking
import { authApi, patientApi, testApi, adminApi, goalApi, dashboardApi } from './api'

beforeEach(() => {
  mockAxios.get.mockReset()
  mockAxios.post.mockReset()
  mockAxios.put.mockReset()
  mockAxios.delete.mockReset()
  localStorage.clear()
})

// --- authApi ---
describe('authApi', () => {
  it('login sends POST /api/auth/login', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: { id: '1', username: 'admin', role: 'admin' } })
    const result = await authApi.login('admin', 'pass')
    expect(mockAxios.post).toHaveBeenCalledWith('/api/auth/login', { username: 'admin', password: 'pass' })
    expect(result).toEqual({ id: '1', username: 'admin', role: 'admin' })
  })

  it('register sends POST /api/auth/register', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: { id: '2', username: 'user1' } })
    const result = await authApi.register('user1', 'pw', 'User One')
    expect(mockAxios.post).toHaveBeenCalledWith('/api/auth/register', { username: 'user1', password: 'pw', name: 'User One' })
    expect(result).toEqual({ id: '2', username: 'user1' })
  })

  it('logout clears localStorage', () => {
    localStorage.setItem('user', JSON.stringify({ id: '1' }))
    authApi.logout()
    expect(localStorage.getItem('user')).toBeNull()
  })

  it('getCurrentUser returns parsed user from localStorage', () => {
    const user = { id: '1', username: 'admin', name: 'Admin', role: 'admin', is_approved: true }
    localStorage.setItem('user', JSON.stringify(user))
    expect(authApi.getCurrentUser()).toEqual(user)
  })

  it('getCurrentUser returns null when no user stored', () => {
    expect(authApi.getCurrentUser()).toBeNull()
  })
})

// --- patientApi ---
describe('patientApi', () => {
  it('create sends POST /api/patients/', async () => {
    const patient = { patient_number: 'P001', name: 'Test', gender: 'M' as const, birth_date: '1990-01-01', height_cm: 170 }
    mockAxios.post.mockResolvedValueOnce({ data: { id: '1', ...patient } })
    const result = await patientApi.create(patient)
    expect(mockAxios.post).toHaveBeenCalledWith('/api/patients/', patient)
    expect(result.id).toBe('1')
  })

  it('getAll sends GET /api/patients/ with default limit', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    await patientApi.getAll()
    expect(mockAxios.get).toHaveBeenCalledWith('/api/patients/?limit=50')
  })

  it('getAll sends GET /api/patients/ with custom limit', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    await patientApi.getAll(100)
    expect(mockAxios.get).toHaveBeenCalledWith('/api/patients/?limit=100')
  })

  it('search encodes query parameter', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    await patientApi.search('test query')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/patients/search?q=test%20query')
  })

  it('getById sends GET /api/patients/:id', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: { id: '1', name: 'Test' } })
    const result = await patientApi.getById('1')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/patients/1')
    expect(result.name).toBe('Test')
  })

  it('update sends PUT /api/patients/:id', async () => {
    mockAxios.put.mockResolvedValueOnce({ data: { id: '1', name: 'Updated' } })
    const result = await patientApi.update('1', { name: 'Updated' })
    expect(mockAxios.put).toHaveBeenCalledWith('/api/patients/1', { name: 'Updated' })
    expect(result.name).toBe('Updated')
  })

  it('delete sends DELETE /api/patients/:id', async () => {
    mockAxios.delete.mockResolvedValueOnce({})
    await patientApi.delete('1')
    expect(mockAxios.delete).toHaveBeenCalledWith('/api/patients/1')
  })
})

// --- adminApi ---
describe('adminApi', () => {
  it('getAllTherapists sends GET /api/admin/therapists', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    const result = await adminApi.getAllTherapists()
    expect(mockAxios.get).toHaveBeenCalledWith('/api/admin/therapists')
    expect(result).toEqual([])
  })

  it('approveTherapist sends POST /api/admin/therapists/:id/approve', async () => {
    mockAxios.post.mockResolvedValueOnce({ data: { id: 'u1', is_approved: true } })
    const result = await adminApi.approveTherapist('u1')
    expect(mockAxios.post).toHaveBeenCalledWith('/api/admin/therapists/u1/approve')
    expect(result.is_approved).toBe(true)
  })

  it('deleteTherapist sends DELETE /api/admin/therapists/:id', async () => {
    mockAxios.delete.mockResolvedValueOnce({})
    await adminApi.deleteTherapist('u1')
    expect(mockAxios.delete).toHaveBeenCalledWith('/api/admin/therapists/u1')
  })
})

// --- testApi (non-upload methods) ---
describe('testApi', () => {
  it('getStatus sends GET /api/tests/status/:fileId', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: { status: 'completed', progress: 100 } })
    const result = await testApi.getStatus('file-123')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/tests/status/file-123')
    expect(result.status).toBe('completed')
  })

  it('getPatientTests sends GET with test_type filter', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    await testApi.getPatientTests('p1', '10MWT')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/tests/patient/p1?test_type=10MWT')
  })

  it('getPatientTests sends GET without filter for ALL', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    await testApi.getPatientTests('p1', 'ALL')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/tests/patient/p1')
  })

  it('getPatientTests sends GET without filter when no type', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    await testApi.getPatientTests('p1')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/tests/patient/p1')
  })

  it('getById sends GET /api/tests/:testId', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: { id: 't1', walk_time_seconds: 8.5 } })
    const result = await testApi.getById('t1')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/tests/t1')
    expect(result.walk_time_seconds).toBe(8.5)
  })

  it('compare sends GET /api/tests/patient/:id/compare', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: { comparison_message: 'improved' } })
    const result = await testApi.compare('p1')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/tests/patient/p1/compare')
    expect(result.comparison_message).toBe('improved')
  })

  it('delete sends DELETE /api/tests/:testId', async () => {
    mockAxios.delete.mockResolvedValueOnce({})
    await testApi.delete('t1')
    expect(mockAxios.delete).toHaveBeenCalledWith('/api/tests/t1')
  })

  it('updateTestNotes sends PUT /api/tests/:id/notes', async () => {
    mockAxios.put.mockResolvedValueOnce({ data: { test: { id: 't1', notes: 'note' } } })
    const result = await testApi.updateTestNotes('t1', 'note')
    expect(mockAxios.put).toHaveBeenCalledWith('/api/tests/t1/notes', { notes: 'note' })
    expect(result.id).toBe('t1')
  })

  it('updateTestDate sends PUT /api/tests/:id/date', async () => {
    mockAxios.put.mockResolvedValueOnce({ data: { test: { id: 't1', test_date: '2025-01-01' } } })
    const result = await testApi.updateTestDate('t1', '2025-01-01')
    expect(mockAxios.put).toHaveBeenCalledWith('/api/tests/t1/date', { test_date: '2025-01-01' })
    expect(result.test_date).toBe('2025-01-01')
  })

  // URL builder methods - these use API_URL which comes from VITE_API_URL env var.
  // In test, VITE_API_URL may be set (e.g. "http://localhost:8000").
  // We test that the path portion is correct by checking endsWith.
  it('downloadCsv URL ends with correct path', () => {
    expect(testApi.downloadCsv('t1')).toMatch(/\/api\/tests\/t1\/report\/csv$/)
  })

  it('downloadPdf URL ends with correct path', () => {
    expect(testApi.downloadPdf('t1')).toMatch(/\/api\/tests\/t1\/report\/pdf$/)
  })

  it('getVideoOverlayUrl URL ends with correct path', () => {
    expect(testApi.getVideoOverlayUrl('t1')).toMatch(/\/api\/tests\/t1\/video\/overlay$/)
  })

  it('getVideoOverlayFrameUrl URL ends with correct path and frame', () => {
    expect(testApi.getVideoOverlayFrameUrl('t1', 42)).toMatch(/\/api\/tests\/t1\/video\/overlay\/frame\?frame_num=42$/)
  })

  it('getPhaseClipUrl URL ends with correct path', () => {
    expect(testApi.getPhaseClipUrl('t1', 'walk_out')).toMatch(/\/api\/tests\/t1\/phase-clip\/walk_out$/)
  })

  it('getVideoUrl returns null when no video_url', () => {
    expect(testApi.getVideoUrl({ video_url: undefined } as any)).toBeNull()
  })

  it('getVideoUrl returns URL containing video path when video_url exists', () => {
    const url = testApi.getVideoUrl({ video_url: '/uploads/vid.mp4' } as any)
    expect(url).not.toBeNull()
    expect(url).toMatch(/\/uploads\/vid\.mp4$/)
  })

  it('getWalkingClipUrl URL ends with correct path', () => {
    expect(testApi.getWalkingClipUrl('t1')).toMatch(/\/api\/tests\/t1\/video\/walking-clip$/)
  })

  it('downloadVideo URL ends with correct path', () => {
    expect(testApi.downloadVideo('t1')).toMatch(/\/api\/tests\/t1\/video\/download$/)
  })

  it('getComparisonVideoUrl URL contains correct query params', () => {
    const url = testApi.getComparisonVideoUrl('p1', 't1', 't2')
    expect(url).toMatch(/\/api\/tests\/patient\/p1\/video\/comparison\?test1_id=t1&test2_id=t2$/)
  })
})

// --- goalApi ---
describe('goalApi', () => {
  it('create sends POST /api/goals/:patientId', async () => {
    const data = { test_type: '10MWT' as const, target_speed_mps: 1.0 }
    mockAxios.post.mockResolvedValueOnce({ data: { id: 'g1', ...data } })
    const result = await goalApi.create('p1', data)
    expect(mockAxios.post).toHaveBeenCalledWith('/api/goals/p1', data)
    expect(result.id).toBe('g1')
  })

  it('getAll sends GET /api/goals/:patientId with optional status', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    await goalApi.getAll('p1', 'active')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/goals/p1?status=active')
  })

  it('getAll sends GET /api/goals/:patientId without status', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    await goalApi.getAll('p1')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/goals/p1')
  })

  it('update sends PUT /api/goals/:goalId/update', async () => {
    mockAxios.put.mockResolvedValueOnce({ data: { id: 'g1', status: 'achieved' } })
    const result = await goalApi.update('g1', { status: 'achieved' })
    expect(mockAxios.put).toHaveBeenCalledWith('/api/goals/g1/update', { status: 'achieved' })
    expect(result.status).toBe('achieved')
  })

  it('delete sends DELETE /api/goals/:goalId/delete', async () => {
    mockAxios.delete.mockResolvedValueOnce({})
    await goalApi.delete('g1')
    expect(mockAxios.delete).toHaveBeenCalledWith('/api/goals/g1/delete')
  })

  it('getProgress sends GET /api/goals/:patientId/progress', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: [] })
    await goalApi.getProgress('p1')
    expect(mockAxios.get).toHaveBeenCalledWith('/api/goals/p1/progress')
  })
})

// --- dashboardApi ---
describe('dashboardApi', () => {
  it('getStats sends GET /api/admin/dashboard/stats', async () => {
    mockAxios.get.mockResolvedValueOnce({ data: { total_patients: 10 } })
    const result = await dashboardApi.getStats()
    expect(mockAxios.get).toHaveBeenCalledWith('/api/admin/dashboard/stats')
    expect(result.total_patients).toBe(10)
  })
})

// --- Request interceptor ---
describe('request interceptor', () => {
  it('interceptor function was captured', () => {
    expect(interceptorFn).toBeDefined()
  })

  it('interceptor adds user headers when user exists', () => {
    const user = { id: 'u1', role: 'therapist', is_approved: true }
    localStorage.setItem('user', JSON.stringify(user))

    const config = { headers: {} } as any
    const result = interceptorFn!(config)
    expect(result.headers['X-User-Id']).toBe('u1')
    expect(result.headers['X-User-Role']).toBe('therapist')
    expect(result.headers['X-User-Approved']).toBe('true')
  })

  it('interceptor does not add headers when no user', () => {
    const config = { headers: {} } as any
    const result = interceptorFn!(config)
    expect(result.headers['X-User-Id']).toBeUndefined()
  })
})
