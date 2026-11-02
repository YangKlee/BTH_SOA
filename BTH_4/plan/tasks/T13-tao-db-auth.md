# T13 — Tạo DB người dùng riêng cho bài 2

**Kết quả duy nhất:** Auth Service có SQLite riêng `database/DB_ProjectManagerment.db`, đúng schema `Users` hiện có và một tài khoản demo đăng nhập được.

**Phụ thuộc:** T02. **Phạm vi:** mã khởi tạo DB có thể chạy lại, DB cục bộ và hướng dẫn tối thiểu; không sửa Product Service.

## Checklist

- [x] Tạo lệnh/script khởi tạo bảng `Users` theo model `authentication.models.Users` mà không thay đổi cấu trúc đã dùng ở bài 2.
- [x] Lệnh chạy lại an toàn: không xóa DB hay ghi đè tài khoản đã có; dùng DB đúng đường dẫn trong `config/settings.py`.
- [x] Tạo một tài khoản demo bằng mật khẩu băm Django; mật khẩu sinh ngẫu nhiên hoặc do biến môi trường cung cấp, không hardcode vào source/test/documentation.
- [x] Giữ thông tin đăng nhập demo tại tệp cục bộ bị Git ignore, chỉ để người dùng chạy thử; không ghi mật khẩu/token vào checklist hoặc log.
- [x] Kiểm tra schema/tài khoản và test login thật ở cổng 8000 hoặc qua Django client với DB cục bộ.
- [x] Cập nhật README: cách khởi tạo DB/tạo tài khoản demo, nơi lấy thông tin đăng nhập và cách chạy lại an toàn.
- [x] Đánh dấu checklist, ghi lệnh và kết quả kiểm tra nhưng không ghi credential.

## Hoàn thành khi

Auth Service có DB riêng và có thể đăng nhập bằng tài khoản demo để T12 kiểm tra xuyên hai service.

## Bằng chứng / ghi chú của agent

- Thêm command `services/auth-service/authentication/management/commands/init_demo_auth_db.py`. Command lấy DB path từ Django settings, dùng schema editor tạo đúng model `Users` unmanaged nếu chưa có, kiểm tra cột khi bảng đã có, không xóa/ghi đè dữ liệu cũ. Tạo đúng một tài khoản demo với `secrets.token_urlsafe(24)` và `make_password`; credential JSON chỉ ghi vào `database/auth_demo_credentials.txt`.
- Trong `services/auth-service`, chạy `venv/Scripts/python.exe manage.py init_demo_auth_db` hai lần: lần đầu tạo bảng và một tài khoản; lần hai báo không thay đổi. `manage.py check` đạt 0 lỗi.
- Introspection DB xác nhận 12 cột của `Users`, `Email` và `Phone` unique, số bản ghi demo bằng 1. Kiểm tra bằng Django client với DB cục bộ: `POST /login/` trả `200`, dùng access token gọi `GET /token/verify/` trả `200`; mật khẩu lưu trong DB là hash Django, khác mật khẩu thử. Không in credential/token trong lệnh hoặc kết quả.
- `venv/Scripts/python.exe manage.py test authentication`: 7/7 đạt. `git check-ignore -v` xác nhận cả DB Auth và `auth_demo_credentials.txt` được ignore bởi `database/.gitignore`.
- README đã cập nhật lệnh khởi tạo/chạy lại và cách đọc credential demo cục bộ. Không thay đổi Product Service hoặc DB sản phẩm.
