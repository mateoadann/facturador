import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useJobStatus(taskId, options = {}) {
  const { enabled = true, refetchInterval = 2000 } = options

  return useQuery({
    queryKey: ['job', taskId],
    queryFn: async () => {
      const response = await api.jobs.getStatus(taskId)
      return response.data
    },
    enabled: enabled && !!taskId,
    refetchInterval: (data) => {
      // Stop polling when job is complete or failed
      if (data?.status === 'SUCCESS' || data?.status === 'FAILURE') {
        return false
      }
      return refetchInterval
    },
  })
}
