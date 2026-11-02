# B4-T03 — Serializers và validation

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T02.

## Mục tiêu và phạm vi

Chốt input/output của 10 API bằng serializer rõ ràng. Phạm vi: orders/serializers.py, helper validation và tests/test_serializers.py.

## Các bước

- [x] Serializer tạo order nhận customer_name, customer_email, items không rỗng; mỗi dòng nhận product_id và quantity.
- [x] Kiểm tra chuỗi trim, tên/email tối đa 255, email hợp lệ, ID và quantity là integer dương; từ chối bool/float/string/null cho integer.
- [x] Từ chối product_id lặp trong items và field lạ/read-only ở cả payload ngoài và từng dòng.
- [x] Serializer trạng thái chỉ nhận status; serializer thêm item nhận order_id/product_id/quantity; serializer sửa item chỉ nhận quantity.
- [x] Serializer đọc phân biệt order list và detail; tiền trả chuỗi 2 số thập phân, timestamps UTC; không nhận các tổng tiền do client gửi.
- [x] Định nghĩa parsing ID URL thống nhất; giới hạn số nguyên phù hợp SQLite, tránh overflow.

## Nghiệm thu

- [x] Test đủ payload hợp lệ, thiếu, rỗng, sai kiểu, email sai, field thừa, nested field thừa và ID quá lớn.
- [x] Không có serializer tự gọi HTTP hoặc ghi DB; phần nghiệp vụ nằm trong service layer.
- [x] Mẫu response khớp hợp đồng plan và không làm mất độ chính xác Decimal.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `py -3.14 -m venv services/order-service/.venv`; pinned existing stack installed successfully.
- From `services/order-service`: `.venv/Scripts/python.exe manage.py migrate` applied all migrations to independent `database/orders.sqlite3`.
- `.venv/Scripts/python.exe manage.py check`: no issues.
- `.venv/Scripts/python.exe manage.py makemigrations --check --dry-run`: no changes.
- `.venv/Scripts/python.exe manage.py test orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 16 tests passed.
- `sqlmigrate orders 0001` inspected: local order FK, monetary/status/quantity checks, unique order/product.
