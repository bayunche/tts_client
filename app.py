import os
import re
import requests
from flask import Flask, request, send_file, jsonify
from pydub import AudioSegment
from pydub.playback import play
import io
from flasgger import Swagger
from tts_client import batch_tts as client_batch_tts # 导入 tts_client 中的 batch_tts 函数
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
Swagger(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def natural_sort_key(s):
    """用于自然排序的键函数，处理文件名中的数字前缀"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

@app.route('/concatenate_wavs', methods=['POST'])
def concatenate_wavs():
    """
    拼接WAV文件并输出MP3文件
    ---
    consumes:
      - multipart/form-data
    parameters:
      - name: files
        in: formData
        type: file
        required: true
        description: 要拼接的WAV文件列表，文件名前缀（如“1_”，“2_”）决定拼接顺序。
        collectionFormat: multi
    responses:
      200:
        description: 拼接后的MP3文件
        schema:
          type: file
      400:
        description: 请求错误，例如没有文件或文件格式不正确
      500:
        description: 服务器内部错误，例如文件处理失败
    """
    logging.info("收到 /concatenate_wavs 请求")
    if 'files' not in request.files:
        logging.error("请求中没有文件部分")
        return jsonify({"error": "No files part in the request"}), 400

    files = request.files.getlist('files')
    if not files:
        logging.error("没有选择任何文件")
        return jsonify({"error": "No selected file"}), 400

    logging.info(f"清理上传目录: {UPLOAD_FOLDER}")
    for f in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, f))

    uploaded_filepaths = []
    for file in files:
        if file.filename == '':
            logging.warning("跳过空文件名")
            continue
        if file and file.filename.endswith('.wav'):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            uploaded_filepaths.append(filepath)
            logging.info(f"已上传文件: {file.filename}")
        else:
            logging.error(f"文件 {file.filename} 不是 WAV 文件")
            return jsonify({"error": f"File {file.filename} is not a WAV file"}), 400

    if not uploaded_filepaths:
        logging.error("没有上传有效的 WAV 文件")
        return jsonify({"error": "No valid WAV files uploaded"}), 400

    logging.info("对上传的 WAV 文件进行自然排序")
    uploaded_filepaths.sort(key=lambda x: natural_sort_key(os.path.basename(x)))

    combined_audio = AudioSegment.empty()
    logging.info("开始拼接 WAV 文件")
    for filepath in uploaded_filepaths:
        try:
            audio = AudioSegment.from_wav(filepath)
            combined_audio += audio
            logging.info(f"已拼接文件: {os.path.basename(filepath)}")
        except Exception as e:
            logging.exception(f"处理文件 {os.path.basename(filepath)} 时发生错误")
            return jsonify({"error": f"Error processing {os.path.basename(filepath)}: {str(e)}"}), 500

    output_filename = "combined_audio.mp3"
    output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)

    logging.info(f"导出拼接后的 MP3 文件到: {output_filepath}")
    try:
        combined_audio.export(output_filepath, format="mp3")
        logging.info("MP3 文件导出成功")
    except Exception as e:
        logging.exception("导出 MP3 文件时发生错误")
        return jsonify({"error": f"Error exporting MP3: {str(e)}"}), 500

    logging.info(f"发送拼接后的 MP3 文件: {output_filename}")
    return send_file(output_filepath, as_attachment=True, download_name=output_filename, mimetype="audio/mpeg")

@app.route('/batch_tts', methods=['POST'])
def batch_tts():
    """
    批量调用TTS接口并拼接音频
    ---
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: array
          items:
            type: object
            properties:
              text:
                type: string
                description: 要转换为语音的文本
              model_name:
                type: string
                description: 要使用的模型名称
              emotion:
                type: string
                default: ""
                description: 情感（可选）
              speed_factor:
                type: number
                format: float
                default: 1.0
                description: 语速因子（可选）
              text_lang:
                type: string
                default: "中英混合"
                description: 文本语言（可选，例如  "中文", "中英混合"）
              speed_facter: # 修正参数名为 speed_facter
                type: number
                format: float
                default: 1.0
                description: 语速因子（可选）
            required:
              - text
              - model_name
    responses:
      200:
        description: 拼接后的音频文件
        schema:
          type: file
      400:
        description: 请求参数错误
      500:
        description: TTS服务调用失败或音频处理失败
    """
    logging.info("收到 /batch_tts 请求")
    inference_requests = request.get_json()
    logging.info(f"接收到的原始请求数据: {inference_requests}") # 添加日志
    if not inference_requests or not isinstance(inference_requests, list):
        logging.error("请求体为空或格式不正确，应为对象数组")
        return jsonify({"error": "请求体为空或格式不正确，应为对象数组"}), 400

    # 验证每个请求对象的结构
    for i, req in enumerate(inference_requests):
        if not isinstance(req, dict):
            logging.error(f"请求数组中第 {i} 个元素不是对象")
            return jsonify({"error": f"请求数组中第 {i} 个元素不是对象"}), 400
        if "text" not in req or not isinstance(req["text"], str):
            logging.error(f"请求对象中缺少 'text' 字段或其格式不正确 (索引: {i})")
            return jsonify({"error": f"请求对象中缺少 'text' 字段或其格式不正确 (索引: {i})"}), 400
        if "model_name" not in req or not isinstance(req["model_name"], str):
            logging.error(f"请求对象中缺少 'model_name' 字段或其格式不正确 (索引: {i})")
            return jsonify({"error": f"请求对象中缺少 'model_name' 字段或其格式不正确 (索引: {i})"}), 400
        # 可以添加更多对 emotion, speed_factor, text_lang 的验证，如果需要的话
    
    logging.info(f"收到 {len(inference_requests)} 个 TTS 推理请求")
    try:
        # 预处理请求，将 speed_factor 改为 speed_facter 以匹配 tts_client
        processed_requests = []
        for req in inference_requests:
            processed_req = req.copy()
            if "speed_factor" in processed_req:
                processed_req["speed_facter"] = processed_req.pop("speed_factor")
            
            # 修正 text_lang 参数，如果传入的是 'zh'，则转换为 '中英混合'
            if "text_lang" in processed_req and processed_req["text_lang"] == "zh":
                processed_req["text_lang"] = "中英混合" # 根据外部API示例进行修正

            processed_requests.append(processed_req)
        
        logging.info(f"传递给 client_batch_tts 的数据: {processed_requests}") # 添加日志
        for i, req in enumerate(processed_requests):
            logging.info(f"App: 准备发送给 TTS 客户端的第 {i+1} 个请求 - text_lang: {req.get('text_lang')}, speed_facter: {req.get('speed_facter')}")

        # 调用 tts_client 中定义的批量 TTS 函数
        generated_audios = client_batch_tts(
            inference_requests=processed_requests
        )
        logging.info(f"TTS 客户端返回 {len(generated_audios)} 个音频数据")

        if not generated_audios:
            logging.error("TTS 客户端没有生成任何音频数据")
            return jsonify({"error": "没有生成任何音频数据"}), 500

        combined_audio = AudioSegment.empty()
        logging.info("开始拼接 TTS 生成的音频")
        for i, audio_bytes in enumerate(generated_audios):
            if audio_bytes:
                try:
                    # 使用 io.BytesIO 从字节数据创建文件对象
                    audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
                    combined_audio += audio
                    logging.info(f"已拼接第 {i+1} 个音频片段")
                except Exception as audio_e:
                    logging.exception(f"处理第 {i+1} 个音频片段时发生错误: {audio_e}")
                    # 即使单个音频处理失败，也尝试继续拼接其他成功的音频
            else:
                logging.warning(f"第 {i+1} 个文本的音频生成失败，将跳过。")

        if not combined_audio.duration_seconds > 0:
            logging.error("合并后的音频为空，可能所有文本的音频都生成失败")
            return jsonify({"error": "合并后的音频为空，可能所有文本的音频都生成失败"}), 500

        output_file = os.path.join(OUTPUT_FOLDER, "combined_tts.mp3")
        logging.info(f"导出拼接后的 TTS 音频到: {output_file}")
        combined_audio.export(output_file, format="mp3")
        logging.info("TTS 拼接音频导出成功")

        logging.info(f"发送拼接后的 TTS 音频文件: combined_tts.mp3")
        return send_file(output_file, as_attachment=True, download_name="combined_tts.mp3", mimetype="audio/mpeg")

    except Exception as e:
        # 捕获并返回更详细的错误信息
        logging.exception(f"处理批量 TTS 请求时发生未预期错误: {e}")
        return jsonify({"error": f"处理批量 TTS 请求时发生错误: {str(e)}"}), 500

@app.route('/convert_tts', methods=['POST'])
def convert_tts():
    """
    调用TTS接口并返回音频下载链接
    ---
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: array
          items:
            type: object
            properties:
              text:
                type: string
                description: 要转换为语音的文本
              model_name:
                type: string
                description: 要使用的模型名称
              emotion:
                type: string
                default: ""
                description: 情感（可选）
              speed_factor:
                type: number
                format: float
                default: 1.0
                description: 语速因子（可选）
              text_lang:
                type: string
                default: "中英混合"
                description: 文本语言（可选，例如  "中文", "中英混合"）
              speed_facter: # 修正参数名为 speed_facter
                type: number
                format: float
                default: 1.0
                description: 语速因子（可选）
            required:
              - text
              - model_name
    responses:
      200:
        description: 包含音频下载链接的JSON对象
        schema:
          type: object
          properties:
            url:
              type: string
              description: 推理后音频文件的下载URL
      400:
        description: 请求参数错误
      500:
        description: TTS服务调用失败或音频处理失败
    """
    logging.info("收到 /convert_tts 请求")
    inference_requests = request.get_json()
    logging.info(f"接收到的原始请求数据: {inference_requests}")
    if not inference_requests or not isinstance(inference_requests, list):
        logging.error("请求体为空或格式不正确，应为对象数组")
        return jsonify({"error": "请求体为空或格式不正确，应为对象数组"}), 400

    for i, req in enumerate(inference_requests):
        if not isinstance(req, dict):
            logging.error(f"请求数组中第 {i} 个元素不是对象")
            return jsonify({"error": f"请求数组中第 {i} 个元素不是对象"}), 400
        if "text" not in req or not isinstance(req["text"], str):
            logging.error(f"请求对象中缺少 'text' 字段或其格式不正确 (索引: {i})")
            return jsonify({"error": f"请求对象中缺少 'text' 字段或其格式不正确 (索引: {i})"}), 400
        if "model_name" not in req or not isinstance(req["model_name"], str):
            logging.error(f"请求对象中缺少 'model_name' 字段或其格式不正确 (索引: {i})")
            return jsonify({"error": f"请求对象中缺少 'model_name' 字段或其格式不正确 (索引: {i})"}), 400
    
    logging.info(f"收到 {len(inference_requests)} 个 TTS 推理请求")
    try:
        processed_requests = []
        for req in inference_requests:
            processed_req = req.copy()
            if "speed_factor" in processed_req:
                processed_req["speed_facter"] = processed_req.pop("speed_factor")
            
            if "text_lang" in processed_req and processed_req["text_lang"] == "zh":
                processed_req["text_lang"] = "中英混合"
            processed_requests.append(processed_req)
        
        logging.info(f"传递给 client_batch_tts 的数据: {processed_requests}")
        for i, req in enumerate(processed_requests):
            logging.info(f"App: 准备发送给 TTS 客户端的第 {i+1} 个请求 - text_lang: {req.get('text_lang')}, speed_facter: {req.get('speed_facter')}")

        generated_audios = client_batch_tts(
            inference_requests=processed_requests
        )
        logging.info(f"TTS 客户端返回 {len(generated_audios)} 个音频数据")

        if not generated_audios:
            logging.error("TTS 客户端没有生成任何音频数据")
            return jsonify({"error": "没有生成任何音频数据"}), 500

        combined_audio = AudioSegment.empty()
        logging.info("开始拼接 TTS 生成的音频")
        for i, audio_bytes in enumerate(generated_audios):
            if audio_bytes:
                try:
                    audio = AudioSegment.from_wav(io.BytesIO(audio_bytes))
                    combined_audio += audio
                    logging.info(f"已拼接第 {i+1} 个音频片段")
                except Exception as audio_e:
                    logging.exception(f"处理第 {i+1} 个音频片段时发生错误: {audio_e}")
            else:
                logging.warning(f"第 {i+1} 个文本的音频生成失败，将跳过。")

        if not combined_audio.duration_seconds > 0:
            logging.error("合并后的音频为空，可能所有文本的音频都生成失败")
            return jsonify({"error": "合并后的音频为空，可能所有文本的音频都生成失败"}), 500

        output_filename = "converted_tts.mp3"
        output_file = os.path.join(OUTPUT_FOLDER, output_filename)
        logging.info(f"导出拼接后的 TTS 音频到: {output_file}")
        combined_audio.export(output_file, format="mp3")
        logging.info("TTS 拼接音频导出成功")

        download_url = f"{request.url_root}output/{output_filename}"
        logging.info(f"生成的下载 URL: {download_url}")
        return jsonify({"url": download_url})

    except Exception as e:
        logging.exception(f"处理 convert_tts 请求时发生未预期错误: {e}")
        return jsonify({"error": f"处理 convert_tts 请求时发生错误: {str(e)}"}), 500

@app.route('/')
def index():
    return """
    WAV Concatenation Service is running.<br>
    API文档: <a href="/apidocs">/apidocs</a><br>
    接口说明:<br>
    - POST /concatenate_wavs : 上传WAV文件进行拼接<br>
    - POST /batch_tts : 批量调用TTS接口并拼接音频<br>
    - POST /convert_tts : 调用TTS接口并返回音频下载链接<br>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4552, debug=True) # 调试模式方便开发，生产环境请关闭