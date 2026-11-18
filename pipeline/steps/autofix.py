"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line


DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _clip(text):
    class_id, x, y, width, height = parse_yolo_line(text)
    left, top = max(0.0, x - width / 2), max(0.0, y - height / 2)
    right, bottom = min(1.0, x + width / 2), min(1.0, y + height / 2)
    if left >= right or top >= bottom:
        return ""
    if left == x - width / 2 and right == x + width / 2 and top == y - height / 2 and bottom == y + height / 2:
        return text
    return f"{class_id} {(left + right) / 2} {(top + bottom) / 2} {right - left} {bottom - top}"


def fix(ds, issues, cfg):
    errors = [issue for issue in issues if issue.severity == ERROR]
    removals = {
        issue.image for issue in errors
        if issue.code in REMOVE_CODES or issue.code.startswith("DUP_IMAGE_")
    }
    fixes = []

    def record(image, line, action, before, after):
        fixes.append({"image": image, "line": line, "action": action, "before": before, "after": after})

    remaining = set()
    for path in ds.image_files():
        if path.stem in removals:
            path.unlink()
            ds.label_path(path.stem).unlink(missing_ok=True)
            record(path.stem, None, "remove_image", path.name, "")
        else:
            remaining.add(path.stem)

    if any(issue.code == "BAD_CLASS_NAME" for issue in errors):
        path = ds.yaml_path
        data = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
        before = data.get("names")
        names = dict(enumerate(cfg["classes"]))
        if ds.yaml_names() != names:
            data["names"] = names
            path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            record("data.yaml", None, "rename_classes", str(before), str(names))

    edits = defaultdict(dict)
    needs_label = set()
    for issue in errors:
        stem, line, code = issue.image, issue.line, issue.code
        if stem in removals:
            continue
        if code == "MISSING_LABEL_FILE":
            needs_label.add(stem)
        elif line is not None and code in DROP_CODES:
            edits[stem][line] = "drop_line"
        elif line is not None and code == "BOX_OUT_OF_IMAGE":
            edits[stem].setdefault(line, "clip_box")

    for stem in sorted(needs_label & remaining):
        if not ds.label_path(stem).exists():
            record(stem, None, "needs_label", "(không có file)", "chuyển người gán")

    for stem, actions in edits.items():
        path = ds.label_path(stem)
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        updated = []
        for line, text in enumerate(original.splitlines(keepends=True), 1):
            action = actions.get(line)
            if action is None or not text.strip():
                updated.append(text)
                continue
            before = text.rstrip("\r\n")
            after = _clip(before) if action == "clip_box" else ""
            if after:
                updated.append(after + text[len(before):])
            if after != before:
                record(stem, line, action if after else "drop_line", before, after)
        revised = "".join(updated)
        if revised != original:
            path.write_text(revised, encoding="utf-8")
    return fixes
