# Phân tích kết quả train raw và clean

Nguồn số liệu là bốn JSON theo seed, `comparison.json` và các báo cáo QC trong `submission/reports/`.

## 1. Chênh mAP50 và độ dao động giữa seed

Raw đạt 0,7256 ở seed 0 và 0,7259 ở seed 1 (trung bình 0,7258, độ lệch chuẩn 0,0002). Clean đạt 0,6788 và 0,7219 (trung bình 0,7004, độ lệch chuẩn 0,0305). Chênh clean − raw lần lượt là −0,0468 và −0,0040, trung bình **−0,0254**. Cả hai lượt raw đều có điểm cao hơn, nhưng độ chênh trung bình nhỏ hơn độ dao động giữa hai seed của clean. Hai seed chỉ cho phép mô tả kết quả của các lượt này. Cần thêm seed và một phép đo kiểm soát rò rỉ để đánh giá tác động của việc làm sạch.

## 2. Số ảnh raw thực sự dùng để train

Cả hai JSON ghi 224 ảnh raw. `scripts/train_compare.py` đếm file trong thư mục train đã dựng, trước khi trừ ảnh mà Ultralytics có thể loại lúc quét. Báo cáo QC ghi 2 ảnh hỏng ở cửa vào và các lỗi nhãn như 3 dòng sai định dạng, 6 dòng sai ID và 8 box tràn. Các số này dùng tiêu chí QC của lab và có thể trùng trên cùng ảnh. Số ảnh thực sự được loader giữ ở hai lượt raw chưa xác nhận được vì repo chưa có log quét train hoặc cache nhãn của Colab. Để xác nhận, đối chiếu dòng quét `train` và các mục `ignoring corrupt image/label` của từng lượt. Ảnh nền hoặc ảnh thiếu file nhãn có thể vẫn được loader giữ, nên cần đọc riêng các trường hợp này.

## 3. Rò rỉ từ raw sang tập test

`01_intake.csv` ghi 4/224 ảnh raw có cờ `LEAK_TEST`, cả bốn đều khớp ảnh test: `img_0049 → test_033.jpg`, `img_0167 → test_044.jpg`, `img_0174 → test_085.jpg` và `img_0221 → test_009.jpg`. Chưa đo được mức tăng mAP50 do rò rỉ. Để ước lượng, chạy thêm một biến thể raw bỏ riêng bốn ảnh trên khỏi tập train, giữ nguyên nhãn còn lại, seed, siêu tham số, val và test. So chênh mAP50 theo từng seed với raw hiện tại. Có thể thêm đối chứng bỏ bốn ảnh raw không rò rỉ để kiểm tra ảnh hưởng riêng của việc giảm số ảnh train.

## 4. AP50 theo lớp

| Lớp | Raw TB | Clean TB | Clean − raw |
|---|---:|---:|---:|
| car | 0,7375 | 0,7485 | +0,0110 |
| person | 0,8221 | 0,8274 | +0,0053 |
| truck | 0,6485 | 0,5588 | −0,0897 |
| bus | 0,6949 | 0,6667 | −0,0282 |

`car` tăng nhiều nhất (+1,10 điểm phần trăm) và tăng ở cả hai seed. `02_error_list_v1.csv` ghi 53 cờ thiếu box và 18 cờ sai lớp. Việc bổ sung box bị thiếu hoặc sửa nhầm giữa car, truck và bus có thể giúp tín hiệu huấn luyện cho car. Đây là giả thuyết vì báo cáo tổng hợp cờ theo mã, chưa định lượng số box car đã sửa. Có thể đối chiếu nhãn raw và clean của các ảnh đã duyệt, đếm box car thêm mới hoặc đổi lớp để kiểm tra.

## 5. Những lỗi còn lại trong clean

Hàng đợi có 125 ảnh, ngân sách duyệt 80 ảnh. Còn 45 ảnh trong hàng đợi ban đầu chưa được duyệt, và gate tính 38/205 ảnh còn cảnh báo chưa được xử lý sau QC cuối. `07_error_list_v3.csv` có 71 cảnh báo, gồm 21 nghi box thừa, 20 nghi box lỏng, 13 nghi thiếu box, 3 nghi sai lớp, 7 box nhỏ, 3 box lớn và 4 nhãn rỗng. Các số dòng này gồm cả cờ trên ảnh đã duyệt và một ảnh có thể có nhiều cờ. Bản clean là bản nháp **Hold** với 0 lỗi bắt buộc. Cần xác minh các cờ còn lại bằng mắt để biết bản nhãn còn có thể cải thiện đến đâu.
