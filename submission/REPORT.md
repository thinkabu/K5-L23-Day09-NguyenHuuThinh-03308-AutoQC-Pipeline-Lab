# Báo cáo Day 09 — Nguyễn Hữu Thịnh, 03308

## 1. Kết luận trước
**Hold (mã thoát 10).** Pipeline nhận 205/224 ảnh và xuất 205 ảnh vào bản nháp `clean_v1`. Sau khi mô phỏng duyệt 80/125 ảnh trong hàng đợi, còn 0 lỗi bắt buộc và 38/205 ảnh có cảnh báo (18,54%), vượt ngưỡng 10%.

## 2. Lỗi và phân việc
Số liệu từ `02_error_list_v1.csv`. Mỗi số là số dòng báo cáo, trừ nhóm cửa vào tính theo ảnh.

| Mã lỗi và số lượng | Ai xử lý | Vì sao |
|---|---|---|
| `CORRUPT_IMAGE` 2, `BAD_SIZE` 3, `DUP_IMAGE_EXACT` 8, `DUP_IMAGE_NEAR` 2, `LEAK_TEST` 4 (19/224 ảnh) | Máy | Loại ở cửa vào theo quy tắc chất lượng, trùng và rò rỉ. |
| `BAD_FORMAT` 3, `BAD_CLASS_ID` 6, `BOX_ZERO` 4, `DUP_BOX` 7 (20/36 lỗi bắt buộc sau cửa vào) | Máy | Bỏ các dòng nhãn hỏng hoặc lặp. |
| `BOX_OUT_OF_IMAGE` 8, `BAD_CLASS_NAME` 2 (10/36) | Máy | Cắt box về trong ảnh hoặc chuẩn hóa tên lớp trong YAML. |
| `MISSING_LABEL_FILE` 6 (6/36) | Người | Xem ảnh và gán nhãn. |
| `POSSIBLE_MISSING` 53, `POSSIBLE_WRONG_CLASS` 18, `POSSIBLE_LOOSE_BOX` 28, `POSSIBLE_FALSE_POS` 29 (128/153 cảnh báo) | Người | So ảnh với nhãn và kiểm tra bất đồng với model. |
| `BOX_TINY` 6, `BOX_HUGE` 3, `EMPTY_LABEL` 12, `CLASS_RARE` 4 (25/153) | Người | Kiểm box, xác nhận ảnh nền và xem thống kê lớp. |

Ảnh `img_0020` đứng đầu với 11,524 điểm nhờ cộng điểm dòng đã xóa và hai cảnh báo `POSSIBLE_MISSING`, `POSSIBLE_WRONG_CLASS` theo độ tin cậy. Ảnh thiếu file nhãn được 10 điểm. Đối chiếu `06_review_log.csv` với `04_error_list_v2.csv`, lượt duyệt 80 ảnh bao phủ **94/123 cảnh báo ngữ nghĩa** trên **74/103 ảnh** có cảnh báo ngữ nghĩa.

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 4 | `DUP_IMAGE_NEAR` 3/3 · 3/6 → 4/4 · 4/6. `DUP_IMAGE_EXACT` giữ 3/3 · 3/3. | 4 bắt thêm 1 ảnh gần trùng và có 0 cờ sai trên calib. Các mức 6–14 cho cùng kết quả. Dùng mức 4 để hạn chế loại nhầm ảnh khi áp dụng trên lô khác. |
| `second_opinion.conf` | 0.25 | 0.60 | `POSSIBLE_MISSING` 8/16 · 8/8 → 8/14 · 8/8. `POSSIBLE_WRONG_CLASS` 5/9 · 5/6 → 5/8 · 5/6. `POSSIBLE_LOOSE_BOX` 2/7 · 2/5 → 1/5 · 1/5. `POSSIBLE_FALSE_POS` giữ 5/16 · 5/5. | 0.60 giảm cờ sai cho lỗi thiếu nhãn và sai lớp, giữ số ca đúng của hai nhóm này. Đổi lại, bỏ sót thêm 1 ca box lỏng. Ở 0.70, recall của thiếu nhãn giảm còn 7/8. |

**Giới hạn của calibration.** Với 39 ảnh và chỉ 6 ca gần trùng đã chèn, việc bắt thêm 1 ca làm recall tăng từ 3/6 lên 4/6 trên calib. Trên raw, hai ngưỡng 2 và 4 lại cho cùng danh sách loại 19/224 ảnh, gồm 8 trùng byte, 2 gần trùng, 4 trùng kho tham chiếu và 5 ảnh hỏng hoặc nhỏ. Khi mở hai cặp gần trùng `img_0076/img_0042` và `img_0143/img_0037`, cả hai đều cho thấy cùng cảnh xe buýt ở hai kích thước ảnh. Cả hai cặp có khoảng cách pHash bằng 0, nên việc nâng ngưỡng không tạo thêm cờ trên các cặp này. Kết quả 4/4 trên calib chưa cho biết precision trên toàn lô raw.

**Chạy thử sau hiệu chỉnh.** Hàng đợi giảm từ 145/205 xuống 125/205 ảnh, vẫn vượt ngân sách 80 ảnh. Gate trả về **Hold** với 0 lỗi bắt buộc và 38/205 ảnh còn cảnh báo (18,54%).

## 4. Cửa chặn và điều pipeline KHÔNG bắt được

**Thử gate với `--budget 0`.** Duyệt 0/125 ảnh, cả 6/6 ảnh thiếu file nhãn vẫn có `MISSING_LABEL_FILE`. Gate trả **Rework**, mã thoát **20**. `08_summary.json` ghi `exported: null` và thư mục export của lần thử không được tạo. Dữ liệu thử nằm trong `work/step5-gate-69645966/`.

**Đối chiếu 10 ảnh đã xem với báo cáo QC trước và sau autofix.**

- `img_0001` — Quan sát thấy một người giữa khung hình thiếu box `person`. QC gắn một cờ `POSSIBLE_MISSING` cho ảnh này.
- `img_0002` — Quan sát thấy hai box `person` không chứa người. Cả hai vòng QC đều không có cờ cho ảnh này. Box sai về ngữ nghĩa có thể vẫn hợp lệ về cú pháp.
- `img_0007` — Quan sát thấy nhiều ô tô thiếu box `car`. Cả hai vòng QC đều không có cờ cho ảnh này. Model có thể bỏ qua vật thể hoặc dự đoán dưới ngưỡng kiểm.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
**Chưa chạy.** Lần nộp này dùng phần lõi của lab và bỏ qua phần train Colab tùy chọn.

## 6. Quyết định và ghi chú AI
Giữ **Hold**. Nếu vẫn có 205 ảnh, cần duyệt tiếp và xử lý cảnh báo của ít nhất 18 trong 38 ảnh còn cờ để còn tối đa 20/205 ảnh (9,76%). Chạy lại QC và xác nhận vẫn còn 0 lỗi bắt buộc trước khi phát hành.

- **Prompt chính** — Nhờ Codex thực hiện Bước 2 trong `GUIDE.md` dựa trên docstring và unit test của bốn module, dùng ngưỡng trong cấu hình.
- **Kiểm tra** — Codex chạy 79 unit test, thử các ca tự tạo có lỗi chèn sẵn, đọc các lệnh sửa file của `autofix` và chạy pipeline trên bản sao làm việc trong `work/`.
- **Một lần AI sai** — Codex ban đầu dùng đường dẫn tạm cố định cho pytest. Lần chạy lại gặp `WinError 5` khi pytest xóa thư mục cũ. Dùng đường dẫn tạm mới cho mỗi lần chạy đã khắc phục lỗi.
