import os
import requests
import google.genai as genai

THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

def generate_post():
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = """
你是一位專業的Instagram文案寫手，請依照以下格式，撰寫一篇關於「今日辯題」的貼文。

格式如下：

今日辯題
[一個關於人際關係或人生選擇的辯題，讓人想停下來思考]（防劇透功能）

[第一段：描述這個議題的日常情境，讓人有共鳴，2-3句]
[第二段：提出反面思考，製造矛盾感，1-2句]
[第三段：拋出另一個角度，讓人重新思考，1-2句]

[重複辯題問題]
會 / 不會，留言告訴我

規則
- 禁止用「——」
- 禁止用「他笑著搖搖頭」「我愣住了」等AI感用語
- 語氣像在跟朋友聊天，自然口語
- 每段不超過3句
- 辯題要讓人有強烈想表態的衝動
- 標點符號使用全形
- 辯論題要貼近真實生活，讓人有感
- 辯題類型請涵蓋：感情、友情、職場、人生選擇，不要重複同一類型
- 不要超過100字
- 只輸出貼文內容，不要加任何說明、標題、編號
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text.strip()

def post_to_threads(content):
    url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    params = {
        "media_type": "TEXT",
        "text": content,
        "access_token": THREADS_ACCESS_TOKEN
    }
    res = requests.post(url, params=params)
    creation_id = res.json().get("id")
    print(f"貼文容器建立成功：{creation_id}")

    publish_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    publish_params = {
        "creation_id": creation_id,
        "access_token": THREADS_ACCESS_TOKEN
    }
    pub_res = requests.post(publish_url, params=publish_params)
    print(f"Threads 發文成功！{pub_res.json()}")
    return True

if __name__ == "__main__":
    print("正在用 Gemini 產生情感辯論題...")
    content = generate_post()
    print(f"產生內容：\n{content}\n")
    success = post_to_threads(content)
    if success:
        print("全部完成！")
