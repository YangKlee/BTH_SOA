# B4-T15 — Tài liệu và script demo

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T07 đến B4-T14.

## Mục tiêu và phạm vi

Có hướng dẫn đủ để chạy và demo từ repo. Phạm vi: README.md, .env.example Order, scripts/smoke-order-service.ps1; không xóa hướng dẫn Auth/Product đang cần dùng.

## Các bước

- [x] Cập nhật README sang bối cảnh bài 4: 3 service, 3 DB, môi trường riêng và thứ tự khởi tạo/chạy.
- [x] Ghi đúng lệnh PowerShell tạo venv/cài requirements/migrate Order/start 8000–8002; không giả định python alias dùng được.
- [x] Bảng đủ 10 API, payload/response mẫu, status codes, snapshot giá, transition và giới hạn chỉ kiểm tra tồn.
- [x] Script nhận URL và credential qua cấu hình local phù hợp, login lấy token, tạo dữ liệu demo riêng và kiểm tra HTTP status.
- [x] Demo ít nhất create/read/status/delete order và create/read/update/delete items, cộng thiếu tồn và token sai.
- [x] Dọn đúng dữ liệu do script tạo bằng ID theo dõi trong lần chạy; không truncate DB, không in token/password.

## Nghiệm thu

- [x] Lệnh và ví dụ bám implementation thực tế, JSON/quote dùng được trên PowerShell.
- [x] Không hardcode product ID hoặc credential cá nhân; không phụ thuộc dữ liệu demo còn lại từ lần chạy trước.
- [x] Script có cleanup kiểm soát; chạy thành công thực tế được xác nhận tại T16.
- [x] README nói rõ .env.example là mẫu và snapshot/không trừ kho là quyết định đã duyệt.

## Bằng chứng

Ngày kiểm chứng: 2026-11-02 (Asia/Saigon).

- README đã cập nhật cho ba service, giữ hướng dẫn Auth/Product kế thừa; bổ sung cài đặt/migration Order, 10 API, luật nghiệp vụ, request/response mẫu, lỗi, cấu hình và các lệnh test.
- Script `scripts/smoke-order-service.ps1` dùng HttpClient, tương thích Windows PowerShell 5.1; AST parser không có lỗi. Kiểm tra local strict-mode với JSON array rỗng/một/nhiều phần tử đã pass sau khi xử lý khác biệt ConvertFrom-Json của PowerShell 5.1.
- Root chạy script tương đương `& .\scripts\smoke-order-service.ps1 -EvidencePath .\plan\bai-4\smoke-result.json` qua Auth 8000, Product 8001 và Order 8002 thật: **62 kiểm tra PASS**, gồm đủ 10 API. Evidence tại [../smoke-result.json](../smoke-result.json); `cleanup_errors` rỗng, chỉ dọn ID tạo trong lần chạy.
- Hồi quy do agent docs chạy: Auth `venv\Scripts\python.exe manage.py test authentication --noinput` **7 tests OK**; Product `.venv\Scripts\python.exe manage.py check` không có lỗi, `manage.py test products --noinput` **41 tests OK**.
- Root xác nhận bộ Order **82 tests OK, không skip** khi dùng ORDER_TEST_DB trỏ DB file thử riêng để kiểm chứng cạnh tranh SQLite.
- Không lưu credential/token vào script, README hoặc evidence; script không tự khởi chạy/dừng service và không thay đổi dữ liệu có sẵn.
