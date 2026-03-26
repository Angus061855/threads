import os
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]

def get_pending_post():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    body = {
        "filter": {
            "property": "狀態",
            "select": {
                "equals": "待發"
            }
        },
        "page_size": 1
    }
    res = requests.post(url, headers=headers, json=body)
    results = res.json().get("results", [])
    if not results:
        print("沒有待發文章")
        return None
    page = results[0]
    page_id = page["id"]
    content = page["properties"]["內容"]["rich_text"][0]["plain_text"]
    return page_id, content

def post_to_threads(content):
    # Step 1: 建立貼文容器
    url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    params = {
        "media_type": "TEXT",
        "text": content,
        "access_token": THREADS_ACCESS_TOKEN
    }
    res = requests.post(url, params=params)
    creation_id = res.json().get("id")
    print(f"📦 貼文容器建立成功：{creation_id}")

    # Step 2: 發布
    publish_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    publish_params = {
        "creation_id": creation_id,
        "access_token": THREADS_ACCESS_TOKEN
    }
    pub_res = requests.post(publish_url, params=publish_params)
    print(f"✅ Threads 發文成功！{pub_res.json()}")
    return True

def update_notion_status(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    body = {
        "properties": {
            "狀態": {
                "select": {
                    "name": "已發"
                }
            }
        }
    }
    requests.patch(url, headers=headers, json=body)
    print("✅ Notion 狀態已更新為「已發」")

if __name__ == "__main__":
    print("🔍 正在從 Notion 取得待發題目...")
    result = get_pending_post()
    if result:
        page_id, content = result
        print(f"📝 準備發文：{content[:30]}...")
        success = post_to_threads(content)
        if success:
            update_notion_status(page_id)
