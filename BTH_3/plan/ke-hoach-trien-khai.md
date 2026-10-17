# Kế hoạch triển khai Product Service

## 1. Căn cứ và quyết định đã chốt

Nguồn yêu cầu: [`tutorial.md`](../tutorial.md) và các câu trả lời của người yêu cầu ngày 17/10/2026.

| Nội dung | Quyết định |
| --- | --- |
| Mục tiêu | Một Product Service CRUD độc lập theo SOA |
| Công nghệ | Python, Django REST Framework như [`services/auth-service/`](../services/auth-service/) |
| Cơ sở dữ liệu | SQLite riêng cho Product Service; không đọc/ghi DB của Auth Service |
| Cổng phát triển | Auth Service `8000`, Product Service `8001` |
| Xác thực | Client đăng nhập tại Auth Service, gửi access JWT dạng `Authorization: Bearer <token>`; Product Service gọi API xác minh mới của Auth Service cho mỗi request |
| Phân quyền | Mọi tài khoản đăng nhập dùng được cả năm API; không phân quyền theo `role` |
| Dữ liệu đầu vào | `name`, `description`, `price`, `quantity` đều bắt buộc; giá và số lượng không âm; cho phép trùng tên |
| Cập nhật | `PUT` yêu cầu đủ bốn trường, thay thế thông tin có thể sửa |
| Xóa | Xóa hẳn khỏi DB |
| Danh sách | Trả toàn bộ sản phẩm, chưa phân trang/tìm kiếm |
| DB người dùng bài 2 | Tạo SQLite riêng `database/DB_ProjectManagerment.db` theo model `Users` hiện có, có tài khoản demo để thử tích hợp |

Phạm vi là API và tài liệu chạy thử, không có giao diện người dùng. Các task triển khai và kết quả kiểm thử được theo dõi tại [`tasks/README.md`](tasks/README.md).

## 2. Hiện trạng mã nguồn

- Workspace hiện có [`services/auth-service/`](../services/auth-service/) với Django 6.1.1, DRF 3.18.1 và Simple JWT 5.5.1.
- Auth Service có `POST /login/`, `POST /token/refresh/`, `GET /token/verify/`, `GET /health/`. Login trả `access` và `refresh`; JWT chứa `user_id`, `email`, `role`.
- [`authentication/authentication.py`](../services/auth-service/authentication/authentication.py) kiểm tra chữ ký/hạn của access JWT và tra bảng `Users`; endpoint xác minh dùng lớp này.
- Auth Service trỏ tới `database/DB_ProjectManagerment.db`. Model `Users` là `managed = False`, nên cần lệnh khởi tạo riêng cho bảng này; Django migration không tự tạo bảng.
- Product Service, test nghiệp vụ và DB Auth riêng đã được tạo trong quá trình triển khai; xem trạng thái từng task và bằng chứng tại [`tasks/README.md`](tasks/README.md).

## 3. Kiến trúc và luồng xác thực

```text
Client -- POST /login/ --------------------> Auth Service :8000
Client <-- access JWT, refresh JWT -------- Auth Service
Client -- Bearer access JWT, /products ----> Product Service :8001
                                      Product Service -- Bearer JWT, GET /token/verify/ --> Auth Service
                                      Product Service <-- 200 hoặc 401 ------------------ Auth Service
Client <-- kết quả sản phẩm hoặc lỗi ------- Product Service

Auth Service --> database/DB_ProjectManagerment.db
Product Service --> database/products.sqlite3
```

### Hợp đồng xác minh giữa hai service

1. Bổ sung `GET /token/verify/` tại Auth Service. Request dùng header `Authorization: Bearer <access JWT>`; không gửi token qua query string.
2. Endpoint dùng `UsersJWTAuthentication` và `IsAuthenticated` hiện có, nên access token phải hợp lệ, chưa hết hạn và `user_id` còn tồn tại trong bảng `Users`. Refresh token không được chấp nhận thay access token.
3. Thành công trả `200` với JSON tối thiểu `{"user_id":"...","email":"...","role":0}` lấy từ user đã xác thực. Thiếu/sai/hết hạn token trả `401`, không trả dữ liệu sản phẩm.
4. Product Service chuyển tiếp header Bearer đến endpoint trên qua URL cấu hình, đặt timeout hữu hạn (đề xuất 3 giây), không lưu hay ghi log JWT.
5. Auth trả `200` thì xử lý API. Auth trả `401` thì Product Service trả `401`. Auth không kết nối được, hết timeout, trả `5xx` hoặc phản hồi không đúng hợp đồng thì Product Service trả `503` với thông điệp trung tính. Không coi lỗi Auth Service là đăng nhập thành công.
6. Product Service không chia sẻ khóa ký JWT và không kết nối cơ sở dữ liệu người dùng. Dữ liệu `role` chỉ phục vụ khả năng mở rộng, chưa dùng để chặn API.

## 4. Mô hình dữ liệu sản phẩm

Tạo bảng `products` bằng Django migration trong **DB riêng** `database/products.sqlite3`.

| Cột | Kiểu/thiết lập | Quy tắc |
| --- | --- | --- |
| `id` | Integer primary key, tự tăng | Do DB cấp; client không ghi |
| `name` | `VARCHAR(255) NOT NULL` | Chuỗi sau khi trim phải có ít nhất một ký tự; tối đa 255 ký tự; không unique |
| `description` | `TEXT NOT NULL` | Chuỗi sau khi trim phải có ít nhất một ký tự |
| `price` | `DECIMAL(10,2) NOT NULL` | Từ `0.00` đến `99999999.99`; tối đa 2 chữ số thập phân; không dùng float để tính/lưu |
| `quantity` | `INT NOT NULL` | Số nguyên từ 0 trở lên; không nhận boolean hoặc số thập phân |
| `created_at` | `TIMESTAMP NOT NULL` | Hệ thống cấp khi tạo; không cho client sửa |
| `updated_at` | `TIMESTAMP NOT NULL` | Hệ thống cấp khi tạo/cập nhật; không cho client sửa |

Dùng múi giờ UTC trong lưu trữ và trả thời gian theo ISO 8601. Ngoài serializer validation, thêm ràng buộc DB cho `price >= 0` và `quantity >= 0`. Hai cột thời gian là read-only trong API. Nếu người dùng gửi `id`, `created_at`, `updated_at` hoặc trường lạ trong `POST`/`PUT`, trả `400` để tránh bỏ qua âm thầm.

## 5. Hợp đồng REST API

Các đường dẫn dùng đúng dạng không có dấu `/` cuối như đề bài. `{id}` là số nguyên dương. Mọi endpoint dưới đây yêu cầu access JWT hợp lệ. Phản hồi là `application/json`, trừ `DELETE` thành công.

### Biểu diễn sản phẩm

```json
{
  "id": 1,
  "name": "Bút bi",
  "description": "Mực xanh",
  "price": "12000.00",
  "quantity": 30,
  "created_at": "2026-10-17T08:00:00Z",
  "updated_at": "2026-10-17T08:00:00Z"
}
```

`price` là chuỗi thập phân trong JSON để giữ chính xác 2 chữ số sau dấu phẩy. `POST`/`PUT` nhận `price` là chuỗi số thập phân; có thể nhận JSON number nếu DRF chuyển đổi chính xác và vẫn kiểm tra tối đa 2 chữ số thập phân. Ví dụ payload:

```json
{
  "name": "Bút bi",
  "description": "Mực xanh",
  "price": "12000.00",
  "quantity": 30
}
```

| API | Xử lý | Thành công | Lỗi chính |
| --- | --- | --- | --- |
| `GET /products` | Lấy tất cả, sắp xếp `id` tăng dần; chưa có dữ liệu trả `[]` | `200` và mảng sản phẩm | `401`, `503` |
| `GET /products/{id}` | Lấy một sản phẩm | `200` và đối tượng sản phẩm | `400` nếu ID không hợp lệ, `404` nếu không có, `401`, `503` |
| `POST /products` | Kiểm tra đủ bốn trường, tạo bản ghi | `201`, đối tượng sản phẩm và header `Location: /products/{id}` | `400`, `401`, `503` |
| `PUT /products/{id}` | Kiểm tra đủ bốn trường, cập nhật bản ghi hiện có; giữ `id`/`created_at` | `200` và đối tượng đã cập nhật | `400`, `404`, `401`, `503` |
| `DELETE /products/{id}` | Xóa hẳn bản ghi hiện có | `204`, body rỗng | `400`, `404`, `401`, `503` |

Chuẩn hóa lỗi xác thực/hạ tầng thành `{"detail":"..."}`; lỗi dữ liệu dùng tên trường để client biết chỗ sửa (theo DRF). URL không khớp mẫu ID số nguyên cũng phải trả JSON `400` hoặc `404` nhất quán và ghi rõ trong README; ưu tiên kiểm tra ID để trả `400`.

## 6. Công việc theo thứ tự triển khai

### Bước 1 — Chuẩn bị cấu hình và cấu trúc dự án

- Tạo `services/product-service/` với `manage.py`, `config/`, app `products/`, `requirements.txt`.
- Khóa phiên bản phụ thuộc tương thích với bài 2; cấu hình `AUTH_SERVICE_URL=http://127.0.0.1:8000`, đường dẫn DB sản phẩm và timeout gọi Auth Service. Ghi lệnh chạy `runserver 8001` trong README; không commit token hay DB chứa dữ liệu cá nhân.
- Tạo thư mục `database/` khi cần; Product Service dùng `database/products.sqlite3`, tách khỏi file người dùng của bài 2.
- Cấu hình DRF và JSON response thống nhất, timezone UTC, kiểm soát debug/secret bằng biến môi trường khi triển khai ngoài máy học tập.

**Đạt khi:** Product Service khởi động được ở cổng 8001, kết nối DB riêng và không cần import module hay model của Auth Service.

### Bước 2 — Bổ sung API xác minh vào Auth Service

- Tạo view `GET /token/verify/` và route tương ứng; dùng lớp xác thực hiện hữu để kiểm tra token và user còn tồn tại.
- Trả đúng JSON `user_id`, `email`, `role`; bảo đảm thiếu token, token sai, refresh token và token hết hạn nhận `401`.
- Giữ hành vi của `/login/` và `/token/refresh/` như hiện tại.

**Đạt khi:** token access lấy từ login xác minh được; các token không hợp lệ bị từ chối; API không mở quyền khi thiếu header.

### Bước 3 — Tạo bảng và lớp dữ liệu sản phẩm

- Viết model, migration và ràng buộc DB theo mục 4; dùng tên bảng `products` rõ ràng.
- Viết serializer cho tạo/cập nhật/đọc, ép kiểu an toàn cho giá và số lượng, trim chuỗi, từ chối trường lạ/read-only và dữ liệu thiếu.
- Dùng ORM Django cho các thao tác tìm danh sách, tìm theo ID, tạo, cập nhật, xóa.

**Đạt khi:** migration tạo bảng đúng schema, dữ liệu hợp lệ lưu và đọc lại được, dữ liệu âm/sai định dạng bị chặn.

### Bước 4 — Gắn xác thực và triển khai năm API

- Viết authentication class hoặc permission layer cho Product Service: lấy Bearer token, gọi Auth Service mỗi request, ánh xạ `200`/`401`/`503` như mục 3.
- Viết URL, views/controller và response theo mục 5; tất cả năm API đều đi qua xác thực.
- Bảo đảm `PUT` chỉ cập nhật sản phẩm có sẵn, không tạo mới; `DELETE` sản phẩm đã xóa trả `404`.

**Đạt khi:** CRUD chạy trọn luồng; thiếu/sai token không truy cập được sản phẩm; Auth Service mất kết nối trả `503`.

### Bước 5 — Tạo DB người dùng bài 2

- Bổ sung lệnh khởi tạo bảng `Users` theo model hiện có, chạy lại không xóa hoặc ghi đè dữ liệu cũ.
- Tạo tài khoản demo với mật khẩu băm Django; giữ credential trong file cục bộ bị Git ignore, không đưa vào mã nguồn/tài liệu.
- Kiểm tra Auth Service login được bằng tài khoản này và DB người dùng tách khỏi DB sản phẩm.

**Đạt khi:** có DB auth riêng để kiểm thử hai service thật.

### Bước 6 — Kiểm thử và hướng dẫn vận hành

- Test model/serializer: trường bắt buộc, chuỗi trắng, giới hạn tên, giá âm/quá lớn/quá 2 chữ số thập phân, số lượng âm/không nguyên, trường lạ, tên trùng, thời gian tạo/cập nhật.
- Test API CRUD theo status và body ở mục 5, gồm danh sách rỗng, ID không hợp lệ, ID không tồn tại, xóa lặp lại.
- Test tích hợp xác thực bằng cách mock phản hồi HTTP Auth Service cho `200`, `401`, timeout và `5xx`; sau khi tạo DB người dùng, test end-to-end thật.
- Viết README: cài thư viện, vị trí DB của bài 2, migration, chạy hai service trên 8000/8001, cách lấy access token, ví dụ `curl` cho năm API, cách chạy test.

**Đạt khi:** test tự động đi qua; chạy thử thật theo thứ tự login → POST → GET list → GET detail → PUT → DELETE; hai file DB độc lập.

## 7. Điều kiện để chạy thử tích hợp

Tạo `database/DB_ProjectManagerment.db` bằng lệnh khởi tạo của Auth Service với bảng `Users` đúng schema và một tài khoản demo có mật khẩu băm Django. Không ghi credential vào Git. Sau khi có DB, chạy smoke test end-to-end và ghi kết quả vào README hoặc báo cáo bàn giao.

## 8. Tiêu chí bàn giao

1. Cả năm API đáp ứng hợp đồng ở mục 5 và đều yêu cầu login.
2. Product Service hoạt động ở cổng 8001, dữ liệu bền vững trong DB riêng; Auth Service hoạt động ở cổng 8000.
3. JWT được xác minh bởi Auth Service cho mỗi request; lỗi xác thực và lỗi kết nối được xử lý đúng.
4. Migration, test và README đủ để người khác cài đặt, chạy lại và kiểm tra toàn bộ luồng.
