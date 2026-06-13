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

本项目 **源码** 遵循 GPL 协议开源。

### ⚠️ 免责声明

本项目所使用的所有角色图片、Live2D 模型、音频等素材均来自网络搜集，
**仅用于个人学习和交流，不遵循任何开源协议**。

源码部分可自由使用、修改和分发，但**请自行替换所有贴图素材**。

如涉及侵权，请联系删除。感谢所有创作者的作品。🙏
