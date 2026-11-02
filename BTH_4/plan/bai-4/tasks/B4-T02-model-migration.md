# B4-T02 — Models, ràng buộc và migration

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T01.

## Mục tiêu và phạm vi

Tạo Order và OrderItem đúng schema trong [plan](../ke-hoach-trien-khai.md). Phạm vi: orders/models.py, migrations/, tests/test_models.py.

## Các bước

- [x] Khai báo đủ 7 cột orders và 7 cột order_items; explicit INT PK, Decimal(10,2), tên bảng đúng hợp đồng.
- [x] FK OrderItem.order có db_column order_id và cascade; product_id chỉ là integer tham chiếu logic.
- [x] Thêm check constraint quantity > 0, tiền không âm, status hợp lệ; unique order/product.
- [x] Khai báo timestamps tự quản lý; nghiệp vụ sẽ cập nhật updated_at khi items đổi.
- [x] Tạo migration đầu tiên; kiểm tra sql/schema và chạy trên DB Order mới, không sửa DB hai service cũ.

## Nghiệm thu

- [x] Migration chạy sạch; kiểm tra không còn model change chưa tạo migration.
- [x] Constraint từ chối dữ liệu âm, quantity bằng 0, trạng thái lạ và duplicate order/product.
- [x] Xóa order kéo theo items, xóa product bên ngoài không tạo FK xuyên service.
- [x] Test model dùng DB test riêng, không dựa vào dữ liệu thật.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `py -3.14 -m venv services/order-service/.venv`; pinned existing stack installed successfully.
- From `services/order-service`: `.venv/Scripts/python.exe manage.py migrate` applied all migrations to independent `database/orders.sqlite3`.
- `.venv/Scripts/python.exe manage.py check`: no issues.
- `.venv/Scripts/python.exe manage.py makemigrations --check --dry-run`: no changes.
- `.venv/Scripts/python.exe manage.py test orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 16 tests passed.
- `sqlmigrate orders 0001` inspected: local order FK, monetary/status/quantity checks, unique order/product.
