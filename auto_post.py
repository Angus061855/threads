import os
import requests
import google.genai as genai

THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

def generate_post():
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = """
你是一位情感類 Threads 文案寫手。
請產生一篇情感辯論題貼文，格式如下：

[一句引人思考的情感辯論題，結尾加問號]
[2-3句情感共鳴的描述，每句換行]

[重複同一句辯論題]
✅ 會 / ❌ 不會，留言告訴我 👇

規則：
- 辯論題要貼近真實生活，讓人有感
- 描述句子要有畫面感，像在跟朋友說話
- 不要用「——」
- 不要超過100字
- 只輸出貼文內容，不要加任何說明
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return response.text.strip()

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

if __name__ == "__main__":
    print("🤖 正在用 Gemini 產生情感辯論題...")
    content = generate_post()
    print(f"📝 產生內容：\n{content}\n")
    success = post_to_threads(content)
    if success:
        print("🎉 全部完成！")
