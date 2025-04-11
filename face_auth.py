# face_auth.py dosyası oluşturalım
import cv2
import face_recognition
import numpy as np

def capture_face():
    """Basit kamera yakalama fonksiyonu"""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Kamera açılamadı")
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise RuntimeError("Kare yakalanamadı")
    
    return frame

def detect_face(frame):
    """Yüz tespiti ve encoding işlemi"""
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    
    if not face_locations:
        raise ValueError("Yüz bulunamadı")
    
    return face_recognition.face_encodings(rgb_frame, face_locations)[0]
