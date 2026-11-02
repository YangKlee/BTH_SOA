# B4-T04 — Xác thực qua Auth Service

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T01.

## Mục tiêu và phạm vi

Tất cả API Order cần access JWT được Auth xác minh. Phạm vi: orders/authentication.py, config/settings.py, tests/test_authentication.py. Tham khảo cách Product đang làm nhưng không import chéo service.

## Các bước

- [x] Parse Bearer token; gọi GET {AUTH_SERVICE_URL}/token/verify/ với timeout cấu hình.
- [x] Kiểm tra phản hồi user_id/email/role đúng hợp đồng Auth hiện có; tạo request.user và giữ raw token trong request.auth để gọi Product.
- [x] Thiếu/header sai/token lỗi/upstream 401 -> 401 và WWW-Authenticate Bearer.
- [x] Timeout, mạng lỗi, upstream khác hợp đồng hoặc JSON/schema sai -> 503 có thông báo kiểm soát.
- [x] Đặt authentication/permission mặc định cho toàn bộ API; không thêm role/owner rule ngoài plan.

## Nghiệm thu

- [x] Mock test xác thực thành công, token thiếu/hết hạn, lỗi upstream và payload sai.
- [x] Không dùng khóa JWT của Auth, không đọc Users DB, không ghi token vào log.
- [x] Các task API sau phải kiểm tra endpoint không bỏ qua authentication mặc định.

## Bằng chứng

Ngày kiểm chứng: 2026-11-02. Chạy từ `services/order-service`:

```powershell
& ./.venv/Scripts/python.exe manage.py test orders.tests.test_authentication orders.tests.test_product_client --verbosity 2
```

Kết quả ban đầu: 18 tests pass (9 tests Auth/transport, 9 tests Product), không cần DB, system check không có lỗi. ProtectedView trong test dùng chính cấu hình authentication mặc định. Transport dùng no-redirect opener, không chuyển tiếp Bearer qua redirect; test xác nhận từ chối chuyển hướng.

Sau khi đủ API, chạy tiếp:

```powershell
& ./.venv/Scripts/python.exe manage.py test orders.tests.test_api_security orders.tests.test_authentication orders.tests.test_product_client --verbosity 2
```

Kết quả: **25 tests pass**, gồm 7 tests API security/propagation. Các subtest đã gọi đủ 10 thao tác API với 5 tình huống: thiếu token, header sai, token hết hạn, Auth timeout và identity response sai. Toàn bộ bị chặn trước nghiệp vụ, DB không đổi và không gọi Product. Kiểm chứng thêm luồng HTTP client thật (transport được mock) tạo đơn -> thêm item -> sửa quantity -> completed: Bearer được chuyển tiếp, mọi HTTP nằm ngoài atomic DB và giá snapshot giữ nguyên dù giá Product đổi. Product trả 401 giữa request vẫn trả 401 và không ghi đơn dở dang.
