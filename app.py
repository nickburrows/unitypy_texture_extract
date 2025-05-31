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
app.secret_key = 'your-secret-key-here'  # 用於 flash 訊息

# 錯誤處理裝飾器
@app.errorhandler(Exception)
def handle_error(error):
    error_message = str(error)
    error_traceback = traceback.format_exc()
    print(f"發生錯誤: {error_message}\n{error_traceback}")
    return jsonify({
        'success': False,
        'message': f'操作失敗：{error_message}',
        'details': error_traceback if app.debug else None
    }), 500

# 檔案大小限制
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['MAX_FILE_SIZE'] = 500  # MB

# 確保所有必要的檔案夾存在
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'extracted')
MODIFIED_FOLDER = os.path.join(BASE_DIR, 'modified')  # 用於存放修改後的資源檔案

print(f"使用的檔案夾路徑:")
print(f"UPLOAD_FOLDER: {UPLOAD_FOLDER}")
print(f"OUTPUT_FOLDER: {OUTPUT_FOLDER}")
print(f"MODIFIED_FOLDER: {MODIFIED_FOLDER}")

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, MODIFIED_FOLDER]:
    try:
        os.makedirs(folder, exist_ok=True)
        os.makedirs(os.path.join(folder, 'temp'), exist_ok=True)
        print(f"成功建立檔案夾: {folder}")
    except Exception as e:
        print(f"建立檔案夾 {folder} 時發生錯誤: {e}")

# 儲存目前處理的資源檔案路徑
current_asset_file = None
current_environment = None

def extract_unity_textures(file_path):
    """提取 Unity 紋理資源"""
    global current_asset_file, current_environment
    current_asset_file = os.path.abspath(file_path)  # 確保使用絕對路徑
    extracted_files = []
    
    try:
        # 使用 UnityPy 載入 Unity 資源檔案
        current_environment = UnityPy.load(file_path)
        
        # 遍歷所有物件
        for obj in current_environment.objects:
            if obj.type.name not in ["Texture2D", "Sprite"]:
                continue
                
            try:
                # 讀取物件數據
                data = obj.read()
                name = data.name if hasattr(data, 'name') else f'{obj.type.name.lower()}_{obj.path_id}'
                
                # 提取圖像
                img = data.image
                if img is not None:
                    output_path = os.path.join(OUTPUT_FOLDER, f'{name}.png')
                    img.save(output_path)
                    
                    # 記錄提取的檔案資訊
                    extracted_files.append({
                        'name': name,
                        'type': obj.type.name,
                        'path_id': obj.path_id,
                        'path': os.path.basename(output_path)
                    })
            except Exception as e:
                print(f"處理 {obj.type.name} (path_id: {obj.path_id}) 時發生錯誤: {e}")
                continue

    except Exception as e:
        print(f"處理檔案時發生錯誤: {e}")
        return []

    return extracted_files

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

        # 檢查並儲存上傳的檔案
        main_file = None
        ress_file = None
        
        for file in files:
            if file and file.filename:  # 確保檔案存在且有檔名
                if file.filename.endswith('.resS'):
                    ress_file = file
                else:
                    main_file = file
        
        if not main_file:
            flash('請上傳紋理資源 .assets 檔案', 'error')
            return redirect(url_for('index'))
        
        # 儲存檔案
        filepath = os.path.join(UPLOAD_FOLDER, secure_filename(main_file.filename))
        filepath = os.path.abspath(filepath)  # 轉換為絕對路徑
        
        # 確保檔案夾存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 儲存主要檔案
        main_file.save(filepath)
        print(f"已儲存紋理資源: {filepath}")
        
        # 檢查檔案是否已正確儲存
        if not os.path.exists(filepath):
            raise Exception(f"檔案無法儲存到: {filepath}")
        
        if ress_file:
            ress_path = filepath + '.resS'
            ress_file.save(ress_path)
            print(f"已儲存資源檔案: {ress_path}")
            
            # 檢查 .resS 檔案是否已正確儲存
            if not os.path.exists(ress_path):
                raise Exception(f"無法儲存 .resS 檔案到: {ress_path}")

        # 提取紋理
        extracted_files = extract_unity_textures(filepath)
        if not extracted_files:
            # 嘗試獲取檔案中的資源類型資訊
            env = UnityPy.load(filepath)
            print(f"檔案讀取成功，找到的對象類型：")
            obj_types = {}
            for obj in env.objects:
                obj_type = obj.type.name
                if obj_type not in obj_types:
                    obj_types[obj_type] = 0
                obj_types[obj_type] += 1
            
            type_info = [f"{t}({c}個)" for t, c in obj_types.items()]
            flash(f'未找到任何可提取的紋理。檔案包含以下類型的資源：{", ".join(type_info)}', 'error')
            return redirect(url_for('index'))
        
        return render_template('results.html', files=extracted_files)
    
    except Exception as e:
        print(f"處理檔案時發生錯誤: {e}")
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
    
    # 確認檔案是圖片
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return jsonify({'success': False, 'message': '請選擇上傳的圖片'}), 400
    
    try:
        # 將上傳的圖片暫存到臨時檔案夾
        temp_dir = os.path.join(UPLOAD_FOLDER, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_path)
        
        # 進行圖片取代
        success, message = replace_texture(path_id, temp_path)
        
        # 刪除暫存檔案
        os.remove(temp_path)
        
        return jsonify({
            'success': success,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'檔案處理時發生錯誤: {str(e)}'
        }), 500

def replace_texture(path_id, image_path):
    """取代指定 path_id 的紋理"""
    global current_environment, current_asset_file
    
    if not current_environment or not current_asset_file:
        print("目前資源檔案狀態：")
        print(f"current_environment: {'已載入' if current_environment else '未載入'}")
        print(f"current_asset_file: {current_asset_file}")
        return False, "沒有載入的資源檔案"
    
    try:
        # 載入新的圖片
        new_image = Image.open(image_path)
        print(f"已載入新圖片: {image_path}")

        # 重新載入環境
        print("重新載入資源檔案...")
        current_environment = UnityPy.load(current_asset_file)
        
        # 尋找目標紋理
        target_obj = None
        for obj in current_environment.objects:
            if obj.path_id == int(path_id):
                target_obj = obj
                break
        
        if not target_obj:
            return False, "找不到指定的資源 ID"
        
        if target_obj.type.name not in ["Texture2D", "Sprite"]:
            return False, f"指定的資源不是紋理或精靈圖片 (類型: {target_obj.type.name})"
        
        print(f"開始處理 {target_obj.type.name} (path_id: {path_id})")
        
        # 讀取並驗證物件數據
        data = target_obj.read()
        if not hasattr(data, 'image'):
            return False, "目標物件沒有圖片資料"
        
        # 檢查並調整圖片大小
        original_size = data.image.size if data.image else None
        print(f"原始圖片大小: {original_size}")
        if original_size and (new_image.size != original_size):
            print(f"調整新圖片大小從 {new_image.size} 到 {original_size}")
            new_image = new_image.resize(original_size)
        
        # 轉換為RGB模式
        if new_image.mode != 'RGB':
            new_image = new_image.convert('RGB')
        
        # 更新圖片
        print("更新紋理圖片...")
        data.set_image(new_image)
        
        # 儲存更改
        print("儲存物件變更...")
        data.save()
        
        # 準備輸出檔案
        print("儲存已編輯的檔案，準備中...")
        output_filename = os.path.basename(current_asset_file)
        output_path = os.path.join(MODIFIED_FOLDER, output_filename)
        
        # 確保輸出檔案夾存在
        os.makedirs(MODIFIED_FOLDER, exist_ok=True)
        
        # 如果檔案已存在，先刪除它
        if os.path.exists(output_path):
            print(f"刪除已存在的檔案: {output_path}")
            os.remove(output_path)
        
        # 儲存環境到新檔案
        print(f"儲存已編輯的檔案: {output_path}")
        with open(output_path, 'wb') as f:
            f.write(current_environment.file.save())
        
        # 驗證檔案是否正確儲存
        if not os.path.exists(output_path):
            raise Exception("檔案儲存失敗")
        if os.path.getsize(output_path) == 0:
            raise Exception("儲存的檔案大小為0")
        
        print(f"檔案儲存成功，大小: {os.path.getsize(output_path)} bytes")
        
        # 複製 .resS 檔案（如果存在）
        ress_path = current_asset_file + '.resS'
        if os.path.exists(ress_path):
            ress_output_path = output_path + '.resS'
            print(f"複製 .resS 檔案到: {ress_output_path}")
            shutil.copy2(ress_path, ress_output_path)
        
        # 重新載入環境以驗證變更
        print("重新載入環境進行驗證...")
        current_environment = UnityPy.load(output_path)
        
        # 驗證變更是否成功
        for obj in current_environment.objects:
            if obj.path_id == int(path_id):
                verify_data = obj.read()
                if verify_data.image:
                    print(f"驗證成功：新圖片大小為 {verify_data.image.size}")
                    return True, "已取代紋理圖片"
                else:
                    raise Exception("驗證失敗：更新後的圖片為空")
        
        raise Exception("驗證失敗：找不到更新後的物件")
        
    except Exception as e:
        error_message = str(e)
        print(f"圖片取代時發生錯誤: {error_message}")
        # 如果錯誤訊息中包含堆疊追蹤，也將其輸出
        if hasattr(e, '__traceback__'):
            import traceback
            traceback.print_exc()
        return False, f"圖片取代時發生錯誤: {error_message}"

@app.route('/download_modified', methods=['GET'])
def download_modified():
    """下載修改後的資源檔案"""
    global current_asset_file
    if not current_asset_file:
        return jsonify({'error': '沒有修改過的資源檔案'}), 404
    
    modified_path = os.path.join(MODIFIED_FOLDER, Path(current_asset_file).name)
    
    if not os.path.exists(modified_path):
        # 檢查檔案是否存在，如果不存在則提供更詳細的錯誤信息
        print(f"嘗試訪問的檔案路徑: {modified_path}")
        print(f"目前的 current_asset_file: {current_asset_file}")
        
        # 列出 modified 檔案夾下的所有檔案
        files = os.listdir(MODIFIED_FOLDER)
        print(f"modified 檔案夾中的檔案: {files}")
        
        return jsonify({
            'error': '找不到修改後的資源檔案',
            'details': f'預期路徑: {modified_path}'
        }), 404
    
    return send_file(modified_path,
                    as_attachment=True,
                    download_name=Path(modified_path).name)

def cleanup_temp_files():
    """清理臨時檔案"""
    temp_folders = [
        os.path.join(UPLOAD_FOLDER, 'temp'),
        os.path.join(OUTPUT_FOLDER, 'temp'),
        os.path.join(MODIFIED_FOLDER, 'temp')
    ]
    
    for folder in temp_folders:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                print(f"清理臨時檔案時發生錯誤: {e}")

@app.before_request
def before_request():
    """在每個請求之前執行清理"""
    if request.endpoint != 'static':
        cleanup_temp_files()

if __name__ == '__main__':
    # 啟動時清理臨時檔案
    cleanup_temp_files()
    app.run(debug=True)
