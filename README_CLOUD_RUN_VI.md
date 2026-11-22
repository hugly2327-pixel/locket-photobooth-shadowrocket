# Locket Photobooth — GitHub + Google Cloud Run

Bản này gộp website/backend Photobooth và module DNS Shadowrocket trong cùng một repository GitHub. GitHub lưu mã nguồn; Google Cloud Run chạy backend Python công khai. Không dùng Render. Cloud Run cấp URL HTTPS dạng `https://...run.app`.

> **Quan trọng:** Cloud Run có hạn mức miễn phí nhưng cần Google Cloud project bật billing. Vượt hạn mức miễn phí, dùng Cloud Storage ngoài hạn mức hoặc phát sinh dịch vụ khác có thể bị tính phí. Hãy tạo ngân sách cảnh báo và kiểm tra Billing. Ngân sách cảnh báo không tự động chặn chi phí.

## Kiến trúc

- GitHub: lưu backend, giao diện và module Shadowrocket trong cùng repository (khuyến nghị Private cho mã nguồn backend).
- Google Cloud Run: chạy Flask + `locketlam`.
- Google Cloud Storage bucket riêng tư: lưu file session `locketlam_session.json` qua volume mount.
- `shadowrocket/modules/locket-photobooth-dns.sgmodule`: module DoH để cài trên iPhone; sau khi có URL Cloud Run, thêm rule hostname theo hướng dẫn trong `shadowrocket/README_SHADOWROCKET_VI.md`.
- Cloud Run chỉ chạy tối đa 1 instance, concurrency 1 để tránh nhiều bản SDK cùng ghi một file session.
- File ảnh/video tải lên chỉ nằm tạm trong `/tmp`, sau khi gửi sẽ bị xóa.
- Website được bảo vệ bằng HTTP Basic Auth qua `APP_USERNAME` và `APP_PASSWORD`.

## 1. Đưa mã nguồn lên GitHub

1. Tạo repository **Private** tại https://github.com/new
2. Giải nén ZIP, upload toàn bộ nội dung thư mục này lên repository.
3. Không upload `.env`, `data/`, session JSON, mật khẩu hoặc token.

## 2. Tạo Google Cloud project và bật API

1. Mở https://console.cloud.google.com/
2. Tạo project mới, liên kết billing account.
3. Chọn project đó ở thanh trên cùng.
4. Mở Cloud Shell (biểu tượng `>_`) và chạy các lệnh dưới đây.

Cài biến môi trường trong Cloud Shell (đổi `PROJECT_ID` thành ID project của bạn; `BUCKET_NAME` phải là tên duy nhất toàn cầu):

```bash
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com storage.googleapis.com secretmanager.googleapis.com
```

Chọn region gần Việt Nam, ví dụ Singapore:

```bash
gcloud config set run/region asia-southeast1
```

Tạo bucket riêng tư để giữ session. Tên bucket chỉ dùng chữ thường, số và dấu gạch ngang:

```bash
gcloud storage buckets create gs://BUCKET_NAME --location=ASIA-SOUTHEAST1 --uniform-bucket-level-access
```

## 3. Tạo mật khẩu website dưới dạng Secret

Chọn username và mật khẩu mạnh, riêng cho website. Không dùng mật khẩu Locket. Tạo secrets bằng lệnh (thay giá trị mẫu; không commit chúng lên GitHub):

```bash
printf '%s' 'TEN_DANG_NHAP_RIENG' | gcloud secrets create locket-app-username --data-file=-
printf '%s' 'MAT_KHAU_RIENG_DAI_VA_KHO_DOAN' | gcloud secrets create locket-app-password --data-file=-
```

Nếu secret đã tồn tại, dùng `gcloud secrets versions add SECRET_NAME --data-file=-` thay cho `create`.

## 4. Deploy từ mã nguồn trong Cloud Shell

Clone repository Private vào Cloud Shell. GitHub sẽ yêu cầu xác thực; không đưa Personal Access Token vào lệnh được lưu hoặc chia sẻ.

```bash
git clone https://github.com/USERNAME/REPOSITORY.git
cd REPOSITORY
gcloud run deploy locket-photobooth --source . --region asia-southeast1 --allow-unauthenticated --port 8080 --memory 1Gi --cpu 1 --timeout 300 --concurrency 1 --max 1 --set-env-vars LOCKET_DATA_DIR=/mnt/locket-data,UPLOAD_TMP_DIR=/tmp/locket-uploads --set-secrets APP_USERNAME=locket-app-username:latest,APP_PASSWORD=locket-app-password:latest
```

`--allow-unauthenticated` chỉ cho phép request tới ứng dụng; chính Flask vẫn yêu cầu Basic Auth. Không bỏ lớp mật khẩu của ứng dụng.

## 5. Gắn bucket lưu session vào Cloud Run

Lấy service account mặc định của Cloud Run:

```bash
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format='value(projectNumber)')
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
```

Cấp quyền đọc/ghi object trong bucket:

```bash
gcloud storage buckets add-iam-policy-binding gs://BUCKET_NAME --member="serviceAccount:${RUNTIME_SA}" --role="roles/storage.objectAdmin"
```

Gắn bucket vào Cloud Run:

```bash
gcloud run services update locket-photobooth --region asia-southeast1 --execution-environment gen2 --add-volume mount-path=/mnt/locket-data,type=cloud-storage,bucket=BUCKET_NAME,readonly=false,mount-options="uid=10001;gid=10001"
```

Kiểm tra service:

```bash
gcloud run services describe locket-photobooth --region asia-southeast1 --format='value(status.url)'
```

Mở URL đó, trình duyệt sẽ hỏi username/password website.

## 6. Kiểm tra sau triển khai

- Mở `https://URL/healthz`: phải trả về `{"ok":true,...}`.
- Mở trang chủ: trình duyệt hỏi thông tin xác thực website.
- Đăng nhập Locket trong giao diện. Session được lưu ở bucket đã mount.
- Thử tải danh sách bạn bè, feed, rồi thử gửi một ảnh riêng tư trước khi gửi rộng hơn.

## 7. Quản lý chi phí và bảo mật

- Cloud Run có free tier theo tháng, bao gồm hạn mức request/CPU/RAM; mức miễn phí áp dụng theo điều kiện và khu vực. Google Cloud yêu cầu billing account. Kiểm tra trang giá hiện hành: https://cloud.google.com/run/pricing
- Cloud Storage có giá riêng; dung lượng, thao tác và mạng có thể phát sinh chi phí. Xem https://cloud.google.com/storage/pricing
- Tạo Budget & Alerts trong Billing. Cảnh báo ngân sách không phải hard spending cap.
- Giữ repository Private. Không chia sẻ bucket, session JSON, Secret Manager values hoặc log chứa thông tin nhạy cảm.
- Không bật nhiều instance: SDK hiện dùng một file session. Cloud Storage FUSE không cung cấp file locking cho nhiều writer.
- Nếu không dùng nữa, xóa Cloud Run service, bucket và secrets để tránh phát sinh chi phí.

## Giới hạn cần biết

1. `locketlam` là thư viện không chính thức, reverse-engineered; Locket có thể thay đổi API, xác minh bổ sung hoặc khóa phiên. Việc deploy thành công không chứng minh đăng nhập/post hoạt động.
2. Mật khẩu Locket được gửi từ trình duyệt tới backend của bạn qua HTTPS. Chỉ triển khai trên project và bucket do bạn kiểm soát.
3. Không gửi mật khẩu Locket, OTP, token, cookie hay file session cho người hỗ trợ.
4. Cloud Run scale-to-zero có thể có cold start. Phiên Locket vẫn được lưu trong bucket, nhưng app có thể cần khởi tạo client lại sau khi khởi động.
5. Không dùng dịch vụ này để chia sẻ tài khoản hoặc cho người khác đăng nhập vào Locket của bạn.

## Tài liệu chính thức

- Cloud Run deploy Python: https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service
- Cloud Run Cloud Storage volume: https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts
- Cloud Run pricing: https://cloud.google.com/run/pricing
- Secret Manager: https://cloud.google.com/secret-manager/docs
