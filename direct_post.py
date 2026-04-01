import os
import time
import requests
from PIL import Image, ImageDraw, ImageFont
import subprocess

NOTION_TOKEN = os.environ["NOTION_API_KEY"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]

GITHUB_REPO = "Angus061855/threads"
IMAGE_FILENAME = "output.png"
IMAGE_URL = f"https://angus061855.github.io/threads/{IMAGE_FILENAME}"

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

def generate_image(text):
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)

    # 簡單暗角效果（不用橢圓，改用漸層矩形）
    for y in range(H):
        darkness = int(80 * ((y / H) ** 2))
        dark_strip = Image.new("RGB", (W, 1), (0, 0, 0))
        mask_strip = Image.new("L", (W, 1), darkness)
        img.paste(dark_strip, (0, y), mask=mask_strip)

    # 載入字體
    try:
        font = ImageFont.truetype("ChiKuSung.otf", size=56)
    except Exception as e:
        print(f"⚠️ 字體載入失敗：{e}，使用預設字體")
        font = ImageFont.load_default()

    # 多行文字處理
    lines = text.split("\n")
    line_height = 80
    total_text_h = len(lines) * line_height

    start_y = (H - total_text_h) / 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) / 2
        y = start_y + i * line_height

        # 陰影
        draw.text((x + 2, y + 2), line, font=font, fill=(60, 60, 60))
        # 主文字
        draw.text((x, y), line, font=font, fill=(235, 235, 235))

    img.save(IMAGE_FILENAME)
    print(f"✅ 圖片已生成：{IMAGE_FILENAME}")

def push_image_to_github():
    subprocess.run(["git", "config", "user.email", "action@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Action"], check=True)
    subprocess.run(["git", "add", IMAGE_FILENAME], check=True)
    subprocess.run(["git", "commit", "-m", "Update output image"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("✅ 圖片已推送到 GitHub")
    print("⏳ 等待 GitHub Pages 部署（30秒）...")
    time.sleep(30)

def post_to_threads(text, image_url):
    create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    res = requests.post(create_url, params={
        "media_type": "IMAGE",
        "image_url": image_url,
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN
    })
    data = res.json()
    print("建立容器回傳：", data)

    creation_id = data.get("id")
    if not creation_id:
        print("❌ 建立容器失敗")
        return False

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

    post = posts[0]
    page_id = post["id"]

    rich_text = post["properties"]["文字"]["rich_text"]
    if not rich_text:
        print("❌ 文字欄位是空的，跳過")
        return

    text = rich_text[0]["plain_text"]
    print(f"準備發文：{text}")

    generate_image(text)
    push_image_to_github()

    success = post_to_threads(text, IMAGE_URL)

    if success:
        update_status(page_id)
        print("✅ 發文成功，狀態已更新為已發")

if __name__ == "__main__":
    main()
