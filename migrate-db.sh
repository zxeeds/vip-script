#!/bin/bash

# ==============================================================================
# Script Migrasi Akun ke Database Terpusat
# Memindahkan data dari database lama ke /etc/vpn/database.db
# ==============================================================================

# --- Warna untuk Output ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Konfigurasi Path dan Nilai Default ---
# Sumber database lama
VMESS_DB="/etc/vmess/.vmess.db"
VLESS_DB="/etc/vless/.vless.db"
TROJAN_DB="/etc/trojan/trojan.db"
SSH_DB="/etc/ssh/.ssh.db"

# Tujuan database terpusat
DEST_DB="/etc/vpn/database.db"

# Nilai default untuk akun yang dimigrasi
QUOTA_GB=200
QUOTA_BYTES=$(($QUOTA_GB * 1024 * 1024 * 1024)) # 200 GB dalam bytes
IP_LIMIT=2

# --- Fungsi Bantuan ---

# Fungsi untuk logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fungsi untuk memeriksa ketergantungan
check_dependencies() {
    if ! command -v sqlite3 &> /dev/null; then
        log_error "sqlite3 tidak terinstall. Silakan install terlebih dahulu."
        echo "  Ubuntu/Debian: sudo apt update && sudo apt install sqlite3"
        exit 1
    fi
}

# Fungsi untuk memigrasikan satu database
# Argumen: $1 = path file db, $2 = nama protokol
migrate_accounts() {
    local source_db="$1"
    local protocol="$2"

    if [ ! -f "$source_db" ]; then
        log_warning "Database sumber tidak ditemukan: $source_db. Melewati."
        return
    fi

    log_info "Memigrasikan akun dari $source_db (protokol: $protocol)..."
    local migrated_count=0
    local skipped_count=0

    # Baca file baris per baris, abaikan baris kosong atau komentar
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Lewati baris kosong atau yang dimulai dengan '# ' (hash + spasi)
        if [[ -z "$line" || "$line" =~ ^#\s ]]; then
            continue
        fi

        # Baca data dari baris. Format: ### [username] [pass/uuid] [quota] [ip_limit] [expired]
        read -r _ username password_or_uuid old_quota_gb old_ip_limit old_expired <<< "$line"

        # Konversi tanggal lama ke Unix epoch
        local expired_epoch=0
        if [ -n "$old_expired" ]; then
            expired_epoch=$(date -d "$old_expired" +%s 2>/dev/null || echo 0)
        fi
        
        local created_at=$(date +%s)

        # --- Konversi kuota lama ke bytes ---
        local quota_bytes_to_insert=$QUOTA_BYTES # Default ke nilai default
        if [[ "$old_quota_gb" =~ ^[0-9]+$ ]]; then
            quota_bytes_to_insert=$(($old_quota_gb * 1024 * 1024 * 1024))
            log_info "  -> Menggunakan kuota lama untuk $username: $old_quota_gb GB"
        else
            log_warning "  -> Kuota lama untuk '$username' tidak valid ('$old_quota_gb'). Menggunakan default ($QUOTA_GB GB)."
        fi

        # --- Gunakan IP limit lama ---
        local ip_limit_to_insert=$IP_LIMIT # Default ke nilai default
        if [[ "$old_ip_limit" =~ ^[0-9]+$ ]]; then
            ip_limit_to_insert=$old_ip_limit
            log_info "  -> Menggunakan IP limit lama untuk $username: $old_ip_limit"
        else
            log_warning "  -> IP limit lama untuk '$username' tidak valid ('$old_ip_limit'). Menggunakan default ($IP_LIMIT)."
        fi

        # --- Sanitasi data untuk mencegah SQL Injection ---
        # Ganti setiap kutip tunggal (') dengan dua kutip tunggal ('')
        # Ini adalah cara standar untuk escape karakter kutip di SQL.
        local safe_username="${username//\'/\'\'}"
        local safe_password_or_uuid="${password_or_uuid//\'/\'\'}"

        # --- Gunakan Here Document untuk perintah sqlite3 ---
        sqlite3 "$DEST_DB" <<EOF
INSERT INTO accounts (username, protocol, password_or_uuid, expired_at, quota, quota_usage, ip_limit, created_at, is_active)
VALUES ('$safe_username', '$protocol', '$safe_password_or_uuid', $expired_epoch, $quota_bytes_to_insert, 0, $ip_limit_to_insert, $created_at, 1);
EOF

        if [ $? -eq 0 ]; then
            ((migrated_count++))
            log_success "  -> Berhasil memigrasi: $username"
        else
            ((skipped_count++))
            log_warning "  -> Dilewati (mungkin duplikat atau error DB): $username"
        fi
    done < "$source_db"

    log_info "Migrasi $protocol selesai. Berhasil: $migrated_count, Dilewati: $skipped_count."
    echo "----------------------------------------"
}

# --- Skrip Utama ---

clear
echo "=========================================================="
echo "      MIGRASI AKUN KE DATABASE TERPUSAT"
echo "=========================================================="
echo

# 1. Periksa ketergantungan
check_dependencies

# 2. Buat backup database tujuan jika sudah ada
if [ -f "$DEST_DB" ]; then
    backup_file="${DEST_DB}.backup.$(date +%s)"
    log_info "Database tujuan ditemukan. Membuat backup di $backup_file"
    cp "$DEST_DB" "$backup_file"
    if [ $? -ne 0 ]; then
        log_error "Gagal membuat backup. Proses dibatalkan."
        exit 1
    fi
fi

# 3. Pastikan direktori tujuan ada
mkdir -p "$(dirname "$DEST_DB")"

# 4. Buat tabel di database tujuan jika belum ada
log_info "Mempersiapkan tabel di database tujuan..."
sqlite3 "$DEST_DB" "CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    protocol TEXT NOT NULL,
    password_or_uuid TEXT NOT NULL,
    expired_at INTEGER NOT NULL,
    quota INTEGER DEFAULT 0,
    quota_usage INTEGER DEFAULT 0,
    ip_limit INTEGER DEFAULT 0,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    is_active INTEGER DEFAULT 1
);"

if [ $? -ne 0 ]; then
    log_error "Gagal membuat tabel di database. Periksa izin penulisan."
    exit 1
fi

log_success "Tabel 'accounts' siap."

# 5. Jalankan proses migrasi untuk setiap database
echo
migrate_accounts "$VMESS_DB" "vmess"
migrate_accounts "$VLESS_DB" "vless"
migrate_accounts "$TROJAN_DB" "trojan"
migrate_accounts "$SSH_DB" "ssh"

# 6. Atur izin file database untuk keamanan
echo
log_info "Mengatur izin file untuk database di $DEST_DB..."
chown root:root "$DEST_DB"
if [ $? -ne 0 ]; then
    log_warning "Gagal mengubah kepemilikan file database. Silakan atur manual dengan: chown root:root $DEST_DB"
fi

chmod 600 "$DEST_DB"
if [ $? -ne 0 ]; then
    log_error "GAGAL: Tidak dapat mengatur izin file database ke 600. Ini adalah RISIKO KEAMANAN."
    log_error "Silakan atur secara manual dengan menjalankan perintah: chmod 600 $DEST_DB"
else
    log_success "Izin file database telah diatur ke 600 (hanya root yang dapat membaca/menulis)."
fi

# 7. Selesai
echo
echo "=========================================================="
log_success "Proses migrasi semua akun telah selesai!"
echo "=========================================================="
echo "Database terpusat berada di: $DEST_DB"
echo "Jika ada masalah, Anda dapat memulihkan dari file backup yang dibuat."
echo
