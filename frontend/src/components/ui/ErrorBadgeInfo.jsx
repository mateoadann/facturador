import { useEffect, useRef, useState } from 'react'
import Badge from './Badge'

function ErrorBadgeInfo({ errorCodigo, errorMensaje }) {
  const [isOpen, setIsOpen] = useState(false)
  const wrapperRef = useRef(null)

  const codigo = errorCodigo || '-'
  const mensaje = errorMensaje || 'Sin detalle'

  useEffect(() => {
    if (!isOpen) return

    const handleOutsideClick = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleOutsideClick)
    document.addEventListener('keydown', handleEscape)

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  return (
    <div
      ref={wrapperRef}
      className="relative inline-flex"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button
        type="button"
        className="rounded-full focus:outline-none focus:ring-2 focus:ring-error/50"
        onClick={() => setIsOpen((prev) => !prev)}
        onFocus={() => setIsOpen(true)}
        aria-label="Ver detalle del error de emisión"
        aria-expanded={isOpen}
      >
        <Badge variant="error">Error</Badge>
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-20 mt-2 w-80 max-w-[80vw] rounded-md border border-border bg-card p-3 text-left shadow-lg">
          <p className="text-xs font-semibold text-text-primary">
            Detalle del error
          </p>
          <p className="mt-2 text-xs text-text-secondary">
            <span className="font-medium text-text-primary">Código:</span> {codigo}
          </p>
          <div className="mt-1 max-h-40 overflow-y-auto">
            <p className="text-xs text-text-secondary whitespace-normal break-words">
              <span className="font-medium text-text-primary">Mensaje:</span> {mensaje}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default ErrorBadgeInfo
