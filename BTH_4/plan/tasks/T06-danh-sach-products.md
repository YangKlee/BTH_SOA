# T06 — GET /products

**Kết quả duy nhất:** API trả danh sách toàn bộ sản phẩm.

**Phụ thuộc:** T03, T04, T05. **Phạm vi:** route/view và test riêng cho `GET /products`.

## Checklist

- [x] Khai báo chính xác đường dẫn `GET /products` không có dấu `/` cuối.
- [x] Yêu cầu access JWT hợp lệ qua lớp xác thực T05.
- [x] Trả `200` với mảng sản phẩm sắp `id` tăng dần; bảng rỗng trả `[]`.
- [x] Không thêm phân trang/tìm kiếm.
- [x] Test bảng rỗng, nhiều sản phẩm đúng thứ tự, thiếu token và auth không khả dụng.

## Hoàn thành khi

Endpoint đáp ứng dòng `GET /products` trong bảng API của kế hoạch.

## Bằng chứng / ghi chú của agent

- `config/urls.py` khai báo route `products` trỏ tới `ProductCollectionView.get` trong `products/collection.py`. View dùng `Product.objects.order_by("id")` và `ProductSerializer(..., many=True)`; xác thực được áp dụng từ DRF settings T05.
- `products/test_collection.py` có 4 test: danh sách rỗng `[]`, ba sản phẩm đúng thứ tự và JSON đầy đủ, thiếu token `401`, Auth Service offline `503`. Test xác nhận mỗi request hợp lệ gọi xác minh Auth đúng một lần.
- Trong `services/product-service`, `.venv/Scripts/python.exe manage.py test products.test_collection`: `Ran 4 tests ... OK`; `.venv/Scripts/python.exe manage.py check`: `System check identified no issues (0 silenced)`.
