# Bài 3 — Product Service với xác thực từ Auth Service

Hai ứng dụng Django REST Framework chạy độc lập: Auth Service ở cổng **8000** quản lý đăng nhập/JWT, Product Service ở cổng **8001** lưu sản phẩm. Mỗi request tới năm API sản phẩm phải có access JWT; Product Service gọi `GET /token/verify/` của Auth Service để xác minh token, không đọc DB người dùng hoặc khóa ký JWT.

## Yêu cầu và cơ sở dữ liệu

- Python **3.14** (đã kiểm tra với 3.14.6), Windows PowerShell và `py -3.14`.
- DB người dùng của Auth Service nằm tại `database/DB_ProjectManagerment.db`. Lệnh khởi tạo bên dưới tạo bảng `Users` đúng model bài 2 và một tài khoản demo nếu chưa có; nếu bạn đã có DB bài 2, lệnh giữ nguyên bảng/tài khoản hiện có.
- DB sản phẩm là `database/products.sqlite3`, được Django tạo khi chạy migration của Product Service. Không sao chép DB bài 2 sang tên này. Product Service không dùng bảng `Users`.

Các lệnh dưới đây chạy từ thư mục gốc của repo. Tạo hai môi trường Python và cài dependencies riêng:

```powershell
py -3.14 -m venv .\services\auth-service\.venv
py -3.14 -m venv .\services\product-service\.venv
& .\services\auth-service\.venv\Scripts\python.exe -m pip install -r .\services\auth-service\requirements.txt
& .\services\product-service\.venv\Scripts\python.exe -m pip install -r .\services\product-service\requirements.txt
```

Khởi tạo DB Auth và một tài khoản demo cục bộ, rồi tạo schema DB sản phẩm:

```powershell
Push-Location .\services\auth-service
& .\.venv\Scripts\python.exe manage.py init_demo_auth_db
Pop-Location

Push-Location .\services\product-service
& .\.venv\Scripts\python.exe manage.py migrate
Pop-Location
```

Lệnh `init_demo_auth_db` có thể chạy lại: nếu bảng/tài khoản demo và tệp credential đã có, nó không ghi đè. Nếu bảng `Users` đã có nhưng không khớp model, hoặc tài khoản và tệp credential không đồng bộ, lệnh dừng mà không thay dữ liệu cũ. Bảng `Users` là unmanaged (`managed = False`), nên `manage.py migrate` của Auth Service không tạo bảng này. Chỉ chạy migration của Product Service trong thư mục Product Service.

Credential demo được ghi duy nhất vào `database/auth_demo_credentials.txt` ở dạng JSON và đã được Git ignore. Mở tệp đó trên máy của bạn để dùng tài khoản demo; không đưa nội dung tệp vào commit, log hay ảnh chụp màn hình.

## Khởi chạy

Mở hai cửa sổ PowerShell tại thư mục gốc repo. **Cửa sổ 1**:

```powershell
Push-Location .\services\auth-service
& .\.venv\Scripts\python.exe manage.py runserver 8000
```

**Cửa sổ 2**:

```powershell
$env:AUTH_SERVICE_URL = 'http://127.0.0.1:8000'
$env:AUTH_SERVICE_TIMEOUT_SECONDS = '3'
Push-Location .\services\product-service
& .\.venv\Scripts\python.exe manage.py runserver 8001
```

`AUTH_SERVICE_URL` và `AUTH_SERVICE_TIMEOUT_SECONDS` có sẵn hai giá trị mặc định trên, nên có thể bỏ hai dòng đặt biến. Timeout phải lớn hơn 0. Product Service dùng UTC, JSON và đọc `PRODUCT_DEBUG`, `PRODUCT_SECRET_KEY`, `PRODUCT_ALLOWED_HOSTS` từ môi trường; xem `services/product-service/.env.example`. Khi `PRODUCT_DEBUG=false`, bắt buộc đặt `PRODUCT_SECRET_KEY`. File `.env.example` là ví dụ, Django không tự nạp file `.env`.

## Thử API bằng PowerShell và curl.exe

Chạy các lệnh sau trong **cửa sổ PowerShell thứ ba** tại thư mục gốc repo, sau khi khởi tạo DB và chạy cả hai service. Ví dụ đọc credential demo cục bộ mà không in mật khẩu. Bạn cũng có thể thay `$loginBody` bằng email/mật khẩu của tài khoản bài 2 khác. Dùng `curl.exe` để tránh alias `curl` của Windows PowerShell; JSON được đưa qua stdin để không vướng cách xử lý dấu nháy của shell.

```powershell
# 1. Đăng nhập và lấy access JWT. Phản hồi có cả access và refresh.
$demo = Get-Content .\database\auth_demo_credentials.txt -Raw | ConvertFrom-Json
$loginBody = @{identifier=$demo.identifier; password=$demo.password} | ConvertTo-Json -Compress
$tokens = $loginBody | curl.exe -sS -H 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:8000/login/ | ConvertFrom-Json
$access = $tokens.access

# Tùy chọn: xem thông tin người dùng mà Product Service sẽ nhận khi xác minh.
curl.exe -sS -H "Authorization: Bearer $access" http://127.0.0.1:8000/token/verify/

# 2. POST /products — tạo sản phẩm; ghi lại id từ phản hồi.
$productBody = @{name='Ballpoint pen'; description='Blue ink'; price='12000.00'; quantity=30} | ConvertTo-Json -Compress
$created = $productBody | curl.exe -sS -H "Authorization: Bearer $access" -H 'Content-Type: application/json' --data-binary '@-' http://127.0.0.1:8001/products | ConvertFrom-Json
$id = $created.id
$created

# 3. GET /products — toàn bộ sản phẩm theo id tăng dần.
curl.exe -sS -H "Authorization: Bearer $access" http://127.0.0.1:8001/products

# 4. GET /products/{id} — một sản phẩm.
curl.exe -sS -H "Authorization: Bearer $access" "http://127.0.0.1:8001/products/$id"

# 5. PUT /products/{id} — phải gửi đủ bốn trường được phép ghi.
$updateBody = @{name='Ballpoint pen'; description='Black ink'; price='12500.50'; quantity=25} | ConvertTo-Json -Compress
$updateBody | curl.exe -sS -X PUT -H "Authorization: Bearer $access" -H 'Content-Type: application/json' --data-binary '@-' "http://127.0.0.1:8001/products/$id"

# 6. DELETE /products/{id} — xóa hẳn; thành công trả 204 và body rỗng.
curl.exe -i -X DELETE -H "Authorization: Bearer $access" "http://127.0.0.1:8001/products/$id"
```

Muốn xem status/header của POST (gồm `Location: /products/{id}`), thêm `-i` vào lệnh `curl.exe` và không chuyển kết quả đó qua `ConvertFrom-Json`.

Các API sản phẩm dùng đường dẫn **không có dấu `/` cuối**. `name`, `description`, `price`, `quantity` đều bắt buộc; tên/mô tả sau trim không được rỗng, tên tối đa 255 ký tự. `price` được trả dưới dạng chuỗi decimal hai chữ số thập phân (`"12000.00"`), nằm từ `0.00` đến `99999999.99`; `quantity` là số nguyên không âm. Tên trùng được phép. `PUT` thay thế đủ bốn trường, giữ `id` và `created_at`; gửi field lạ hoặc field chỉ đọc (`id`, `created_at`, `updated_at`) sẽ bị từ chối. `DELETE` xóa hẳn bản ghi.

| Status | Ý nghĩa |
| --- | --- |
| `400` | Dữ liệu thiếu/sai hoặc ID không phải số nguyên dương; lỗi field trả theo tên field. |
| `401` | Thiếu access JWT, token sai/hết hạn, hoặc người dùng không còn trong DB bài 2. |
| `404` | ID hợp lệ nhưng sản phẩm không tồn tại; xóa lặp lại cũng trả `404`. |
| `503` | Product Service không xác minh được token vì Auth Service không khả dụng, timeout hoặc phản hồi sai hợp đồng. |

## Chạy kiểm thử

Hai bộ test dùng DB thử riêng/mocking, không yêu cầu DB bài 2:

```powershell
Push-Location .\services\auth-service
& .\.venv\Scripts\python.exe manage.py test authentication
Pop-Location

Push-Location .\services\product-service
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py test products
Pop-Location
```

Nếu dùng môi trường có sẵn `services/auth-service/venv`, thay `.venv` bằng `venv` ở lệnh test Auth Service. Sau khi chạy `init_demo_auth_db`, tài khoản demo có thể dùng để thử toàn bộ luồng login → CRUD.
