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
    W, H = 1200, 400
    img = Image.new("RGB", (W, H), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 黑板漸層效果（用多層半透明橢圓模擬）
    for i in range(80, 0, -1):
        alpha = int(60 * (i / 80))
        overlay = Image.new("RGB", (W, H), (30, 30, 30))
        ellipse_mask = Image.new("L", (W, H), 0)
        ellipse_draw = ImageDraw.Draw(ellipse_mask)
        margin = (80 - i) * 4
        ellipse_draw.ellipse(
            [W//2 - (W//2 - margin), H//2 - (H//2 - margin),
             W//2 + (W//2 - margin), H//2 + (H//2 - margin)],
            fill=alpha
        )
        img.paste(overlay, mask=ellipse_mask)

    # 底部暗角
    for y in range(H):
        darkness = int(120 * ((y / H) ** 1.5))
        dark_strip = Image.new("RGB", (W, 1), (0, 0, 0))
        mask_strip = Image.new("L", (W, 1), darkness)
        img.paste(dark_strip, (0, y), mask=mask_strip)

    # 載入字體
    try:
        font = ImageFont.truetype("ChiKuSung.otf", size=52)
    except:
        font = ImageFont.load_default()
        print("⚠️ 字體載入失敗，使用預設字體")

    # 文字置中
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (W - text_w) / 2
    y = (H - text_h) / 2

    # 文字陰影
    draw.text((x + 2, y + 2), text, font=font, fill=(80, 80, 80))
    # 主文字（白色）
    draw.text((x, y), text, font=font, fill=(240, 240, 240))

    img.save(IMAGE_FILENAME)
    print(f"✅ 圖片已生成：{IMAGE_FILENAME}")

def push_image_to_github():
    subprocess.run(["git", "config", "user.email", "action@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Action"], check=True)
    subprocess.run(["git", "add", IMAGE_FILENAME], check=True)
    subprocess.run(["git", "commit", "-m", "Update output image"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("✅ 圖片已推送到 GitHub")
    # 等待 GitHub Pages 部署
    print("⏳ 等待 GitHub Pages 部署（30秒）...")
    time.sleep(30)

def post_to_threads(text, image_url):
    # Step 1：建立圖片貼文容器
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

    # 生成圖片
    generate_image(text)

    # 推送圖片到 GitHub Pages
    push_image_to_github()

    # 發文到 Threads（圖片 + 文字）
    success = post_to_threads(text, IMAGE_URL)

    # 發文成功後更新 Notion 狀態
    if success:
        update_status(page_id)
        print("✅ 發文成功，狀態已更新為已發")

if __name__ == "__main__":
    main()
