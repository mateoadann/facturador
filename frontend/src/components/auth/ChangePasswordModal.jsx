import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/api/client'
import { toast } from '@/stores/toastStore'
import { Button, Input, Modal } from '@/components/ui'

function ChangePasswordModal({ isOpen, onClose }) {
  const [formData, setFormData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [errors, setErrors] = useState({})

  const mutation = useMutation({
    mutationFn: (data) => api.auth.changePassword(data),
    onSuccess: () => {
      toast.success('Contraseña actualizada correctamente')
      handleClose()
    },
    onError: (error) => {
      toast.error(
        'Error al cambiar contraseña',
        error.response?.data?.error || 'No se pudo cambiar la contraseña'
      )
    },
  })

  const handleClose = () => {
    setFormData({ current_password: '', new_password: '', confirm_password: '' })
    setErrors({})
    onClose()
  }

  const validate = () => {
    const newErrors = {}

    if (!formData.current_password) {
      newErrors.current_password = 'La contraseña actual es requerida'
    }

    if (!formData.new_password) {
      newErrors.new_password = 'La nueva contraseña es requerida'
    } else if (formData.new_password.length < 8) {
      newErrors.new_password = 'Mínimo 8 caracteres'
    }

    if (formData.new_password !== formData.confirm_password) {
      newErrors.confirm_password = 'Las contraseñas no coinciden'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = () => {
    if (!validate()) return

    mutation.mutate({
      current_password: formData.current_password,
      new_password: formData.new_password,
    })
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Cambiar Contraseña"
      className="max-w-md"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={mutation.isPending}>
            {mutation.isPending ? 'Guardando...' : 'Cambiar Contraseña'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <Input
            label="Contraseña actual"
            type="password"
            placeholder="••••••••"
            value={formData.current_password}
            onChange={(e) =>
              setFormData({ ...formData, current_password: e.target.value })
            }
          />
          {errors.current_password && (
            <p className="mt-1 text-xs text-error">{errors.current_password}</p>
          )}
        </div>

        <div>
          <Input
            label="Nueva contraseña"
            type="password"
            placeholder="Mínimo 8 caracteres"
            value={formData.new_password}
            onChange={(e) =>
              setFormData({ ...formData, new_password: e.target.value })
            }
          />
          {errors.new_password && (
            <p className="mt-1 text-xs text-error">{errors.new_password}</p>
          )}
        </div>

        <div>
          <Input
            label="Confirmar nueva contraseña"
            type="password"
            placeholder="Repetir nueva contraseña"
            value={formData.confirm_password}
            onChange={(e) =>
              setFormData({ ...formData, confirm_password: e.target.value })
            }
          />
          {errors.confirm_password && (
            <p className="mt-1 text-xs text-error">{errors.confirm_password}</p>
          )}
        </div>

        {mutation.error && (
          <div className="rounded-md bg-error-light p-3 text-sm text-error-foreground">
            {mutation.error.response?.data?.error || 'Error al cambiar la contraseña'}
          </div>
        )}
      </div>
    </Modal>
  )
}

export default ChangePasswordModal
