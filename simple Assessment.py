import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import whisper
import subprocess
import tempfile
import requests
import unicodedata
import traceback

# 加载 Whisper medium 模型
model = whisper.load_model("medium")

# OpenRouter API Key，请替换成你的
OPENROUTER_API_KEY = "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"

# OpenRouter Chat API 端点
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def sanitize_unicode(text):
    return ''.join(c for c in text if unicodedata.category(c)[0] != 'C')

def log_error(e):
    with open("error_log.txt", "a", encoding="utf-8") as f:
        f.write(traceback.format_exc())
        f.write("\n\n")

def call_openrouter(messages, max_tokens=300):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    data = {
        "model": "openai/gpt-4",
        "messages": messages,
        "max_tokens": max_tokens
    }
    response = requests.post(OPENROUTER_URL, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def analyze_speech(text_clean):
    try:
        # 1. 雅思评分
        messages = [
            {"role": "system", "content": "你是雅思口语考官。"},
            {"role": "user", "content": (
                "请根据IELTS四项评分标准（流利度与连贯性，词汇资源，语法范围与准确性，发音）"
                "对以下内容评分（0-9），给简短点评和总分。\n\n" + text_clean
            )}
        ]
        score_feedback = call_openrouter(messages)

        # 2. 词汇升级建议
        messages = [
            {"role": "system", "content": "你是英语词汇专家。"},
            {"role": "user", "content": (
                "请列出以下内容中学生使用的词汇中哪些可以用更高级表达替代，并给出示例：\n\n" + text_clean
            )}
        ]
        vocab_upgrade = call_openrouter(messages)

        # 3. 词汇错误指出和解释
        messages = [
            {"role": "system", "content": "你是英语教师。"},
            {"role": "user", "content": (
                "请指出以下内容中的词汇使用错误或不当，并简要解释原因：\n\n" + text_clean
            )}
        ]
        vocab_errors = call_openrouter(messages)

        # 4. 语法结构统计
        messages = [
            {"role": "system", "content": "你是英语语法专家。"},
            {"role": "user", "content": (
                "请简要统计以下内容中使用的句型类型（简单句、复合句、复杂句）、"
                "主要时态及其频率：\n\n" + text_clean
            )}
        ]
        grammar_stats = call_openrouter(messages)

        final_feedback = (
            "【雅思四项评分与点评】\n" + score_feedback + "\n\n"
            "【词汇升级建议】\n" + vocab_upgrade + "\n\n"
            "【词汇错误指出】\n" + vocab_errors + "\n\n"
            "【语法结构统计】\n" + grammar_stats
        )
        return final_feedback
    except Exception as e:
        log_error(e)
        return f"调用OpenRouter接口出错：{e}"

def transcribe_audio():
    file_path = filedialog.askopenfilename(
        filetypes=[("音频文件", "*.aac *.mp3 *.wav *.m4a *.flac *.webm *.ogg *.mp4")]
    )
    if not file_path:
        return

    try:
        output_box.delete(1.0, tk.END)
        output_box.insert(tk.END, "正在识别音频...\n")
        root.update()

        if file_path.lower().endswith(".aac"):
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
            cmd = ["ffmpeg", "-y", "-i", file_path, temp_wav]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            real_path = temp_wav
        else:
            real_path = file_path

        result = model.transcribe(real_path, language=language_var.get())
        text = result["text"]
        text_clean = sanitize_unicode(text)

        output_box.insert(tk.END, "\nWhisper 识别结果：\n")
        output_box.insert(tk.END, text_clean + "\n\n")
        output_box.insert(tk.END, "正在调用 GPT (OpenRouter) 分析文本，请稍候...\n")
        root.update()

        feedback = analyze_speech(text_clean)

        output_box.insert(tk.END, "\n=== GPT 分析结果 ===\n")
        output_box.insert(tk.END, feedback)

    except Exception as e:
        log_error(e)
        messagebox.showerror("错误", "程序运行出错，请查看 error_log.txt。")

def save_text():
    text = output_box.get(1.0, tk.END).strip()
    if not text:
        messagebox.showinfo("提示", "没有文字可保存")
        return

    save_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("文本文件", "*.txt")]
    )
    if save_path:
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("成功", "文本已保存")
        except Exception as e:
            log_error(e)
            messagebox.showerror("保存失败", "无法保存文本，请查看 error_log.txt。")

root = tk.Tk()
root.title("Whisper 音频转文字与 GPT 多步雅思评分")
root.geometry("800x600")
output_font = ("Microsoft YaHei", 12)

tk.Label(root, text="语言代码（如 zh / en / ja）：").pack(pady=5)
language_var = tk.StringVar(value="en")
tk.Entry(root, textvariable=language_var).pack(padx=10, fill=tk.X)

tk.Button(root, text="上传音频并识别+评分", command=transcribe_audio).pack(pady=10)

output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=output_font)
output_box.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

tk.Button(root, text="保存结果为文本", command=save_text).pack(pady=10)

root.mainloop()
