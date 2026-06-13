# DesktopPet 🐱

一个常驻桌面的互动角色，陪伴你的日常。支持 AI 对话、动作互动、Live2D 模型、电池状态语音提醒。

![screenshot](./data/assets/images/firefly/icon/icon.png)

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🎮 **角色交互** | 左键触摸、拖拽移动、双击比心，角色会做出不同动作回应 |
| 🤖 **AI 对话** | 接入大语言模型，随时聊天。角色会根据对话内容做出相应表情动作 |
| 🎵 **语音系统** | 开关机问候、电池状态提醒、闲时随机语音 |
| 🔋 **电池监控** | 插拔电源检测、低电量/健康/充满各阶段语音提醒 |
| 🎨 **Live2D 模型** | 支持 Live2D 角色独立窗口显示（开发中） |
| 🌓 **主题切换** | 深色/浅色/跟随系统，自由切换 |
| 🚶 **自由行走** | 角色可在屏幕上自由走动（开发中） |
| 📦 **便携打包** | 单目录发布，无需安装 Python，解压即用 |

---

## 🚀 快速开始

### 下载即玩

```bash
# 1. 从 Releases 下载最新版并解压
# 2. 在解压目录创建 .env 文件（可参考 .env.example）
AI_API_KEY=sk-your-key-here
AI_API_BASE=https://api.deepseek.com
AI_MODEL=deepseek-chat

# 3. 双击 DesktopPet.exe
```

> 无需安装 Python，所有依赖已打包在发布包中。

### 从源码运行

```bash
git clone https://github.com/golden-train/DesktopPet.git
cd DesktopPet
pip install -r requirements.txt

# 配置 AI（可选，不配也能启动）
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 启动
python src/main.py
```

### 打包构建

```bash
pip install pyinstaller
BUILD.bat
# 产物在 dist/DesktopPet/
```

---

## 🎮 操作指南

| 操作 | 效果 |
|------|------|
| **左键角色** | 触发互动动作（点上半身比心，下半身蹭蹭） |
| **拖拽角色** | 在屏幕上随意移动位置 |
| **双击角色** | 触发比心动画 |
| **右键角色** | 打开功能菜单 |
| **右键 → 打开聊天** | 和 AI 对话，角色会自动走到对话框旁 |
| **右键 → 设置** | 人物缩放、音频开关、主题切换、AI 配置 |

---

## ⚙️ 配置

### AI 供应商

内置常见大模型供应商预设，也可自定义：

| 供应商 | API 地址 | 推荐模型 |
|--------|---------|---------|
| **DeepSeek** | `api.deepseek.com` | `deepseek-chat` |
| **OpenAI** | `api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` |
| **通义千问** | `dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus`, `qwen-max` |
| **月之暗面** | `api.moonshot.cn/v1` | `moonshot-v1-8k` |
| **智谱 GLM** | `open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| **SiliconFlow** | `api.siliconflow.cn/v1` | `DeepSeek-V3` 等 |
| **自定义** | 手动填入 | 手动输入 |

API Key 写入 `.env` 文件，会被 `.gitignore` 排除，不会提交到仓库。

---

## 🧱 项目结构

```
DesktopPet/
├── src/
│   ├── main.py              # 应用入口，模块组装
│   ├── core/
│   │   ├── config.py        # 统一配置管理器（JSON 读写）
│   │   └── paths.py         # 路径常量（开发/打包双模式）
│   ├── window/
│   │   ├── main_window.py   # 角色主窗口（透明无边框置顶）
│   │   ├── chat_window.py   # AI 对话窗口
│   │   └── management_window.py  # 设置管理窗口
│   ├── character/
│   │   └── animation.py     # 动作动画系统（帧序列播放）
│   ├── ai/
│   │   ├── client.py        # OpenAI SDK 封装 + .env 安全读写
│   │   ├── prompts.py       # 提示词管理 + 动作标记常量
│   │   └── providers.py     # 供应商预设配置
│   ├── voice/
│   │   └── service.py       # 统一语音播放服务
│   ├── extends/
│   │   └── battery_voice/   # 电池监控扩展线程
│   ├── live2d/              # Live2D 查看器
│   └── widgets/             # 可复用组件
├── data/
│   ├── config/              # JSON 配置文件
│   ├── audio/               # 语音 WAV 文件
│   ├── assets/images/       # 角色动作图片
│   └── live2d/              # Live2D 模型
├── BUILD.bat                # PyInstaller 打包脚本
└── .env.example             # AI 配置模板
```

---

## 🛠️ 技术栈

| 层 | 技术 |
|---|------|
| **GUI 框架** | PySide6 (Qt6) |
| **UI 组件库** | qfluentwidgets |
| **AI 接口** | OpenAI SDK（兼容任意 OpenAI 格式 API） |
| **音频播放** | Qt Multimedia (QMediaPlayer) |
| **电池监控** | psutil |
| **打包** | PyInstaller |
| **配置** | JSON + .env |
| **日志** | Python logging（控制台着色 + 文件双输出） |

---

## 📦 关于发布包

发布包使用 PyInstaller 打包为单目录应用，包含运行所需的所有依赖（Python、PySide6、qfluentwidgets、OpenAI SDK 等）。

```
DesktopPet.exe              # 主程序
_internal/                  # 依赖库和资源（不动）
data/                       # 配置、图片、音频
.env                        # API Key（首次运行自行创建）
```

> 发布包约 300MB，主要为 PySide6 的 DLL 文件，属于正常大小。

---

## 📄 License

**AGPL-3.0**

> **免责声明**：本项目所有角色贴图、Live2D 模型、音频等素材均来自网络搜集，**不遵循开源协议**，仅开源程序源代码。
> 本程序灵感来源于 PYmili，代码无关，贴图参考自 <a href="https://github.com/PYmili/MyFlowingFireflyWife">PYmili/MyFlowingFireflyWife</a>
> 如涉及侵权，请联系删除。感谢所有创作者的作品 🙏
