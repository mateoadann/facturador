class ArcaError(Exception):
    """Error base de ARCA."""
    pass


class ArcaAuthError(ArcaError):
    """Error de autenticación con ARCA."""
    pass


class ArcaValidationError(ArcaError):
    """Error de validación de datos para ARCA."""
    pass


class ArcaNetworkError(ArcaError):
    """Error de red al comunicarse con ARCA."""
    pass
