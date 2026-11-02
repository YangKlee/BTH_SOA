# B4-T07 — POST /orders

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T03, B4-T04, B4-T06.

## Mục tiêu và phạm vi

Tạo đơn kèm items qua một request. Phạm vi: orders/views/order_collection.py, config/urls.py, tests/test_order_create.py.

## Các bước

- [x] Khai báo POST /orders không slash cuối, validate bằng serializer và gọi nghiệp vụ tạo đơn.
- [x] Kiểm tra mọi sản phẩm/tồn kho qua Product, không nhận đơn rỗng hoặc product trùng.
- [x] Mặc định pending; snapshot name/price, tính tổng server, ghi toàn bộ nguyên tử.
- [x] Trả 201, body order kèm items và Location /orders/{id}; ánh xạ lỗi theo plan.

## Nghiệm thu

- [x] Tạo đơn nhiều sản phẩm thành công; giá/tên/tổng đúng dữ liệu Product, DB khớp response.
- [x] Thiếu tồn ở item sau, product không tồn tại, dependency lỗi hoặc tổng overflow đều không để lại order/item.
- [x] Client giả mạo total_amount/unit_price/status hoặc gửi payload thiếu bị từ chối.
- [x] Không token -> 401; token hợp lệ được chuyển tiếp tới Product; không cập nhật quantity trong Product.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `.venv/Scripts/python.exe manage.py test orders.tests.test_api orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 37 tests passed, including 21 API tests.
- API tests use actual Django routing/serializers/local ORM and mocked Auth HTTP/Product boundary; live three-service verification belongs to T16.
- Coverage includes all ten authenticated endpoints and lifecycle, 3x3 status matrix, snapshot totals, cascade/empty 204 responses, stock conflicts, validation and missing IDs.
- Root domain/concurrency tests additionally verify rollback and competing writes; evidence is recorded separately in T06/T14.
