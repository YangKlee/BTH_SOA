# Kế hoạch bài thực hành số 4: Order Management

**Trạng thái: HOÀN THÀNH 16/16 TASK, ĐÃ NGHIỆM THU NGÀY 02/11/2026.**

## 1. Nguồn yêu cầu và hiện trạng

- Đề gốc: `C:/Users/yangk/Downloads/BÀI THỰC HÀNH SỐ 4.pdf`, đã đọc cả 2 trang và đối chiếu hình ảnh.
- Yêu cầu của người dùng ở lượt này: lập plan chi tiết, chia từng task, chờ người dùng duyệt rồi mới bắt đầu làm.
- Những yêu cầu trong PDF được dùng làm đầu vào thiết kế, không phải lệnh cho phép triển khai ngay.
- Repo hiện có `services/auth-service`, `services/product-service`, tài liệu và task bài 3. Chưa thấy Order Service trong danh sách file đã khảo sát.
- Auth hiện có `POST /login/`, `POST /token/refresh/`, `GET /token/verify/`; Product có CRUD `/products`, `/products/{id}` và xác thực từ xa.
- Chưa chạy test hoặc xác nhận runtime của hai service ở bước lập kế hoạch. Các trạng thái “Hoàn thành” trong task bài 3 là ghi nhận cũ, chưa được kiểm chứng lại.
- Bộ plan bài 4 nằm riêng tại `plan/bai-4/`, không sửa task bài 3.

## 2. Yêu cầu bắt buộc từ PDF

1. Order Service chạy độc lập, có cổng và cơ sở dữ liệu riêng.
2. Đủ 5 API đơn hàng: danh sách, chi tiết, tạo kèm kiểm tra tồn kho, cập nhật trạng thái, xóa.
3. Đủ 5 API chi tiết đơn hàng: danh sách, chi tiết, tạo, cập nhật, xóa.
4. Controller xử lý nghiệp vụ và truy vấn dữ liệu.
5. Xác thực qua service bài 2.
6. Hai bảng có các cột như phụ lục; lưu thông tin sản phẩm và giá tại thời điểm đặt hàng.

## 3. Các quyết định đề xuất cần duyệt cùng plan

Đề chưa định nghĩa các chi tiết dưới đây. Đây là **đề xuất thiết kế**, không khẳng định là yêu cầu có sẵn trong PDF.

| Điểm cần chốt | Phương án đề xuất |
| --- | --- |
| Công nghệ | Kế thừa Django REST Framework và SQLite của repo; kiểm tra dependencies hiện có khi triển khai, không nâng cấp hai service cũ trong phạm vi này. |
| Cổng | Auth `8000`, Product `8001`, Order `8002`. |
| Tên bảng chi tiết | Dùng `order_items` đồng nhất với API. Phụ lục viết `other_items`, xem là lỗi tên cần chuẩn hóa. |
| Tồn kho | Chỉ kiểm tra số lượng hiện tại qua HTTP Product Service, đúng phạm vi tối thiểu đề nêu. Không trừ, giữ chỗ hoặc hoàn kho. Không cộng số lượng các đơn khác để giả lập giữ kho. |
| Giới hạn tồn kho | Kiểm tra tại thời điểm gọi API; không bảo đảm chống bán vượt tồn giữa các đơn đồng thời. Nếu muốn trừ/giữ kho thật, phải duyệt thêm API tồn kho nguyên tử ở Product Service và cơ chế bù trừ liên service. |
| Tạo đơn | `POST /orders` nhận thông tin khách và danh sách `items` không rỗng; tạo order và toàn bộ items cùng một transaction cục bộ. |
| Trạng thái | Mặc định `pending`; cho phép `pending -> completed` hoặc `pending -> cancelled`; trạng thái cuối không đổi sang trạng thái khác. Gửi lại cùng trạng thái là thành công, không tạo tác dụng phụ. |
| Sửa mặt hàng | Chỉ đơn `pending` được thêm/sửa/xóa item. `PUT /order_items/{id}` chỉ cập nhật `quantity`; `order_id`, `product_id` bất biến. Đổi sản phẩm bằng thao tác thêm/xóa dòng trong đơn pending. |
| Đơn rỗng | Không tạo đơn rỗng; không xóa item cuối cùng. Muốn bỏ toàn bộ đơn dùng `DELETE /orders/{id}`. |
| Trùng sản phẩm | Mỗi đơn có một dòng cho mỗi `product_id`; payload tạo đơn trùng sản phẩm bị từ chối, không tự gộp. |
| Giá và tên sản phẩm | Server lấy từ Product khi tạo item. Sửa quantity giữ nguyên tên/giá đã chụp tại thời điểm tạo; không lấy giá mới áp vào đơn cũ. |
| Xóa đơn | Xóa cứng đơn ở mọi trạng thái và cascade items; không gọi cập nhật kho vì phương án này không trừ kho. |
| Phân quyền | Mọi API cần access JWT hợp lệ. Chưa thêm owner/role restriction vì schema và đề không định nghĩa. Người dùng đã xác thực có thể thao tác mọi đơn theo hợp đồng bài tập. |
| Giao diện | API backend và hướng dẫn demo; không có frontend, Docker, gateway hoặc thanh toán trong phạm vi đề. |

Nếu người dùng sửa một lựa chọn trên, cập nhật hợp đồng và task liên quan trước khi code. Nếu người dùng duyệt toàn bộ plan, dùng các mặc định này, không cần hỏi lại từng lựa chọn.

## 4. Kiến trúc và phạm vi file

Luồng: Client -> Order Service -> Auth Service để xác minh JWT; Order Service -> Product Service để lấy sản phẩm và kiểm tra tồn kho; Order Service chỉ ghi DB riêng.

| Service | Đường dẫn | DB | Giao tiếp |
| --- | --- | --- | --- |
| Auth hiện có | `services/auth-service` | `database/DB_ProjectManagerment.db` | Order gọi `GET /token/verify/` với Bearer token. |
| Product hiện có | `services/product-service` | `database/products.sqlite3` | Order gọi `GET /products/{id}` với cùng Bearer token. |
| Order mới | `services/order-service` | `database/orders.sqlite3` | 10 API bên dưới trên cổng 8002. |

Order không import model/module của Auth/Product, không đọc DB của hai service đó, không giữ khóa ký JWT của Auth. `product_id` là số nguyên tham chiếu logic, không phải khóa ngoại xuyên DB. `order_id` là khóa ngoại thật trong DB Order.

Cấu trúc dự kiến:

```text
services/order-service/
  manage.py
  requirements.txt
  .env.example
  config/{settings,urls,asgi,wsgi}.py
  orders/
    models.py
    serializers.py
    authentication.py
    clients/product.py
    services.py
    views/{order_collection,order_detail,item_collection,item_detail}.py
    migrations/
    tests/
scripts/smoke-order-service.ps1
```

Cấu hình: `AUTH_SERVICE_URL`, `PRODUCT_SERVICE_URL`, timeout hữu hạn cho mỗi service (đề xuất 3 giây), `ORDER_DEBUG`, `ORDER_SECRET_KEY`, `ORDER_ALLOWED_HOSTS`. Ghi rõ cách nạp cấu hình; file `.env.example` không đồng nghĩa Django tự đọc `.env`.

## 5. Hợp đồng dữ liệu

### Bảng orders

| Cột | Kiểu / quy tắc |
| --- | --- |
| id | INT tự tăng, khóa chính. |
| customer_name | VARCHAR(255), chuỗi bắt buộc, trim, không rỗng. |
| customer_email | VARCHAR(255), email hợp lệ, bắt buộc. |
| total_amount | DECIMAL(10,2), server tính từ items, không âm, tối đa `99999999.99`. |
| status | VARCHAR(50), một trong `pending`, `completed`, `cancelled`. |
| created_at | Timestamp do server tạo, UTC. |
| updated_at | Timestamp do server cập nhật, UTC; thay đổi cả khi thay đổi items. |

### Bảng order_items

| Cột | Kiểu / quy tắc |
| --- | --- |
| id | INT tự tăng, khóa chính. |
| order_id | INT FK -> orders.id, ON DELETE CASCADE. |
| product_id | INT dương; không có quan hệ ORM tới DB Product. |
| product_name | VARCHAR(255), snapshot từ Product. |
| quantity | INT dương; JSON integer, từ chối boolean, số thực, chuỗi và null. |
| unit_price | DECIMAL(10,2), snapshot từ Product, không âm. |
| total_price | DECIMAL(10,2), `quantity * unit_price`, server tính. |

- Ràng buộc DB: quantity > 0, các số tiền >= 0, status hợp lệ, unique `(order_id, product_id)`.
- Toàn bộ phép tính tiền dùng Decimal, trả JSON dưới dạng chuỗi 2 chữ số thập phân. Kiểm tra overflow cả dòng và tổng đơn trước khi ghi.
- Client không được ghi `id`, snapshot tên/giá, các tổng tiền hoặc timestamps. Từ chối field lạ thay vì âm thầm bỏ qua.
- ID URL sai định dạng hoặc không dương: 400; ID đúng định dạng nhưng bản ghi local không tồn tại: 404.

## 6. Hợp đồng 10 API

URL không có dấu `/` cuối, đồng nhất với API Product hiện tại. Mọi API bắt buộc `Authorization: Bearer <access>` và dùng JSON.

| Method / URL | Input / hành vi | Thành công | Task |
| --- | --- | --- | --- |
| GET /orders | Danh sách đơn, sắp xếp id tăng dần, không phân trang trong phạm vi bài. | 200, array thông tin order, không nhúng items. | B4-T08 |
| GET /orders/{id} | Chi tiết order kèm array `items`. | 200, object. | B4-T08 |
| POST /orders | `customer_name`, `customer_email`, `items: [{product_id, quantity}]`; tối thiểu 1 item. | 201, order kèm items; Location trỏ `/orders/{id}`. | B4-T07 |
| PUT /orders/{id} | Chỉ nhận `status`, kiểm tra chuyển trạng thái. | 200, order kèm items. | B4-T09 |
| DELETE /orders/{id} | Xóa order và mọi item trong cùng transaction. | 204, body rỗng. | B4-T10 |
| GET /order_items | Danh sách toàn bộ items, sắp xếp id tăng dần. | 200, array. | B4-T11 |
| GET /order_items/{id} | Chi tiết một item. | 200, object. | B4-T11 |
| POST /order_items | `order_id`, `product_id`, `quantity`; chỉ order pending, kiểm tra tồn và dòng trùng. | 201, item; Location trỏ `/order_items/{id}`. | B4-T12 |
| PUT /order_items/{id} | Chỉ nhận `quantity`; kiểm tra tồn theo số lượng mới, giữ snapshot giá/tên. | 200, item. | B4-T13 |
| DELETE /order_items/{id} | Chỉ order pending; không xóa dòng cuối; tính lại tổng. | 204, body rỗng. | B4-T13 |

Ví dụ tạo đơn:

```json
{
  "customer_name": "Nguyen Van A",
  "customer_email": "a@example.com",
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 2, "quantity": 1}
  ]
}
```

Các object phản hồi dùng đúng tên cột trong bảng; order detail/create/update-status bổ sung `items`. Không nhận `status` ở create; server gán `pending`.

### Quy ước lỗi

| HTTP | Trường hợp |
| --- | --- |
| 400 | Payload thiếu/sai, field lạ/read-only, email sai, ID sai, product_id không tồn tại ở Product, sản phẩm lặp trong payload, tiền vượt giới hạn. |
| 401 | Thiếu/sai/hết hạn token; upstream trả 401 khi token không còn hợp lệ. |
| 404 | Order hoặc item local không tồn tại, gồm order_id của POST item. |
| 409 | Tồn kho không đủ, chuyển trạng thái không hợp lệ, sửa items của đơn đã chốt/hủy, trùng dòng đã tồn tại, xóa item cuối. |
| 503 | Auth/Product timeout, mất kết nối, 5xx hoặc phản hồi sai hợp đồng; SQLite bận quá timeout (`database_busy`). Upstream 403 bất thường cũng là 503 trong hợp đồng hiện tại. |

Validation theo field dùng object `{field: [message]}`; lỗi nghiệp vụ/tích hợp dùng `{code, detail}` và có thể kèm `product_id`, `requested_quantity`, `available_quantity` cho lỗi tồn kho. Lỗi xác thực giữ dạng chuẩn DRF `{detail}`. Không trả traceback, token hoặc credential.

## 7. Luồng nghiệp vụ và tính nhất quán

### Tạo đơn

1. Xác thực qua Auth; validate payload và ID sản phẩm không trùng.
2. Gọi Product theo từng product_id riêng, chuyển tiếp Bearer token; xác thực schema `id`, `name`, `price`, `quantity` và ID phản hồi khớp request.
3. Kiểm tra quantity <= tồn hiện tại; chụp tên và giá; tính từng dòng và tổng đơn.
4. Nếu bất kỳ bước nào lỗi, không tạo order/item.
5. Ghi order và toàn bộ items trong một transaction DB Order; trả 201 sau commit.

### Thêm/sửa/xóa items và cập nhật trạng thái

- HTTP tới Product thực hiện ngoài transaction DB để tránh giữ khóa trong lúc chờ mạng.
- Sau khi có dữ liệu Product, vào transaction, đọc lại order/status và dữ liệu item hiện tại trước khi ghi. Kiểm tra lại những điều kiện có thể đã thay đổi.
- Mọi thay đổi items và tổng đơn phải commit/rollback cùng nhau; tính lại tổng từ các dòng đang tồn tại, không tin tổng do client gửi.
- Chuyển trạng thái phải đồng bộ với việc sửa items. Hoàn thành đơn kiểm tra lại tồn của toàn bộ items; vẫn giữ snapshot giá. Nếu thiếu tồn, giữ pending.
- Tạo đơn hoặc thêm/sửa items không thể bảo đảm tồn Product giữ nguyên sau HTTP response; đây là giới hạn đã chốt của phương án chỉ kiểm tra.
- SQLite không cung cấp khóa hàng thực như một số DB khác; không xem `select_for_update()` là bảo đảm trên SQLite. B4-T06 phải chọn cơ chế ghi tuần tự phù hợp SQLite (ví dụ transaction IMMEDIATE có kiểm soát) và kiểm chứng xung đột bằng hai connection; lock timeout trả lỗi kiểm soát được, không 500. Không tự retry thao tác ghi tạo đơn gây nhân đôi.
- Cập nhật trạng thái cùng giá trị là no-op; không gọi Product hoặc thay đổi timestamps. `completed`/`cancelled` vẫn được GET, không sửa items.
- Đọc/xóa đơn và xóa item không phụ thuộc Product còn hoạt động; mọi request vẫn phụ thuộc Auth để xác thực.

## 8. Danh sách và thứ tự task

Chi tiết từng task: [tasks/README.md](tasks/README.md). Mỗi task có mục tiêu, phụ thuộc, phạm vi file, các bước và điều kiện nghiệm thu.

Thứ tự thực hiện đề xuất:

1. B4-T01: dựng service.
2. B4-T02, B4-T03: schema và hợp đồng dữ liệu.
3. B4-T04, B4-T05: kết nối Auth và Product.
4. B4-T06: nghiệp vụ dùng chung, transaction và tính tiền.
5. B4-T07 đến B4-T13: đủ 10 API.
6. B4-T14: kiểm thử tổng hợp, lỗi tích hợp, rollback, cạnh tranh và hồi quy.
7. B4-T15: README và script demo.
8. B4-T16: chạy tích hợp 3 service thật, đối chiếu PDF và bàn giao.

Người dùng đã yêu cầu chia sub-agent triển khai. Phân công: `foundation_api` phụ trách T01–T03 rồi T07–T13; `integrations` phụ trách T04–T05 rồi hỗ trợ review; `docs_smoke` phụ trách T15 và hỗ trợ T14; agent chính phụ trách T06, tích hợp T14/T16 và nghiệm thu chung. Công việc độc lập có thể làm song song, các task phụ thuộc chỉ nghiệm thu sau khi nền tảng sẵn sàng.

## 9. Chiến lược kiểm chứng và điều kiện bàn giao

- Mỗi task code có kiểm thử hành vi liên quan; B4-T14 bổ sung các luồng xuyên tính năng thay vì viết lại test trùng lặp.
- Các test tự động dùng DB thử và mock ranh giới HTTP; không phụ thuộc dữ liệu demo cá nhân.
- Smoke test cuối chạy 3 service thật: login -> tạo sản phẩm thử -> tạo đơn -> CRUD items -> hoàn thành/hủy -> xóa; có cả thiếu tồn và token lỗi.
- Smoke test dùng dữ liệu gắn nhãn riêng, dọn đúng ID do lần chạy tạo ra; không xóa dữ liệu có sẵn. Credential chỉ đọc từ nguồn local đã cấu hình, không ghi vào log/tài liệu.
- Kiểm tra migration sạch, `manage.py check`, toàn bộ test Order; chạy lại test Auth/Product để xác nhận tương thích.
- Mỗi task chỉ đánh dấu hoàn thành sau khi có lệnh kiểm chứng và kết quả thực tế; ghi rõ nếu môi trường thiếu điều kiện.
- Bàn giao gồm source Order Service, migration, tests, `.env.example`, README cập nhật, script demo, bảng đối chiếu 10 API và bằng chứng test. Không coi plan hoặc code chưa chạy là đã hoàn thành.

## 10. Cổng duyệt

- [x] Đọc đủ PDF và khảo sát repo ở mức lập kế hoạch.
- [x] Có hợp đồng đề xuất, danh sách task và tiêu chí nghiệm thu.
- [x] Người dùng duyệt qua yêu cầu chia sub-agent làm các task.
- [x] Bắt đầu triển khai B4-T01 sau khi đã duyệt.

Lượt lập plan trước chỉ tạo Markdown. Lượt hiện tại đã được phép triển khai, kiểm thử và chạy tích hợp theo phạm vi trên.

## 11. Final verification

Completed with user-authorized sub-agents. Order82/Auth7/Product41 automated tests passed;62 live HTTP smoke checks passed; temporary demo data cleaned and owned server processes stopped. See [verification report](ket-qua-kiem-thu.md).
