# DesktopPet 🐱

一个常驻桌面的互动角色，支持 AI 对话、Live2D 模型、电池状态语音提醒。

## 快速开始

### 下载即玩

1. 从 [Releases](https://github.com/golden-train/DesktopPet/releases) 下载最新版 `DesktopPet-v*.zip`
2. 解压到任意目录
3. 编辑 `.env` 填入你的 AI API Key
4. 双击 `DesktopPet.exe`

> 无需安装 Python，所有依赖已打包。

### 从源码运行

```bash
git clone https://github.com/golden-train/DesktopPet.git
cd DesktopPet
pip install -r requirements.txt
python src/main.py
```

## 用法

| 操作 | 效果 |
|------|------|
| 左键角色 | 触发互动动作 |
| 右键角色 | 打开菜单（聊天 / 设置 / 退出） |
| 拖拽角色 | 移动窗口位置 |
| 右键 → 打开聊天 | 和 AI 对话，角色自动走到对话框旁 |

## 技术栈

| 层 | 技术 |
|---|------|
| GUI | PySide6 (Qt6) |
| UI 组件 | qfluentwidgets |
| AI | OpenAI SDK（兼容 DeepSeek / 通义千问 等） |
| 音频 | Qt Multimedia |
| 电池监控 | psutil |
| 打包 | PyInstaller |

## 项目结构

```
src/
├── main.py              # 应用入口
├── core/                # 配置管理、路径常量
├── window/              # 主窗口、聊天、设置
├── character/           # 动画系统
├── ai/                  # AI 客户端、提示词管理
├── voice/               # 语音播放服务
├── extends/             # 电池监控扩展
├── live2d/              # Live2D 查看器
└── widgets/             # 可复用组件
```

## License

APGL

> 注：本项目所有贴图来自网络，不遵循开源协议，仅开源原代码，有侵权请联系。
