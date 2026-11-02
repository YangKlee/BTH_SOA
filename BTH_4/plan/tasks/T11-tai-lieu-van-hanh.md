# T11 — Hướng dẫn chạy và gọi API

**Kết quả duy nhất:** README giúp người khác tự chạy và thử hai service.

**Phụ thuộc:** T01–T10. **Phạm vi:** README và tệp ví dụ cấu hình cần thiết; không thay đổi nghiệp vụ.

## Checklist

- [x] Ghi phiên bản Python và lệnh cài dependencies cho từng service.
- [x] Ghi rõ vị trí DB người dùng bài 2 do người yêu cầu bổ sung và DB sản phẩm do migration tạo.
- [x] Ghi lệnh migration, chạy Auth Service ở 8000 và Product Service ở 8001, cấu hình `AUTH_SERVICE_URL`/timeout.
- [x] Có ví dụ `curl` login lấy access JWT rồi gọi đủ năm API với payload đúng schema.
- [x] Giải thích mã `400`, `401`, `404`, `503`, format giá, quy tắc `PUT`, xóa hẳn và cách chạy test.
- [x] Tự làm theo README trong môi trường sạch hoặc kiểm tra từng lệnh với môi trường hiện có; ghi giới hạn nếu chưa có DB bài 2.

## Hoàn thành khi

Người đọc không cần xem mã nguồn để cài đặt, khởi chạy và thử API.

## Bằng chứng / ghi chú của agent

- Tạo `README.md` ở gốc repo bằng tiếng Việt, dùng PowerShell và `curl.exe`, có hướng dẫn cài Python 3.14/venv/dependencies từng service, migration chỉ cho Product Service, chạy 8000/8001, biến môi trường, login/verify và đủ năm API CRUD.
- Đối chiếu các route `services/auth-service/config/urls.py`, `services/product-service/config/urls.py`, payload login tại `authentication/views.py`, response CRUD tại `products/collection.py` và `products/detail.py`; lệnh test/migration dùng đường dẫn thực tế.
- Trong `services/auth-service`, `venv/Scripts/python.exe manage.py check` đạt 0 lỗi và `venv/Scripts/python.exe manage.py test authentication` đạt 7/7. Trong `services/product-service`, `.venv/Scripts/python.exe manage.py check` đạt 0 lỗi và `.venv/Scripts/python.exe manage.py test products` đạt 41/41.
- File `database/DB_ProjectManagerment.db` chưa tồn tại, nên không thể chạy login/verify/CRUD end-to-end thật; README nêu rõ điều kiện này và ví dụ `curl.exe` chưa được chạy với tài khoản thật. Venv Auth hiện có tên `venv`; README hướng dẫn tạo `.venv` mới và có ghi cách thay đường dẫn nếu dùng venv hiện tại.
