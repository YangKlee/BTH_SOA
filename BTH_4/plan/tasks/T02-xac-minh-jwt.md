# T02 — Endpoint xác minh JWT ở Auth Service

**Kết quả duy nhất:** Auth Service có `GET /token/verify/` để xác minh access JWT cho service khác.

**Phụ thuộc:** Không. **Phạm vi:** `services/auth-service/authentication/`, `services/auth-service/config/urls.py` và test liên quan. Giữ nguyên login/refresh.

## Checklist

- [x] Thêm route `GET /token/verify/` dùng `UsersJWTAuthentication` và yêu cầu đăng nhập.
- [x] Trả `200` với `user_id`, `email`, `role` từ user đã xác thực; không trả thông tin nhạy cảm.
- [x] Thiếu Bearer, access token sai/hết hạn, refresh token hoặc user không còn tồn tại đều bị từ chối bằng `401`.
- [x] Viết/chạy test cho thành công và các trường hợp từ chối bằng user fixture hoặc mock, không phụ thuộc DB bài 2 thật.
- [x] Chạy kiểm tra Django; xác nhận `/login/` và `/token/refresh/` vẫn hoạt động theo hợp đồng cũ.

## Hoàn thành khi

Endpoint có thể được Product Service gọi với cùng header Bearer mà client gửi; không cần chia sẻ khóa ký hoặc DB cho Product Service.

## Bằng chứng / ghi chú của agent

- Chuyển `authentication/models.py` từ UTF-16 LE sang UTF-8, không đổi định nghĩa model. Python không thể import file gốc vì có null byte.
- Trong môi trường ảo Python 3.14 tạm, cài từ `requirements.txt`: `manage.py test authentication --verbosity 2` đạt 7/7 test, dùng mock và không cần DB thật.
- `manage.py check`: `System check identified no issues (0 silenced)`.
