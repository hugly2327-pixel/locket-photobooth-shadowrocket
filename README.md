# Locket Photobooth + Shadowrocket DNS

Repository gộp hai phần:

1. **Locket Photobooth** — Flask backend + giao diện web, deploy lên Google Cloud Run.
2. **Shadowrocket DNS** — module `.sgmodule` dùng Cloudflare DoH và Google DoH fallback trên iPhone.

## Cấu trúc

- `app.py`, `static/`, `requirements.txt`, `Dockerfile`: ứng dụng Photobooth.
- `README_CLOUD_RUN_VI.md`: hướng dẫn triển khai backend.
- `shadowrocket/modules/locket-photobooth-dns.sgmodule`: module Shadowrocket.
- `shadowrocket/README_SHADOWROCKET_VI.md`: hướng dẫn cài module và thêm rule domain Photobooth.
- `DEPLOY_CHECKLIST_CLOUD_RUN.txt`: checklist triển khai.

## Cách dùng nhanh

1. Tạo GitHub repository. Khuyến nghị để **Private** vì đây là backend xử lý đăng nhập Locket.
2. Upload toàn bộ nội dung repository.
3. Làm theo `README_CLOUD_RUN_VI.md` để deploy Cloud Run.
4. Sau khi có hostname `*.run.app`, làm theo `shadowrocket/README_SHADOWROCKET_VI.md` để thêm rule domain thật vào module.
5. Cài module vào Shadowrocket bằng link Raw GitHub hoặc tải file `.sgmodule` về iPhone.

## Phân biệt vai trò

- GitHub chỉ lưu và phân phối mã nguồn/module.
- Cloud Run chạy website/backend Photobooth.
- Cloud Storage giữ session Locket qua lần khởi động lại.
- Shadowrocket dùng DNS-over-HTTPS và rule định tuyến trên iPhone.

Module DNS không làm backend chạy và không tạo proxy/VPN node.

## Cảnh báo

`locketlam` là SDK không chính thức, reverse-engineered. Chưa có kiểm thử end-to-end với tài khoản Locket thật hoặc xác nhận Locket sẽ chấp nhận các thao tác từ SDK. Không đưa mật khẩu Locket, OTP, token, cookie hay session file lên GitHub. Đặt mật khẩu riêng cho website qua Secret Manager.
