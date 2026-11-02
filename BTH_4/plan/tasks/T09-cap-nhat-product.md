# T09 — PUT /products/{id}

**Kết quả duy nhất:** API thay thế bốn trường có thể sửa của một sản phẩm hiện có.

**Phụ thuộc:** T03, T04, T05. **Phạm vi:** route/view và test riêng cho `PUT /products/{id}`.

## Checklist

- [x] Khai báo `PUT /products/{id}` không có dấu `/` cuối và yêu cầu access JWT.
- [x] Yêu cầu đủ bốn trường; payload hợp lệ trả `200` với sản phẩm sau cập nhật.
- [x] Giữ `id` và `created_at`; cập nhật `updated_at`; không tạo mới khi ID chưa tồn tại.
- [x] ID chưa tồn tại trả `404`, payload sai trả `400`; ID sai định dạng xử lý nhất quán với T07.
- [x] Test lưu/đọc lại thay đổi, timestamp, dữ liệu thiếu, ID không có, thiếu token và auth không khả dụng.

## Hoàn thành khi

Endpoint đáp ứng dòng `PUT /products/{id}` trong bảng API của kế hoạch.

## Bằng chứng / ghi chú của agent

- `ProductDetailView.put()` dùng route có sẵn `products/<str:product_id>`, hàm `parse_product_id` chung với GET/DELETE và `ProductSerializer` ở chế độ cập nhật đầy đủ (`partial=False`).
- `manage.py test products.test_update products.test_detail products.test_delete --verbosity 1`: 13/13 test đạt với SQLite in-memory và mock Auth Service. `manage.py check`: không có lỗi.
