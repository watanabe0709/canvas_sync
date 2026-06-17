#!/usr/bin/env python3
import os
import datetime
import requests
import re
from dotenv import load_dotenv
from icalendar import Calendar

# 環境変数の読み込み
load_dotenv()
CANVAS_ICAL_URL = os.getenv("CANVAS_ICAL_URL")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

JST = datetime.timezone(datetime.timedelta(hours=9))

def sync_ical_to_notion():
    print("カレンダーデータの取得を開始します...")
    
    try:
        response = requests.get(CANVAS_ICAL_URL)
        if response.status_code != 200:
            print(f"❌ カレンダーの取得に失敗しました。ステータス: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 通信エラー: {e}")
        return

    cal = Calendar.from_ical(response.content)

    now = datetime.datetime.now(JST)
    
    # 🌟修正点①：「過去3日」をやめて、「今現在」から7日後までにする
    past_limit = now 
    future_limit = now + datetime.timedelta(days=7)

    for event in cal.walk('vevent'):
        title_full = str(event.get('summary', '無題'))
        uid_raw = str(event.get('uid', ''))
        url = str(event.get('url', ''))

        # 🌟修正点②：UIDから数字だけを抽出してAPI時代のID形式に合わせる
        # (例: "event-assignment-123456" -> "123456")
        match = re.search(r'\d+', uid_raw)
        uid = match.group() if match else uid_raw

        dtstart = event.get('dtstart')
        due_date_str = ""
        
        if dtstart:
            dt = dtstart.dt
            if type(dt) is datetime.date:
                dt = datetime.datetime.combine(dt, datetime.time.min, tzinfo=JST)
            elif dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc).astimezone(JST)
            else:
                dt = dt.astimezone(JST)
            
            # 現在時刻より未来、かつ7日以内のものだけを処理
            if past_limit <= dt <= future_limit:
                due_date_str = dt.isoformat()
            else:
                continue 
        
        course_name = ""
        title = title_full
        if "[" in title_full and title_full.endswith("]"):
            parts = title_full.rsplit("[", 1)
            title = parts[0].strip()
            course_name = parts[1].replace("]", "").strip()

        if not is_already_registered(uid):
            create_notion_task(title, due_date_str, course_name, url, uid)
            print(f"✨ 新着課題を登録しました: {title}")


def is_already_registered(canvas_id):
    api_url = f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query"
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
    response = requests.post(api_url, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        return len(result.get("results", [])) > 0
    return False

def create_notion_task(title, due_date, course_name, item_url, canvas_id):
    api_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    properties = {
        "タスク": {"title": [{"text": {"content": title}}]},
        "科目名": {"rich_text": [{"text": {"content": course_name}}]},
        "URL": {"url": item_url if item_url else None},
        "CanvasID": {"rich_text": [{"text": {"content": canvas_id}}]},
        "ラベル": {
            "multi_select": [{"name": "日次"}, {"name": "課題"}]
        },
    }

    if due_date and isinstance(due_date, str) and due_date.strip() != "":
        properties["期日"] = {"date": {"start": due_date}}

    payload = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": properties
    }
    
    response = requests.post(api_url, headers=headers, json=payload)
    status_code = response.status_code
    if status_code in [200, 201]:
        result_data = response.json()
        print(f"✅ Notion API 登録成功 | URL: {result_data.get('url')}")
    else:
        print(f"❌ Notion API エラー (ステータス: {status_code})")
        print(f"詳細: {response.text}")

if __name__ == "__main__":
    sync_ical_to_notion()