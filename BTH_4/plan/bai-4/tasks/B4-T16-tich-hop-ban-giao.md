# B4-T16 — Tích hợp thật và bàn giao

Trạng thái: **Hoàn thành**. Phụ thuộc: B4-T14, B4-T15.

## Mục tiêu và phạm vi

Chứng minh ba service thật hoạt động cùng nhau, đối chiếu đầy đủ yêu cầu PDF và bàn giao source/tài liệu. Không thay đổi hợp đồng để bỏ qua lỗi demo.

## Các bước

- [x] Kiểm tra cổng 8000/8001/8002; tái sử dụng process đúng service nếu có, không tự dừng process không rõ nguồn.
- [x] Chuẩn bị credential local hợp lệ theo cơ chế Auth đã có; không in bí mật. Nếu thiếu credential thật sự cần người dùng, ghi rõ điều kiện thiếu.
- [x] Chạy ba service bằng đúng môi trường; nếu cần background process trên Windows thì chạy hidden và ghi nhận process do mình tạo.
- [x] Chạy smoke script qua HTTP thật, xác nhận cả 10 API cùng các tình huống thiếu tồn/token lỗi.
- [x] Kiểm tra DB Order riêng, giá snapshot, tổng tiền, rollback lỗi; xác nhận Product.quantity không đổi theo phương án đã duyệt.
- [x] Dọn dữ liệu thử theo ID do mình tạo; dừng các process chỉ phục vụ test do mình khởi tạo sau khi kết thúc, trừ khi người dùng cần giữ để demo.
- [x] Đối chiếu từng yêu cầu hai trang PDF với file/API/test tương ứng; ghi báo cáo ngắn tại plan/bai-4/ket-qua-kiem-thu.md.
- [x] Cập nhật checklist/trạng thái task theo bằng chứng, tóm tắt thay đổi, cách chạy và giới hạn thực tế.

## Nghiệm thu

- [x] Đủ 10 API đã gọi thật, JWT Auth và Product stock check hoạt động qua HTTP.
- [x] Tests tự động và hồi quy đã pass; không coi mock test là bằng chứng chạy 3 service thật.
- [x] Không còn lỗi chặn yêu cầu PDF; mọi giới hạn hoặc phần chưa chạy phải được nêu rõ, không đánh dấu hoàn thành thay.
- [x] Bàn giao link source chính, migration, tài liệu, script và kết quả kiểm chứng; không commit DB/credential/venv.

## Bằng chứng

2026-11-02: Started Auth8000/Product8001/Order8002 in hidden processes with --noreload, using existing separate service environments. Ran scripts/smoke-order-service.ps1 -EvidencePath plan/bai-4/smoke-result.json: 62 checks passed, all10 APIs exercised through actual HTTP, cleanup_errors empty. Baseline row hashes of products/orders/order_items unchanged after cleanup. Stopped only recorded parent/child processes created by this run; no listener left on8000/8001/8002. No credential/token output. Requirement mapping and complete commands recorded in ../ket-qua-kiem-thu.md. Full automated suites: Order82, Auth7, Product41 all passed.
