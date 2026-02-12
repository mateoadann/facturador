import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Save, Wifi, Send, Loader2, FileText } from 'lucide-react'
import { api } from '@/api/client'
import { toast } from '@/stores/toastStore'
import { Card } from '@/components/ui'
import { Button, Input, Badge, Checkbox } from '@/components/ui'

function Email() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    smtp_host: '',
    smtp_port: '587',
    smtp_use_tls: true,
    smtp_user: '',
    smtp_password: '',
    from_email: '',
    from_name: '',
    email_habilitado: true,
    email_asunto: '',
    email_mensaje: '',
    email_saludo: '',
  })
  const [testEmail, setTestEmail] = useState('')

  const { data: config, isLoading } = useQuery({
    queryKey: ['email-config'],
    queryFn: async () => {
      const response = await api.email.getConfig()
      return response.data
    },
  })

  useEffect(() => {
    if (config?.configured) {
      setFormData({
        smtp_host: config.smtp_host || '',
        smtp_port: String(config.smtp_port || 587),
        smtp_use_tls: config.smtp_use_tls ?? true,
        smtp_user: config.smtp_user || '',
        smtp_password: '',
        from_email: config.from_email || '',
        from_name: config.from_name || '',
        email_habilitado: config.email_habilitado ?? true,
        email_asunto: config.email_asunto || '',
        email_mensaje: config.email_mensaje || '',
        email_saludo: config.email_saludo || '',
      })
    }
  }, [config])

  const saveMutation = useMutation({
    mutationFn: (data) => api.email.updateConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['email-config'])
      toast.success('Configuración guardada correctamente')
    },
    onError: (error) => {
      toast.error('Error al guardar', error.response?.data?.error || 'No se pudo guardar la configuración')
    },
  })

  const testConnectionMutation = useMutation({
    mutationFn: () => api.email.testConnection(),
    onSuccess: () => {
      toast.success('Conexión exitosa', 'Se conectó correctamente al servidor SMTP')
    },
    onError: (error) => {
      toast.error('Error de conexión', error.response?.data?.error || 'No se pudo conectar al servidor SMTP')
    },
  })

  const testSendMutation = useMutation({
    mutationFn: (data) => api.email.testSend(data),
    onSuccess: () => {
      toast.success('Email de prueba enviado', `Se envió correctamente a ${testEmail}`)
    },
    onError: (error) => {
      toast.error('Error al enviar', error.response?.data?.error || 'No se pudo enviar el email de prueba')
    },
  })

  const handleSave = () => {
    const payload = {
      smtp_host: formData.smtp_host,
      smtp_port: parseInt(formData.smtp_port, 10),
      smtp_use_tls: formData.smtp_use_tls,
      smtp_user: formData.smtp_user,
      from_email: formData.from_email,
      from_name: formData.from_name,
      email_habilitado: formData.email_habilitado,
      email_asunto: formData.email_asunto,
      email_mensaje: formData.email_mensaje,
      email_saludo: formData.email_saludo,
    }
    if (formData.smtp_password) {
      payload.smtp_password = formData.smtp_password
    }
    saveMutation.mutate(payload)
  }

  const handleTestConnection = () => {
    testConnectionMutation.mutate()
  }

  const handleTestSend = () => {
    if (!testEmail) {
      toast.warning('Ingresá un email de destino para la prueba')
      return
    }
    testSendMutation.mutate({ to_email: testEmail })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* SMTP Config */}
      <Card>
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Servidor SMTP</h2>
            <p className="text-sm text-text-muted">
              Configurá el servidor de email para enviar comprobantes a los receptores.
            </p>
          </div>
          {config?.configured ? (
            <Badge variant="success">Configurado</Badge>
          ) : (
            <Badge variant="warning">Sin configurar</Badge>
          )}
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <Input
              label="Host SMTP"
              placeholder="smtp.gmail.com"
              value={formData.smtp_host}
              onChange={(e) => setFormData({ ...formData, smtp_host: e.target.value })}
              className="col-span-2"
            />
            <Input
              label="Puerto"
              type="number"
              placeholder="587"
              value={formData.smtp_port}
              onChange={(e) => setFormData({ ...formData, smtp_port: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Usuario SMTP"
              placeholder="user@gmail.com"
              value={formData.smtp_user}
              onChange={(e) => setFormData({ ...formData, smtp_user: e.target.value })}
            />
            <Input
              label={config?.tiene_password ? 'Contraseña SMTP (dejar vacío para mantener)' : 'Contraseña SMTP'}
              type="password"
              placeholder={config?.tiene_password ? '••••••••' : 'App password'}
              value={formData.smtp_password}
              onChange={(e) => setFormData({ ...formData, smtp_password: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Email remitente"
              placeholder="noreply@empresa.com"
              value={formData.from_email}
              onChange={(e) => setFormData({ ...formData, from_email: e.target.value })}
            />
            <Input
              label="Nombre remitente"
              placeholder="Mi Empresa"
              value={formData.from_name}
              onChange={(e) => setFormData({ ...formData, from_name: e.target.value })}
            />
          </div>

          <div className="flex items-center gap-6">
            <Checkbox
              label="Usar TLS"
              checked={formData.smtp_use_tls}
              onChange={(e) => setFormData({ ...formData, smtp_use_tls: e.target.checked })}
            />
            <Checkbox
              label="Email habilitado"
              checked={formData.email_habilitado}
              onChange={(e) => setFormData({ ...formData, email_habilitado: e.target.checked })}
            />
          </div>

          {!formData.email_habilitado && (
            <p className="text-sm text-warning">
              El envío automático de comprobantes por email está deshabilitado.
            </p>
          )}
        </div>

        <div className="mt-6 flex items-center gap-3">
          <Button
            icon={Save}
            onClick={handleSave}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? 'Guardando...' : 'Guardar configuración'}
          </Button>
          <Button
            variant="secondary"
            icon={Wifi}
            onClick={handleTestConnection}
            disabled={!config?.configured || testConnectionMutation.isPending}
          >
            {testConnectionMutation.isPending ? 'Testeando...' : 'Testear conexión'}
          </Button>
        </div>
      </Card>

      {/* Personalización del email */}
      {config?.configured && (
        <Card>
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-text-primary">Personalización del email</h2>
            <p className="text-sm text-text-muted">
              Personalizá el contenido del email que se envía con los comprobantes.
              Dejá los campos vacíos para usar los valores predeterminados.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <Input
                label="Asunto"
                placeholder="Comprobante 00001-00000042 - Mi Empresa SRL"
                value={formData.email_asunto}
                onChange={(e) => setFormData({ ...formData, email_asunto: e.target.value })}
              />
              <p className="mt-1 text-xs text-text-muted">
                Podés usar <code className="rounded bg-secondary px-1">{'{comprobante}'}</code> y <code className="rounded bg-secondary px-1">{'{facturador}'}</code> para insertar datos automáticamente.
              </p>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-text-primary">
                Mensaje principal
              </label>
              <textarea
                className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                rows={5}
                placeholder="Adjunto encontrará el comprobante electrónico correspondiente."
                value={formData.email_mensaje}
                onChange={(e) => setFormData({ ...formData, email_mensaje: e.target.value })}
              />
              <p className="mt-1 text-xs text-text-muted">
                Texto que aparece en el cuerpo del email. Podés incluir información de pago, datos bancarios, etc.
              </p>
            </div>

            <Input
              label="Saludo"
              placeholder="Saludos cordiales"
              value={formData.email_saludo}
              onChange={(e) => setFormData({ ...formData, email_saludo: e.target.value })}
            />
          </div>

          <div className="mt-6">
            <Button
              icon={Save}
              onClick={handleSave}
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? 'Guardando...' : 'Guardar configuración'}
            </Button>
          </div>
        </Card>
      )}

      {/* Test Send */}
      {config?.configured && (
        <Card>
          <div className="mb-5">
            <h2 className="text-lg font-semibold text-text-primary">Email de prueba</h2>
            <p className="text-sm text-text-muted">
              Enviá un email de prueba para verificar que todo funciona correctamente.
            </p>
          </div>

          <div className="flex items-end gap-3">
            <Input
              label="Email de destino"
              type="email"
              placeholder="test@ejemplo.com"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              className="flex-1"
            />
            <Button
              variant="secondary"
              icon={Send}
              onClick={handleTestSend}
              disabled={testSendMutation.isPending}
            >
              {testSendMutation.isPending ? 'Enviando...' : 'Enviar prueba'}
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}

export default Email
