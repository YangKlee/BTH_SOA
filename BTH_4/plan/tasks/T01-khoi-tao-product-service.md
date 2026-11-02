# T01 — Khởi tạo Product Service

**Kết quả duy nhất:** một dự án Django REST Framework độc lập có thể khởi động ở cổng 8001.

**Phụ thuộc:** Không. **Phạm vi:** `services/product-service/`, cấu hình DB sản phẩm và tệp ví dụ cấu hình. Chưa tạo model/API sản phẩm.

## Checklist

- [x] Tạo `manage.py`, package `config`, app `products` và `requirements.txt` với phiên bản tương thích bài 2.
- [x] Cấu hình SQLite tại `database/products.sqlite3`, không dùng `DB_ProjectManagerment.db`.
- [x] Cấu hình `AUTH_SERVICE_URL` mặc định `http://127.0.0.1:8000` và timeout hữu hạn cho bước gọi auth sau này.
- [x] Cấu hình timezone UTC, DRF, và cách cấp secret/debug từ biến môi trường phù hợp môi trường phát triển.
- [x] Chạy `python manage.py check` và khởi động thử `python manage.py runserver 8001`; ghi kết quả.
- [x] Xác nhận Product Service không import model/module hoặc mở DB của Auth Service.

## Hoàn thành khi

Project chạy độc lập ở 8001 và dùng đường dẫn DB riêng. Chưa cần Auth Service đang chạy.

## Bằng chứng / ghi chú của agent

- Dùng Python 3.14.6 qua `py -3.14`; môi trường ảo riêng `services/product-service/.venv` đã cài các phiên bản trong `requirements.txt` (Django 6.1.1, DRF 3.18.1).
- `services/product-service/.venv/Scripts/python.exe manage.py check`: `System check identified no issues (0 silenced)`.
- `services/product-service/.venv/Scripts/python.exe manage.py runserver 8001 --noreload`: báo `Starting WSGI development server at http://127.0.0.1:8001/`; `curl.exe --noproxy '*' http://127.0.0.1:8001/` trả HTTP 200 (trang Django mặc định vì chưa tạo API). Server đã dừng sau khi thử. Django báo 14 migration `auth`, `contenttypes` chưa áp dụng; sẽ chạy migration khi tạo schema sản phẩm ở T03.
- `manage.py shell` in đường dẫn DB `D:\BTH_SOA\BTH_3\database\products.sqlite3`, URL Auth mặc định `http://127.0.0.1:8000`, timeout `3.0` giây. Chưa kết nối hoặc tạo DB Auth. Tìm `auth-service`, `DB_ProjectManagerment`, `authentication` trong mã Product Service không có kết quả.
