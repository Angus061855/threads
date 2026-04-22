def create_container(text, reply_to_id=None):
    url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    payload = {
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN
    }
    if reply_to_id:
        payload["reply_to_id"] = reply_to_id
    res = requests.post(url, data=payload)
    data = res.json()
    print(f"create_container 回應：{res.status_code} / {data}")
    container_id = data.get("id")
    # 把錯誤訊息一起回傳
    error_msg = data.get("error", {}).get("message", "未知錯誤")
    return container_id, error_msg

def publish_container(container_id):
    url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    payload = {
        "creation_id": container_id,
        "access_token": THREADS_ACCESS_TOKEN
    }
    res = requests.post(url, data=payload)
    data = res.json()
    print(f"publish_container 回應：{res.status_code} / {data}")
    post_id = data.get("id")
    error_msg = data.get("error", {}).get("message", "未知錯誤")
    return post_id, error_msg

def post_thread_series(segments, title_text):
    previous_post_id = None

    for i, text in enumerate(segments):
        print(f"發第 {i+1} 段...")

        container_id, err = create_container(text, reply_to_id=previous_post_id)
        if not container_id:
            msg = f"❌ 串文發布失敗！\n標題：{title_text}\n段落：第 {i+1} 段\n階段：建立 container\n原因：{err}"
            print(msg)
            send_telegram(msg)
            return False

        time.sleep(5)

        post_id, err = publish_container(container_id)
        if not post_id:
            msg = f"❌ 串文發布失敗！\n標題：{title_text}\n段落：第 {i+1} 段\n階段：publish\n原因：{err}"
            print(msg)
            send_telegram(msg)
            return False

        print(f"第 {i+1} 段發布成功，post_id：{post_id}")
        previous_post_id = post_id

        if i < len(segments) - 1:
            time.sleep(3)

    return True

def mark_as_posted(page_id, title_text):
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
    res = requests.patch(url, headers=NOTION_HEADERS, json=payload)
    print("更新 Notion 狀態：", res.status_code)
    if res.status_code != 200:
        send_telegram(f"⚠️ Threads 發布成功，但 Notion 狀態更新失敗！\n標題：{title_text}\n狀態碼：{res.status_code}")

if __name__ == "__main__":
    try:
        page = get_first_pending_post()
        if page:
            page_id, segments, title_text = get_page_content(page)
            print(f"共 {len(segments)} 段，準備發串文...")
            success = post_thread_series(segments, title_text)
            if success:
                mark_as_posted(page_id, title_text)
                send_telegram(f"✅ Threads 串文發布成功！\n標題：{title_text}\n共 {len(segments)} 段")
        else:
            print("沒有待發文章，結束。")
    except Exception as e:
        send_telegram(f"🔥 程式發生未預期錯誤！\n原因：{str(e)}")
        raise
