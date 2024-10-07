# demo

[![用树莓派DIY随身语音聊天小蜜，连刀郎的新歌她都知道](https://res.cloudinary.com/marcomontalbano/image/upload/v1728272835/video_to_markdown/images/youtube--0uAuJgzIW3I-c05b58ac6eb4c4700831b2b3070cd403.jpg)](https://youtu.be/0uAuJgzIW3I?si=yyXegoMsISi0GfvS "用树莓派DIY随身语音聊天小蜜，连刀郎的新歌她都知道")

# MacOS 开发环境配置

```shell
brew install python@3.11 portaudio
python3.11 -m venv .venv
source .venv/bin/activate
pip3.11 install -r requirements.txt
```

# 树莓派 OS 开发环境配置

```shell
sudo apt install portaudio19-dev python3-dev libopenblas0
python3.11 -m venv .venv
source .venv/bin/activate
pip3.11 install -r requirements.txt
```

# 配置科大讯飞开放平台接口认证环境变量

```shell
cp .env.example .env
```

打开 https://console.xfyun.cn/services/iat 申请接口认证信息，将 APPID、APP_KEY、API_SECRET 填入 .env 文件中。

```text
asr_app_id=xxx
asr_api_key=xxx
asr_api_secret=xxx
```

打开 https://console.xfyun.cn/services/tts 申请接口认证信息，将 APPID、APP_KEY、API_SECRET 填入 .env 文件中。

```text
tts_app_id=xxx
tts_api_key=xxx
tts_api_secret=xxx
```

打开 https://console.xfyun.cn/services/bm3 申请接口认证信息，将 APIPassword 替换 .env 中的 openai_api_key。

```text
openai_url=https://spark-api-open.xf-yun.com/v1
openai_model=generalv3
openai_api_key=xxx
```

# 运行

```shell
python3.11 -u main.py
```
