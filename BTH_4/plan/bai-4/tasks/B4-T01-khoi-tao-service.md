# B4-T01 — Khởi tạo Order Service độc lập

Trạng thái: **Hoàn thành**. Phụ thuộc: người dùng duyệt [plan](../ke-hoach-trien-khai.md).

## Mục tiêu và phạm vi

Tạo project `services/order-service` dùng Django REST Framework, chạy cổng 8002 với DB `database/orders.sqlite3`. Phạm vi: manage.py, requirements.txt, config/, package orders/, .env.example và ignore nếu cần.

## Các bước

- [x] Kiểm tra Python, dependencies và môi trường ảo sẵn có; chọn bộ dependency tương thích stack repo, không tự nâng cấp Auth/Product.
- [x] Tạo project và app độc lập, không import source của service khác.
- [x] Cấu hình SQLite riêng, JSON renderer/parser, timezone UTC, URL không dấu slash cuối.
- [x] Cấu hình URL Auth/Product, timeout hữu hạn > 0, debug/secret/allowed hosts qua môi trường; ghi giá trị mặc định trong .env.example.
- [x] Không commit venv, DB, credential; không dùng secret Auth làm secret Order.

## Nghiệm thu

- [x] `manage.py check` thành công, project import được trong môi trường riêng.
- [x] Cấu hình DB trỏ đúng orders.sqlite3; không truy vấn DB Auth/Product.
- [x] Thiếu secret khi tắt debug hoặc timeout <= 0 gây lỗi cấu hình rõ ràng.
- [x] Chưa cần có API nghiệp vụ ở task này.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `py -3.14 -m venv services/order-service/.venv`; pinned existing stack installed successfully.
- From `services/order-service`: `.venv/Scripts/python.exe manage.py migrate` applied all migrations to independent `database/orders.sqlite3`.
- `.venv/Scripts/python.exe manage.py check`: no issues.
- `.venv/Scripts/python.exe manage.py makemigrations --check --dry-run`: no changes.
- `.venv/Scripts/python.exe manage.py test orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 16 tests passed.
- `sqlmigrate orders 0001` inspected: local order FK, monetary/status/quantity checks, unique order/product.
