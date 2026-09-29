import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client.js'

export default function DemoReset() {
  const [params, setParams] = useSearchParams()

  useEffect(() => {
    if (params.get('reset') === '1') {
      api.resetDemo().then(() => {
        params.delete('reset')
        setParams(params, { replace: true })
      })
    }
  }, [params, setParams])

  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey && e.altKey && (e.key === 'r' || e.key === 'R')) {
        e.preventDefault()
        api.resetDemo()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return null
}
