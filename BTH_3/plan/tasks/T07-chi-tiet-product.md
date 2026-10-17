# T07 — GET /products/{id}

**Kết quả duy nhất:** API trả chi tiết một sản phẩm theo ID.

**Phụ thuộc:** T03, T04, T05. **Phạm vi:** route/view và test riêng cho `GET /products/{id}`.

## Checklist

- [x] Khai báo đường dẫn `GET /products/{id}` không có dấu `/` cuối và yêu cầu access JWT.
- [x] ID hợp lệ, tồn tại trả `200` với đối tượng sản phẩm đầy đủ.
- [x] ID không tồn tại trả `404`; ID không hợp lệ trả JSON `400` hoặc `404` nhất quán và ghi lựa chọn trong tài liệu.
- [x] Test thành công, ID không tồn tại, ID sai, thiếu token và auth không khả dụng.

## Hoàn thành khi

Endpoint đáp ứng dòng `GET /products/{id}` trong bảng API của kế hoạch.

## Bằng chứng / ghi chú của agent

- Dùng route sẵn có `products/<str:product_id>` và `ProductDetailView.get()`. ID không là số nguyên dương trong giới hạn SQLite trả JSON `400`; ID hợp lệ nhưng không tồn tại trả `404`. GET và DELETE dùng chung `parse_product_id`.
- `manage.py test products.test_detail products.test_delete --verbosity 2`: 8/8 test đạt; `manage.py check`: không có lỗi. Test dùng SQLite in-memory và mock Auth Service.
