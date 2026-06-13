# DesktopPet 项目规划书

## 1. 项目概述

桌面宠物—— 一个常驻桌面的互动角色，支援 AI 对话、Live2D 模型、电池状态语音提醒。

### 技术栈

| 层 | 技术 |
|---|------|
| GUI | PySide6 (Qt6) |
| UI 组件 | qfluentwidgets（可选，可徒手写 Qt 样式） |
| AI | OpenAI SDK（可接入任意兼容 API） |
| 音频 | PySide6.QtMultimedia.QMediaPlayer |
| 本地服务器 | Python 标准库 http.server |
| 日志 | Python 标准库 logging |
| 配置 | JSON 文件 |
| 电池监控 | psutil |

### 目录结构

```
src/
├── main.py                    # 应用入口
├── core/                      # 核心基础设施
│   ├── __init__.py
│   ├── config.py              # 统一配置管理器
│   └── paths.py               # 路径常量
├── window/                    # 窗口管理
│   ├── __init__.py
│   ├── main_window.py         # 主窗口（角色显示）
│   ├── chat_window.py         # AI 对话窗口
│   ├── management_window.py   # 设置/管理窗口
│   ├── popup_window.py        # 弹出消息窗
│   └── loading_window.py      # 启动加载窗口
├── character/                 # 角色表现
│   ├── __init__.py
│   ├── animation.py           # 动作序列（图片切换）
│   └── walking.py             # 自由行走逻辑
├── ai/                        # AI 服务
│   ├── __init__.py
│   ├── client.py              # API 调用封装
│   └── prompts.py             # 系统提示词管理
├── voice/                     # 语音服务
│   ├── __init__.py
│   └── service.py             # 统一语音播放
├── extends/                   # 扩展系统
│   ├── __init__.py
│   ├── base.py                # 扩展基类
│   └── battery_voice/         # 电池语音扩展
│       ├── __init__.py
│       └── main.py
├── live2d/                    # Live2D 查看器
│   ├── __init__.py
│   ├── server.py              # 本地 HTTP 服务器
│   └── viewer.py              # 查看器窗口
└── widgets/                   # 可复用小组件
    ├── __init__.py
    ├── toggle_card.py         # 带开关的卡片组件
    └── group_header.py        # 分组头部组件

data/
├── config/
│   ├── main.json              # 主配置
│   ├── voice_pack.json        # 语音包数据
│   ├── battery_voice.json     # 电池语音数据（可选，可合入主配置）
│   ├── action_pictures.json   # 动作图片配置
│   ├── skills.json            # AI 技能预设
│   └── live2d.json            # Live2D 配置
├── audio/
│   └── firefly/               # WAV 音频文件
├── assets/
│   └── images/
│       └── firefly/           # 角色动作图片
└── live2d/                    # Live2D 模型文件（不变动）
```

---

## 2. 模块规格说明书

### 2.1 core/config.py — 配置管理器

```python
class ConfigManager:
    """统一读写 data/config/ 下的所有 JSON 配置"""

    def __init__(self, config_dir: str):
        """config_dir = data/config/"""

    def read(self, name: str) -> dict:
        """读取 name.json，返回 dict"""

    def write(self, name: str, data: dict) -> None:
        """将 data 写入 name.json"""

    def get(self, name: str, key: str, default=None):
        """读取 name.json 中指定 key 的值"""

    def set(self, name: str, key: str, value) -> None:
        """修改 name.json 中指定 key 的值并保存"""
```

**配置文件列表及结构**：

```json
// main.json — 主配置
{
    "scaling": 0,
    "current_bg_image": "data/assets/images/firefly/default/bg.png",
    "voice_on_start": false,
    "voice_on_close": false
}

// voice_pack.json — 语音包
{
    "VoiceOnStart": {
        "morn": [{ "title": "...", "wav": "..." }],
        "noon": [{ "title": "...", "wav": "..." }],
        "night": [{ "title": "...", "wav": "..." }],
        "other": [{ "title": "...", "wav": "..." }]
    },
    "VoiceOnClose": { /* 同上结构 */ }
}

// battery_voice.json — 电池语音
{
    "power_plugged": [{ "title": "...", "wav": "..." }],
    "power_not_plugged": [{ "title": "...", "wav": "..." }],
    "LOW_BATTERY": [{ "title": "...", "wav": "..." }],
    "HEALTHY_POWER": [{ "title": "...", "wav": "..." }],
    "FULL_POWER": [{ "title": "...", "wav": "..." }]
}

// action_pictures.json — 动作图片集
{
    "Standby":    { "path": "data/assets/images/firefly/standby/" },
    "mention":    { "path": "data/assets/images/firefly/mention/" },
    "sleep":      { "path": "data/assets/images/firefly/sleep/" },
    "eat":        { "path": "data/assets/images/firefly/eat/" },
    "love":       { "path": "data/assets/images/firefly/love/" },
    "discomfort": { "path": "data/assets/images/firefly/discomfort/" },
    "left":       { "path": "data/assets/images/firefly/left/" },
    "right":      { "path": "data/assets/images/firefly/right/" }
}

// skills.json — AI 技能预设
{
    "skills": [
        { "name": "流萤", "prompt": "..." },
        { "name": "简洁助手", "prompt": "..." }
    ]
}

// live2d.json — Live2D 配置
{
    "current_model": "firefly",
    "server_port": 8687
}

// .env — AI 密钥（不提交 git）
AI_API_KEY=sk-xxx
AI_API_BASE=https://api.deepseek.com
AI_MODEL=deepseek-v4-flash
AI_SYSTEM_PROMPT=用最简洁最短的语句回答
```

---

### 2.2 character/animation.py — 动作动画系统

```python
class AnimationManager(QObject):
    """管理角色动作图片的加载和循环播放"""

    def __init__(self, config: ConfigManager):
        """
        - 在初始化时从 action_pictures.json 读取所有动作路径
        - 每个动作执行一次 os.walk() 收集图片列表，缓存下来
        """

    def load_action(self, key: str) -> list[str]:
        """获取指定动作的图片路径列表"""

    def get_next_image(self, key: str) -> str:
        """
        返回下一帧图片路径。
        - 持续动作（Standby/mention/sleep/discomfort）: 循环播放（播完再追加到末尾）
        - 一次性动作（left/right）: 播完返回 None
        """

    def available_actions(self) -> list[str]:
        """返回所有可用动作名"""
```

**行为规则**：
- `Standby` / `mention` / `sleep` / `discomfort` — 循环播放（帧播完追加到末尾）
- `eat` / `love` — 播放一次后回到 Standby
- `left` / `right` — 播放一次后触发行走移动
- 切换动作时立即中断当前播放

---

### 2.3 character/walking.py — 自由行走

```python
class WalkingController:
    """
    控制主窗口在屏幕上自由行走（左/右移动）
    通过 QTimer 定时向左或向右移动窗口位置
    """

    def __init__(self, window: QMainWindow):
        self.window = window
        self.direction: str = "left"   # "left" | "right"
        self.is_walking: bool = False
        self.timer: QTimer = None
        self.step_pixels: int = 15     # 每帧移动像素
        self.interval_ms: int = 200    # 帧间隔

    def toggle(self):
        """切换行走/停止"""

    def start(self):
        """开始行走"""

    def stop(self):
        """停止行走"""

    def _move(self):
        """
        每 tick 调用：
        1. 按 direction 方向移动窗口 self.step_pixels 像素
        2. 碰撞屏幕边缘则切换方向
        """
```

---

### 2.4 ai/client.py — AI 服务

```python
# 动作标记常量
ANIMATION_MARKERS = {
    "eat": "吃东西",
    "love": "比心/爱心",
    "sleep": "睡觉",
    "Standby": "待机/站立",
    "mention": "蹭蹭/引起注意",
    "discomfort": "不舒服",
    "left": "向左走",
    "right": "向右走",
}

class AIClient:
    """AI API 调用封装"""

    def __init__(self):
        """从 .env 读取 API Key / Base URL / Model"""

    def build_messages(self, history: list[dict]) -> list[dict]:
        """
        在 system prompt 末尾拼接 ANIMATION_MARKERS 说明，
        让 AI 知道可以通过 [eat] 等标记触发动画。
        """

    def ask(self, messages: list[dict]) -> str:
        """发送对话请求，返回 AI 回复文本（同步阻塞）"""


class ChatSignal(QObject):
    """用于跨线程信号传递（需要在主线程创建）"""
    reply_received = Signal(str)
    error_occurred = Signal(str)


def chat_async(messages: list[dict], signal: ChatSignal):
    """在后台线程调用 AI，完成后通过信号通知主线程"""
```

**AI 回复格式规范**：
- AI 回复中嵌入 `[动作名]` 标记（如 `[eat]`、`[love]`）来触发角色动画
- 多个标记同时出现时只取第一个

---

### 2.5 voice/service.py — 统一语音服务

```python
class VoiceService(QObject):
    """统一管理所有语音播放（电池语音 + 语音包）"""

    def __init__(self):
        """
        使用 PySide6.QtMultimedia.QMediaPlayer 播放音频
        支持 WAV / MP3 等 QMediaPlayer 支持的格式
        """

    def play(self, wav_path: str):
        """
        播放一个音频文件。
        如果正在播放则停止当前播放，立即播新的（不排队）。
        """

    def play_battery_voice(self, key: str):
        """
        从 battery_voice.json 中读取列表，随机选一条播放。
        key: power_plugged / power_not_plugged / LOW_BATTERY / HEALTHY_POWER / FULL_POWER
        """

    def play_voice_pack(self, key: str, time_of_day: str):
        """
        从 voice_pack.json 中按时段取列表，随机选一条播放。
        key: VoiceOnStart / VoiceOnClose
        time_of_day: morn / noon / evening / night / other
        """

    @staticmethod
    def get_time_of_day(hour: int) -> str:
        """
        6-8时   → morn
        10-12时 → noon
        18-21时 → evening
        21-6时  → night
        其他    → other
        """
```

---

### 2.6 main.py — 应用入口

```python
class DesktopPetApplication:
    """应用主控制器，负责组装所有模块并连接信号"""

    def __init__(self):
        # 1. 创建 QApplication
        # 2. 初始化 ConfigManager
        # 3. 初始化 VoiceService
        # 4. 初始化 AnimationManager
        # 5. 初始化 MainWindow
        # 6. 连接信号
        # 7. 初始化 BatteryVoice（if enabled）
        # 8. 显示窗口

    def run(self):
        """启动应用事件循环"""

    def _on_ai_reply(self, reply: str):
        """
        收到 AI 回复时：
        1. 解析 [动作名] 标记
        2. 触发 AnimationManager 切换动作
        3. 显示对话气泡
        """

    def _parse_animation_marker(self, text: str) -> str | None:
        """从文本中提取 [动作名] 标记，返回动作名或 None"""
```

**信号连接图**（核心）：
```
MainWindow.showEvent()
  └─→ VoiceService.play_voice_pack("VoiceOnStart", ...)

MainWindow.closeEvent()
  └─→ VoiceService.play_voice_pack("VoiceOnClose", ...)
  └─→ 等待播放完成后真正关闭窗口

MainWindow.clicked                    → AnimationManager.mentionEvent()
MainWindow.released                  → AnimationManager.standbyEvent()
MainWindow.double_clicked            → AnimationManager.loveEvent()
MainWindow.set_free_walking          → WalkingController.toggle()

AIClient.chat_async → reply_received → 提取 [动作名] → AnimationManager 切换
                                       → VoiceService 可扩展（AI 主动说话）
BatteryVoiceThread → 电池状态变化     → VoiceService.play_battery_voice(key)
```

---

### 2.7 extends/battery_voice/main.py — 电池语音扩展

```python
class BatteryMonitor(QThread):
    """
    独立线程，每 3 秒检测一次电池状态。
    检测到状态变化时通过信号通知主线程播放对应语音。
    """
    voice_triggered = Signal(str)   # 参数: key (power_plugged / LOW_BATTERY 等)

    def __init__(self):
        super().__init__()
        self._stop_flag: bool = False
        self._was_plugged: bool | None = None
        self._low_triggered: bool = False
        self._healthy_triggered: bool = False
        self._full_triggered: bool = False

    def stop(self):
        """请求线程停止"""

    def run(self):
        """每 3 秒检测：
        1. 电源插入/拔出状态变化 → 发射对应 signal
        2. 仅插入电源时检测电量阶段（低电量 / 健康 / 充满）
        3. 每个阶段只触发一次，拔电后重置
        """
```

**电池状态机**：
```
[拔电] ──插入电源──→ [插电]
                        │
                        ├─ 电量 < 50%  → 发射 "LOW_BATTERY" (仅一次)
                        ├─ 50-90%      → 发射 "HEALTHY_POWER" (仅一次)
                        └─ 100%        → 发射 "FULL_POWER" (仅一次)
[插电] ──拔掉电源──→ [拔电]  ← 重置所有触发标记
```

---

### 2.8 live2d/ — Live2D 查看器

```python
class Live2DServer:
    """
    基于 Python http.server 的本地 HTTP 服务器
    在独立线程中运行
    """

    def __init__(self, port: int = 8687, model_dir: str = "data/live2d"):
        """
        路由:
        GET /firefly  → 返回 firefly.html
        GET /chun     → 返回 chun.html
        GET /<path>   → 从 static/ 目录返回静态文件
        """

    def start(self):
        """在后台线程启动服务器"""

    def stop(self):
        """停止服务器"""


class Live2DViewer(QMainWindow):
    """
    透明无边框窗口，通过 QWebEngineView 加载 Live2D 模型
    """

    def __init__(self, server: Live2DServer, model: str = "firefly"):
        """
        - 无边框、透明背景、置顶
        - 默认位置：屏幕右下角
        - 右键菜单：刷新 / 切换模型(流萤/椿) / 退出
        """

    def load_model(self, model_name: str):
        """切换模型（/firefly 或 /chun）"""

    def closeEvent(self):
        """关闭时停止服务器线程（不调 sys.exit）"""
```

---

### 2.9 widgets/popup_window.py — 弹出消息窗

```python
class PopupWindow(QWidget):
    """
    右下角弹出的消息气泡，显示头像 + 文字，5 秒后自动关闭。
    """

    def __init__(self, text: str, icon_path: str = None, duration_ms: int = 5000):
        """
        - FramelessWindowHint
        - 自动避开任务栏
        - 双击关闭
        - 定时器关闭
        """
```

---

### 2.10 window/chat_window.py — AI 对话窗口

```python
class ChatWindow(QWidget):
    """
    独立的 AI 对话窗口，顶部置顶。
    """

    def __init__(self, ai_client: AIClient):
        """
        - 标题栏显示「✦ 与流萤聊天 ✦」
        - 聊天记录显示区（富文本）
        - 快捷问题按钮（4 个预设）
        - 输入框 + 发送按钮
        - 正在思考时禁用输入
        """

    def send_message(self, text: str):
        """
        1. 显示用户消息
        2. 追加到 history
        3. 显示 "正在思考..."
        4. 启动 ChatWorker（QThread）发送请求
        5. 收到回复 → 替换占位 → 显示 AI 消息
        """

    def _on_reply(self, reply: str):
        """收到 AI 回复，显示并追加到 history"""
```

---

### 2.11 window/management_window.py — 设置管理窗口

```python
class ManagementWindow(MSFluentWindow):
    """
    使用 qfluentwidgets 的导航窗口，内含：
    - 主页（占位）
    - 扩展管理
    - Live2D 设置
    - 设置（扫描 / 音频开关 / AI 配置 / 技能管理）
    """

    def __init__(self, main_window_ref):
        """
        导航项：
        1. 主页 → 占位
        2. 扩展 → ExtendInterface（开关电池语音等）
        3. Live2D → Live2DSettingsInterface
        4. 设置 → SettingInterface（底部）
        5. 帮助 → MessageBox（源码链接）
        """
```

**设置界面内容**：

| 设置项 | 控件 | 存储 |
|--------|------|------|
| 人物缩放 | ComboBox (0/2/4/8) | main.json → scaling |
| 启动音频 | SwitchButton | main.json → voice_on_start |
| 关闭音频 | SwitchButton | main.json → voice_on_close |
| API Key | LineEdit | .env → AI_API_KEY |
| AI 提供商 | ComboBox (DeepSeek/OpenAI 等) | .env → AI_API_BASE+AI_MODEL |
| API 地址 | LineEdit | .env → AI_API_BASE |
| 模型名称 | LineEdit | .env → AI_MODEL |
| 系统提示词 | TextEdit | .env → AI_SYSTEM_PROMPT |
| 技能预设 | ComboBox + 添加/删除 | skills.json |

---

## 3. 数据流图

```
┌──────────────────────────────────────────────────────────────────┐
│  main.py (DesktopPetApplication)                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │
│  │ MainWindow│  │ChatWindow│  │Live2D    │  │Management    │     │
│  │ (角色显示) │  │(AI对话)  │  │Viewer    │  │Window (设置) │     │
│  └─────┬────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘     │
│        │             │             │               │            │
│        └──────┬──────┘             │               │            │
│               │ (信号连接)          │               │            │
│               ▼                    │               │            │
│  ┌────────────────────┐            │               │            │
│  │  AnimationManager  │            │               │            │
│  │  action_pics.json  │            │               │            │
│  └────────────────────┘            │               │            │
│                                    │               │            │
│  ┌────────────────────┐            │               │            │
│  │  VoiceService      │◄───────────┘               │            │
│  │  QMediaPlayer      │                            │            │
│  └────────┬───────────┘                            │            │
│           │ ▲                                      │            │
│           ▼ │                                      │            │
│  ┌────────────────────┐  ┌────────────────────┐   │            │
│  │  BatteryMonitor    │  │  ConfigManager     │◄──┘            │
│  │  (QThread, psutil) │  │  data/config/*.json │                │
│  └────────────────────┘  └────────────────────┘                │
│                                                                │
│  ┌────────────────────┐  ┌────────────────────┐               │
│  │  AIClient          │  │  config.py          │               │
│  │  (openai SDK)      │  │  paths.py           │               │
│  └────────────────────┘  └────────────────────┘               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. 关键行为规范

### 4.1 窗口关闭流程

```
closeEvent 触发
  → 隐藏窗口 (self.hide())
  → 如果 voice_on_close == True:
      → 播放关闭语音（异步，不影响关闭流程）
  → 停止所有 QTimer
  → 停止 AnimationManager 线程
  → 调用 super().closeEvent()
```

### 4.2 角色点击交互

```
鼠标按下 (mousePressEvent):
  ├─ 左键:
  │    ├─ 如果点击上半区域 → 触发 loveEvent（比心）
  │    └─ 否则 → 触发 mentionEvent（蹭蹭）
  └─ 右键:
       └─ 弹出菜单（暂停/继续AI/设置/退出）

鼠标释放 (mouseReleaseEvent):
  └─ 回到 StandbyEvent
```

### 4.3 AI 回复解析

```python
def _parse_animation_marker(text: str) -> str | None:
    """匹配 [eat]、[love] 等标记"""
    match = re.search(r'\[(\w+)\]', text)
    if match and match.group(1) in ANIMATION_MARKERS:
        return match.group(1)
    return None
```

### 4.4 音频播放说明

```python
# 使用 PySide6 内置播放器，不需要 PyAudio
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

player = QMediaPlayer()
audio_output = QAudioOutput()
player.setAudioOutput(audio_output)
player.setSource(QUrl.fromLocalFile(wav_path))
audio_output.setVolume(0.8)
player.play()
```

### 4.5 Live2D 本地服务器

```python
# 使用标准库 http.server，不需要 Flask
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

class Live2DHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/firefly":
            # 返回 firefly.html
        elif self.path == "/chun":
            # 返回 chun.html
        else:
            # 从 static/ 目录提供文件

server = HTTPServer(("127.0.0.1", 8687), Live2DHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
```

---

## 5. 状态管理

### 5.1 主窗口状态

```python
class MainWindowState:
    """主窗口运行时状态（不持久化）"""
    scaling: int = 0
    current_bg_image: str = ""
    is_free_walking: bool = False
    walking_direction: str = "left"
    current_action: str = "Standby"
```

### 5.2 角色属性（RoleProperties）

```python
class RoleProperties:
    """角色属性（运行时）"""
    mood: int = 100       # 心情值 0-100
    satiety: int = 100    # 饱食度 0-100
    stamina: int = 100    # 体力值 0-100
```

---
## 打包程序要求
1.首次打开弹窗提示本程序的开源协议：GPL类型（在Phase 8时你需要撰写开源协议）和免责声明，必须停留15秒
2.打包所有依赖，是所有！！！确保仅需要exe就可运行

## 7. 实现顺序建议

| 阶段          | 内容                                  | 交付物           |
|-------------|-------------------------------------|---------------|
| **Phase 1** | 基础设施：ConfigManager + Paths + 目录结构   | 能读写配置         |
| **Phase 2** | 主窗口 + 角色图片切换 + 动作系统                 | 角色能在桌面显示并切换动作 |
| **Phase 3** | AI 客户端 + 对话窗口                       | 能聊天并触发动画      |
| **Phase 4** | 语音服务（VoiceService + BatteryMonitor） | 电池语音 + 开关机语音  |
| **Phase 5** | 设置管理窗口 + 扩展界面                       | 所有设置可调节       |
| **Phase 6** | Live2D 查看器                          | Live2D 独立窗口   |
| **Phase 7** | 收尾：行走、弹出窗、加载动画                      | 完整功能          |
| **Phase 8** | 执行打包程序 包要求只需要exe文件即可运行 在第一次运行时需要提示  | 打包可发行         |
