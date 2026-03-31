import os
import requests
from notion_client import Client

# === 設定 ===
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID_3"]
THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]

notion = Client(auth=NOTION_TOKEN)

def get_ready_posts():
    response = notion.databases.query(
        database_id=NOTION_DATABASE_ID,
        filter={
            "property": "狀態",
            "status": {
                "equals": "待發"
            }
        }
    )
    return response["results"]

def post_to_threads(text):
    # Step 1: 建立 container
    url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    payload = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN
    }
    res = requests.post(url, data=payload)
    res.raise_for_status()
    creation_id = res.json()["id"]

    # Step 2: 發布
    publish_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": THREADS_ACCESS_TOKEN
    }
    pub_res = requests.post(publish_url, data=publish_payload)
    pub_res.raise_for_status()
    return pub_res.json()

def update_status(page_id, status):
    notion.pages.update(
        page_id=page_id,
        properties={
            "狀態": {
                "status": {
                    "name": status
                }
            }
        }
    )

def main():
    posts = get_ready_posts()
    if not posts:
        print("沒有待發文章")
        return

    for post in posts:
        page_id = post["id"]
        try:
            # 抓取「文字」欄位內容
            rich_text = post["properties"]["文字"]["rich_text"]
            if not rich_text:
                print(f"頁面 {page_id} 文字欄位為空，跳過")
                continue
            text = rich_text[0]["plain_text"]

            print(f"發文中：{text[:30]}...")
            post_to_threads(text)
            update_status(page_id, "已發")
            print(f"✅ 發文成功")

        except Exception as e:
            print(f"❌ 發文失敗：{e}")

if __name__ == "__main__":
    main()
