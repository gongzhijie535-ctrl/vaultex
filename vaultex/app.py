import os
import gradio as gr
from vaultex.core import extract, DEFAULT_EXTENSIONS


def pick_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        folder = filedialog.askdirectory(title="选择文件夹")
        root.destroy()
        return folder or ""
    except Exception as e:
        return f"⚠️ 无法打开选择窗口：{e}"


def _merge_extensions(selected, custom_str):
    exts = set(selected or [])
    for line in custom_str.splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith("."):
            line = "." + line
        exts.add(line.lower())
    return list(exts)


def _parse_lines(raw: str) -> list:
    return [s.strip() for s in raw.splitlines() if s.strip()]


def _parse_keyword_files(raw: str) -> set:
    return {s.strip().lower() for s in raw.splitlines() if s.strip()}


def _build_common_args(folder_path, selected_extensions, custom_extensions_str,
                       recursive, only_folders_str, skip_folders_str,
                       keyword_files_str, skip_files_str, max_file_kb):
    folder_path   = folder_path.strip()
    extensions    = _merge_extensions(selected_extensions, custom_extensions_str)
    only_folders  = _parse_lines(only_folders_str)
    skip_folders  = _parse_lines(skip_folders_str)
    keyword_files = _parse_keyword_files(keyword_files_str)
    skip_files    = _parse_lines(skip_files_str)
    max_kb        = int(max_file_kb) if str(max_file_kb).strip().isdigit() else 0
    return folder_path, extensions, only_folders, skip_folders, keyword_files, skip_files, max_kb


def run_scan(folder_path, selected_extensions, custom_extensions_str,
             recursive, only_folders_str, skip_folders_str,
             keyword_files_str, skip_files_str, max_file_kb):

    folder_path, extensions, only_folders, skip_folders, keyword_files, skip_files, max_kb = _build_common_args(
        folder_path, selected_extensions, custom_extensions_str,
        recursive, only_folders_str, skip_folders_str,
        keyword_files_str, skip_files_str, max_file_kb
    )

    if not folder_path:
        return "⚠️ 请输入文件夹路径"
    if not os.path.isdir(folder_path):
        return "⚠️ 路径不存在或不是文件夹"
    if not extensions:
        return "⚠️ 请至少选择或填写一种文件类型"

    from vaultex.core import _collect_files
    file_list = _collect_files(
        folder_path, extensions, recursive,
        skip_folders, skip_files, only_folders, max_kb, keyword_files
    )
    file_list.sort()

    if not file_list:
        return "⚠️ 没有找到符合条件的文件"

    lines = [f"🔍 扫描完成，共找到 {len(file_list)} 个文件：", ""]
    for i, f in enumerate(file_list, 1):
        rel  = os.path.relpath(f, folder_path)
        size = os.path.getsize(f) / 1024
        lines.append(f"  {i:>3}. {rel}  ({size:.1f} KB)")

    return "\n".join(lines)


def run_extract(folder_path, selected_extensions, custom_extensions_str,
                recursive, separator, only_folders_str, skip_folders_str,
                keyword_files_str, skip_files_str, max_file_kb,
                sort_by, save_to_file, output_filename):

    folder_path, extensions, only_folders, skip_folders, keyword_files, skip_files, max_kb = _build_common_args(
        folder_path, selected_extensions, custom_extensions_str,
        recursive, only_folders_str, skip_folders_str,
        keyword_files_str, skip_files_str, max_file_kb
    )

    if not folder_path:
        return "⚠️ 请输入文件夹路径", "未选择文件夹"
    if not os.path.isdir(folder_path):
        return "⚠️ 路径不存在或不是文件夹", "路径无效"
    if not extensions:
        return "⚠️ 请至少选择或填写一种文件类型", "未选择文件类型"

    separator_str = separator.strip() if separator.strip() else "=" * 60

    merged, file_list, stats = extract(
        folder_path=folder_path,
        extensions=extensions,
        recursive=recursive,
        separator=separator_str,
        skip_folders=skip_folders,
        skip_files=skip_files,
        only_folders=only_folders,
        max_file_kb=max_kb,
        sort_by=sort_by,
        keyword_files=keyword_files,
    )

    if not file_list:
        return "⚠️ 没有找到符合条件的文件", "0 个文件"

    saved_msg = ""
    if save_to_file:
        out_name = output_filename.strip() or "代码汇总.txt"
        if not out_name.endswith(".txt"):
            out_name += ".txt"
        out_path = os.path.join(folder_path, out_name)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(merged)
            saved_msg = f"\n💾 已保存到：{out_path}"
        except Exception as e:
            saved_msg = f"\n⚠️ 保存失败：{e}"

    summary_lines = [
        f"✅ 共提取 {stats['file_count']} 个文件",
        f"📊 总字符数：{stats['char_count']:,}",
        f"🤖 估算 Token：{stats['token_est']:,}  （字符数 ÷ 4，英文准 / 中文偏低）",
        "",
        "📋 文件清单：",
    ]
    for f in file_list:
        summary_lines.append(f"  • {os.path.relpath(f, folder_path)}")
    if saved_msg:
        summary_lines.append(saved_msg)

    return merged, "\n".join(summary_lines)


HELP_TEXT = """
## 📖 用法说明

**基本流程**
1. 点击 `📂 选择` 按钮选择目标文件夹，或直接粘贴路径
2. 勾选需要的文件类型（也可在下方自定义）
3. 按需展开「过滤条件」和「输出设置」填写参数
4. 点 `🔍 预览文件列表` 确认文件范围
5. 确认无误后点 `🚀 开始提取`

---

**过滤功能说明**

| 功能 | 说明 |
|------|------|
| ✅ 指定文件夹 | 只在这些文件夹里查找，每行一个，留空 = 不限制 |
| ⛔ 跳过文件夹 | 排除这些文件夹，每行一个 |
| ✅ 指定文件名 | 精确匹配完整文件名（含后缀），每行一个，留空 = 不限制 |
| ⛔ 跳过文件名 | 排除这些文件，每行一个完整文件名（含后缀） |
| 📦 文件大小上限 | 跳过超过指定 KB 的文件，0 = 不限制 |
| 🔁 递归模式 | 勾选则进入所有子文件夹，取消则只读当前层 |

---

**Token 估算说明**

- 纯英文代码：误差较小
- 含中文注释：实际 Token 会更高

主流模型上下文参考：GPT-4o ≈ 128K，Claude ≈ 200K，Gemini 1.5 Pro ≈ 1M
""".strip()


def launch():
    with gr.Blocks(title="Vaultex") as demo:

        gr.Markdown("# 🔐 Vaultex\n### 从文件夹中提取并合并文本文件内容")

        with gr.Tabs():

            # ── Tab 1：主界面 ────────────────────────────────────
            with gr.Tab("🚀 提取"):
                with gr.Row():

                    # 左栏：配置
                    with gr.Column(scale=1, min_width=340):

                        # 路径
                        with gr.Row():
                            folder_input = gr.Textbox(
                                label="📁 文件夹路径",
                                placeholder="手动输入或点右侧按钮选择",
                                lines=1,
                                scale=5
                            )
                            pick_btn = gr.Button("📂 选择", scale=1, min_width=60)
                        pick_btn.click(fn=pick_folder, inputs=[], outputs=[folder_input])

                        # 文件类型
                        with gr.Accordion("📄 文件类型", open=True):
                            ext_selector = gr.CheckboxGroup(
                                choices=DEFAULT_EXTENSIONS,
                                value=[".txt", ".md", ".py", ".js", ".json"],
                                label="勾选类型"
                            )
                            custom_ext_input = gr.Textbox(
                                label="➕ 自定义类型（每行一个）",
                                placeholder=".vue\n.svelte\n.lock",
                                lines=2
                            )

                        # 过滤条件（默认折叠）
                        with gr.Accordion("🔽 过滤条件", open=False):

                            gr.Markdown("**📂 文件夹**")
                            with gr.Row():
                                only_folders_input = gr.Textbox(
                                    label="✅ 指定文件夹（只看这些）",
                                    placeholder="src\nlib\nutils",
                                    lines=4
                                )
                                skip_folders_input = gr.Textbox(
                                    label="⛔ 跳过文件夹（排除这些）",
                                    placeholder="__pycache__\n.git\nnode_modules",
                                    lines=4
                                )

                            gr.Markdown("**📄 文件**")
                            with gr.Row():
                                keyword_files_input = gr.Textbox(
                                    label="✅ 指定文件名（只要这些，含后缀）",
                                    placeholder="model.py\nconfig.json",
                                    lines=4
                                )
                                skip_files_input = gr.Textbox(
                                    label="⛔ 跳过文件名（排除这些，含后缀）",
                                    placeholder="setup.py\nconfig.py",
                                    lines=4
                                )

                            max_kb_input = gr.Number(
                                label="📦 文件大小上限（KB，0 = 不限）",
                                value=0,
                                precision=0
                            )

                        # 输出设置（默认折叠）
                        with gr.Accordion("💾 输出设置", open=False):
                            with gr.Row():
                                recursive_toggle = gr.Checkbox(
                                    label="🔁 包含子文件夹",
                                    value=True,
                                    scale=1
                                )
                                sort_selector = gr.Radio(
                                    choices=[("路径", "path"), ("文件名", "name"), ("修改时间", "mtime")],
                                    value="path",
                                    label="🔃 排序方式",
                                    scale=2
                                )
                            separator_input = gr.Textbox(
                                label="✂️ 文件分隔符",
                                value="=" * 60,
                                lines=1
                            )
                            save_toggle = gr.Checkbox(
                                label="💾 同时保存到文件",
                                value=False
                            )
                            output_filename_input = gr.Textbox(
                                label="📄 输出文件名",
                                value="代码汇总.txt",
                                lines=1
                            )

                        # 按钮
                        with gr.Row():
                            scan_btn    = gr.Button("🔍 预览文件列表", variant="secondary", scale=1)
                            extract_btn = gr.Button("🚀 开始提取",     variant="primary",   scale=1)

                    # 右栏：输出
                    with gr.Column(scale=2):
                        scan_output = gr.Textbox(
                            label="🔍 文件列表预览",
                            lines=8,
                            interactive=False
                        )
                        summary_output = gr.Textbox(
                            label="📋 提取摘要",
                            lines=8,
                            interactive=False
                        )
                        result_output = gr.Textbox(
                            label="📝 合并内容",
                            lines=18,
                            interactive=False
                        )

            # ── Tab 2：用法说明 ──────────────────────────────────
            with gr.Tab("📖 用法说明"):
                gr.Markdown(HELP_TEXT)

        # 事件绑定
        scan_btn.click(
            fn=run_scan,
            inputs=[
                folder_input, ext_selector, custom_ext_input,
                recursive_toggle, only_folders_input, skip_folders_input,
                keyword_files_input, skip_files_input, max_kb_input
            ],
            outputs=[scan_output]
        )

        extract_btn.click(
            fn=run_extract,
            inputs=[
                folder_input, ext_selector, custom_ext_input,
                recursive_toggle, separator_input,
                only_folders_input, skip_folders_input,
                keyword_files_input, skip_files_input, max_kb_input,
                sort_selector, save_toggle, output_filename_input
            ],
            outputs=[result_output, summary_output]
        )

    demo.launch(theme=gr.themes.Soft())


if __name__ == "__main__":
    launch()
