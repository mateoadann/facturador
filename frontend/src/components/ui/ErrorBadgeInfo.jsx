import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import Badge from './Badge'

function ErrorBadgeInfo({ errorCodigo, errorMensaje, floating = false }) {
  const [isOpen, setIsOpen] = useState(false)
  const wrapperRef = useRef(null)
  const triggerRef = useRef(null)
  const [position, setPosition] = useState(null)

  const codigo = errorCodigo || '-'
  const mensaje = errorMensaje || 'Sin detalle'
  const tooltipWidth = 320
  const tooltipMaxWidth = 80

  const tooltipClasses = useMemo(() => (
    'w-80 max-w-[80vw] rounded-md border border-border bg-card p-3 text-left shadow-lg'
  ), [])

  const updateFloatingPosition = useCallback(() => {
    if (!floating || !isOpen || !triggerRef.current) return

    const rect = triggerRef.current.getBoundingClientRect()
    const margin = 8
    const verticalOffset = 8
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    const maxWidthPx = (viewportWidth * tooltipMaxWidth) / 100
    const panelWidth = Math.min(tooltipWidth, maxWidthPx)
    const estimatedHeight = 220

    let left = rect.left
    if (left + panelWidth > viewportWidth - margin) {
      left = viewportWidth - panelWidth - margin
    }
    if (left < margin) {
      left = margin
    }

    const topPreferred = rect.bottom + verticalOffset
    const topFallback = rect.top - estimatedHeight - verticalOffset
    const top =
      topPreferred + estimatedHeight <= viewportHeight - margin
        ? topPreferred
        : Math.max(margin, topFallback)

    setPosition({
      top,
      left,
      width: panelWidth,
    })
  }, [floating, isOpen])

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

  useEffect(() => {
    if (!floating || !isOpen) return

    updateFloatingPosition()

    const handleViewportChange = () => {
      updateFloatingPosition()
    }

    window.addEventListener('resize', handleViewportChange)
    window.addEventListener('scroll', handleViewportChange, true)

    return () => {
      window.removeEventListener('resize', handleViewportChange)
      window.removeEventListener('scroll', handleViewportChange, true)
    }
  }, [floating, isOpen, updateFloatingPosition])

  const defaultPanel = (
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
  )

  const floatingPanel = position ? createPortal(
    <div
      className="fixed z-[60]"
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`,
        width: `${position.width}px`,
      }}
    >
      <div className={tooltipClasses}>
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
    </div>,
    document.body
  ) : null

  return (
    <div
      ref={wrapperRef}
      className="relative inline-flex"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button
        ref={triggerRef}
        type="button"
        className="rounded-full focus:outline-none focus:ring-2 focus:ring-error/50"
        onClick={() => setIsOpen((prev) => !prev)}
        onFocus={() => setIsOpen(true)}
        aria-label="Ver detalle del error de emisión"
        aria-expanded={isOpen}
      >
        <Badge variant="error">Error</Badge>
      </button>

      {isOpen && !floating && defaultPanel}
      {isOpen && floating && floatingPanel}
    </div>
  )
}

export default ErrorBadgeInfo
