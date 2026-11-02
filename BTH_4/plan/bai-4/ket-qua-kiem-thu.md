# Kết quả nghiệm thu bài 4

Ngày kiểm chứng: **02/11/2026**, múi giờ người dùng Asia/Saigon.

## Kết quả

- Hoàn thành Order Service độc lập tại `services/order-service`, cổng 8002, DB `database/orders.sqlite3`.
- Đủ 10 API, xác thực qua Auth và kiểm tra tồn qua Product bằng HTTP.
- Order: **82 test pass, không skip**; gồm 4 test cạnh tranh SQLite dùng DB file thật và hai connection.
- Hồi quy Auth: **7 test pass**. Hồi quy Product: **41 test pass**.
- Ba service thật: **62 kiểm tra smoke pass**, không có lỗi cleanup. Evidence: [smoke-result.json](smoke-result.json).
- `manage.py check` không có lỗi; `makemigrations --check --dry-run` không phát hiện thay đổi thiếu migration.
- Sau smoke, hash nội dung các bảng products/orders/order_items khớp baseline trước chạy. Dữ liệu demo đã dọn; sequence ID tăng theo thao tác tạo/xóa bình thường.
- Đã dừng toàn bộ process test do agent chính mở, gồm các child Python; không còn listener trên 8000/8001/8002 sau kết thúc. Muốn demo lại, khởi chạy theo README.

## Phân công đã thực hiện

| Người thực hiện | Phạm vi |
| --- | --- |
| foundation_api | T01–T03, T07–T13: khung service, models/migration, serializers, toàn bộ views/routes và test API. |
| integrations | T04–T05: xác thực, Product client, transport chặn redirect; thêm test bảo vệ 10 API và review tích hợp. |
| docs_smoke | T15: README, script PowerShell, kiểm thử hồi quy Auth/Product. |
| Agent chính | T06/T14/T16: nghiệp vụ, transaction, test cạnh tranh, tích hợp source, chạy toàn bộ suite và smoke thật, đối chiếu/bàn giao. |

## Đối chiếu 10 API

| API | Source | Bằng chứng smoke |
| --- | --- | --- |
| GET /orders | orders/views/order_collection.py | GET /orders; đơn tạo xuất hiện trong collection. |
| GET /orders/{id} | orders/views/order_detail.py | GET /orders/{id}; response nhúng items. |
| POST /orders | orders/views/order_collection.py | POST /orders; 201, Location, pending, tổng chính xác; thiếu tồn 409 không tạo dở. |
| PUT /orders/{id} | orders/views/order_detail.py | Complete, cancel, recheck tồn, no-op giữ timestamp, chặn chuyển trạng thái cuối. |
| DELETE /orders/{id} | orders/views/order_detail.py | 204 rỗng, items cascade, xóa lại 404; xóa được đơn cancelled. |
| GET /order_items | orders/views/item_collection.py | GET /order_items; có đủ items do lần chạy tạo. |
| GET /order_items/{id} | orders/views/item_detail.py | GET /order_items/{id}; snapshot giá đúng. |
| POST /order_items | orders/views/item_collection.py | 201 và Location; trùng sản phẩm 409; đơn completed bị chặn. |
| PUT /order_items/{id} | orders/views/item_detail.py | Quantity đổi, snapshot tên/giá giữ nguyên, tổng cập nhật; thiếu tồn 409. |
| DELETE /order_items/{id} | orders/views/item_detail.py | 204; chặn xóa item cuối và item của đơn completed. |

Các đường dẫn source trong bảng tính từ `services/order-service/`.

## Đối chiếu các yêu cầu còn lại

| Yêu cầu | Hiện thực / kiểm chứng |
| --- | --- |
| Service có cổng, DB riêng | config/settings.py; runserver 127.0.0.1:8002; migration trên orders.sqlite3. |
| Hai bảng theo phụ lục | models.py, migrations/0001_initial.py; đủ cột, FK order nội bộ, product_id tham chiếu logic. |
| Controller nghiệp vụ và truy vấn | views/ điều phối; services.py tính tiền, kiểm tra trạng thái và ghi DB nguyên tử. |
| Kiểm tra tồn từ Product | clients/product.py; smoke thiếu tồn lúc create/update/complete; không import/đọc DB Product. |
| Xác thực bài 2 | authentication.py gọi GET /token/verify/; smoke token đúng/sai/thiếu; test security chặn đủ 10 API và giữ DB nguyên trạng. |
| Tên/giá tại lúc đặt | ProductSnapshot + OrderItem; smoke đổi Product rồi sửa quantity vẫn giữ snapshot. |
| Lỗi không ghi nửa chừng | Test service rollback lúc insert, lỗi dependency, overflow dòng/tổng; smoke create thiếu tồn không tạo order. |
| Cạnh tranh cục bộ | SQLite IMMEDIATE, HTTP ngoài transaction, đọc lại trạng thái; 4 test hai connection kiểm tra duplicate/different adds, cancel/update race và lock timeout503. |

## Lệnh kiểm chứng

Từ `services/order-service`:

```powershell
$env:ORDER_TEST_DB = Join-Path $env:TEMP ('bth4-full-test-' + [guid]::NewGuid().ToString('N') + '.sqlite3')
& ./.venv/Scripts/python.exe manage.py check
& ./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
& ./.venv/Scripts/python.exe manage.py test orders --verbosity 1 --noinput
Remove-Item Env:ORDER_TEST_DB
```

Kết quả: 82 tests, OK, không skip; Django hủy DB test tạm sau chạy. Chạy mặc định không đặt ORDER_TEST_DB sẽ dùng memory DB và bỏ qua 4 test concurrency có chủ đích; vì vậy bản nghiệm thu đã đặt đường dẫn file.

Từ từng thư mục service tương ứng:

```powershell
# services/auth-service: dung venv co san
& ./venv/Scripts/python.exe manage.py test authentication --noinput
# services/product-service
& ./.venv/Scripts/python.exe manage.py check
& ./.venv/Scripts/python.exe manage.py test products --noinput
```

Từ gốc `BTH_4`, sau khi khởi chạy ba service:

```powershell
& ./scripts/smoke-order-service.ps1 -EvidencePath plan/bai-4/smoke-result.json
```

Kết quả: 62 checks, passed=true, failure=null, cleanup_errors=[]. Lần chạy đầu phát hiện lỗi parse array rỗng của PowerShell 5; đã sửa chuẩn hóa JSON array và lần chạy nghiệm thu cuối pass đầy đủ.

## Giới hạn theo plan đã duyệt

- Chỉ kiểm tra tồn, không trừ/giữ/hoàn kho; không bảo đảm chống bán vượt tồn giữa các đơn đồng thời.
- Phân quyền theo JWT hợp lệ; mọi người dùng đã xác thực có thể thao tác mọi đơn trong phạm vi bài tập.
- SQLite và Django development server dùng cho bài thực hành. Không có frontend hoặc luồng thanh toán trong phạm vi này.
- Bảng chi tiết dùng tên `order_items` như API, chuẩn hóa lỗi tên `other_items` ở phụ lục.

Hướng dẫn chạy: [README](../../README.md). Trạng thái từng task: [tasks/README.md](tasks/README.md).
