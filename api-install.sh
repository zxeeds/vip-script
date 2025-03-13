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
        wget
    
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
        python-dotenv
    
    # Kembalikan ke shell normal
    deactivate
}

# Persiapan Direktori
prepare_directory() {
    log_install "Menyiapkan direktori API"
    mkdir -p "$API_DIR/logs"
    
    # Buat users.json jika belum ada
    if [[ ! -f "$API_DIR/users.json" ]]; then
        echo '[]' > "$API_DIR/users.json"
        chmod 644 "$API_DIR/users.json"
    fi
}

# Konfigurasi File
configure_files() {
    log_install "Mengatur konfigurasi file"
    
    # Generate API key
    API_KEY=$(openssl rand -hex 32)
    
    # Download app.py
    wget -O "$API_DIR/app.py" "https://raw.githubusercontent.com/zxeeds/vip-script/main/api/app.py"
    
    # Download config.json template
    wget -O "$API_DIR/config.json" "https://raw.githubusercontent.com/zxeeds/vip-script/main/api/config.json"
    
    # Modifikasi config.json dengan API key baru menggunakan sed
    sed -i "s/\"api_key\": \"[^\"]*\"/\"api_key\": \"$API_KEY\"/g" "$API_DIR/config.json"
    
    # Set permissions
    chmod 644 "$API_DIR/app.py"
    chmod 600 "$API_DIR/config.json"
    
    # Catat API key (opsional, untuk referensi)
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
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$API_DIR
Environment=PATH=/opt/vpn-api-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=$API_DIR
ExecStart=/opt/vpn-api-env/bin/gunicorn \
    --bind 0.0.0.0:8082 \
    --workers 2 \
    --threads 4 \
    --log-level=debug \
    --log-file=$API_DIR/logs/gunicorn.log \
    --capture-output \
    --enable-stdio-inheritance \
    app:app

Restart=always
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

# Proses Utama
main() {
    install_dependencies
    prepare_directory
    configure_files
    create_systemd_service
    configure_firewall
    enable_service
    
    log_install "Instalasi API VPN Selesai"
    log_install "API berjalan di port 8082"

    # Tampilkan API key
    echo "API Key tersimpan di: $API_DIR/api_key.txt"
    cat "$API_DIR/api_key.txt"

}

# Jalankan
main
