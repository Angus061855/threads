import os
import requests
import datetime
import time
from google import genai

# ── 環境變數 ──────────────────────────────────────────
NOTION_TOKEN       = os.environ["NOTION_API_KEY"]
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
            title_list = props.get("辯題", {}).get("title", [])
            if title_list:
                used.append(title_list[0]["plain_text"])
        if not res.get("has_more"):
            break
        payload["start_cursor"] = res["next_cursor"]
    return used

# ── 2. 用 Gemini 產生新辯題與貼文內容 ────────────────
def generate_post(used_topics):
    client = genai.Client(api_key=GEMINI_API_KEY)

    recent_topics = used_topics[-30:] if len(used_topics) > 30 else used_topics
    used_str = "\n".join(f"- {t}" for t in recent_topics) if recent_topics else "（目前沒有已用辯題）"

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
「[辯題內容]」

[第一句，不超過20字]

[第二句，不超過20字]

（彈性2到4句，視內容決定）

規則：
- 每一句可以是完整的一個想法，不強制每行很短，但不要超過20個字
- 同一個意思不強制換行
- 句子要有流暢感，像在說話，不要切太碎
- 辯題與下面段落之間空一行
- 禁止用「——」
- 禁止用「他笑著搖搖頭」「我愣住了」等AI感用語
- 語氣像在跟朋友聊天，自然口語
- 辯題要讓人有強烈想表態的衝動
- 標點符號使用全形
- 只輸出貼文內容，不要加任何說明、標題、編號
"""

    response = client.models.generate_content(
        model="gemma-4-31b-it",
        contents=prompt,
    )
    return response.text.strip()

# ── 3. 從貼文內容擷取辯題文字 ────────────────────────
def extract_topic(post_text):
    lines = post_text.strip().split("\n")
    for i, line in enumerate(lines):
        if "今日辯題" in line:
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    return lines[j].strip()
    return lines[1].strip() if len(lines) > 1 else "未知辯題"

# ── 3b. 把貼文拆成兩段 ───────────────────────────────
def split_post(post_text):
    lines = post_text.strip().split("\n")

    topic_end_idx = 0
    for i, line in enumerate(lines):
        if "今日辯題" in line:
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    topic_end_idx = j
                    break
            break

    part1 = "\n".join(lines[:topic_end_idx + 1]).strip()
    part2 = "\n".join(lines[topic_end_idx + 1:]).strip()

    return part1, part2

# ── 4. 發文到 Threads（支援留言回覆）────────────────
def post_to_threads(text, reply_to_id=None):
    create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    data = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_TOKEN,
    }
    if reply_to_id:
        data["reply_to_id"] = reply_to_id

    res = requests.post(create_url, data=data).json()
    creation_id = res.get("id")
    if not creation_id:
        raise Exception(f"建立 container 失敗：{res}")

    publish_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    pub_res = requests.post(publish_url, data={
        "creation_id": creation_id,
        "access_token": THREADS_TOKEN,
    }).json()
    return pub_res

# ── 5. 把新辯題記錄進 Notion ─────────────────────────
def save_to_notion(topic, post_text, post_id):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "辯題": {
                "title": [{"text": {"content": topic}}]
            },
            "貼文內容": {
                "rich_text": [{"text": {"content": post_text}}]
            },
            "貼文 ID": {
                "rich_text": [{"text": {"content": post_id}}]
            },
            "發文時間": {
                "date": {"start": now}
            }
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    print("Notion 回應狀態：", res.status_code)
    print("Notion 回應內容：", res.json())

# ── 6. 發送 Telegram 通知 ─────────────────────────────
def send_telegram(message):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    res = requests.post(url, data={"chat_id": chat_id, "text": message})
    print("Telegram 回應：", res.status_code, res.json())

# ── 主程式 ────────────────────────────────────────────
if __name__ == "__main__":
    try:
        print("📥 撈取已用辯題...")
        used_topics = get_used_topics()
        print(f"共 {len(used_topics)} 個已用辯題")

        print("✍️ 產生新貼文...")
        post_text = generate_post(used_topics)
        print("貼文內容：\n", post_text)

        part1, part2 = split_post(post_text)
        print("第一則：\n", part1)
        print("留言：\n", part2)

        print("🚀 發文到 Threads（貼文：辯題）...")
        result = post_to_threads(part1)
        print("貼文發文結果：", result)

        post_id = result.get("id", "")

        if part2 and post_id:
            time.sleep(2)
            print("💬 發留言到 Threads...")
            result2 = post_to_threads(part2, reply_to_id=post_id)
            print("留言發文結果：", result2)

        topic = extract_topic(post_text)
        print("📝 記錄辯題到 Notion：", topic)
        save_to_notion(topic, post_text, post_id)

        print("✅ 完成！")
        send_telegram(f"✅ angus 辯題貼文發送完成！\n今天發了：{topic}")

    except Exception as e:
        error_msg = f"❌ angus 辯題貼文失敗！\n錯誤原因：{str(e)}"
        print(error_msg)
        send_telegram(error_msg)
        raise
