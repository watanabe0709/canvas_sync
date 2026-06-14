#!/usr/bin/env python3
import datetime
import json
import requests
import os
from dotenv import load_dotenv

# .envファイルの内容を環境変数として読み込む
load_dotenv()

# ==========================================
# 設定情報の読み込み
# ==========================================
CANVAS_DOMAIN = os.getenv("CANVAS_DOMAIN")
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

# タイムゾーンの設定（日本標準時）
JST = datetime.timezone(datetime.timedelta(hours=9))

def sync_canvas_to_notion():
    now = datetime.datetime.now(JST)
    
    # 1. 期間の計算（過去3日前 〜 7日後まで）
    past = now - datetime.timedelta(days=3)
    future = now + datetime.timedelta(days=7)

    start_date = past.isoformat()
    end_date = future.isoformat()

    # 2. Canvas APIから課題一覧を取得
    canvas_url = f"https://{CANVAS_DOMAIN}/api/v1/planner/items"
    canvas_params = {"start_date": start_date, "end_date": end_date}
    canvas_headers = {"Authorization": f"Bearer {CANVAS_TOKEN}"}

    try:
        response = requests.get(
            canvas_url, headers=canvas_headers, params=canvas_params
        )
        if response.status_code != 200:
            print(f"Canvas API エラー: {response.text}")
            return
        items = response.json()
    except Exception as e:
        print(f"Canvas通信エラー: {e}")
        return

    # 3. 各アイテムをループ処理
    for item in items:
        plannable_type = item.get("plannable_type")
        submissions = item.get("submissions", {})
        is_submitted = submissions.get("submitted") if submissions else False

        if plannable_type in ["assignment", "quiz"] and not is_submitted:
            title = item["plannable"]["title"]
            due_date = item["plannable"].get("due_at")
            course_name = item.get("context_name", "")
            item_url = item.get("html_url", "")
            canvas_id = str(item["plannable_id"])

            if not is_already_registered(canvas_id):
                create_notion_task(title, due_date, course_name, item_url, canvas_id)
                print(f"新着課題を登録しました: {title}")

def is_already_registered(canvas_id):
    """Notionに同じCanvasIDが登録されているか確認"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {
        "filter": {
            "property": "CanvasID",
            "rich_text": {"equals": canvas_id},
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        return len(result.get("results", [])) > 0
    return False

def create_notion_task(title, due_date, course_name, item_url, canvas_id):
    """Notionに新規タスクを作成（Null対応・RichText対応版）"""
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    # 基本プロパティ（期日以外）
    properties = {
        "タスク": {"title": [{"text": {"content": title}}]},
        "科目名": {"rich_text": [{"text": {"content": course_name}}]}, # SelectからRichTextに変更
        "URL": {"url": item_url},
        "CanvasID": {"rich_text": [{"text": {"content": canvas_id}}]},
        "ラベル": {
            "multi_select": [{"name": "日次"}, {"name": "課題"}]
        },
    }

    # 期日が存在し、かつ空文字でない場合のみ追加
    if due_date and isinstance(due_date, str) and due_date.strip() != "":
        properties["期日"] = {"date": {"start": due_date}}

    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": properties
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    # ログ出力
    status_code = response.status_code
    if status_code in [200, 201]:
        print(f"✅ Notion API 登録成功 (ステータス: {status_code})")
    else:
        print(f"❌ Notion API エラー (ステータス: {status_code})")
        print(f"詳細: {response.text}")

if __name__ == "__main__":
    sync_canvas_to_notion()