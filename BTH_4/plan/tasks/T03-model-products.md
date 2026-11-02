# T03 — Model và migration products

**Kết quả duy nhất:** bảng `products` được tạo đúng schema trong DB riêng của Product Service.

**Phụ thuộc:** T01. **Phạm vi:** model, migration và test mức DB của app `products`. Chưa xử lý HTTP.

## Checklist

- [x] Tạo model với `id`, `name` 255 ký tự, `description`, `price` decimal(10,2), `quantity`, `created_at`, `updated_at`.
- [x] Tự cấp ID và timestamp; `created_at` giữ nguyên khi cập nhật, `updated_at` thay đổi khi cập nhật.
- [x] Thêm ràng buộc DB `price >= 0` và `quantity >= 0`; tên sản phẩm không unique.
- [x] Tạo migration, chạy migration trên DB sản phẩm và kiểm tra tên bảng `products`.
- [x] Test lưu/đọc dữ liệu, giá trị biên, ràng buộc DB và timestamp.
- [x] Xác nhận migration không đụng DB của Auth Service.

## Hoàn thành khi

SQLite sản phẩm chứa schema đúng mục 4 của kế hoạch và test DB liên quan chạy qua.

## Bằng chứng / ghi chú của agent

- `products/models.py` và `products/migrations/0001_initial.py` định nghĩa bảng `products`, hai `CHECK` cho giá/số lượng không âm; tên không unique.
- Trong `services/product-service`, chạy `.venv/Scripts/python.exe manage.py makemigrations products` và `.venv/Scripts/python.exe manage.py migrate`: migration `products.0001_initial` áp dụng thành công vào `D:\BTH_SOA\BTH_3\database\products.sqlite3`. `makemigrations --check --dry-run`: `No changes detected`.
- `.venv/Scripts/python.exe manage.py test products`: 5 test, `OK`; kiểm tra lưu/đọc, tên trùng, giá `0.00` và `99999999.99`, vượt quá `max_digits`, hai ràng buộc DB và timestamp qua thời gian cố định.
- `connection.introspection.table_names()` có `products`; introspection xác nhận `id` là primary key và cả `products_price_nonnegative` lẫn `products_quantity_nonnegative` là `CHECK`. `database/DB_ProjectManagerment.db` không tồn tại trong workspace lúc chạy; migration chỉ dùng DB sản phẩm cấu hình trong `config/settings.py`.
