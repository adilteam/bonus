import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, send_from_directory
import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from extensions import init_extensions, db, sse
import time
from sqlalchemy import create_engine

# Create the app
app = Flask(__name__)

# Configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/customer_bonus.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Customer Bonus startup')

# Configure the app
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "a secret key")
app.config['STATIC_FOLDER'] = 'static'

# Set production configuration
app.config['DEBUG'] = False
app.config['ENV'] = 'production'

# PostgreSQL connection
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL', 'postgresql://adil_database_user:ADSnWcp5ngzXNC7kt5ZuC0YPu3gubAz8@dpg-cvor58k9c44c73br2uag-a.oregon-postgres.render.com/adil_database')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Redis connection configuration (optional, only if Redis is used)
redis_url = os.environ.get('REDIS_URL', None)
if redis_url:
    app.config['REDIS_URL'] = redis_url

# Configure SQLAlchemy connection pool
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
    "pool_timeout": 30,
    "pool_size": 10,
    "max_overflow": 5
}

# Configure Redis for real-time notifications (optional)
REDIS_RETRY_ATTEMPTS = 3
REDIS_RETRY_DELAY = 2  # seconds
REDIS_CONFIG = {
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'socket_keepalive': True,
    'health_check_interval': 30,
    'retry_on_timeout': True,
    'decode_responses': True
}

def connect_redis_with_retry():
    """Attempt to connect to Redis with retry logic"""
    app.logger.info("Attempting to connect to Redis")
    
    for attempt in range(REDIS_RETRY_ATTEMPTS):
        try:
            redis_client = redis.from_url(redis_url, **REDIS_CONFIG)
            redis_client.ping()
            app.logger.info("Redis connection successful")
            return redis_client
        except RedisConnectionError as e:
            if attempt < REDIS_RETRY_ATTEMPTS - 1:
                wait_time = REDIS_RETRY_DELAY * (attempt + 1)
                app.logger.warning(f"Redis connection attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                app.logger.error(f"Failed to connect to Redis after {REDIS_RETRY_ATTEMPTS} attempts")
                return None
        except Exception as e:
            app.logger.error(f"Unexpected Redis error: {str(e)}")
            return None

# Try to initialize Redis connection (optional)
if redis_url:
    redis_client = connect_redis_with_retry()
    if redis_client:
        app.config['NOTIFICATIONS_ENABLED'] = True
        app.config['REDIS_PUBSUB_OPTIONS'] = {
            'channel_prefix': 'sse',
            'retry_interval': 5000,
            'max_retry_interval': 30000
        }
    else:
        app.logger.warning("Redis connection failed, falling back to database-only notifications")

# Initialize extensions
try:
    init_extensions(app)
    app.logger.info("Extensions initialized successfully")
except Exception as e:
    app.logger.error(f"Failed to initialize extensions: {str(e)}")
    raise

# Import routes after app is created
import routes  # noqa: F401
import admin  # noqa: F401

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    app.logger.error(f'Page not found: {error}')
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    app.logger.error(f'Server Error: {error}')
    return render_template('errors/500.html'), 500

# Static file handling for production
@app.route('/static/<path:filename>')
def serve_static(filename):
    cache_timeout = 2592000  # 30 days
    return send_from_directory(
        app.static_folder or 'static',
        filename,
        cache_timeout=cache_timeout
    )
