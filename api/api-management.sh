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
    local domain=$(cat /etc/xray/domain)
    local exp=$(date -d "+3 days" +"%Y-%m-%d")  # Default 3 hari

    # Tambahkan user ke konfigurasi Vmess WS
    sed -i '/#vmess$/a\### '"$username $exp"'\
},{"id": "'""$uuid""'","alterId": '"0"',"email": "'""$username""'"' "$config_path"

    # Tambahkan user ke konfigurasi Vmess gRPC
    sed -i '/#vmessgrpc$/a\### '"$username $exp"'\
},{"id": "'""$uuid""'","alterId": '"0"',"email": "'""$username""'"' "$config_path"

    # Buat file konfigurasi klien
    mkdir -p /var/www/html
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

    # Tambahkan ke database
    echo "### ${username} ${exp} ${uuid} 100 3" >> /etc/vmess/.vmess.db

    # Buat direktori jika belum ada
    mkdir -p /etc/vmess
    mkdir -p /etc/kyt/limit/vmess/ip

    # Atur limit IP (default 3)
    echo "3" > /etc/kyt/limit/vmess/ip/$username

    # Atur quota (default 100 GB)
    local quota_bytes=$((100 * 1024 * 1024 * 1024))
    echo "$quota_bytes" > /etc/vmess/$username

    # Restart Xray
    systemctl restart xray

    return 0
}
# Fungsi generate konfigurasi Vless
generate_vless_config() {
    local uuid="$1"
    local username="$2"
    local config_path="/etc/xray/config.json"
    local domain=$(cat /etc/xray/domain)
    local exp=$(date -d "+3 days" +"%Y-%m-%d")  # Default 3 hari

    # Tambahkan user ke konfigurasi Vless WS
    sed -i '/#vless$/a\### '"$username $exp"'\
},{"id": "'""$uuid""'","email": "'""$username""'"' "$config_path"

    # Tambahkan user ke konfigurasi Vless gRPC
    sed -i '/#vlessgrpc$/a\### '"$username $exp"'\
},{"id": "'""$uuid""'","email": "'""$username""'"' "$config_path"

    # Buat file konfigurasi klien
    mkdir -p /var/www/html
    cat > "/var/www/html/vless-$username.txt" <<-END
[server]
remarks = $username
server = $domain
port = 443
type = vless
id = $uuid
network = ws
path = /vless
tls = true
allowInsecure = false
END

    # Tambahkan ke database
    echo "### ${username} ${exp} ${uuid} 100 3" >> /etc/vless/.vless.db

    # Buat direktori jika belum ada
    mkdir -p /etc/vless
    mkdir -p /etc/kyt/limit/vless/ip

    # Atur limit IP (default 3)
    echo "3" > /etc/kyt/limit/vless/ip/$username

    # Atur quota (default 100 GB)
    local quota_bytes=$((100 * 1024 * 1024 * 1024))
    echo "$quota_bytes" > /etc/vless/$username

    # Restart Xray
    systemctl restart xray

    return 0
}

# Fungsi generate konfigurasi Trojan
generate_trojan_config() {
    local uuid="$1"
    local username="$2"
    local config_path="/etc/xray/config.json"
    local domain=$(cat /etc/xray/domain)
    local exp=$(date -d "+3 days" +"%Y-%m-%d")  # Default 3 hari

    # Tambahkan user ke konfigurasi Trojan WS
    sed -i '/#trojan$/a\### '"$username $exp"'\
},{"password": "'""$uuid""'","email": "'""$username""'"' "$config_path"

    # Tambahkan user ke konfigurasi Trojan gRPC
    sed -i '/#trojangrpc$/a\### '"$username $exp"'\
},{"password": "'""$uuid""'","email": "'""$username""'"' "$config_path"

    # Buat file konfigurasi klien
    mkdir -p /var/www/html
    cat > "/var/www/html/trojan-$username.txt" <<-END
[server]
remarks = $username
server = $domain
port = 443
type = trojan
password = $uuid
network = ws
path = /trojan
tls = true
allowInsecure = false
END

    # Tambahkan ke database
    echo "### ${username} ${exp} ${uuid} 100 3" >> /etc/trojan/.trojan.db

    # Buat direktori jika belum ada
    mkdir -p /etc/trojan
    mkdir -p /etc/kyt/limit/trojan/ip

    # Atur limit IP (default 3)
    echo "3" > /etc/kyt/limit/trojan/ip/$username

    # Atur quota (default 100 GB)
    local quota_bytes=$((100 * 1024 * 1024 * 1024))
    echo "$quota_bytes" > /etc/trojan/$username

    # Restart Xray
    systemctl restart xray

    return 0
}

# Fungsi validasi user sebelum menghapus
validate_user_for_deletion() {
    local username="$1"
    local protocol="$2"
    local config_path="/etc/vpn-api/config.json"
    local user_db="/etc/vpn-api/users.json"

    # Validasi username tidak kosong
    if [[ -z "$username" ]]; then
        echo "Error: Username tidak boleh kosong" >&2
        return 1
    fi

    # Validasi protokol tidak kosong
    if [[ -z "$protocol" ]]; then
        echo "Error: Protokol tidak boleh kosong" >&2
        return 1
    fi

    # Validasi protokol
    case "$protocol" in
        "vmess"|"vless"|"trojan")
            # Protokol valid, lanjutkan
            ;;
        *)
            echo "Error: Protokol tidak valid. Gunakan vmess/vless/trojan" >&2
            return 1
            ;;
    esac

    # Periksa apakah user ada di database dengan protokol spesifik
    local user_exists=$(jq --arg username "$username" --arg protocol "$protocol" \
        '.users[] | select(.username == $username and .protocol == $protocol)' "$user_db")
    
    if [[ -z "$user_exists" ]]; then
        echo "Error: User '$username' dengan protokol '$protocol' tidak ditemukan" >&2
        return 1
    fi

    return 0
}
#delete vmess config
remove_vmess_user() {
    local username="$1"
    local config_path="/etc/xray/config.json"

    # Hapus user dari konfigurasi Vmess WS
    sed -i "/### $username /d" "$config_path"
    sed -i "/\"email\": \"$username\"/,/},/d" "$config_path"

    # Hapus dari konfigurasi gRPC
    sed -i "/### $username /d" "$config_path"
    sed -i "/\"email\": \"$username\"/,/},/d" "$config_path"
}

# Fungsi hapus user
delete_user() {
    local username="$1"
    local protocol="$2"
    local config_path="/etc/xray/config.json"
    local user_db="/etc/vpn-api/users.json"

    # Validasi user
    if ! validate_user_for_deletion "$username" "$protocol"; then
        echo "{\"status\": \"error\", \"message\": \"Validasi gagal\"}"
        exit 1
    fi

    # Ambil UUID user untuk logging
    local uuid=$(jq -r --arg username "$username" --arg protocol "$protocol" \
        '.users[] | select(.username == $username and .protocol == $protocol) | .uuid' "$user_db")

    # Hapus dari database user
    jq --arg username "$username" --arg protocol "$protocol" \
        'del(.users[] | select(.username == $username and .protocol == $protocol))' \
        "$user_db" > temp.json && mv temp.json "$user_db"

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
    esac

    # Hapus file pendukung
    rm -f "/var/www/html/${protocol}-$username.txt"
    rm -f "/etc/kyt/limit/${protocol}/ip/$username"
    rm -f "/etc/files/${protocol}/$username"
    
    # Hapus dari database protokol spesifik
    sed -i "/\b${username}\b/d" "/etc/${protocol}/.${protocol}.db"

    # Restart Xray
    systemctl restart xray

    # Keluarkan konfirmasi dengan tambahan UUID
    echo "{\"status\": \"success\", \"message\": \"User $username ($protocol) berhasil dihapus\", \"uuid\": \"$uuid\"}"
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
            delete_user "$3" "$4"  # Tambahkan protokol
            ;;
        *)
            echo "Aksi tidak valid"
            exit 1
            ;;
    esac
}

# Jalankan
main "$@"
