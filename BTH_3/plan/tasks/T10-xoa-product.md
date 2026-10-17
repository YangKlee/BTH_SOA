# T10 — DELETE /products/{id}

**Kết quả duy nhất:** API xóa hẳn một sản phẩm hiện có.

**Phụ thuộc:** T03, T05. **Phạm vi:** route/view và test riêng cho `DELETE /products/{id}`.

## Checklist

- [x] Khai báo `DELETE /products/{id}` không có dấu `/` cuối và yêu cầu access JWT.
- [x] Xóa bản ghi khỏi DB, trả `204` với body rỗng.
- [x] Xóa lại hoặc ID không tồn tại trả `404`; ID sai định dạng xử lý nhất quán với T07.
- [x] Test xóa và xác nhận bản ghi không còn, xóa lặp lại, thiếu token và auth không khả dụng.

## Hoàn thành khi

Endpoint đáp ứng dòng `DELETE /products/{id}` trong bảng API của kế hoạch.

## Bằng chứng / ghi chú của agent

- Route `path("products/<str:product_id>", ProductDetailView.as_view(), name="product_detail")` nhận ID dạng chuỗi để view trả `400` cho ID không hợp lệ. T07/T09 có thể thêm `get`/`put` vào `products/detail.py`.
- `manage.py test products.test_delete --verbosity 2`: 4/4 test đạt với SQLite in-memory và mock Auth Service; `manage.py check`: không có lỗi.
