# B4-T14 — Kiểm thử tổng hợp và hồi quy

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T07 đến B4-T13.

## Mục tiêu và phạm vi

Kiểm chứng hành vi xuyên tính năng và bổ sung khoảng trống các task trước. Phạm vi: tests/ của Order và báo cáo kết quả; chỉ sửa code khi có lỗi được phát hiện.

## Các bước

- [x] Lập ma trận đủ 10 API: thành công, không token/token lỗi, ID/payload lỗi phù hợp.
- [x] Chạy vòng đời tạo -> thêm/sửa/xóa item -> chốt/hủy -> xóa order; kiểm tra snapshot và tổng sau từng bước.
- [x] Kiểm tra Auth/Product timeout, mạng lỗi, JSON sai, thiếu schema, product 404 và token hết hạn giữa các lần gọi.
- [x] Test create nhiều item thất bại ở dòng sau; overflow tổng dù mỗi dòng hợp lệ; không có dữ liệu dở dang.
- [x] Chạy test cạnh tranh với DB file test và hai connection thật; không dùng in-memory hoặc mock lock để tuyên bố đã kiểm chứng SQLite concurrency.
- [x] Kiểm tra 405 cho method ngoài hợp đồng, 204 không body, thứ tự array và không vô tình thêm slash bắt buộc.
- [x] Chạy manage.py check, kiểm tra migration và toàn bộ test Order; chạy lại test Auth/Product trong đúng môi trường của chúng.

## Nghiệm thu

- [x] Các test liên quan pass, có lệnh/kết quả thực tế và số test đã chạy.
- [x] Không ghi DB nghiệp vụ thật, không lộ credential/token; không bỏ test thất bại bằng skip không giải thích.
- [x] Phân biệt unit/mock integration đã pass với smoke 3 service thật ở T16.
- [x] Nếu dependency/runtime không sẵn, ghi chính xác điều kiện thiếu và xử lý trước khi tuyên bố hoàn thành.

## Bằng chứng

2026-11-02: Order full suite passed 82 tests with ORDER_TEST_DB pointing to a unique temporary file (no skips), including 4 real SQLite two-connection concurrency tests. manage.py check clean; makemigrations --check --dry-run found no changes. Agent docs_smoke ran Auth regression (7 pass) and Product check/regression (41 pass). Commands and requirement mapping are recorded in ../ket-qua-kiem-thu.md. Unit tests use isolated DBs/mocked transport; actual runtime verification is separate in T16.
