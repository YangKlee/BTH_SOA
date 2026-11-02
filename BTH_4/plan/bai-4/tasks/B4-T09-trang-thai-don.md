# B4-T09 — PUT trạng thái orders

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T04, B4-T06, B4-T07.

## Mục tiêu và phạm vi

PUT /orders/{id} chỉ cập nhật trạng thái. Phạm vi: order_detail.py, service layer nếu cần, tests/test_order_status.py.

## Các bước

- [x] Payload chỉ có status; giá trị lạ -> 400, field khác -> 400.
- [x] pending -> completed hoặc cancelled; trạng thái cuối -> trạng thái khác trả 409.
- [x] completed kiểm tra lại tồn của tất cả items trước khi đổi trạng thái; thiếu tồn giữ nguyên pending.
- [x] Gửi cùng status -> 200 không thay dữ liệu/timestamp và không gọi Product.
- [x] Cancel không hoàn kho; trả 200 order kèm items, không thay giá/tổng/customer.

## Nghiệm thu

- [x] Test toàn bộ ma trận 3 x 3 trạng thái; no-op không có tác dụng phụ.
- [x] Test thiếu tồn, timeout và token hết hạn khi complete; không cập nhật một phần.
- [x] Test race với thao tác item theo cơ chế transaction T06; ID lỗi và JWT lỗi đúng status.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `.venv/Scripts/python.exe manage.py test orders.tests.test_api orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 37 tests passed, including 21 API tests.
- API tests use actual Django routing/serializers/local ORM and mocked Auth HTTP/Product boundary; live three-service verification belongs to T16.
- Coverage includes all ten authenticated endpoints and lifecycle, 3x3 status matrix, snapshot totals, cascade/empty 204 responses, stock conflicts, validation and missing IDs.
- Root domain/concurrency tests additionally verify rollback and competing writes; evidence is recorded separately in T06/T14.
