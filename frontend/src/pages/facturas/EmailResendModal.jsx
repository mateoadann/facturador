import { useState, useEffect } from 'react'
import { Loader2, X } from 'lucide-react'
import { Button, Input, Modal } from '@/components/ui'
import { api } from '@/api/client'
import { toast } from '@/stores/toastStore'

const TIPO_COMPROBANTE_LABELS = {
  1: 'Factura A',
  2: 'Nota de Debito A',
  3: 'Nota de Credito A',
  6: 'Factura B',
  7: 'Nota de Debito B',
  8: 'Nota de Credito B',
  11: 'Factura C',
  12: 'Nota de Debito C',
  13: 'Nota de Credito C',
}

function formatDateTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return String(dateStr)
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  return `${day}/${month}/${year} ${hours}:${minutes}`
}

function EmailResendModal({ isOpen, onClose, factura, onConfirm }) {
  const [destinatarios, setDestinatarios] = useState([])
  const [nuevoEmail, setNuevoEmail] = useState('')
  const [asunto, setAsunto] = useState('')
  const [body, setBody] = useState('')
  const [loading, setLoading] = useState(false)
  const [configError, setConfigError] = useState(false)

  useEffect(() => {
    if (!isOpen || !factura) return

    setLoading(true)
    setConfigError(false)
    setNuevoEmail('')

    // Pre-cargar email del receptor + emails_cc
    const initialEmails = []
    if (factura.receptor?.email) {
      initialEmails.push(factura.receptor.email)
    }
    if (factura.emails_cc) {
      const ccEmails = factura.emails_cc.split(',').map((e) => e.trim()).filter(Boolean)
      ccEmails.forEach((e) => {
        if (!initialEmails.includes(e)) initialEmails.push(e)
      })
    }
    setDestinatarios(initialEmails)

    // Build comprobante string (shared by both paths)
    const tipoLabel = TIPO_COMPROBANTE_LABELS[factura.tipo_comprobante] || 'Comprobante'
    const pv = String(factura.punto_venta || 0).padStart(5, '0')
    const nro = String(factura.numero_comprobante || 0).padStart(8, '0')
    const comprobanteStr = `${tipoLabel} ${pv}-${nro}`
    const facturadorNombre = factura.facturador?.razon_social || 'Facturador'
    const receptorNombre = factura.receptor?.razon_social || factura.receptor?.doc_nro || ''

    // If CSV override fields exist, use them directly (no config fetch needed for subject/body)
    if (factura.email_asunto) {
      const csvAsunto = factura.email_asunto
        .replace('{comprobante}', comprobanteStr)
        .replace('{facturador}', facturadorNombre)
        .replace('{receptor}', receptorNombre)
      setAsunto(csvAsunto)

      const csvParts = []
      if (factura.email_mensaje) csvParts.push(factura.email_mensaje)
      if (factura.email_firma) csvParts.push(factura.email_firma)
      setBody(csvParts.join('\n\n'))
      setLoading(false)
      return
    }

    api.email
      .getConfig()
      .then((response) => {
        const config = response.data

        // Build subject
        if (config.email_asunto) {
          setAsunto(
            config.email_asunto
              .replace('{comprobante}', comprobanteStr)
              .replace('{facturador}', facturadorNombre)
          )
        } else {
          setAsunto(`Comprobante ${comprobanteStr} - ${facturadorNombre}`)
        }

        // Build body from config fields
        const saludo = (config.email_saludo || 'Estimado/a {receptor},')
          .replace('{receptor}', receptorNombre)
          .replace('{facturador}', facturadorNombre)
          .replace('{comprobante}', comprobanteStr)

        const mensaje = config.email_mensaje || 'Adjunto encontrará el comprobante electrónico correspondiente.'
        const despedida = config.email_despedida || 'Saludos cordiales'
        const firma = config.email_firma || ''

        const parts = [saludo, mensaje, despedida]
        if (firma) parts.push(firma)
        setBody(parts.join('\n\n'))
      })
      .catch(() => {
        setConfigError(true)
        toast.error('Error', 'No se pudo obtener la configuración de email')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [isOpen, factura])

  const addEmail = () => {
    const email = nuevoEmail.trim().toLowerCase()
    if (!email) return
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.warning('Email inválido', 'Ingrese un email válido')
      return
    }
    if (destinatarios.includes(email)) {
      toast.warning('Duplicado', 'Este email ya está en la lista')
      return
    }
    setDestinatarios([...destinatarios, email])
    setNuevoEmail('')
  }

  const removeEmail = (email) => {
    setDestinatarios(destinatarios.filter((e) => e !== email))
  }

  const handleEmailKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addEmail()
    }
  }

  const handleConfirm = () => {
    if (destinatarios.length === 0) {
      toast.warning('Sin destinatarios', 'Agregue al menos un email')
      return
    }
    onConfirm({ custom_asunto: asunto, custom_body: body, destinatarios })
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={factura?.email_enviado ? 'Reenviar comprobante por email' : 'Enviar comprobante por email'}
      className="max-w-lg"
      footer={(
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleConfirm} disabled={loading || configError || !asunto.trim()}>
            {loading ? 'Cargando...' : factura?.email_enviado ? 'Reenviar' : 'Enviar'}
          </Button>
        </>
      )}
    >
      <div className="space-y-4">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-text-secondary" />
          </div>
        ) : (
          <>
            <p className="text-sm text-text-secondary">
              {factura?.email_enviado
                ? <>Este comprobante ya fue enviado{factura?.email_enviado_at ? ` el ${formatDateTime(factura.email_enviado_at)}` : ''}. Puede editar el contenido del email antes de reenviarlo.</>
                : 'Configure los destinatarios y el contenido del email antes de enviarlo.'}
            </p>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-primary">
                Destinatarios
              </label>
              <div className="flex flex-wrap gap-1.5 rounded-lg border border-border bg-card p-2 min-h-[40px]">
                {destinatarios.map((email) => (
                  <span
                    key={email}
                    className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
                  >
                    {email}
                    <button
                      type="button"
                      onClick={() => removeEmail(email)}
                      className="rounded-full p-0.5 hover:bg-primary/20"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
                <input
                  type="email"
                  className="flex-1 min-w-[180px] bg-transparent text-sm text-text-primary placeholder-text-muted outline-none"
                  placeholder="Agregar email y presionar Enter"
                  value={nuevoEmail}
                  onChange={(e) => setNuevoEmail(e.target.value)}
                  onKeyDown={handleEmailKeyDown}
                  onBlur={addEmail}
                />
              </div>
            </div>

            <Input
              label="Asunto"
              value={asunto}
              onChange={(e) => setAsunto(e.target.value)}
            />

            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-primary">
                Cuerpo del email
              </label>
              <textarea
                className="w-full resize-y rounded-lg border border-border bg-card px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                rows={10}
                value={body}
                onChange={(e) => setBody(e.target.value)}
              />
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}

export default EmailResendModal
