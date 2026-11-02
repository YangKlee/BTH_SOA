# T04 — Serializer và kiểm tra dữ liệu sản phẩm

**Kết quả duy nhất:** serializer nhận/trả sản phẩm đúng hợp đồng JSON và từ chối dữ liệu sai.

**Phụ thuộc:** T03. **Phạm vi:** serializer và test serializer; chưa thêm endpoint.

## Checklist

- [x] `POST` và `PUT` yêu cầu đủ `name`, `description`, `price`, `quantity`.
- [x] Trim tên/mô tả; từ chối chuỗi rỗng hoặc toàn khoảng trắng; tên tối đa 255 ký tự.
- [x] Kiểm tra giá không âm, tối đa `99999999.99`, tối đa hai chữ số thập phân; xuất JSON dạng chuỗi có hai chữ số thập phân.
- [x] Kiểm tra quantity là số nguyên không âm; không nhận boolean hay số thập phân.
- [x] Từ chối field lạ và `id`, `created_at`, `updated_at` trong dữ liệu ghi; chỉ xuất các field này khi đọc.
- [x] Test cả dữ liệu hợp lệ, dữ liệu biên, dữ liệu thiếu/sai kiểu và tên trùng.

## Hoàn thành khi

Serializer thực thi toàn bộ quy tắc mục 4–5 của kế hoạch với lỗi theo tên trường.

## Bằng chứng / ghi chú của agent

- `products/serializers.py`: `ProductSerializer` dùng các field bắt buộc cho tạo/cập nhật đầy đủ; chuỗi phải đúng kiểu và được trim; quantity phải là JSON integer thực sự (không bool/float/string); `price` là decimal chính xác, xuất chuỗi 2 chữ số thập phân. `to_internal_value` trả lỗi theo tên field đối với mọi field lạ/chỉ đọc.
- `products/test_serializers.py`: 8 test cho tạo/đọc, cập nhật đầy đủ, thiếu field ở POST/PUT, biên giá và quantity, kiểu sai, tên trùng và các field bị cấm.
- Trong `services/product-service`, `.venv/Scripts/python.exe manage.py test products.test_serializers`: `Ran 8 tests ... OK`; `.venv/Scripts/python.exe manage.py check`: `System check identified no issues (0 silenced)`.
