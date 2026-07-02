#!/usr/bin/env python3
import datetime
import os
from pathlib import Path
import re

import requests
from dotenv import load_dotenv
from icalendar import Calendar


load_dotenv()

CANVAS_ICAL_URL = os.getenv("CANVAS_ICAL_URL")
OBSIDIAN_VAULT_PATH = Path(
    os.getenv(
        "OBSIDIAN_VAULT_PATH",
        "/Users/zumak/Library/Mobile Documents/iCloud~md~obsidian/Documents/Nexus",
    )
)
OBSIDIAN_TASK_FOLDER = os.getenv("OBSIDIAN_TASK_FOLDER", "task/データベース/タスク")

JST = datetime.timezone(datetime.timedelta(hours=9))


def sync_ical_to_obsidian():
    if not CANVAS_ICAL_URL:
        print("CANVAS_ICAL_URL が設定されていません。")
        return

    task_folder = OBSIDIAN_VAULT_PATH / OBSIDIAN_TASK_FOLDER
    task_folder.mkdir(parents=True, exist_ok=True)

    print("カレンダーデータの取得を開始します...")

    try:
        response = requests.get(CANVAS_ICAL_URL, timeout=30)
        if response.status_code != 200:
            print(f"カレンダーの取得に失敗しました。ステータス: {response.status_code}")
            return
    except Exception as error:
        print(f"通信エラー: {error}")
        return

    cal = Calendar.from_ical(response.content)
    now = datetime.datetime.now(JST)
    future_limit = now + datetime.timedelta(days=7)

    created_count = 0
    skipped_count = 0

    for event in cal.walk("vevent"):
        title_full = str(event.get("summary", "無題"))
        uid_raw = str(event.get("uid", ""))
        url = str(event.get("url", ""))

        match = re.search(r"\d+", uid_raw)
        canvas_id = match.group() if match else uid_raw

        dtstart = event.get("dtstart")
        if not dtstart:
            continue

        due_at = to_jst_datetime(dtstart.dt)
        if not due_at or not (now <= due_at <= future_limit):
            continue

        title, course_name = split_canvas_title(title_full)

        if is_already_registered(task_folder, canvas_id):
            skipped_count += 1
            continue

        create_obsidian_task(task_folder, title, due_at, course_name, url, canvas_id)
        created_count += 1
        print(f"新着課題を登録しました: {title}")

    print(f"同期完了: 新規 {created_count} 件 / スキップ {skipped_count} 件")


def to_jst_datetime(value):
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc).astimezone(JST)
        return value.astimezone(JST)

    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min, tzinfo=JST)

    return None


def split_canvas_title(title_full):
    title = title_full
    course_name = ""

    if "[" in title_full and title_full.endswith("]"):
        parts = title_full.rsplit("[", 1)
        title = parts[0].strip()
        course_name = parts[1].replace("]", "").strip()

    return title, course_name


def is_already_registered(task_folder, canvas_id):
    if not canvas_id:
        return False

    pattern = re.compile(r"^CanvasID:\s*[\"']?" + re.escape(canvas_id) + r"[\"']?\s*$")
    for path in task_folder.glob("*.md"):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if pattern.match(line.strip()):
                    return True
        except UnicodeDecodeError:
            continue

    return False


def create_obsidian_task(task_folder, title, due_at, course_name, item_url, canvas_id):
    now = datetime.datetime.now(JST).replace(microsecond=0).isoformat()
    due_date = due_at.replace(microsecond=0).isoformat()
    path = unique_task_path(task_folder, sanitize_file_name(title))

    content = (
        "---\n"
        'base: "[[タスク.base]]"\n'
        "完了: false\n"
        f"CanvasID: {yaml_string(canvas_id)}\n"
        f"URL: {yaml_string(item_url)}\n"
        '優先度: "中"\n'
        f"期日: {due_date}\n"
        "ラベル:\n"
        '  - "日次"\n'
        '  - "課題"\n'
        f"作成日時: {now}\n"
        f"説明: {yaml_string('')}\n"
        f"科目名: {yaml_string(course_name)}\n"
        f"更新日時: {now}\n"
        "---\n\n"
        f"# {title}\n\n"
        "## 内容\n\n"
        "Canvas LMS から自動登録された課題です。\n\n"
        "## 提出・リンク\n\n"
        f"{item_url}\n"
    )

    path.write_text(content, encoding="utf-8")


def unique_task_path(task_folder, base_name):
    if not base_name:
        base_name = "Canvas 課題"

    path = task_folder / f"{base_name}.md"
    index = 1
    while path.exists():
        path = task_folder / f"{base_name} {index}.md"
        index += 1

    return path


def sanitize_file_name(value):
    return (
        str(value)
        .replace("/", " ")
        .replace("\\", " ")
        .replace(":", " ")
        .replace("*", " ")
        .replace("?", " ")
        .replace('"', " ")
        .replace("<", " ")
        .replace(">", " ")
        .replace("|", " ")
        .replace("#", " ")
        .replace("^", " ")
        .replace("[", " ")
        .replace("]", " ")
        .strip()[:120]
    )


def yaml_string(value):
    text = "" if value is None else str(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


if __name__ == "__main__":
    sync_ical_to_obsidian()
