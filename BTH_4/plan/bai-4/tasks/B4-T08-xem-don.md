# B4-T08 — GET danh sách và chi tiết orders

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T02, B4-T03, B4-T04.

## Mục tiêu và phạm vi

Hoàn thiện GET /orders và GET /orders/{id}. Phạm vi: order_collection.py, order_detail.py, config/urls.py, tests/test_order_read.py.

## Các bước

- [x] Danh sách trả array theo id tăng dần, trường order không nhúng items; DB rỗng trả [].
- [x] Chi tiết trả order kèm items theo id tăng dần; dùng prefetch phù hợp để tránh truy vấn theo từng item.
- [x] Kiểm tra ID: sai định dạng 400, không tồn tại 404.
- [x] Lấy snapshot đã lưu; không gọi Product để dựng lại tên/giá hoặc kiểm tra tồn khi đọc.

## Nghiệm thu

- [x] Test rỗng/nhiều đơn, nested items, sắp xếp, Decimal/timestamps và ID lỗi.
- [x] Đơn vẫn đọc được sau khi giá/tên Product đổi hoặc Product ngừng hoạt động.
- [x] Hai endpoint yêu cầu JWT; không thêm filter owner/role ngoài plan.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `.venv/Scripts/python.exe manage.py test orders.tests.test_api orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 37 tests passed, including 21 API tests.
- API tests use actual Django routing/serializers/local ORM and mocked Auth HTTP/Product boundary; live three-service verification belongs to T16.
- Coverage includes all ten authenticated endpoints and lifecycle, 3x3 status matrix, snapshot totals, cascade/empty 204 responses, stock conflicts, validation and missing IDs.
- Root domain/concurrency tests additionally verify rollback and competing writes; evidence is recorded separately in T06/T14.
