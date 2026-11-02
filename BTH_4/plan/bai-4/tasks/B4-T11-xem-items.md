# B4-T11 — GET danh sách và chi tiết items

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T02, B4-T03, B4-T04.

## Mục tiêu và phạm vi

GET /order_items và GET /order_items/{id}. Phạm vi: item_collection.py, item_detail.py, config/urls.py, tests/test_item_read.py.

## Các bước

- [x] Danh sách toàn bộ items theo id tăng dần, DB rỗng trả [].
- [x] Chi tiết gồm đúng 7 trường đã quy định; tiền là chuỗi Decimal.
- [x] ID sai 400, không tồn tại 404; không gọi Product lúc đọc snapshot.

## Nghiệm thu

- [x] Test nhiều order, danh sách đầy đủ, chi tiết đúng order_id và snapshot.
- [x] Tên/giá đã lưu không đổi dù Product thay đổi hoặc bị xóa.
- [x] JWT bắt buộc cho cả hai endpoint; Product unavailable không làm GET thất bại.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `.venv/Scripts/python.exe manage.py test orders.tests.test_api orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 37 tests passed, including 21 API tests.
- API tests use actual Django routing/serializers/local ORM and mocked Auth HTTP/Product boundary; live three-service verification belongs to T16.
- Coverage includes all ten authenticated endpoints and lifecycle, 3x3 status matrix, snapshot totals, cascade/empty 204 responses, stock conflicts, validation and missing IDs.
- Root domain/concurrency tests additionally verify rollback and competing writes; evidence is recorded separately in T06/T14.
