#!/bin/bash

# Konfigurasi Dasar
CONFIG_PATH="/etc/vpn-api/config.json"
USER_DB="/etc/vpn-api/users.json"
XRAY_CONFIG="/etc/xray/config.json"

# Validasi API Key
validate_api_key() {
    local provided_key="$1"
    local stored_key=$(jq -r '.api_key' "$CONFIG_PATH")
    
    if [[ "$provided_key" != "$stored_key" ]]; then
        echo "Invalid API Key"
        exit 1
    fi
}

# Fungsi untuk memeriksa apakah user sudah ada
is_user_exists() {
    local username="$1"
    
    # Cek apakah user dengan username sudah ada
    jq -e --arg username "$username" \
        '.users[] | select(.username == $username)' \
        "$USER_DB" > /dev/null
}

# Modifikasi fungsi add_user untuk meminta input tambahan
add_user() {
    local username="$1"
    local protocol="$2"
    local validity_days="${3:-30}"
    local quota="${4:-100}"      # Tambah parameter quota
    local ip_limit="${5:-3}"     # Tambah parameter IP limit

    # Generate UUID
    local uuid=$(uuidgen)
    local expiry_date=$(date -d "+$validity_days days" +"%Y-%m-%d")

    # Tambah user ke database
    jq --arg username "$username" \
       --arg uuid "$uuid" \
       --arg protocol "$protocol" \
       --arg expiry "$expiry_date" \
       --arg quota "$quota" \
       --arg iplimit "$ip_limit" \
       '.users += [{"username": $username, "uuid": $uuid, "protocol": $protocol, "expiry": $expiry, "quota": $quota, "iplimit": $iplimit}]' \
       "$USER_DB" > temp.json && mv temp.json "$USER_DB"

    # Fungsi untuk mencatat user di database spesifik protokol
    record_user_to_specific_db() {
        local db_path="$1"
        echo "### ${username} ${expiry_date} ${uuid} ${quota} ${iplimit}" >> "$db_path"
    }

    # Generate konfigurasi dan catat user sesuai protokol
    case "$protocol" in
        "vmess")
            generate_vmess_config "$uuid" "$username"
            record_user_to_specific_db "/etc/vmess/.vmess.db"
            ;;
        "vless")
            generate_vless_config "$uuid" "$username"
            record_user_to_specific_db "/etc/vless/.vless.db"
            ;;
        "trojan")
            generate_trojan_config "$uuid" "$username"
            record_user_to_specific_db "/etc/trojan/.trojan.db"
            ;;
        *)
            echo "Protokol tidak didukung"
            exit 1
            ;;
    esac

    # Simpan limit IP
    if [[ "$ip_limit" -gt 0 ]]; then
        mkdir -p "/etc/kyt/limit/${protocol}/ip"
        echo "$ip_limit" > "/etc/kyt/limit/${protocol}/ip/${username}"
    fi
    
    # Simpan quota
    if [[ "$quota" -gt 0 ]]; then
        mkdir -p "/etc/files/${protocol}"
        echo "$((quota * 1024 * 1024 * 1024))" > "/etc/files/${protocol}/${username}"
    fi

    # Restart Xray
    systemctl restart xray

    # Keluarkan informasi
    echo "{\"status\": \"success\", \"username\": \"$username\", \"uuid\": \"$uuid\", \"expiry\": \"$expiry_date\", \"quota\": \"$quota\", \"iplimit\": \"$ip_limit\"}"
}

# Fungsi generate konfigurasi Vmess
generate_vmess_config() {
    local uuid="$1"
    local username="$2"
    local config_path="/etc/xray/config.json"
    local backup_path="/etc/xray/config.json.bak"
    local temp_path="/etc/xray/config.json.tmp"

    # Debug: Cetak input
    echo "Debug: UUID = $uuid" >&2
    echo "Debug: Username = $username" >&2

    # Validasi input
    if [[ -z "$uuid" ]] || [[ -z "$username" ]]; then
        echo "Error: UUID dan username diperlukan" >&2
        return 1
    fi

    # Pastikan file konfigurasi ada dan tidak kosong
    if [[ ! -s "$config_path" ]]; then
        echo "Error: File konfigurasi kosong atau tidak ada" >&2
        return 1
    fi

    # Validasi JSON sebelum manipulasi
    if ! jq empty "$config_path" > /dev/null 2>&1; then
        echo "Error: Konfigurasi JSON tidak valid" >&2
        return 1
    fi

    # Debug: Cetak konfigurasi WS sebelum perubahan
    echo "Debug: Konfigurasi WS sebelum perubahan:" >&2
    jq '.inbounds[] | select(.protocol == "vmess" and .streamSettings.network == "ws")' "$config_path" >&2

    # Buat backup sebelum manipulasi
    cp "$config_path" "$backup_path"

    # Tambahkan user ke konfigurasi WebSocket Vmess
    jq --arg uuid "$uuid" \
       --arg username "$username" \
       '(.inbounds[] | 
         select(.protocol == "vmess" and .streamSettings.network == "ws") | 
         .settings.clients) += [{"id": $uuid, "alterId": 0, "email": $username}]' \
       "$config_path" > "$temp_path.ws"

    # Debug: Cetak konfigurasi WS setelah perubahan
    echo "Debug: Konfigurasi WS setelah perubahan:" >&2
    jq '.' "$temp_path.ws" >&2

    # Tambahkan user ke konfigurasi gRPC Vmess
    jq --arg uuid "$uuid" \
       --arg username "$username" \
       '(.inbounds[] | 
         select(.protocol == "vmess" and .streamSettings.network == "grpc") | 
         .settings.clients) += [{"id": $uuid, "alterId": 0, "email": $username}]' \
       "$temp_path.ws" > "$temp_path"

    # Debug: Cetak konfigurasi gRPC setelah perubahan
    echo "Debug: Konfigurasi gRPC setelah perubahan:" >&2
    jq '.' "$temp_path" >&2

    # Validasi konfigurasi baru
    if ! jq empty "$temp_path" > /dev/null 2>&1; then
        echo "Error: Konfigurasi baru tidak valid" >&2
        # Kembalikan backup jika gagal
        mv "$backup_path" "$config_path"
        rm -f "$temp_path" "$temp_path.ws"
        return 1
    fi

    # Perbarui konfigurasi
    mv "$temp_path" "$config_path"
    rm -f "$temp_path.ws"

    # Buat file konfigurasi klien
    mkdir -p /var/www/html
    local domain=$(cat /etc/xray/domain)
    cat > "/var/www/html/vmess-$username.txt" <<-END
[server]
remarks = $username
server = $domain
port = 443
type = vmess
id = $uuid
alterId = 0
network = ws
path = /vmess
tls = true
allowInsecure = false
END

    # Log keberhasilan
    echo "Berhasil menambahkan user $username dengan UUID $uuid" >&2

    # Restart Xray
    if ! systemctl restart xray; then
        echo "Error: Gagal restart Xray" >&2
        return 1
    fi

    return 0
}
# Fungsi generate konfigurasi Vless
generate_vless_config() {
    local uuid="$1"
    local username="$2"
    local config_path="/etc/xray/config.json"

    local updated_config=$(jq --arg uuid "$uuid" --arg username "$username" \
        '.inbounds[] | select(.protocol == "vless" and .settings.clients) | 
        .settings.clients += [{"id": $uuid, "email": $username}]' \
        "$config_path")

    # Logika yang sama dengan generate_vmess_config
    if [[ -n "$updated_config" ]]; then
        echo "$updated_config" > /tmp/xray_config_temp.json
        jq -s '.[0] * .[1]' "$config_path" /tmp/xray_config_temp.json > "$config_path.tmp"
        mv "$config_path" "$config_path.bak"
        mv "$config_path.tmp" "$config_path"
        rm -f /tmp/xray_config_temp.json
    else
        echo "Gagal menambahkan user Vless"
        return 1
    fi
}

# Fungsi generate konfigurasi Trojan
generate_trojan_config() {
    local uuid="$1"
    local username="$2"
    local config_path="/etc/xray/config.json"

    local updated_config=$(jq --arg password "$uuid" --arg username "$username" \
        '.inbounds[] | select(.protocol == "trojan" and .settings.clients) | 
        .settings.clients += [{"password": $password, "email": $username}]' \
        "$config_path")

    # Logika yang sama dengan generate_vmess_config
    if [[ -n "$updated_config" ]]; then
        echo "$updated_config" > /tmp/xray_config_temp.json
        jq -s '.[0] * .[1]' "$config_path" /tmp/xray_config_temp.json > "$config_path.tmp"
        mv "$config_path" "$config_path.bak"
        mv "$config_path.tmp" "$config_path"
        rm -f /tmp/xray_config_temp.json
    else
        echo "Gagal menambahkan user Trojan"
        return 1
    fi
}

# Hapus User
delete_user() {
    local username="$1"
    local config_path="/etc/xray/config.json"
    local protocol=""

    # Cari protokol user dari database
    protocol=$(jq -r --arg username "$username" \
        '.users[] | select(.username == $username) | .protocol' "$USER_DB")

    if [[ -z "$protocol" ]]; then
        echo "User tidak ditemukan"
        exit 1
    fi

    # Hapus dari database user
    jq --arg username "$username" \
        'del(.users[] | select(.username == $username))' \
        "$USER_DB" > temp.json && mv temp.json "$USER_DB"

    # Hapus dari konfigurasi Xray sesuai protokol
    case "$protocol" in
        "vmess")
            remove_vmess_user "$username"
            ;;
        "vless")
            remove_vless_user "$username"
            ;;
        "trojan")
            remove_trojan_user "$username"
            ;;
        *)
            echo "Protokol tidak didukung"
            exit 1
            ;;
    esac

    # Restart Xray
    systemctl restart xray

    echo "{\"status\": \"success\", \"message\": \"User $username berhasil dihapus\"}"
}

# Fungsi hapus user Vmess
remove_vmess_user() {
    local username="$1"
    local config_path="/etc/xray/config.json"

    # Hapus user dari konfigurasi
    jq --arg username "$username" \
        '.inbounds[] | select(.protocol == "vmess") | 
        .settings.clients = (.settings.clients | 
        map(select(.email != $username)))' \
        "$config_path" > "$config_path.tmp" && mv "$config_path.tmp" "$config_path"
}

# Fungsi hapus user Vless
remove_vless_user() {
    local username="$1"
    local config_path="/etc/xray/config.json"

    # Hapus user dari konfigurasi
    jq --arg username "$username" \
        '.inbounds[] | select(.protocol == "vless") | 
        .settings.clients = (.settings.clients | 
        map(select(.email != $username)))' \
        "$config_path" > "$config_path.tmp" && mv "$config_path.tmp" "$config_path"
}

# Fungsi hapus user Trojan
remove_trojan_user() {
    local username="$1"
    local config_path="/etc/xray/config.json"

    # Hapus user dari konfigurasi
    jq --arg username "$username" \
        '.inbounds[] | select(.protocol == "trojan") | 
        .settings.clients = (.settings.clients | 
        map(select(.email != $username)))' \
        "$config_path" > "$config_path.tmp" && mv "$config_path.tmp" "$config_path"
}

# Main
main() {
    # Validasi API Key
    validate_api_key "$1"
    
    # Debug: Cetak semua argumen
    echo "Argumen diterima:"
    for arg in "$@"; do
        echo "$arg"
    done
    
    # Aksi
     case "$2" in
        "add")
            # Redirect debug output
            add_user "$3" "$4" "$5" "$6" "$7" 2>/dev/null
            ;;
        "delete")
            delete_user "$3"
            ;;
        *)
            echo "Aksi tidak valid"
            exit 1
            ;;
    esac
}

# Jalankan
main "$@"
