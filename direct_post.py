import os
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID_3"]
THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_pending_posts():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "狀態",
            "status": {
                "equals": "待發"
            }
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    return res.json().get("results", [])

def mark_as_done(page_id):
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
    requests.patch(url, headers=headers, json=payload)

def post_to_threads(text):
    # Step 1: 建立容器
    url1 = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    res1 = requests.post(url1, params={
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN
    })
    container_id = res1.json().get("id")
    if not container_id:
        print("❌ 建立容器失敗", res1.json())
        return False

    # Step 2: 發布
    url2 = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    res2 = requests.post(url2, params={
        "creation_id": container_id,
        "access_token": THREADS_ACCESS_TOKEN
    })
    print("✅ 發布結果：", res2.json())
    return res2.status_code == 200

def main():
    posts = get_pending_posts()
    if not posts:
        print("沒有待發文章")
        return

    # 每次只發第一筆
    post = posts[0]
    page_id = post["id"]
    text = post["properties"]["文字"]["rich_text"]
    if not text:
        print("文字欄位是空的")
        return

    content = text[0]["plain_text"]
    success = post_to_threads(content)
    if success:
        mark_as_done(page_id)

if __name__ == "__main__":
    main()
