import os
import sys


venv_base = os.path.dirname(os.path.abspath(__file__))
proj_path = os.path.join(venv_base, 'venv', 'Lib', 'site-packages', 'rasterio', 'proj_data')

if os.path.exists(proj_path):
    os.environ['PROJ_LIB'] = proj_path
    
    gdal_path = os.path.join(venv_base, 'venv', 'Lib', 'site-packages', 'rasterio', 'gdal_data')
    if os.path.exists(gdal_path):
        os.environ['GDAL_DATA'] = gdal_path


import cv2
import rasterio
import geojson
import numpy as np
from ultralytics import YOLO
from rasterio.transform import xy
from rasterio.warp import transform as warp_transform


MODEL_PATH = "yolov8n.pt" 
IMAGE_PATH = "citra_satelit.tif"  
OUTPUT_JSON = "hasil_deteksi.json"
TILE_SIZE = 640  
OVERLAP = 100    

def run_tiled_detection():
    
    model = YOLO(MODEL_PATH)
    
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: File {IMAGE_PATH} tidak ditemukan!")
        return

    
    with rasterio.open(IMAGE_PATH) as src:
        transform = src.transform
        crs = src.crs 
        
       
        if src.count >= 3:
            img = src.read([1, 2, 3]).transpose(1, 2, 0)
        else:
            band1 = src.read(1)
            img = np.stack([band1, band1, band1], axis=-1)
        
        h, w, _ = img.shape

    all_features = []
    print(f"Sistem Koordinat Terdeteksi: {crs}")
    print("Memulai deteksi... Mohon tunggu sebentar.")

  
    for y in range(0, h, TILE_SIZE - OVERLAP):
        for x in range(0, w, TILE_SIZE - OVERLAP):
            tile = img[y:y+TILE_SIZE, x:x+TILE_SIZE]
            if tile.shape[0] < 100 or tile.shape[1] < 100: continue
                
           
            if tile.max() > 255 or tile.dtype != np.uint8:
                tile = cv2.normalize(tile, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

       
            results = model.predict(tile, conf=0.3, verbose=False)
            
            for r in results:
                boxes = r.boxes.cpu().numpy()
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    global_px = x + (x1 + x2) / 2
                    global_py = y + (y1 + y2) / 2
                    
                    
                    mx, my = xy(transform, global_py, global_px)
                    
                   
                    converted = warp_transform(crs, 'EPSG:4326', [mx], [my])
                    lon = converted[0][0]
                    lat = converted[1][0]
                    
                  
                    feat = geojson.Feature(
                        geometry=geojson.Point((lon, lat)),
                        properties={
                            "nama": f"AI: {model.names[int(box.cls[0])]}",
                            "confidence": f"{float(box.conf[0]):.2f}",
                            "type": "ai_detected"
                        }
                    )
                    all_features.append(feat)

   
    with open(OUTPUT_JSON, 'w') as f:
        geojson.dump(geojson.FeatureCollection(all_features), f)
    
    print(f"Berhasil! {len(all_features)} objek ditemukan dan dikonversi ke derajat.")
    print(f"Hasil disimpan di: {OUTPUT_JSON}")

if __name__ == "__main__":
    run_tiled_detection()