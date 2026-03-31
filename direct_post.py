import os
import requests

NOTION_TOKEN = os.environ["NOTION_API_KEY"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_pending_posts():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(url, headers=headers, json={
        "filter": {
            "property": "狀態",
            "status": {
                "equals": "待發"
            }
        }
    })
    data = res.json()
    results = data.get("results", [])
    print(f"找到 {len(results)} 筆待發文章")
    return results

def post_to_threads(text):
    # Step 1：建立貼文容器
    create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    res = requests.post(create_url, params={
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN
    })
    data = res.json()
    print("建立容器回傳：", data)
    
    creation_id = data.get("id")
    if not creation_id:
        print("❌ 建立容器失敗")
        return False

    # Step 2：發布貼文
    publish_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    res = requests.post(publish_url, params={
        "creation_id": creation_id,
        "access_token": THREADS_ACCESS_TOKEN
    })
    print("發布回傳：", res.json())
    return True

def update_status(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    res = requests.patch(url, headers=headers, json={
        "properties": {
            "狀態": {
                "status": {
                    "name": "已發"
                }
            }
        }
    })
    print("更新狀態回傳：", res.json())

def main():
    posts = get_pending_posts()
    
    if not posts:
        print("沒有待發文章，結束")
        return
    
    # 只發第一篇
    post = posts[0]
    page_id = post["id"]
    
    # 取得文字內容
    rich_text = post["properties"]["文字"]["rich_text"]
    if not rich_text:
        print("❌ 文字欄位是空的，跳過")
        return
    
    text = rich_text[0]["plain_text"]
    print(f"準備發文：{text}")
    
    # 發文到 Threads
    success = post_to_threads(text)
    
    # 發文成功後更新 Notion 狀態
    if success:
        update_status(page_id)
        print("✅ 發文成功，狀態已更新為已發")

if __name__ == "__main__":
    main()
