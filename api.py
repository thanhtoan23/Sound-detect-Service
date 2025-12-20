"""REST API for Sound Detection Service"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time

from sound_service import SoundDetectionService

app = Flask(__name__)
CORS(app)

service = None
service_lock = threading.Lock()


@app.route('/')
def index():
    return jsonify({
        'name': 'ReSpeaker Sound Detection API',
        'version': '1.0.0',
        'endpoints': {
            'GET /status': 'Lấy trạng thái hiện tại',
            'GET /statistics': 'Lấy thống kê',
            'GET /history': 'Lấy lịch sử events',
            'GET /history?limit=N': 'Lấy N events gần nhất',
            'POST /start': 'Khởi động service',
            'POST /stop': 'Dừng service',
            'POST /led/brightness': 'Đổi độ sáng LED (body: {brightness: 0-100})',
            'POST /led/pattern': 'Đổi LED pattern (body: {pattern: "echo"|"google"})',
            'POST /led/off': 'Tắt LED',
        }
    })


@app.route('/status', methods=['GET'])
def get_status():
    global service
    
    with service_lock:
        if service is None or not service.is_running:
            return jsonify({
                'running': False,
                'message': 'Service is not running'
            }), 503
        
        state = service.get_current_state()
        
        return jsonify({
            'running': True,
            'state': state
        })


@app.route('/statistics', methods=['GET'])
def get_statistics():
    global service
    
    with service_lock:
        if service is None:
            return jsonify({
                'error': 'Service not initialized'
            }), 503
        
        stats = service.get_statistics()
        
        return jsonify({
            'running': service.is_running,
            'statistics': stats
        })


@app.route('/history', methods=['GET'])
def get_history():
    global service
    
    with service_lock:
        if service is None:
            return jsonify({
                'error': 'Service not initialized'
            }), 503
        
        limit = request.args.get('limit', default=50, type=int)
        limit = max(1, min(limit, 1000))
        
        history = service.get_history(limit=limit)
        
        return jsonify({
            'count': len(history),
            'limit': limit,
            'events': history
        })


@app.route('/start', methods=['POST'])
def start_service():
    global service
    
    with service_lock:
        if service is not None and service.is_running:
            return jsonify({
                'success': False,
                'message': 'Service is already running'
            }), 400
        
        data = request.get_json() or {}
        enable_led = data.get('enable_led', True)
        enable_audio = data.get('enable_audio_classification', True)
        
        service = SoundDetectionService(
            enable_led=enable_led,
            enable_audio_classification=enable_audio
        )
        
        if service.start():
            return jsonify({
                'success': True,
                'message': 'Service started successfully',
                'config': {
                    'enable_led': enable_led,
                    'enable_audio_classification': enable_audio
                }
            })
        else:
            service = None
            return jsonify({
                'success': False,
                'message': 'Failed to start service'
            }), 500


@app.route('/stop', methods=['POST'])
def stop_service():
    global service
    
    with service_lock:
        if service is None or not service.is_running:
            return jsonify({
                'success': False,
                'message': 'Service is not running'
            }), 400
        
        service.stop()
        service = None
        
        return jsonify({
            'success': True,
            'message': 'Service stopped successfully'
        })


@app.route('/led/brightness', methods=['POST'])
def set_led_brightness():
    global service
    
    with service_lock:
        if service is None or not service.is_running:
            return jsonify({
                'success': False,
                'message': 'Service is not running'
            }), 503
        
        if not service.enable_led or service.led_visualizer is None:
            return jsonify({
                'success': False,
                'message': 'LED visualization is not enabled'
            }), 400
        
        data = request.get_json()
        if not data or 'brightness' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing brightness parameter'
            }), 400
        
        brightness = data['brightness']
        
        if not isinstance(brightness, int) or brightness < 0 or brightness > 100:
            return jsonify({
                'success': False,
                'message': 'Brightness must be an integer between 0 and 100'
            }), 400
        
        service.led_visualizer.set_brightness(brightness)
        
        return jsonify({
            'success': True,
            'brightness': brightness
        })


@app.route('/led/pattern', methods=['POST'])
def set_led_pattern():
    global service
    
    with service_lock:
        if service is None or not service.is_running:
            return jsonify({
                'success': False,
                'message': 'Service is not running'
            }), 503
        
        if not service.enable_led or service.led_visualizer is None:
            return jsonify({
                'success': False,
                'message': 'LED visualization is not enabled'
            }), 400
        
        data = request.get_json()
        if not data or 'pattern' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing pattern parameter'
            }), 400
        
        pattern = data['pattern']
        
        if pattern not in ['echo', 'google']:
            return jsonify({
                'success': False,
                'message': 'Pattern must be "echo" or "google"'
            }), 400
        
        service.led_visualizer.change_pattern(pattern)
        
        return jsonify({
            'success': True,
            'pattern': pattern
        })


@app.route('/led/off', methods=['POST'])
def turn_off_led():
    global service
    
    with service_lock:
        if service is None or not service.is_running:
            return jsonify({
                'success': False,
                'message': 'Service is not running'
            }), 503
        
        if not service.enable_led or service.led_visualizer is None:
            return jsonify({
                'success': False,
                'message': 'LED visualization is not enabled'
            }), 400
        
        service.led_visualizer.off()
        
        return jsonify({
            'success': True,
            'message': 'LED turned off'
        })


@app.route('/health', methods=['GET'])
def health_check():
    global service
    
    with service_lock:
        return jsonify({
            'healthy': True,
            'service_running': service is not None and service.is_running if service else False,
            'timestamp': time.time()
        })


def run_api(host='0.0.0.0', port=5000, debug=False, auto_start_service=True):
    global service
    
    print("=" * 60)
    print("🌐 Starting ReSpeaker Sound Detection API")
    print("=" * 60)
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Debug: {debug}")
    print(f"  Auto-start service: {auto_start_service}")
    print()
    
    if auto_start_service:
        print("🚀 Auto-starting sound detection service...")
        service = SoundDetectionService(
            #enable_led=True,
            enable_audio_classification=True
        )
        if service.start():
            print("✅ Service started successfully")
        else:
            print("❌ Failed to start service")
            service = None
        print()
    
    try:
        print("🌐 API server is running!")
        print(f"   Access at: http://{host}:{port}")
        print(f"   API docs at: http://{host}:{port}/")
        print()
        print("   Nhấn Ctrl+C để dừng")
        print("=" * 60)
        
        app.run(host=host, port=port, debug=debug, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\n\nStopping API server...")
    finally:
        if service and service.is_running:
            print("🧹 Stopping service...")
            service.stop()
        print("Goodbye!")


if __name__ == '__main__':
    run_api(
        host='0.0.0.0',
        port=5000,
        debug=False,
        auto_start_service=True
    )
