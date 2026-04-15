import os

DEFAULT_EXTENSIONS = [
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".scss",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".env",
    ".md", ".txt", ".rst", ".csv", ".xml",
    ".sh", ".bat", ".ps1",
    ".c", ".cpp", ".h", ".java", ".go", ".rs",
]


def extract(
    folder_path: str,
    extensions: list,
    recursive: bool = True,
    separator: str = "=" * 60,
    skip_folders: list = None,
    skip_files: list = None,
    only_folders: list = None,
    max_file_kb: int = 0,
    sort_by: str = "path",
    keyword_files: set = None,
) -> tuple[str, list, dict]:

    skip_folders  = skip_folders or []
    skip_files    = skip_files or []
    only_folders  = only_folders or []
    keyword_files = keyword_files or set()

    file_list = _collect_files(
        folder_path, extensions, recursive,
        skip_folders, skip_files, only_folders, max_file_kb, keyword_files
    )

    if sort_by == "name":
        file_list.sort(key=lambda p: os.path.basename(p).lower())
    elif sort_by == "mtime":
        file_list.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    else:
        file_list.sort()

    if not file_list:
        return "", [], {}

    lines = []
    total = len(file_list)

    lines.append("📁 代码汇总报告")
    lines.append(f"根目录：{folder_path}")
    lines.append(f"共读取：{total} 个文件")
    lines.append(separator)
    lines.append("")

    lines.append("📋 文件目录索引")
    lines.append("-" * 40)
    for i, filepath in enumerate(file_list, 1):
        rel = os.path.relpath(filepath, folder_path)
        size_kb = os.path.getsize(filepath) / 1024
        lines.append(f"  {i:>3}. {rel}  ({size_kb:.1f} KB)")
    lines.append("")
    lines.append("")

    for i, filepath in enumerate(file_list, 1):
        rel = os.path.relpath(filepath, folder_path)
        lines.append(separator)
        lines.append(f"# 文件 {i}/{total}：{rel}")
        lines.append(separator)
        lines.append("")
        content = _read_file(filepath)
        lines.append(content)
        lines.append("")
        lines.append("")

    merged = "\n".join(lines)

    char_count = sum(len(_read_file(f)) for f in file_list)
    stats = {
        "file_count": total,
        "char_count": char_count,
        "token_est":  char_count // 4,
    }

    return merged, file_list, stats


def _collect_files(folder, extensions, recursive, skip_folders, skip_files,
                   only_folders, max_file_kb, keyword_files=None):
    collected = []
    keyword_files = keyword_files or set()

    if recursive:
        for root, dirs, files in os.walk(folder):
            # 指定文件夹：当前层级的文件夹名必须在列表里
            if only_folders:
                dirs[:] = [
                    d for d in dirs
                    if d in only_folders and d not in skip_folders and not d.startswith(".")
                ]
            else:
                dirs[:] = [
                    d for d in dirs
                    if d not in skip_folders and not d.startswith(".")
                ]

            # 指定文件夹时，根目录本身的文件也要判断是否在指定范围内
            # 根目录直接收录，子目录只收录在 only_folders 里的
            rel_root = os.path.relpath(root, folder)
            if only_folders and rel_root != ".":
                top_dir = rel_root.split(os.sep)[0]
                if top_dir not in only_folders:
                    continue

            for file in files:
                full_path = os.path.join(root, file)
                if not _passes_filters(file, extensions, skip_files, max_file_kb, keyword_files, full_path):
                    continue
                collected.append(full_path)
    else:
        for item in os.listdir(folder):
            full_path = os.path.join(folder, item)
            if not os.path.isfile(full_path):
                continue
            if not _passes_filters(item, extensions, skip_files, max_file_kb, keyword_files, full_path):
                continue
            collected.append(full_path)

    return collected


def _passes_filters(filename, extensions, skip_files, max_file_kb, keyword_files, full_path):
    if filename in skip_files:
        return False
    if not any(filename.endswith(ext) for ext in extensions):
        return False
    if max_file_kb > 0 and os.path.getsize(full_path) / 1024 > max_file_kb:
        return False
    if keyword_files and filename.lower() not in keyword_files:
        return False
    return True


def _read_file(filepath):
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return f"⚠️ 读取失败：{e}"
    return "⚠️ 读取失败：所有编码均无法解析"
