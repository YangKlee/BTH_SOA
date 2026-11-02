# B4-T10 — DELETE orders và cascade

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T04, B4-T06, B4-T07.

## Mục tiêu và phạm vi

DELETE /orders/{id} xóa order và items nguyên tử. Phạm vi: order_detail.py, tests/test_order_delete.py.

## Các bước

- [x] Xóa cứng ở cả pending/completed/cancelled theo quyết định của plan.
- [x] Dùng FK cascade trong transaction; không gọi Product, không hoàn tồn.
- [x] Thành công 204 body rỗng; ID sai 400; đơn không tồn tại hoặc xóa lần hai -> 404.

## Nghiệm thu

- [x] Kiểm tra order và items liên quan biến mất, đơn/items khác giữ nguyên.
- [x] Test ở cả ba trạng thái và khi Product unavailable.
- [x] Thiếu/sai token không xóa dữ liệu; response 204 không chứa JSON null hoặc thông báo.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `.venv/Scripts/python.exe manage.py test orders.tests.test_api orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 37 tests passed, including 21 API tests.
- API tests use actual Django routing/serializers/local ORM and mocked Auth HTTP/Product boundary; live three-service verification belongs to T16.
- Coverage includes all ten authenticated endpoints and lifecycle, 3x3 status matrix, snapshot totals, cascade/empty 204 responses, stock conflicts, validation and missing IDs.
- Root domain/concurrency tests additionally verify rollback and competing writes; evidence is recorded separately in T06/T14.
