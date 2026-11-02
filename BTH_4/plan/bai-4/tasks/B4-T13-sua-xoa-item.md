# B4-T13 — PUT và DELETE order_items

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T04, B4-T06, B4-T12.

## Mục tiêu và phạm vi

Hoàn thiện PUT /order_items/{id} và DELETE /order_items/{id}. Phạm vi: item_detail.py, tests/test_item_update.py, tests/test_item_delete.py.

## Các bước

- [x] PUT chỉ nhận quantity nguyên dương; giữ order_id/product_id/product_name/unit_price.
- [x] PUT kiểm tra Product còn tồn tại và tồn hiện tại đủ số lượng mới; tính total_price theo giá snapshot cũ.
- [x] DELETE chỉ đơn pending, chặn xóa item cuối bằng 409; không cần gọi Product.
- [x] Cả hai thao tác tính lại order.total_amount và updated_at cùng transaction, kiểm tra lại trạng thái lúc ghi.
- [x] PUT trả 200 item; DELETE trả 204 body rỗng; ID sai/không tồn tại -> 400/404.

## Nghiệm thu

- [x] Test tăng/giảm quantity, thiếu tồn, giá Product đã đổi, product đã bị xóa và overflow.
- [x] Test quantity 0/âm/sai kiểu, field bất biến và field tính toán bị gửi lên.
- [x] Test xóa một dòng trong đơn nhiều dòng, chặn dòng cuối và chặn sửa/xóa ở trạng thái cuối.
- [x] Test rollback giữ item/tổng nhất quán; xóa không phụ thuộc Product; JWT bắt buộc.

## Bằng chứng

Verified 2026-11-02 (Asia/Saigon), Order Service Python 3.14 virtual environment.

- `.venv/Scripts/python.exe manage.py test orders.tests.test_api orders.tests.test_models orders.tests.test_serializers orders.tests.test_configuration`: 37 tests passed, including 21 API tests.
- API tests use actual Django routing/serializers/local ORM and mocked Auth HTTP/Product boundary; live three-service verification belongs to T16.
- Coverage includes all ten authenticated endpoints and lifecycle, 3x3 status matrix, snapshot totals, cascade/empty 204 responses, stock conflicts, validation and missing IDs.
- Root domain/concurrency tests additionally verify rollback and competing writes; evidence is recorded separately in T06/T14.
