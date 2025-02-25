#!/bin/bash

# Konfigurasi Dasar
API_DIR="/etc/vpn-api"
SERVICE_FILE="/etc/systemd/system/vpn-api.service"

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
    apt update
    apt install -y python3 python3-pip jq uuid-runtime
    pip3 install flask
}

# Persiapan Direktori
prepare_directory() {
    log_install "Menyiapkan direktori API"
    mkdir -p "$API_DIR/logs"
    
    # Buat users.json jika belum ada
    if [[ ! -f "$API_DIR/users.json" ]]; then
        echo '{"users":[]}' > "$API_DIR/users.json"
    fi
}

# Konfigurasi File
configure_files() {
    log_install "Mengatur konfigurasi file"
    
    # Download app.py
    wget -O "$API_DIR/app.py" "https://raw.githubusercontent.com/zxeeds/vip-script/main/api/app.py"
    
    # Download api-management.sh
    wget -O "$API_DIR/api-management.sh" "https://raw.githubusercontent.com/zxeeds/vip-script/main/api/api-management.sh"
    chmod +x "$API_DIR/api-management.sh"
    
    # Download config.json
    wget -O "$API_DIR/config.json" "https://raw.githubusercontent.com/zxeeds/vip-script/main/api/config.json"
    chmod 644 "$API_DIR/config.json"
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
WorkingDirectory=$API_DIR
ExecStart=/usr/bin/python3 $API_DIR/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL
}

# Konfigurasi Firewall
configure_firewall() {
    log_install "Mengkonfigurasi Firewall"
    if command -v ufw &> /dev/null; then
        ufw allow 8080/tcp
    fi
}

# Aktifkan Service
enable_service() {
    log_install "Mengaktifkan VPN API Service"
    systemctl daemon-reload
    systemctl enable vpn-api
    systemctl start vpn-api
}

# Proses Utama
main() {
    install_dependencies
    prepare_directory
    configure_files
    create_systemd_service
    configure_firewall
    enable_service
    log_install "Instalasi API VPN Selesai"
}

# Jalankan
main
