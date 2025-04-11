from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, flash, current_app
from flask_admin.form import rules
from extensions import admin, db, sse
from models import User, Gift
from werkzeug.security import generate_password_hash
from redis.exceptions import ConnectionError as RedisConnectionError
import json
from datetime import datetime

class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.customer_code == 'ADMIN'

    def inaccessible_callback(self, name, **kwargs):
        flash('Please login as admin to access this page.')
        return redirect(url_for('admin_login'))

class UserAdmin(AdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    
    column_list = ['customer_code', 'name', 'surname', 'email', 'bonus_points', 'profile_picture']
    column_searchable_list = ['customer_code', 'email', 'name', 'surname']
    column_filters = ['customer_code', 'bonus_points']
    
    form_columns = ['customer_code', 'name', 'surname', 'email', 'bonus_points', 'profile_picture']
    form_excluded_columns = ['password_hash', 'notifications', 'selected_gift_id']
    
    def on_model_change(self, form, model, is_created):
        if is_created:
            model.set_password('default_password')
            current_app.logger.info(f"Created new user: {model.customer_code}")
            flash(f'New user created with default password: default_password')

        # Send notification for bonus points update
        if not is_created and form.bonus_points.data != model.bonus_points:
            current_app.logger.info(f"Updating bonus points for user {model.id} from {model.bonus_points} to {form.bonus_points.data}")
            try:
                # Create notification in database
                notification = model.add_notification(
                    'Bonus Points Updated!',
                    f'Your bonus points have been updated to {form.bonus_points.data}'
                )
                db.session.flush()  # Ensure notification has an ID
                
                # Prepare notification data with bonus points update
                notification_data = {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'timestamp': notification.timestamp.isoformat(),
                    'bonus_points': form.bonus_points.data,
                    'type': 'bonus_update',
                    'user_id': model.id
                }

                # Only attempt SSE publish if Redis is enabled
                if current_app.config.get('NOTIFICATIONS_ENABLED', False):
                    try:
                        channel = f'user_{model.id}'
                        current_app.logger.debug(f"Publishing notification to channel: {channel}")
                        current_app.logger.debug(f"Notification data: {json.dumps(notification_data)}")
                        
                        sse.publish(
                            notification_data,
                            type='notification',
                            channel=channel
                        )
                        current_app.logger.info(f"Notification sent to user {model.id} via channel {channel}")
                    except RedisConnectionError as e:
                        current_app.logger.error(f"Redis publish error: {str(e)}")
                        current_app.logger.error(f"Redis connection details: {current_app.config.get('REDIS_URL')}")
                        flash("Notification saved but real-time delivery failed", "warning")
                else:
                    current_app.logger.warning("Real-time notifications are disabled")
                
                db.session.commit()
                current_app.logger.info(f"Bonus points update completed for user {model.id}")
            except Exception as e:
                current_app.logger.error(f"Notification error for user {model.id}: {str(e)}")
                db.session.rollback()
                flash("Failed to create notification", "error")
                raise

class GiftAdmin(AdminModelView):
    can_create = True
    can_edit = True
    can_delete = True
    
    column_list = ['name', 'description', 'points_required', 'available']
    column_searchable_list = ['name', 'description']
    column_filters = ['available', 'points_required']
    
    form_columns = ['name', 'description', 'points_required', 'available']
    
    def after_model_change(self, form, model, is_created):
        # Send notifications when a gift becomes available
        if model.available:
            current_app.logger.info(f"Processing gift availability notifications for gift: {model.name}")
            try:
                users = User.query.filter(User.customer_code != 'ADMIN').all()
                current_app.logger.debug(f"Sending gift notifications to {len(users)} users")
                
                for user in users:
                    notification = user.add_notification(
                        'New Gift Available!',
                        f'The gift "{model.name}" is now available for {model.points_required} points!'
                    )
                    db.session.flush()  # Ensure notification has an ID
                    
                    notification_data = {
                        'id': notification.id,
                        'title': notification.title,
                        'message': notification.message,
                        'timestamp': notification.timestamp.isoformat(),
                        'type': 'gift_available',
                        'gift_id': model.id,
                        'user_id': user.id
                    }
                    
                    if current_app.config.get('NOTIFICATIONS_ENABLED', False):
                        try:
                            channel = f'user_{user.id}'
                            current_app.logger.debug(f"Publishing gift notification to channel: {channel}")
                            
                            sse.publish(
                                notification_data,
                                type='notification',
                                channel=channel
                            )
                            current_app.logger.info(f"Gift notification sent to user {user.id} via channel {channel}")
                        except RedisConnectionError as e:
                            current_app.logger.error(f"Redis publish error for gift notification to user {user.id}: {str(e)}")
                            continue  # Continue with other users even if one fails
                
                db.session.commit()
                current_app.logger.info(f"Gift availability notifications completed for gift: {model.name}")
            except Exception as e:
                current_app.logger.error(f"Gift notification error: {str(e)}")
                db.session.rollback()
                flash("Failed to send gift notifications", "error")
                raise

# Register admin views
admin.add_view(UserAdmin(User, db.session))
admin.add_view(GiftAdmin(Gift, db.session))
