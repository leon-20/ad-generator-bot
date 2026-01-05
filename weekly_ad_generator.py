import os
import datetime
import json
import base64
from dataclasses import dataclass
from typing import List, Dict, Optional
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- 設定 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here")
NANOBABANA_API_KEY = os.getenv("NANOBABANA_API_KEY", "your_nanobabana_api_key_here")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID") 

@dataclass
class AdProject:
    product_name: str
    target: str
    appeal: str
    color: str
    taste: str

class GeminiClient:
    """Gemini テキスト生成クライアント（モック）"""
    def generate_ad_copy(self, project: AdProject) -> Dict[str, str]:
        print(f"[Gemini] {project.product_name} のコピーを生成中...")
        return {
            "キャッチコピー": f"{project.product_name}で、うるおい習慣。",
            "サブコピー": f"{project.target}へ送る、内側からのケア",
            "画像構成": f"{project.color}を背景に、{project.taste}な雰囲気で商品を配置。光の反射でハリ感を演出。",
            "prompt": f"Professional advertisement banner for {project.product_name}, {project.color} theme, {project.taste} style, high quality, soft lighting, product centerpiece."
        }

class NanobabanaClient:
    """Nanobabana Pro 画像生成クライアント（モック）"""
    def generate_image(self, prompt: str) -> bytes:
        print(f"[Nanobabana Pro] 生成プロンプト: '{prompt}'...")
        # 本番ではここで画像生成APIを叩き、バイトデータを取得します
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (800, 400), color=(240, 240, 240))
            d = ImageDraw.Draw(img)
            d.text((20, 20), "Nanobabana Pro Output (Cloud Run)", fill=(50, 50, 50))
            d.text((20, 50), f"Prompt: {prompt[:60]}...", fill=(50, 50, 50))
            
            output_buffer = io.BytesIO()
            img.save(output_buffer, format='PNG')
            return output_buffer.getvalue()
        except ImportError:
            return b"Placeholder image content"

class DriveManager:
    """Google Drive API マネージャー"""
    def __init__(self):
        self.service = None
        try:
            # google.auth.default() が自動的に認証情報を探します:
            # 1. Workload Identity (GitHub Actions)
            # 2. 環境変数 GOOGLE_APPLICATION_CREDENTIALS
            # 3. gcloud auth application-default login (ローカル)
            creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/drive'])
            self.service = build('drive', 'v3', credentials=creds)
            print("[Drive] 認証に成功しました。")
        except Exception as e:
            print(f"[Drive] 認証に失敗したか、認証情報が見つかりません: {e}")
            print("[Drive] Dry-run（テスト）モードで実行します。")

    def get_weekly_folder_id(self, parent_id: Optional[str]) -> Optional[str]:
        """親フォルダIDをそのまま返す（サブフォルダは作成しない）"""
        if not self.service:
            print(f"[Drive] Dry-run: 親フォルダ {parent_id} を使用します")
            return "dry-run-folder-id"
        
        # サブフォルダを作成せず、親フォルダIDをそのまま返す
        print(f"[Drive] フォルダID {parent_id} を使用します")
        return parent_id

    def save_image(self, image_data: bytes, filename: str, folder_id: str):
        """画像をGoogle Driveにアップロードします"""
        if not self.service:
            print(f"[Drive] Dry-run: {filename} をフォルダ {folder_id} にアップロードします")
            # ローカル実行時の確認用
            if folder_id == "dry-run-folder-id":
                with open(filename, 'wb') as f:
                    f.write(image_data)
                print(f"[Local] キーがないためローカルに保存しました: {filename}")
            return

        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(io.BytesIO(image_data), mimetype='image/png', resumable=True)
        file = self.service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id',
            supportsAllDrives=True
        ).execute()
        print(f"[Drive] ファイルをアップロードしました: {filename} (ID: {file.get('id')})")

    def save_log(self, log_data: List[Dict], folder_id: str):
        """実行ログを保存します"""
        if not self.service:
            print(f"[Drive] Dry-run: ログをフォルダ {folder_id} に保存します")
            return

        # 簡易実装: 毎回タイムスタンプ付きの新しいログファイルを作成します
        log_filename = f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        file_metadata = {
            'name': log_filename,
            'parents': [folder_id]
        }
        
        # ログデータをバイト列に変換
        log_bytes = json.dumps(log_data, indent=2, ensure_ascii=False).encode('utf-8')
        media = MediaIoBaseUpload(io.BytesIO(log_bytes), mimetype='application/json')
        
        self.service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id',
            supportsAllDrives=True
        ).execute()
        print(f"[Drive] 実行ログを保存しました: {log_filename}")

def job():
    print(f"\n[{datetime.datetime.now()}] 週間広告バナー生成ジョブを開始します (GitHub Actions Mode)...")
    
    projects = [
        AdProject(
            product_name="コラーゲンゼリー",
            target="30代女性",
            appeal="肌のハリ、乾燥対策",
            color="淡いピンクと白",
            taste="ナチュラル・清潔感"
        )
    ]

    gemini = GeminiClient()
    nanobabana = NanobabanaClient()
    drive = DriveManager()

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    folder_id = drive.get_weekly_folder_id(DRIVE_FOLDER_ID)
    
    job_logs = []

    for project in projects:
        print(f"--- 処理中: {project.product_name} ---")
        
        # Step 2: コピーとプロンプトの生成
        content = gemini.generate_ad_copy(project)
        
        # Step 3: 画像生成
        image_data = nanobabana.generate_image(content['prompt'])
        image_filename = f"{project.product_name}_{today_str}.png"
        
        # Step 4: アップロード
        drive.save_image(image_data, image_filename, folder_id)
        
        job_logs.append({
            "date": today_str,
            "project": project.product_name,
            "content": content,
            "filename": image_filename
        })

    # Step 5: ログ保存
    drive.save_log(job_logs, folder_id)
    print("=== ジョブが完了しました ===")

if __name__ == "__main__":
    job()
