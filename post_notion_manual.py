import os
import requests
import time
import re

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_DATABASE_ID_2 = os.environ["NOTION_DATABASE_ID_2"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
THREADS_USER_ID = os.environ["THREADS_USER_ID"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def get_first_pending_post():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID_2}/query"
    payload = {
        "filter": {
            "property": "狀態",
            "status": {
                "equals": "待發"
            }
        },
        "page_size": 1
    }
    res = requests.post(url, headers=NOTION_HEADERS, json=payload)
    results = res.json().get("results", [])
    if not results:
        print("沒有待發文章")
        return None
    return results[0]

def get_page_content(page):
    page_id = page["id"]

    title = page["properties"]["標題"]["title"]
    title_text = title[0]["plain_text"] if title else ""

    content_prop = page["properties"].get("內容", {})
    rich_text = content_prop.get("rich_text", [])
    content_text = rich_text[0]["plain_text"] if rich_text else ""

    if title_text and content_text:
        full_text = f"{title_text}\n\n{content_text}"
    elif title_text:
        full_text = title_text
    else:
        full_text = content_text

    segments = re.split(r'§\d+', full_text)
    segments = [s.strip() for s in segments if s.strip()]

    return page_id, segments, title_text

def create_container(text, reply_to_id=None):
    url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    payload = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN
    }
    if reply_to_id:
        payload["reply_to_id"] = reply_to_id
    res = requests.post(url, data=payload)
    print(f"create_container 回應：{res.status_code} / {res.json()}")
    container_id = res.json().get("id")
    return container_id

def publish_container(container_id):
    url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    payload = {
        "creation_id": container_id,
        "access_token": THREADS_ACCESS_TOKEN
    }
    res = requests.post(url, data=payload)
    print(f"publish_container 回應：{res.status_code} / {res.json()}")
    return res.json().get("id")

def post_thread_series(segments, title_text):
    previous_post_id = None

    for i, text in enumerate(segments):
        print(f"發第 {i+1} 段...")

        container_id = create_container(text, reply_to_id=previous_post_id)
        if not container_id:
            print(f"第 {i+1} 段建立 container 失敗")
            send_telegram(f"❌ 串文發布失敗！\n標題：{title_text}\n原因：第 {i+1} 段建立 container 失敗")
            return False

        time.sleep(5)

        post_id = publish_container(container_id)
        if not post_id:
            print(f"第 {i+1} 段發布失敗")
            send_telegram(f"❌ 串文發布失敗！\n標題：{title_text}\n原因：第 {i+1} 段發布失敗")
            return False

        print(f"第 {i+1} 段發布成功，post_id：{post_id}")
        previous_post_id = post_id

        if i < len(segments) - 1:
            time.sleep(3)

    return True

def mark_as_posted(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "狀態": {
                "status": {
                    "name": "已發"
                }
            }
        }
    }
    res = requests.patch(url, headers=NOTION_HEADERS, json=payload)
    print("更新 Notion 狀態：", res.status_code)

if __name__ == "__main__":
    page = get_first_pending_post()
    if page:
        page_id, segments, title_text = get_page_content(page)
        print(f"共 {len(segments)} 段，準備發串文...")
        success = post_thread_series(segments, title_text)
        if success:
            mark_as_posted(page_id)
            send_telegram(f"✅ 串文發布成功！\n標題：{title_text}\n共 {len(segments)} 段")
