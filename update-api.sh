#!/bin/bash

# ==============================================================================
# Script Update API VPN
# Memperbarui instalasi API dari repository dengan aman
# ==============================================================================

# --- Warna untuk Output ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Konfigurasi Dasar ---
API_DIR="/etc/vpn-api"      # Direktori ROOT proyek
APP_DIR="$API_DIR/api"       # Direktori APLIKASI
SERVICE_NAME="vpn-api"
REPO_URL="https://raw.githubusercontent.com/zxeeds/vip-script/main/api"

# --- Fungsi Bantuan ---

# Fungsi untuk logging
log_update() {
    local level="$1"
    local message="$2"
    
    case "$level" in
        "info")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        "success")
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        "warning")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        "error")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
    esac
}

# Fungsi untuk memeriksa apakah layanan berjalan
is_service_running() {
    systemctl is-active --quiet "$SERVICE_NAME"
}

# --- Proses Utama ---

# 1. Pemeriksaan Awal
pre_update_checks() {
    log_update "info" "Memulai pemeriksaan awal..."
    
    if [[ $EUID -ne 0 ]]; then
        log_update "error" "Script harus dijalankan sebagai root."
        exit 1
    fi

    if [ ! -d "$API_DIR" ]; then
        log_update "error" "Direktori API tidak ditemukan di $API_DIR. Jalankan script install terlebih dahulu."
        exit 1
    fi
    
    log_update "success" "Pemeriksaan awal selesai."
}

# 2. Backup Instalasi Lama
backup_current_installation() {
    local backup_dir="${API_DIR}.backup.$(date +%s)"
    log_update "info" "Membuat backup instalasi lama di $backup_dir..."
    
    if cp -r "$API_DIR" "$backup_dir"; then
        log_update "success" "Backup berhasil dibuat."
        echo "$backup_dir" > /tmp/api_backup_path
    else
        log_update "error" "Gagal membuat backup. Proses dibatalkan."
        exit 1
    fi
}

# 3. Hentikan Layanan
stop_service() {
    log_update "info" "Menghentikan layanan $SERVICE_NAME..."
    systemctl stop "$SERVICE_NAME"
    
    # Tunggu sebentar hingga layanan benar-benar berhenti
    local count=0
    while is_service_running && [ $count -lt 10 ]; do
        sleep 1
        ((count++))
    done
    
    if is_service_running; then
        log_update "error" "Gagal menghentikan layanan $SERVICE_NAME."
        exit 1
    else
        log_update "success" "Layanan $SERVICE_NAME telah dihentikan."
    fi
}

# 4. Unduh File Baru
download_new_files() {
    log_update "info" "Mengunduh file-file baru dari repository..."
    
    # --- PERUBAHAN: Unduh file aplikasi ke dalam folder /api ---
    # File utama aplikasi
    wget -q -O "$APP_DIR/app.py" "$REPO_URL/app.py"
    
    # --- PERUBAHAN: Unduh file-file modul aplikasi ke dalam folder /api ---
    # Gunakan loop untuk mempermudah
    local subdirs=("config" "utils" "services" "routes")
    for subdir in "${subdirs[@]}"; do
        # Buat direktori jika tidak ada
        mkdir -p "$APP_DIR/$subdir"
        # Unduh semua file .py dari subdirektori repo
        wget -q -r -np -nH --cut-dirs -A "*.py" -P "$APP_DIR/$subdir/" "$REPO_URL/$subdir/"
    done
    
    # --- PERUBAHAN: Jangan unduh config.json untuk menjaga pengaturan pengguna ---
    log_update "warning" "File config.json tidak diunduh untuk menjaga pengaturan Anda yang ada."
    
    log_update "success" "File-file baru berhasil diunduh."
}

# 5. Perbarui Dependensi
update_dependencies() {
    log_update "info" "Memperbarui dependensi Python..."
    
    # Aktifkan virtual environment
    source /opt/vpn-api-env/bin/activate
    
    # Install package dalam mode editable untuk memperbarui dependensi
    if pip install -e "$API_DIR"; then
        log_update "success" "Dependensi berhasil diperbarui."
    else
        log_update "error" "Gagal memperbarui dependensi."
        deactivate
        return 1
    fi
    
    # Kembalikan ke shell normal
    deactivate
}

# 6. Install Versi Baru
install_new_version() {
    log_update "info" "Menginstall versi baru aplikasi..."
    
    # Aktifkan virtual environment
    source /opt/vpn-api-env/bin/activate
    
    # Install package dalam mode editable
    if pip install -e "$API_DIR"; then
        log_update "success" "Aplikasi versi baru berhasil diinstall."
        deactivate
    else
        log_update "error" "Gagal menginstall versi baru aplikasi."
        deactivate
        return 1
    fi
}

# 7. Mulai Ulang Layanan
start_service() {
    log_update "info" "Memulai ulang layanan $SERVICE_NAME..."
    systemctl start "$SERVICE_NAME"
    
    # Tunggu sebentar hingga layanan berjalan
    sleep 5
    
    if is_service_running; then
        log_update "success" "Layanan $SERVICE_NAME berhasil dimulai."
    else
        log_update "error" "Gagal memulai layanan $SERVICE_NAME."
        return 1
    fi
}

# 8. Verifikasi Pembaruan
verify_update() {
    log_update "info" "Memverifikasi pembaruan..."
    
    # Dapatkan API key dari config yang ada
    local api_key=$(jq -r '.api_key' "$API_DIR/config.json")
    
    # Test endpoint dasar
    local response=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: $api_key" http://localhost:8082/api/ping)
    
    if [ "$response" == "200" ]; then
        log_update "success" "Verifikasi berhasil. API berjalan dengan normal."
        return 0
    else
        log_update "error" "Verifikasi gagal. API mengembalikan status $response."
        return 1
    fi
}

# 9. Kembalikan ke Versi Lama (Rollback)
rollback_update() {
    local backup_dir=$(cat /tmp/api_backup_path)
    log_update "error" "Terjadi kesalahan. Melakukan rollback ke versi lama dari $backup_dir..."
    
    stop_service
    
    # Hapus instalasi yang rusak
    rm -rf "$API_DIR"
    
    # Kembalikan dari backup
    if mv "$backup_dir" "$API_DIR"; then
        log_update "success" "Rollback berhasil."
    else
        log_update "error" "Rollback gagal. Sistem mungkin dalam keadaan tidak stabil."
        exit 1
    fi
    
    start_service
    log_update "warning" "Sistem telah dikembalikan ke versi sebelumnya."
}

# 10. Bersihkan Backup
cleanup_backup() {
    local backup_dir=$(cat /tmp/api_backup_path)
    log_update "info" "Membersihkan backup..."
    rm -rf "$backup_dir"
    rm -f /tmp/api_backup_path
    log_update "success" "Backup telah dibersihkan."
}

# --- Fungsi Utama ---
main() {
    clear
    echo "=========================================================="
    echo "        UPDATE API VPN"
    echo "=========================================================="
    echo

    pre_update_checks
    backup_current_installation
    stop_service
    
    # Jika download atau update dependensi gagal, lakukan rollback
    if ! download_new_files || ! update_dependencies; then
        rollback_update
        exit 1
    fi
    
    start_service
    
    # Jika verifikasi gagal, lakukan rollback
    if ! verify_update; then
        rollback_update
        exit 1
    fi
    
    cleanup_backup
    
    echo
    echo "=========================================================="
    log_update "success" "Update API VPN berhasil diselesaikan!"
    echo "=========================================================="
    echo "Struktur aplikasi berada di: $APP_DIR"
    echo "Konfigurasi utama ada di: $API_DIR/config.json"
    echo "Jika ada masalah, Anda dapat memulihkan dari file backup yang dibuat."
    echo
}

# Jalankan fungsi utama
main