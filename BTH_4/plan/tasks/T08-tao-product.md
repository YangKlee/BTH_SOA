# T08 — POST /products

**Kết quả duy nhất:** API tạo sản phẩm mới.

**Phụ thuộc:** T03, T04, T05. **Phạm vi:** route/view và test riêng cho `POST /products`.

## Checklist

- [x] Khai báo `POST /products` không có dấu `/` cuối và yêu cầu access JWT.
- [x] Dùng serializer T04; payload hợp lệ tạo bản ghi, trả `201`, đối tượng đã tạo và `Location: /products/{id}`.
- [x] Payload thiếu/sai trường trả `400`; cho phép trùng tên.
- [x] Test tạo thành công và đọc lại DB; dữ liệu sai, tên trùng, thiếu token và auth không khả dụng.

## Hoàn thành khi

Endpoint đáp ứng dòng `POST /products` trong bảng API của kế hoạch.

## Bằng chứng / ghi chú của agent

- Thêm `post` vào `ProductCollectionView` trong `products/collection.py`; dùng route `/products` sẵn có và lớp xác thực DRF T05. Serializer hợp lệ mới gọi `save()`, trả `201`, body sản phẩm đã tạo, header `Location` tương đối.
- `products/test_create.py`: 5 test cho tạo/đọc lại DB và Location, tên trùng, payload thiếu/sai/field lạ, thiếu token `401`, Auth Service offline `503`; hai lỗi xác thực không tạo bản ghi.
- Trong `services/product-service`, `.venv/Scripts/python.exe manage.py test products.test_create products.test_collection`: `Ran 9 tests ... OK` (bao gồm 4 test GET cũ để xác nhận không ảnh hưởng); `.venv/Scripts/python.exe manage.py check`: `System check identified no issues (0 silenced)`.
