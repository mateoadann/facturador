import { Navigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuthStore } from '@/stores/authStore'
import { useLogin } from '@/hooks/useAuth'
import { Button, Input } from '@/components/ui'

const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(1, 'Contraseña requerida'),
})

function Login() {
  const { accessToken } = useAuthStore()
  const { mutate: login, isPending, error } = useLogin()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
  })

  if (accessToken) {
    return <Navigate to="/dashboard" replace />
  }

  const onSubmit = (data) => {
    login(data)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F8FAFC]">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <img
            src="/factura.png"
            alt="Facturador"
            className="mx-auto mb-4 h-16 w-16 rounded-xl object-cover"
          />
          <h1 className="text-2xl font-semibold text-text-primary">
            Facturador
          </h1>
          <p className="mt-2 text-text-secondary">
            Ingresá tus credenciales para continuar
          </p>
        </div>

        {/* Form */}
        <div className="rounded-lg bg-card p-8 shadow-sm">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <Input
              label="Email"
              type="email"
              placeholder="tu@email.com"
              error={errors.email?.message}
              {...register('email')}
            />

            <Input
              label="Contraseña"
              type="password"
              placeholder="••••••••"
              error={errors.password?.message}
              {...register('password')}
            />

            {error && (
              <div className="rounded-md bg-error-light p-3 text-sm text-error-foreground">
                {error.response?.data?.error || 'Error al iniciar sesión'}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? 'Ingresando...' : 'Ingresar'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default Login
