from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app import app
from extensions import db
from models import User, Gift, Notification
from forms import LoginForm, RegistrationForm, SettingsForm
from utils import save_picture
from datetime import datetime
from sqlalchemy import or_
import cv2
import face_recognition
import numpy as np

# ... (keep all your existing routes)

@app.route('/login_with_face', methods=['POST'])
def login_with_face():
    if not request.files.get('image'):
        return jsonify({"success": False, "error": "No image provided"}), 400
    
    email = request.form.get('email')
    if not email:
        return jsonify({"success": False, "error": "Email required"}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    try:
        # Read and process image
        file = request.files['image']
        img_array = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # Detect face
        face_locations = face_recognition.face_locations(frame)
        if not face_locations:
            return jsonify({"success": False, "error": "No face detected"}), 400
            
        current_encoding = face_recognition.face_encodings(frame, face_locations)[0]
        
        # Verify against stored encoding
        if user.face_encoding and face_recognition.compare_faces(
            [user.get_face_encoding()], 
            current_encoding
        )[0]:
            login_user(user)
            return jsonify({
                "success": True,
                "redirect": "/admin/" if user.customer_code == "ADMIN" else "/dashboard"
            })
            
        return jsonify({"success": False, "error": "Face verification failed"}), 401
        
    except Exception as e:
        app.logger.error(f"Face login error: {str(e)}")
        return jsonify({"success": False, "error": "Processing error"}), 500

@app.route('/register_face', methods=['POST'])
@login_required
def register_face():
    if not request.files.get('image'):
        return jsonify({"success": False, "error": "No image provided"}), 400
    
    try:
        # Read and process image
        file = request.files['image']
        img_array = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # Detect and store face encoding
        face_locations = face_recognition.face_locations(frame)
        if not face_locations:
            return jsonify({"success": False, "error": "No face detected"}), 400
            
        current_user.set_face_encoding(face_recognition.face_encodings(frame, face_locations)[0])
        db.session.commit()
        return jsonify({"success": True})
        
    except Exception as e:
        app.logger.error(f"Face registration error: {str(e)}")
        return jsonify({"success": False, "error": "Processing error"}), 500
