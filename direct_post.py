import os
import requests

NOTION_TOKEN = os.environ["NOTION_API_KEY"]
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
    
    # 先不加任何filter，把全部資料撈出來看看
    res = requests.post(url, headers=headers, json={})
    data = res.json()
    
    print("=== Notion 回傳原始資料 ===")
    print(data)
    print("===========================")
    
    results = data.get("results", [])
    print(f"總共找到 {len(results)} 筆資料")
    
    for r in results:
        props = r["properties"]
        print("--- 欄位內容 ---")
        print(props)
        print("----------------")
    
    return results

def main():
    get_pending_posts()

if __name__ == "__main__":
    main()
