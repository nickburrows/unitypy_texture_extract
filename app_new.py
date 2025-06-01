import os
from flask import Flask, request, render_template, send_file, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
import UnityPy
from PIL import Image
import io
import shutil
from pathlib import Path
import traceback

app = Flask(__name__)

# 配置設定
def configure_app(app):
    """配置 Flask 應用程式的設定"""
    if os.environ.get('FLASK_ENV') == 'production':
        if 'FLASK_SECRET_KEY' not in os.environ:
            raise RuntimeError('錯誤：在生產環境中必須設定 FLASK_SECRET_KEY 環境變數！')
        app.secret_key = os.environ['FLASK_SECRET_KEY']
    else:
        app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(24)

configure_app(app)

# 檔案大小限制
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['MAX_FILE_SIZE'] = 500  # MB

# 設定檔案夾路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'extracted')
MODIFIED_FOLDER = os.path.join(BASE_DIR, 'modified')

# 建立必要的檔案夾
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, MODIFIED_FOLDER]:
    os.makedirs(folder, exist_ok=True)
    os.makedirs(os.path.join(folder, 'temp'), exist_ok=True)

class AssetHandler:
    def __init__(self):
        self.original_file = None
        self.modified_file = None
        self.unity_env = None
    
    def set_files(self, original_file):
        """設置檔案路徑"""
        self.original_file = os.path.abspath(original_file)
        self.modified_file = os.path.join(MODIFIED_FOLDER, os.path.basename(original_file))
        
        # 複製主要檔案
        shutil.copy2(self.original_file, self.modified_file)
        
        # 複製 .resS 檔案（如果存在）
        ress_original = self.original_file + '.resS'
        ress_modified = self.modified_file + '.resS'
        if os.path.exists(ress_original):
            shutil.copy2(ress_original, ress_modified)
    
    def load_environment(self):
        """載入 Unity 環境"""
        self.unity_env = UnityPy.load(self.modified_file)
    
    def extract_textures(self):
        """提取所有紋理"""
        if not self.unity_env:
            self.load_environment()
        
        extracted = []
        for obj in self.unity_env.objects:
            if obj.type.name not in ["Texture2D", "Sprite"]:
                continue
            
            try:
                data = obj.read()
                name = data.name if hasattr(data, 'name') else f'{obj.type.name.lower()}_{obj.path_id}'
                
                if hasattr(data, 'image') and data.image:
                    output_path = os.path.join(OUTPUT_FOLDER, f'{name}.png')
                    data.image.save(output_path)
                    
                    extracted.append({
                        'name': name,
                        'type': obj.type.name,
                        'path_id': obj.path_id,
                        'path': os.path.basename(output_path)
                    })
            except Exception as e:
                print(f"處理 {obj.type.name} (path_id: {obj.path_id}) 時發生錯誤: {e}")
        
        return extracted
    
    def replace_texture(self, path_id, image_path):
        """替換指定的紋理"""
        try:
            print(f"開始處理紋理替換...")
            print(f"目標 Path ID: {path_id}")
            print(f"新圖片路徑: {image_path}")
            
            if not self.unity_env:
                print("重新載入資源檔案...")
                self.load_environment()
            
            # 載入新圖片
            print("載入新圖片...")
            new_image = Image.open(image_path)
            print(f"新圖片大小: {new_image.size}")
            new_image = new_image.convert('RGBA')
            
            # 尋找目標紋理
            target_obj = None
            for obj in self.unity_env.objects:
                if obj.path_id == int(path_id):
                    target_obj = obj
                    break
            
            if not target_obj:
                raise ValueError("找不到指定的資源 ID")
            
            if target_obj.type.name not in ["Texture2D", "Sprite"]:
                raise ValueError(f"指定的資源不是紋理或精靈圖片 (類型: {target_obj.type.name})")
            
            print(f"開始處理 {target_obj.type.name} (path_id: {path_id})")
            
            # 讀取並更新圖片
            data = target_obj.read()
            if not hasattr(data, 'image'):
                raise ValueError("目標物件沒有圖片資料")
            
            # 保存原始設定
            original_settings = {
                "m_TextureFormat": data.m_TextureFormat,
                "m_CompleteImageSize": data.m_CompleteImageSize,
                "m_TextureDimension": data.m_TextureDimension,
                "m_TextureSettings": data.m_TextureSettings,
                "m_StreamData": data.m_StreamData,
                "m_MipMap": data.m_MipMap,
                "m_IsReadable": data.m_IsReadable,
            }
            
            # 調整圖片大小
            if data.image and new_image.size != data.image.size:
                print(f"調整圖片大小從 {new_image.size} 到 {data.image.size}")
                new_image = new_image.resize(data.image.size)
            
            print("更新紋理圖片...")
            # 更新圖片
            data.image = new_image
            
            # 還原原始設定
            print("還原原始設定...")
            for key, value in original_settings.items():
                if hasattr(data, key):
                    setattr(data, key, value)
            
            try:
                print("儲存物件變更...")
                # 將修改後的數據寫回
                data.save()
            except Exception as e:
                print(f"使用原始格式儲存失敗，嘗試使用 RGBA32 格式: {str(e)}")
                # 如果儲存失敗，嘗試使用預設格式
                data.m_TextureFormat = 4  # RGBA32 format
                data.save()
            
            # 儲存修改後的檔案
            print("儲存已編輯的檔案...")
            if os.path.exists(self.modified_file):
                print(f"刪除已存在的檔案: {self.modified_file}")
                os.remove(self.modified_file)
            
            print(f"寫入新檔案: {self.modified_file}")
            with open(self.modified_file, 'wb') as f:
                file_data = self.unity_env.file.save()
                f.write(file_data)
                print(f"檔案儲存成功，大小: {len(file_data)} bytes")
            
            # 檢查並複製 .resS 檔案
            ress_file = self.original_file + '.resS'
            if os.path.exists(ress_file):
                output_ress = self.modified_file + '.resS'
                print(f"複製 .resS 檔案到: {output_ress}")
                shutil.copy2(ress_file, output_ress)
            
            # 重新載入並驗證
            print("重新載入環境進行驗證...")
            self.load_environment()
            for obj in self.unity_env.objects:
                if obj.path_id == int(path_id):
                    verify_data = obj.read()
                    if hasattr(verify_data, 'image') and verify_data.image:
                        print(f"驗證成功：新圖片大小為 {verify_data.image.size}")
                        return True, "修改成功"
            
            raise ValueError("驗證失敗：找不到更新後的紋理")
            
        except Exception as e:
            error_msg = f"替換紋理時發生錯誤: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())  # 印出完整的錯誤堆疊
            return False, error_msg

# 全域變數
asset_handler = AssetHandler()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            flash('沒有上傳檔案', 'error')
            return redirect(url_for('index'))
        
        files = request.files.getlist('file')
        if not files or files[0].filename == '':
            flash('未選擇檔案', 'error')
            return redirect(url_for('index'))

        # 檢查並儲存主要檔案和 .resS 檔案
        main_file = next((f for f in files if not f.filename.endswith('.resS')), None)
        ress_file = next((f for f in files if f.filename.endswith('.resS')), None)
        
        if not main_file:
            flash('請上傳紋理資源 .assets 檔案', 'error')
            return redirect(url_for('index'))
        
        # 儲存檔案
        main_path = os.path.join(UPLOAD_FOLDER, secure_filename(main_file.filename))
        main_file.save(main_path)
        
        if ress_file:
            ress_path = main_path + '.resS'
            ress_file.save(ress_path)
        
        # 設置檔案並提取紋理
        asset_handler.set_files(main_path)
        extracted_files = asset_handler.extract_textures()
        
        if not extracted_files:
            flash('未找到任何可提取的紋理', 'error')
            return redirect(url_for('index'))
        
        return render_template('results.html', files=extracted_files)
        
    except Exception as e:
        flash(f'處理檔案時發生錯誤: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/view/<path:filename>')
def view_file(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename))

@app.route('/replace_texture', methods=['POST'])
def handle_texture_replace():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '沒有上傳檔案'}), 400
    
    path_id = request.form.get('path_id')
    if not path_id:
        return jsonify({'success': False, 'message': '未指定 Path ID'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未選擇檔案'}), 400
    
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return jsonify({'success': False, 'message': '請選擇圖片檔案'}), 400
    
    try:
        # 儲存上傳的圖片到臨時檔案
        temp_path = os.path.join(UPLOAD_FOLDER, 'temp', secure_filename(file.filename))
        file.save(temp_path)
        
        # 替換紋理
        success, message = asset_handler.replace_texture(path_id, temp_path)
        
        # 刪除臨時檔案
        os.remove(temp_path)
        
        return jsonify({'success': success, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/download_modified', methods=['GET'])
def download_modified():
    try:
        if not asset_handler.modified_file or not os.path.exists(asset_handler.modified_file):
            return jsonify({'error': '沒有可下載的修改檔案'}), 404
        
        return send_file(
            asset_handler.modified_file,
            as_attachment=True,
            download_name=os.path.basename(asset_handler.modified_file),
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(
        host='localhost' if debug_mode else '0.0.0.0',
        port=5000 if debug_mode else 5001,
        debug=debug_mode
    )
