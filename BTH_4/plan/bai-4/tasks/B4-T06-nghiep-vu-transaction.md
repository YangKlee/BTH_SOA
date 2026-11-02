# B4-T06 — Nghiệp vụ, tính tiền và transaction

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T02, B4-T03, B4-T05.

## Mục tiêu và phạm vi

Đặt nghiệp vụ dùng chung trong orders/services.py, để views chỉ điều phối request/response. Phạm vi gồm helper tiền/trạng thái/lỗi, cấu hình transaction nếu cần và tests/test_services.py.

## Các bước

- [x] Tính total_price, total_amount bằng Decimal; chặn overflow Decimal(10,2) ở cả dòng và tổng.
- [x] Thực hiện create order + nested items nguyên tử; một item lỗi không để lại bản ghi nửa chừng.
- [x] Thực hiện add/update/delete item và tính lại tổng trong cùng transaction; cập nhật order.updated_at.
- [x] Áp dụng một dòng/product, đơn không rỗng, chỉ pending sửa item; giữ snapshot khi đổi quantity.
- [x] Áp dụng bảng chuyển trạng thái; completed kiểm tra lại tồn; cùng trạng thái là no-op.
- [x] HTTP nằm ngoài transaction; vào transaction phải đọc lại trạng thái và nội dung order/item trước khi commit.
- [x] Chọn cơ chế serialize ghi thực sự hiệu lực trên SQLite; không dựa vào select_for_update đơn lẻ. Nếu dùng IMMEDIATE, giới hạn transaction chỉ quanh phần DB, không bao quanh network request.
- [x] Ánh xạ conflict/DB lock được dự kiến sang lỗi rõ ràng, bảo đảm rollback và không tự retry tạo đơn.

## Nghiệm thu

- [x] Test tiền chính xác, giá 0, biên overflow, snapshot, tổng sau mỗi mutation và updated_at.
- [x] Test rollback lỗi giữa chừng; lỗi dependency không ghi dở DB.
- [x] Test hai DB connection cạnh tranh item/status bảo toàn tổng và quy tắc pending; lỗi khóa không trả traceback/500 ngoài kiểm soát.
- [x] Không tuyên bố transaction SQLite bao trùm hoặc khóa được tồn kho Product.

## Bằng chứng

Ngày 02/11/2026: hoàn thành orders/services.py và errors.py. SQLite dùng transaction_mode=IMMEDIATE, timeout 3 giây; HTTP luôn ở ngoài transaction. Đọc lại trạng thái và so sánh chữ ký items sau khi kiểm tra tồn để tránh chốt đơn trên dữ liệu đã thay đổi. Lỗi DB bận trả 503, không tự retry tạo đơn.

Chạy với ORDER_TEST_DB trỏ đến file SQLite tạm duy nhất:

```powershell
& ./.venv/Scripts/python.exe manage.py test orders.tests.test_services orders.tests.test_concurrency --verbosity 1 --noinput
```

Kết quả: 20 tests pass, không skip (16 service tests và 4 test cạnh tranh với hai connection/file DB thật). Bao phủ rollback, snapshot, tiền Decimal, hai request thêm cùng/khác sản phẩm, race hủy đơn/sửa item và DB lock timeout. Suite tổng hợp sau đó có 82 tests pass. Xem [báo cáo](../ket-qua-kiem-thu.md).
