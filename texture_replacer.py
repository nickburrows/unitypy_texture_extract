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
    # 讀取 .assets 檔案
    env = UnityPy.load(assets_path)
    
    # 讀取新的紋理圖片
    new_image = Image.open(new_texture_path)
    
    # 尋找並取代指定的 Texture2D
    texture_found = False
    for obj in env.objects:
        if obj.path_id == path_id and obj.type.name == "Texture2D":
            texture_found = True
            # 獲取 Texture2D 物件
            texture = obj.read()
            
            # 儲存原始設定
            original_format = texture.m_TextureFormat
            original_settings = {
                "m_CompleteImageSize": texture.m_CompleteImageSize,
                "m_TextureDimension": texture.m_TextureDimension,
                "m_TextureSettings": texture.m_TextureSettings,
                "m_StreamData": texture.m_StreamData,
                "m_MipMap": texture.m_MipMap,
                "m_IsReadable": texture.m_IsReadable,
            }
            
            # 取代圖片數據
            texture.m_TextureFormat = original_format
            texture.image = new_image
            
            # 還原原始設定
            for key, value in original_settings.items():
                setattr(texture, key, value)
            
            # 將修改後的數據寫回
            texture.save()
            break
    
    if not texture_found:
        raise ValueError(f"找不到 Path_ID 為 {path_id} 的 Texture2D")
    
    # 儲存修改後的 .assets 檔案
    with open(output_path, "wb") as f:
        f.write(env.file.save())
    
    print(f"成功取代紋理並儲存至 {output_path}")

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
