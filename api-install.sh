#!/bin/bash

# Konfigurasi Dasar
API_DIR="/etc/vpn-api"
SERVICE_FILE="/etc/systemd/system/vpn-api.service"
APP_DIR="$API_DIR/api"  # Direktori untuk aplikasi modular

# Fungsi Log
log_install() {
    echo "[API INSTALL] $1"
}

# Validasi Root
if [[ $EUID -ne 0 ]]; then
   log_install "Script harus dijalankan sebagai root"
    exit 1
fi

# Instalasi Dependensi
install_dependencies() {
    log_install "Menginstall dependensi Python"
    
    # Update paket
    apt update
    
    # Instalasi dependensi sistem
    apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        jq \
        uuid-runtime \
        curl \
        wget \
        git \
        build-essential
    
    # Buat virtual environment
    python3 -m venv /opt/vpn-api-env
    
    # Aktifkan virtual environment
    source /opt/vpn-api-env/bin/activate
    
    # Instalasi pip
    pip install --upgrade pip
    
    # Instalasi dependensi Python
    pip install \
        flask \
        gunicorn \
        requests \
        python-dotenv \
        pyyaml
    
    # Kembalikan ke shell normal
    deactivate
}

# Persiapan Direktori
prepare_directory() {
    log_install "Menyiapkan direktori API"
    mkdir -p "$APP_DIR" "$API_DIR/logs"
    mkdir -p /usr/local/sbin
    
    # Buat struktur folder modular
    mkdir -p "$APP_DIR"/{config,utils,services,routes}
    
    # Buat __init__.py untuk setiap folder
    touch "$APP_DIR"/{config,utils,services,routes}/__init__.py
    
    # Buat direktori log
    mkdir -p /var/log/vpn-api
    chown -R root:root /var/log/vpn-api
    chmod -R 755 /var/log/vpn-api
    
    # Buat direktori limit untuk quota
    log_install "Menyiapkan direktori limit untuk quota"
    mkdir -p /etc/limit/{vmess,vless,trojan}
    chmod -R 755 /etc/limit
}

# Download File Modular
download_modular_files() {
    log_install "Mengunduh file modular API"
    
    # Base URL GitHub
    BASE_URL="https://raw.githubusercontent.com/zxeeds/vip-script/main/api"
    
    # File utama
    wget -q -O "$APP_DIR/app.py" "$BASE_URL/app.py"
    
    # Config
    wget -q -O "$APP_DIR/config/config_manager.py" "$BASE_URL/config/config_manager.py"
    wget -q -O "$API_DIR/config.json" "$BASE_URL/config.json"  # Unduh config.json dari GitHub
    
    # Utils
    wget -q -O "$APP_DIR/utils/logger.py" "$BASE_URL/utils/logger.py"
    wget -q -O "$APP_DIR/utils/validators.py" "$BASE_URL/utils/validators.py"
    wget -q -O "$APP_DIR/utils/subprocess_utils.py" "$BASE_URL/utils/subprocess_utils.py"
    
    # Services
    wget -q -O "$APP_DIR/services/user_service.py" "$BASE_URL/services/user_service.py"
    wget -q -O "$APP_DIR/services/quota_service.py" "$BASE_URL/services/quota_service.py"  # Tambahkan quota service
    
    # Routes
    wget -q -O "$APP_DIR/routes/user_routes.py" "$BASE_URL/routes/user_routes.py"
    wget -q -O "$APP_DIR/routes/health_routes.py" "$BASE_URL/routes/health_routes.py"
    wget -q -O "$APP_DIR/routes/quota_routes.py" "$BASE_URL/routes/quota_routes.py"  # Tambahkan quota routes
    
    # Generate API key dan perbarui config.json
    API_KEY=$(openssl rand -hex 32)
    
    # Perbarui API key di config.json yang diunduh
    if [ -f "$API_DIR/config.json" ]; then
        # Gunakan jq untuk memperbarui API key
        jq --arg key "$API_KEY" '.api_key = $key' "$API_DIR/config.json" > "$API_DIR/config.json.tmp"
        mv "$API_DIR/config.json.tmp" "$API_DIR/config.json"
    else
        # Jika file tidak ada, buat config.json baru
        log_install "PERINGATAN: config.json tidak ditemukan, membuat file baru"
        cat > "$API_DIR/config.json" << EOL
{
  "api_key": "$API_KEY",
  "allowed_ips": ["127.0.0.1"],
  "protocols_allowed": ["vmess", "vless", "trojan", "ssh"],
  "port": 8082,
  "log_dir": "/var/log/vpn-api",
  "default_quota": 100,
  "default_validity": 30,
  "max_ip_limit": 5
}
EOL
    fi
    
    # Set permissions
    chmod 644 "$APP_DIR/app.py"
    chmod 600 "$API_DIR/config.json"
    
    # Catat API key
    echo "Generated API Key: $API_KEY" > "$API_DIR/api_key.txt"
    chmod 600 "$API_DIR/api_key.txt"
    
    log_install "API Key berhasil digenerate"
}

# Buat Systemd Service
create_systemd_service() {
    log_install "Membuat Systemd Service"
    cat > "$SERVICE_FILE" << EOL
[Unit]
Description=VPN API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
Environment="PYTHONPATH=$APP_DIR"
Environment="FLASK_APP=app.py"
ExecStart=/opt/vpn-api-env/bin/gunicorn \\
    --bind 0.0.0.0:8082 \\
    --workers 2 \\
    --threads 4 \\
    --timeout 120 \\
    --log-level debug \\
    --access-logfile /var/log/vpn-api/access.log \\
    --error-logfile /var/log/vpn-api/error.log \\
    --capture-output \\
    app:app
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL
}

# Konfigurasi Firewall
configure_firewall() {
    log_install "Mengkonfigurasi Firewall"
    
    # UFW
    if command -v ufw &> /dev/null; then
        ufw allow 8082/tcp
        ufw reload
    fi
    
    # Firewalld
    if command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=8082/tcp
        firewall-cmd --reload
    fi
}

# Aktifkan Service
enable_service() {
    log_install "Mengaktifkan VPN API Service"
    systemctl daemon-reload
    systemctl enable vpn-api
    systemctl start vpn-api
}

# Verifikasi Instalasi
verify_installation() {
    log_install "Verifikasi instalasi"
    
    # Cek service status
    if ! systemctl is-active --quiet vpn-api; then
        log_install "ERROR: Service tidak berjalan"
        journalctl -u vpn-api -n 20 --no-pager
        exit 1
    fi
    
    # Test endpoint dasar
    API_KEY=$(jq -r '.api_key' $API_DIR/config.json)
    response=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: $API_KEY" http://localhost:8082/api/ping)
    
    if [ "$response" != "200" ]; then
        log_install "ERROR: Test endpoint gagal (HTTP $response)"
        tail -n 20 /var/log/vpn-api/error.log
        exit 1
    fi
    
    log_install "Verifikasi berhasil"
}

# Proses Utama
main() {
    install_dependencies
    prepare_directory
    download_modular_files
    create_systemd_service
    configure_firewall
    enable_service
    verify_installation
    
    log_install "Instalasi API VPN Selesai"
    log_install "API berjalan di port 8082"
    log_install "Struktur modular terinstall di: $APP_DIR"
    log_install "Script CLI terinstall di: /usr/local/sbin"
    
    # Tampilkan API key
    echo "=============================================="
    echo "API Key tersimpan di: $API_DIR/api_key.txt"
    echo "Gunakan header berikut untuk akses API:"
    echo "Authorization: $(cat $API_DIR/api_key.txt | cut -d' ' -f3)"
    echo "=============================================="
    
    # Tampilkan informasi endpoint quota
    echo "Endpoint Quota yang tersedia:"
    echo "- GET /api/quota/<username>/<protocol> - Mendapatkan kuota pengguna"
    echo "- GET /api/quota/all/<protocol> - Mendapatkan kuota semua pengguna untuk protokol tertentu"
    echo "- GET /api/quota/summary - Mendapatkan ringkasan kuota untuk semua protokol"
    echo "=============================================="
}

# Jalankan
main
