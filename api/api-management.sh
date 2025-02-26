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

# Tambah User
add_user() {
    local username="$1"
    local protocol="$2"
    local validity_days="${3:-30}"

    # Cek apakah user sudah ada
    if is_user_exists "$username"; then
        echo "{\"status\": \"error\", \"message\": \"Username sudah digunakan\"}"
        exit 1
    fi

    # Generate UUID
    local uuid=$(uuidgen)
    local expiry_date=$(date -d "+$validity_days days" +"%Y-%m-%d")

    # Tambah user ke database
    jq --arg username "$username" \
       --arg uuid "$uuid" \
       --arg protocol "$protocol" \
       --arg expiry "$expiry_date" \
       '.users += [{"username": $username, "uuid": $uuid, "protocol": $protocol, "expiry": $expiry}]' \
       "$USER_DB" > temp.json && mv temp.json "$USER_DB"

    # Generate konfigurasi sesuai protokol
    case "$protocol" in
        "vmess")
            generate_vmess_config "$uuid" "$username"
            ;;
        "vless")
            generate_vless_config "$uuid" "$username"
            ;;
        "trojan")
            generate_trojan_config "$uuid" "$username"
            ;;
        *)
            echo "Protokol tidak didukung"
            exit 1
            ;;
    esac

    # Restart Xray
    systemctl restart xray

    # Keluarkan informasi
    echo "{\"status\": \"success\", \"username\": \"$username\", \"uuid\": \"$uuid\", \"expiry\": \"$expiry_date\"}"
}

# Fungsi generate konfigurasi Vmess
generate_vmess_config() {
    local uuid="$1"
    local username="$2"
    local config_path="/etc/xray/config.json"

    # Debug: Cetak semua inbound vmess
    echo "Debug: Semua inbound Vmess" >&2
    jq '.inbounds[] | select(.protocol == "vmess")' "$config_path" >&2

    # Debug: Cetak inbound dengan clients
    echo "Debug: Inbound Vmess dengan clients" >&2
    jq '.inbounds[] | select(.protocol == "vmess" and .settings.clients)' "$config_path" >&2

    # Baca konfigurasi existing
    local updated_config=$(jq --arg uuid "$uuid" --arg username "$username" \
        '.inbounds[] | select(.protocol == "vmess" and .settings.clients) | 
        .settings.clients += [{"id": $uuid, "alterId": 0, "email": $username}]' \
        "$config_path")

    # Debug: Cetak updated_config
    echo "Debug: Updated Config" >&2
    echo "$updated_config" >&2

    # Perbarui konfigurasi
    if [[ -n "$updated_config" ]]; then
        # Simpan konfigurasi sementara
        echo "$updated_config" > /tmp/xray_config_temp.json
        
        # Gabungkan kembali dengan konfigurasi asli
        jq -s '.[0] * .[1]' "$config_path" /tmp/xray_config_temp.json > "$config_path.tmp"
        
        # Backup dan perbarui konfigurasi
        mv "$config_path" "$config_path.bak"
        mv "$config_path.tmp" "$config_path"
        
        # Bersihkan file sementara
        rm -f /tmp/xray_config_temp.json
    else
        echo "Gagal menambahkan user Vmess" >&2
        return 1
    fi
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
    
    # Aksi
    case "$2" in
        "add")
            add_user "$3" "$4" "$5"
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
