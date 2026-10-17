# T12 — Kiểm thử tích hợp hai service

**Kết quả duy nhất:** có bằng chứng luồng login và CRUD chạy thật qua hai service, mỗi service dùng DB riêng.

**Phụ thuộc:** T01–T11 và T13 tạo `database/DB_ProjectManagerment.db`. **Phạm vi:** chạy thử, sửa lỗi tích hợp nếu có, ghi kết quả.

## Checklist

- [x] Kiểm tra file DB bài 2 do T13 tạo tồn tại, bảng `Users` đúng schema và có tài khoản thử hợp lệ; không ghi mật khẩu/token thật vào tài liệu.
- [x] Chạy Auth Service ở 8000 và Product Service ở 8001, migration sản phẩm hoàn tất.
- [x] Gọi login thật lấy access JWT; xác minh token qua `GET /token/verify/`.
- [x] Chạy theo thứ tự: tạo → danh sách → chi tiết → cập nhật → xóa; kiểm tra status/body và DB sản phẩm.
- [x] Kiểm tra thiếu/sai token bị `401`; dừng Auth Service rồi kiểm tra Product Service trả `503`.
- [x] Xác nhận DB sản phẩm và DB người dùng là hai file khác nhau; ghi lệnh, kết quả và mọi lỗi đã sửa.
- [x] Chạy toàn bộ test tự động liên quan và cập nhật README nếu kết quả thật khác hướng dẫn.

## Hoàn thành khi

Có báo cáo ngắn với bằng chứng chạy thành công và không còn checklist chưa đạt.

## Bằng chứng / ghi chú của agent

- DB Auth do T13 tạo có bảng `Users` với 12 cột đúng model (`UserId`, `LastName`, `FirstName`, `Gender`, `DateOfBirth`, `Password`, `Email`, `Phone`, `Role`, `Status`, `CreatedAt`, `UpdatedAt`) và một tài khoản demo đăng nhập thành công. Credential và JWT chỉ được đọc trong tiến trình kiểm thử, không ghi ra log/tài liệu.
- Chạy `manage.py runserver 127.0.0.1:8000 --noreload` và `manage.py runserver 127.0.0.1:8001 --noreload`; Product migration `0001_initial` đã áp dụng. Smoke test HTTP thật: `POST /login/` → `200`, `GET /token/verify/` → `200`, `POST /products` → `201` với `Location`, `GET /products` → `200`, `GET /products/{id}` → `200`, `PUT /products/{id}` → `200`, `DELETE /products/{id}` → `204` body rỗng, GET lại → `404`.
- SQL trực tiếp xác nhận bản ghi xuất hiện sau POST, tên đổi sau PUT, rồi số dòng DB sản phẩm trở về ban đầu sau DELETE. Số dòng `Users` không đổi. Hai đường dẫn DB là hai file khác nhau; DB Auth chỉ có bảng `Users` trong hai bảng nghiệp vụ, DB Product chỉ có bảng `products`.
- Qua HTTP thật: thiếu Bearer → `401`; access JWT sai với Auth Service đang chạy → `401`; dừng Auth Service rồi gửi Bearer → `503`. Đã dừng cả hai server sau kiểm tra.
- Chạy lại `manage.py test --verbosity 1`: Auth 7/7, Product 41/41. `manage.py check` ở cả hai service: không có lỗi. Kết quả phù hợp README hiện tại nên không cần sửa hướng dẫn. Không phát hiện lỗi tích hợp cần sửa.
