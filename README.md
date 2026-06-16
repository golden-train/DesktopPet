# DesktopPet 🐱

一个常驻桌面的互动角色，陪伴你的日常。
支持 AI 对话、自定义角色模型、Live2D 显示、语音提醒。

（本项目的灵感和初始贴图素材来源于PYmili老师的[项目地址](https://github.com/PYmili/MyFlowingFireflyWife)，在这里感谢老师的贡献）

（基于其已经实现的功能，在精简了一下依赖库后，整体重构了代码和逻辑，去除了多余的依赖重新整理了文件结构，支持到新版本的QT以及python，以及增添了自定义模型的功能）

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 🎮 **角色交互** | 左键触摸（上半区比心/下半区蹭蹭）、拖拽移动、双击比心 |
| 🤖 **AI 对话** | 接入大语言模型，角色根据对话内容触发对应动作 |
| 🧑 **自定义模型** | 导入像素小人角色（任意动作名 + 任意帧数），在模型页一键切换，大小写不敏感 |
| 🎨 **Live2D 模型** | 支持 Live2D 角色独立窗口显示，支持导入自定义 Live2D 模型 |
| 🚶 **自由行走** | 角色可在屏幕上自由行走（无行走资源的模型自动禁用菜单） |
| 🎵 **语音系统** | 开关机问候、电池状态提醒、闲时随机语音，语音跟随当前模型 |
| 🔌 **扩展系统** | 插件架构，设置页统一管理，方便后续功能增强 |
| 🎯 **动作测试** | 模型页右键可测试模型的任意动作效果 |
>注意：
> 
> 1.如果你的自定模型没有standby将无法导入，导入失败时，检查命名，在模型ID命名阶段1.2.0版本存在中文文件夹会自动生成__导致无法更改的问题，自行删除__后用英文命名ID，下次的发行版中将会修复此问题。
> 
> 2.如果你新命名了文件动作，没有love和mention左键触摸（上半区比心/下半区蹭蹭）、拖拽移动、双击比心这里的功能不会生效
> 
> ！live2D模型当前仅供展示，为未完全功能和早期错误的技术路线，等待修改
> 
> 可以参考程序内的帮助文档导入帧动画，如果你没看懂，我？也许？会发个视频在B站上？也许？

---

## 🚀 快速开始

### 下载即玩
1.直接下载打包好的安装程序，结尾时setup，exe文件

2.从 Releases 下载最新版（zip文件）并解压，双击 `DesktopPet.exe`。（猜猜为什么要写这一段？）

> 无需安装 Python，所有依赖已打包在发布包中。
> 首次启动会显示许可协议弹窗，停留 15 秒后同意即可进入。

### 从源码运行（你觉得大我也没办法，QT就这么大，那你自己下源码吧，这总小了吧）

```bash
git clone https://github.com/golden-train/DesktopPet.git
cd DesktopPet
pip install -r requirements.txt 
#你不装依赖库如果跑了问我为什么运行不了，我只能说，你在航空学最简易的飞行工具炸了

# 启动（AI 功能可不配，不配也能启动，只是不能聊天）
python src/main.py

# AI 配置：右键角色 → 设置 → AI 配置 → 填写 API Key
```


---

## 🎮 操作指南

| 操作 | 效果 |
|------|------|
| **左键上半身** | 比心动画 |
| **左键下半身** | 蹭蹭动画 |
| **拖拽角色** | 在屏幕上随意移动位置 |
| **双击角色** | 触发比心动画 |
| **右键角色** | 打开功能菜单 |
| **右键 → 打开聊天** | AI 对话，角色自动走到对话框旁，行走自动停止 |
| **右键 → Live2D 查看器** | 切换到 Live2D 模型显示 |
| **右键 → 自由行走** | 角色在屏幕边缘自动来回行走（需模型支持） |
| **右键 → 复位位置** | 窗口移出屏幕时复位到右下角 |
| **右键 → 设置** | 模型管理、缩放、音频、AI 配置、扩展管理 |

---

## ⚙️ AI 配置

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

API Key 写入 exe 同级目录的 `.env` 文件，不会被 Git 追踪。

### AI 提示词生成

在 AI 配置页点击「AI 生成提示词」，用自然语言描述角色特征，
AI 自动生成结构化系统提示词，支持命名保存为预设。

---

## 🧑 自定义角色模型

支持两种类型：

### 像素小人（帧动画模型）

准备以下目录结构，通过 设置 → 模型 → 导入新角色 导入：

```
你的模型/
├── actions/
│   ├── Standby/      ← 必需（待机动画帧）
│   │   ├── 0.png
│   │   └── 1.png
│   ├── love/         ← 可选
│   ├── left/         ← 可选（同时有 left+right 才支持行走）
│   └── kiss/         ← 可自定义任意动作名
├── model.json        ← 推荐：{"name":"角色名","has_walking":true}
├── icon/icon.png     ← 可选
└── voice/            ← 可选（语音包）
```

- 支持 PNG/JPG/WebP/GIF 格式
- 目录名即动作名，可自定义
- 帧数量无限制，由你决定
- 大小写不敏感（`standby` / `Standby` 都识别）
- 在模型页右键 → 测试动作 可预览效果

### Live2D 模型

准备包含 `.model3.json` 的标准 Live2D 目录。
在 设置 → 模型 → 导入新模型 中导入，在 Live2D 查看器中切换查看。

---

## 🔌 扩展系统

扩展在 设置 → 扩展 中统一管理，支持开关。

| 内置扩展 | 说明 |
|---------|------|
| **🔋 电池语音** | 检测电源插拔和电量变化，播放语音提醒（默认关闭） |

注意，扩展系统基本脱离本程序独立存在，您可以在`src/extends/` 下，每个扩展一个子目录，继承 `ExtensionBase` 即可被自动发现。当前对扩展没有任何限制，您可以自由编写适合您的扩展功能

---

## 🧱 项目结构

```
DesktopPet/
├── src/
│   ├── main.py                  # 应用入口
│   ├── core/                    # 配置管理器 + 路径常量
│   ├── window/                  # 主窗口、聊天窗、设置窗
│   │   ├── main_window.py       # 角色显示（透明置顶无边框）
│   │   ├── chat_window.py       # AI 对话
│   │   └── management_window.py # 设置/模型/扩展/帮助
│   ├── character/               # 动画系统 + 行走控制
│   ├── model/                   # 模型导入（注册表/校验/导入器）
│   ├── ai/                      # AIClient + 提示词 + 供应商预设
│   ├── voice/                   # 语音播放（多模型支持）
│   ├── extends/                 # 扩展系统（电池语音等）
│   │   ├── base.py              # ExtensionBase 基类
│   │   ├── registry.py          # 自动发现注册表
│   │   └── battery_voice/       # 电池监控扩展
│   ├── live2d/                  # Live2D 服务器 + 查看器
│   └── widgets/                 # 可复用组件
├── data/
│   ├── config/                  # JSON 配置
│   ├── audio/                   # 语音文件
│   ├── assets/images/           # 角色动作帧
│   └── live2d/                  # Live2D 模型
├── READ/                        # 设计文档与开发指南
│   ├── IMPORT_GUIDE.md          # 模型导入教程
│   ├── EXTENSION_GUIDE.md       # 扩展开发指南
│   ├── CODING_AGENT_PLAN.md     # AI 编程助手设计方案
│   ├── FRAME_GENERATOR_GUIDE.md # 帧动画生成器学习指南
│   └── HELP_HOWTO.md            # 帮助页面修改指南
├── BUILD.bat                    # PyInstaller 打包
├── BUILD_INSTALLER.bat          # 一键构建安装包
├── DesktopPet.iss               # Inno Setup 安装脚本
└── DesktopPet.spec              # PyInstaller 配置
```

---

## 🛠️ 技术栈

| 层 | 技术 |
|---|------|
| GUI 框架 | PySide6 (Qt6) |
| UI 组件库 | qfluentwidgets |
| AI 接口 | OpenAI SDK（兼容任意 OpenAI 格式 API） |
| 音频播放 | Qt Multimedia (QMediaPlayer) |
| 电池监控 | psutil |
| 打包 | PyInstaller + Inno Setup |
| 配置 | JSON + .env |
| 日志 | Python logging |

---

## 📦 关于发布包
### 打包构建（您如果修改了源码需要重新打包程序可以参考）

```bash
# 方式一：PyInstaller 打包为目录（便携版）
BUILD.bat
# 输出在 dist/DesktopPet/

# 方式二：一键构建安装包（需要 Inno Setup 6+）
BUILD_INSTALLER.bat
# 输出在 dist/DesktopPet_Setup_x.x.x.exe
```
### 更新规划

1.AI agent接入，接入agent后，模型可以帮助你在编辑器中进行代码编写，在1.2.0发行的时候，已经完成了可行性测试，demo验收也通过了，正在编写正式版的过程中

2.Live2D模型的进一步支持，在后续版本中会增加于Live2D模型互动的相关内容

3.内存管理，当前项目在运行中会占用约150MB的内存，这是因为所有的模型直接在浏览器内核上调用运行的，如果想要优化基本只有重写自己的渲染逻辑，这是想当大的工作量，这个小项目本来是自己用的，想着不浪费大家tokens就放公开了，所以这一项基本不太可能实现。

4.自动帧动画生成器，目前在可行性验证阶段，还没有完全确定技术路线，如果您有对应的经验，我们可以一起来实现

PS：第四项是在帮同学远程导入模型时差点被血压带走时的想法。。。。。。

---

## 📄 License

**AGPL-3.0**

> **免责声明**：本项目所有角色贴图、Live2D 模型、音频等素材均来自网络搜集，**不遵循开源协议**，仅开源程序源代码。
> 如涉及侵权，请联系删除。感谢所有创作者的作品 🙏
