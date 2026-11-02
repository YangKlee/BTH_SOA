# Task bài 4

**Hoàn thành 16/16 task ngày 02/11/2026 sau khi triển khai bằng sub-agent theo yêu cầu người dùng.** Hợp đồng: [Kế hoạch triển khai](../ke-hoach-trien-khai.md).

| ID | Kết quả công việc | Phụ thuộc | Trạng thái |
| --- | --- | --- | --- |
| B4-T01 | [Khởi tạo Order Service độc lập](B4-T01-khoi-tao-service.md) | Người dùng duyệt | Hoàn thành |
| B4-T02 | [Models, ràng buộc và migration](B4-T02-model-migration.md) | T01 | Hoàn thành |
| B4-T03 | [Serializers và validation](B4-T03-serializers-validation.md) | T02 | Hoàn thành |
| B4-T04 | [Xác thực qua Auth Service](B4-T04-xac-thuc.md) | T01 | Hoàn thành |
| B4-T05 | [Client Product và kiểm tra tồn](B4-T05-product-client.md) | T01, T04 | Hoàn thành |
| B4-T06 | [Nghiệp vụ, tính tiền và transaction](B4-T06-nghiep-vu-transaction.md) | T02, T03, T05 | Hoàn thành |
| B4-T07 | [POST /orders](B4-T07-tao-don.md) | T03, T04, T06 | Hoàn thành |
| B4-T08 | [GET danh sách và chi tiết orders](B4-T08-xem-don.md) | T02, T03, T04 | Hoàn thành |
| B4-T09 | [PUT trạng thái orders](B4-T09-trang-thai-don.md) | T04, T06, T07 | Hoàn thành |
| B4-T10 | [DELETE orders và cascade](B4-T10-xoa-don.md) | T04, T06, T07 | Hoàn thành |
| B4-T11 | [GET danh sách và chi tiết items](B4-T11-xem-items.md) | T02, T03, T04 | Hoàn thành |
| B4-T12 | [POST order_items](B4-T12-them-item.md) | T04, T06, T07 | Hoàn thành |
| B4-T13 | [PUT và DELETE order_items](B4-T13-sua-xoa-item.md) | T04, T06, T12 | Hoàn thành |
| B4-T14 | [Kiểm thử tổng hợp và hồi quy](B4-T14-kiem-thu.md) | T07–T13 | Hoàn thành |
| B4-T15 | [Tài liệu và script demo](B4-T15-tai-lieu-demo.md) | T07–T14 | Hoàn thành |
| B4-T16 | [Tích hợp thật và bàn giao](B4-T16-tich-hop-ban-giao.md) | T14, T15 | Hoàn thành |

Trong cột phụ thuộc, `Txx` là viết tắt của `B4-Txx` trong bộ task này, không phải task bài 3.

## Cách cập nhật khi được duyệt

1. Chuyển từng task đủ phụ thuộc sang `Đang làm`, thực hiện theo hợp đồng đã duyệt.
2. Không thêm quy tắc nghiệp vụ mới mà không cập nhật plan và ghi rõ lý do.
3. Checklist đang trống là công việc chưa làm; không đánh dấu dựa trên dự định hoặc chỉ có source.
4. Sau kiểm chứng, ghi lệnh, kết quả, ngày chạy và giới hạn còn lại trong mục Bằng chứng của từng file; cập nhật bảng này.
5. Không đụng vào bộ task bài 3. Chỉ sửa Auth/Product nếu thật sự cần để giữ hợp đồng tích hợp đã duyệt và giải thích thay đổi.
6. Phân công: foundation_api T01–T03 và T07–T13; integrations T04–T05; docs_smoke T15; agent chính T06/T14/T16. Triển khai song song phần độc lập theo yêu cầu mới của người dùng, nghiệm thu theo phụ thuộc.

Verification: Order 82 tests, Auth 7, Product 41 passed; 62 live HTTP smoke checks passed. See [report](../ket-qua-kiem-thu.md).
