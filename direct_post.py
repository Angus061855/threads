import os
import time
import requests
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageDraw, ImageFont

NOTION_TOKEN = os.environ["NOTION_API_KEY"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
CLOUDINARY_CLOUD_NAME = os.environ["CLOUDINARY_CLOUD_NAME"]
CLOUDINARY_API_KEY = os.environ["CLOUDINARY_API_KEY"]
CLOUDINARY_API_SECRET = os.environ["CLOUDINARY_API_SECRET"]

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

IMAGE_FILENAME = "output.png"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"

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

def smart_split(text, max_chars=24):
    text = text.strip()
    raw_lines = text.split("\n")

    if len(raw_lines) == 1 and len(text.replace(" ", "")) <= max_chars:
        return [text]

    if len(raw_lines) > 1:
        lines = [l.strip() for l in raw_lines if l.strip()]
        if len(lines) > 3:
            print(f"⚠️ 文字超過三行，只取前三行")
            lines = lines[:3]
        return lines

    break_chars = "，。！？、"
    sentences = []
    current = ""
    for char in text:
        current += char
        if char in break_chars:
            sentences.append(current)
            current = ""
    if current:
        sentences.append(current)

    lines = []
    current_line = ""
    for sentence in sentences:
        test = current_line + sentence
        if len(test.replace(" ", "")) <= max_chars:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            while len(sentence.replace(" ", "")) > max_chars:
                lines.append(sentence[:max_chars])
                sentence = sentence[max_chars:]
            current_line = sentence
    if current_line:
        lines.append(current_line)

    if len(lines) > 3:
        print(f"⚠️ 文字超過三行，只取前三行")
        lines = lines[:3]

    return lines

def generate_image(text):
    W, H = 1920, 640
    font_size = 72
    line_height = 100
    gap = 60

    img = Image.open(os.path.join(BASE_DIR, "background.png")).convert("RGB").resize((W, H))
    draw = ImageDraw.Draw(img)

    # 暗角漸層
    for y in range(H):
        darkness = int(100 * ((y / H) ** 2))
        dark_strip = Image.new("RGB", (W, 1), (0, 0, 0))
        mask_strip = Image.new("L", (W, 1), darkness)
        img.paste(dark_strip, (0, y), mask=mask_strip)

    try:
        font = ImageFont.truetype(FONT_PATH, size=font_size)
        font_sign = ImageFont.truetype(FONT_PATH, size=32)   # ← 簽名字體
        print(f"✅ 字體載入成功：{FONT_PATH}")
    except Exception as e:
        print(f"❌ 字體載入失敗：{e}")
        font = ImageFont.load_default()
        font_sign = ImageFont.load_default()

    lines = smart_split(text)
    print(f"斷行結果：{lines}")

    total_text_h = len(lines) * line_height
    start_y = (H - total_text_h) / 2

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        parts = line.split(" ")
        part_widths = []
        for p in parts:
            bbox = draw.textbbox((0, 0), p, font=font)
            part_widths.append(bbox[2] - bbox[0])
        total_w = sum(part_widths) + gap * (len(parts) - 1)
        x = (W - total_w) / 2
        for j, part in enumerate(parts):
            draw.text((x + 3, y + 3), part, font=font, fill=(40, 40, 40))
            draw.text((x, y), part, font=font, fill=(235, 235, 235))
            x += part_widths[j] + gap

    # ✅ 右下角簽名
    sign_text = "- Angus"
    sign_margin = 40
    bbox = draw.textbbox((0, 0), sign_text, font=font_sign)
    sw = bbox[2] - bbox[0]
    sh = bbox[3] - bbox[1]
    sx = W - sw - sign_margin
    sy = H - sh - sign_margin
    draw.text((sx + 2, sy + 2), sign_text, font=font_sign, fill=(20, 20, 20))   # 陰影
    draw.text((sx, sy), sign_text, font=font_sign, fill=(160, 160, 160))         # 本體

    img.save(IMAGE_FILENAME)
    print(f"✅ 圖片已生成：{IMAGE_FILENAME}")

def format_caption(text):
    """caption 換行 + 結尾加簽名"""
    lines = smart_split(text)
    return "\n".join(lines) + "\n\n- Angus"   # ✅ 文案簽名

def upload_to_cloudinary():
    result = cloudinary.uploader.upload(IMAGE_FILENAME)
    url = result.get("secure_url")
    if url:
        print(f"✅ 圖片上傳成功：{url}")
        return url
    else:
        print("❌ 圖片上傳失敗")
        return None

def post_to_threads(image_url, caption):
    create_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    res = requests.post(create_url, params={
        "media_type": "IMAGE",
        "image_url": image_url,
        "text": caption,
        "access_token": THREADS_ACCESS_TOKEN
    })
    data = res.json()
    print("建立容器回傳：", data)

    creation_id = data.get("id")
    if not creation_id:
        print("❌ 建立容器失敗")
        return False

    print("⏳ 等待容器準備（10秒）...")
    time.sleep(10)

    publish_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    res = requests.post(publish_url, params={
        "creation_id": creation_id,
        "access_token": THREADS_ACCESS_TOKEN
    })
    result = res.json()
    print("發布回傳：", result)

    if result.get("id"):
        return True
    else:
        print("❌ 發布失敗")
        return False

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

    image_url = upload_to_cloudinary()
    if not image_url:
        print("❌ 無法取得圖片 URL，終止")
        return

    caption = format_caption(text)
    print(f"caption：\n{caption}")

    success = post_to_threads(image_url, caption=caption)

    if success:
        update_status(page_id)
        print("✅ 發文成功，狀態已更新為已發")

if __name__ == "__main__":
    main()
