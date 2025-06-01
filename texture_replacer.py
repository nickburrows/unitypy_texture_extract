import UnityPy
from PIL import Image
import os
import argparse

def replace_texture(assets_path, path_id, new_texture_path, output_path):
    """
    取代 .assets 檔案中指定 Path_ID 的 Texture2D 資源
    
    Args:
        assets_path (str): 輸入的 .assets 檔案路徑
        path_id (int): 要取代的 Texture2D 的 Path_ID
        new_texture_path (str): 新紋理圖片的路徑
        output_path (str): 輸出的 .assets 檔案路徑
    """
    print(f"已載入新圖片: {new_texture_path}")
    print("重新載入資源檔案...")
    
    # 讀取 .assets 檔案
    try:
        env = UnityPy.load(assets_path)
    except Exception as e:
        raise Exception(f"載入資源檔案時發生錯誤: {str(e)}")
    
    # 讀取新的紋理圖片
    try:
        new_image = Image.open(new_texture_path)
        print(f"新圖片大小: {new_image.size}")
        new_image = new_image.convert('RGBA')
    except Exception as e:
        raise Exception(f"讀取新圖片時發生錯誤: {str(e)}")
    
    # 尋找並取代指定的 Texture2D
    texture_found = False
    for obj in env.objects:
        if obj.path_id == path_id and obj.type.name == "Texture2D":
            print(f"開始處理 Texture2D (path_id: {path_id})")
            texture_found = True
            
            try:
                # 獲取 Texture2D 物件
                texture = obj.read()
                
                # 確保圖片尺寸相符
                if hasattr(texture, 'image'):
                    original_size = texture.image.size
                    print(f"原始圖片大小: {original_size}")
                    if original_size != new_image.size:
                        print(f"調整新圖片大小為: {original_size}")
                        new_image = new_image.resize(original_size)
                
                # 儲存原始設定
                original_settings = {
                    "m_TextureFormat": texture.m_TextureFormat,
                    "m_CompleteImageSize": texture.m_CompleteImageSize,
                    "m_TextureDimension": texture.m_TextureDimension,
                    "m_TextureSettings": texture.m_TextureSettings,
                    "m_StreamData": texture.m_StreamData,
                    "m_MipMap": texture.m_MipMap,
                    "m_IsReadable": texture.m_IsReadable,
                }
                
                print("更新紋理圖片...")
                # 設定新的圖片
                texture.image = new_image
                
                # 還原原始設定
                for key, value in original_settings.items():
                    if hasattr(texture, key):
                        setattr(texture, key, value)
                
                print("儲存物件變更...")
                try:
                    # 將修改後的數據寫回
                    texture.save()
                except Exception as e:
                    print(f"使用原始格式儲存失敗，嘗試使用 RGBA32 格式: {str(e)}")
                    # 如果儲存失敗，嘗試使用預設格式
                    texture.m_TextureFormat = 4  # RGBA32 format
                    texture.save()
                
            except Exception as e:
                raise Exception(f"處理紋理時發生錯誤: {str(e)}")
            
            break
    
    if not texture_found:
        raise ValueError(f"找不到 Path_ID 為 {path_id} 的 Texture2D")
    
    # 儲存修改後的 .assets 檔案
    try:
        print("儲存已編輯的檔案，準備中...")
        if os.path.exists(output_path):
            print(f"刪除已存在的檔案: {output_path}")
            os.remove(output_path)
        
        print(f"儲存已編輯的檔案: {output_path}")
        with open(output_path, "wb") as f:
            data = env.file.save()
            f.write(data)
            print(f"檔案儲存成功，大小: {len(data)} bytes")
        
        # 如果有對應的 .resS 檔案，也要一併複製
        ress_file = assets_path + ".resS"
        if os.path.exists(ress_file):
            output_ress = output_path + ".resS"
            print(f"複製 .resS 檔案到: {output_ress}")
            import shutil
            shutil.copy2(ress_file, output_ress)
        
        # 重新載入並驗證
        print("重新載入環境進行驗證...")
        verify_env = UnityPy.load(output_path)
        for obj in verify_env.objects:
            if obj.path_id == path_id and obj.type.name == "Texture2D":
                verify_texture = obj.read()
                if hasattr(verify_texture, 'image'):
                    print(f"驗證成功：新圖片大小為 {verify_texture.image.size}")
                break
                
    except Exception as e:
        raise Exception(f"儲存檔案時發生錯誤: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="取代 Unity .assets 檔案中的 Texture2D 資源")
    parser.add_argument("assets_path", help="輸入的 .assets 檔案路徑")
    parser.add_argument("path_id", type=int, help="要取代的 Texture2D 的 Path_ID")
    parser.add_argument("new_texture_path", help="新紋理圖片的路徑")
    parser.add_argument("output_path", help="輸出的 .assets 檔案路徑")
    
    args = parser.parse_args()
    
    try:
        replace_texture(args.assets_path, args.path_id, args.new_texture_path, args.output_path)
    except Exception as e:
        print(f"錯誤: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
