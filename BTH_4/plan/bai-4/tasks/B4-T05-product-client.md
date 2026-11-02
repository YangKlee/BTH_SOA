# B4-T05 — Client Product và kiểm tra tồn

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T01, B4-T04.

## Mục tiêu và phạm vi

Một HTTP client duy nhất lấy sản phẩm và snapshot phục vụ mọi thao tác Order. Phạm vi: orders/clients/product.py, kiểu lỗi dùng chung, tests/test_product_client.py.

## Các bước

- [x] Gọi GET {PRODUCT_SERVICE_URL}/products/{id}, chuyển tiếp access token từ request.auth, có timeout hữu hạn.
- [x] Kiểm tra id trả về khớp request; name hợp lệ; price parse Decimal hữu hạn, không âm, đúng phạm vi; quantity là integer không âm.
- [x] Cung cấp hàm kiểm tra requested quantity <= available quantity; lỗi thiếu tồn có product_id, số yêu cầu và tồn hiện tại.
- [x] Ánh xạ product 404 -> lỗi input 400; upstream 401 -> 401; timeout/mạng/5xx/phản hồi khác hợp đồng -> 503.
- [x] Không gọi PUT Product, không ghi DB Product, không tự retry thao tác ghi.

## Nghiệm thu

- [x] Test đủ tồn, tồn bằng 0, thiếu tồn, product không tồn tại, token hết hạn giữa luồng, timeout và JSON/schema/Decimal sai.
- [x] Kiểm tra URL, header và timeout gửi đi bằng mock.
- [x] Không chấp nhận price hoặc tên sản phẩm từ payload client làm snapshot.

## Bằng chứng

Ngày kiểm chứng: 2026-11-02. Chạy từ `services/order-service`:

```powershell
& ./.venv/Scripts/python.exe manage.py test orders.tests.test_authentication orders.tests.test_product_client --verbosity 2
```

Kết quả: 18 tests pass, gồm 9 tests Product với các subtests malformed schema/type/price và lỗi mạng/HTTP. Client chỉ nhận product_id/token, snapshot bất biến lấy duy nhất từ HTTP Product. `OrderAPIError` giữ nguyên kiểu số cho product_id/requested_quantity/available_quantity. Không truy cập DB hoặc có API ghi kho. Phạm vi bổ sung `orders/clients/http.py` dùng chung cho Auth/Product để chặn redirect làm chuyển Bearer sang địa chỉ khác.
