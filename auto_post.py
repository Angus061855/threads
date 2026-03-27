import os
import requests
import google.generativeai as genai

# ── 環境變數 ──────────────────────────────────────────
NOTION_TOKEN       = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
GEMINI_API_KEY     = os.environ["GEMINI_API_KEY"]
THREADS_USER_ID    = os.environ["THREADS_USER_ID"]
THREADS_TOKEN      = os.environ["THREADS_ACCESS_TOKEN"]

# ── 1. 從 Notion 撈所有已發過的辯題 ──────────────────
def get_used_topics():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    used = []
    payload = {}
    while True:
        res = requests.post(url, headers=headers, json=payload).json()
        for page in res.get("results", []):
            props = page.get("properties", {})
            # 假設 Notion 欄位名稱是「辯題」
            title_list = props.get("辯題", {}).get("title", [])
            if title_list:
                used.append(title_list[0]["plain_text"])
        if not res.get("has_more"):
            break
        payload["start_cursor"] = res["next_cursor"]
    return used

# ── 2. 用 Gemini 產生新辯題與貼文內容 ────────────────
def generate_post(used_topics):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    used_str = "\n".join(f"- {t}" for t in used_topics)

    prompt = f"""
你是一位擅長寫感情辯題貼文的文案寫手。

以下是已經用過的辯題，【全部禁止重複】：
{used_str}

參考風格（只參考語感，不能重複）：
- 暗戀被轉為明戀時，應該要繼續還是放棄？
- 喜歡和愛的區別是什麼？
- 愛使人自由還是不自由？

請產生一個全新的感情辯題，並照以下格式輸出貼文內容：

「今日辯題」
[辯題]

[第一句，不超過20字]
[第二句，不超過20字]
（彈性2到4句，視內容決定）

規則：
- 每一句獨立一行，每行不超過20個字
- 段落之間空一行
- 禁止用「——」
- 禁止用「他笑著搖搖頭」「我愣住了」等AI感用語
- 語氣像在跟朋友聊天，自然口語
- 辯題要讓人有強烈想表態的衝動
- 標點符號使用全形
- 只輸出貼文內容，不要加任何說明、標題、編號
"""

    response = model.generate_content(prompt)
    return response.text.strip()

# ── 3. 從貼文內容擷取辯題文字 ────────────────────────
def extract_topic(post_text):
    lines = post_text.strip().split("\n")
    # 第二行是辯題
    for i, line in enumerate(lines):
        if "今日辯題" in line:
            # 找下一個非空行
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    return lines[j].strip()
    return lines[1].strip() if len(lines) > 1 else "未知辯題"

# ── 4. 發文到 Threads ────────────────────────────────
def post_to_threads(text):
    # Step 1：建立 container
    create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    res = requests.post(create_url, data={
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_TOKEN,
    }).json()
    creation_id = res.get("id")
    if not creation_id:
        raise Exception(f"建立 container 失敗：{res}")

    # Step 2：發佈
    publish_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    pub_res = requests.post(publish_url, data={
        "creation_id": creation_id,
        "access_token": THREADS_TOKEN,
    }).json()
    return pub_res

# ── 5. 把新辯題記錄進 Notion ─────────────────────────
def save_to_notion(topic):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "辯題": {
                "title": [{"text": {"content": topic}}]
            }
        }
    }
    requests.post(url, headers=headers, json=payload)

# ── 主程式 ────────────────────────────────────────────
if __name__ == "__main__":
    print("📥 撈取已用辯題...")
    used_topics = get_used_topics()
    print(f"共 {len(used_topics)} 個已用辯題")

    print("✍️ 產生新貼文...")
    post_text = generate_post(used_topics)
    print("貼文內容：\n", post_text)

    print("🚀 發文到 Threads...")
    result = post_to_threads(post_text)
    print("發文結果：", result)

    topic = extract_topic(post_text)
    print("📝 記錄辯題到 Notion：", topic)
    save_to_notion(topic)

    print("✅ 完成！")
