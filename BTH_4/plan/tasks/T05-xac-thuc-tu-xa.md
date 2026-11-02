# T05 — Xác thực từ xa ở Product Service

**Kết quả duy nhất:** lớp xác thực của Product Service gọi Auth Service để xác minh mỗi access JWT.

**Phụ thuộc:** T01, T02. **Phạm vi:** authentication/permission, cấu hình liên quan và test bằng mock HTTP; chưa thêm CRUD.

## Checklist

- [x] Đọc `Authorization: Bearer <token>` và gọi `GET {AUTH_SERVICE_URL}/token/verify/` cho mỗi request được bảo vệ.
- [x] Chỉ chấp nhận `200` có JSON danh tính đúng hợp đồng; không dùng DB hoặc khóa ký của Auth Service.
- [x] Thiếu/sai Bearer hoặc Auth trả `401` thì Product Service trả `401` với `detail`.
- [x] Timeout, mất kết nối, Auth trả `5xx` hoặc payload không hợp lệ thì trả `503`, không cho qua.
- [x] Đặt timeout cấu hình được; không ghi token vào log hay đưa token vào URL.
- [x] Test mock cho các nhánh `200`, `401`, timeout, lỗi kết nối, `5xx` và payload sai.

## Hoàn thành khi

Có thể gắn lớp xác thực vào cả năm endpoint và kiểm tra hành vi bằng test không cần DB bài 2 thật.

## Bằng chứng / ghi chú của agent

- Lớp `RemoteJWTAuthentication` dùng `urllib` của thư viện chuẩn, gửi Bearer qua header đến `/token/verify/` cho mỗi request; DRF mặc định yêu cầu `IsAuthenticated`.
- `manage.py test products.test_authentication --verbosity 2`: 6/6 test đạt, mock HTTP và không dùng DB thật.
- `manage.py check`: không có lỗi.
