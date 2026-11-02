# Danh sách task triển khai

Nguồn hợp đồng: [`../ke-hoach-trien-khai.md`](../ke-hoach-trien-khai.md). Mỗi file bên dưới là **một kết quả công việc** để giao cho một agent. Agent chỉ đánh dấu `[x]` sau khi đã thực hiện và kiểm tra mục tương ứng; ghi bằng chứng ngắn ở cuối file. Không đánh dấu task hoàn thành chỉ vì mã đã được viết.

| ID | Task | Phụ thuộc | Trạng thái |
| --- | --- | --- | --- |
| T01 | [Khởi tạo Product Service](T01-khoi-tao-product-service.md) | — | Hoàn thành |
| T02 | [Endpoint xác minh JWT ở Auth Service](T02-xac-minh-jwt.md) | — | Hoàn thành |
| T03 | [Model và migration products](T03-model-products.md) | T01 | Hoàn thành |
| T04 | [Serializer và kiểm tra dữ liệu](T04-serializer-products.md) | T03 | Hoàn thành |
| T05 | [Xác thực từ xa ở Product Service](T05-xac-thuc-tu-xa.md) | T01, T02 | Hoàn thành |
| T06 | [GET /products](T06-danh-sach-products.md) | T03, T04, T05 | Hoàn thành |
| T07 | [GET /products/{id}](T07-chi-tiet-product.md) | T03, T04, T05 | Hoàn thành |
| T08 | [POST /products](T08-tao-product.md) | T03, T04, T05 | Hoàn thành |
| T09 | [PUT /products/{id}](T09-cap-nhat-product.md) | T03, T04, T05 | Hoàn thành |
| T10 | [DELETE /products/{id}](T10-xoa-product.md) | T03, T05 | Hoàn thành |
| T11 | [Hướng dẫn chạy và gọi API](T11-tai-lieu-van-hanh.md) | T01–T10 | Hoàn thành |
| T13 | [Tạo DB người dùng bài 2](T13-tao-db-auth.md) | T02 | Hoàn thành |
| T12 | [Kiểm thử tích hợp hai service](T12-kiem-thu-tich-hop.md) | T01–T11, T13 | Hoàn thành |

## Cách làm việc

1. Nhận một task khi các phụ thuộc của nó đã hoàn thành. T02 có thể làm song song T01; T06–T10 có thể làm song song sau T03–T05, nhưng các agent phải thống nhất cách khai báo URL để tránh sửa cùng một file.
2. Đọc hợp đồng trong kế hoạch và phạm vi file của task. Chỉ thay đổi ngoài phạm vi khi cần để hoàn thành chính task đó, rồi ghi lý do vào mục Ghi chú của file task.
3. Tạo kiểm thử có ý nghĩa cho kết quả của task; chạy kiểm thử liên quan và ghi lệnh/kết quả.
4. Đánh dấu các checklist, cập nhật trạng thái của dòng task trong bảng này thành `Hoàn thành`. Nếu bị chặn, giữ checkbox chưa đạt và ghi rõ điều kiện còn thiếu.
5. T13 tạo DB người dùng riêng và tài khoản thử theo yêu cầu mới của người dùng; T12 chạy kiểm thử tích hợp thật sau T13. Các task T01–T11 vẫn kiểm thử bằng mock/fixture.

Không thay đổi [`../ke-hoach-trien-khai.md`](../ke-hoach-trien-khai.md) khi triển khai, trừ khi người yêu cầu đổi nghiệp vụ; khi đó cập nhật hợp đồng trước rồi điều chỉnh task bị ảnh hưởng.
