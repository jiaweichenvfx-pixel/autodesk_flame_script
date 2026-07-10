# Flame EXR Layers To Action

Autodesk Flame 2025 Batch 右键菜单脚本。

在 Batch 里选中一个 EXR ClipNode 后，右键运行 `Jiawei > EXR Layers To Action`。脚本会读取 EXR 里的 multipart/channel groups，弹出 UI 让你勾选要进入 Action 的层，然后自动创建一个 Action。

## 功能

- 读取选中 Batch `PyClipNode` 的 EXR 路径。
- 纯 Python 解析 EXR header，不依赖 OpenEXR / OpenImageIO / exrheader。
- UI 列出 EXR 里的所有 layer/group。
- 支持 multipart EXR，也支持 single-part EXR 中以 `layer.R/G/B/A` 命名的 channel groups。
- 单独的根通道 `R/G/B/A` 会自动合并显示为 `RGB` 或 `RGBA`。
- 默认全不选，支持鼠标拖过多行连续勾选。
- 生成一个 Action。
- 自动把 `RGBA` 连接到 Action `Back`，用于匹配 EXR 分辨率。
- 每个选中的 layer 创建一个 Action Media 和一个 Surface。
- Surface 通过 media index 绑定到对应 Media，避免绑定到 background。
- Flame socket 名匹配不区分大小写，并兼容空格、下划线、重复名称及 `RGB` / `RGBA` 名称差异。
- Action 会放在源 EXR 节点右侧较远位置，并与 `RGBA/rgb` 输出水平对齐。
- 每个 Action Media 会放在两者中间，并与对应的 EXR output socket 水平对齐，减少连线交叉。
- 如果 Batch 里已有同名 Action，会自动使用 `EXR_LAYERS_ACTION_02`、`_03` 等唯一名称。
- 当前 blend mode 使用 Flame 默认设置；在当前测试环境里默认是 Add。

## 安装

把 `exr_autocomp.py` 复制到 Flame 会扫描的 Python 脚本目录：

```bash
cp exr_autocomp.py /opt/Autodesk/shared/python/exr_autocomp.py
rm -rf /opt/Autodesk/shared/python/__pycache__
```

如果安装过旧版，请删除旧文件，避免出现重复菜单：

```bash
rm -f /opt/Autodesk/shared/python/custom_actions_hook.py
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
import exr_autocomp as h
print(h.__file__)
print(h.get_batch_custom_ui_actions())
```

正确时应返回类似：

```python
[{'name': 'Jiawei', 'actions': [{'name': 'EXR Layers To Action', ...}]}]
```

## 注意

如果右键菜单没有出现，通常是下面两个原因之一：

- Flame 实际读取的不是你复制的那份 `exr_autocomp.py`。
- 对应目录里的 `__pycache__` 还缓存着旧版本。

## 当前测试环境

- Autodesk Flame 2025.2.4
- Batch 里选中 EXR ClipNode 运行
- EXR multipart layers 已验证可以列出并创建 Action Media / Surface
