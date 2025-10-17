from flask import Flask, Blueprint, request, session, render_template, jsonify, flash
import os
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import io
import base64
from db import get_db
from auth import login_required


bp = Blueprint('home', __name__)

# Load model
model = load_model('model/rice_crop_disease_model_densenet121.h5')
class_names = [
    'Bacterial leaf blight',
    'Bacterial leaf streak',
    'Bacterial panicle blight',
    'Blast',
    'Brown spot',
    'Dead heart',
    'Downy mildew',
    'Hispa',
    'Healthy',
    'Tungro'
]

def preprocess(img):
    img = img.resize((256, 256))
    img_array = image.img_to_array(img)
    img_array = img_array / 255.0
    return np.expand_dims(img_array, axis=0)


@bp.route('/')
@login_required
def index():
    db = get_db()
    user = db.execute('SELECT * FROM user WHERE user_id = ?', (session['user_id'],)).fetchone()
    return render_template('index.html', user=user)


@bp.route('/predict', methods=['POST'])
@login_required
def predict():
    if 'images' not in request.files:
        return jsonify({'error': 'No images uploaded'}), 400

    files = request.files.getlist('images')

    if len(files) > 30:
        return jsonify({'error': 'Too many images! Max 30 images allowed.'}), 400

    user_id = session.get('user_id', None)    
    batch_id = str(uuid.uuid4())
    batch_name = f"{len(files)} rice crop image{'s' if len(files) > 1 else ''}"
    timestamp = datetime.now()

    results = []
    db = get_db()

    for file in files:
        filename = secure_filename(file.filename)
        image_data = file.read()
        file.stream.seek(0)

        # Predict
        img = Image.open(file.stream).convert('RGB')
        processed = preprocess(img)
        pred = model.predict(processed)
        class_index = np.argmax(pred)
        result = class_names[class_index]

        # Save to DB
        db.execute(
            'INSERT INTO history (user_id, batch_id, batch_name, pred_image, image_name, pred_result, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, batch_id, batch_name, image_data, filename, result, timestamp)
        )

        # Convert image to base64 for display
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        results.append({
            'image_name': filename,
            'prediction': result,
            'image_base64': encoded_image
        })

    db.commit()

    return jsonify({'predictions': results})
