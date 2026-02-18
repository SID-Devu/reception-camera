camera_settings = {
    "resolution": (1920, 1080),
    "fps": 30,
    "camera_index": 0
}

database_config = {
    "host": "localhost",
    "port": 5432,
    "user": "your_username",
    "password": "your_password",
    "database": "reception_camera_db"
}

recognition_thresholds = {
    "face_distance_threshold": 0.6,
    "confidence_threshold": 0.7
}

enrollment_settings = {
    "max_samples": 5,
    "augmentation": True
}

greeting_settings = {
    "greeting_message": "Welcome, {name}!",
    "farewell_message": "Goodbye, {name}!"
}