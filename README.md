# MacOS 开发环境配置

```shell
brew install python@3.11 portaudio
python3.11 -m venv .venv
source .venv/bin/activate
pip3.11 install -r requirements.txt
```

# 树莓派 OS 开发环境配置

```shell
sudo apt install portaudio19-dev
python3.11 -m venv .venv
source .venv/bin/activate
pip3.11 install -r requirements.txt
```

# 配置科大讯飞开放平台接口认证环境变量

```shell
cp .env.example .env
```

打开 https://console.xfyun.cn/services/iat 申请接口认证信息，将 APPID、APP_KEY、API_SECRET 填入 .env 文件中。


# 运行

```shell
python3.11 -u main.py
```