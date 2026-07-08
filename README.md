# Flame EXR Layers To Action

Autodesk Flame 2025 Batch 右键菜单脚本。

在 Batch 里选中一个 EXR ClipNode 后，右键运行 `Jiawei > EXR Layers To Action`。脚本会读取 EXR 里的 multipart/channel groups，弹出 UI 让你勾选要进入 Action 的层，然后自动创建一个 Action。

## 功能

- 读取选中 Batch `PyClipNode` 的 EXR 路径。
- 纯 Python 解析 EXR header，不依赖 OpenEXR / OpenImageIO / exrheader。
- UI 列出 EXR 里的所有 layer/group。
- 默认全不选，支持鼠标拖过多行连续勾选。
- 生成一个 Action。
- 自动把 `RGBA` 连接到 Action `Back`，用于匹配 EXR 分辨率。
- 每个选中的 layer 创建一个 Action Media 和一个 Surface。
- Surface 通过 media index 绑定到对应 Media，避免绑定到 background。
- 当前 blend mode 使用 Flame 默认设置；在当前测试环境里默认是 Add。

## 安装

把 `custom_actions_hook.py` 复制到 Flame 会扫描的 Python 脚本目录：

```bash
cp custom_actions_hook.py /opt/Autodesk/shared/python/custom_actions_hook.py
rm -rf /opt/Autodesk/shared/python/__pycache__
```

然后重启 Flame，或在 Flame 里执行 `Refresh Python Hooks`。

## 使用

1. 打开 Flame Batch。
2. 选中一个 EXR ClipNode。
3. 右键打开菜单。
4. 点击 `Jiawei > EXR Layers To Action`。
5. 在弹出的 UI 里勾选需要的 EXR layers。
6. 点击 `Create Action`。

脚本会创建一个 Action，并为每个选择的 layer 创建对应的 Media 和 Surface。

## 验证菜单是否加载

在 Flame Python Console 里运行：

```python
import custom_actions_hook as h
print(h.__file__)
print(h.get_batch_custom_ui_actions())
```

正确时应返回类似：

```python
[{'name': 'Jiawei', 'actions': [{'name': 'EXR Layers To Action', ...}]}]
```

## 注意

`custom_actions_hook.py` 是 Flame 的固定 hook 入口文件名。如果你的 Flame 环境里有多个同名文件，请以 Console 里 `h.__file__` 打印出来的路径为准。

如果右键菜单没有出现，通常是下面两个原因之一：

- Flame 实际读取的不是你复制的那份 `custom_actions_hook.py`。
- 对应目录里的 `__pycache__` 还缓存着旧版本。

## 当前测试环境

- Autodesk Flame 2025.2.4
- Batch 里选中 EXR ClipNode 运行
- EXR multipart layers 已验证可以列出并创建 Action Media / Surface
