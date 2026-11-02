# B4-T12 — POST order_items

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T04, B4-T06, B4-T07.

## Mục tiêu và phạm vi

POST /order_items thêm một sản phẩm vào đơn pending. Phạm vi: item_collection.py, tests/test_item_create.py.

## Các bước

- [x] Nhận order_id, product_id, quantity; order không tồn tại -> 404.
- [x] Kiểm tra pending và product chưa có trong đơn; dòng trùng đã tồn tại -> 409.
- [x] Lấy snapshot từ Product, kiểm tra tồn và giới hạn tiền.
- [x] Tạo item, tính lại order.total_amount và updated_at cùng transaction; kiểm tra lại status/duplicate lúc ghi.
- [x] Trả 201 item cùng Location /order_items/{id}.

## Nghiệm thu

- [x] Thêm item thành công làm tổng đơn tăng chính xác; không ảnh hưởng snapshot các dòng cũ.
- [x] Đơn completed/cancelled, thiếu tồn, duplicate, overflow hoặc dependency lỗi không tạo item hoặc đổi tổng.
- [x] Test race hai request thêm cùng product: không có hai dòng trùng, không sai tổng.
- [x] Từ chối giá/tên/tổng do client gửi; JWT bắt buộc.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `.venv/Scripts/python.exe manage.py test orders.tests.test_api orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 37 tests passed, including 21 API tests.
- API tests use actual Django routing/serializers/local ORM and mocked Auth HTTP/Product boundary; live three-service verification belongs to T16.
- Coverage includes all ten authenticated endpoints and lifecycle, 3x3 status matrix, snapshot totals, cascade/empty 204 responses, stock conflicts, validation and missing IDs.
- Root domain/concurrency tests additionally verify rollback and competing writes; evidence is recorded separately in T06/T14.
