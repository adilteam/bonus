# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_admin import Admin
from flask_sse import sse

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
admin = Admin(name='Customer Bonus Admin', template_mode='bootstrap3')

def init_extensions(app):
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Initialize Flask-Admin
    admin.init_app(app)

    # Register SSE blueprint
    app.register_blueprint(sse, url_prefix='/stream')

    # Import models after db is initialized to avoid circular imports
    with app.app_context():
        from models import User
        
        @login_manager.user_loader
        def load_user(id):
            return User.query.get(int(id))
            
        # Create tables
        db.create_all()
        app.logger.info("Database initialized successfully")
