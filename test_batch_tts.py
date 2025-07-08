import requests
import json

# 服务地址
url = "http://127.0.0.1:4552/batch_tts"

# 请求体，包含两个TTS任务
# 第一个任务指定了 version 为 'v4'
# 第二个任务未指定 version，将使用服务器默认值
payload = [
    {
        "text": "你好，这是一个带版本号的测试。",
        "model_name": "崩坏三-中文-丽塔",
        "version": "v4"
    },
    {
        "text": "这是第二个句子，使用默认版本。",
        "model_name": "崩坏三-中文-丽塔"
    }
]

headers = {
    'Content-Type': 'application/json'
}

print(f"向 {url} 发送请求...")
print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

try:
    response = requests.post(url, headers=headers, data=json.dumps(payload).encode('utf-8'), timeout=600)

    # 检查响应状态码
    if response.status_code == 200:
        # 尝试将响应内容保存为文件
        try:
            with open("test_output.mp3", "wb") as f:
                f.write(response.content)
            print("测试成功！响应的音频文件已保存为 test_output.mp3")
        except Exception as e:
            print(f"测试失败：无法写入文件。错误: {e}")
    else:
        # 打印错误信息
        print(f"测试失败！状态码: {response.status_code}")
        try:
            error_details = response.json()
            print(f"错误详情: {error_details}")
        except json.JSONDecodeError:
            print(f"无法解析JSON格式的错误响应: {response.text}")

except requests.exceptions.RequestException as e:
    print(f"测试失败：请求过程中发生错误。错误: {e}")
