from flask import Flask
from flask_cors import CORS

from .extensions import db, jwt, migrate, init_celery
from .config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    init_celery(app)
    CORS(app, origins=app.config['CORS_ORIGINS'].split(','))

    # Register blueprints
    from .api.auth import auth_bp
    from .api.dashboard import dashboard_bp
    from .api.facturadores import facturadores_bp
    from .api.receptores import receptores_bp
    from .api.facturas import facturas_bp
    from .api.lotes import lotes_bp
    from .api.jobs import jobs_bp
    from .api.comprobantes import comprobantes_bp
    from .api.usuarios import usuarios_bp
    from .api.audit import audit_bp
    from .api.email import email_bp
    from .api.downloads import downloads_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(facturadores_bp, url_prefix='/api/facturadores')
    app.register_blueprint(receptores_bp, url_prefix='/api/receptores')
    app.register_blueprint(facturas_bp, url_prefix='/api/facturas')
    app.register_blueprint(lotes_bp, url_prefix='/api/lotes')
    app.register_blueprint(jobs_bp, url_prefix='/api/jobs')
    app.register_blueprint(comprobantes_bp, url_prefix='/api/comprobantes')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(audit_bp, url_prefix='/api/audit')
    app.register_blueprint(email_bp, url_prefix='/api/email')
    app.register_blueprint(downloads_bp, url_prefix='/api/downloads')

    return app
