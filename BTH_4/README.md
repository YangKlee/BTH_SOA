# Bài 4 — Dịch vụ quản lý đơn hàng

Ba ứng dụng Django REST Framework chạy độc lập: Auth Service ở cổng **8000**, Product Service ở cổng **8001**, Order Service ở cổng **8002**. Order xác minh JWT qua Auth và kiểm tra tồn kho qua HTTP Product; mỗi service dùng DB riêng, không import model hoặc đọc DB của service khác. Các mục đầu giữ hướng dẫn Auth/Product kế thừa; phần **Order Service** bên dưới bổ sung cài đặt, 10 API và script kiểm chứng bài 4.

Kế hoạch: [plan bài 4](plan/bai-4/ke-hoach-trien-khai.md), [16 task](plan/bai-4/tasks/README.md).

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

## Order Service — chuẩn bị và chạy

Các lệnh sau chạy từ thư mục gốc `BTH_4`. Tạo môi trường riêng, cài dependencies rồi tạo schema **DB Order riêng** tại `database/orders.sqlite3`:

```powershell
py -3.14 -m venv .\services\order-service\.venv
& .\services\order-service\.venv\Scripts\python.exe -m pip install -r .\services\order-service\requirements.txt
Push-Location .\services\order-service
& .\.venv\Scripts\python.exe manage.py migrate
Pop-Location
```

Chạy Auth 8000 và Product 8001 theo hướng dẫn trên. Mở **cửa sổ thứ ba** tại gốc repo để chạy Order:

```powershell
$env:AUTH_SERVICE_URL = 'http://127.0.0.1:8000'
$env:PRODUCT_SERVICE_URL = 'http://127.0.0.1:8001'
$env:AUTH_SERVICE_TIMEOUT_SECONDS = '3'
$env:PRODUCT_SERVICE_TIMEOUT_SECONDS = '3'
Push-Location .\services\order-service
& .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8002
```

Đó cũng là các URL/timeout mặc định. Timeout phải hữu hạn và lớn hơn 0. Order đọc `ORDER_DEBUG`, `ORDER_SECRET_KEY`, `ORDER_ALLOWED_HOSTS`; khi `ORDER_DEBUG=false`, bắt buộc đặt secret riêng. Xem [cấu hình mẫu](services/order-service/.env.example). `.env.example` chỉ là mẫu, Django không tự nạp `.env`; đặt biến trong cửa sổ chạy service. Không dùng khóa JWT Auth cho Order.

Order gọi `GET /token/verify/` với Bearer token để xác thực, rồi chuyển tiếp token khi gọi `GET /products/{id}` để kiểm tra sản phẩm/tồn kho. `product_id` là tham chiếu logic; `order_id` là FK nội bộ. Tên bảng là `orders` và `order_items`, chuẩn hóa chỗ phụ lục PDF viết `other_items`.

## Hợp đồng 10 API Order

URL **không có dấu `/` cuối**, mọi API cần access JWT và body JSON. Danh sách trả array theo id tăng dần, không phân trang; rỗng trả `[]`.

| Method / URL | Input / kết quả | Thành công |
| --- | --- | --- |
| `GET /orders` | Danh sách đơn, không nhúng items. | 200 |
| `GET /orders/{id}` | Một đơn kèm `items`. | 200 |
| `POST /orders` | customer_name, customer_email, items: [{product_id, quantity}]; trả đơn kèm items. | 201 + Location |
| `PUT /orders/{id}` | Chỉ nhận status; trả đơn kèm items. | 200 |
| `DELETE /orders/{id}` | Xóa đơn và cascade items. | 204 rỗng |
| `GET /order_items` | Toàn bộ mặt hàng. | 200 |
| `GET /order_items/{id}` | Chi tiết một mặt hàng. | 200 |
| `POST /order_items` | order_id, product_id, quantity; trả item mới. | 201 + Location |
| `PUT /order_items/{id}` | Chỉ nhận quantity; trả item cập nhật. | 200 |
| `DELETE /order_items/{id}` | Xóa item, tính lại tổng đơn. | 204 rỗng |

Quy tắc nghiệp vụ:

- Tạo đơn phải có ít nhất một item và không trùng product_id; mặc định `pending`. quantity là JSON integer dương, không nhận bool, chuỗi, số thực hoặc null.
- Một đơn có tối đa một dòng mỗi sản phẩm. Chỉ đơn pending được thêm/sửa/xóa item; không xóa item cuối. order_id/product_id của item bất biến.
- Server chụp product_name/unit_price từ Product khi tạo item. Sửa quantity giữ nguyên tên/giá đã lưu dù Product thay đổi. Client không được ghi snapshot, tổng tiền, id, timestamps hoặc field lạ.
- Server tính total_price = quantity × unit_price và total_amount = tổng items bằng Decimal, trả chuỗi hai số thập phân; chặn vượt `99999999.99`. Thay đổi item và tổng đơn commit/rollback cùng transaction, đồng thời cập nhật order.updated_at.
- `pending -> completed` hoặc `pending -> cancelled`; completed kiểm tra lại tồn hiện tại. Trạng thái cuối không chuyển sang trạng thái khác. Gửi cùng status là no-op, không đổi updated_at.
- **Chỉ kiểm tra tồn kho**, không trừ/giữ/hoàn kho. Không bảo đảm chống bán vượt tồn giữa các đơn đồng thời.
- Xóa đơn ở mọi trạng thái là xóa cứng và cascade items. Đọc/xóa không cần Product đang hoạt động, nhưng vẫn cần Auth xác thực.
- Mọi người dùng đã xác thực được thao tác mọi đơn theo phạm vi bài tập; không có owner/role rule bổ sung.

| HTTP lỗi | Ý nghĩa ở Order |
| --- | --- |
| 400 | Payload/ID sai, email sai, field lạ/read-only, product không tồn tại hoặc tiền overflow. |
| 401 | Token thiếu/sai/hết hạn hoặc upstream từ chối token. |
| 404 | Order/item local không tồn tại, gồm order_id khi tạo item. |
| 409 | Thiếu tồn, item trùng, chuyển trạng thái sai, sửa item đơn đã chốt/hủy hoặc xóa item cuối. |
| 503 | Auth/Product lỗi/timeout/sai hợp đồng hoặc DB đang bận theo xử lý của service. |

Validation theo field trả `{field: [message]}`; lỗi nghiệp vụ/tích hợp trả `{code, detail}` và có thể kèm product_id/số lượng; lỗi xác thực dùng `{detail}`.

## Gọi thử API Order bằng PowerShell

Trong **cửa sổ thứ tư** tại gốc repo, đăng nhập theo ví dụ Auth ở trên để có `$access`. Ví dụ dưới tạo sản phẩm thử và lấy ID thật:

```powershell
$headers = @{Authorization="Bearer $access"}
$productBody = @{name='Order demo pen'; description='Blue ink'; price='10.25'; quantity=100} | ConvertTo-Json
$product = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/products -Headers $headers -ContentType 'application/json' -Body $productBody
$orderBody = @{
    customer_name='Nguyen Van A'
    customer_email='a@example.com'
    items=@(@{product_id=$product.id; quantity=2})
} | ConvertTo-Json -Depth 5
$order = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8002/orders -Headers $headers -ContentType 'application/json' -Body $orderBody
$order
Invoke-RestMethod -Uri "http://127.0.0.1:8002/orders/$($order.id)" -Headers $headers

$item = $order.items[0]
$quantityBody = @{quantity=3} | ConvertTo-Json
Invoke-RestMethod -Method Put -Uri "http://127.0.0.1:8002/order_items/$($item.id)" -Headers $headers -ContentType 'application/json' -Body $quantityBody
$statusBody = @{status='completed'} | ConvertTo-Json
Invoke-RestMethod -Method Put -Uri "http://127.0.0.1:8002/orders/$($order.id)" -Headers $headers -ContentType 'application/json' -Body $statusBody

# Don chi con mot item: xoa order de xoa ca don.
Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:8002/orders/$($order.id)" -Headers $headers
Invoke-RestMethod -Method Delete -Uri "http://127.0.0.1:8001/products/$($product.id)" -Headers $headers
```

Response tạo đơn có dạng sau; ID/timestamps thay đổi theo lần chạy:

```json
{
  "id": 1,
  "customer_name": "Nguyen Van A",
  "customer_email": "a@example.com",
  "total_amount": "20.50",
  "status": "pending",
  "created_at": "2026-11-02T00:00:00Z",
  "updated_at": "2026-11-02T00:00:00Z",
  "items": [
    {"id": 1, "order_id": 1, "product_id": 1, "product_name": "Order demo pen", "quantity": 2, "unit_price": "10.25", "total_price": "20.50"}
  ]
}
```

## Smoke test ba service thật

[Script smoke](scripts/smoke-order-service.ps1) dùng credential local, tự tạo hai sản phẩm và các đơn riêng để kiểm chứng đủ 10 API, token sai/thiếu, thiếu tồn, snapshot tên/giá, tổng tiền, recheck khi complete, cancel và cascade. Chạy sau khi ba service đã sẵn sàng:

```powershell
& .\scripts\smoke-order-service.ps1 -EvidencePath .\plan\bai-4\smoke-result.json
```

Tham số tùy chọn: `-AuthUrl`, `-ProductUrl`, `-OrderUrl`, `-CredentialPath`, `-TimeoutSeconds`. CredentialPath mặc định là `database/auth_demo_credentials.txt` tính từ vị trí script, không phụ thuộc thư mục hiện tại. Script không khởi động server.

Script không in token/password; evidence chỉ chứa kết quả kiểm tra và ID lần chạy. `finally` dọn đúng các ID do lần chạy tạo ra, không xóa dữ liệu có sẵn. Nếu cleanup thất bại, script báo các ID còn lại và kết thúc lỗi. Product quantity được kiểm chứng không đổi do thao tác Order.

## Kiểm thử Order

```powershell
Push-Location .\services\order-service
& .\.venv\Scripts\python.exe manage.py check
& .\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
$env:ORDER_TEST_DB = Join-Path $env:TEMP ('bth4-test-' + [guid]::NewGuid().ToString('N') + '.sqlite3')
try {
    & .\.venv\Scripts\python.exe manage.py test orders --noinput
}
finally {
    Remove-Item Env:ORDER_TEST_DB -ErrorAction SilentlyContinue
    Pop-Location
}
```

Lệnh trên dùng file DB thử riêng để chạy đủ **82 test, không skip**, gồm kiểm chứng cạnh tranh SQLite qua nhiều connection thật. Django dọn DB thử sau lần chạy bình thường. Nếu bỏ ORDER_TEST_DB, DB thử mặc định là in-memory và 4 test cạnh tranh sẽ được skip; đó không phải lượt kiểm chứng đầy đủ.

Test tự động dùng DB thử và mock HTTP; smoke script kiểm chứng ba service thật. Các lệnh test hồi quy Auth/Product vẫn giữ ở phần trên. Không coi mock test là bằng chứng tích hợp runtime.
