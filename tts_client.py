import requests
from typing import List, Dict, Any
import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _process_single_tts_request(
    index: int,
    req: Dict[str, Any],
    infer_single_url: str,
    headers: Dict[str, str]
) -> (int, bytes):
    """
    处理单个 TTS 请求并下载音频。
    返回 (原始索引, 音频数据)
    """
    payload = {
        "model_name": req.get("model_name", ""),
        "emotion": req.get("emotion", "默认"),
        "text": req.get("text", ""),
        "speed_facter": req.get("speed_facter", 1), # 参数名修正为 speed_facter
        "text_lang": req.get("text_lang", "中英混合"), # 根据 curl 示例调整默认值
        "version": "v4",
        "prompt_text_lang": "中文",
        "top_k": 10,
        "top_p": 1,
        "temperature": 1,
        "text_split_method": "按标点符号切",
        "batch_size": 10,
        "batch_threshold": 0.75,
        "split_bucket": True,
        "fragment_interval": 0.3,
        "media_type": "wav",
        "parallel_infer": True,
        "repetition_penalty": 1.35,
        "seed": -1,
        "sample_steps": 16,
        "if_sr": False,
        "dl_url": "http://117.50.162.197:8000"
    }
    logging.info(f"TTS 客户端：已为第 {index+1} 个请求构建 payload (部分): text='{payload['text'][:30]}...', model_name='{payload.get('model_name')}', emotion='{payload.get('emotion')}', speed_facter='{payload.get('speed_facter')}', text_lang='{payload.get('text_lang')}'")
    logging.info(f"TTS 客户端：第 {index+1} 个请求完整 payload: {payload}")

    try:
        response = requests.post(infer_single_url, json=payload, headers=headers, timeout=600)
        response.raise_for_status()
        logging.info(f"TTS 客户端：第 {index+1} 个请求成功，状态码: {response.status_code}")

        response_json = response.json()
        audio_url = response_json.get("audio_url")
        if audio_url:
            logging.info(f"TTS 客户端：第 {index+1} 个请求获取到音频URL: {audio_url}")
            audio_response = requests.get(audio_url, timeout=600)
            audio_response.raise_for_status()
            logging.info(f"TTS 客户端：成功下载第 {index+1} 个音频数据")
            return index, audio_response.content
        else:
            logging.warning(f"TTS 客户端：第 {index+1} 个请求响应中未找到 audio_url。响应: {response_json}")
            return index, b""

    except requests.exceptions.Timeout:
        logging.exception(f"TTS 客户端：第 {index+1} 个请求超时，URL: {infer_single_url}")
        return index, b""
    except requests.exceptions.RequestException as e:
        status_code = response.status_code if response else 'N/A'
        response_text = response.text if response else 'N/A'
        logging.exception(f"TTS 客户端：第 {index+1} 个请求失败: {e}, 状态码: {status_code}, 响应内容: {response_text}")
        return index, b""
    except Exception as e:
        logging.exception(f"TTS 客户端：处理第 {index+1} 个响应时发生未预期错误: {e}")
        return index, b""

def batch_tts(
    inference_requests: List[Dict[str, Any]],
    base_url: str = "http://117.50.162.197:8000"
) -> List[bytes]:
    """
    为文本列表生成批量 TTS 音频数据，支持并发下载。

    Args:
        inference_requests: 包含要转换为语音的文本、模型信息、text_lang、speed_factor 和 emotion 的对象数组。
        base_url: API 的基础 URL。

    Returns:
        包含每个文本生成的音频数据的字节列表，顺序与输入请求一致。
    """
    infer_single_url = f"{base_url}/infer_single"
    logging.info(f"TTS 客户端：正在向 {infer_single_url} 发送 TTS 请求 (并发处理)")

    headers = {"Content-Type": "application/json"}
    
    # 使用 ThreadPoolExecutor 进行并发处理
    # max_workers 可以根据实际情况调整，例如 CPU 核心数或网络带宽
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_index = {
            executor.submit(_process_single_tts_request, i, req, infer_single_url, headers): i
            for i, req in enumerate(inference_requests)
        }
        
        # 初始化一个与请求列表长度相同的空列表，用于按顺序存储结果
        ordered_audio_data = [None] * len(inference_requests)

        for future in as_completed(future_to_index):
            original_index = future_to_index[future]
            try:
                index, audio_data = future.result()
                ordered_audio_data[index] = audio_data
            except Exception as exc:
                logging.exception(f"TTS 客户端：第 {original_index+1} 个请求在处理过程中发生异常: {exc}")
                ordered_audio_data[original_index] = b"" # 确保即使失败也保留占位符

    return ordered_audio_data

if __name__ == "__main__":
    # 示例用法
    inference_requests_list = [
        {
            "text": "你好，这是一个测试。",
            "model_name": "崩坏三-中文-丽塔",
            "emotion": "默认",
            "speed_factor": 1.0,
            "text_lang": "中文"
        },
        {
            "text": "这是第二个句子，用于批量处理。",
            "model_name": "崩坏三-中文-丽塔",
            "emotion": "默认",
            "speed_factor": 1.0,
            "text_lang": "中文"
        },
        {
            "text": "希望一切顺利。",
            "model_name": "崩坏三-中文-丽塔",
            "emotion": "默认",
            "speed_factor": 1.0,
            "text_lang": "中文"
        }
    ]

    logging.info(f"正在生成批量 TTS 音频...")
    generated_audios = batch_tts(
        inference_requests=inference_requests_list
    )

    if generated_audios:
        for i, audio in enumerate(generated_audios):
            if audio:
                output_filename = f"output_audio_{i+1}.wav"
                try:
                    with open(output_filename, "wb") as f:
                        f.write(audio)
                    logging.info(f"已将音频保存到 {output_filename}")
                except IOError as file_e:
                    logging.error(f"保存音频文件 {output_filename} 失败: {file_e}")
            else:
                logging.warning(f"第 {i+1} 个文本的音频生成失败。")
    else:
        logging.warning("没有生成任何音频数据。")