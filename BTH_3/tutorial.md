# BÀI THỰC HÀNH SỐ 3
## Xây dựng dịch vụ quản lý sản phẩm (Product Management)

### Mục tiêu:
* Xây dựng dịch vụ quản lý sản phẩm (tạo, xem, cập nhật, xóa sản phẩm).
* Dịch vụ hoạt động độc lập trên một cổng và cơ sở dữ liệu riêng (tuân theo nguyên tắc của kiến trúc SOA).

### Thực hiện:
* Khởi tạo một cổng mới cho service. Ví dụ: `localhost:***1/`
* Thiết kế RESTful API cho dịch vụ quản lý sản phẩm:
  * `GET /products`: Lấy danh sách tất cả các sản phẩm.
  * `GET /products/id`: Lấy thông tin chi tiết một sản phẩm.
  * `POST /products`: Thêm một sản phẩm mới.
  * `PUT /products/id`: Cập nhật thông tin sản phẩm.
  * `DELETE /products/id`: Xóa một sản phẩm.
* Xây dựng controller xử lý nghiệp vụ và truy vấn dữ liệu theo yêu cầu của API ở trên.

> **Lưu ý:** Xác thực qua service đã xây dựng ở bài thực hành số 2.

---

### Phụ lục:

#### Bảng sản phẩm (products)

| Tên cột | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| **id** | INT (PRIMARY KEY) | ID duy nhất của sản phẩm |
| **name** | VARCHAR(255) | Tên sản phẩm |
| **description** | TEXT | Mô tả sản phẩm |
| **price** | DECIMAL(10, 2) | Giá sản phẩm |
| **quantity** | INT | Số lượng sản phẩm trong kho |
| **created_at** | TIMESTAMP | Ngày sản phẩm được tạo |
| **updated_at** | TIMESTAMP | Ngày sản phẩm được cập nhật lần cuối |