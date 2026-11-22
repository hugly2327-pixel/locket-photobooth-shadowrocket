# Shadowrocket: Photobooth + DNS

Module: `modules/locket-photobooth-dns.sgmodule`

## Hiện module làm gì?

- Dùng Cloudflare DNS-over-HTTPS làm DNS chính.
- Dùng Google DNS-over-HTTPS làm DNS dự phòng.
- Có sẵn dòng hướng dẫn để thêm rule định tuyến riêng cho hostname Photobooth sau khi Cloud Run cấp URL.

**Chưa thể điền rule hostname chính xác** vì hostname Cloud Run chỉ xuất hiện sau khi bạn deploy. Không nên đoán hostname hoặc dùng rule `run.app` quá rộng vì có thể ảnh hưởng website Cloud Run khác.

## Cài từ GitHub

1. Đưa repository lên GitHub.
2. Mở file `shadowrocket/modules/locket-photobooth-dns.sgmodule`.
3. Chọn Raw và sao chép URL.
4. Trong Shadowrocket, vào Config/Modules và thêm module bằng URL; nếu app không hỗ trợ nhập URL ở mục này, tải file `.sgmodule` về iPhone rồi Share → Shadowrocket.
5. Bật module, reconnect và kiểm tra DNS.

Link Raw sẽ có dạng:

`https://raw.githubusercontent.com/GITHUB_USERNAME/REPOSITORY/main/shadowrocket/modules/locket-photobooth-dns.sgmodule`

Thay `GITHUB_USERNAME` và `REPOSITORY` bằng thông tin repository của bạn.

## Gắn rule Photobooth sau khi deploy

Khi Cloud Run cấp URL, ví dụ:

`https://locket-photobooth-abc123-as.a.run.app`

hostname là:

`locket-photobooth-abc123-as.a.run.app`

Mở file module, trong phần `[Rule]` thêm:

```ini
[Rule]
DOMAIN,locket-photobooth-abc123-as.a.run.app,DIRECT
```

Thay hostname ví dụ bằng hostname thật của bạn. Commit thay đổi lên GitHub, sau đó cập nhật module trong Shadowrocket.

Nếu muốn website đi qua proxy, đổi `DIRECT` thành tên policy proxy đã tồn tại trong cấu hình Shadowrocket của bạn. Không tự dùng `PROXY` nếu config của bạn không có policy tên đó.

## Lưu ý

- DNS chỉ phân giải tên miền; Rule quyết định kết nối đi DIRECT hay qua policy proxy.
- Module này không tạo VPN/proxy node và không thay thế backend Cloud Run.
- Module DNS dùng resolver công cộng, không phải authoritative DNS riêng cho tên miền.
- Không thay toàn bộ cấu hình Shadowrocket hiện có bằng file snippet DNS.
